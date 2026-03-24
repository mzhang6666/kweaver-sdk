---
name: kweaver-core
description: >-
  操作 KWeaver 知识网络与 Decision Agent — 构建知识网络、查询 Schema/实例、
  语义搜索、执行 Action、Agent CRUD 与对话。
  操作 Vega 可观测平台 — 查询 Catalog/资源/连接器类型、健康巡检。
  当用户提到"知识网络"、"知识图谱"、"查询对象类"、
  "执行 Action"、"有哪些 Agent"、"创建 Agent"、"跟 Agent 对话"、
  "数据源"、"Catalog"、"Vega"、
  "健康检查"、"巡检"等意图时自动使用。
allowed-tools: Bash(kweaver *), Bash(npx kweaver *)
argument-hint: [自然语言指令]
---

# KWeaver CLI

KWeaver 平台的命令行工具，覆盖认证、知识网络管理与查询、Agent CRUD 与对话、数据源管理。

> **此 skill 替代旧版 `kweaver-core`**，新增 Vega 可观测平台、BKN push/pull 等功能。
> 旧版仍可使用但不再更新。

## 安装

```bash
npm install -g @kweaver-ai/kweaver-sdk
```

需 Node.js 22+。也可用 `npx kweaver` 临时运行。

## 使用方式

```bash
kweaver <command> [subcommand] [options]
```

**完整子命令与参数以当前安装的 CLI 为准**：运行 `kweaver --help`（或 `-h`）查看与代码同步的用法列表；查版本用 `kweaver --version` / `-V` / `kweaver version`。子命令细节用 `kweaver <group> <subcommand> --help`（例如 `kweaver auth --help`、`kweaver bkn push --help`）。

本 skill 下的 `references/*.md` 与 CLI 行为对齐；**表格与 reference 为速查**，新增标志（如 `auth` 的 `--alias`、BKN `validate`/`push` 的编码选项）在 reference 中有说明。

**别名**：`kweaver curl` 等同于 `kweaver call`；`kweaver context` 等同于 `kweaver context-loader`。

## 使用前提

**认证凭据通过 `~/.kweaver/` 管理，支持自动刷新。禁止提前检查环境变量，禁止询问用户提供密码或 Token。**

### 认证优先级

1. `KWEAVER_TOKEN` + `KWEAVER_BASE_URL` 环境变量 → 静态 Token（如存在则优先使用，**不会**自动刷新）
2. `~/.kweaver/` 凭据（`kweaver auth login` 写入）→ 自动刷新（推荐）

## 命令组总览

| 命令组 | 说明 | 常用命令 | 详细参考 |
|--------|------|---------|---------|
| `auth` | 认证管理 | `auth login <url> [--alias name]`（简写：`auth <url> [--alias …]`）；可选 `-u`/`-p` 或 `--playwright`；`auth use` / `status` / `logout` / `delete` 支持平台 URL 或别名 | `references/auth.md` |
| `token` | 打印当前 access token（自动刷新） | `token` | — |
| `bkn` | BKN 知识网络管理、Schema、查询、Action | `bkn validate`/`push` 默认检测 `.bkn` 编码并规范为 UTF-8，可用 `--no-detect-encoding` 或 `--source-encoding gb18030`；另有 `pull`、`object-type`、`search`、`create-from-ds`/`create-from-csv` 等，见 `references/bkn.md` | `references/bkn.md` |
| `agent` | Agent CRUD、发布、对话 | `agent list`, `agent get <id>`, `agent chat <id> -m "..."`、`agent sessions <agent_id>`、`agent history <conversation_id>` | `references/agent.md` |
| `ds` | 数据源管理 | `ds list`, `ds get <id>`, `ds import-csv <file> --name <name>` | `references/ds.md` |
| `vega` | Vega 可观测平台 | `vega health`, `vega catalog list`, `vega resource list` | `references/vega.md` |
| `config` | 平台配置（business domain 等） | `config show`, `config set-bd <uuid>` | `references/config.md` |
| `context-loader` | MCP 分层检索 | `context-loader config show`, `context-loader kn-search <query>` | `references/context-loader.md` |
| `call` | 通用 API 调用 | `call <url> [-X POST] [-d '...']`（可用 `curl` 别名；支持 `--url`、`--data-raw` 等，见 `kweaver --help`） | `references/call.md` |

## 操作指南

| 场景 | 说明 | 详细参考 |
|------|------|---------|
| 从数据库/CSV 构建 KN | 连接数据源 → CSV 导入 → 创建 KN → 构建索引 → 查询验证 → 绑定 Agent | [references/build-kn-from-db.md](references/build-kn-from-db.md) |

**按需阅读**：需要子命令完整参数或编排示例时，读取对应的 reference 文件。

## 调用示例

```
/kweaver 列出所有知识网络
/kweaver 查看 Vega 健康状况
/kweaver 有哪些 Agent
/kweaver 跟 Agent xxx 对话，问他"今天库存情况"
/kweaver 搜索知识网络 xxx 中关于"供应链"的内容
```

## 注意事项

- **不要自行猜测 business_domain 值**。首次使用时运行 `kweaver config show` 确认当前 business domain。如果返回 `bd_public (default)` 但命令结果为空，可能需要用 `kweaver config set-bd <uuid>` 设置正确的值（从平台 UI 的请求头中获取 `X-Business-Domain`）
- Action 执行有副作用，执行前向用户确认
- **禁止运行 `kweaver auth status` 做预检**。直接执行目标命令，CLI 会自动处理认证和 token 刷新
- Token 1 小时过期。当 `~/.kweaver/` 中存在 `refresh_token`（通过 OAuth2 登录获得）时，CLI 会**自动刷新**；仅 Playwright cookie 登录（无 `refresh_token`）时需要用户重新运行 `kweaver auth login <url>`。遇到 401 错误时 CLI 会自动尝试刷新，刷新失败才提示用户重新登录

## 查询策略（重要）

**所有 `object-type query` 调用必须遵守以下规则，否则返回数据过大会导致 JSON 截断和解析失败：**

1. **limit 不要超过 30**。CLI 默认 limit=30。字段多的宽表建议 limit 10~20，按实际单条记录大小调整
2. **需要更多数据时使用 `search_after` 分页**，不要加大 limit：
   ```
   # 第一页
   kweaver bkn object-type query <kn> <ot> '{"limit":20}'
   # → 返回 search_after: ["v1","v2","v3"]
   # 第二页
   kweaver bkn object-type query <kn> <ot> '{"limit":20,"search_after":["v1","v2","v3"]}'
   ```
3. **尽量使用 `condition` 过滤**，缩小返回集：按编号、名称、状态等精确或模糊过滤，避免全表扫描
4. **优先使用 `==`、`like`、`in` 操作符**（SQL 视图兼容）。`match`/`contain` 仅 OpenSearch 索引支持，SQL 视图下会报错
5. **自动裁剪**：当查询结果超过 100KB 时，CLI 会自动裁剪 `datas` 数组并附加 `_truncated` 字段。如果返回中包含 `_truncated`，按其中的 `hint` 提示执行下一轮查询：
   ```json
   {"_truncated": {"returned": 176, "total_fetched": 200, "remaining": 24,
     "next_search_after": ["v1","v2","v3"],
     "hint": "Pass --search-after '[...]' --limit 176 to fetch the next page."}}
   ```
   直接使用 `next_search_after` 的值作为下一次查询的 `--search-after` 参数即可
