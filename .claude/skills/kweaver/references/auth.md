# 认证命令参考

平台认证管理。凭据存储在 `~/.kweaver/`，支持多平台和自动刷新。

## 命令

```bash
kweaver auth login <url> [--alias <name>] [--port 9010]    # 浏览器 OAuth2 登录
kweaver auth logout [<platform>]                            # 登出（默认当前平台）
kweaver auth status                                         # 查看 token 状态
kweaver auth list                                           # 列出已保存的平台
kweaver auth use <platform>                                 # 切换平台（URL 或 alias）
kweaver auth delete <platform> [-y]                         # 删除平台凭证
```

## 说明

- `login` 打开浏览器进行 OAuth2 授权，回调写入 `~/.kweaver/`
- 支持多平台，用 `--alias` 设置短名称方便切换
- Token 1 小时过期，SDK 和 CLI 自动通过 refresh token 刷新
- 如果 refresh token 也失效（服务端撤销），需要重新 `auth login`

## 示例

```bash
kweaver auth login https://kweaver.example.com --alias prod
kweaver auth login https://kweaver-dev.example.com --alias dev
kweaver auth list
kweaver auth use prod
kweaver auth status
```
