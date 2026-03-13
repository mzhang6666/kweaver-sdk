---
name: kweaver
description: >-
  操作 ADP 知识网络与 Decision Agent — 连接数据库、构建知识网络、查询 Schema/实例、
  语义搜索、执行 Action、列举 Agent、与 Agent 对话。
  当用户提到"知识网络"、"知识图谱"、"连接数据库并建模"、"查询对象类"、
  "执行 Action"、"有哪些 Agent"、"跟 Agent 对话"等意图时自动使用。
allowed-tools: Bash(python *), Bash(${KWEAVER_PYTHON:-python} *), Bash(kweaver *)
argument-hint: [自然语言指令]
requires:
  env: [ADP_BASE_URL, ADP_BUSINESS_DOMAIN, ADP_TOKEN, ADP_USERNAME, ADP_PASSWORD]
  bins: [python]
---

# KWeaver CLI

KWeaver/ADP 平台的命令行工具，覆盖认证、数据源管理、知识网络管理与查询、Action 执行、Agent 对话六大能力。

## 安装

```bash
pip install kweaver-sdk[cli]
```

或从源码安装：

```bash
pip install -e "/path/to/kweaver-sdk[cli]"
```

需 Python >= 3.10。

## 使用前提

**使用任何命令前，必须先认证。** 若用户未认证，提示先执行 `kweaver auth login <platform-url>`。

**重要规则**:
1. 如果环境变量 `KWEAVER_PYTHON` 已设置，用它作为 Python 解释器路径；否则用 `python`
2. **所有环境变量已预配置，直接执行命令即可。禁止提前检查环境变量是否存在，禁止询问用户提供密码或 Token。**

### 认证优先级

CLI 按以下顺序尝试认证（无需用户干预）：

1. **ConfigAuth**（推荐）— 读取 `~/.kweaver/` 凭据（与 kweaverc CLI 共享），自动刷新 Token
2. **PasswordAuth** — 通过 `ADP_USERNAME` + `ADP_PASSWORD` 环境变量
3. **TokenAuth** — 通过 `ADP_TOKEN` 环境变量

环境变量 `ADP_BASE_URL` 和 `ADP_BUSINESS_DOMAIN` 用于指定平台地址和业务域。

---

## 命令速查

### 认证 (auth)

```bash
kweaver auth login <platform-url>                # 浏览器 OAuth2 登录
kweaver auth login <platform-url> --alias prod   # 登录并设别名
kweaver auth status                              # 当前认证状态
kweaver auth list                                # 已保存的平台
kweaver auth use <platform|alias>                # 切换平台
kweaver auth logout                              # 登出
```

### 数据源 (ds)

```bash
kweaver ds connect <db_type> <host> <port> <database> --account <user> --password <pass> [--schema <schema>] [--name <ds_name>]
kweaver ds list [--keyword <text>] [--type <db_type>]
kweaver ds get <datasource_id>
kweaver ds delete <datasource_id>
kweaver ds tables <datasource_id> [--keyword <text>]
```

### 知识网络 (kn)

```bash
kweaver kn list [--name <filter>]
kweaver kn get <kn-id>
kweaver kn export <kn-id>
kweaver kn create <datasource_id> --name <kn_name> [--tables <t1,t2,...>] [--build/--no-build] [--timeout N]
kweaver kn build <kn-id> [--no-wait] [--timeout N]
kweaver kn delete <kn-id>
```

### 查询 (query)

```bash
kweaver query search <kn-id> "<query>" [--max-concepts N]
kweaver query instances <kn-id> <ot-id> [--condition '<json>'] [--limit N]
kweaver query kn-search <kn-id> "<query>" [--only-schema]
kweaver query subgraph <kn-id> --start-type <ot_name> --start-condition '<json>' --path <rt1,rt2,...>
```

### Action (action)

```bash
kweaver action query <kn-id> <action_type_id>
kweaver action execute <kn-id> [<action_type_id>] [--action-name <name>] [--params '<json>'] [--no-wait] [--timeout N]
kweaver action logs <kn-id> [--limit N]
kweaver action log <kn-id> <log-id>
```

> `execute` 可通过 `--action-name` 按名称查找 action_type_id（内部调用 kn-search）。

### Agent (agent)

```bash
kweaver agent list [--keyword <text>]
kweaver agent chat <agent-id> -m "<message>" [--conversation-id <id>]
kweaver agent sessions <agent-id>
kweaver agent history <conversation-id> [--limit N]
```

### 通用 API 调用 (call)

```bash
kweaver call <path>                              # GET（自动注入认证）
kweaver call <path> -X POST -d '<json>'          # POST
```

---

## 操作手册

### 1. 从零构建知识网络

```bash
# 连接数据库，获取 datasource_id 和表列表
kweaver ds connect mysql 10.0.1.100 3306 erp_prod --account readonly --password xxx

# 用 datasource_id 创建知识网络（自动构建）
kweaver kn create <datasource_id> --name erp_prod --tables products,inventory

# 查看知识网络结构
kweaver kn export <kn-id>

# 语义搜索
kweaver query search <kn-id> "高库存的产品"
```

### 2. 探索已有知识网络

```bash
# 列出所有知识网络
kweaver kn list

# 导出某个知识网络的完整结构（对象类型、关系类型、属性）
kweaver kn export <kn-id>

# 查看某个对象类型的实例数据
kweaver query instances <kn-id> <ot-id> --limit 10
```

### 3. Agent 对话

```bash
# 列出可用 Agent
kweaver agent list

# 与 Agent 对话（自动创建会话）
kweaver agent chat <agent-id> -m "华东仓库库存情况"

# 查看该 Agent 的所有会话
kweaver agent sessions <agent-id>

# 查看某个会话的历史消息
kweaver agent history <conversation-id>
```

### 4. 执行 Action

```bash
# 按名称执行 Action（自动查找 action_type_id）
kweaver action execute <kn-id> --action-name "库存盘点"

# 按 ID 执行，传入参数
kweaver action execute <kn-id> <action_type_id> --params '{"warehouse": "华东"}'

# 查看执行日志
kweaver action logs <kn-id>
kweaver action log <kn-id> <log-id>
```

---

## 注意事项

- **不要自行猜测或枚举 business_domain 值**，只使用环境变量中配置的值。
- 如果 API 返回 "Bad Request"，最常见原因是 Token 过期或 business_domain 未设置。
- `execute_action` 有副作用，仅在用户明确请求时执行，执行前向用户确认。
- 构建知识网络 (`kn create` / `kn build`) 可能需要等待一段时间，提前告知用户。
- 所有命令输出 JSON 格式，可用 `jq` 进一步处理。
