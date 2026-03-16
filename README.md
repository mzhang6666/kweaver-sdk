# KWeaver SDK

让 AI 智能体（Claude Code、GPT、自定义 Agent 等）通过 `kweaver` CLI 命令访问 KWeaver 平台的知识网络与 Decision Agent。同时提供 Python SDK 供程序化集成。

## 安装

### TypeScript CLI（推荐，含交互式 agent chat TUI）

```bash
npm install -g kweaver-sdk
```

需 Node.js 22+。安装后使用 `kweaver` 命令。

### Python CLI（备用，用于测试或无 Node 环境）

```bash
pip install kweaver-sdk[cli]
```

需 Python >= 3.10。安装后同样使用 `kweaver` 命令。

### Python SDK（程序化调用）

```bash
pip install kweaver-sdk
```

```python
from kweaver import KWeaverClient, ConfigAuth

client = KWeaverClient(auth=ConfigAuth(), business_domain="bd_public")
kns = client.knowledge_networks.list()
```

## 定位

| 入口 | 安装方式 | 用途 |
|------|----------|------|
| **TS CLI** | `npm install -g kweaver-sdk` | 主力 CLI，含 Ink 交互式 TUI、流式 agent chat |
| **Python CLI** | `pip install kweaver-sdk[cli]` | 备用 CLI，功能对齐，用于测试或纯 Python 环境 |
| **Python SDK** | `pip install kweaver-sdk` | 程序化 API，`from kweaver import KWeaverClient` |

两套 CLI 命令结构完全一致（`kweaver auth`、`kweaver bkn`、`kweaver agent`、`kweaver context-loader` 等），凭据共享 `~/.kweaver/`。

## 认证

```bash
kweaver auth login https://your-kweaver-instance.com
kweaver auth login https://your-kweaver-instance.com --alias prod
```

或使用环境变量：`KWEAVER_BASE_URL`、`KWEAVER_BUSINESS_DOMAIN`、`KWEAVER_TOKEN`（或 `KWEAVER_USERNAME` + `KWEAVER_PASSWORD`）。

## 命令速查

```bash
kweaver auth login/status/list/use/delete/logout
kweaver token
kweaver bkn list/get/stats/export/create/update/delete
kweaver bkn object-type query/properties
kweaver bkn subgraph
kweaver bkn action-type query/execute
kweaver bkn action-execution get
kweaver bkn action-log list/get/cancel
kweaver agent list/chat/sessions/history
kweaver context-loader config set/use/list/show
kweaver context-loader kn-search/query-object-instance/...
kweaver call <path> [-X METHOD] [-d BODY] [-H header] [-bd domain]
```

Python CLI 额外提供：`kweaver ds`（数据源）、`kweaver query`（语义搜索、实例、子图）、`kweaver action`（高层编排）。

## 项目结构（Monorepo）

```
kweaver-sdk/
├── packages/
│   ├── python/          # Python SDK + CLI
│   └── typescript/      # TypeScript CLI
├── skills/kweaver-core/ # AI Agent 操作手册
├── docs/
└── README.md
```

## CLI 手动测试

以下命令用于验证 CLI 功能，需先完成 `kweaver auth login`。业务域默认 `bd_public`，可通过 `KWEAVER_BUSINESS_DOMAIN` 或 `-bd` 覆盖。

```bash
# 可选：覆盖业务域（默认 bd_public）
# export KWEAVER_BUSINESS_DOMAIN=bd_public

# 1. 认证状态
kweaver auth status

# 2. Agent 列表（默认简化输出 name/id/description）
kweaver agent list
kweaver agent list -v              # 完整输出

# 3. 给 Agent 发消息（替换 <agent_id> 为 agent list 返回的 id）
kweaver agent chat <agent_id> -m "你好"
# 续聊：使用上一条返回的 --conversation-id
kweaver agent chat <agent_id> -m "今天天气怎么样" --conversation-id <conversation_id>

# 4. BKN 列表（默认 limit=50，简化输出）
kweaver bkn list
kweaver bkn list -v                # 完整输出
kweaver bkn list --limit 10        # 限制条数

# 5. Context-loader（需先配置 kn-id）
kweaver context-loader config set --kn-id <kn_id> --name my-bkn
kweaver context-loader config use my-bkn
kweaver context-loader kn-search "关键词"
kweaver context-loader tools       # 列出可用工具

# 6. 原始 API 调用
kweaver call "/api/agent-factory/v3/personal-space/agent-list?offset=0&limit=3" --pretty
```

**TypeScript CLI**（需 Node.js 24+，`nvm use 24`）：

```bash
cd packages/typescript
npx tsx src/cli.ts auth status
npx tsx src/cli.ts agent list
npx tsx src/cli.ts agent chat <agent_id> -m "你好"
npx tsx src/cli.ts bkn list
npx tsx src/cli.ts context-loader config set --kn-id <kn_id>
npx tsx src/cli.ts context-loader kn-search "关键词"
```

**Python CLI**：

```bash
cd packages/python
.venv/bin/kweaver auth status
.venv/bin/kweaver agent list
.venv/bin/kweaver agent chat <agent_id> -m "你好"
.venv/bin/kweaver bkn list
.venv/bin/kweaver context-loader config set --kn-id <kn_id>
.venv/bin/kweaver context-loader kn-search "关键词"
```

## 开发与测试

```bash
# 运行所有测试（Python + TypeScript）
make test

# 仅 Python
make -C packages/python test

# 仅 TypeScript
make -C packages/typescript test
```

## 在 AI 智能体中使用

```bash
npx skills add kweaver-ai/kweaver-sdk --skill kweaver-core
```

详见 [skills/kweaver-core/SKILL.md](skills/kweaver-core/SKILL.md)。
