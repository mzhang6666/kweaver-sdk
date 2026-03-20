# Action 命令参考

Action Type 查询与执行。**执行有副作用，执行前向用户确认。**

> **注意**：Action 功能通过 `bkn` 子命令提供，没有独立的 `action` 顶层命令。

## 命令

```bash
kweaver bkn action-type list <kn_id>
kweaver bkn action-type query <kn_id> <at_id>
kweaver bkn action-type execute <kn_id> <at_id> [<params_json>]
kweaver bkn action-execution get <kn_id> <execution_id> [--wait/--no-wait] [--timeout 300]
kweaver bkn action-log list <kn_id> [--offset 0] [--limit 20]
kweaver bkn action-log get <kn_id> <log_id>
kweaver bkn action-log cancel <kn_id> <log_id> [-y]
```

## 说明

- `action-type execute` 触发真实操作，需要用户确认
- `action-execution get --wait` 轮询直到执行完成或超时
- `action-log cancel` 取消正在执行的任务

## 端到端示例

```bash
# 查看可用 action
kweaver bkn action-type list <kn_id>

# 查看 action 详情
kweaver bkn action-type query <kn_id> <at_id>

# 执行 action（带参数）
kweaver bkn action-type execute <kn_id> <at_id> '{"source": "erp"}'

# 查看执行日志
kweaver bkn action-log list <kn_id>
kweaver bkn action-log get <kn_id> <log_id>
```
