# import-csv: CSV 文件到知识网络的完整管线

**日期**: 2026-03-24
**Issue**: #15
**分支**: `feature/15-build-kn-from-db-guide`

## 概述

通过 dataflow API 将本地 CSV 文件导入 KWeaver 可访问的数据源，再构建知识网络。新增两个 CLI 命令和一个 SDK 层 API 封装。

## 动机

e2e 集成测试已验证 CSV → dataflow → MySQL → KN 的完整管线可行，但该能力未暴露给用户。用户目前需要手动将数据导入数据库才能建 KN，门槛过高。

## 架构

```
CSV files
    ↓  (CLI 层: 解析、校验、分批)
ds import-csv
    ↓  (SDK 层: dataflow API)
dataflow.execute()  →  /api/automation/v1/*
    ↓  (平台内置算子)
@internal/database/write  →  数据源表
    ↓  (现有 CLI 命令)
bkn create-from-ds  →  KN + OT + 构建索引
```

组合命令 `bkn create-from-csv` 串联以上全流程。

## 详细设计

### 1. SDK 层: `src/api/dataflow.ts`

封装 4 个 `/api/automation/v1/*` 公开端点:

| 方法 | 端点 | 说明 |
|------|------|------|
| `create(body)` | `POST /api/automation/v1/data-flow/flow` | 创建 DAG |
| `run(dagId)` | `POST /api/automation/v1/run-instance/{dagId}` | 执行 DAG |
| `pollResults(dagId, timeout?)` | `GET /api/automation/v1/dag/{dagId}/results` | 轮询状态 |
| `delete(dagId)` | `DELETE /api/automation/v1/data-flow/flow/{dagId}` | 删除 DAG |

便捷方法:

```typescript
execute(body: DataflowCreateParams, opts?: { timeout: number }): Promise<DataflowResult>
// create → run → pollResults → finally delete
```

类型定义:

```typescript
interface DataflowStep {
  id: string
  title: string
  operator: string
  parameters: Record<string, unknown>
}

interface DataflowCreateParams {
  title: string
  description?: string
  trigger_config: { operator: string }  // e.g. { operator: "@trigger/manual" }
  steps: DataflowStep[]                 // 必须包含 trigger step 作为第一个元素
}

interface DataflowResult {
  status: "success" | "completed" | "failed" | "error"
  reason?: string
}
```

**DAG 结构要求:**

- `steps` 数组第一个元素必须是 trigger step: `{ id: "trigger", title: "trigger", operator: "@trigger/manual", parameters: {} }`
- `run(dagId)` 发送空 JSON body `{}`
- `pollResults` 解析响应格式 `{ results: [{ status, reason }] }`，取 `results[0]` 的状态
- DAG title 附加时间戳后缀（`Date.now()`）确保唯一

轮询间隔: 3s，默认超时: 900s (15 分钟)

### 2. CLI: `kweaver ds import-csv`

在 `src/commands/ds.ts` 新增子命令。

**用法:**

```bash
kweaver ds import-csv <datasource_id> --files <glob_or_list> \
  [--table-prefix <p>] [--batch-size <n>]
```

**参数:**

| 参数 | 必填 | 默认值 | 说明 |
|------|------|--------|------|
| `datasource_id` | 是 | — | 目标数据源 ID |
| `--files` | 是 | — | CSV 文件路径，逗号分隔或 glob |
| `--table-prefix` | 否 | `""` | 表名前缀 |
| `--batch-size` | 否 | 500 | 每批写入行数 |

**表名映射:** `{prefix}{文件名去.csv后缀}`，如 `--table-prefix my_` + `物料.csv` → `my_物料`

**覆盖策略:** 第一批 `table_exist: false`（建表/覆盖），后续批 `table_exist: true, operate_type: append`。

**列映射:** 所有列统一为 `VARCHAR(512)`，空值转 `null`（与 e2e 测试一致）。

**`datasource_type` 获取:** CLI 通过 `kweaver ds get <datasource_id>` 获取数据源元数据，从中提取 `datasource_type`（如 `mysql`），用于构建 DAG step 的 `parameters.datasource_type` 字段。用户无需手动指定。

**CSV 编码:** 默认 UTF-8。支持 BOM 头自动剥离。

**`--batch-size` 校验:** 有效范围 1~10000，超出则报错。

**进度输出:**

```
[物料] batch 1/3 (500 rows)... 2.1s
[物料] batch 2/3 (500 rows)... 1.8s
[物料] batch 3/3 (242 rows)... 1.2s
[物料] done (1242 rows in 5.1s)
[库存] batch 1/1 (156 rows)... 1.5s
[库存] done (156 rows in 1.5s)

Import complete: 2 tables, 1398 rows in 6.6s
```

### 3. CLI: `kweaver bkn create-from-csv`

在 `src/commands/bkn.ts` 新增子命令。

**用法:**

```bash
kweaver bkn create-from-csv <datasource_id> --files <glob_or_list> --name <kn_name> \
  [--table-prefix <p>] [--batch-size <n>] \
  [--build/--no-build] [--timeout <n>] [--tables <t1,t2>]
```

**行为:**

1. 调用 `ds import-csv` 逻辑导入 CSV
2. 调用 `bkn create-from-ds <ds_id>` 创建 KN（透传 `--name`, `--build`, `--timeout`, `--tables`）
3. `--tables` 未指定时默认使用 import 创建的所有表名

**超时说明:** `--timeout` 仅控制 KN 构建阶段（透传给 `create-from-ds`，默认 300s）。import 阶段使用 dataflow 默认超时 900s。

**中止策略:** import 阶段有任何文件失败，中止不继续建 KN。

### 4. 错误处理

**原则:** 能在本地检测的尽早失败，不等 API 调用。

**分层检测:**

| 错误场景 | 检测位置 | 时机 | 反馈 |
|----------|---------|------|------|
| 文件不存在 / glob 无匹配 | CLI | 命令启动 | 立即报错，列出无效路径 |
| CSV 解析失败 | CLI (`csv-parse`) | 读取时 | 报文件名和行号 |
| 无表头 / 空文件 | CLI | 解析后 | 警告跳过 |
| 行数为 0（仅表头） | CLI | 解析后 | 警告跳过 |
| 列数不一致 | CLI (`csv-parse` 严格模式) | 解析时 | 报行号 |
| dataflow 执行失败 | `pollResults` | 轮询时 | 报表名 + 服务端 reason |
| dataflow 超时 | `pollResults` | 超时后 | 报已完成/未完成的表 |
| datasource_id 无效 | API 返回 | 首批执行时 | 透传服务端错误 |

**执行策略:**

- 所有 CSV 先全部解析校验，全部通过后才调 API
- 多文件导入时，某文件 DAG 失败，打印错误继续处理剩余文件，最后汇总
- `create-from-csv` 中 import 有任何失败则中止

### 5. Skill 指南

更新 `skills/kweaver-core/references/build-kn-from-db.md`，新增 CSV 章节。
更新 `skills/kweaver-core/SKILL.md` 的 ds 命令行提及 `import-csv`。

### 6. 依赖

- 新增: `csv-parse`（轻量零依赖 CSV 解析库）

### 7. 测试

| 层 | 方式 | 内容 |
|---|---|---|
| `dataflow.ts` | 单元测试 mock HTTP | 端点调用、超时、错误处理 |
| `ds import-csv` | 单元测试 mock dataflow | CSV 解析、分批、表名、覆盖逻辑 |
| `bkn create-from-csv` | 单元测试 mock import + create-from-ds | 参数透传、表名串联 |

### 8. 不做的事

- 不改 Python SDK
- 不加 Excel/JSON 等格式支持
- 不加自定义列类型映射
- 不加 `--append` 模式（默认覆盖，未来按需加）
