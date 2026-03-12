# ADP Python SDK & Skill 设计文档

v0.4.0 | 2026-03-12

---

## 1 背景

ADP 平台通过多个微服务提供从数据接入到知识查询的全链路能力。但这些能力只通过 REST API 暴露，存在三个问题：

1. **Agent 不可直接使用** — Agent 需要的是意图级操作（"把这个库变成知识网络"），而非拼装 HTTP 请求。
2. **链路割裂** — 完成一个流程需跨多个服务、多步调用，调用方需理解服务边界和参数传递。
3. **无 Python 入口** — 当前只有前端 TypeScript 客户端，Agent 框架和数据工具链无法程序化使用。

---

## 2 功能目标

构建面向 Agent 的 ADP 技能层。三个核心场景：

1. **从数据库自动构建可查询的知识网络**（写入路径）
2. **通过 Context Loader 查询知识网络的 Schema 与对象**（读取路径）
3. **发现并与 Decision Agent 对话**（交互路径）

场景 1→2 构成"构建→探索→查询"闭环；场景 3 在此基础上进一步将知识网络的能力通过 Decision Agent 暴露给终端用户，形成"构建→探索→Agent 对话"的完整价值链。

设计上需容纳未来的其他技能，包括但不限于：

| 技能 | 数据来源 | 产出 |
|------|---------|------|
| **从数据库构建** (v0.1) | 数据库连接 | 知识网络 |
| **Context Loader** (v0.2) | 知识网络 ID | Schema 结构 + 对象实例 |
| **Agent 列举与对话** (v0.4) | Decision Agent ID | Agent 列表 + 对话回复 |
| 从文档构建 (规划) | 文件路径 / URL | 知识网络 |
| 查询知识 (规划) | 知识网络 ID + 自然语言 | 结构化结果 |
| 执行行动 (规划) | 行动类 + 实例 | 执行结果 |

因此 SDK 层的模块划分和 Skill 层的接口设计，都需要是可组合、可扩展的，而非只服务于单一流程。

---

## 3 设计思路与折衷

### 3.1 三层分离

```
┌───────────────────────────────────────────────┐
│  Skill 层（对外）                              │
│  Agent 看到的 Tool 定义，意图级粒度             │
│  不暴露 ADP 内部概念（DataView、kn_id...）      │
├───────────────────────────────────────────────┤
│  SDK 层（内部实现）                             │
│  Python 方法，1:1 映射 ADP 概念                 │
│  类型安全、跨服务编排、参数转换                  │
├───────────────────────────────────────────────┤
│  HTTP 层（传输）                               │
│  httpx / 认证 / 重试 / Header 注入             │
└───────────────────────────────────────────────┘
```

**对外 vs 内部的边界原则：**

- Agent 看到的（Skill Tool）：业务语义参数（数据库地址、表名、查询意图），不出现 `dataview_id`、`kn_id` 等 ADP 内部 ID。
- 开发者看到的（SDK）：ADP 概念的 Python 映射，需要理解 DataSource → DataView → ObjectType 的关系。
- 两者均不暴露 REST 层的嵌套结构（`bin_data`、`ResourceInfo`、`mapping_rules`）。

### 3.2 Skill 粒度选择

| 方案 | 优点 | 缺点 |
|------|------|------|
| 一个 Skill 覆盖全流程 | Agent 一次调用完成 | 参数太多，灵活性差 |
| 每个 REST 接口一个 Tool | 最大灵活性 | Agent 决策负担重，易出错 |
| **按用户意图分组（选定）** | 平衡灵活性和认知负担 | 需要设计合理的分组 |

选定方案：按用户意图分成少量 Tool。每个 Tool 内部可能编排多个 SDK 调用，但 Agent 只需表达意图。

### 3.3 其他折衷

| 决策 | 选择 | 理由 |
|------|------|------|
| SDK 参数风格 | 扁平化 | `primary_keys=["id"]` 优于 `ResourceInfo(type=..., id=...)` |
| 同步/异步 | 先同步 | 当前用例不需异步，后续按需加 |
| SDK 模块作为独立积木 | 是 | 未来"从文档构建"等新 Skill 可复用 `knowledge_networks`、`object_types` 等模块 |

---

## 4 架构设计

### 4.1 逻辑分层

```
Agent
 │ 自然语言
 ▼
┌──────────────────────────────────────────────────────────────────┐
│  Skill 层 — 对外 Tool 定义                                       │
│                                                                  │
│  读取类                        写入类           交互类            │
│  ┌────────────────┐ ┌────────┐ ┌──────────┐ ┌────────────────┐  │
│  │load_kn_context │ │query_kn│ │connect_db│ │discover_agents │  │
│  │(Schema+实例)    │ │(查询)   │ │(连接DB)   │ │(列举Agent)     │  │
│  └───────┬────────┘ └───┬────┘ └────┬─────┘ └───────┬────────┘  │
│          │              │           │               │            │
│                        ┌──────────┐ ┌──────────────┐            │
│                        │ build_kn │ │  chat_agent  │            │
│                        │(构建KN)  │ │(Agent 对话)   │            │
│                        └────┬─────┘ └──────┬───────┘            │
│  ┌──────┴───────────────────┴──────────────┴─────────────────┐  │
│  │  未来:  import_docs │ execute_action │ ...                 │  │
│  └───────────────────────────────────────────────────────────┘  │
└──────────────────────────────┬───────────────────────────────────┘
                               │ Python 调用
┌──────────────────────────────▼───────────────────────────────────┐
│  SDK 层 — 内部模块（可独立使用，也被 Skill 编排）                   │
│                                                                  │
│  datasources │ dataviews │ knowledge_networks                    │
│  object_types │ relation_types │ query                           │
│  agents │ conversations                        ← v0.4 新增       │
│  concept_groups │ action_types (预留)                             │
└──────────────────────────────┬───────────────────────────────────┘
                               │ HTTP
┌──────────────────────────────▼───────────────────────────────────┐
│  HTTP 层 — httpx + AuthProvider                                  │
│  data-connection │ mdl-data-model │ ontology-mgr                 │
│  ontology-query │ agent-retrieval │ decision-agent               │
└──────────────────────────────────────────────────────────────────┘
```

### 4.2 核心流程：从数据库构建知识网络

```
用户: "把 10.0.1.100 的 ERP 库接进来"
 │
 ├─ Skill: connect_db ──────────────────────────────────────
 │   │  SDK: datasources.test() → datasources.create()
 │   │  SDK: datasources.list_tables()
 │   └─ 返回: datasource_id, 可用表列表
 │
 ├─ Skill: build_kn ────────────────────────────────────────
 │   │  SDK: dataviews.create()          ← 每张目标表
 │   │  SDK: knowledge_networks.create()
 │   │  SDK: object_types.create()       ← 每个视图
 │   │  SDK: relation_types.create()     ← 每对关联
 │   │  SDK: knowledge_networks.build().wait()
 │   └─ 返回: kn_id, 对象类/关系类摘要
 │
 └─ Skill: query_kn ────────────────────────────────────────
     │  SDK: query.semantic_search() / query.instances() / query.subgraph()
     └─ 返回: 查询结果
```

### 4.3 核心流程：Context Loader（Schema 与对象查询）

```
用户/Agent: "这个知识网络里有什么？"
 │
 ├─ Skill: load_kn_context ────────────────────────────
 │   │  SDK: knowledge_networks.list()  ← 发现可用知识网络
 │   │  SDK: knowledge_networks.get(id)
 │   │  SDK: object_types.list(kn_id)   ← 获取全部对象类及属性
 │   │  SDK: relation_types.list(kn_id) ← 获取全部关系类
 │   └─ 返回: 完整 Schema 结构（对象类、关系类、属性、索引配置）
 │
 └─ Skill: load_kn_context (mode=instances) ───────────
     │  SDK: object_types.list(kn_id)   ← 定位目标对象类
     │  SDK: query.instances(kn_id, ot_id, condition?, limit?)
     └─ 返回: 对象实例列表 + Schema 上下文
```

**与 query_kn 的区别：**

| | load_kn_context | query_kn |
|---|---|---|
| **目的** | 发现和理解结构，为后续操作提供上下文 | 回答具体的业务问题 |
| **典型调用者** | Agent 的规划/推理阶段 | Agent 的执行阶段 |
| **输入** | 知识网络名称/ID，可选对象类名 | 知识网络 ID + 具体查询意图 |
| **输出** | Schema 结构 + 样本数据 | 查询结果 + 摘要 |

**闭环示意：**

```
    构建（写入）              探索（读取）              查询（使用）
  ┌────────────┐         ┌──────────────────┐      ┌────────────┐
  │ connect_db │───────▶ │ load_kn_context  │────▶ │  query_kn  │
  │ build_kn   │         │  (schema+对象)    │      │ (业务查询)  │
  └────────────┘         └──────────────────┘      └────────────┘
       ▲                         │                        │
       │                         │ "缺少关系/字段"         │
       └─────────────────────────┘                        │
              反馈驱动增量构建                               ▼
                                                     业务决策/行动
```

### 4.4 核心流程：Decision Agent 列举与对话

```
用户/Agent: "有哪些可用的 Agent？"
 │
 ├─ Skill: discover_agents ──────────────────────────
 │   │  SDK: agents.list()        ← 列举平台上的 Decision Agent
 │   │  SDK: agents.get(id)       ← 获取 Agent 详情（绑定的 KN、提示词等）
 │   └─ 返回: Agent 列表及能力概要
 │
 └─ Skill: chat_agent ───────────────────────────────
     │  SDK: conversations.create(agent_id)  ← 创建会话
     │  SDK: conversations.send_message(conversation_id, content)
     │  SDK: conversations.list_messages(conversation_id)
     └─ 返回: Agent 回复内容（支持流式）
```

**与 query_kn 的区别：**

| | query_kn | chat_agent |
|---|---|---|
| **交互对象** | 直接查询知识网络 | 通过 Decision Agent 间接查询 |
| **输入** | 结构化查询参数（对象类、条件、路径） | 自然语言问题 |
| **智能程度** | SDK 侧无推理，精确匹配 | Agent 侧做意图理解、多轮推理 |
| **适用场景** | 确切知道要查什么 | 探索性问题、复杂推理、多步决策 |

**完整价值链：**

```
  构建（写入）        探索（读取）         查询（使用）         Agent 对话（交互）
┌────────────┐    ┌──────────────┐    ┌────────────┐    ┌────────────────┐
│ connect_db │──▶ │load_kn_context│──▶│  query_kn  │    │discover_agents │
│ build_kn   │    │ (schema+对象) │    │ (精确查询)  │    │  chat_agent    │
└────────────┘    └──────────────┘    └────────────┘    │ (自然语言对话)  │
                                                        └────────────────┘
                  知识网络 ────────────────────────────────▶ Decision Agent
                  （数据基座）                                （智能入口）
```

### 4.5 扩展示例：从文档构建（未来）

```
用户: "把 /docs/api-spec.pdf 导入知识网络"
 │
 ├─ Skill: import_docs ─────────────────────────────────────
 │   │  读取文件 → 解析结构 → 调用与 build_kn 相同的 SDK 模块
 │   │  SDK: knowledge_networks.create()
 │   │  SDK: object_types.create()   ← 从文档结构推断
 │   │  SDK: relation_types.create() ← 从文档语义推断
 │   └─ 复用 SDK 模块，只是数据来源不同
```

SDK 模块是积木，Skill 是积木的不同组合方式。新增 Skill 不需要改 SDK。

---

## 5 Skill 对外接口

Agent 看到的全部 Tool 定义。这是整个系统的**对外 API 边界**。

Skill 按职责分为三类：

| 类别 | Skill | 职责 |
|------|-------|------|
| **读取类** — 探索与查询 | `load_kn_context`  | 发现 KN、浏览 Schema、查看实例 |
|                        | `query_kn`          | 语义搜索、精确查询、子图关联 |
|                        | `discover_agents`   | 列举 Decision Agent、查看能力概要 |
| **写入类** — 接入与构建 | `connect_db`        | 连接数据库、探索表结构 |
|                        | `build_kn`          | 建模、索引、构建知识网络 |
| **交互类** — Agent 对话 | `chat_agent`        | 与 Decision Agent 多轮对话 |

读取类 Skill 不产生副作用，可安全重复调用；写入类 Skill 会变更 ADP 状态；交互类 Skill 会创建会话并产生对话记录。

### 5.1 读取类 Skill — 探索与查询

#### 5.1.1 load_kn_context — 知识网络 Context Loader

```yaml
name: load_kn_context
description: |
  查询知识网络的 Schema 结构和对象实例。支持三种模式：
  - schema: 返回知识网络的完整结构（对象类、关系类、属性定义）
  - instances: 返回指定对象类的实例数据
  - overview: 返回知识网络列表及摘要信息
  用于 Agent 在规划阶段了解可用数据，为后续的 query_kn 或 build_kn 提供上下文。
parameters:
  type: object
  required: [mode]
  properties:
    mode:
      type: string
      enum: [overview, schema, instances]
      description: "查询模式"
    # overview 模式
    keyword:
      type: string
      description: "按名称过滤知识网络（overview 模式）"
    # schema 模式
    kn_id:
      type: string
      description: "知识网络 ID（schema/instances 模式必填）"
    kn_name:
      type: string
      description: "知识网络名称，可替代 kn_id（SDK 内部按名称查找）"
    include_properties:
      type: boolean
      default: true
      description: "是否返回每个对象类的属性详情（schema 模式）"
    include_samples:
      type: boolean
      default: false
      description: "是否为每个对象类返回少量样本数据（schema 模式）"
    sample_size:
      type: integer
      default: 3
      description: "每个对象类的样本数量（include_samples=true 时生效）"
    # instances 模式
    object_type:
      type: string
      description: "对象类名称或 ID（instances 模式必填）"
    conditions:
      type: object
      description: "过滤条件 {field, op, value}"
    limit:
      type: integer
      default: 20
    include_type_info:
      type: boolean
      default: true
      description: "是否在返回中附带对象类的 Schema 信息"
returns:
  # overview 模式
  knowledge_networks:
    - id: string
      name: string
      object_type_count: integer
      relation_type_count: integer
  # schema 模式
  kn_id: string
  kn_name: string
  object_types:
    - id: string
      name: string
      primary_keys: [string]
      display_key: string
      properties: [{ name: string, type: string, indexed: boolean, fulltext: boolean, vector: boolean }]
      sample_data: [object]       # include_samples=true 时
  relation_types:
    - id: string
      name: string
      source: string              # 源对象类名称
      target: string              # 目标对象类名称
      mapping_type: string
  # instances 模式
  object_type_schema:             # include_type_info=true 时
    name: string
    properties: [{ name: string, type: string }]
  data: array
  total_count: integer
  has_more: boolean
```

**内部编排：**

**overview 模式：**
1. `knowledge_networks.list(name=keyword)` — 获取知识网络列表
2. 对每个 KN 提取 `statistics` 中的计数信息

**schema 模式：**
1. 解析 `kn_id` 或 `kn_name`（若传名称，先 `knowledge_networks.list(name=kn_name)` 查找）
2. `object_types.list(kn_id)` — 获取全部对象类及属性
3. `relation_types.list(kn_id)` — 获取全部关系类
4. （可选）`query.instances(kn_id, ot_id, limit=sample_size)` × N — 为每个对象类拉取样本

**instances 模式：**
1. 解析 `object_type`（若传名称，先 `object_types.list(kn_id)` 查找对应 ID）
2. `query.instances(kn_id, ot_id, condition?, limit?)` — 查询实例
3. （可选）附带对象类 Schema 信息

#### 5.1.2 query_kn — 查询知识网络

```yaml
name: query_kn
description: |
  查询知识网络中的数据。支持三种模式：
  - search: 语义搜索，不确定查什么时用
  - instances: 精确查询某类对象的实例
  - subgraph: 沿关系路径做关联查询
parameters:
  type: object
  required: [kn_id, mode]
  properties:
    kn_id: { type: string }
    mode:  { type: string, enum: [search, instances, subgraph] }
    # search 模式
    query: { type: string, description: "自然语言查询" }
    # instances 模式
    object_type: { type: string, description: "对象类名称或 ID" }
    conditions:  { type: object, description: "过滤条件 {field, op, value}" }
    limit:       { type: integer, default: 20 }
    # subgraph 模式
    start_object: { type: string, description: "起点对象类" }
    start_condition: { type: object }
    path: { type: array, items: { type: string }, description: "关系路径，如 [产品, 库存]" }
returns:
  data: array    # 查询结果
  summary: string  # 结果摘要
```

**内部编排：** 根据 `mode` 分别调用 `query.semantic_search()` / `query.instances()` / `query.subgraph()`

#### 5.1.3 discover_agents — 发现 Decision Agent

```yaml
name: discover_agents
description: |
  列举平台上可用的 Decision Agent，查看其能力和关联的知识网络。
  支持两种模式：
  - list: 列举所有可用 Agent
  - detail: 查看指定 Agent 的详细信息（绑定的知识网络、能力描述、配置摘要）
parameters:
  type: object
  required: [mode]
  properties:
    mode:
      type: string
      enum: [list, detail]
      description: "查询模式"
    # list 模式
    keyword:
      type: string
      description: "按名称过滤 Agent"
    status:
      type: string
      enum: [published, draft, all]
      default: published
      description: "Agent 状态过滤"
    # detail 模式
    agent_id:
      type: string
      description: "Agent ID（detail 模式必填）"
    agent_name:
      type: string
      description: "Agent 名称，可替代 agent_id（SDK 内部按名称查找）"
returns:
  # list 模式
  agents:
    - id: string
      name: string
      description: string
      status: string                # published / draft
      knowledge_networks: [string]  # 关联的 KN 名称列表
  # detail 模式
  agent:
    id: string
    name: string
    description: string
    status: string
    knowledge_networks:
      - id: string
        name: string
    prompts:                        # Agent 的提示词配置摘要
      system_prompt_preview: string # 截取前 200 字
    capabilities: [string]          # 支持的能力标签，如 ["知识问答", "数据查询"]
    conversation_count: integer     # 历史会话数量
```

**内部编排：**

**list 模式：**
1. `agents.list(keyword?, status?)` — 列举 Agent
2. 对每个 Agent 提取关联 KN 名称

**detail 模式：**
1. 解析 `agent_id` 或 `agent_name`
2. `agents.get(id)` — 获取 Agent 详情
3. 提取关联 KN、提示词摘要、能力标签

### 5.2 写入类 Skill — 接入与构建

#### 5.2.1 connect_db — 连接数据源

```yaml
name: connect_db
description: |
  连接一个数据库，验证连通性，返回可用的表和字段信息。
  不会创建知识网络，仅建立连接并探索结构。
parameters:
  type: object
  required: [db_type, host, port, database, account, password]
  properties:
    db_type:
      type: string
      enum: [mysql, maria, oracle, postgresql, sqlserver, doris, hive,
             clickhouse, mongodb, dameng, gaussdb, hologres, opengauss]
      description: "数据库类型"
    host:       { type: string }
    port:       { type: integer }
    database:   { type: string }
    account:    { type: string }
    password:   { type: string }
    schema:     { type: string, description: "Schema 名称（PostgreSQL/Oracle 等需要）" }
returns:
  datasource_id: string
  tables:
    - name: string
      columns: [{ name: string, type: string, comment: string }]
```

**内部编排：** `datasources.test()` → `datasources.create()` → `datasources.list_tables()`

#### 5.2.2 build_kn — 构建知识网络

```yaml
name: build_kn
description: |
  从已连接的数据源构建知识网络。选择要纳入的表，定义对象间关系，
  自动完成数据视图创建、对象类建模、关系建模和索引构建。
parameters:
  type: object
  required: [datasource_id]
  properties:
    datasource_id: { type: string, description: "connect_db 返回的 ID" }
    network_name:  { type: string }
    tables:
      type: array
      items: { type: string }
      description: "要纳入的表名。为空则纳入全部。"
    relations:
      type: array
      items:
        type: object
        required: [name, from_table, to_table, from_field, to_field]
        properties:
          name:       { type: string }
          from_table: { type: string }
          to_table:   { type: string }
          from_field: { type: string }
          to_field:   { type: string }
      description: "关系定义。必须显式指定，不做自动推断。"
returns:
  kn_id: string
  kn_name: string
  object_types: [{ name: string, id: string, field_count: integer }]
  relation_types: [{ name: string, from: string, to: string }]
  status: ready | failed
```

**内部编排：**

1. `datasources.list_tables(datasource_id)` — 获取表结构
2. `dataviews.create()` × N — 每张目标表创建数据视图
3. `knowledge_networks.create()` — 创建知识网络
4. `object_types.create()` × N — 每个视图创建对象类（Skill 自动选取主键和显示键）
5. `relation_types.create()` × M — 根据 `relations` 参数创建关系（Skill 内部维护 表名→OT ID 的映射）
6. `knowledge_networks.build().wait()` — 触发索引构建并等待完成

### 5.3 交互类 Skill — Agent 对话

#### 5.3.1 chat_agent — 与 Decision Agent 对话

```yaml
name: chat_agent
description: |
  与平台上的 Decision Agent 进行多轮对话。支持三种模式：
  - ask: 向 Agent 发送一条消息并获取回复（最常用）
  - history: 查看指定会话的历史消息
  - sessions: 列举与某个 Agent 的历史会话
parameters:
  type: object
  required: [mode]
  properties:
    mode:
      type: string
      enum: [ask, history, sessions]
      description: "操作模式"
    # ask 模式
    agent_id:
      type: string
      description: "目标 Agent ID（ask 模式必填，除非提供 agent_name）"
    agent_name:
      type: string
      description: "目标 Agent 名称，可替代 agent_id"
    question:
      type: string
      description: "用户问题（ask 模式必填）"
    conversation_id:
      type: string
      description: "会话 ID。为空则自动创建新会话，传入则续接已有会话"
    stream:
      type: boolean
      default: false
      description: "是否流式返回（逐 token 输出）"
    # history 模式
    # conversation_id: 同上（history 模式必填）
    limit:
      type: integer
      default: 50
      description: "返回的消息数量上限"
    # sessions 模式
    # agent_id / agent_name: 同上
returns:
  # ask 模式
  answer: string              # Agent 的回复内容
  conversation_id: string     # 会话 ID（续接或新建的）
  references:                 # Agent 引用的知识来源
    - source: string          # 来源对象类 / 文档名
      content: string         # 引用片段
      score: float            # 相关度
  # history 模式
  messages:
    - role: string            # user / assistant
      content: string
      timestamp: string
  # sessions 模式
  conversations:
    - id: string
      title: string
      message_count: integer
      last_active: string     # ISO 时间戳
      preview: string         # 最后一条消息摘要
```

**内部编排：**

**ask 模式：**
1. 解析 `agent_id` 或 `agent_name`（若传名称，先 `agents.list(keyword=agent_name)` 查找）
2. 若无 `conversation_id`，调用 `conversations.create(agent_id)` 创建新会话
3. `conversations.send_message(conversation_id, content, stream?)` — 发送消息并获取回复
4. 提取回复内容、引用来源

**history 模式：**
1. `conversations.list_messages(conversation_id, limit?)` — 获取历史消息

**sessions 模式：**
1. 解析 `agent_id`
2. `conversations.list(agent_id?)` — 获取会话列表

### 5.4 对话示例

**场景 1: 从数据库构建知识网络（写入路径）**

```
用户: 帮我连上 10.0.1.100 的 MySQL 库 erp_prod，账号 readonly

Agent: [调用 connect_db]
       → 连接成功，发现 12 张表:
         products (8 字段), inventory (6 字段), suppliers (5 字段), ...
         需要把哪些表纳入知识网络？

用户: products、inventory、suppliers 三张表，产品和库存通过 material_number 关联

Agent: [调用 build_kn]
       → 已创建知识网络「erp_prod」:
         - 产品 (8 字段), 库存 (6 字段), 供应商 (5 字段)
         - 关系: 产品→库存 (material_number = material_code)
         索引构建完成，可以查询了。
```

**场景 2: Context Loader 探索与查询（读取路径）**

```
用户: 系统里有哪些知识网络？

Agent: [调用 load_kn_context, mode=overview]
       → 找到 3 个知识网络:
         1. erp_prod — 3 个对象类, 1 个关系类
         2. crm_contacts — 5 个对象类, 4 个关系类
         3. supply_chain — 8 个对象类, 12 个关系类

用户: erp_prod 里面有哪些数据结构？

Agent: [调用 load_kn_context, mode=schema, kn_name="erp_prod", include_samples=true]
       → 知识网络「erp_prod」的结构:
         对象类:
           - 产品 (主键: material_number, 8 个属性: material_number, product_name, category, ...)
             样本: [{material_number: "746-000031", product_name: "轴承组件A", ...}, ...]
           - 库存 (主键: seq, 6 个属性: seq, material_code, warehouse, quantity, ...)
           - 供应商 (主键: supplier_id, 5 个属性: ...)
         关系类:
           - 产品→库存 (通过 material_number = material_code)

用户: 看看库存表里有哪些数据

Agent: [调用 load_kn_context, mode=instances, kn_name="erp_prod", object_type="库存", limit=10]
       → 库存 (共 1,523 条记录，显示前 10 条):
         | seq | material_code | warehouse | quantity | update_time |
         | 1   | 746-000031    | 华东仓     | 1200     | 2026-03-10  |
         | 2   | 746-000031    | 华南仓     | 800      | 2026-03-10  |
         | ... |

用户: 产品 746-000031 的库存情况

Agent: [调用 query_kn, mode=subgraph]  ← 已经了解 Schema，直接精确查询
       → 产品 746-000031 在 3 个仓库有库存:
         华东仓: 1200件, 华南仓: 800件, 华北仓: 350件
```

**场景 3: 闭环 — 探索发现问题后驱动增量构建（读→写协作）**

```
用户: 我想查产品的供应商信息

Agent: [调用 load_kn_context, mode=schema, kn_name="erp_prod"]
       → 当前 erp_prod 中有「产品」和「供应商」对象类，
         但它们之间没有定义关系。需要先建立关联。
         产品表有 supplier_id 字段，供应商表主键也是 supplier_id，
         要我建立这个关系吗？

用户: 是的，帮我建上

Agent: [调用 build_kn, 增量添加关系]
       → 已添加关系: 产品→供应商 (supplier_id = supplier_id)
         重建索引完成。现在可以查产品的供应商了。
```

**场景 4: 发现并选择 Decision Agent（交互路径入口）**

```
用户: 有哪些可用的 Agent？

Agent: [调用 discover_agents, mode=list]
       → 平台上有 3 个已发布的 Decision Agent:
         1. 供应链助手 — 绑定知识网络: HD供应链业务知识网络_v3
            "产品供应分析、库存查询、BOM 展开"
         2. HR 问答 — 绑定知识网络: hr_policy
            "人事制度、考勤政策、薪酬标准"
         3. 客服质检 — 绑定知识网络: service_qa
            "客服对话分析、质检评分"

用户: 供应链助手具体能做什么？

Agent: [调用 discover_agents, mode=detail, agent_name="供应链助手"]
       → 供应链助手:
         - 状态: 已发布
         - 关联知识网络: HD供应链业务知识网络_v3 (8 个对象类, 12 个关系类)
         - 能力: 知识问答, 数据查询, 供应分析
         - 系统提示词: "你是一个供应链领域的专家助手，基于企业知识网络回答..."
         - 历史会话: 42 次
```

**场景 5: 与 Decision Agent 多轮对话**

```
用户: 帮我问一下供应链助手，物料 746-000031 的供应情况

Agent: [调用 chat_agent, mode=ask, agent_name="供应链助手",
        question="物料 746-000031 的供应情况如何？"]
       → 供应链助手回复:
         物料 746-000031（轴承组件A）的供应情况如下:
         - 当前库存: 华东仓 1200件, 华南仓 800件, 华北仓 350件
         - 主供应商: 精密轴承有限公司（供应商ID: SUP-0042）
         - 最近采购: 2026-03-05, 2000件
         [引用: 产品BOM, 库存表, 采购订单]
         (会话 ID: conv_a1b2c3)

用户: 这个物料最近有质量问题吗？

Agent: [调用 chat_agent, mode=ask, agent_name="供应链助手",
        question="这个物料最近有质量问题吗？",
        conversation_id="conv_a1b2c3"]  ← 续接上一轮会话
       → 供应链助手回复:
         根据质检记录，物料 746-000031 近 30 天内有 2 次质量异常:
         - 2026-03-01: 华东仓入库批次，表面划痕超标，退货 50 件
         - 2026-02-18: 华南仓入库批次，尺寸偏差，让步接收
         建议关注供应商精密轴承有限公司的质量趋势。
         [引用: 质检记录, 供应商评价]
```

**场景 6: 查看历史对话记录**

```
用户: 之前跟供应链助手聊过什么？

Agent: [调用 chat_agent, mode=sessions, agent_name="供应链助手"]
       → 与「供应链助手」的历史会话:
         1. conv_a1b2c3 — "物料 746-000031 的供应情况" (2 条消息, 刚刚)
         2. conv_x7y8z9 — "Q1 采购成本分析" (6 条消息, 2026-03-10)
         3. conv_m4n5o6 — "供应商交期对比" (4 条消息, 2026-03-08)

用户: 看看上次采购成本分析的内容

Agent: [调用 chat_agent, mode=history, conversation_id="conv_x7y8z9"]
       → 会话「Q1 采购成本分析」(2026-03-10):
         用户: Q1 各品类的采购成本同比变化？
         助手: 根据采购订单和历史数据分析...
         用户: 哪些品类涨幅超过 10%？
         助手: 以下 3 个品类涨幅超过 10%: ...
         ...
```

### 5.5 未来 Skill 预留

| 类别 | Skill | 触发场景 | 依赖的 SDK 模块 |
|------|-------|---------|----------------|
| 读取 | `compute_metric` | "产品 A 的 BOM 展开" | query.logic_properties |
| 写入 | `import_docs` | "把这份文档导入知识网络" | knowledge_networks, object_types, relation_types + 文档解析 |
| 写入 | `execute_action` | "为物料 X 发起采购订单" | query + **action_types** + 行动执行 |
| 写入 | `manage_kn` | "删除/更新知识网络中的对象类" | knowledge_networks, object_types, relation_types, **concept_groups** |

新增 Skill 只需组合已有 SDK 模块 + 可能新增的模块，不改动已有 Skill 和 SDK。

---

## 6 SDK 内部模块

SDK 是 Skill 的实现基础，也可被开发者直接使用。以下按模块列出接口和关键参数映射。

### 6.1 datasources

对应服务: `data-connection`（dc-datasource）

| 方法 | HTTP | 路径 |
|------|------|------|
| `create(name, type, host, port, database, account, password, schema?, comment?)` | POST | `/api/data-connection/v1/datasource` |
| `test(type, host, port, database, account, password, schema?)` | POST | `/api/data-connection/v1/datasource/test` |
| `list(keyword?, type?)` | GET | `/api/data-connection/v1/datasource` |
| `get(id)` | GET | `/api/data-connection/v1/datasource/{id}` |
| `delete(id)` | DELETE | `/api/data-connection/v1/datasource/{id}` |
| `list_tables(id, keyword?, limit?, offset?)` | GET | `/api/data-connection/v1/metadata/data-source/{id}` |

SDK 扁平参数 → REST 嵌套结构:

```python
# SDK 调用
datasources.create(name="ERP库", type="mysql", host="10.0.1.100", port=3306,
                   database="erp", account="root", password="secret")

# → REST 请求体
{
    "name": "ERP库",
    "type": "mysql",
    "bin_data": {
        "host": "10.0.1.100",
        "port": 3306,
        "database_name": "erp",
        "connect_protocol": "jdbc",
        "account": "root",
        "password": "secret"
    }
}
```

```python
# SDK 调用
datasources.test(type="mysql", host="10.0.1.100", port=3306,
                 database="erp", account="root", password="secret")

# → REST 请求体
{
    "type": "mysql",
    "bin_data": {
        "host": "10.0.1.100",
        "port": 3306,
        "database_name": "erp",
        "connect_protocol": "jdbc",
        "account": "root",
        "password": "secret"
    }
}
```

**`connect_protocol` 推断规则：** SDK 根据 `type` 自动设置 `connect_protocol`。大多数数据库为 `"jdbc"`，`maxcompute` / `anyshare7` / `opensearch` 等为 `"https"`。

**支持的数据源类型：** `mysql`, `maria`, `oracle`, `postgresql`, `sqlserver`, `doris`, `hive`, `clickhouse`, `mongodb`, `dameng`, `gaussdb`, `hologres`, `opengauss`, `inceptor-jdbc`, `maxcompute`, `excel`, `anyshare7`, `tingyun`, `opensearch`

### 6.2 dataviews

对应服务: VEGA `mdl-data-model`

| 方法 | HTTP | 路径 |
|------|------|------|
| `create(name, datasource_id, table?, sql?, fields?)` | POST | `/api/mdl-data-model/v1/data-views` |
| `list(datasource_id?, name?, type?)` | GET | `/api/mdl-data-model/v1/data-views` |
| `get(id)` | GET | `/api/mdl-data-model/v1/data-views/{id}` |
| `delete(id)` | DELETE | `/api/mdl-data-model/v1/data-views/{id}` |

两种模式: `table="products"` (整表映射) 或 `sql="SELECT ..."` (自定义 SQL)。

SDK 内部转换为 `data_scope` + `query_type` 结构：

```python
# SDK 调用 — 整表映射
dataviews.create(name="products", datasource_id="ds_01", table="products")

# → REST 请求体
[{
    "name": "products",
    "type": "atomic",
    "query_type": "SQL",
    "data_source_id": "ds_01",
    "data_scope": [{
        "id": "node_0",
        "title": "products",
        "type": "source",
        "config": {"table": "products"},
        "input_nodes": [],
        "output_fields": []    # 自动从表结构继承
    }],
    "fields": []               # 自动从表结构继承
}]

# SDK 调用 — 自定义 SQL
dataviews.create(name="custom_view", datasource_id="ds_01",
                 sql="SELECT id, name FROM products WHERE status = 'active'")

# → REST 请求体
[{
    "name": "custom_view",
    "type": "custom",
    "query_type": "SQL",
    "data_source_id": "ds_01",
    "data_scope": [{
        "id": "node_0",
        "title": "custom_view",
        "type": "sql",
        "config": {"sql": "SELECT id, name FROM products WHERE status = 'active'"},
        "input_nodes": [],
        "output_fields": []
    }],
    "fields": []
}]
```

> **注意：** REST API 接受的是数组（支持批量创建），SDK 的 `create()` 单次创建一个视图，内部包装为单元素数组。

### 6.3 knowledge_networks

对应服务: `ontology-manager` + `agent-retrieval`

| 方法 | HTTP | 路径 |
|------|------|------|
| `create(name, description?, tags?)` | POST | `/api/ontology-manager/v1/knowledge-networks` |
| `list(name?)` | GET | `/api/ontology-manager/v1/knowledge-networks` |
| `get(id)` | GET | `/api/ontology-manager/v1/knowledge-networks/{id}` |
| `update(id, ...)` | PUT | `/api/ontology-manager/v1/knowledge-networks/{id}` |
| `delete(id)` | DELETE | `/api/ontology-manager/v1/knowledge-networks/{id}` |
| `build(id)` | POST | `/api/agent-retrieval/in/v1/kn/full_build_ontology` |
| `build_status(id)` | GET | `/api/agent-retrieval/in/v1/kn/full_ontology_building_status?kn_id={id}` |

**Build 机制：**

```python
# 触发构建
job = client.knowledge_networks.build(kn_id)

# → REST 请求体
{"kn_id": "kn_01"}

# → 返回 BuildJob 对象
```

`build()` 返回 `BuildJob`，支持 `.wait(timeout=300)` 阻塞等待和 `.poll()` 轮询。

**状态查询使用 `kn_id`（非 job_id）：** `GET .../full_ontology_building_status?kn_id=kn_01`，返回该知识网络最近构建任务的整体状态。

状态值: `running` → `completed | failed`。

### 6.4 object_types

对应服务: `ontology-manager`。路径前缀: `/api/ontology-manager/v1`

| 方法 | HTTP | 路径 |
|------|------|------|
| `create(kn_id, name, dataview_id, primary_keys, display_key, properties?)` | POST | `.../knowledge-networks/{kn_id}/object-types` |
| `list(kn_id)` | GET | `.../knowledge-networks/{kn_id}/object-types` |
| `get(kn_id, ot_id)` | GET | `.../knowledge-networks/{kn_id}/object-types/{ot_id}` |
| `update(kn_id, ot_id, ...)` | PUT | `.../knowledge-networks/{kn_id}/object-types/{ot_id}` |
| `delete(kn_id, ot_ids)` | DELETE | `.../knowledge-networks/{kn_id}/object-types/{ot_ids}` |

**核心参数映射：**

```python
# SDK 调用
client.object_types.create(
    kn_id="kn_01",
    name="产品",
    dataview_id="dv_01",
    primary_keys=["material_number"],       # 注意：数组，支持复合主键
    display_key="product_name",
    properties=[
        Property(name="material_number", indexed=True),
        Property(name="product_name", fulltext=True, vector=True),
    ],
)

# → REST 请求体
{
    "entries": [{
        "name": "产品",
        "data_source": {
            "type": "data_view",
            "id": "dv_01"
        },
        "primary_keys": ["material_number"],
        "display_key": "product_name",
        "data_properties": [
            {
                "name": "material_number",
                "display_name": "material_number",
                "index_config": {
                    "keyword_config": {"enabled": true},
                    "fulltext_config": {"enabled": false},
                    "vector_config": {"enabled": false}
                }
            },
            {
                "name": "product_name",
                "display_name": "product_name",
                "index_config": {
                    "keyword_config": {"enabled": false},
                    "fulltext_config": {"enabled": true},
                    "vector_config": {"enabled": true}
                }
            }
        ]
    }]
}
```

**SDK 便捷接口：** 同时支持 `primary_keys=["id"]`（规范形式）和 `primary_key="id"`（单主键快捷方式，内部转为数组）。`properties` 不传时自动从 DataView 继承全部字段。

**主键类型约束：** `primary_keys` 中的字段类型必须为 `integer`、`unsigned integer` 或 `string`。

> **注意：** REST API 通过 `entries` 数组支持批量创建。SDK 的 `create()` 单次创建一个对象类，内部包装为单元素数组并返回第一个结果。

### 6.5 relation_types

对应服务: `ontology-manager`。路径前缀同上。

| 方法 | HTTP | 路径 |
|------|------|------|
| `create(kn_id, name, source_ot_id, target_ot_id, ...)` | POST | `.../knowledge-networks/{kn_id}/relation-types` |
| `list(kn_id)` | GET | `.../knowledge-networks/{kn_id}/relation-types` |
| `get(kn_id, rt_id)` | GET | `.../knowledge-networks/{kn_id}/relation-types/{rt_id}` |
| `update(kn_id, rt_id, ...)` | PUT | `.../knowledge-networks/{kn_id}/relation-types/{rt_id}` |
| `delete(kn_id, rt_ids)` | DELETE | `.../knowledge-networks/{kn_id}/relation-types/{rt_ids}` |

**两种映射模式：**

**模式 1: 直接映射 (`direct`)** — 源对象和目标对象的属性直接关联：

```python
# SDK 调用
client.relation_types.create(
    kn_id="kn_01",
    name="产品_库存",
    source_ot_id="ot_products",
    target_ot_id="ot_inventory",
    mappings=[("material_number", "material_code")],   # [(源属性, 目标属性)]
)

# → REST 请求体
{
    "entries": [{
        "name": "产品_库存",
        "source_object_type_id": "ot_products",
        "target_object_type_id": "ot_inventory",
        "type": "direct",
        "mapping_rules": [
            {
                "source_property": {"name": "material_number"},
                "target_property": {"name": "material_code"}
            }
        ]
    }]
}
```

**模式 2: 视图映射 (`data_view`)** — 通过中间数据视图关联：

```python
# SDK 调用
client.relation_types.create(
    kn_id="kn_01",
    name="产品_供应商",
    source_ot_id="ot_products",
    target_ot_id="ot_suppliers",
    mapping_view_id="dv_product_supplier",
    source_mappings=[("product_id", "prod_id")],    # [(对象属性, 视图字段)]
    target_mappings=[("supplier_id", "sup_id")],    # [(对象属性, 视图字段)]
)

# → REST 请求体
{
    "entries": [{
        "name": "产品_供应商",
        "source_object_type_id": "ot_products",
        "target_object_type_id": "ot_suppliers",
        "type": "data_view",
        "mapping_rules": {
            "backing_data_source": {
                "type": "data_view",
                "id": "dv_product_supplier"
            },
            "source_mapping_rules": [
                {
                    "source_property": {"name": "product_id"},
                    "target_property": {"name": "prod_id"}
                }
            ],
            "target_mapping_rules": [
                {
                    "source_property": {"name": "supplier_id"},
                    "target_property": {"name": "sup_id"}
                }
            ]
        }
    }]
}
```

SDK 根据是否传 `mapping_view_id` 自动选择映射模式。

### 6.6 query

对应服务: `agent-retrieval`（语义搜索）+ `ontology-query`（实例查询）

| 方法 | HTTP | 路径 | 服务 |
|------|------|------|------|
| `semantic_search(kn_id, query, mode?, max_concepts?)` | POST | `/api/agent-retrieval/v1/kn/semantic-search` | agent-retrieval |
| `kn_search(kn_id, query, only_schema?)` | POST | `/api/agent-retrieval/in/v1/kn/kn_search` | agent-retrieval |
| `instances(kn_id, ot_id, condition?, limit?)` | POST | `/api/ontology-query/v1/knowledge-networks/{kn_id}/object-types/{ot_id}` | ontology-query |
| `subgraph(kn_id, paths)` | POST | `/api/agent-retrieval/in/v1/kn/query_instance_subgraph` | agent-retrieval |

**语义搜索：**

```python
# SDK 调用
result = client.query.semantic_search(
    kn_id="kn_01",
    query="哪些产品库存不足",
    mode="keyword_vector_retrieval",    # 默认值
    max_concepts=10,                    # 默认值
)

# → REST 请求体
{
    "kn_id": "kn_01",
    "query": "哪些产品库存不足",
    "mode": "keyword_vector_retrieval",
    "rerank_action": "default",
    "max_concepts": 10,
    "return_query_understanding": false
}
```

语义搜索支持三种模式: `keyword_vector_retrieval`（关键词+向量检索）、`agent_intent_planning`（意图规划）、`agent_intent_retrieval`（意图检索）。

**实例查询：**

```python
# SDK 调用
result = client.query.instances(kn_id="kn_01", ot_id="ot_products",
                                condition=Condition(field="status", operation="==", value="active"),
                                limit=20)

# → REST 请求
# POST /api/ontology-query/v1/knowledge-networks/kn_01/object-types/ot_products
# Header: X-HTTP-Method-Override: GET
{
    "condition": {"field": "status", "operation": "==", "value": "active", "value_from": "const"},
    "limit": 20,
    "need_total": true
}
```

> **分页机制：** 实例查询使用 search_after 游标分页（基于 OpenSearch）。SDK 封装为迭代器接口：
>
> ```python
> # 自动分页遍历
> for batch in client.query.instances_iter(kn_id, ot_id, limit=100):
>     for item in batch.data:
>         process(item)
>
> # 手动翻页
> page1 = client.query.instances(kn_id, ot_id, limit=20)
> page2 = client.query.instances(kn_id, ot_id, limit=20, search_after=page1.search_after)
> ```

查询条件 `Condition` 支持递归组合: `{field, operation, value}` 或 `{operation: "and"/"or", sub_conditions: [...]}`.

支持的操作符: `==`, `!=`, `<`, `>`, `<=`, `>=`, `in`, `range`, `like` 等。

### 6.7 concept_groups（预留）

对应服务: `ontology-manager`。用于组织对象类/关系类的分组。v0.1 暂不实现，但 SDK 模块结构中预留位置。

| 方法 | HTTP | 路径 |
|------|------|------|
| `create(kn_id, name)` | POST | `.../knowledge-networks/{kn_id}/concept-groups` |
| `list(kn_id)` | GET | `.../knowledge-networks/{kn_id}/concept-groups` |
| `add_object_types(kn_id, cg_id, ot_ids)` | POST | `.../concept-groups/{cg_id}/object-types` |

语义搜索的 `search_scope.concept_groups` 参数依赖此模块。

### 6.8 action_types（预留）

对应服务: `ontology-manager`。用于定义可执行的业务操作（如发起采购订单）。v0.1 暂不实现。

| 方法 | HTTP | 路径 |
|------|------|------|
| `create(kn_id, name, action_type, object_type_id, action_source, ...)` | POST | `.../knowledge-networks/{kn_id}/action-types` |
| `list(kn_id)` | GET | `.../knowledge-networks/{kn_id}/action-types` |

`execute_action` Skill（§5.5）依赖此模块。

### 6.9 agents

对应服务: `decision-agent`。管理平台上的 Decision Agent。

| 方法 | HTTP | 路径 |
|------|------|------|
| `list(keyword?, status?)` | GET | `/api/decision-agent/v1/agents` |
| `get(id)` | GET | `/api/decision-agent/v1/agents/{id}` |

```python
# SDK 调用
agents = client.agents.list(status="published")
agent = client.agents.get("agent_001")
```

返回类型 `Agent`：

```python
class Agent(BaseModel):
    id: str
    name: str
    description: str | None = None
    status: str                          # published / draft
    kn_ids: list[str] = []               # 关联的知识网络 ID 列表
    system_prompt: str | None = None     # 系统提示词
    capabilities: list[str] = []         # 能力标签
    model_config: dict[str, Any] | None = None  # 模型配置摘要
    conversation_count: int = 0
```

### 6.10 conversations

对应服务: `decision-agent`。管理与 Decision Agent 的会话和消息。

| 方法 | HTTP | 路径 |
|------|------|------|
| `create(agent_id, title?)` | POST | `/api/decision-agent/v1/conversations` |
| `list(agent_id?, limit?)` | GET | `/api/decision-agent/v1/conversations` |
| `get(id)` | GET | `/api/decision-agent/v1/conversations/{id}` |
| `send_message(conversation_id, content, stream?)` | POST | `/api/decision-agent/v1/conversations/{id}/messages` |
| `list_messages(conversation_id, limit?, offset?)` | GET | `/api/decision-agent/v1/conversations/{id}/messages` |
| `delete(id)` | DELETE | `/api/decision-agent/v1/conversations/{id}` |

```python
# SDK 调用 — 创建会话并发送消息
conv = client.conversations.create(agent_id="agent_001")
reply = client.conversations.send_message(conv.id, content="物料 746-000031 的库存情况？")
print(reply.content)   # Agent 的回复
print(reply.references) # 引用的知识来源

# SDK 调用 — 流式输出
for chunk in client.conversations.send_message(conv.id, content="详细分析", stream=True):
    print(chunk.delta, end="")

# SDK 调用 — 查看历史
messages = client.conversations.list_messages(conv.id, limit=20)
```

返回类型：

```python
class Conversation(BaseModel):
    id: str
    agent_id: str
    title: str | None = None
    message_count: int = 0
    last_active: str | None = None       # ISO 时间戳

class Reference(BaseModel):
    source: str                           # 来源对象类 / 文档名
    content: str                          # 引用片段
    score: float = 0.0                    # 相关度

class Message(BaseModel):
    id: str
    role: str                             # user / assistant
    content: str
    references: list[Reference] = []      # assistant 消息可带引用
    timestamp: str

class MessageChunk(BaseModel):
    """流式输出的单个片段。"""
    delta: str                            # 增量文本
    finished: bool = False
    references: list[Reference] = []      # 最后一个 chunk 可带引用
```

---

## 7 API 设计

SDK 的 Python 公共接口规约。面向两类使用者：直接调用 SDK 的开发者，以及基于 SDK 编写新 Skill 的作者。

### 7.1 Client

```python
from kweaver import ADPClient
from kweaver._auth import TokenAuth, OAuth2Auth

# 最简
client = ADPClient(base_url="https://adp.example.com", token="Bearer eyJ...")

# 完整
client = ADPClient(
    base_url="https://adp.example.com",
    auth=OAuth2Auth(client_id="...", client_secret="...", token_endpoint="..."),
    account_id="user-001",
    account_type="user",
    business_domain="domain-001",        # 注入 x-business-domain（算子/执行服务必需）
    timeout=30.0,
)

# Resource 通过属性访问
client.datasources       # DataSourcesResource
client.dataviews          # DataViewsResource
client.knowledge_networks # KnowledgeNetworksResource
client.object_types       # ObjectTypesResource
client.relation_types     # RelationTypesResource
client.query              # QueryResource
client.agents             # AgentsResource          ← v0.4 新增
client.conversations      # ConversationsResource   ← v0.4 新增
```

`ADPClient` 本身是无状态的（不持有业务数据），可以安全地在多线程间共享。

### 7.2 方法签名约定

所有 Resource 方法遵循统一模式：

| 操作 | 方法名 | 返回值 | 说明 |
|------|--------|--------|------|
| 创建 | `create(...)` | 实体对象 | 必填参数为位置参数，可选参数为关键字参数 |
| 列表 | `list(...)` | `list[T]` | 过滤条件均为可选关键字参数 |
| 详情 | `get(id)` | 实体对象 | 不存在时抛 `NotFoundError` |
| 更新 | `update(id, ...)` | 实体对象 | 仅传需要更新的字段 |
| 删除 | `delete(id)` | `None` | 不存在时抛 `NotFoundError` |

```python
# 创建：必填在前，可选在后
client.object_types.create(
    kn_id,                                  # 必填，位置参数
    name="产品",                            # 必填，关键字
    dataview_id=view.id,                    # 必填，关键字
    primary_keys=["material_number"],       # 必填，关键字（数组）
    display_key="product_name",             # 必填，关键字
    properties=None,                        # 可选，不传则自动继承
)

# 单主键快捷方式
client.object_types.create(
    kn_id, name="产品", dataview_id=view.id,
    primary_key="material_number",          # 等价于 primary_keys=["material_number"]
    display_key="product_name",
)

# 列表：全部可选
client.datasources.list()
client.datasources.list(keyword="erp", type="mysql")
```

### 7.3 类型定义

全部使用 Pydantic v2 BaseModel。按职责分三类：

**实体类型** — API 返回的业务对象：

```python
class DataSource(BaseModel):
    id: str
    name: str
    type: str                        # mysql, postgresql, ...
    comment: str | None = None

class DataView(BaseModel):
    id: str
    name: str
    query_type: str                  # SQL, DSL, IndexBase
    fields: list[ViewField]

class ViewField(BaseModel):
    name: str
    type: str
    display_name: str | None = None
    comment: str | None = None

class KnowledgeNetwork(BaseModel):
    id: str
    name: str
    tags: list[str] = []
    comment: str | None = None
    statistics: KNStatistics | None = None

class KNStatistics(BaseModel):
    object_types_total: int = 0
    relation_types_total: int = 0
    action_types_total: int = 0
    concept_groups_total: int = 0

class ObjectType(BaseModel):
    id: str
    name: str
    kn_id: str
    dataview_id: str                 # 从 data_source.id 提取
    primary_keys: list[str]
    display_key: str
    incremental_key: str | None = None
    properties: list[DataProperty]
    status: ObjectTypeStatus | None = None

class DataProperty(BaseModel):
    name: str
    display_name: str | None = None
    type: str                        # varchar, integer, timestamp, ...
    comment: str | None = None
    indexed: bool = False            # 从 index_config.keyword_config 提取
    fulltext: bool = False           # 从 index_config.fulltext_config 提取
    vector: bool = False             # 从 index_config.vector_config 提取

class ObjectTypeStatus(BaseModel):
    index_available: bool = False
    doc_count: int = 0
    storage_size: int = 0
    update_time: int = 0

class RelationType(BaseModel):
    id: str
    name: str
    kn_id: str
    source_ot_id: str
    target_ot_id: str
    mapping_type: str                # direct | data_view
```

**参数类型** — 用户构造后传入 SDK 的结构：

```python
class Property(BaseModel):
    """创建 ObjectType 时指定属性的索引配置。"""
    name: str
    display_name: str | None = None
    type: str | None = None
    indexed: bool = False
    fulltext: bool = False
    vector: bool = False

class Condition(BaseModel):
    """查询过滤条件，支持递归组合。"""
    field: str | None = None
    operation: str               # ==, !=, >, <, <=, >=, like, in, range, and, or
    value: Any = None
    value_from: str = "const"
    sub_conditions: list["Condition"] | None = None

class PathNode(BaseModel):
    id: str                      # 对象类 ID
    condition: Condition | None = None
    limit: int = 100

class PathEdge(BaseModel):
    id: str                      # 关系类 ID
    source: str
    target: str

class SubgraphPath(BaseModel):
    object_types: list[PathNode]
    relation_types: list[PathEdge]
```

**结果类型** — 查询返回的结构：

```python
class SemanticSearchResult(BaseModel):
    """语义搜索结果。"""
    concepts: list[ConceptResult]
    hits_total: int
    query_understanding: dict | None = None

class ConceptResult(BaseModel):
    concept_type: str            # object_type, relation_type, action_type
    concept_id: str
    concept_name: str
    concept_detail: dict | None = None
    intent_score: float = 0.0
    match_score: float = 0.0
    rerank_score: float = 0.0
    samples: list[dict] = []

class KnSearchResult(BaseModel):
    """KN 搜索结果（内部接口）。"""
    object_types: list[dict] | None = None
    relation_types: list[dict] | None = None
    action_types: list[dict] | None = None
    nodes: list[dict] | None = None

class InstanceResult(BaseModel):
    """实例查询结果。"""
    data: list[dict]
    total_count: int | None = None
    search_after: list[Any] | None = None   # 翻页游标
    object_type: dict | None = None         # include_type_info=True 时返回

class SubgraphResult(BaseModel):
    entries: list[dict]

class BuildJob(BaseModel):
    kn_id: str
    def wait(self, timeout: float = 300, poll_interval: float = 2.0) -> "BuildStatus": ...
    def poll(self) -> "BuildStatus": ...

class BuildStatus(BaseModel):
    state: str                   # running | completed | failed
    state_detail: str | None = None
```

### 7.4 错误处理

```python
class ADPError(Exception):
    """所有 SDK 异常的基类。"""
    status_code: int | None      # HTTP 状态码，网络错误时为 None
    error_code: str | None       # ADP 业务错误码
    message: str                 # 人类可读的错误描述
    trace_id: str | None         # 服务端 trace ID，用于跨团队排查

class AuthenticationError(ADPError): ...  # 401
class AuthorizationError(ADPError): ...   # 403
class NotFoundError(ADPError): ...        # 404
class ValidationError(ADPError): ...      # 400
class ConflictError(ADPError): ...        # 409
class ServerError(ADPError): ...          # 5xx
class NetworkError(ADPError): ...         # 网络不可达（避免与内置 ConnectionError 冲突）
```

**Skill 层的错误转换：** Skill 捕获 `ADPError` 后转换为 Agent 可理解的结构化结果，而非直接抛异常。

```python
# Skill 内部
try:
    kn = client.knowledge_networks.create(name=name)
except AuthorizationError:
    return {"error": True, "message": "当前账号无权创建知识网络，请联系管理员"}
except ServerError as e:
    return {"error": True, "message": f"ADP 服务异常 (trace: {e.trace_id})，请稍后重试"}
```

### 7.5 幂等与重试

| 层 | 策略 |
|-----|------|
| HTTP 层 | 对 `5xx` 和网络错误自动重试，最多 3 次，指数退避。`4xx` 不重试。 |
| SDK 层 | 不做额外重试，将错误抛给调用方。 |
| Skill 层 | 对可重试错误（网络、5xx）可选择重试整个步骤，对不可重试错误（400、403）直接返回。 |

`POST` 创建类接口不幂等，SDK 不自动重试。如需幂等，调用方应先 `list()` 检查是否已存在。

---

## 8 安全与认证

### 8.1 认证模型

```
┌─────────┐     ┌─────────┐     ┌───────────┐
│  Agent  │────▶│  Skill  │────▶│ ADPClient │──── Bearer Token ─────▶ ADP 服务
│         │     │         │     │           │──── x-account-id ─────▶
└─────────┘     └─────────┘     └───────────┘──── x-account-type ───▶
                                             ──── x-business-domain ▶
```

SDK 通过 `AuthProvider` 接口管理认证，所有请求自动注入认证 Header。

```python
client = ADPClient(
    base_url="https://adp.example.com",
    auth=TokenAuth("Bearer eyJ..."),        # 最简方式
    account_id="user-001",                  # 注入 x-account-id
    account_type="user",                    # 注入 x-account-type
    business_domain="bd-001",               # 注入 x-business-domain（算子服务必需）
)
```

### 8.2 认证方式

| 方式 | 适用场景 | 实现 |
|------|---------|------|
| **静态 Token** | 开发调试、短期脚本 | `TokenAuth(token)` |
| **OAuth2 Client Credentials** | 服务间调用、生产部署 | `OAuth2Auth(client_id, secret, token_endpoint)` — 自动获取并缓存 token，过期前刷新 |
| **自定义** | 特殊认证体系 | 实现 `AuthProvider` 接口 |

```python
class AuthProvider(Protocol):
    def auth_headers(self) -> dict[str, str]: ...

class OAuth2Auth(AuthProvider):
    def __init__(self, client_id: str, client_secret: str, token_endpoint: str): ...
    # 内部: token 缓存 + 过期前 30s 自动刷新 + 线程安全
```

### 8.3 凭据安全

| 风险 | 措施 |
|------|------|
| 数据源密码泄露（日志/异常） | SDK 在日志和异常信息中自动脱敏 `password` 字段，仅显示 `***` |
| Token 泄露 | `AuthProvider` 不在 `__repr__` 中暴露 token |
| Skill 层传递密码 | `connect_db` Skill 接收密码后仅传给 SDK，不写入返回值和日志 |
| 请求日志 | `log_requests=True` 时自动过滤 `Authorization` Header 和 body 中的敏感字段 |

### 8.4 权限边界

SDK 本身不做权限校验（由 ADP 服务端完成），但需要处理权限错误:

```python
class AuthenticationError(ADPError): ...   # 401 — Token 无效或过期
class AuthorizationError(ADPError): ...    # 403 — 无权限操作此资源
```

Skill 层在收到 403 时向 Agent 返回可理解的错误信息（"当前账号无权创建知识网络，请联系管理员"），而非裸露的 HTTP 状态码。

---

## 9 包结构

```
kweaver-sdk/
├── pyproject.toml
├── src/kweaver/
│   ├── __init__.py              # 导出 ADPClient, tools
│   ├── _client.py               # ADPClient
│   ├── _http.py                 # httpx + 重试 + 日志脱敏
│   ├── _auth.py                 # AuthProvider, TokenAuth, OAuth2Auth
│   ├── _errors.py               # ADPError 层级
│   ├── types.py                 # Pydantic 模型
│   ├── resources/               # SDK 内部模块
│   │   ├── datasources.py
│   │   ├── dataviews.py
│   │   ├── knowledge_networks.py
│   │   ├── object_types.py
│   │   ├── relation_types.py
│   │   ├── query.py
│   │   ├── agents.py            # v0.4 新增: Decision Agent 管理
│   │   └── conversations.py     # v0.4 新增: 会话与消息管理
│   └── skills/                  # Skill 层（对外 Tool 定义 + 编排逻辑）
│       ├── __init__.py          # 导出所有 Tool 定义
│       ├── _base.py             # Skill 基类
│       ├── connect_db.py
│       ├── build_kn.py
│       ├── query_kn.py
│       ├── load_kn_context.py
│       ├── discover_agents.py   # v0.4 新增: 列举 Decision Agent
│       └── chat_agent.py        # v0.4 新增: Agent 对话
└── tests/
    ├── conftest.py              # 共享 fixture: mock client, test config
    ├── unit/
    │   ├── test_auth.py
    │   ├── test_datasources.py
    │   ├── test_dataviews.py
    │   ├── test_knowledge_networks.py
    │   ├── test_object_types.py
    │   ├── test_relation_types.py
    │   ├── test_query.py
    │   ├── test_agents.py       # v0.4 新增
    │   └── test_conversations.py # v0.4 新增
    ├── skills/
    │   ├── test_connect_db.py
    │   ├── test_build_kn.py
    │   ├── test_query_kn.py
    │   ├── test_load_kn_context.py
    │   ├── test_discover_agents.py  # v0.4 新增
    │   └── test_chat_agent.py       # v0.4 新增
    └── integration/
        └── test_full_flow.py    # 端到端: 数据库 → 知识网络 → 查询 → Agent 对话
```

---

## 10 测试

### 10.1 分层测试策略

测试按架构分层组织，每层有明确的测试目标和隔离方式：

```
┌───────────────────────────────────────────┐
│  Skill 测试                               │  mock SDK，验证编排逻辑
├───────────────────────────────────────────┤
│  SDK 单元测试                              │  mock HTTP，验证参数转换
├───────────────────────────────────────────┤
│  集成测试                                  │  真实 ADP 实例，验证端到端
└───────────────────────────────────────────┘
```

| 层 | 隔离方式 | 验证什么 | 运行时机 |
|----|---------|---------|---------|
| SDK 单元测试 | mock httpx 响应 | 参数转换（扁平→嵌套）、响应解析、错误映射 | 每次提交 |
| Skill 测试 | mock SDK Resource | 编排顺序、参数传递、错误处理、返回值组装 | 每次提交 |
| 集成测试 | 真实 ADP 实例 | 端到端流程、服务兼容性 | CI 定时 / 发版前 |

### 10.2 SDK 单元测试

mock HTTP 层，验证 SDK 方法是否正确地将扁平参数转换为 REST 请求、将 REST 响应解析为类型化对象。

```python
import httpx
import pytest
from kweaver import ADPClient
from kweaver._http import MockTransport

def test_datasource_create_transforms_params():
    """验证 SDK 扁平参数正确转换为 REST 嵌套结构。"""
    requests = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, json=[{"id": "ds_01"}])

    client = ADPClient(
        base_url="https://mock",
        token="test",
        transport=MockTransport(handler),
    )

    ds = client.datasources.create(
        name="测试库", type="mysql",
        host="10.0.1.100", port=3306,
        database="erp", account="root", password="secret",
    )

    # 验证请求 body 结构
    body = requests[0].content
    assert body["bin_data"]["host"] == "10.0.1.100"
    assert body["bin_data"]["database_name"] == "erp"
    assert body["bin_data"]["connect_protocol"] == "jdbc"
    assert "password" in body["bin_data"]

    # 验证返回类型
    assert ds.id == "ds_01"


def test_object_type_create_wraps_in_entries():
    """验证 create 将参数包装为 entries 数组，primary_keys 为数组。"""
    ...


def test_object_type_primary_key_shortcut():
    """primary_key='id' 应自动转换为 primary_keys=['id']。"""
    ...


def test_object_type_create_auto_inherits_fields():
    """properties 不传时，SDK 应从 DataView 自动继承字段。"""
    ...


def test_relation_type_direct_mapping():
    """不传 mapping_view_id 时，生成 direct 类型的 mapping_rules。"""
    ...


def test_relation_type_dataview_mapping():
    """传 mapping_view_id 时，生成 data_view 类型的 mapping_rules。"""
    ...


def test_instances_query_sends_method_override_header():
    """实例查询应发送 X-HTTP-Method-Override: GET header。"""
    ...


def test_instances_query_returns_search_after():
    """实例查询结果应包含 search_after 游标用于翻页。"""
    ...


def test_401_raises_authentication_error():
    """服务端返回 401 时，SDK 应抛出 AuthenticationError。"""
    def handler(request):
        return httpx.Response(401, json={"error_code": "TOKEN_EXPIRED", "message": "token expired"})

    client = ADPClient(base_url="https://mock", token="bad", transport=MockTransport(handler))

    with pytest.raises(AuthenticationError) as exc:
        client.datasources.list()
    assert exc.value.error_code == "TOKEN_EXPIRED"


def test_password_not_in_logs(caplog):
    """日志中不应出现明文密码。"""
    ...
```

### 10.3 Skill 测试

mock 整个 SDK 层，只验证 Skill 的编排逻辑：调用了哪些 SDK 方法、顺序是否正确、中间结果是否正确传递。

```python
from unittest.mock import MagicMock
from kweaver.skills.build_kn import BuildKnSkill
from kweaver.types import DataSource, DataView, KnowledgeNetwork, ObjectType, Table, Column

def test_build_kn_full_flow():
    """验证 build_kn 按正确顺序编排 SDK 调用。"""
    mock_client = MagicMock()

    # 设置 mock 返回值
    mock_client.datasources.list_tables.return_value = [
        Table(name="products", columns=[Column(name="id", type="integer")]),
        Table(name="inventory", columns=[Column(name="seq", type="integer")]),
    ]
    mock_client.dataviews.create.side_effect = [
        DataView(id="dv_01", name="products", query_type="SQL", fields=[]),
        DataView(id="dv_02", name="inventory", query_type="SQL", fields=[]),
    ]
    mock_client.knowledge_networks.create.return_value = KnowledgeNetwork(
        id="kn_01", name="test", statistics=None,
    )
    mock_client.object_types.create.side_effect = [
        ObjectType(id="ot_01", name="products", kn_id="kn_01", dataview_id="dv_01",
                   primary_keys=["id"], display_key="id", properties=[]),
        ObjectType(id="ot_02", name="inventory", kn_id="kn_01", dataview_id="dv_02",
                   primary_keys=["seq"], display_key="seq", properties=[]),
    ]
    mock_client.knowledge_networks.build.return_value = MagicMock()

    skill = BuildKnSkill(client=mock_client)
    result = skill.run(
        datasource_id="ds_01",
        tables=["products", "inventory"],
        relations=[{"name": "prod_inv", "from_table": "products", "to_table": "inventory",
                     "from_field": "id", "to_field": "product_id"}],
    )

    # 验证编排顺序
    assert mock_client.dataviews.create.call_count == 2
    assert mock_client.knowledge_networks.create.call_count == 1
    assert mock_client.object_types.create.call_count == 2
    assert mock_client.relation_types.create.call_count == 1
    assert mock_client.knowledge_networks.build.call_count == 1

    # 验证参数传递: relation_types.create 收到的是 object_type ID 而非表名
    rt_call = mock_client.relation_types.create.call_args
    assert rt_call.kwargs["source_ot_id"] == "ot_01"
    assert rt_call.kwargs["target_ot_id"] == "ot_02"

    # 验证返回值
    assert result["status"] == "ready"
    assert len(result["object_types"]) == 2


def test_build_kn_handles_auth_error():
    """SDK 抛出 AuthorizationError 时，Skill 返回可读错误而非抛异常。"""
    mock_client = MagicMock()
    mock_client.datasources.list_tables.return_value = []
    mock_client.knowledge_networks.create.side_effect = AuthorizationError(
        status_code=403, error_code="FORBIDDEN", message="no permission", trace_id="t1"
    )

    skill = BuildKnSkill(client=mock_client)
    result = skill.run(datasource_id="ds_01")

    assert result["error"] is True
    assert "无权" in result["message"]


def test_build_kn_empty_tables_uses_all():
    """tables 参数为空时，应纳入 list_tables 返回的全部表。"""
    ...


# ---- load_kn_context Skill 测试 ----

def test_load_kn_context_overview():
    """overview 模式应调用 knowledge_networks.list 并提取统计信息。"""
    mock_client = MagicMock()
    mock_client.knowledge_networks.list.return_value = [
        KnowledgeNetwork(id="kn_01", name="erp_prod",
                         statistics=KNStatistics(object_types_total=3, relation_types_total=1)),
        KnowledgeNetwork(id="kn_02", name="crm",
                         statistics=KNStatistics(object_types_total=5, relation_types_total=4)),
    ]

    skill = LoadKnContextSkill(client=mock_client)
    result = skill.run(mode="overview")

    assert len(result["knowledge_networks"]) == 2
    assert result["knowledge_networks"][0]["object_type_count"] == 3


def test_load_kn_context_schema():
    """schema 模式应返回对象类和关系类的完整结构。"""
    mock_client = MagicMock()
    mock_client.object_types.list.return_value = [
        ObjectType(id="ot_01", name="产品", kn_id="kn_01", dataview_id="dv_01",
                   primary_keys=["id"], display_key="name", properties=[
                       DataProperty(name="id", type="integer", indexed=True),
                       DataProperty(name="name", type="varchar", fulltext=True),
                   ]),
    ]
    mock_client.relation_types.list.return_value = [
        RelationType(id="rt_01", name="产品_库存", kn_id="kn_01",
                     source_ot_id="ot_01", target_ot_id="ot_02", mapping_type="direct"),
    ]

    skill = LoadKnContextSkill(client=mock_client)
    result = skill.run(mode="schema", kn_id="kn_01")

    assert len(result["object_types"]) == 1
    assert result["object_types"][0]["properties"][0]["indexed"] is True
    assert len(result["relation_types"]) == 1


def test_load_kn_context_schema_with_samples():
    """include_samples=true 时，应为每个对象类拉取样本数据。"""
    mock_client = MagicMock()
    mock_client.object_types.list.return_value = [
        ObjectType(id="ot_01", name="产品", kn_id="kn_01", dataview_id="dv_01",
                   primary_keys=["id"], display_key="name", properties=[]),
    ]
    mock_client.relation_types.list.return_value = []
    mock_client.query.instances.return_value = InstanceResult(
        data=[{"id": 1, "name": "轴承A"}, {"id": 2, "name": "轴承B"}],
        total_count=100,
    )

    skill = LoadKnContextSkill(client=mock_client)
    result = skill.run(mode="schema", kn_id="kn_01", include_samples=True, sample_size=2)

    mock_client.query.instances.assert_called_once()
    assert len(result["object_types"][0]["sample_data"]) == 2


def test_load_kn_context_instances():
    """instances 模式应查询实例并附带 Schema 信息。"""
    mock_client = MagicMock()
    mock_client.object_types.list.return_value = [
        ObjectType(id="ot_01", name="库存", kn_id="kn_01", dataview_id="dv_01",
                   primary_keys=["seq"], display_key="seq", properties=[
                       DataProperty(name="seq", type="integer"),
                       DataProperty(name="quantity", type="integer"),
                   ]),
    ]
    mock_client.query.instances.return_value = InstanceResult(
        data=[{"seq": 1, "quantity": 1200}],
        total_count=1523,
        search_after=[1],
    )

    skill = LoadKnContextSkill(client=mock_client)
    result = skill.run(mode="instances", kn_id="kn_01", object_type="库存", limit=10)

    assert result["total_count"] == 1523
    assert result["has_more"] is True
    assert result["object_type_schema"]["name"] == "库存"


def test_load_kn_context_by_name():
    """传 kn_name 时，应先按名称查找再返回 Schema。"""
    mock_client = MagicMock()
    mock_client.knowledge_networks.list.return_value = [
        KnowledgeNetwork(id="kn_01", name="erp_prod"),
    ]
    mock_client.object_types.list.return_value = []
    mock_client.relation_types.list.return_value = []

    skill = LoadKnContextSkill(client=mock_client)
    result = skill.run(mode="schema", kn_name="erp_prod")

    mock_client.knowledge_networks.list.assert_called_once_with(name="erp_prod")
    assert result["kn_id"] == "kn_01"
```

### 10.4 集成测试

对真实 ADP 实例运行端到端流程。通过环境变量配置连接信息，CI 中定时执行。

```python
import os
import pytest
from kweaver import ADPClient

SKIP_REASON = "ADP_BASE_URL not set"

@pytest.fixture
def client():
    base_url = os.getenv("ADP_BASE_URL")
    token = os.getenv("ADP_TOKEN")
    if not base_url:
        pytest.skip(SKIP_REASON)
    return ADPClient(base_url=base_url, token=token, account_id=os.getenv("ADP_ACCOUNT_ID", "test"))


def test_full_flow_database_to_query(client):
    """端到端: 连接数据库 → 创建知识网络 → 查询。"""
    # 1. 连接（使用测试数据库）
    ds = client.datasources.create(
        name="sdk_integration_test",
        type=os.getenv("ADP_TEST_DB_TYPE", "mysql"),
        host=os.getenv("ADP_TEST_DB_HOST"),
        port=int(os.getenv("ADP_TEST_DB_PORT", "3306")),
        database=os.getenv("ADP_TEST_DB_NAME"),
        account=os.getenv("ADP_TEST_DB_USER"),
        password=os.getenv("ADP_TEST_DB_PASS"),
    )

    try:
        # 2. 发现表
        tables = client.datasources.list_tables(ds.id)
        assert len(tables) > 0

        # 3. 创建视图
        view = client.dataviews.create(name="test_view", datasource_id=ds.id, table=tables[0].name)

        # 4. 创建知识网络 + 对象类
        kn = client.knowledge_networks.create(name="sdk_test_kn")
        ot = client.object_types.create(
            kn_id=kn.id, name="test_ot",
            dataview_id=view.id,
            primary_keys=[tables[0].columns[0].name],
            display_key=tables[0].columns[0].name,
        )

        # 5. 构建
        client.knowledge_networks.build(kn.id).wait(timeout=120)

        # 6. 查询
        result = client.query.semantic_search(kn_id=kn.id, query="test")
        assert result is not None

    finally:
        # 清理（逆序删除）
        client.knowledge_networks.delete(kn.id)
        client.dataviews.delete(view.id)
        client.datasources.delete(ds.id)
```

### 10.5 测试配置

```ini
# pyproject.toml
[tool.pytest.ini_options]
testpaths = ["tests"]
markers = [
    "integration: 需要真实 ADP 实例（通过环境变量配置）",
]

# 默认只跑单元测试，集成测试需显式指定
addopts = "-m 'not integration'"
```

```bash
# 本地开发: 只跑单元测试
pytest

# CI / 发版前: 跑全部
pytest -m ""

# 只跑集成测试
ADP_BASE_URL=https://... ADP_TOKEN=... pytest -m integration
```

---

## 11 扩展路线

| 用例 | 新增 Skill | 新增 SDK 模块 | 依赖的已有模块 |
|------|-----------|--------------|--------------|
| **Agent 列举与对话** (v0.4) | `discover_agents`, `chat_agent` | `agents`, `conversations` | — |
| 执行业务操作（发起 PO） | `execute_action` | `action_types` | query |
| BOM 展开 / 指标计算 | `compute_metric` | `query.logic_properties()` | query |
| 从文档构建知识网络 | `import_docs` | 文档解析模块 | knowledge_networks, object_types, relation_types |
| 管理知识网络 | `manage_kn` | `concept_groups` | knowledge_networks, object_types, relation_types |
| 算子管理 | `manage_operators` | `operators` resource | — |
| 外部 MCP 接入 | — | `mcp` resource | — |

---

## 附录 A: v0.3 → v0.4 变更记录

| 变更 | 原因 |
|------|------|
| 新增 `discover_agents` Skill（§5.1.3） | 列举 Decision Agent，了解平台上可用的智能体及其能力 |
| 新增 `chat_agent` Skill（§5.3.1） | 与 Decision Agent 多轮对话，支持流式输出和历史会话管理 |
| 新增交互类 Skill 分类（§5.3） | Agent 对话既非纯读也非纯写，独立为第三类 |
| 新增 `agents` SDK 模块（§6.9） | Decision Agent 的列举和详情查询 |
| 新增 `conversations` SDK 模块（§6.10） | 会话生命周期管理：创建、发送消息（含流式）、查看历史 |
| 功能目标新增场景 3: Agent 列举与对话（§2） | 形成"构建→探索→Agent 对话"完整价值链 |
| 新增 §4.4 Decision Agent 流程图 | 说明 discover_agents 和 chat_agent 的内部编排 |
| 对话示例新增场景 4/5/6（§5.4） | 覆盖 Agent 发现、多轮对话、历史回溯 |
| HTTP 层新增 `decision-agent` 服务 | 对接 Decision Agent 管理与对话 API |

## 附录 B: v0.2 → v0.3 变更记录

| 变更 | 原因 |
|------|------|
| 新增 `load_kn_context` Skill（§5.1.1） | 提供 Schema 发现和对象浏览能力，与构建场景形成读写闭环 |
| 功能目标新增场景 2: Context Loader（§2） | 明确"构建→探索→查询"的完整工作流 |
| 新增 §4.3 Context Loader 流程图 | 说明 load_kn_context 的内部编排和与其他 Skill 的关系 |
| 新增 load_kn_context Skill 测试（§10.3） | 覆盖 overview/schema/instances 三种模式 |
| 包结构新增 `load_kn_context.py` 和对应测试 | 对齐新 Skill |

## 附录 C: v0.1 → v0.2 变更记录

| 变更 | 原因 |
|------|------|
| `primary_key: str` → `primary_keys: list[str]`（保留 `primary_key` 快捷方式） | 与 ADP 实际 API 对齐，支持复合主键 |
| `list_tables` 路径修正为 `/api/data-connection/v1/metadata/data-source/{id}` | 与实际 data-connection 服务路径对齐 |
| `db_type` 枚举扩展为 19 种数据源 | 对齐 ADP ConnectorEnums 完整列表 |
| `query.search()` → `query.semantic_search()` + `query.kn_search()` | 区分两个不同的搜索接口，semantic_search 功能更完整 |
| `instances()` 路径修正为 ontology-query 服务 | 实际实例查询在 ontology-query 而非 agent-retrieval |
| 新增 search_after 游标分页 + `instances_iter()` | 对齐 ADP 基于 OpenSearch 的分页机制 |
| `ConnectionError` → `NetworkError` | 避免与 Python 内置 `ConnectionError` 冲突 |
| 新增 `business_domain` 参数 | 算子/执行服务（execution-factory）必需 x-business-domain header |
| 包名 `adp` → `kweaver` | 避免通用名冲突，与项目名 kweaver-sdk 一致 |
| 新增 `concept_groups`、`action_types` 预留模块（§6.7/§6.8） | 为 execute_action / manage_kn Skill 预留扩展点 |
| 补充 REST 请求体的 `entries` 数组包装 | 对齐 ontology-manager 批量创建 API 的实际结构 |
| 补充 DataView 创建时 `data_scope` 的完整结构 | 消除实现时的歧义 |
| 补充 RelationType 两种映射模式的完整参数映射 | 原文档只描述了 direct 模式 |
| 移除关系自动推断（"为空则根据同名字段自动推断"） | 推断逻辑不明确且 ADP 不提供此能力，要求显式指定 |
| `build_status` 明确使用 `kn_id` 查询（非 job_id） | 与 agent-retrieval 实际接口对齐 |
| HTTP 层服务列表更新 | 新增 ontology-query 服务，明确各服务职责 |
