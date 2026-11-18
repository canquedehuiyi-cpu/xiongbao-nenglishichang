# Commands

本文件按主链流程编排 49 个 CLI 命令详情（#3/#6/#12 已移除占位，实际可用 46 个）。每条含：CLI tool spec → MCP 兜底 → 入参业务字段 → 出参业务字段 → skill tool output 示例 → human-only / 危险确认标记。skill 是每个命令的调用方；下列 `> 命令` 片段是 skill 调 CLI 的 syntax 示例，不是用户手输。

约定：
- CLI 命令前缀：`alipay-cli miniapp`
- skill 在请求里携带 OAuth 凭证（经 CLI 透传），无需用户显式传；OAuth scope = `miniapp:all`
- 代操作（C 代 B）：skill 在请求里携带被代理人标识（经 facade 透传），服务端自动判定代操作语义；skill 不感知、不对用户暴露
- MCP 兜底：`alipay-cli miniapp <命令>` 报错（CLI 未装/版本过低/命令不支持）或 skill 直接调 tool 时，兜底 `alipay-cli mcp call miniapprelease.<method> --data '<json>'`；MCP tool 方法名与 developerportal `MiniAppCliLifecycleMcpFacade` 接口方法名 1:1 对齐
- skill tool output 示例来源于 Demo 录制 env1-env10 动线，实际渲染由 skill 以自然语言向用户呈现

## CLI ↔ MCP tool 方法名映射

| # | CLI 命令 | MCP tool (`miniapprelease.<method>`) | action / 备注 |
|---|---|---|---|
| 1 | `app create --name` | `miniapprelease.createMiniApp` | — |
| 2 | `config keysign` | `miniapprelease.configKeySign` | action=CREATE_CONFIRM_PAGE(一步;写密钥由核身页扫码后平台自完成) |
| 3 | `config keysign` (step2) | — | 已移除(写密钥由核身页扫码后平台自完成,无独立 CONFIRM) |
| 4 | `info set` | `miniapprelease.modifyBaseInfo` | action=MODIFY（专注修改） |
| 5 | `info get` | `miniapprelease.queryMiniAppDetail` | includeBasicInfo=true（原 modifyBaseInfo QUERY 已移除） |
| 6 | `info name-check` | — | 已移除（改名走 info set，冲突由 modify 返回） |
| 7 | `privacy create` | `miniapprelease.managePrivacy` | action=APPLY |
| 8 | `privacy get` | `miniapprelease.managePrivacy` | action=QUERY |
| 9 | `privacy cancel` | `miniapprelease.managePrivacy` | action=CANCEL;轻量提示 |
| 10 | `category ls` | `miniapprelease.queryCategory` | action=QUERY_TREE |
| 11 | `category require` | `miniapprelease.queryCategory` | action=REQUIRE_QUERY |
| 12 | `category edit-url` | — | 已移除(类目/信息修改改走 info set 带 categoryIds 直存);facade GET_EDIT_URL 保留但 skill 不引导 |
| 13 | `upload --version` | `miniapprelease.uploadBuild` | — |
| 14 | `build status --version` | `miniapprelease.queryBuildStatus` | — |
| 15 | `experience create --version` | `miniapprelease.manageExperience` | action=CREATE;CLI createMiniApp app lifecycle INIT → **可用** |
| 16 | `experience get` | `miniapprelease.manageExperience` | action=QUERY |
| 17 | `experience cancel` | `miniapprelease.manageExperience` | action=CANCEL |
| 18 | `audit submit --version --desc` | `miniapprelease.auditApply` | action=SUBMIT |
| 19 | `audit status --version` | `miniapprelease.auditApply` | action=QUERY |
| 20 | `version ls` | `miniapprelease.queryVersionList` | action=LIST_QUERY |
| 21 | `version show` | `miniapprelease.queryVersionList` | action=DETAIL_QUERY |
| 22 | `name modify-count` | `miniapprelease.queryNameModifyCount` | — |
| 23 | `publish online --version` | `miniapprelease.publishOnline` | — |
| 24 | `publish gray --version --ratio` | `miniapprelease.publishGray` | cancel=false |
| 25 | `publish gray cancel` | `miniapprelease.publishGray` | cancel=true |
| 26 | `safedomain add --domain` | `miniapprelease.manageSafeDomain` | action=ADD |
| 27 | `safedomain delete --domain` | `miniapprelease.manageSafeDomain` | action=DELETE |
| 28 | `safedomain ls` | `miniapprelease.manageSafeDomain` | action=QUERY |
| 29 | `version offline` | `miniapprelease.offlineVersion` | — |
| 30 | `version rollback` | `miniapprelease.rollbackVersion` | — |
| 31 | `app delete` | `miniapprelease.deleteMiniApp` | 不可逆 yes 确认 |
| 32 | `app ls` | `miniapprelease.queryMiniAppList` | — |
| 33 | `app detail --app-id` | `miniapprelease.queryMiniAppDetail` | serviceConfig 段已覆盖 |
| 34 | `icp submit` | `miniapprelease.icpSubmit` | 默认返备案页 URL |
| 35 | `icp status` | `miniapprelease.icpStatus` | 查询备案状态 |
| 36 | `icp revoke` | `miniapprelease.icpRevoke` | 不可逆 yes;撤销备案 |
| 37 | `audit cancel --version` | `miniapprelease.auditApply` | action=CANCEL;轻量提示 |
| 38 | `audit withdraw --version` | `miniapprelease.auditApply` | action=WITHDRAW;轻量提示 |
| 39 | `version delete --version` | `miniapprelease.deleteVersion` | 不可逆 yes |
| 40 | `plugin ls` | `miniapprelease.queryPluginList` | 查询已订购插件列表 |
| 41 | `product catalog` | `miniapprelease.queryProductCatalog` | 查询可调用产品类目(支付/私域/公域等) |
| 42 | `product ls [--category]` | `miniapprelease.queryCallableProducts` | 查可调用产品(复用旧 Web 链路 ProductQueryManager) |
| 43 | `product detail --code` | `miniapprelease.queryProductDetail` | 查单个产品详情(含权限集) |
| 44 | `plugin self` | `miniapprelease.querySelfPlugins` | 查名下自研插件(已上线) |
| 45 | `plugin other [--keyword]` | `miniapprelease.queryOtherPlugins` | 搜索插件市场其他插件 |
| 52 | `member invite` | `miniapprelease.memberInvite` | 需应用 owner/MANAGER/APP_MANAGER/DEVELOPER 权限;★human-only 待被邀请人 App 确认 |
| 53 | `member remove` | `miniapprelease.memberRemove` | 需应用 owner/MANAGER/APP_MANAGER/DEVELOPER 权限 |
| 54 | `member list` | `miniapprelease.memberList` | 查询指定角色成员列表 |
| 55 | `plugin subscribe` | `miniapprelease.pluginSubscribe` | 订购/启用插件(幂等,pluginVersion 可选) |

MCP 兜底模板（示例 env2 创建）：
```bash
# primary
alipay-cli miniapp app create --name 茶语时刻
# fallback (CLI 报错/缺子命令)
alipay-cli mcp call miniapprelease.createMiniApp --data '{"appName":"茶语时刻"}'
```

## 主链 env1 · 登录授权

skill 检查登录态：`alipay-cli diagnose auth --json`：
- 未登录 → `alipay-cli auth login --scope miniapp:all --json`
- 已登录但 scope 不含 `miniapp:all`(如仅 `app:write`) → 先 `alipay-cli auth logout` 退出当前授权(直接 login 会沿用旧低 scope token,不提 scope) → 再 `alipay-cli auth login --scope miniapp:all --json`

渲染二维码给用户扫码授权。本步不属命令表内。

## 主链 env2 · 创建小程序

### 1. app create

- CLI: `alipay-cli miniapp app create --name <名称>`
- **入参**（所有基础信息均可在本步一次传入;CLI createMiniApp 后 app appStatus=ON_LINE + lifecycle INIT,后续 modify/experience/safedomain 全部直接可用）:
  - `appName`(**必填**,小程序名称)
  - `appEnglishName`(可选,英文名)
  - `appSlogan`(可选,简介)
  - `appLogo`(可选,logo 图片 AFTS fileKey 或 https URL)
  - `categoryIds`(可选,新 XS 格式类目如 `XS1014_XS2117`,创建后不必再走 O站 类目编辑)
  - `appDesc`(可选,描述)
  - `serviceTel`(可选,客服电话)
  - `serviceMail`(可选,客服邮箱)
  - 开发者账号(身份)= OAuth 登录 `uid`,skill 不从入参接收 / 不让用户 input
  - **不确定 CLI flags 怎么对应字段时,先 `alipay-cli miniapp app create --help` 查入参 flag 名,不要盲猜**
- 出参: `appId`, `appName`, 状态（"开发中"）
- skill tool output 示例 (Demo env2):

```
> alipay-cli miniapp app create --name 茶语时刻
⏳ 正在创建小程序实例…
✅ 创建成功
   小程序名称:茶语时刻
   APPID:2024090100123456
   状态:开发中
   下一步:完成接口加签(config keysign)
```

skill 收到 `appId` 后自动推进到 env3 接口加签。

## 主链 env3 · 接口加签

### 2. config keysign (生成核身页)

- CLI: `alipay-cli miniapp config keysign`
- MCP tool: `miniapprelease.configKeySign` (action=CREATE_CONFIRM_PAGE)
- 入参: `appId`, `publicKey`(**必填**,用户用官方工具自生成的 RSA2 公钥;skill 必须先引导用户使用 https://opendocs.alipay.com/common/02kipk 生成,**未提供 publicKey 时 skill 停止等待用户输入,严禁空 publicKey 调 configKeySign**,否则 CLI_KEY_SIGN_FAIL: publicKey 不能为空), `signType`(可选,默认 RSA2)
- **防重复**:skill 先 `app detail` → securityKeys 已含公钥 → **skip env3,直接 env4**;skill 本会话已成功调 configKeySign(用户确认扫码成功)→ **不再重调**,推进 env4(避免公钥设置成功后多余调 configKeySign)
- 出参: `keyConfirmToken`, `confirmPageUrl`, `qrCodeUrl`
- ★ human-only：skill 把 qrCodeUrl 渲染给用户，等待用户用支付宝 App 扫码核身 → skill 轮询确认成功
- 安全红线：密钥必须用户自生成，skill 不生成密钥；skill 不接收私钥
- skill tool output 示例 (Demo env3):

```
> alipay-cli miniapp config keysign
⚠️ 接口加签:须先有用户 publicKey 才能生成核身页。未提供 publicKey 时 skill 停止等待用户输入,严禁空调 config keysign(否则 publicKey 不能为空)。加签非管理操作总开关,modifyBaseInfo 不强制先加签。
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

### 3. config keysign (step2) — 已移除

configKeySign 不再有独立 CONFIRM 步:写密钥由核身页扫码后平台移动网关自完成。原 step2 入参 `keyConfirmToken` 与 CONFIRM 不再需要,用户扫码核身即完成加签。

详细加签交互与密钥安全红线见 `appendix/security-and-identity.md`。

## 主链 env4 · 完善配置

### 4. info set (基础信息修改)

> ⚠️ modifyBaseInfo 返回 success=true 即成功(已提交信息审核单据或已生效);**skill 不再调 `app detail` 核对修改是否生效**——审核中基础信息详情不会立即回显新值,detail 会误判"未生效";只有**未上架的 app 直接生效路径**详情会立即更新,但两路 facade 返回 success 已区分,无需 detail 二次确认。

- CLI: `alipay-cli miniapp info set --package ./chayu/`（skill 层解析 `info.json` + 本地截图）
- MCP tool: `miniapprelease.modifyBaseInfo`（action=MODIFY，专注修改）
- 入参: `appId`, 名称/简介/英文名/Logo(OSS)/类目/客服/服务区域/截图，`incrementalUpdate`(bool,默认 false;传 true 走增量改:只传要改字段,未传字段服务端按当前值补齐不被覆盖清空)
- 出参: 操作结果（成功/失败描述）
- 提审前置校验项：提审时会被校验
- **全量覆盖语义，两种防覆盖姿势**：modifyBaseInfo 全量覆盖（未传字段会被 minicore 清空），故要么增量要么全量回传:
  - **增量模式（推荐）**：传 `incrementalUpdate=true`，skill 只传要改字段，服务端按当前详情补齐未传字段，不被覆盖清空（要清空某字段则用全量模式传空）。
  - **全量模式（默认）**：先 `app detail --app-id` 取 basicInfo（appName/appEnglishName/appSlogan/appLogo/categoryIds/serviceTel/serviceMail/appDesc），把本次要改字段替换后连同未改字段**全量回传** modify。
  - **categoryIds 用 detail 返的 miniCategoryIds 原值透传，不要拼/改/省略**（拼错或传非法类目 id 会 INVALID_CATEGORY）。
- **改名频率限制**：改名受 **每自然年 2 次**频率限制（仅实际改名时校验，改 logo/slogan/desc 等非改名不受限；由 `MiniAppCheckManagerImpl.checkNameModifyCnt` 按 `queryNameModifyConfig` 年配额 enforce）。CLI 未设 `forceModifyName`、不自动跳过该限制（`forceModifyName=true` 才跳过，CLI 不走）。改名前可先 `name modify-count` 查剩余次数。
- CLI createMiniApp 出来的 app appStatus=ON_LINE → **modifyBaseInfo 可用**(无需首发上线)。增量 incrementalUpdate=true 只传要改字段(未传字段服务端补齐,不被覆盖清空);或全量先 app detail 拿全字段再回传;改名受 每自然年 2 次频率限制(非改名不受限)。skill 改前先 `app detail` 看 appStatus + `name modify-count` 判断可改范围。
- 注：modifyBaseInfo 仅支持 MODIFY；基础信息查询用 `app detail`，名称不再独立校验（改名冲突由 modify 自身返回）

### 5. info get (基础信息查询)

- CLI: `alipay-cli miniapp app detail --app-id <id>`（原 `info get` 已并入 `app detail`）
- MCP tool: `miniapprelease.queryMiniAppDetail`（includeBasicInfo=true）
- 入参: `appId`
- 出参: 基础信息 JSON（basicInfo 段：名称、简介、英文名、Logo、类目、客服、服务区域、截图等）
- 注：原 `info get` → modifyBaseInfo(QUERY) 已移除，基础信息查询统一用 `app detail`

### 6. info name-check（已移除）

- modifyBaseInfo 的 NAME_CHECK 已下线；改名直接调 `info set`（modifyBaseInfo MODIFY），改名冲突由 modify 自身返回错误，不再独立预校验。

### 7. privacy create (隐私政策创建)

- CLI: `alipay-cli miniapp privacy create --template default`
- 入参: `appId`, `bundleId`（不传默认 `com.alipay.alipaywallet`）
- 出参: JSON,含 `mcpMode` 开关字段:
  - `mcpMode=false`(开关关闭,默认):`{"mcpMode":false,"url":"https://open.alipay.com/develop/privacy/mini/privacyManagement?...","tips":"请在浏览器打开以下链接完成隐私政策配置"}` → skill 渲染 URL 给用户,等待浏览器完成
  - `mcpMode=true`(开关打开):`{"mcpMode":true,"message":"隐私政策已提交"}` → skill 读 message,直接推进主链
- **skill 处理逻辑**:调 `privacy create` 后,解析返回 JSON,读 `mcpMode` 字段 — `false` 则渲染 URL + tips 给用户在浏览器操作(human-only);`true` 则不需人工浏览器操作,读 message 推进下一步
- 开关由服务端 DRM 控制(`cliPrivacyApplyMcpMode`),skill 不感知开关配置,只读返回的 `mcpMode` 做分支

### 8. privacy get (隐私政策查询)

- CLI: `alipay-cli miniapp privacy get`
- 入参: `appId`
- 出参: 当前生效版本信息
- 提审前置校验项

### 9. privacy cancel (撤销隐私政策)

- CLI: `alipay-cli mcp call miniapprelease.managePrivacy --data '{"request":{"appId":"<appId>","action":"CANCEL"}}'`
- MCP tool: `miniapprelease.managePrivacy` (action=CANCEL)
- 入参: `appId`
- 出参: 操作结果"隐私政策已拆除"
- 轻量温馨提示：skill 向用户说明"撤销生效的隐私政策，撤销后无生效隐私版，提审前置校验会拦，需重新 `privacy create`"，执行（可逆操作，非 yes 硬清单）

### 10. category ls (类目树)

- CLI: `alipay-cli miniapp category ls`
- 入参: `invokePid`, `isFilter`（可选）
- 出参: 类目树 JSON

### 11. category require (类目要求)

- CLI: `alipay-cli miniapp category require [--app-id <id>]`
- MCP tool: `miniapprelease.queryCategory`（action=REQUIRE_QUERY）
- 入参: `appId`（可选）、`invokePid`（不传 appId 时按商户身份查可选类目）
  - 传 `appId` → 查该 appId 已选类目的资质要求
  - 不传 `appId` → 查可选类目列表（根据商户身份 invokePid，供选定类目前查看）
- 出参: 类目资质要求列表（传 appId）/ 可选类目列表（不传 appId）

### 12. category edit-url (已移除，二期去页面化)

> **已移除主链**：二期起 类目设置/基础信息修改 统一走 `info set`（modifyBaseInfo 带 `categoryIds`）直存，不再引导用户去页面。facade `queryCategory` GET_EDIT_URL 仍保留（平台侧能力），但 skill 不再调用。

- 类目设置：用 #4 `info set` 传 `categoryIds`（XS 格式如 `XS1014_XS2117`，多个按分号拆，下划线是 level 连接符；切忌用旧数字 id 或按下划线拆，否则 rcconsultcore 返 `PARAMETER_ERROR:类目code不存在`）
- 基础信息（名称/简介/Logo/客服/描述）修改：同 #4 `info set`
- 原 `category edit-url` 返的 O 站编辑页 URL 已不是 skill 推荐路径；附录 `o-station-routing.md` 已移除类目段，仅保留隐私页

## 主链 env5 · 备案（并行不阻塞）

备案命令 `icp submit`（#34，返备案页 URL）/ `icp status`（#35）/ `icp revoke`（#36）详见下方 #34-36 命令详情。

★ human-only：备案页上传材料 + 人脸核验 + 工信部短信验证；skill 在此暂停等待用户完成。

## 主链 env6 · 开发上传构建

`dev init` / `dev preview` 由 minidev 客户端工具实现，skill 转发该类命令给对应客户端工具执行；首次使用 ★ human-only：minidev 扫码授权，skill 等待用户授权后继续。

### 13. upload (上传构建)

把代码提交给平台构建。**仅支持两种 buildMode**(CODE 模式已删除):

| 用户场景 | buildMode | 怎么操作（skill 主动） |
|---|---|---|
| 本地有源码工程（最常见） | `source_afts` ⭐ 推荐(默认) | skill 读用户工程目录→zip→CLI 直传 AFTS(miniappskill) 拿 fileKey→传 `--package-url <fileKey>`。避开大工程 base64 over RPC 慢/卡 |
| 用 `alipay-cli file upload` 上传 zip 得到 fileKey | `source_afts` | `alipay-cli file upload` 返 **fileKey**→ 直接用 `--build-mode source_afts --package-url <fileKey>`。⚠️ `--scene` 参数应为 `miniapp`(不是 `miniappskill`) |
| 基于模板实例化（有 templateId） | `template` | 传 `--template-id <id> --version <v>`(`--template-version`/`--ext-json` 可选,C代B 加 `--isv-app-id`),实例化自模板 |

> ⚠️ **CODE 模式已删除**(bug Dima 2026092000119259666):CODE 模式要求 `packageUrl` 为 http URL,但 CLI 上传本地 zip 得到的是 AFTS fileKey(非 URL)→ SSRF `PROTOCOL_NOT_ALLOWED`。**只支持 `source_afts`(fileKey)与 `template`(templateId)两种**。`source`(base64)仅小工程兜底。

**详细入参/CLI:**

- **SOURCE_AFTS 模式** ⭐ 推荐(默认走此模式):
  - CLI: `alipay-cli miniapp upload --build-mode source_afts --version 1.0.0 --package-url <fileKey>`
  - 入参: `appId`, `version`(必填), `packageUrl`(必填,**AFTS fileKey**), `bundleId`
  - 操作: CLI 直传源码 zip 到 AFTS 拿 fileKey → 传 `--package-url <fileKey>` → 服务端读 AFTS 流 → zip→tar→pkgcore → 构建版本
  - `alipay-cli file upload <zip> --scene miniapp --json` 返 fileKey → 直接传给 `upload --package-url <fileKey>`
  - ⚠️ `--scene` 值是 `miniapp`(不是 `miniappskill`——后者是 AFTS 空间内部标识,CLI `--scene` 不接受)
- **TEMPLATE 模式**(模板实例化,已支持):
  - CLI: `alipay-cli miniapp upload --build-mode template --version 1.0.0 --template-id <id>`
  - 入参: `appId`, `templateId`(**必填**), `version`(**必填**,新版本号), `templateVersion`(建议传), `extJson`, `bundleId`, `isvAppId`(C代B/托管必填)
- **SOURCE 模式**(小工程兜底,base64 over RPC):
  - CLI: `alipay-cli miniapp upload --build-mode source --version 1.0.0 --source-zip-base64 <base64>`
  - 入参: `appId`, `version`, `sourceZipBase64`(必填), `bundleId`
  - 服务端自动 strip macOS 元数据(__MACOSX/.DS_Store 等,bug Dima 2026091500119063429)

> 推荐路径：用户本地有源码工程 → 默认 `source_afts`；模板实例化 → `template`。**不要用 code 模式(已删除)**。

**开发版本达到上限时的恢复流程：**

- `uploadBuild` 返回 `DEV_VERSION_EXCEED_MAX_COUNT` 后停止重复上传。
- 先执行 `alipay-cli miniapp version ls`，分页读取版本列表，只展示状态为 `INIT`（开发中）的版本号、创建时间供用户选择。
- 不得删除 `AUDITING`、`WAIT_RELEASE`、`GRAY`、`RELEASE`、`OFFLINE` 或 `AUDIT_OFFLINE` 状态的版本。
- 用户选定版本后，明确提示“删除开发版本后该版本构建不可恢复”，取得 `yes` 后执行 `alipay-cli miniapp version delete --version <version>`。
- 删除成功后重试一次原上传；仍超限则重新展示版本列表，不循环删除或无限重试。

通用出参: 构建状态（构建中/完成/失败）、版本号、**`packageId`（构建包 ID，必记住，后续 `build status` 轮询必传）**
- skill tool output 示例 (Demo env6):

```
> alipay-cli miniapp upload --build-mode source_afts --version 1.0.0 --package-url <fileKey>
⏳ 正在上传代码…
✅ 上传完成,版本 1.0.0 已提交构建
   packageId: <构建包ID,后续 build status 必传>
```

### 14. build status (查询构建状态)

- CLI: `alipay-cli miniapp build status --version 1.0.0 --package-id <packageId>`
- 入参: `appId`, **`version`(必填,取自 uploadBuild 的 version)**, `bundleId`, **`packageId`（必填，取自 uploadBuild 返回的 packageId,构建系统按 packageId+version 轮询)**
- ⚠️ `version` 和 `packageId` 都必填,缺任一会报 `CLI_PARAM_INVALID`;skill 从 `uploadBuild` 结果带入 `version` + `packageId`
- 出参: 构建状态、版本号
- skill 行为: 从 upload 结果取 `packageId` 带入本步;未传则报 `packageId 不能为空`
- skill tool output 示例 (Demo env6):

```
> alipay-cli miniapp build status --version 1.0.0 --package-id <packageId>
⏳ 查询构建状态…
✅ 构建完成,可生成体验版或提审
```

## 主链 env7 · 体验版（可跳）

### 15. experience create (创建体验版)

- CLI: `alipay-cli miniapp experience create --version 1.0.0`
- 入参: `appId`, `version`, `bundleId`
- 出参: `status`, `expSchemeUrl`, `expQrCodeUrl`, `screenshotUrl`, `version`
- **业务前置**:CLI createMiniApp 出来的 app lifecycle=INIT(非 PREINIT) → **experience create 可用**(基于已构建的开发中版本设体验版扫码预览);体验版是"已注册 app 在正式更新前预览下一版的机制"
- skill tool output 示例 (Demo env7):

```
> alipay-cli miniapp experience create --version 1.0.0
✅ 体验版已生成,测试人员可扫码体验
```

### 16. experience get (查询体验版)

- CLI: `alipay-cli miniapp experience get`
- 入参: `appId`, `version`（可选）；未传时服务端自动取该 appId 最新版本，显式传入时按传入版本查询
- 出参: `schemeUrl`, `screenshot`, `qrCodeUrl`
- skill 行为:直接允许省略 version，不先查版本列表、不猜版本重试；仅当服务端确认没有可解析版本时，引导用户先上传构建或显式指定有效版本

### 17. experience cancel (取消体验版)

- CLI: `alipay-cli miniapp experience cancel`
- 入参: `appId`, `version`, `bundleId`
- 出参: 操作结果

## 主链 env8 · 提审

### 18. audit submit (提审)

- CLI: `alipay-cli miniapp audit submit --version 1.0.0 --desc "首版:菜单浏览+点单+自取核销"`
- 入参: `appId`, `version`（**可选**,不传默认当前最新开发中版本）, `bundleId`, `auditNote`
- 出参: 前置校验结果（隐私/类目/基础/安全扫描逐项）、`auditNo`、审核状态(`AUDITING`)、未备案受限标志、受限描述
- 关键约束: 默认非自动上架、不涉及加急
- skill tool output 示例 (Demo env8):

```
> alipay-cli miniapp audit submit --version 1.0.0 --desc "首版:菜单浏览+点单+自取核销"
⏳ 提审前置校验中…
   ✓ 隐私政策:已配置
   ✓ 类目:已设置(1 个)
   ✓ 基础信息:名称/简介/Logo/描述/客服/服务区域/截图 齐全
   ✓ 安全扫描:已通过
⏳ 正在提交审核…
✅ 已提交审核
   版本:1.0.0
   预计 2 个工作日出结果
```

### 19. audit status (审核状态查询)

- CLI: `alipay-cli miniapp audit status --version 1.0.0`
- 入参: `appId`, `version`
- 出参: 审核状态、未备案受限标志、受限描述（审核通过 skill 主动告知"未备案受限上架 50人/天"提示）
- skill tool output 示例 (Demo env8):

```
> alipay-cli miniapp audit status --version 1.0.0
⏳ 查询审核状态…
✅ 审核通过
   版本:1.0.0  状态:审核通过,待上架
   ⚠️ 未完成备案将受限上架(50 人/天),完成备案后解除
```

## 主链 env9 · 发布

### 20. version ls (版本列表)

- CLI: `alipay-cli miniapp version ls`
- 入参: `appId`, 分页参数, `bundleId`（默认）
- 出参: 版本列表 JSON
- skill tool output 示例 (Demo env10):

```
> alipay-cli miniapp version ls
📋 版本列表(茶语时刻 / 2024090100123456)
   1.0.0  已上架   2026-09-05
   0.9.2  已下架   2026-08-28
```

### 21. version show (版本详情)

- CLI: `alipay-cli miniapp version show --version 1.0.0`
- 入参: `appId`, `version`（**必填**,详情查询按版本号精确查;skill 调用前可先 `version ls` 取版本号,无 version 会返 CLI_PARAM_INVALID: version 不能为空）
- 出参: 版本详情 JSON

### 22. name modify-count (改名剩余次数)

- CLI: `alipay-cli miniapp name modify-count`
- 入参: `appId`（**扁平入参**,facade 方法签名 `queryNameModifyCount(String appId)` 无 request 对象;命令表中唯一扁平入参方法,其余方法均 `xxxRequest` 对象入参）
- MCP 兜底: `alipay-cli mcp call miniapprelease.queryNameModifyCount --data '{"appId":"<appId>"}'`
  - ⚠️ **扁平 `{"appId":"..."}`,不要套 `{"request":{...}}` 信封**(套信封会 `parameter mapping failed: no property definition for key: request`);对象入参方法才用 `{"request":{字段}}` 信封,扁平入参方法用 `{参数名:值}`
- 出参: 剩余改名次数

### 23. publish online (正式上架，不可逆操作温馨提示确认)

> 不可逆操作温馨提示确认:skill 执行前**会**先以温馨提示向用户说明影响并征求明确 `yes`,得到 yes 后再调用 CLI/MCP 工具;未得 yes 时 skill 暂不执行,等待用户进一步指示。详见 SKILL.md「全局规范 → 不可逆操作确认规范」与 appendix/dangerous-op-confirm.md。

- CLI: `alipay-cli miniapp publish online --version 1.0.0`
- 入参: `appId`, `version`, `bundleId`（`confirmToken` 保留但忽略，服务端无 token 两步）
- 出参: 单次调用返操作结果（`confirmRequired` 恒 false）；未备案走受限发布(50人/天)
- 不可逆操作：skill 以温馨提示说明"正式上架 / 目标版本 1.0.0 / 全量用户可访问,是否继续?" → 用户答 yes → skill **单次调用直接执行**
- 详细见 `appendix/dangerous-op-confirm.md`
- skill tool output 示例 (Demo env9):

```
> alipay-cli miniapp publish online --version 1.0.0
温馨提示:正式上架
   目标版本:1.0.0
   操作影响:全量用户可访问
[skill 温馨提示说明影响, 用户答 yes 后 skill 单次执行]
⏳ 正在执行正式上架…
✅ 正式上架成功 🎉
   版本:1.0.0  状态:已上线
```

### 24. publish gray (灰度上架，不可逆操作温馨提示确认)

> 不可逆操作温馨提示确认:skill 执行前**会**先以温馨提示向用户说明影响并征求明确 `yes`,得到 yes 后再调用 CLI/MCP 工具;未得 yes 时 skill 暂不执行,等待用户进一步指示。详见 SKILL.md「全局规范 → 不可逆操作确认规范」与 appendix/dangerous-op-confirm.md。

- CLI: `alipay-cli miniapp publish gray --version 1.0.0 --ratio 10`
- 入参: `appId`, `version`, `bundleId`, `grayStrategy`（`confirmToken` 忽略，服务端无 token 两步）
- 出参: 单次调用返操作结果
- 不可逆操作：skill 同上以温馨提示征求 yes;用户答 yes → skill 单次调用直接执行;灰度比例 ≤ 50 只升不降
- skill tool output 示例 (Demo env9):

```
> alipay-cli miniapp publish gray --version 1.0.0 --ratio 10
温馨提示:灰度上架
   目标版本:1.0.0
   灰度比例:10%(只升不降,上限 50%)
   操作影响:10% 用户可访问此版本
[skill 温馨提示说明影响, 用户答 yes 后 skill 单次执行]
⏳ 正在执行灰度上架…
✅ 灰度上架成功
   版本:1.0.0  灰度比例:10%  状态:灰度中
```

### 25. publish gray cancel (取消灰度，不可逆操作温馨提示确认)

> 不可逆操作温馨提示确认:skill 执行前**会**先以温馨提示向用户说明影响并征求明确 `yes`,得到 yes 后再调用 CLI/MCP 工具;未得 yes 时 skill 暂不执行,等待用户进一步指示。详见 SKILL.md「全局规范 → 不可逆操作确认规范」与 appendix/dangerous-op-confirm.md。

- CLI: `alipay-cli miniapp publish gray cancel`
- 入参: `appId`, `version`, `bundleId`（`confirmToken` 忽略）
- 出参: 操作结果
- 不可逆操作：skill 温馨提示征求 yes → 单次调用直接执行；未备案放行(取消非上架)

### 26. safedomain add (添加域名白名单)

- CLI: `alipay-cli miniapp safedomain add --domain api.chayu-moment.com`
- 入参: `appId`, `domain`
- 出参: 操作结果
- **业务前置**:CLI createMiniApp 出来的 app appStatus=ON_LINE → **safedomain 可用**(无需首发上线)。`safedomain ls`(#28)查询不受限
- skill tool output 示例 (Demo):

```
> alipay-cli miniapp safedomain add --domain api.chayu-moment.com
✅ 域名白名单已添加:api.chayu-moment.com
```

### 27. safedomain delete (删除域名白名单)

- CLI: `alipay-cli miniapp safedomain delete --domain <域名>`
- 入参: `appId`, `domain`
- 出参: 操作结果
- **业务前置:同 #26** CLI createMiniApp app ON_LINE → **safedomain 可用**

### 28. safedomain ls (查询域名白名单)

- CLI: `alipay-cli miniapp safedomain ls`
- 入参: `appId`
- 出参: 域名列表 JSON

## 主链 env10 · 日常管理

### 29. version offline (下架版本，不可逆操作温馨提示确认)

> 不可逆操作温馨提示确认:skill 执行前**会**先以温馨提示向用户说明影响并征求明确 `yes`,得到 yes 后再调用 CLI/MCP 工具;未得 yes 时 skill 暂不执行,等待用户进一步指示。详见 SKILL.md「全局规范 → 不可逆操作确认规范」与 appendix/dangerous-op-confirm.md。

- CLI: `alipay-cli miniapp version offline`
- 入参: `appId`, `version`
- 出参: 操作结果
- 不可逆操作：skill 温馨提示征求 yes → 单次调用直接执行;下架不可恢复

### 30. version rollback (版本回滚，不可逆操作温馨提示确认)

> 不可逆操作温馨提示确认:skill 执行前**会**先以温馨提示向用户说明影响并征求明确 `yes`,得到 yes 后再调用 CLI/MCP 工具;未得 yes 时 skill 暂不执行,等待用户进一步指示。详见 SKILL.md「全局规范 → 不可逆操作确认规范」与 appendix/dangerous-op-confirm.md。

- CLI: `alipay-cli miniapp version rollback`
- 入参: `appId`, `version`
- 出参: 操作结果
- 不可逆操作：skill 温馨提示征求 yes → 单次调用直接执行;线上版本切换为上一版本
- ⚠️ 业务前置(skill 必须先做):
  1. skill **先调 `version ls`** 查询该 appId 下所有版本 + 状态
  2. 从结果中找出**当前状态为已上架(RELEASE)**的版本 → 这是**当前上线版本**(rollback 的入参 version 必须是它,不是回滚目标,而是"当前上架版本号")
  3. 向用户展示"当前上线版本:X.X.X,可回滚的已下架版本有:Y.Y.Y/Z.Z.Z",让用户**自行选择回退到哪个版本**
  4. 用户选定后,skill 用**当前上线版本号**做 `version rollback --version <当前上线版本>`(不是用户选的回退目标版本号)

  **关键**:`rollbackVersion` 的 `version` 参数含义是"**当前上架的版本号**"(服务端据此查到该版本并为它做回滚,内部找已下架的前一版本实现切换),**不是**"要回退到的目标版本号"。
  - 传错(传了非 RELEASE 版本)→ 服务端 `rollbackValidCheck` 抛 `CAN_NOT_ROLLBACK_WITHOUT_ONLINE`(只有上架的版本才能回滚)
  - 传了目标版本→回滚服务端逻辑不匹配→可能误触其他操作(如波酱遇到"回滚失败引导重新上架导致失败")

- skill tool output 示例 (Demo env10):

```
> alipay-cli miniapp version ls
📋 版本列表
   1.0.0  已上架   2026-09-16
   0.9.2  已下架   2026-09-12
   0.9.0  已下架   2026-08-30
skill 向用户展示:当前上线版本 1.0.0,可回滚到已下架版本:
  1. 0.9.2
  2. 0.9.0
请选择回滚目标(输入序号或版本号):
> 1
温馨提示:回滚
   当前上线版本:1.0.0 → 将回滚至:0.9.2
   操作影响:线上版本将切换为 0.9.2
[skill 温馨提示说明影响, 用户答 yes 后 skill 单次执行]
> alipay-cli miniapp version rollback --version 1.0.0
⏳ 正在执行回滚…
✅ 回滚成功
   线上版本:0.9.2
```

### 31. app delete (删除小程序实例，不可逆操作温馨提示确认)

> 不可逆操作温馨提示确认：skill 执行前**会**先以温馨提示向用户说明影响并征求明确 `yes`，得到 yes 后再调用 CLI/MCP 工具；未得 yes 时 skill 暂不执行，等待用户进一步指示。详见 SKILL.md「全局规范 → 不可逆操作确认规范」与 appendix/dangerous-op-confirm.md。

- CLI: `alipay-cli miniapp app delete`
- MCP tool: `miniapprelease.deleteMiniApp`
- 入参: `appId`
- 出参: DangerousOpConfirmResult（`operationDesc=删除小程序实例`）；真实删除
- **删除成功后** skill 提醒用户:该 appId 已彻底删除不可恢复,无法再用此 appId 创建小程序,名下所有版本/体验版/域名/隐私/备案信息均已清除
- 前置 fail-fast（PreCheckOrchestrator.preCheckDeleteMiniApp）：已上架 → `CLI_STATE_CONFLICT`「请先下架」；存在体验版 → `CLI_STATE_CONFLICT`「请先取消体验版」；类型/存在性校验
- 不可逆操作：skill 温馨提示"删除小程序实例 `<appId>`，删除不可恢复，是否继续?" → 用户答 yes → skill 单次调用直接执行

## 续期流程指引（接 env1 之后）

skill 在 env1 登录授权完成后，判断用户是"首次创建"还是"已有小程序续跑"：

1. **未知 appId / 续期 / 用户说"继续 / 找已有小程序"** → skill 调 `app ls`（#32）列名下小程序，用户凭 appId 或 name 过滤选一个 → skill 调 `app detail --app-id`（#33）拉该小程序当前详情 + 版本状态 → 按 baseline 跳到对应 env（未加签 → env3；已加签未配置 → env4；已配置待上传 → env6；已构建 → env7；审核中/通过 → env8/9；已上架 → env10）。
2. **用户已知 appId（提供 / 自然语言说出）** → skill 直接调 `app detail --app-id`（#33）拉 baseline → 按 baseline 跳到对应 env。
3. **首次 / `app ls` 返空列表** → skill 不再调 detail，推进到 env2 创建。

skill 在每个主链节点结束后可选调 `app detail` 再拉一次状态作 checkpoint，确认上一步成果已生效（如 create 成功后 verify appId 出现在 detail；audit submit 后 verify versions 列里出现 audit 状态）。是否调 detail 由 skill 按"是否需 baseline 核对"决定；不必每个 env 强制调。

### 32. app ls (查询名下小程序列表)

- CLI: `alipay-cli miniapp app ls [--app-id <id>] [--name <关键词>] [--page-no <n>] [--page-size <n>]`
- 入参: 可选 `appId`（精确匹配）、`appName`（模糊匹配, 不区分大小写）、`appStatus`（可过滤状态）、分页 `pageNo` (默认 1) / `pageSize` (默认 20)
- 出参: `items`（List[{appId, appName, appStatus, appLogo, appEnglishName, appDesc, oid}]）、`totalCount`、`pageNo`、`pageSize`
- skill 行为: 列表空 → 推进 env2 创建；非空 → 把 list 渲染给用户选 appId/name 继续后续流程

skill tool output 示例 (续期场景):

```
> alipay-cli miniapp app ls
📋 你名下的小程序(共 2 个):
   APPID              名称               状态
   2024090100123456  茶语时刻           已上架
   2024080100666077  二期店铺           开发中
   0. 创建新的小程序
skill 向用户询问: 选哪个继续? (输入 APPID 或名称，或输入 0 创建新)
> 2024090100123456
```

### 33. app detail (查询单个小程序详情)

- CLI: `alipay-cli miniapp app detail --app-id <id> [--bundle-id <bid>] [--include-versions] [--include-privacy] [--include-experience] [--include-safedomain] [--version-limit 5]`
- 入参: `appId`（必填）、`bundleId`（可选，默认 com.alipay.alipaywallet）、8 个 include 开关（默认 includeBasicInfo=true、includeVersions=true、includePrivacyStatus=true、includeSafeDomain=true；其余默认 false）、`versionLimit`（默认 5）
- 出参: `basicInfo`({appId, appName, appEnglishName, slogan, logo, desc, appStatus, categoryIds, serviceTel, serviceMail, serviceArea, oid, createTime})、`versions`(List[{versionNo, status, bundleId, createTime}])、`privacyStatus`({configured, onlineVersionNo})、`experience`({expVersionNo, expQrCodeUrl, expSchemaUrl})、`safeDomains`(List<String>)、`securityKeys`/`serviceConfig` 占位 available=false
- skill 行为: 读 baseline，对照版本状态/隐私/域名/体验版推断当前进度，自动跳到对应 env；如 env 已完成则 skill 告知用户"该小程序已上架/审核中"等不再推进
- 归属校验: 服务端按 identityContext.uid 校验 appId 归属，非归属 AUTH_FAIL

skill tool output 示例 (查"茶语时刻"详情):

```
> alipay-cli miniapp app detail --app-id 2024090100123456
📋 小程序详情
   APPID     : 2024090100123456
   名称      : 茶语时刻
   状态      : 已上架
   类目      : 餐饮-茶饮
   客服电话  : 0571-28001234
   最近版本  :
     - 1.0.0  已上架   2026-09-05
     - 0.9.2  已下架   2026-08-28
   域名白名单: api.chayu-moment.com
   隐私政策  : 已配置 (版本 v2.0)
skill 推断: 该小程序已上架，可跳 env10 日常管理(下架/回滚/删除)
```

## 主链 env5 · 备案详情

### 34. icp submit (备案提交)

- CLI: `alipay-cli mcp call miniapprelease.icpSubmit --data '{"request":{"appId":"<appId>"}}'`
- MCP tool: `miniapprelease.icpSubmit`
- 入参: `appId`，`entityType`（可选，主体类型）、`legalPersonName`/`legalPersonIdCard`/`legalPersonPhone`（可选，法人信息）、`mainCategory`（可选，主营类目）、`provinceId`（可选，省份）
- 出参: JSON,含 `mcpMode` 开关字段:
  - `mcpMode=false`(开关关闭,默认):`{"mcpMode":false,"url":"https://open.alipay.com/platform/portal/icp.htm?appId=...","tips":"请在浏览器打开以下链接完成备案材料提交(需上传材料 + 人脸核验 + 工信部短信验证)"}` → skill 渲染 URL 给用户,★human-only 等待浏览器完成
  - `mcpMode=true`(开关打开):`{"mcpMode":true,"message":"..."}` → CLI 直接结构化提交(当前三期暂未接入,返提示信息)
- **skill 处理逻辑**:调 `icp submit` 后,解析返回 JSON,读 `mcpMode` 字段 — `false` 则渲染 URL + tips 给用户在浏览器操作(human-only);`true` 则读 message 推进
- 开关由服务端 DRM 控制(`cliIcpSubmitMcpMode`),skill 不感知开关配置,只读返回的 `mcpMode` 做分支

### 35. icp status (备案状态查询)

- CLI: `alipay-cli mcp call miniapprelease.icpStatus --data '{"request":{"appId":"<appId>"}}'`
- MCP tool: `miniapprelease.icpStatus`
- 入参: `appId`
- 出参: 备案状态 JSON
- skill 据 `registrationStatus` 字段告知用户(INITIAL=未备案 / AUDITING=审核中 / SUCCESS=已通过 / FAIL=未通过);`registrationSubStatus` 仅供辅助参考,可能与 `registrationStatus` 不一致

### 36. icp revoke (备案撤销，不可逆操作温馨提示确认)

> 不可逆操作温馨提示确认：skill 执行前**会**先以温馨提示向用户说明影响并征求明确 `yes`，得到 yes 后再调用 CLI/MCP 工具；未得 yes 时 skill 暂不执行，等待用户进一步指示。详见 SKILL.md「全局规范 → 不可逆操作确认规范」与 appendix/dangerous-op-confirm.md。

- CLI: `alipay-cli mcp call miniapprelease.icpRevoke --data '{"request":{"appId":"<appId>"}}'`
- MCP tool: `miniapprelease.icpRevoke`
- 入参: `appId`
- 出参: 操作结果（调 `MiniRegistrationFacade.cancelRegistrationInfoAudit` 撤销备案审核申请）
- 不可逆操作: skill 温馨提示"撤销备案审核申请，撤销后需重新提交备案，是否继续?" → 用户答 yes → skill 单次调用直接执行

## env8 补充 · 提审撤回/退回

### 37. audit cancel (撤审)

- CLI: `alipay-cli mcp call miniapprelease.auditApply --data '{"request":{"appId":"<appId>","action":"CANCEL","version":"1.0.0"}}'`
- MCP tool: `miniapprelease.auditApply` (action=CANCEL)
- 入参: `appId`, `version`, `bundleId`
- 出参: AuditApplyResult（`auditStatus=CANCELED`）；撤回审核中版本
- 轻量温馨提示: skill 向用户说明"撤回该版本的审核，撤回后可修改重新提审"，执行（可逆，非 yes 硬清单）

### 38. audit withdraw (退回开发)

- CLI: `alipay-cli mcp call miniapprelease.auditApply --data '{"request":{"appId":"<appId>","action":"WITHDRAW","version":"1.0.0"}}'`
- MCP tool: `miniapprelease.auditApply` (action=WITHDRAW)
- 入参: `appId`, `version`, `bundleId`
- 出参: AuditApplyResult（`auditStatus=WITHDRAWN`）；审核中版本退回开发
- 轻量温馨提示: skill 说明"将该版本退回开发，可重新上传构建提审"，执行

## env10 补充 · 删除开发版本

### 39. version delete (删除开发版本，不可逆操作温馨提示确认)

> 不可逆操作温馨提示确认：skill 执行前**会**先以温馨提示向用户说明影响并征求明确 `yes`，得到 yes 后再调用 CLI/MCP 工具；未得 yes 时 skill 暂不执行，等待用户进一步指示。

- CLI: `alipay-cli mcp call miniapprelease.deleteVersion --data '{"request":{"appId":"<appId>","version":"1.0.0"}}'`
- MCP tool: `miniapprelease.deleteVersion`
- 入参: `appId`, `version`, `bundleId`
- 出参: DangerousOpConfirmResult（`operationDesc=删除开发版本`）；删除开发中版本
- 不可逆操作: skill 温馨提示"删除开发中版本 `<version>`，构建将丢失，是否继续?" → 用户答 yes → skill 单次调用直接执行
- **前置状态提示**:skill 调用前先 `version show --version <version>` 确认该版本处于"开发中"状态;非"开发中"状态(已提审/已上架/已下架)的版本无法删除,返 `CAN_NOT_DELETE_WITHOUT_DEV_STATUS`

## env4 补充 · 插件/可调用产品查询

### 40. plugin ls (查询插件订购列表)

- CLI: `alipay-cli mcp call miniapprelease.queryPluginList --data '{"request":{"appId":"<appId>"}}'`
- MCP tool: `miniapprelease.queryPluginList`
- 入参: `appId`
- 出参: 插件订购列表 JSON；空列表返 `[]`

### 41. product ls (查询可调用产品列表)

- CLI: `alipay-cli mcp call miniapprelease.queryCallableProducts --data '{"request":{"appId":"<appId>","category":"<类目>","pageNo":1,"pageSize":20}}'`
- MCP tool: `miniapprelease.queryCallableProducts`
- 入参: `appId`, `category`（可选）, `pageNo`（默认 1）, `pageSize`（默认 20）
- 出参: 可调用产品列表 JSON；空返 `[]`

## env4 补充 · 成员管理(需应用 owner/MANAGER/APP_MANAGER/DEVELOPER 权限)

> 成员管理(开发成员/体验成员/应用管理员/数据查看/自定义灰度)。
> 鉴权:仅 **应用归属账号**可操作,非 owner 返回 `CLI_AUTH_FAIL`(无成员管理权限)。
> `memberType` 取 `InviteRoleEnum` 名:`DEVELOPER`(开发成员)/`EXPERIENCER`(体验成员)/`MANAGER`(应用管理员)/`DATA_VIEWER`(数据查看)/`CUSTOM_GRAY_MEMBER`(自定义灰度)。

### 42. member invite (邀请成员)

- CLI: `alipay-cli mcp call miniapprelease.memberInvite --data '{"request":{"appId":"<appId>","inviteLogonId":"<账号>","memberType":"<角色>"}}'`
- MCP tool: `miniapprelease.memberInvite`
- 入参: `appId`, `inviteLogonId`(被邀请人支付宝登录账号,邮箱/手机), `memberType`
- 出参: `成员邀请已发出,待被邀请人在支付宝 App 确认`
- ★ human-only: 邀请发出后需被邀请人支付宝 App 确认;skill 暂停等待用户确认
- **邀请管理员(MANAGER)**:需应用归属账号操作;非归属账号(仅 MANAGER/DEVELOPER 角色)邀请 MANAGER 会返"邀请管理员需应用归属账号操作,您的权限不足";邀请 DEVELOPER/EXPERIENCER 不受此限制

### 43. member remove (移除成员)

- CLI: `alipay-cli mcp call miniapprelease.memberRemove --data '{"request":{"appId":"<appId>","userId":"<userId>","memberType":"<角色>"}}'`
- MCP tool: `miniapprelease.memberRemove`
- 入参: `appId`, `userId`(被移除成员 userId,从 `member list` 结果取得,非登录账号), `memberType`
- 出参: `成员已移除`

### 44. member list (查询成员列表)

- CLI: `alipay-cli mcp call miniapprelease.memberList --data '{"request":{"appId":"<appId>","memberType":"<角色>"}}'`
- MCP tool: `miniapprelease.memberList`
- 入参: `appId`, `memberType`(指定要查的角色)
- 出参: 成员列表 JSON 数组,元素 {userId, logonId, nickName, portrait, status, gmtJoin, gmtInvite, role};空列表返 `[]`

## env4/能力 补充 · 可调用产品(类目/列表/详情)

> 可调用产品类目/列表/详情复用旧 Web 站点能力链路(ProductQueryManager + pdcore catalog),不走 abilitycore。

### 45. product catalog (查询可调用产品类目)

- CLI: `alipay-cli mcp call miniapprelease.queryProductCatalog --data '{"request":{"appId":"<appId>"}}'`
- MCP tool: `miniapprelease.queryProductCatalog`
- 入参: `appId`(必填)
- 出参: 类目列表 JSON 数组,元素含 catalogId/catalogName/sortOrder(支付/私域/公域/营销/资金/会员/信用/安全/其他等)

### 46. product ls (查询可调用产品列表)

- CLI: `alipay-cli mcp call miniapprelease.queryCallableProducts --data '{"request":{"appId":"<appId>"}}'`
- MCP tool: `miniapprelease.queryCallableProducts`
- 入参: `appId`(必填), `category`/`pageNo`/`pageSize`(可选)
- 出参: 产品列表 JSON 数组,元素含 productCode/productName/productDesc;空列表返 `[]`

### 47. product detail (查询可调用产品详情)

- CLI: `alipay-cli mcp call miniapprelease.queryProductDetail --data '{"request":{"appId":"<appId>","productCode":"<code>","packageCodes":["<code>"]}}'`
- MCP tool: `miniapprelease.queryProductDetail`
- 入参: `appId`(必填), `productCode`(必填), `packageCodes`(可选,挂包 code 列表)
- 出参: 产品详情 JSON,含 productCode/productName/productDesc/permissions(权限集列表 含 permissionName/permissionCode/permissionDesc)

## env4/能力 补充 · 可订阅插件(自研/其他)

> 插件分为自研(自己名下已上线插件)和其他(插件市场搜索),两条查询链路分开。

### 48. plugin self (查询自研插件)

- CLI: `alipay-cli mcp call miniapprelease.querySelfPlugins --data '{"request":{"pageNo":1,"pageSize":10}}'`
- MCP tool: `miniapprelease.querySelfPlugins`
- 入参: `appId`(可选), `pageNo`/`pageSize`(可选,默认 1/10);oid 从身份上下文自动取
- 出参: 自研插件列表 JSON 数组,元素含 pluginId/pluginName/pluginDesc/pluginOid/serviceCode

### 49. plugin other (搜索市场插件)

- CLI: `alipay-cli mcp call miniapprelease.queryOtherPlugins --data '{"request":{"appId":"<appId>","keyword":"<kw>","pageNo":1,"pageSize":5}}'`
- MCP tool: `miniapprelease.queryOtherPlugins`
- 入参: `appId`(必填), `keyword`/`pageNo`/`pageSize`(可选,默认 1/5)
- 出参: `{totalCount:N, values:[{pluginId,pluginName,pluginDesc,pluginOid,serviceCode,pluginDetailUrl,binded,hasBindingHistory,supportMarketList}]}`

## env4/能力 补充 · 订阅:插件订购

> 插件订购/启用为幂等操作:无使用→新增启用,有→改状态+更新失效日期。

### 50. plugin subscribe (插件订购/启用)

- CLI: `alipay-cli mcp call miniapprelease.pluginSubscribe --data '{"request":{"appId":"<appId>","pluginId":"<id>"}}'`
- MCP tool: `miniapprelease.pluginSubscribe`
- 入参: `appId`, `pluginId`(必填), `pluginVersion`/`pluginDeployVersion`/`sourceFrom`/`runModeType`/`orderChannel`/`gmtActive`/`gmtInvalid`(可选;gmtActive/Invalid 格式 yyyy-MM-dd HH:mm:ss);pluginVersion 非必填
- 出参: 操作结果字符串"插件已订购/启用";底层插件计数/版本冲突 BizException 透传给 CLI

## 未覆盖 / TODO

以下命令当前未覆盖，待后续补齐：

- `dev init` / `dev preview`（env6）— 客户端 minidev 工具，skill 转发 minidev 命令给客户端工具
- `auth login`（env1）— CLI 客户端 OAuth，skill 调 `alipay-cli auth login --scope miniapp:all`
