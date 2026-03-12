---
name: kweaver
description: 操作 ADP 知识网络与 Decision Agent — 连接数据库、构建知识网络、查询 Schema/实例、语义搜索、列举 Agent、与 Agent 对话。当用户提到"知识网络"、"知识图谱"、"连接数据库并建模"、"查询对象类"、"有哪些 Agent"、"跟 Agent 对话"等意图时自动使用。
allowed-tools: Bash(python *)
argument-hint: [自然语言指令]
---

# KWeaver — ADP 知识网络与 Decision Agent 技能

你可以通过 kweaver SDK 操作 ADP 平台的知识网络和 Decision Agent。根据用户意图选择合适的操作。

## 环境准备

```python
from kweaver import ADPClient, TokenAuth
from kweaver.skills import (
    ConnectDbSkill, BuildKnSkill, LoadKnContextSkill, QueryKnSkill,
    DiscoverAgentsSkill, ChatAgentSkill,
)

client = ADPClient(base_url="$ADP_BASE_URL", auth=TokenAuth("$ADP_TOKEN"))
```

环境变量 `ADP_BASE_URL` 和 `ADP_TOKEN` 必须已设置。

---

## 可用操作

根据用户意图，选择下面 **一个或多个** 操作组合执行。

### 1. connect_db — 连接数据库

**何时用**: 用户想接入一个数据库、查看库里有哪些表。

```python
result = ConnectDbSkill(client).run(
    db_type="mysql",       # mysql|postgresql|oracle|sqlserver|clickhouse|...
    host="10.0.1.100",
    port=3306,
    database="erp_prod",
    account="readonly",
    password="xxx",
    # schema="public",     # PostgreSQL/Oracle 等需要
)
# 返回: { datasource_id, tables: [{ name, columns: [{ name, type, comment }] }] }
```

### 2. build_kn — 构建知识网络

**何时用**: 用户想把数据库中的表建模为知识网络。需要先 connect_db 拿到 datasource_id。

```python
result = BuildKnSkill(client).run(
    datasource_id="<connect_db 返回的 ID>",
    network_name="erp_prod",
    tables=["products", "inventory", "suppliers"],  # 为空则全部纳入
    relations=[
        {
            "name": "产品_库存",
            "from_table": "products",
            "to_table": "inventory",
            "from_field": "material_number",
            "to_field": "material_code",
        }
    ],
)
# 返回: { kn_id, kn_name, object_types, relation_types, status }
```

### 3. load_kn_context — 查看知识网络结构与数据

**何时用**: 用户想了解有哪些知识网络、某个网络的 Schema、或某个对象类的实例数据。

```python
skill = LoadKnContextSkill(client)

# 3a. overview — 列出所有知识网络
result = skill.run(mode="overview")
result = skill.run(mode="overview", keyword="erp")  # 按名称过滤

# 3b. schema — 查看某个知识网络的完整结构
result = skill.run(mode="schema", kn_name="erp_prod")
result = skill.run(mode="schema", kn_name="erp_prod", include_samples=True, sample_size=3)

# 3c. instances — 查看某个对象类的实例
result = skill.run(mode="instances", kn_name="erp_prod", object_type="products", limit=10)
result = skill.run(
    mode="instances", kn_name="erp_prod", object_type="products",
    conditions={"field": "price", "op": ">", "value": 100},
)
```

### 4. query_kn — 查询知识网络

**何时用**: 用户有具体的业务问题要查询（语义搜索、精确查询、关联查询）。

```python
skill = QueryKnSkill(client)

# 4a. search — 语义搜索（不确定查什么时用）
result = skill.run(kn_id="<id>", mode="search", query="高库存的产品")

# 4b. instances — 精确查询某类对象
result = skill.run(
    kn_id="<id>", mode="instances", object_type="products",
    conditions={"field": "status", "op": "==", "value": "active"},
    limit=20,
)

# 4c. subgraph — 沿关系路径做关联查询
result = skill.run(
    kn_id="<id>", mode="subgraph",
    start_object="products",
    start_condition={"field": "category", "op": "==", "value": "电子"},
    path=["inventory", "suppliers"],
)
```

### 5. discover_agents — 发现 Decision Agent

**何时用**: 用户想知道平台上有哪些可用的 Agent、某个 Agent 的详细信息。

```python
skill = DiscoverAgentsSkill(client)

# 5a. list — 列出所有已发布的 Agent
result = skill.run(mode="list")
result = skill.run(mode="list", keyword="供应链", status="published")

# 5b. detail — 查看某个 Agent 的详情（关联 KN、能力、提示词摘要）
result = skill.run(mode="detail", agent_name="供应链助手")
result = skill.run(mode="detail", agent_id="<id>")
```

### 6. chat_agent — 与 Decision Agent 对话

**何时用**: 用户想跟某个 Agent 聊天、问业务问题、查看历史对话。

```python
skill = ChatAgentSkill(client)

# 6a. ask — 向 Agent 提问（自动创建新会话）
result = skill.run(mode="ask", agent_name="供应链助手", question="物料 746 的库存情况")
# 返回: { answer, conversation_id, references }

# 6b. ask — 续接已有会话（多轮对话）
result = skill.run(
    mode="ask", agent_name="供应链助手",
    question="这个物料最近有质量问题吗？",
    conversation_id="<上一轮返回的 conversation_id>",
)

# 6c. ask — 流式输出（Skill 内部收集所有 chunk 后返回完整结果）
result = skill.run(mode="ask", agent_name="供应链助手", question="详细分析", stream=True)

# 6d. sessions — 列出与某个 Agent 的历史会话
result = skill.run(mode="sessions", agent_name="供应链助手")

# 6e. history — 查看某次会话的完整消息记录
result = skill.run(mode="history", conversation_id="<id>", limit=50)
```

---

## 操作编排指南

典型的多步流程：

1. **从零构建**: connect_db → build_kn → load_kn_context(schema) → query_kn
2. **探索已有**: load_kn_context(overview) → load_kn_context(schema) → query_kn
3. **直接查询**: 如果用户给了明确的 kn_id/kn_name，直接 query_kn
4. **发现 Agent**: discover_agents(list) → discover_agents(detail) → chat_agent(ask)
5. **Agent 对话**: chat_agent(ask) → chat_agent(ask, conversation_id=...) 多轮续接
6. **回顾历史**: chat_agent(sessions) → chat_agent(history, conversation_id=...)

## 注意事项

- 所有操作返回 dict。如果 `result.get("error")` 为 True，向用户说明错误原因。
- kn_name 可以替代 kn_id 使用（SDK 内部自动按名称查找）。
- agent_name 可以替代 agent_id 使用（SDK 内部自动按名称查找）。
- 不要向用户暴露 dataview_id、ot_id 等内部 ID，用名称展示即可。
- 构建知识网络(build_kn)可能需要等待一段时间，提前告知用户。
- chat_agent 的 ask 模式会自动创建会话，返回的 conversation_id 用于多轮续接。
