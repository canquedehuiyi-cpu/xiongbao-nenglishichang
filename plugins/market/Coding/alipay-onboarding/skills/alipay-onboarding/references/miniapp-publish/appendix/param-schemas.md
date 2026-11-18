# 接口传参 schema 与示例（miniapprelease.*）

本附录按 `developerportal MiniAppCliLifecycleMcpFacade` 的 30 个方法,逐个给出:
- 入参字段表（必填/选填/默认/格式）
- 每种 `action` / `buildMode` / `cancel` 变体的一份示例 JSON，可直接用于 `alipay-cli mcp call miniapprelease.<method> --data '<json>'`

字段校验以 **minicenter `MiniAppCliLifecycleFacadeImpl` 实际代码**为准（dev 为套壳透传，除 `configKeySign`、`manageExperience` 外不做字段级校验）。无 JSR-303 注解，全部在 impl 里用 `StringUtils.isBlank()` 命令式校验。

---

## 公共约定

### identityContext（CLI 不传）

身份上下文**不在 dev request DTO 中**，由 dev `McpIdentityFilter` 写 ThreadLocal，impl body 读后经 `IdentityContextConverter` 转成 minicenter `IdentityContext` 注入。CLI 调用方无需也无法传入。

dev→minicenter 字段映射：

| dev 字段 | minicenter 字段 |
|---|---|
| `uid` | `uid` |
| `operatorUid` | `operatorUid` |
| `authUid` | `authUid` |
| `oid` | `principalOid` |
| `pid` | `operatorPid` |

### 公共字段（继承自 `AbstractMiniAppCliRequest`）

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `appId` | String | 视方法 | 小程序 appId（各方法表标注；`createMiniApp` 不传，自动生成） |
| `isvAppId` | String | 选填 | ISV 影子应用 appId（C 代 B 透传；`createMiniApp` 有值走 `ISV_MODE`，空走 `SELF_MODE`） |
| `invokePid` | String | 选填 | 调用方 PID（类目查询按 PID 过滤时用） |
| `sourceChannel` | String | 选填 | 渠道来源标，默认 `"CLI"`（仅 `createMiniApp` 打标） |

### 全局默认值

| 默认 | 值 | 用在 |
|---|---|---|
| sourceChannel | `CLI` | createMiniApp |
| appSlogan | `小程序简介待完善` | createMiniApp（简介空时补） |
| appDesc | `小程序正在开发中，详细介绍待完善。` | createMiniApp（描述空时补） |
| bundleId | `com.alipay.alipaywallet` | 多方法（支付宝端） |
| version（CODE/SOURCE 构建） | `0.0.1` | uploadBuild CODE/SOURCE |
| mainUrl（CODE/SOURCE 构建） | `/index.html` | uploadBuild CODE |

### 不可逆操作 confirmToken（全局说明）

不可逆操作（`publishOnline` / `publishGray` / `offlineVersion` / `rollbackVersion` / `deleteMiniApp` / `deleteVersion` / `icpRevoke`）的 `confirmToken` 字段**被服务端完全忽略** —— 单步直接执行，无两步确认流程。

- `DangerousOpConfirmResult.confirmRequired` 恒为 `false`
- `DangerousOpConfirmer`（ZCache 两步实现）从未被注入或调用（死代码）
- skill 层用法：skill 以温馨提示向用户说明影响并确认「yes」后**单次直接调用 facade**，传不传 `confirmToken` 无影响

### 错误码常量

| 值 | 含义 |
|---|---|
| `CLI_PARAM_INVALID` | 参数无效 |
| `CLI_AUTH_FAIL` | 鉴权失败 |
| `CLI_DANGEROUS_CONFIRM` | 危险操作确认失败 |
| `CLI_KEY_SIGN_FAIL` | 加签核身失败 |
| `CLI_INTERNAL_ERROR` | 内部异常 |
| `CLI_NOT_SUPPORTED` | 不支持（如 `configKeySign` 在 minicenter 端、`icpSubmit` MCP 结构化提交未接入三期） |
| `CLI_STATE_CONFLICT` | 状态机冲突 |

---

## action / buildMode 枚举速查

| 方法 | 字段 | 枚举值 | 默认 |
|---|---|---|---|
| `uploadBuild` | `buildMode` | `SOURCE_AFTS` / `TEMPLATE` / `SOURCE`(兜底) | `SOURCE_AFTS` |
| `auditApply` | `action` | `SUBMIT` / `QUERY` / `CANCEL` / `WITHDRAW` | `SUBMIT` |
| `manageExperience` | `action` | `CREATE` / `QUERY` / `CANCEL` | 必填 |
| `managePrivacy` | `action` | `APPLY` / `QUERY` / `CANCEL` | 必填 |
| `queryCategory` | `action` | `QUERY_TREE` / `REQUIRE_QUERY` / `GET_EDIT_URL` | `QUERY_TREE` |
| `queryVersionList` | `action` | `LIST_QUERY` / `DETAIL_QUERY` | `LIST_QUERY` |
| `manageSafeDomain` | `action` | `ADD` / `DELETE` / `QUERY` | 必填 |
| `publishGray` | `cancel` | `true` / `false` | `false` |
| `configKeySign` | `action` | `CREATE_CONFIRM_PAGE` | 必填 |

---

## 1. createMiniApp

`miniapprelease.createMiniApp`

| 字段 | 类型 | 必填 | 默认 | 说明 |
|---|---|---|---|---|
| `appName` | String | **必填** | — | 小程序名称（3-30 字符） |
| `appEnglishName` | String | 选填 | null | 英文名 |
| `appSlogan` | String | 选填 | `小程序简介待完善` | 简介 |
| `appLogo` | String | 选填 | null | logo URL（非 http 时按 AFTS fileKey 处理） |
| `categoryIds` | String | 选填 | null | 类目 ID 列表，逗号分隔；创建不依赖类目 |
| `serviceTel` | String | 选填 | null | 客服电话 |
| `serviceMail` | String | 选填 | null | 客服邮箱 |
| `appDesc` | String | 选填 | `小程序正在开发中，详细介绍待完善。` | 描述 |
| `sourceChannel` | String | 选填 | `CLI` | 渠道来源标 |

```json
{"request":{
  "appName": "茶语小程序",
  "appEnglishName": "ChayuMiniApp",
  "appSlogan": "茶文化社区",
  "appDesc": "茶文化爱好者社区小程序",
  "categoryIds": "12,13",
  "serviceTel": "0571-12345678",
  "serviceMail": "service@chayu.com",
  "appLogo": "https://oss.example.com/logo.png",
  "sourceChannel": "CLI"
}}
```

C 代 B 创建（加 `isvAppId`）：

```json
{"request":{
  "appName": "商家小程序",
  "isvAppId": "2021000000000001",
  "sourceChannel": "CLI"
}}
```

---

## 2. configKeySign

`miniapprelease.configKeySign`

已在 developerportal 接口加签中实现;不走 minicenter。

| 字段 | 类型 | 必填 | 默认 | 说明 |
|---|---|---|---|---|
| `action` | String | **必填** | — | 必须为 `CREATE_CONFIRM_PAGE`（仅支持生成核身页一步） |
| `appId` | String | **必填** | — | 小程序 appId |
| `publicKey` | String | **必填** | — | RSA2 应用公钥（用户用官方工具自生成，skill 不代生成） |
| `signType` | String | 选填 | `RSA2` | 签名类型 |

写密钥由核身页扫码后平台自动完成，无独立确认步。`keyConfirmToken` 仅出现在返回中，入参不消费。

```json
{"request":{
  "appId": "2021000000000002",
  "action": "CREATE_CONFIRM_PAGE",
  "publicKey": "MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEA...",
  "signType": "RSA2"
}}
```

---

## 3. uploadBuild

`miniapprelease.uploadBuild` —— **2 种 buildMode**(CODE 已删除)

| 公共字段 | 必填 | 默认 |
|---|---|---|
| `appId` | **必填** | — |
| `buildMode` | 选填 | `SOURCE_AFTS` |
| `bundleId` | 选填 | `com.alipay.alipaywallet` |
| `version` | **必填** | — |
| `isvAppId` | 选填 | null |

### 3a. SOURCE_AFTS（默认⭐推荐）

| 字段 | 必填 |
|---|---|
| `packageUrl` | **必填**（AFTS fileKey，非 http URL） |

服务端：fileKey → `downloadFile` → zip→tar → pkgcore → `doBuildByCode`。自动 strip macOS 元数据。

```json
{"request":{
  "appId": "2021000000000002",
  "buildMode": "SOURCE_AFTS",
  "packageUrl": "uOjcQbVtA7IAAAAAQDAAAAgAnLS4AAJr",
  "version": "1.0.0"
}}
```

### 3b. TEMPLATE（模板实例化，已支持）

模板构建已端到端支持:从模板实例化构建得到新版本;默认返回 O 站隐私管理页 URL。

| 字段 | 必填 | 说明 |
|---|---|---|
| `appId` | **必填** | 实例化到哪个小程序 |
| `templateId` | **必填** | 实例化自哪个模板 |
| `templateVersion` | 选填(建议传) | 指定所用模板版本;不传走"模板存在上架版本"判定,无则 `MINI_APP_PACKAGE_INFO_NOT_EXIST` |
| `version` | **必填** | 实例化生成的新版本号(目标小程序的新版本,非模板版本) |
| `extJson` | 选填 | 模板扩展参数 JSON(ext.json),被 `buildExtJson` 处理 |
| `bundleId` | 选填 | 端标识,默认 `com.alipay.alipaywallet`(底层 DTO 字段是小写 `bundleid`,facade 已转换) |
| `isvAppId` | C代B/托管模式必填 | 三方鉴权:校验小程序是否授权给该三方;自建模式 `skipAuthCheck` 跳过 |

```json
{"request":{
  "appId": "2021000000000002",
  "buildMode": "TEMPLATE",
  "templateId": "TPL_2021000000000001",
  "templateVersion": "1.2.0",
  "version": "1.0.0",
  "extJson": "{\"theme\":\"blue\"}"
}}
```

C代B(操作员代主账号创建)加 `isvAppId`:

```json
{"request":{
  "appId": "2021000000000002",
  "buildMode": "TEMPLATE",
  "templateId": "TPL_2021000000000001",
  "version": "1.0.0",
  "isvAppId": "2021000000000001"
}}
```

### 3c. SOURCE（小工程兜底，base64 over RPC）

| 字段 | 必填 |
|---|---|
| `sourceZipBase64` | **必填** |

```json
{"request":{
  "appId": "2021000000000002",
  "buildMode": "SOURCE",
  "sourceZipBase64": "UEsDBAoAAAAAA...",
  "version": "1.0.0"
}}
```

### ~~CODE（已删除）~~

CODE 模式已删除(bug Dima 2026092000119259666):fileKey 非 http URL → SSRF `PROTOCOL_NOT_ALLOWED`。用 `source_afts` 替代。

---

## 4. queryBuildStatus

`miniapprelease.queryBuildStatus`

| 字段 | 必填 | 默认 | 说明 |
|---|---|---|---|
| `appId` | **必填** | — | — |
| `packageId` | **必填** | — | 构建包 ID，取自 `uploadBuild` 返回 |
| `version` | **必填** | — | 上传时的版本号,取自 `uploadBuild` 的 version;空会报 `CLI_PARAM_INVALID` |
| `bundleId` | 选填 | null | — |

```json
{"request":{
  "appId": "2021000000000002",
  "version": "1.0.0",
  "packageId": "PKG_20260914_001"
}}
```

---

## 5. auditApply

`miniapprelease.auditApply`

| 字段 | 必填 | 默认 | 说明 |
|---|---|---|---|
| `appId` | **必填** | — | — |
| `action` | 选填 | `SUBMIT` | `SUBMIT` / `QUERY` / `CANCEL` / `WITHDRAW`；null 或非 QUERY/CANCEL/WITHDRAW 均走 SUBMIT |
| `version` | SUBMIT 选填 / QUERY 选填 / CANCEL/WITHDRAW 必填 | SUBMIT 空→服务端查最新开发中版本 | 版本号 |
| `bundleId` | 选填 | `com.alipay.alipaywallet` | — |
| `auditNote` | 选填 | null | 提审备注/版本描述（仅 SUBMIT 消费） |
| `auditParams` | 选填 | null | 提审额外参数 JSON |
| `cancel` / `cancelReason` | **废弃** | — | 旧字段;改用 action=CANCEL/WITHDRAW 实现撤审/退回,不再消费 |

### 5a. SUBMIT（默认，提审）

```json
{"request":{
  "appId": "2021000000000002",
  "action": "SUBMIT",
  "version": "1.0.0",
  "auditNote": "首版:菜单浏览+点单+自取核销"
}}
```

version 省略时服务端自动取最新开发中版本：

```json
{"request":{
  "appId": "2021000000000002",
  "auditNote": "首版提审"
}}
```

### 5b. QUERY（查审核状态）

```json
{"request":{
  "appId": "2021000000000002",
  "action": "QUERY"
}}
```

```json
{"request":{
  "appId": "2021000000000002",
  "action": "QUERY",
  "version": "1.0.0"
}}
```

### 5c. CANCEL（撤审）

```json
{"request":{
  "appId": "2021000000000002",
  "action": "CANCEL",
  "version": "1.0.0"
}}
```

撤回审核中版本,返 AuditApplyResult(auditStatus=CANCELED)。非不可逆操作,skill 轻量提示。

### 5d. WITHDRAW（退回开发）

```json
{"request":{
  "appId": "2021000000000002",
  "action": "WITHDRAW",
  "version": "1.0.0"
}}
```

审核中版本退回开发,返 AuditApplyResult(auditStatus=WITHDRAWN)。

---

## 6. publishOnline

`miniapprelease.publishOnline` —— 不可逆操作（`confirmToken` 忽略，单步直执）

| 字段 | 必填 | 默认 | 说明 |
|---|---|---|---|
| `appId` | **必填** | — | — |
| `version` | **必填** | — | 须已审核通过 |
| `bundleId` | 选填 | `com.alipay.alipaywallet` | — |
| `confirmToken` | **忽略** | — | 字段保留但服务端不读 |

```json
{"request":{
  "appId": "2021000000000002",
  "version": "1.0.0"
}}
```

---

## 7. publishGray

`miniapprelease.publishGray` —— 不可逆操作（`confirmToken` 忽略，单步直执）

| 字段 | 必填 | 默认 | 说明 |
|---|---|---|---|
| `appId` | **必填** | — | — |
| `version` | **必填** | — | 须已审核通过 |
| `cancel` | 选填 | `false` | `true`=取消灰度回正式版；`false`=发起/调整灰度 |
| `grayStrategy` | `cancel=false` **必填**；`cancel=true` 可空 | — | 裸百分比如 `"10"`=10%；或维度前缀 `p10`/`d20`/`a30`（用户/设备/appId）；裸数字自动归一化为 `p` 前缀 |
| `bundleId` | 选填 | `com.alipay.alipaywallet` | — |
| `confirmToken` | **忽略** | — | minicenter 转发前显式 clear |

### 7a. cancel=false（发起/调整灰度）

裸比例：

```json
{"request":{
  "appId": "2021000000000002",
  "version": "1.0.0",
  "cancel": false,
  "grayStrategy": "10"
}}
```

维度策略（设备 20%）：

```json
{"request":{
  "appId": "2021000000000002",
  "version": "1.0.0",
  "cancel": false,
  "grayStrategy": "d20"
}}
```

### 7b. cancel=true（取消灰度）

```json
{"request":{
  "appId": "2021000000000002",
  "version": "1.0.0",
  "cancel": true
}}
```

---

## 8. manageExperience

`miniapprelease.manageExperience`

dev impl 特殊：CREATE action 30s 幂等缓存（同 appId+version 30s 内直接返 `status="BUILDING"`），RPC 超时 3s→6s。

| 字段 | 必填 | 默认 | 说明 |
|---|---|---|---|
| `appId` | **必填** | — | — |
| `action` | **必填** | — | `CREATE` / `QUERY` / `CANCEL`；空或不匹配 → `CLI_PARAM_INVALID` |
| `version` | CREATE/CANCEL **必填**（下游依赖）/ QUERY 可空 | QUERY 空时自动取最新版本 | QUERY 显式传入时严格使用传入版本，不调用最新版本查询 |
| `bundleId` | 选填 | `com.alipay.alipaywallet` | — |

### 8a. CREATE

```json
{"request":{
  "appId": "2021000000000002",
  "action": "CREATE",
  "version": "1.0.0"
}}
```

### 8b. QUERY

```json
{"request":{
  "appId": "2021000000000002",
  "action": "QUERY"
}}
```

### 8c. CANCEL

```json
{"request":{
  "appId": "2021000000000002",
  "action": "CANCEL",
  "version": "1.0.0"
}}
```

---

## 9. managePrivacy

`miniapprelease.managePrivacy` —— 隐私政策管理;APPLY 默认返回隐私管理页链接,CANCEL 已支持

| 字段 | 必填 | 默认 | 说明 |
|---|---|---|---|
| `appId` | **必填** | — | — |
| `action` | **必填** | — | `APPLY` / `QUERY` / `CANCEL` |
| `bundleId` | 选填 | `com.alipay.alipaywallet` | APPLY 拼 O 站隐私管理页 URL 用 |
| `storageLocation` / `replyCycle` 等 | 选填 | — | APPLY MCP 模式（mcpMode=true）消费；URL 模式（mcpMode=false）不消费 |

> APPLY 返回 JSON 含 `mcpMode` 开关。`mcpMode=false`（默认）→ 返隐私管理页 URL,skill 渲染给用户浏览器操作;`mcpMode=true` → CLI 直接提交,返 message。skill 读 mcpMode 做分支。CANCEL/QUERY 不受开关影响。

### 9a. APPLY

```json
{"request":{
  "appId": "2021000000000002",
  "action": "APPLY"
}}
```

返回（mcpMode=false，开关关闭）:
```json
{"mcpMode":false,"url":"https://open.alipay.com/develop/privacy/mini/privacyManagement?appId=2021000000000002&bundleId=com.alipay.alipaywallet&edit=true&source=draft&usePrivacyType=template&from=","tips":"请在浏览器打开以下链接完成隐私政策配置"}
```

返回（mcpMode=true，开关打开）:
```json
{"mcpMode":true,"message":"隐私政策已提交"}
```

### 9b. QUERY（查在线隐私版本）

```json
{"request":{
  "appId": "2021000000000002",
  "action": "QUERY"
}}
```

### 9c. CANCEL（撤销隐私政策）

```json
{"request":{
  "appId": "2021000000000002",
  "action": "CANCEL"
}}
```

撤销生效隐私版,返"隐私政策已撤销"。可重新创建。

---

## 10. queryCategory

`miniapprelease.queryCategory`

| 字段 | 必填 | 默认 | 说明 |
|---|---|---|---|
| `action` | 选填 | `QUERY_TREE` | `QUERY_TREE` / `REQUIRE_QUERY` / `GET_EDIT_URL` |
| `appId` | QUERY_TREE 不用 / REQUIRE_QUERY 选填 / GET_EDIT_URL **必填** | — | REQUIRE_QUERY：传→查已选类目资质；不传→按 `invokePid` 查可选类目 |
| `invokePid` | 选填 | — | REQUIRE_QUERY 无 appId 时按 invokePid 查 |
| `filter` | 选填 | `false` | true=只返当前 PID 可申请类目（仅 QUERY_TREE） |
| `bundleId` | 选填 | `com.alipay.alipaywallet` | GET_EDIT_URL 拼 O 站编辑页 URL |

### 10a. QUERY_TREE（默认，查类目树）

```json
{"request":{
  "appId": "2021000000000002",
  "action": "QUERY_TREE",
  "filter": false
}}
```

### 10b. REQUIRE_QUERY（查类目要求/可选类目）

有 appId（查已选类目资质）：

```json
{"request":{
  "appId": "2021000000000002",
  "action": "REQUIRE_QUERY"
}}
```

无 appId（按 invokePid 查可选类目）：

```json
{"request":{
  "invokePid": "2088000000000001",
  "action": "REQUIRE_QUERY"
}}
```

### 10c. GET_EDIT_URL（返 O 站类目/基础信息编辑页 URL，二期起 skill 不再引导）

```json
{"request":{
  "appId": "2021000000000002",
  "action": "GET_EDIT_URL"
}}
```

> 二期去页面化：类目设置/基础信息修改改走 `modifyBaseInfo`（带 `categoryIds` 直存），skill 不再调用 GET_EDIT_URL 引导用户去页面。本 action 保留仅为平台侧能力完整，仍可返回编辑页 URL。

---

## 11. modifyBaseInfo

`miniapprelease.modifyBaseInfo` —— 无 action 分支，仅修改；查询走 `queryMiniAppDetail`。

| 字段 | 必填 | 默认 | 说明 |
|---|---|---|---|
| `appId` | **必填** | — | — |
| `appName` | 改名时必传 | — | 改名次数限每自然年 2 次,先 `queryNameModifyCount` 查剩余 |
| `appEnglishName` | 选填 | null | — |
| `appSlogan` | 选填 | null | — |
| `appLogo` | 选填 | null | logo URL（非 http 按 AFTS fileKey） |
| `categoryIds` | 选填 | null | 类目 ID 列表，逗号分隔 |
| `appDesc` | 选填 | null | — |
| `serviceTel` | 选填 | null | — |
| `serviceMail` | 选填 | null | — |
| `incrementalUpdate` | 选填 | `null`（false=全量覆盖；true=未传字段从当前详情补齐，防 minicore 全量覆盖清空） | — |

增量改名：

```json
{"request":{
  "appId": "2021000000000002",
  "appName": "茶语小程序新名",
  "incrementalUpdate": true
}}
```

全量修改：

```json
{"request":{
  "appId": "2021000000000002",
  "appName": "茶语小程序",
  "appSlogan": "茶文化社区",
  "appDesc": "茶文化爱好者社区",
  "categoryIds": "12,13",
  "serviceTel": "0571-12345678",
  "serviceMail": "service@chayu.com",
  "appLogo": "https://oss.example.com/logo.png",
  "incrementalUpdate": false
}}
```

---

## 12. queryVersionList

`miniapprelease.queryVersionList`

| 字段 | 必填 | 默认 | 说明 |
|---|---|---|---|
| `appId` | **必填** | — | — |
| `action` | 选填 | `LIST_QUERY` | `LIST_QUERY` / `DETAIL_QUERY` |
| `version` | DETAIL_QUERY **必填** / LIST_QUERY 选填 | — | DETAIL_QUERY 指定查哪个版本 |
| `pageNo` | LIST_QUERY 选填 | `1` | null / <1 → `CLI_PARAM_INVALID` |
| `pageSize` | LIST_QUERY 选填 | `20` | null / <1 → `CLI_PARAM_INVALID` |
| `bundleId` | 选填 | `com.alipay.alipaywallet` | — |

### 12a. LIST_QUERY（默认，版本列表）

```json
{"request":{
  "appId": "2021000000000002",
  "action": "LIST_QUERY",
  "pageNo": 1,
  "pageSize": 20
}}
```

### 12b. DETAIL_QUERY（版本详情）

```json
{"request":{
  "appId": "2021000000000002",
  "action": "DETAIL_QUERY",
  "version": "1.0.0"
}}
```

---

## 13. queryNameModifyCount

`miniapprelease.queryNameModifyCount` —— **入参裸 `String appId`，无 request 对象**

| 参数 | 必填 | 说明 |
|---|---|---|
| `appId` | **必填** | 小程序 appId |

MCP 兜底 JSON 用扁平入参（**不要套 `{request:{...}}` 信封**）：

```json
"2021000000000002"
```

---

## 14. manageSafeDomain

`miniapprelease.manageSafeDomain`

| 字段 | 必填 | 默认 | 说明 |
|---|---|---|---|
| `appId` | **必填** | — | — |
| `action` | **必填** | — | `ADD` / `DELETE` / `QUERY` |
| `safeDomain` | ADD/DELETE **必填** / QUERY 可空 | — | 域名，如 `api.example.com` |

### 14a. ADD

```json
{"request":{
  "appId": "2021000000000002",
  "action": "ADD",
  "safeDomain": "api.chayu-moment.com"
}}
```

### 14b. DELETE

```json
{"request":{
  "appId": "2021000000000002",
  "action": "DELETE",
  "safeDomain": "api.chayu-moment.com"
}}
```

### 14c. QUERY

```json
{"request":{
  "appId": "2021000000000002",
  "action": "QUERY"
}}
```

---

## 15. deleteMiniApp

`miniapprelease.deleteMiniApp` —— 不可逆操作;真实删除

| 字段 | 必填 | 默认 | 说明 |
|---|---|---|---|
| `appId` | **必填** | — | — |
| `confirmToken` | **忽略** | — | 字段保留但服务端不读 |

**当前行为**：真实删除小程序实例。
PreCheck 约束（PreCheckOrchestrator.preCheckDeleteMiniApp）：已上架 → `CLI_STATE_CONFLICT`「请先下架」；存在体验版 → `CLI_STATE_CONFLICT`「请先取消体验版」；类型/存在性校验。

```json
{"request":{
  "appId": "2021000000000002"
}}
```

---

## 16. offlineVersion

`miniapprelease.offlineVersion` —— 不可逆操作（`confirmToken` 忽略）

| 字段 | 必填 | 默认 | 说明 |
|---|---|---|---|
| `appId` | **必填** | — | — |
| `version` | **必填** | — | 要下架的版本号 |
| `bundleId` | 选填 | `com.alipay.alipaywallet` | — |
| `confirmToken` | **忽略** | — | — |

```json
{"request":{
  "appId": "2021000000000002",
  "version": "1.0.0"
}}
```

---

## 17. rollbackVersion

`miniapprelease.rollbackVersion` —— 不可逆操作（`confirmToken` 忽略）；**复用 `OfflineVersionRequest`**（与 offlineVersion 共用 DTO）

| 字段 | 必填 | 默认 | 说明 |
|---|---|---|---|
| `appId` | **必填** | — | — |
| `version` | **必填** | — | **当前已上架版本号**(RELEASE 状态),不是回滚目标版本;服务端据此查到该版本并内部找已下架的前一版本实现回滚切换;传非 RELEASE 版本会 `CAN_NOT_ROLLBACK_WITHOUT_ONLINE` |
| `bundleId` | 选填 | `com.alipay.alipaywallet` | — |
| `confirmToken` | **忽略** | — | — |

> ⚠️ skill 调用前必须先 `version ls` 查当前 RELEASE 版本号用作入参;回滚目标由用户从已下架版本中自行选择(skill 展示 + 询问),但 `version` 参数传的是**当前上线版本号**不是目标版本号。

```json
{"request":{
  "appId": "2021000000000002",
  "version": "1.0.0"
}}
```

---

## 18. queryMiniAppList

`miniapprelease.queryMiniAppList`

dev impl 特殊：`request == null` 不报错，默认 `new QueryMiniAppListRequest()`（pageNo=1/pageSize=20），因为 MCP 网关会把空入参映射成 null。

| 字段 | 必填 | 默认 | 说明 |
|---|---|---|---|
| `appName` | 选填 | null | 模糊匹配名称（不区分大小写） |
| `appId` | 选填 | null | 精确过滤 |
| `appStatus` | 选填 | null | 状态过滤，如 `ONLINE` / `DEVELOPING` |
| `pageNo` | 选填 | `1` | — |
| `pageSize` | 选填 | `20` | — |

```json
{"request":{
  "appName": "茶",
  "pageNo": 1,
  "pageSize": 20,
  "appStatus": "ONLINE"
}}
```

---

## 19. queryMiniAppDetail

`miniapprelease.queryMiniAppDetail`

| 字段 | 必填 | 默认 | 说明 |
|---|---|---|---|
| `appId` | **必填** | — | — |
| `bundleId` | 选填 | `com.alipay.alipaywallet` | — |
| `includeBasicInfo` | 选填 | `true` | 基础信息 |
| `includeVersions` | 选填 | `true` | 版本列表 |
| `includePrivacyStatus` | 选填 | `true` | 隐私状态 |
| `includeExperience` | 选填 | `false` | 体验版状态 |
| `includeSafeDomain` | 选填 | `true` | 域名白名单 |
| `includeSecurityKeys` | 选填 | `false` | 密钥信息(须传 true 才填充) |
| `includeServiceConfig` | 选填 | `false` | 服务配置(须传 true 才填充;含 gatewayUrl/encryptType/openidEnabled/msgSubscriptionList) |
| `versionLimit` | 选填 | `5` | 版本列表最多返 N 条 |

全量查询：

```json
{"request":{
  "appId": "2021000000000002",
  "includeBasicInfo": true,
  "includeVersions": true,
  "includePrivacyStatus": true,
  "includeExperience": true,
  "includeSafeDomain": true,
  "versionLimit": 10
}}
```

轻量查询（仅基础信息）：

```json
{"request":{
  "appId": "2021000000000002",
  "includeBasicInfo": true,
  "includeVersions": false,
  "includePrivacyStatus": false,
  "includeSafeDomain": false
}}
```

---

## 20. icpSubmit

`miniapprelease.icpSubmit` —— 备案提交。返回 JSON 含 `mcpMode` 开关;mcpMode=false 返备案页 URL(用户浏览器人工填);mcpMode=true 走 CLI 结构化提交(当前暂未接入)。

| 字段 | 必填 | 默认 | 说明 |
|---|---|---|---|
| `appId` | **必填** | — | 哪个小程序 |
| `entityType` | 选填 | null | 主体类型(MCP 模式消费) |
| `legalPersonName` / `legalPersonIdCard` / `legalPersonPhone` | 选填 | null | 负责人信息(MCP 模式消费) |
| `mainCategory` | 选填 | null | 主营类目(MCP 模式消费) |
| `provinceId` | 选填 | null | 省份(MCP 模式消费) |

返回（mcpMode=false，开关关闭）:
```json
{"mcpMode":false,"url":"https://open.alipay.com/platform/portal/icp.htm?appId=2021000000000002","tips":"请在浏览器打开以下链接完成备案材料提交(需上传材料 + 人脸核验 + 工信部短信验证)"}
```

返回（mcpMode=true，开关打开）:
```json
{"mcpMode":true,"message":"MCP 结构化备案提交暂未接入,请先在开放平台管理台人工备案"}
```

```json
{"request":{
  "appId": "2021000000000002"
}}
```

---

## 21. icpStatus

`miniapprelease.icpStatus` —— 查询小程序备案状态。

| 字段 | 必填 | 说明 |
|---|---|---|
| `appId` | **必填** | 哪个小程序 |

```json
{"request":{
  "appId": "2021000000000002"
}}
```

返回:备案状态 JSON。主要字段:
- `registrationStatus`:备案状态(`INITIAL`=未备案 / `AUDITING`=审核中 / `SUCCESS`=已通过 / `FAIL`=审核未通过 等);**skill 以此字段为主判断备案进度**
- `registrationSubStatus`:监管审核阶段描述(可能为空或 "尚未达到监管审核阶段";**仅供辅助参考,与 registrationStatus 可能存在不一致,不应单独用于判断**)
- `mittResultCode`/`mittResultMsg`:工信部备案结果描述(可能为空)
- `registrationTighten`:是否受限(受限于未备案 → 上架受限发布)

---

## 22. icpRevoke

`miniapprelease.icpRevoke` —— 撤销备案申请,不可逆操作(skill 先温馨提示征求 yes 后执行)。

| 字段 | 必填 | 说明 |
|---|---|---|
| `appId` | **必填** | 哪个小程序 |

```json
{"request":{
  "appId": "2021000000000002"
}}
```

返回:撤销成功。

---

## 23. deleteVersion

`miniapprelease.deleteVersion` —— 删除开发中版本,不可逆操作(skill 先温馨提示征求 yes 后执行)。

| 字段 | 必填 | 默认 | 说明 |
|---|---|---|---|
| `appId` | **必填** | — | 哪个小程序 |
| `version` | **必填** | — | 待删除的开发中版本号 |
| `bundleId` | 选填 | `com.alipay.alipaywallet` | 端标识 |

```json
{"request":{
  "appId": "2021000000000002",
  "version": "1.0.0"
}}
```

返回:删除成功。

---

## 24. queryPluginList

`miniapprelease.queryPluginList` —— 查询当前小程序已订购的插件列表。

| 字段 | 必填 | 说明 |
|---|---|---|
| `appId` | **必填** | 哪个小程序 |

```json
{"request":{
  "appId": "2021000000000002"
}}
```

返回:已订购插件列表 JSON,无插件返回 `[]`。

---

## 25. queryCallableProducts

`miniapprelease.queryCallableProducts` —— 查询当前小程序可调用的产品/能力列表,支持按类目过滤 + 分页。

| 字段 | 必填 | 默认 | 说明 |
|---|---|---|---|
| `appId` | **必填** | — | 哪个小程序 |
| `category` | 选填 | null | 类目过滤 |
| `pageNo` | 选填 | `1` | 页码,从 1 开始 |
| `pageSize` | 选填 | `20` | 每页数量 |

```json
{"request":{
  "appId": "2021000000000002",
  "category": "支付",
  "pageNo": 1,
  "pageSize": 20
}}
```

返回:可调用产品列表 JSON,无内容返回 `[]`。

---

## 26. memberInvite

`miniapprelease.memberInvite` —— 邀请小程序成员(开发成员/体验成员/应用管理员/数据查看/自定义灰度)。需应用 owner/MANAGER/APP_MANAGER/DEVELOPER 权限;邀请发出后需被邀请人在支付宝 App 确认(★human-only)。

| 字段 | 必填 | 说明 |
|---|---|---|
| `appId` | **必填** | 哪个小程序 |
| `inviteLogonId` | **必填** | 被邀请人支付宝登录账号(邮箱/手机) |
| `memberType` | **必填** | 成员角色:`DEVELOPER`(开发成员)/`EXPERIENCER`(体验成员)/`MANAGER`(应用管理员)/`DATA_VIEWER`(数据查看)/`CUSTOM_GRAY_MEMBER`(自定义灰度) |

鉴权:需应用归属账号操作,非归属账号返回鉴权失败。

```json
{"request":{
  "appId": "2021000000000002",
  "inviteLogonId": "dev@alipay.com",
  "memberType": "DEVELOPER"
}}
```

返回:成功返回"成员邀请已发出,待被邀请人在支付宝 App 确认";失败返回原因。

---

## 27. memberRemove

`miniapprelease.memberRemove` —— 移除小程序成员(开发/体验/应用管理员等)。允许应用 owner/MANAGER/APP_MANAGER/DEVELOPER 四类角色操作。

| 字段 | 必填 | 说明 |
|---|---|---|
| `appId` | **必填** | 哪个小程序 |
| `userId` | **必填** | 被移除成员的用户 ID(从 member list 结果中获取,非登录账号) |
| `memberType` | **必填** | 成员角色(取值同 memberInvite) |

鉴权同 memberInvite。

```json
{"request":{
  "appId": "2021000000000002",
  "userId": "2088000000000001",
  "memberType": "DEVELOPER"
}}
```

返回:成功返回"成员已移除"。

---

## 28. memberList

`miniapprelease.memberList` —— 查询指定角色的小程序成员列表(应用归属账号视角)。

| 字段 | 必填 | 说明 |
|---|---|---|
| `appId` | **必填** | 哪个小程序 |
| `memberType` | **必填** | 要查询的成员角色(取值同 memberInvite) |

鉴权同 memberInvite。

```json
{"request":{
  "appId": "2021000000000002",
  "memberType": "DEVELOPER"
}}
```

返回:成员列表 JSON,元素含 userId/logonId/nickName/portrait/status/gmtJoin/gmtInvite/role;无成员返回 `[]`。

---

## 29. pluginSubscribe

`miniapprelease.pluginSubscribe` —— 订购或启用插件(幂等:无使用关系时新增并启用,有使用关系时改状态并更新失效日期)。

| 字段 | 必填 | 说明 |
|---|---|---|
| `appId` | **必填** | 哪个小程序 |
| `pluginId` | **必填** | 要订购/启用的插件 ID |
| `pluginVersion` | **必填** | 订购目标插件版本号 |
| `pluginDeployVersion` | 选填 | 不传用插件默认部署版本 |
| `sourceFrom` | 选填 | 客户端来源标识(CLI/O站/服务市场);不传默认门店小程序 |
| `runModeType` | 选填 | 运行模式类型(线上/联调);不传用默认 |
| `orderChannel` | 选填 | 渠道来源统计码 |
| `gmtActive` | 选填 | 启用生效时间,格式 yyyy-MM-dd HH:mm:ss |
| `gmtInvalid` | 选填 | 失效时间,格式 yyyy-MM-dd HH:mm:ss |

```json
{"request":{
  "appId": "2021000000000002",
  "pluginId": "PLUGIN_X",
  "pluginVersion": "1.0"
}}
```

返回:成功返回"插件已订购/启用";失败返回原因。

---

## 附：不可逆操作总表

| 方法 | 两步 | 执行 |
|---|---|---|
| `publishOnline` | 否 | 立即执行上架 |
| `publishGray` | 否 | 立即执行灰度 |
| `offlineVersion` | 否 | 立即执行下架(不可恢复) |
| `rollbackVersion` | 否 | 立即执行回滚 |
| `deleteMiniApp` | 否 | 立即删除小程序(不可恢复) |
| `deleteVersion` | 否 | 立即删除开发中版本 |
| `icpRevoke` | 否 | 立即撤销备案 |

以上操作均为单步执行且不可逆,由 skill 温馨提示层向用户确认后再调用。
