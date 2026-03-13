# Action 执行

查询和执行知识网络中的 Action Type（有副作用）。

## CLI 命令总览

| 命令 | 说明 |
|------|------|
| `kweaver action query <kn-id> <at-id>` | 查询 Action 定义和参数 |
| `kweaver action execute <kn-id> <at-id> [--params '<json>'] [--no-wait] [--timeout N]` | 按 ID 执行 Action |
| `kweaver action execute <kn-id> --action-name "<name>" [--params '<json>'] [--no-wait] [--timeout N]` | 按名称执行 Action |
| `kweaver action logs <kn-id> [--limit N]` | 列出执行日志 |
| `kweaver action log <kn-id> <log-id>` | 查看单条日志 |

## CLI 用法详解

### 按名称执行（自动查找 action_type_id）

```bash
kweaver action execute <kn-id> --action-name "库存盘点"
# -> 返回 execution_id, status, result
```

### 按 ID 执行，传入参数

```bash
kweaver action execute <kn-id> <at-id> --params '{"warehouse":"华东"}' --timeout 600
# -> 等待执行完成，返回结果
```

### 异步执行（不等待完成）

```bash
kweaver action execute <kn-id> <at-id> --no-wait
# -> 返回 execution_id, status: "pending"
```

### 查看日志

```bash
kweaver action logs <kn-id>
kweaver action logs <kn-id> --limit 50
kweaver action log <kn-id> <log-id>
```

## 关键约束

- Action 有**副作用**（修改数据、触发流程），仅在用户**明确请求**时执行
- 执行前向用户确认 Action 名称和参数
- 默认等待执行完成（最多 300 秒），加 `--no-wait` 可异步执行
- 取消执行需通过 `kweaver call` 调用底层 API

## 默认策略

- 用户说"执行某个 Action"：先 `kweaver action query <kn-id> <at-id>` 查看参数定义，确认后 `kweaver action execute`
- 用户说"看看执行记录"：`kweaver action logs <kn-id>`
- 用户说"取消执行"：需要 `log_id`，先 `kweaver action logs` 找到正在运行的记录
