# 页面签约兜底子 Skill

> **MCP 在线签约是本 Skill 的主路径。** 仅当**授权已通过、MCP 调用仍然失败**（不在白名单、系统异常等）时，才降级引导用户到页面完成签约。本文只负责这个兜底动作。

## 1. 子 Skill 元信息

- **name**: page-fallback
- **description**: MCP 调用失败（非授权原因）时，引导用户到页面完成签约
- **触发条件**：已完成 `mcp-guide.md` §2.4 的登录态与授权范围检查（**登录有效、scope 齐全**），随后调用 MCP 接口失败

⛔ **本节最重要的边界：授权类失败不属于本流程。** 若失败原因是登录态失效或权限不足，正确动作是补登录 / 补授权，**引导去页面会把可自愈的问题变成一个绕行**。两者必须分清，判据见 §2。

## 2. 失败分类（决定是否兜底）

调用失败后，按下表归类。**先看失败信号，不要凭猜测**：

| 失败信号 | 归类 | 处置 |
|---|---|---|
| `bizTips` 为 `MCP上下文不能为空`，或 `auth status --json` 的 `expires_at` 已过期 | **登录态失效** | 提示用户 `alipay-cli auth login`，然后重试；⛔ **不走本流程** |
| `errorCode` / `bizTips` 指向权限或 scope 不足 | **授权不足** | 按 `mcp-guide.md` §2.4 走 `auth grant` 补授权；⛔ **不走本流程** |
| 指向入参问题（如 `渠道码不能为空`、字段校验 `checkedError`） | **入参问题** | 按错误信息修正参数或字段后重试；⛔ **不走本流程** |
| **写操作 `apply` 结果不确定**：stdout 为空 / 退出码非 0 且无结构化响应 | **可能已建单，结果待确认** | ⛔ **既不重试、也不兜底**：先按 §2.1 核实是否已生成订单；确认未建单后才可按 §3 兜底 |
| 不在白名单、系统异常、服务不可用、超时、**以及无法归入以上各类的未知失败**（且已排除"结果不确定"） | **MCP 签约通道不可用** | ✅ **走本流程**（§3） |

### 2.1 为什么 `apply` 结果不确定时不能重试、也不能直接兜底

`build_apply_request.py` 的 `bizRequestNo` 每次执行都是随机的 `uuid4()`，**幂等键不固定**，后端不据此去重 ⇒ 同一份数据重跑 apply 每次都可能新增一条订单。叠加「首次调用偶发空响应、`exit=1`」的现象，stdout 为空且 stderr 被 `2>/dev/null` 丢弃时，**前端无从判断是否已建单**。实测已有账号累积 33 条重复生效单。

因此 apply 结果不确定时的正确动作是**先核实、再决定**：

1. 查订单/合约核实是否已建单（⚠️ 订单查询需额外 read scope，见 `mcp-guide.md` §2.4；合约查询 `ar-query` 不做 scope 门禁）
2. 已建单 → 告知用户签约申请已提交，**不给页面入口**
3. 确认未建单，且失败属 §2 最后一行 → 才按 §3 引导页面
4. 无法核实时，如实告知用户「申请可能已提交、也可能未提交，请先到商家中心确认」，⛔ 不要替他断定失败、⛔ 不要重复提交

⚠️ 三类"不走本流程"的情形里，前两类正是 `mcp-guide.md` §2.4 已要求前置检查的项——**前置检查没过就不该发起调用**，所以走到本流程时通常已经排除了它们。若发现前置检查被跳过，先回去补检查，而不是兜底。

## 3. 兜底动作：引导到页面签约

### 3.1 各产品的页面签约入口

所有产品共用同一个 URL 模板，**只换 `productCode` 参数**（PC 与手机浏览器都用同一个 URL）：

```
https://pay.alipay.com/page/ar-center/front-product-sign/form?productCode=<salesCode>
```

| 产品 | salesCode | 签约入口 |
|---|---|---|
| 智能收 | I1080300001000160457 | https://pay.alipay.com/page/ar-center/front-product-sign/form?productCode=I1080300001000160457 |
| 电脑网站支付 | I1080300001000041203 | https://pay.alipay.com/page/ar-center/front-product-sign/form?productCode=I1080300001000041203 |
| APP 支付 | I1080300001000041313 | https://pay.alipay.com/page/ar-center/front-product-sign/form?productCode=I1080300001000041313 |
| JSAPI 支付 | I1080300001000060370 | https://pay.alipay.com/page/ar-center/front-product-sign/form?productCode=I1080300001000060370 |

⛔ 上表 URL 必须逐字使用：不得改写、不得增删参数、不得替换域名。**新增产品按同一模板换 `productCode` 即可**，无需另找链接。

⛔ **不使用短链**（`u.alipay.cn` 一类已弃用），统一用上表的参数化 URL。

**另一形态：支付宝内 deeplink**（可选，仅当调用方明确运行于支付宝客户端内时给出）。同样只换产品名与 `frontProductCodes`：

```
智能收
alipays://platformapi/startapp?appId=2021001135650823&page=pages%2FfrontProductForm%2Findex%3FproductName%3D%25E6%2599%25BA%25E8%2583%25BD%25E6%2594%25B6%26frontProductCodes%3DI1080300001000160457%26channelCode%3DB_SELF_HELP_WIRELESS

电脑网站支付
alipays://platformapi/startapp?appId=2021001135650823&page=pages%2FfrontProductForm%2Findex%3FproductName%3D%25E7%2594%25B5%25E8%2584%2591%25E7%25BD%2591%25E7%25AB%2599%25E6%2594%25AF%25E4%25BB%2598%26frontProductCodes%3DI1080300001000041203%26channelCode%3DB_SELF_HELP_WIRELESS

APP支付
alipays://platformapi/startapp?appId=2021001135650823&page=pages%2FfrontProductForm%2Findex%3FproductName%3DAPP%25E6%2594%25AF%25E4%25BB%2598%26frontProductCodes%3DI1080300001000041313%26channelCode%3DB_SELF_HELP_WIRELESS

JSAPI支付
alipays://platformapi/startapp?appId=2021001135650823&page=pages%2FfrontProductForm%2Findex%3FproductName%3DJSAPI%25E6%2594%25AF%25E4%25BB%2598%26frontProductCodes%3DI1080300001000060370%26channelCode%3DB_SELF_HELP_WIRELESS
```

⚠️ **deeplink 整串含双重 URL 编码**（`%25` 解一层才是 `%`），必须**逐字复制，禁止任何再加工**：⛔ 不得解码成 `%E6%94%AF%E4%BB%98` 或 `支付`，不得把 `%2F`/`%3F`/`%3D`/`%26` 还原成符号，不得自行重新编码，不得增删参数。

⚠️ 产品名以本条为准：**`APP支付`、`JSAPI支付` 不带空格**（`SKILL.md`/`recommend-product.md` 表格里写的是「APP 支付」「JSAPI 支付」，那是排版空格，**不是名字的一部分**）。差一个空格会导致页面打开后产品不预填，且**不报错**。

⛔ 给出的 deeplink 其产品名与 `frontProductCodes` **必须同属一个产品**，不得混用不同产品的片段。

### 3.2 对客话术

默认给 **URL**（跨端可点；deeplink 只在支付宝客户端内、或用户主动索要唤起方式时给）：

> MCP 在线签约通道当前不可用（不是你的账号或授权问题），可以改用支付宝页面完成签约：
>
> 打开下面这个链接，登录商家账号后就会直接进入签约表单页：
> <从 §3.1 取该产品那一行的 URL，逐字复制>
>
> 页面提交后签约结果不在本次流程内，完成后可回来查询合约确认是否生效。

调用方在支付宝客户端内时，可把上面那句换成：`在支付宝里打开下面这个链接，直接进入签约表单页：` + 对应产品那条 deeplink。

产品不在 §3.1 表中（无对应 URL）时用降级话术，⛔ 禁止编造 URL：

> MCP 在线签约通道当前不可用（不是你的账号或授权问题）。页面签约入口暂未配置，请前往支付宝商家中心，在产品市场中搜索对应产品后自助签约。

## 4. 硬约束

1. ⛔ **不得把授权类失败引导到页面**：登录态失效、scope 不足、入参问题都应就地修复后重试（§2 判据）。
2. ⛔ **不得输出错误码、字段名、接口名、堆栈等技术细节**给用户；对客只说"通道当前不可用，且不是你的账号或授权问题"。
3. ⛔ **不得因一次 MCP 失败就断言产品不可用、账号异常、或需要解约重签**——这些结论都没有数据支撑。
4. **链接只能取自 §3.1 的两处清单**（产品 URL 表、四条 deeplink），并且**逐字复制**：不长不短、不改参数、不换域名、不解码/再编码。
   - ✅ **允许**的唯一构造方式：按 §3.1 模板把 `<salesCode>`（URL）或 `productName`+`frontProductCodes`（deeplink）换成**同一已登记产品**的对应值
   - ⛔ **禁止**：凭空拼一个项目里没有的产品码、改动已验证链接的任何字符、把 URL 与 deeplink 的参数互相挪、换用短链、对 deeplink 解码或重新编码
   - ⛔ **禁止跨产品混用**：给出的链接，其 `productCode`（URL）或 `productName`+`frontProductCodes`（deeplink）必须与用户本次要签的产品**一致**
5. ⛔ **不要静默降级**：走了兜底必须明确告诉用户"这次是走页面签的"，避免用户以为已经通过在线流程办妥。
6. 页面签约**不在本 Skill 闭环内**：签约后本 Skill 无法得知结果，须提示用户完成后再来查询合约（`query-ar.md`）确认生效。

## 5. 引用文件

| 文件 | 用途 |
|---|---|
| `references/mcp-guide.md` | §2.4 登录态与授权范围检查（本流程的前置）；§7 错误处理 |
| `references/query-ar.md` | 页面签约完成后回来查合约确认生效 |