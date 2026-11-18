# Alipay Sandbox Tool

提供沙箱能力：**创建快速沙箱**（匿名沙箱，返回 appId、密钥、商家/买家账号等），返回示例见 [EXAMPLES.md](./EXAMPLES.md)。

基于本仓库 `alipay-cli`（Alipay Open CLI），调用 `alipay-anonymous-sandbox.createAnonymousSandbox`。

## 1. 环境检测

### 1.1 CLI 探测

```bash
which alipay-cli 2>/dev/null && alipay-cli version
```

### 1.2 安装（如未检测到）

```bash
curl -fsSL https://opengw.alipay.com/alipaycli/install | bash
```

安装脚本默认写入 `~/.local/bin`（用户级目录，通常无需 sudo），并自动把该目录加入 PATH 配置。若仍想装到 `/usr/local/bin` 等系统目录：

```bash
curl -fsSL https://opengw.alipay.com/alipaycli/install | bash -s -- -b /usr/local/bin
# /usr/local/bin 需要管理员权限时：
sudo curl -fsSL https://opengw.alipay.com/alipaycli/install | bash -s -- -b /usr/local/bin
```

### 1.3 安装验证

```bash
alipay-cli version
```

若提示 command not found，安装脚本已默认将 CLI 装到 `~/.local/bin` 并写好 PATH 配置。尝试 `source ~/.zshrc`（或 `~/.bashrc`）刷新 PATH；若仍未生效，直接使用绝对路径 `~/.local/bin/alipay-cli`。

## 2. 创建快速沙箱

**重要：输出时必须完整展示所有字段，不允许省略 privateKey、publicKey 等长字段。如果输出被截断，需重新输出完整内容。**

```bash
alipay-cli mcp call alipay-anonymous-sandbox.createAnonymousSandbox --data '{"request":{"appType":"<APP_TYPE>"}}'
```

**appType 推断：**

| 产品/语境 | appType |
|-----------|---------|
| 小程序支付、JSAPI（小程序内） | `TINYAPP` |
| 网页应用、移动应用（电脑网站/手机网站/APP 支付等） | `PUBLICAPP` |
| AI 服务应用 | `AISERVICEAPP` |
| 未指定 / 多产品组合 | `all` |

**结果解析：**

1. 取 `result.content[0].text`，去转义还原 JSON
2. `success === true` → 输出简短成功提示，将 `data` 字段**完整原样**按 [沙箱环境初始化](sandbox-setup-guide.md) 中的沙箱信息输出格式以表格展示，保持原始字段值不变，不做任何脱敏、省略或重排。关键字段映射：
   - `data.appIds[0]` → appId / appPrivateKey / appPublicKey / alipayPublicKey / pid
   - `data.sandboxAccounts.partner` → 商家账号（merchantId / userId / email）
   - `data.sandboxAccounts.user` → 买家账号（userId / email / logonPassword / payPassword 等）
   - `data.sandboxId` → 记录以便后续认领
3. `success !== true` → 按错误处理流程

## 3. 认领链接

根据 `data.sandboxId` 拼接认领链接：

```
https://open.alipay.com/ai/ai-resource-center/sandbox/{sandboxId}/auth
```

用户要求认领时直接拼接；未提供 sandboxId 时提示先创建或提供。

## 4. 错误处理

CLI 输出不暴露 HTTP 状态码，统一按响应体中的 `success` 字段判断：

| 条件 | 策略 |
|------|------|
| `success === false` 且 `msg` 含"证书密钥"等临时错误 | 静默等待 2 秒后自动重试 1 次，仍失败则展示 `errorCode`、`msg`/`resultMsg`、`traceId` |
| `success === false` 且 `msg` 含"版本过旧"或 CLI 退出码非 0 | 不重试，友好提示"服务不可用，可能是 CLI 版本过旧"，询问用户是否升级 CLI |
| CLI 执行超时或网络错误 | 最多重试 2 次 |

所有失败均提取 `traceId` 展示给用户。

## 5. 注意事项

- 执行前向用户展示即将运行的命令
- 参数不确定时先向用户确认