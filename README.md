# KWeaver SDK

让 AI 智能体（Claude Code、GPT、自定义 Agent 等）通过 `kweaver` CLI 命令访问 KWeaver / ADP 平台的知识网络与 Decision Agent。同时提供 Python SDK 供程序化集成。

## 这个项目解决什么问题

KWeaver (ADP) 平台提供了知识网络构建、语义搜索、Decision Agent 对话等能力，但这些能力藏在复杂的 REST API 背后。本项目提供 **`kweaver` CLI 命令行工具**，智能体直接调用 shell 命令即可完成操作，无需了解底层 API 细节。

## 前置条件

1. **Python >= 3.10**
2. **ADP 平台账号**
3. 安装：

```bash
pip install kweaver-sdk[cli]    # CLI + SDK
```

## 认证

提供四种认证方式，按推荐顺序：

### 方式 A（推荐）：CLI 登录

```bash
kweaver auth login https://your-adp-instance.com
kweaver auth login https://your-adp-instance.com --alias prod  # 设别名
```

登录后凭据存储在 `~/.kweaver/`，所有命令自动使用。与 kweaverc (TypeScript CLI) 共享凭据。

### 方式 B：环境变量

```bash
export ADP_BASE_URL="https://your-adp-instance.com"
export ADP_BUSINESS_DOMAIN="bd_public"
export ADP_TOKEN="Bearer ory_at_xxxxx"    # 或 ADP_USERNAME + ADP_PASSWORD
```

> **注意**: `ADP_BUSINESS_DOMAIN` 是必填项。不传或传错会导致 API 返回空结果或 Bad Request。

---

## CLI 命令

### 数据源管理

```bash
# 连接数据库：测试连通性、注册、发现表
kweaver ds connect mysql 10.0.1.100 3306 erp_prod \
    --account readonly --password xxx
# -> {"datasource_id": "ds_01", "tables": [...]}

kweaver ds list [--keyword <filter>] [--type <db-type>]
kweaver ds get <datasource-id>
kweaver ds delete <datasource-id>
kweaver ds tables <datasource-id> [--keyword <filter>]
```

### 知识网络

```bash
# 从数据源创建知识网络（自动检测主键/显示键）
kweaver kn create <datasource-id> --name 供应链 \
    [--tables orders,products] [--no-build] [--timeout 600]
# -> {"kn_id": "kn_abc", "object_types": [...], "status": "completed"}

kweaver kn list [--name <filter>]
kweaver kn get <kn-id>
kweaver kn export <kn-id>              # 导出完整定义（对象类型、关系类型、属性）
kweaver kn build <kn-id> [--no-wait]
kweaver kn delete <kn-id>
```

### 查询

```bash
kweaver query search <kn-id> "高库存的产品"
kweaver query instances <kn-id> <ot-id> [--condition '<json>'] [--limit N]
kweaver query kn-search <kn-id> "<query>" [--only-schema]
kweaver query subgraph <kn-id> \
    --start-type products \
    --start-condition '{"field":"category","operation":"eq","value":"电子"}' \
    --path has_inventory,belongs_to_supplier
```

### Action

```bash
kweaver action query <kn-id> <at-id>
kweaver action execute <kn-id> <at-id> [--params '<json>'] [--no-wait]
kweaver action execute <kn-id> --action-name 库存盘点   # 按名称查找
kweaver action logs <kn-id> [--limit N]
kweaver action log <kn-id> <log-id>
```

### Agent

```bash
kweaver agent list [--keyword <text>]
kweaver agent chat <agent-id> -m "华东仓库库存情况"
kweaver agent chat <agent-id> -m "和上月比呢？" --conversation-id <id>
kweaver agent sessions <agent-id>       # 列出会话
kweaver agent history <conversation-id> # 查看消息历史
```

### 通用 API 调用

```bash
kweaver call /api/ontology-manager/v1/knowledge-networks
kweaver call /api/test -X POST -d '{"key":"val"}'
```

---

## 典型流程

| 场景 | CLI 命令 |
|---|---|
| 从零构建知识网络 | `ds connect` → `kn create` → `kn export` → `query search` |
| 探索已有知识网络 | `kn list` → `kn export <kn-id>` → `query instances` |
| 与 Agent 对话 | `agent list` → `agent chat` → `agent sessions` → `agent history` |
| 执行 Action | `action execute --action-name 库存盘点` |

## Python SDK

CLI 之外，也可以直接使用 Python SDK 进行程序化操作：

```python
from kweaver import ADPClient, ConfigAuth

client = ADPClient(auth=ConfigAuth(), business_domain="bd_public")

# 资源层 API
kns = client.knowledge_networks.list()
result = client.query.semantic_search(kn_id, "高库存的产品")
```

SDK 提供以下资源：`datasources`, `dataviews`, `knowledge_networks`, `object_types`, `relation_types`, `query`, `action_types`, `agents`, `conversations`。

## 在 AI 智能体中使用

### 安装 Skill

通过 [skills.sh](https://skills.sh) 一键安装到 Claude Code、Cursor、OpenClaw 等支持 Skill 的智能体平台：

```bash
npx skills add kweaver-ai/kweaver-sdk --skill kweaver-core
```

安装后需确保运行环境有 Python >= 3.10 且已安装 SDK：

```bash
pip install kweaver-sdk[cli]
```

### 认证

推荐先用 CLI 登录：

```bash
kweaver auth login https://your-adp-instance.com
```

### Claude Code（本地开发）

在 kweaver-sdk 项目目录下工作时，Skill 自动加载（`.claude/skills/kweaver/SKILL.md`）。其他项目可通过上述 `npx skills add` 安装。

## 开发与测试

```bash
# 单元测试
pytest

# E2E 测试（需要 ADP 环境）
pytest tests/e2e/ --run-destructive
```

E2E 测试推荐先用 `kweaver auth login` 登录，测试会自动使用 `~/.kweaver/` 凭据。
