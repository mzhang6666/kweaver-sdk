# 查询命令参考

知识网络查询：语义搜索、实例查询、Schema 搜索。

> **注意**：查询功能通过 `bkn` 子命令提供，没有独立的 `query` 顶层命令。

## 命令

```bash
kweaver bkn search <kn_id> <query> [--max-concepts 10]
kweaver bkn object-type query <kn_id> <ot_id> [<body_json>] [--limit 5]
kweaver bkn object-type properties <kn_id> <ot_id> [<body_json>]
```

### 通过 Context Loader (MCP) 查询

```bash
kweaver context-loader kn-search <query>
kweaver context-loader kn-schema-search <query>
kweaver context-loader query-object-instance <ot_id> [--condition '<json>'] [--limit 20]
kweaver context-loader query-instance-subgraph <paths_json>
```

## 参数说明

### body_json 格式（object-type query）

```json
{"page": 1, "limit": 10}
```

### condition JSON 格式（Context Loader）

```json
{"field": "name", "operation": "==", "value": "Pod-123"}
```

支持的 operation: `==`, `!=`, `>`, `<`, `>=`, `<=`, `in`, `not_in`, `match`

## 端到端示例

```bash
# 语义搜索
kweaver bkn search <kn_id> "库存风险"

# 查询实例
kweaver bkn object-type query <kn_id> <ot_id> '{"page":1,"limit":5}'

# 通过 MCP 搜索 schema
kweaver context-loader kn-schema-search "订单"

# 通过 MCP 查询实例
kweaver context-loader query-object-instance <ot_id> --limit 5
```
