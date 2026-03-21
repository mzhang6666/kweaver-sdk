# BKN 命令参考

知识网络管理：schema CRUD、构建、导出、推送/拉取。

## 概览

```bash
kweaver bkn list                     # 列出知识网络
kweaver bkn get <kn_id> [--stats] [--export]
```

## 知识网络

```bash
kweaver bkn list [--name <n>] [--name-pattern <p>] [--tag <t>] [--sort update_time] [--direction desc] [--offset 0] [--limit 50] [-v]
kweaver bkn get <kn_id> [--stats] [--export]
kweaver bkn stats <kn_id>
kweaver bkn export <kn_id>
kweaver bkn create [options]                         # 创建空知识网络（或 --body-file）
kweaver bkn create-from-ds <ds_id> --name <name> [--tables <t1,t2>] [--build/--no-build] [--timeout 300]
kweaver bkn update <kn_id> [--name <n>] [--description <d>] [--tag <t> ...]
kweaver bkn build <kn_id> [--wait/--no-wait] [--timeout 300]
kweaver bkn delete <kn_id> [--yes]
kweaver bkn push <directory> [--branch main]         # 上传 BKN 目录为 tar
kweaver bkn pull <kn_id> [<directory>] [--branch main]  # 下载 BKN tar 并解压
```

## Object Type

```bash
kweaver bkn object-type list <kn_id>
kweaver bkn object-type get <kn_id> <ot_id>                # -v 显示完整 data_properties
kweaver bkn object-type create <kn_id> --name <n> --dataview-id <dv> --primary-key <pk> --display-key <dk> [--property '<json>' ...]
kweaver bkn object-type update <kn_id> <ot_id> [--name <n>] [--display-key <dk>]
kweaver bkn object-type delete <kn_id> <ot_ids> [--yes/-y]
kweaver bkn object-type query <kn_id> <ot_id> ['<json>']   # 查询实例（支持 --limit/--search-after）
kweaver bkn object-type properties <kn_id> <ot_id> '<json>' # 查询实例属性
```

## Relation Type

```bash
kweaver bkn relation-type list <kn_id>
kweaver bkn relation-type get <kn_id> <rt_id>
kweaver bkn relation-type create <kn_id> --name <n> --source <ot_id> --target <ot_id> [--mapping src:tgt ...]
kweaver bkn relation-type update <kn_id> <rt_id> [--name <n>]
kweaver bkn relation-type delete <kn_id> <rt_ids> [--yes/-y]
```

## Search

```bash
kweaver bkn search <kn_id> <query> [--max-concepts <n>] [--mode <mode>]   # 语义搜索
```

## Subgraph

```bash
kweaver bkn subgraph <kn_id> '<json>'   # 子图查询
```

## Action Type / Log / Execution

```bash
kweaver bkn action-type list <kn_id>
kweaver bkn action-type query <kn_id> <at_id> '<json>'
kweaver bkn action-type execute <kn_id> <at_id> '<json>'   # 有副作用，执行前确认
kweaver bkn action-execution get <kn_id> <execution_id> [--wait/--no-wait] [--timeout 300]
kweaver bkn action-log list <kn_id> [--offset 0] [--limit 20] [--sort create_time] [--direction desc]
kweaver bkn action-log get <kn_id> <log_id>
kweaver bkn action-log cancel <kn_id> <log_id> [--yes/-y]
```

## 端到端示例

```bash
# 接入数据源 → 创建 KN → 查询
kweaver ds connect mysql db.example.com 3306 erp --account root --password pass
kweaver bkn create-from-ds <ds_id> --name "erp-kn" --build
kweaver bkn object-type list <kn_id>
kweaver bkn search <kn_id> "订单"
```
