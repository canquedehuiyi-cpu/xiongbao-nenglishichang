# Alipay CLI Reference

> 支付宝开放平台命令行工具使用指南,供 AI Agent / Skill 引用。涵盖安装、认证、MCP 工具调用、文件上传与诊断等能力。

## 一句话定位

Alipay CLI(`alipay-cli`)是支付宝开放平台的终端工具,帮助开发者通过命令行完成 OAuth 2.0 Device Flow 认证、调用 MCP(Model Context Protocol)工具、上传文件与环境诊断。

## 功能特性

- **OAuth 2.0 Device Flow 认证**:完整实现 PKCE + RFC 8628,支持交互式与非交互式登录(后者面向 CI/CD 与 AI Agent 集成)。
- **MCP 工具调用**:支持工具列举与调用,工具名格式 `<server>.<tool>`;支持匿名工具(无需登录)。
- **诊断工具**:内置 network / auth / config / all 四类诊断。
- **双输出模式**:人类可读格式与 `--json` 结构化输出。
- **安全存储**:系统密钥环(keyring)优先,加密文件(file)降级。
- **dry-run 预览**:login / logout / mcp / file 命令支持预览请求而不实际发送。

## 安装

```bash
# 安装最新版本(推荐)
curl -fsSL https://opengw.alipay.com/alipaycli/install | bash

# 安装指定版本
curl -fsSL https://opengw.alipay.com/alipaycli/install | bash -s -- v1.0.0

# 验证
alipay-cli version
```

## 全局参数

所有命令共享以下参数。

| 参数 | 简写 | 说明 |
| --- | --- | --- |
| `--json` | `-j` | JSON 输出模式(便于脚本/Agent 解析) |
| `--dry-run` | — | 预览请求而不实际发送(login/logout/mcp/file) |

## 命令参考

### login — 登录授权

```bash
alipay-cli login [flags]
```

| 参数 | 说明 |
| --- | --- |
| `--non-interactive` | 非交互式模式(用于 CI/CD 或 Agent 集成);不带此参数默认走交互式 |
| `--complete` | 检查非交互式登录授权状态(单次检查,**不轮询**,需反复调用直到成功) |
| `--scope` | OAuth 权限范围(覆盖配置文件中的默认值) |

**交互式流程**(默认):CLI 生成 PKCE 参数 → 调用设备授权端点获取 `device_code` 与验证 URL → 用户在浏览器完成授权 → CLI 轮询 Token 端点等待授权完成 → 保存凭据到安全存储。

**非交互式流程**(Agent 集成场景,两步):

```bash
# 步骤 1:发起登录(已有会话则短路返回 already_logged_in,否则返回 device_code 与验证 URL)
alipay-cli login --non-interactive --json
# 已有会话:{"success":true,"data":{"status":"already_logged_in","scope":"app:read","expires_at":"2026-05-12T10:00:00Z"}}
# 无会话:{"success":true,"data":{"device_code":"...","verification_url":"https://...","verification_code":"XXXX-XXXX","expires_in":600,"interval":5}}

# 步骤 2:引导用户在浏览器打开 verification_url 完成授权后,轮询检查状态
alipay-cli login --complete --json
# 授权待确认:{"success":true,"data":{"status":"pending","code":"authorization_pending","message":"授权待确认","action":"RETRY","interval":5}}
# 授权完成:{"success":true,"data":{"status":"logged_in","scope":"app:read","expires_at":"2026-05-12T10:00:00Z"}}
```

### logout — 登出

```bash
alipay-cli logout
```

撤销服务端 Token 并清除本地会话。支持 `--dry-run` 预览。

### mcp — MCP 工具调用

```bash
# 列出某个服务可用工具
alipay-cli mcp list <server>

# 调用工具
alipay-cli mcp call <server>.<tool> -d '<json-params>'

# 预览请求(不实际发送)
alipay-cli mcp call <server>.<tool> -d '<json-params>' --dry-run
```

`mcp call` 参数:

| 参数 | 简写 | 说明 |
| --- | --- | --- |
| `<server>.<tool>` | — | 位置参数,工具全名,例如 `apprelease.queryApplicationInfo` |
| `--data` | `-d` | 请求参数(JSON 格式) |

要点:

- 工具名必须为 `<server>.<tool>` 格式,否则报错。
- 以 `alipay-anonymous-sandbox.` 为前缀的工具**不需要登录**即可调用。
- 调用前可先用 `mcp list <server>` 探测该服务可用工具。

示例:

```bash
# 列出 apprelease 服务的工具
alipay-cli mcp list apprelease

# 调用 apprelease.queryApplicationInfo
alipay-cli mcp call apprelease.queryApplicationInfo -d '{"request":{"appId":"2021006129682469"}}'

# 调用匿名沙箱工具(免登录)
alipay-cli mcp call alipay-anonymous-sandbox.createAnonymousSandbox -d '{}'
```

### file — 文件操作

```bash
# 上传文件(--scene 为必填参数)
alipay-cli file upload <file-path> --scene <scene-name>
```

| 参数 | 简写 | 说明 |
| --- | --- | --- |
| `<file-path>` | — | 位置参数,待上传文件路径 |
| `--scene` | `-s` | 业务场景(必填),例如 `payMerchantcodeSkill` |

支持 `--dry-run` 预览。

### diagnose — 诊断

```bash
alipay-cli diagnose <command>
```

| 子命令 | 说明 |
| --- | --- |
| `network` | 网络诊断:DNS、API 网关连通性、OAuth 服务器可达性、健康检查端点 |
| `auth` | 认证诊断:会话状态、Token 有效性、凭据存储读写测试 |
| `all` | 运行所有诊断 |

诊断结果支持 `--json` 输出。

```bash
alipay-cli diagnose all --json
alipay-cli diagnose network
```

### version / whoami

```bash
alipay-cli version    # 版本信息
alipay-cli whoami     # 当前登录状态信息
```

## 退出码

退出码统一由中间件映射,范围 0–7:

| 退出码 | 说明 |
| --- | --- |
| 0 | 成功 |
| 1 | 一般错误 |
| 2 | 参数错误 |
| 3 | 认证错误 |
| 4 | 权限错误 |
| 5 | 配置错误 |
| 6 | API 错误 |
| 7 | I/O 错误 |

## 故障排查

### 登录失败:密钥环不可用

```
错误:初始化应用上下文失败: keyring not available
```

**解决**:确保系统密钥环服务可用,或运行 `alipay-cli diagnose auth --json` 获取结构化排查信息。

### Token 过期

```bash
alipay-cli diagnose auth    # 检查会话状态
alipay-cli login            # 重新登录
```

### 网络连接问题

```bash
alipay-cli diagnose network
```

## Agent 集成要点

将 Alipay CLI 嵌入 AI Agent / Skill 时,推荐遵循以下约定:

1. **统一用 `--json` 输出**:所有命令均支持,便于程序化解析。错误也以 JSON 返回,不直接中断进程,退出码由中间件统一处理。
2. **登录走非交互式两步**:`login --non-interactive --json` 取 device_code/verification_url → 引导用户授权 → 反复 `login --complete --json` 检查,直到 `status` 非 `pending`。注意 `--complete` 是单次检查,不轮询。
3. **调用 MCP 工具用 `-d` 传 JSON**:`mcp call <server>.<tool> -d '<json>' --json`。先用 `mcp list <server>` 探测可用工具。
4. **匿名工具免登录**:以 `alipay-anonymous-sandbox.` 为前缀的工具可直接调用,适合无需用户身份的场景(如创建匿名沙箱)。
5. **预览先于执行**:用 `--dry-run` 预览将要发送的请求,确认无误再正式调用(避免误操作文件上传、Token 撤销等)。
6. **靠退出码判断结果**:0 成功;3=认证失败需重新登录;6=API 错误需检查参数;其它码见退出码表。
7. **诊断兜底**:网络/认证/配置异常时,优先 `diagnose all --json` 获取结构化排查信息。