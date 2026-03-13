# 知识网络管理与查询

管理知识网络（KN），以及查询对象实例、子图、语义搜索。

## CLI 命令总览

### 数据源管理

| 命令 | 说明 |
|------|------|
| `kweaver ds connect --type mysql --host <host> --port 3306 --database <db> --account <user> --password <pwd>` | 连接数据库 |
| `kweaver ds list` | 列出数据源 |
| `kweaver ds get <ds-id>` | 查看数据源详情 |
| `kweaver ds tables <ds-id>` | 查看数据源的表列表 |
| `kweaver ds delete <ds-id>` | 删除数据源 |

### 知识网络管理

| 命令 | 说明 |
|------|------|
| `kweaver kn list [--name <filter>]` | 列出知识网络 |
| `kweaver kn get <kn-id>` | 查看网络详情 |
| `kweaver kn export <kn-id>` | 导出网络定义（对象类型、关系类型、属性） |
| `kweaver kn create --name <name> --ds-id <ds-id> --tables t1,t2 [--relations '<json>']` | 创建知识网络 |
| `kweaver kn build <kn-id> [--no-wait] [--timeout N]` | 触发全量构建 |
| `kweaver kn delete <kn-id>` | 删除网络（需确认） |

### 查询

| 命令 | 说明 |
|------|------|
| `kweaver query search <kn-id> "<query>" [--max-concepts N]` | 语义搜索 |
| `kweaver query instances <kn-id> <ot-id> [--condition '<json>'] [--limit N]` | 对象实例查询 |
| `kweaver query kn-search <kn-id> "<query>" [--only-schema]` | KN schema 搜索 |
| `kweaver query subgraph <kn-id> --start <ot-id> [--condition '<json>'] --path ot1,ot2` | 子图查询 |

### 通用 API 调用

```bash
kweaver call /api/ontology-manager/v1/knowledge-networks
kweaver call /api/ontology-query/v1/knowledge-networks/<kn-id>/object-types/<ot-id> -X POST -d '<json>'
```

## CLI 用法详解

### 连接数据库

```bash
kweaver ds connect --type mysql --host 10.0.1.100 --port 3306 \
  --database erp_prod --account readonly --password xxx
# -> 返回 datasource_id 和 tables 列表
```

### 创建并构建知识网络

```bash
# 创建知识网络
kweaver kn create --name erp_prod --ds-id <datasource-id> \
  --tables products,inventory \
  --relations '[{"name":"产品_库存","from_table":"products","to_table":"inventory","from_field":"material_number","to_field":"material_code"}]'
# -> 返回 kn_id

# 触发构建
kweaver kn build <kn-id>
# -> 等待构建完成，返回状态
```

### 查看结构与数据

```bash
# 列出所有知识网络
kweaver kn list

# 按名称筛选
kweaver kn list --name erp

# 查看网络详情
kweaver kn get <kn-id>

# 导出 Schema（对象类型、关系类型、属性）
kweaver kn export <kn-id>
```

### 查询知识网络

```bash
# 语义搜索
kweaver query search <kn-id> "高库存的产品"

# 精确查询对象实例
kweaver query instances <kn-id> <ot-id> \
  --condition '{"field":"status","operation":"eq","value":"active"}' --limit 20

# 子图查询
kweaver query subgraph <kn-id> --start <ot-id> \
  --condition '{"field":"category","operation":"eq","value":"电子"}' \
  --path inventory,suppliers
```

## Condition 语法

```json
// 单条件
{"field": "name", "operation": "like", "value": "高血压"}

// 组合条件
{"operation": "and", "sub_conditions": [
  {"field": "name", "operation": "like", "value": "高血压"},
  {"field": "severity", "operation": "eq", "value": "重度"}
]}
```

操作符：`eq`、`neq`、`gt`、`gte`、`lt`、`lte`、`in`、`not_in`、`like`、`not_like`、`exist`、`not_exist`、`match`。

## 默认策略

- 用户说"看看有哪些知识网络"：`kweaver kn list`
- 用户说"查某个知识网络的结构"：`kweaver kn export <id>`
- 用户说"查对象实例"：`kweaver query instances <kn-id> <ot-id>`
- 用户有模糊的业务问题：`kweaver query search <kn-id> "..."`

## 典型编排

1. **从零构建**: `ds connect` -> `kn create` -> `kn build` -> `kn export` -> `query search`
2. **探索已有**: `kn list` -> `kn export <id>` -> `query instances` / `query search`
3. **直接查询**: 已知 kn_id 时直接 `query search` 或 `query instances`
