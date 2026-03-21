# 通用 API 调用参考

直接调用 KWeaver REST API，自动注入认证。类似 curl。

## 命令

```bash
kweaver call <path> [-X <method>] [-d '<json>'] [-H 'Name: Value' ...] [-bd <domain>] [-v]
```

| 参数 | 说明 |
|------|------|
| `<path>` | API 路径（如 `/api/ontology-manager/v1/knowledge-networks`） |
| `-X` | HTTP 方法（默认 GET） |
| `-d` | JSON 请求体 |
| `-H` | 额外请求头（可重复） |
| `-bd` | 覆盖 business domain |
| `-v` | 打印请求信息到 stderr |
| `--pretty` | Pretty-print JSON 输出（默认开启） |

## 示例

```bash
# GET
kweaver call /api/ontology-manager/v1/knowledge-networks

# POST
kweaver call /api/ontology-manager/v1/knowledge-networks -X POST -d '{"name": "test", "branch": "main"}'

# 带自定义 header
kweaver call /api/some-service/v1/endpoint -H 'X-Custom: value'

# 指定 business domain
kweaver call /api/ontology-manager/v1/knowledge-networks -bd my_domain
```
