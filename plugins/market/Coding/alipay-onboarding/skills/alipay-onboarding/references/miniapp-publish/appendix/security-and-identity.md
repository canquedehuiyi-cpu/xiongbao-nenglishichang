# 接口加签与身份交互

本附录从业务侧详述接口加签的二步交互流程、身份授权说明、密钥安全红线。skill 是接口加签流程的主动驱动者：skill 调用 `config keysign` CLI、渲染二维码给用户、轮询确认结果，但不生成密钥、不接收私钥。

## 1. 接口加签二步交互

接口加签是独立能力(复用 developercore createKeyConfirmPage 核身链),与 modifyBaseInfo 等管理操作无前置依赖(加签非"管理操作总开关",modifyBaseInfo 不强制先加签)。skill 不代用户生成密钥,必须先引导用户前往 https://opendocs.alipay.com/common/02kipk 用官方密钥工具生成 RSA2 密钥对。**skill 必须等用户提供应用公钥(publicKey)后才调 config keysign;未提供 publicKey 时停止并等待用户输入,严禁空 publicKey 调 configKeySign(否则 CLI_KEY_SIGN_FAIL: publicKey 不能为空)**。一步生成核身页 + 扫码核身(写密钥由核身页扫码后平台自完成,无独立 CONFIRM 步)。

### 生成核身页(等 publicKey 后调 configKeySign)

用户提供自生成的应用公钥(publicKey),skill 调用 `config keysign`(action=CREATE_CONFIRM_PAGE)返回：
- `keyConfirmToken`：核身会话标识
- `confirmPageUrl`：核身页 URL
- `qrCodeUrl`：二维码 URL

skill 把 qrCodeUrl 渲染给用户（终端二维码或 URL 链接），暂停并等待用户用支付宝 App 扫码核身。

### 扫码核身(写密钥由平台自完成) + skill 验证

用户用支付宝 App 扫码后,核身页内平台移动网关自完成公钥写入(无独立 CONFIRM 步),skill 端验证:

**密钥写入成功判断(bug Dima 2026091800119206812)**：
- 用户告知扫码完成后,skill 调 `alipay-cli miniapp app detail --app-id <appId> --include-security-keys true` 查详情(**必须加 `--include-security-keys true`**，否则 securityKeys 段为 null/占位 `available=false`，`fillSecurityKeysFromOpencore` 不执行,无法判断密钥状态)
- MCP 兜底: `alipay-cli mcp call miniapprelease.queryMiniAppDetail --data '{"appId":"<appId>","includeSecurityKeys":true}'`
- 返回 `securityKeys` 段：
  - `available=true`(dev 套壳层用 opencore SecurityManageServiceClient.querySecurityByAppId 填充,minicenter 本身 available=false)
  - `hasKeys=true` → **密钥已设置成功**
  - `hasKeys=false` → 密钥未设置(扫码未完成或失败)
  - `signType` = 如 "RSA2"
  - `publicKeyFingerprint` = partnerPublicKey 前 32 字符(skill 可与 configKeySign 时传入的 publicKey 前缀比对,确认写入的是用户上传的公钥)
  - `storedPublicKey` = 服务端存储的完整应用公钥原文
- 读写同源验证:addSign 写 partnerPublicKey → querySecurity 查 partnerPublicKey,同一 opencore 平台;skill 比对 `storedPublicKey` 或 `publicKeyFingerprint` 与用户传入的 `publicKey` 一致即确认密钥写入成功
- 如果查询结果 `hasKeys=true` 且 `publicKeyFingerprint` 与用户传入公钥前缀匹配 → ✅ 加签配置成功；否则提示重试或检查

configKeySign 仅生成核身页一步;写密钥由核身页扫码后平台移动网关自完成,无独立 CONFIRM 步(原 step2 CONFIRM/keyConfirmToken 已移除)。

### skill tool output 示例（Demo env3）

```
> alipay-cli miniapp config keysign
⚠️ 接口加签是管理操作的总开关,须先完成才能进行基础信息配置等。
【第一步】确认密钥对
请先用官方密钥工具自行生成 RSA2 密钥对:
https://opendocs.alipay.com/common/02kipk
(密钥对须由你本人用官方工具生成,skill 不代生成)
已有密钥对?输入 yes 继续,输入 no 查看下载指引
> yes
【第二步】上传应用公钥
请粘贴你的应用公钥(以 -----BEGIN 开头):
> -----BEGIN PUBLIC KEY-----
> ……(粘贴)
> -----END PUBLIC KEY-----
⏳ 正在生成公钥确认页…
★ human-only:请用支付宝 App 扫码核身,确认后公钥即完成配置
   [skill 渲染二维码给用户]
```

```
⏳ 等待核身确认中……
✅ 接口加签配置成功
   算法:RSA2
   APPID:2024090100123456
⏳ 正在验证加签通路…
✅ 加签验证通过,可以开始配置了
```

## 2. 身份与授权说明

- skill 在请求里携带 OAuth 凭证（经 CLI 透传），授权 scope 为 `miniapp:all`
- 支持开发者自己操作与代操作（C 代 B）两种模式
- 代操作时 skill 在请求里携带被代理人标识（经 facade 透传），服务端自动判定代操作语义，skill 不感知也不对用户显式暴露
- 权限校验失败时 skill 收到错误并返回给用户，由用户决定下一步

## 3. 密钥安全红线

<important>
**公钥私钥属于敏感信息，严格遵守以下规范：**

1. **禁止生成或建议生成密钥**：严禁向用户表示可 "帮助生成公钥/密钥对"，严禁提供 `openssl` / `ssh-keygen` 等密钥生成代码、命令、脚本
2. **禁止接收私钥**：严禁请求、接收、存储或处理用户的私钥信息
3. **仅接受公钥输入**：第一步入参 `publicKey` 由用户明确输入；skill 不生成、不推断、不改写
4. **引导官方工具**：skill 必须先引导用户前往 https://opendocs.alipay.com/common/02kipk 使用官方密钥生成工具
5. **标准话术**："请前往支付宝开放平台密钥生成工具（https://opendocs.alipay.com/common/02kipk）下载并使用官方工具生成应用公私钥对，生成后将应用公钥提供给我继续后续流程。**私钥请妥善保管，切勿泄露给任何人。**"
</important>
