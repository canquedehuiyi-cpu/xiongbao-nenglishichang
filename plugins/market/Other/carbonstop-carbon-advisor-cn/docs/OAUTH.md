# Qoder 国内站 OAuth 接入交接

## 精确回调

由合作方提供的国内站回调为：

```text
https://mcp.qoder.cn/api/mcp/oauth_callback
```

请 Gateway/Auth 管理员精确放行该字符串，并确认动态注册、授权请求和换票过程的回调校验一致。不使用通配符，不额外添加尾斜杠、查询参数或 WorkBuddy 回调。

插件根目录的 `.mcp.json` 只声明 MCP 服务，不添加未经 Qoder 确认支持的 `callback` / `redirect_uri` 字段。Qoder 在动态注册或使用已登记客户端时携带回调；资料中的回调本身不是授权凭证。

上述回调是合作方提供的 Qoder 国内托管接入地址，并不表示所有 IDE、CLI 或 SDK 本地授权流程都会使用它。若本地导入时实际发送了不同回调，双方应核对并登记该客户端真正使用的地址，不把授权请求强改为无法接收回调的地址。

## 生产端点

| 参数 | 值 |
| --- | --- |
| MCP resource / audience | `https://gateway.carbonstop.com/mcp/ccdb` |
| 资源元数据 | `https://gateway.carbonstop.com/.well-known/oauth-protected-resource/mcp/ccdb` |
| issuer | `https://gateway.carbonstop.com/auth` |
| 授权服务器元数据 | `https://gateway.carbonstop.com/auth/.well-known/oauth-authorization-server` |
| 注册端点 | `https://gateway.carbonstop.com/auth/oauth/register` |
| 授权端点 | `https://agent.carbonstop.com/oauth/authorize` |
| 令牌端点 | `https://gateway.carbonstop.com/auth/oauth/token` |
| 撤销端点 | `https://gateway.carbonstop.com/auth/oauth/revoke` |
| response_type | `code` |
| grants | `authorization_code`、`refresh_token` |
| PKCE | `S256` |
| token_endpoint_auth_method | `none`，公共客户端不携带 client_secret |
| 业务 scopes | `ccdb.factor.search ccdb.factor.read` |
| 可选续期 scope | `offline_access`，按实际刷新令牌策略申请 |

端点来自 2026-10-27 的生产元数据检查；正式接入时以发现结果为准。绑定 MCP resource，不要误用 CLI REST resource 或内部执行路由。

## Client ID 如何交付

本包不虚构或复用 CLI、WorkBuddy 的 client_id。当前服务器公布动态客户端注册端点：如果 Qoder 采用该方式，client_id 由注册响应分配，注册时提交国内回调，并使用公共客户端 + PKCE。发现端点存在不代表本次注册已成功。

如果 Qoder 合作接入必须使用预注册 Client ID，由 Carbonstop 后端登记国内专用客户端后另行提供实际 ID，并绑定本文回调、scopes、MCP resource 和所需 grants。不得使用占位符或默认的本地 CLI client_id 冒充已登记值。若另要求 client_secret，需先与双方确认兼容性和安全交付方式；当前元数据只公布 `none`。

## 联调边界

先完成用户授权，再用用户自己的 Bearer Access Token 调用 MCP。令牌由 Qoder 安全存储和续期，不放在包、上架文案、截图或聊天中。此连接器只交付 OAuth 接入，不配置共用 API Key 或自动切换认证方式。

待确认项：国内回调白名单已发布、实际 client_id/注册方式已确定、PKCE 授权成功、刷新与撤权可用。本次未修改或验证后端白名单；应通过 Qoder 实际请求及后端日志确认，而非仅看资料文件。
