# MCP 调用约定

> 签约 Skill 后端 MCP 能力声明、参数映射、调用规范、错误处理与输出格式。
> 被 references/preview.md、references/apply.md 引用。

> ⛔ **硬约束：previewFormView 和 apply 的请求 JSON 必须由 `scripts/` 下的脚本生成，禁止自行组装。**
> 脚本内含业务规则（MCC 拆分、SKIP_BLOCKS 过滤、pageData 合并、固定参数注入），这些规则会随版本演进。自行组装会丢失这些规则，导致静默错误或数据丢失。

## 2. 后端能力声明

本 Skill 依赖 5 个后端 MCP 能力，对应 3 个 MCP Facade。

### 2.1 MCP Server 与 Facade 映射

| MCP Server | MCP Facade | 方法 | MCP tool 名称 |
|---|---|---|---|
| `ar-sign` | `ProductOpenMcpFacade` | `previewFormView` | `ar-sign.previewFormView` |
| `ar-sign` | `ProductOpenMcpFacade` | `apply` | `ar-sign.apply` |
| `ar-query` | `McpArQueryFacade` | `queryArInfosBySalesProd` | `ar-query.queryArInfosBySalesProd` |
| `ar-query` | `McpArQueryFacade` | `queryArInfosByBackProd` | `ar-query.queryArInfosByBackProd` |
| `ar-order-query` | `McpBizOrderQueryFacade` | `queryBizOrder` | `ar-order-query.queryBizOrder` |
| `ar-order-query` | `McpBizOrderQueryFacade` | `queryBizOrdersByAccount` | `ar-order-query.queryBizOrdersByAccount` |

### 2.2 能力详情

| 能力名称 | Skill 侧参数 | MCP 实际参数 | 返回 | 职责 |
|---|---|---|---|---|
| `previewFormView` | salesCodes + values（可选） | `McpPreviewFormViewRequest { salesProductCodes, callMode, pageData, ... }` | `ResultDTO<McpPreviewFormViewResponse>` 含 artisanPage | 初始化/刷新签约页面 |
| `apply` | 完整 artisanPage 数据 | `McpApplyRequest { businessProperty, salesProductCodes, ... }` | `ResultDTO<McpApplyResponse>` 含 orderNo | 提交签约申请 |
| `queryArInfosBySalesProd` | salesProductCodes | `McpQueryArBySalesProdRequest { salesProductCodes }` | `ResultDTO<McpQueryArBySalesProdResponse>` 含 arInfoList | 按前台产品查合约 |
| `queryArInfosByBackProd` | backProdCodes | `McpQueryArByBackProdRequest { backProdCodes }` | `ResultDTO<McpQueryArByBackProdResponse>` 含 arInfoList | 按后台产品查合约 |
| `queryBizOrder` | orderNos（列表，单个订单号包装为 `["xxx"]`） | `McpQueryBizOrderRequest { tntInstId, orderNos }` | `ResultDTO<McpBizOrderBasicInfoResponse>` | 按订单号查签约订单 |
| `queryBizOrdersByAccount` | accountNo + salesCode | `McpQueryBizOrderByAccountRequest { purchaserAccountNo, salesCode }` | `ResultDTO<McpBizOrderBasicInfoResponse>` | 按账号查签约订单 |

### 2.3 参数映射规则

> ⛔ **以下映射规则已内置于 `scripts/` 脚本中，禁止自行实现这些映射逻辑。** 此表仅供理解参考，不可作为组装 JSON 的依据。

| Skill 参数 | MCP 参数 | 处理方 |
|---|---|---|
| `salesCodes` | `salesProductCodes` | 脚本自动映射 |
| artisanPage values | `pageData` | 脚本从 ar-sign-data.json 提取合并 |
| （固定值） | `callMode="INTERACTION"` | 脚本自动注入 |
| （固定值） | `channelCode="B_SK_SH_RPC"` | 脚本自动注入 |
| （固定值） | `orderType="NEW_SIGN"` | 脚本自动注入 |

> `pid` 通过 CLI 授权登录后由网关自动获取，Skill **不需要向用户收集 pid**。
> `McpOperateContext` 需传入空对象 `{}`，脚本自动生成。

### 2.4 调用约定

通过 `alipay-cli` 调用 MCP tool。**切换环境只需修改下方环境配置，所有子 Skill 引用此处。**

#### CLI 前置检查

每次进入签约流程前，先检测 CLI 是否可用，并确认登录态与授权范围：

```bash
# 1. 检测是否已安装
which alipay-cli

# 2. 未安装则自动安装（开发版）
curl -fsSL https://opengw-pre.alipay.com/alipayopencli/install | bash -s -- --beta

# 3. 验证安装成功
alipay-cli version

# 4. 检查登录态与授权范围（JSON 输出，判定规则见下方「授权范围检查」）
alipay-cli auth status --json
```

若安装失败，告知用户：
> "alipay-cli 安装失败，请参考文档手动安装后重试。"

#### 授权范围检查（⛔ 调用 MCP 接口前必做）

`alipay-cli auth status --json` 的实测返回：

```json
{
  "success": true,
  "data": {
    "logged_in": true,
    "scope": "app:read,fast_instant_trade_pay:write",
    "expires_at": "2026-10-12T12:44:34.40527+08:00",
    "expires_in": "48m29s",
    "device_name": "U-W6LW9WQV-0012.local"
  }
}
```

判定规则：

1. ⚠️ **是否过期必须看 `data.expires_at` / `data.expires_in`，⛔ 不能只看 `logged_in`**。实测 token 过期后 `alipay-cli auth status`（文本模式）**仍打印「✓ 已登录」**，过期信息只在下一行。
2. `data.scope` 是**逗号分隔**的权限范围列表，必须包含目标产品对应的 scope（见下表）。已过期 → 提示用户执行 `alipay-cli auth login`（交互式，需用户自行运行），终止流程、不调接口。
3. 缺目标 scope → 按下方「授权流程」补授权后再调接口。
4. ⛔ **scope 未确认的产品（下表标 🔲）不要因为"无法确认"而阻断流程**：直接调用即可，若返回权限类错误，再按错误提示里的 scope 走授权流程。只有下表已明确列出 scope 的产品才做前置阻断。

| 产品 | 所需 scope | 依据 |
|---|---|---|
| JSAPI 支付 | `jsapi_pay:all` | 已验证为合法 scope（`auth grant --dry-run` 返回设备码；假 scope 名则报 `invalid scope`）；补授权后 apply 端到端跑通 |
| 电脑网站支付 | `fast_instant_trade_pay:write` | 实测授权范围中观察到 |
| **订单查询**（`ar-order-query` 两个接口，任意产品） | 额外需一个 **read** scope：`fast_instant_trade_pay:read` / `machine_pay:read` / `auth_alipay_apppay:read`（**任选其一**） | 实测：仅持 `jsapi_pay:all` 时两接口均报「错误: 缺少所需权限」，退出码 3、stdout 空；错误信息会列出这三个可选值 |
| APP 支付 / 智能收 / 其他 | 🔲 **未确认** | ⛔ 不得按"产品短码小写 + `:all`"之类命名规律推测；缺失时以 CLI 报错提示的 scope 为准 |

**授权流程**（`auth grant` 是设备码授权流，agent 无法静默完成）：

```bash
alipay-cli auth grant --scope jsapi_pay:all --non-interactive --json
```

返回 `data.device_code` / `verification_code` / `verification_url` / `expires_in`（秒）。必须把 **`verification_url` 与 `verification_code` 原样交给用户**，请其完成授权，然后单次检查（不轮询）：

```bash
alipay-cli auth grant --scope jsapi_pay:all --complete
```

完成后重新 `auth status --json` 确认 `scope` 已包含目标值，才继续调用 MCP。

⛔ 三条实测约束：

- **`--dry-run` 不阻止请求**：实测 `auth grant --scope jsapi_pay:all --dry-run` 仍在服务端创建了真实设备授权请求（返回 device_code / verification_code / verification_url）。仅可用于校验 scope 名是否合法，不要当作无副作用的试探。
- **退出码不可靠**：scope 名非法时报「错误: 追加授权失败: invalid scope: 请求的权限范围超出允许范围」，但**退出码仍为 0**。判定成功失败必须解析输出，⛔ 不得用 `$?`。
- **权限门禁按接口不同，⛔ 不可一概而论**（两条实测结论方向相反）：
  - `ar-query`（`queryArInfosBySalesProd` / `queryArInfosByBackProd`）**不做 scope 门禁**：实测授权范围不含对应权限时仍返回 `success=true`。⇒ ⛔ **不能因为这两个接口查询成功就推断授权已充分**，缺 scope 的后果可能是写接口失败或结论不可信。
  - `ar-order-query`（`queryBizOrdersByAccount` / `queryBizOrder`）**做 scope 门禁**：仅持 `jsapi_pay:all` 时两接口均报「错误: 缺少所需权限」，**退出码 3、stdout 为空**，并在错误里列出可选的 read scope（见下表）。⇒ 想核对订单状态，须先补一个 read scope。

#### 环境配置

```
CLI命令: alipay-cli
```

#### MCP 输出规范

CLI 的调试信息（ANSI 转义码、表格边框、日志）输出到 **stderr**，JSON 响应输出到 **stdout**。调用 MCP 时**必须**用 `2>/dev/null` 丢弃 stderr，只保留 stdout 的纯 JSON：

```bash
# ✅ 正确：2>/dev/null 丢弃 stderr，stdout 为纯 JSON
alipay-cli mcp call <server>.<tool> -d '<json>' 2>/dev/null

# ✅ 正确：保存结果到文件
alipay-cli mcp call <server>.<tool> -d '<json>' 2>/dev/null > ~/.alipay/ar/tmp/response.json

# ❌ 错误：tee 会同时输出到终端和文件，文件包含调试输出
alipay-cli mcp call ... 2>&1 | tee ~/.alipay/ar/tmp/response.txt

# ❌ 错误：2>&1 把 stderr 混入 stdout，文件包含 ANSI 转义码和表格
alipay-cli mcp call ... > ~/.alipay/ar/tmp/response.txt 2>&1
```

> **⚠️ 不加 `2>/dev/null` 会导致文件被 ANSI 转义码、表格边框（│ ─ ┌ ┐）、调试日志污染，脚本无法解析。**

#### 调用示例

> ⛔ **previewFormView 和 apply 的请求 JSON 禁止自行组装，必须通过脚本生成后传入 CLI。** 以下示例中的 `-d "$(cat ...)"` 读取的是脚本输出的文件，不是手写的 JSON。

```bash
# previewFormView — 首次调用（无 ar-sign-data.json）
python3 scripts/init_preview_request.py -s I1080300001000041203 -o ~/.alipay/ar/tmp/preview_request.json
alipay-cli mcp call ar-sign.previewFormView -d "$(cat ~/.alipay/ar/tmp/preview_request.json)" 2>/dev/null > ~/.alipay/ar/tmp/preview_response.json
python3 scripts/save_preview_response.py -r ~/.alipay/ar/tmp/preview_response.json

# previewFormView — 后续调用（已有 ar-sign-data.json，修改字段）
python3 scripts/build_preview_request.py webSiteInfo.webStatus=OFFLINE -o ~/.alipay/ar/tmp/preview_request.json
alipay-cli mcp call ar-sign.previewFormView -d "$(cat ~/.alipay/ar/tmp/preview_request.json)" 2>/dev/null > ~/.alipay/ar/tmp/preview_response.json
python3 scripts/save_preview_response.py -r ~/.alipay/ar/tmp/preview_response.json

# apply — 提交签约申请
python3 scripts/build_apply_request.py -o ~/.alipay/ar/tmp/apply_request.json
alipay-cli mcp call ar-sign.apply -d "$(cat ~/.alipay/ar/tmp/apply_request.json)" 2>/dev/null
```

APP 支付调用示例：

```bash
# previewFormView — 首次调用（APP 支付）
python3 scripts/init_preview_request.py -s I1080300001000041313 -o ~/.alipay/ar/tmp/preview_request.json
alipay-cli mcp call ar-sign.previewFormView -d "$(cat ~/.alipay/ar/tmp/preview_request.json)" 2>/dev/null > ~/.alipay/ar/tmp/preview_response.json
python3 scripts/save_preview_response.py -r ~/.alipay/ar/tmp/preview_response.json

# previewFormView — 后续调用（APP 支付，修改字段）
python3 scripts/build_preview_request.py commonAppDeviceInfo.appStatus=OFFLINE -o ~/.alipay/ar/tmp/preview_request.json
alipay-cli mcp call ar-sign.previewFormView -d "$(cat ~/.alipay/ar/tmp/preview_request.json)" 2>/dev/null > ~/.alipay/ar/tmp/preview_response.json
python3 scripts/save_preview_response.py -r ~/.alipay/ar/tmp/preview_response.json

# apply — 提交 APP 支付签约申请（脚本自动检测产品类型，无需额外参数）
python3 scripts/build_apply_request.py -o ~/.alipay/ar/tmp/apply_request.json
alipay-cli mcp call ar-sign.apply -d "$(cat ~/.alipay/ar/tmp/apply_request.json)" 2>/dev/null
```

JSAPI 支付调用示例：

```bash
# previewFormView — 首次调用（JSAPI 支付）
python3 scripts/init_preview_request.py -s I1080300001000060370 -o ~/.alipay/ar/tmp/preview_request.json
alipay-cli mcp call ar-sign.previewFormView -d "$(cat ~/.alipay/ar/tmp/preview_request.json)" 2>/dev/null > ~/.alipay/ar/tmp/preview_response.json
python3 scripts/save_preview_response.py -r ~/.alipay/ar/tmp/preview_response.json

# previewFormView — 后续调用（JSAPI 支付，传入经营类目）
python3 scripts/build_preview_request.py businessInfo.mccInfo.mccCode=<mccCode> -o ~/.alipay/ar/tmp/preview_request.json
alipay-cli mcp call ar-sign.previewFormView -d "$(cat ~/.alipay/ar/tmp/preview_request.json)" 2>/dev/null > ~/.alipay/ar/tmp/preview_response.json
python3 scripts/save_preview_response.py -r ~/.alipay/ar/tmp/preview_response.json

# apply — 提交 JSAPI 支付签约申请（脚本按 salesCodes 自动识别 JSAPI，businessProperty 仅含 mccCode）
python3 scripts/build_apply_request.py -o ~/.alipay/ar/tmp/apply_request.json
alipay-cli mcp call ar-sign.apply -d "$(cat ~/.alipay/ar/tmp/apply_request.json)" 2>/dev/null
```

> JSAPI 支付没有网站/APP 资质区块，需要向用户收集的字段以 previewFormView 返回的 schema 为准（交易场景等字段可能由后端预置值直接给出）。与所有产品一致：**禁止预设区块或字段清单**。

查询类接口参数简单，可直接构造：

```bash
# 按前台产品查合约
alipay-cli mcp call ar-query.queryArInfosBySalesProd -d '{"request":{"salesProductCodes":["I1080300001000041203"]},"ctx":{}}' 2>/dev/null

# 按后台产品查合约
alipay-cli mcp call ar-query.queryArInfosByBackProd -d '{"request":{"backProdCodes":["I1011000100000000005"]},"ctx":{}}' 2>/dev/null

# 按订单号查订单（orderNos 为列表，单个订单号也需包装；tntInstId/操作者信息由 CLI 网关自动注入）
alipay-cli mcp call ar-order-query.queryBizOrder -d '{"request":{"orderNos":["ORD20260411160001"]},"ctx":{}}' 2>/dev/null

# 按账号+产品查订单
alipay-cli mcp call ar-order-query.queryBizOrdersByAccount -d '{"request":{"purchaserAccountNo":"2088xxx","salesCode":"I1080300001000041203"},"ctx":{}}' 2>/dev/null
```

## 7. 后端错误处理

### 7.1 后端返回结构

后端 MCP 接口统一使用 `ResultDTO<T>` 包装返回：

| 字段 | 类型 | 说明 |
|---|---|---|
| `errorCode` | string | 错误码 |
| `errorMessage` | string | 错误描述 |
| `bizTips` | string | 业务提示信息（可展示给用户） |
| `needRetry` | boolean | 是否建议重试 |

apply 响应额外包含 `checkedError` 字段，表示字段校验错误。

### 7.2 Skill 层错误处理规则

| 场景 | 处理方式 |
|---|---|
| 后端返回 errorCode | 展示 errorMessage 给用户；如有 bizTips 一并展示 |
| `needRetry=true` | 告知用户可以重试 |
| apply 返回 checkedError | 提取校验错误信息，引导用户修正对应字段 |
| Skill 弱校验不通过 | 直接告知用户缺少哪些参数 |

Skill 层面**不做自动重试**，展示错误信息由用户决定下一步。

⛔ **`apply` 尤其禁止自动重试**，理由是可能重复建单：`build_apply_request.py` 每次执行的 `bizRequestNo` 是 `str(uuid.uuid4())`（**随机、非确定性**），同一份 pageData 重跑会换幂等键，后端不据此去重。叠加「首次调用偶发空响应、`exit=1`」的现象——当 stdout 为空且 stderr 被 `2>/dev/null` 丢弃时，**前端无法判断是否已建单**，此时重试即成潜在重复单（该账号已实测出现 33 条重复生效单）。⇒ apply 结果不确定时，⛔ 不要重试、⛔ 不要直接断言失败，应告知用户结果待确认，并引导查询订单/合约核实（注意订单查询需额外 read scope，见 §2.4）。

### 7.3 MCP 调用失败时的页面兜底

**MCP 在线签约是主路径，页面签约是兜底。** 仅当满足以下**两个条件同时成立**时才降级到页面：

1. §2.4 的前置检查已通过（登录有效、目标产品的 scope 齐全）；
2. 随后调用 MCP 接口仍然失败，且失败原因**不属于**授权类或入参类（如不在白名单、系统异常、服务不可用、超时、未知失败）。

⛔ **授权类失败不得兜底**：登录态失效（`bizTips="MCP上下文不能为空"`）应重新 `auth login`；权限不足应 `auth grant`；入参问题应修参数。把可自愈的问题引导去页面，是把问题绕过去而不是解决。

兜底动作、各产品的页面入口链接、对客话术与硬约束见 **`references/page-fallback.md`**，此处不重复。

## 8. Skill 对外输出格式

### 8.1 收集进行中

```json
{
  "status": "collecting",
  "productName": "电脑网站支付",
  "checklist": [
    { "title": "经营信息", "state": "completed", "desc": "经营类目：零售-超市" },
    { "title": "店铺信息", "state": "in_progress", "desc": "网站状态：未上线，待收集：网站页面截图" },
    { "title": "联系人", "state": "pending" }
  ],
  "currentStep": {
    "title": "店铺信息",
    "mode": "form",
    "fields": [
      { "name": "shopName", "label": "店铺名称", "widget": "input", "required": true, "value": null },
      { "name": "shopPhoto", "label": "店铺门头照", "widget": "ImageUploadV2", "required": true, "value": null }
    ]
  }
}
```

- `checklist`：全局进度，渲染时用 ✅（completed）🔘（in_progress）🔲（pending）。`desc` 必须从 ar-sign-data.json 的 schema/values 中提取，使用 `title` 作为字段名、`enums[].key` 作为枚举展示名，禁止展示程序字段名（如 `mccCode`、`webStatus`）或技术元数据（如 `type`、`widget`）
- `currentStep.mode`：`single_field`（单字段，对话式）或 `form`（>=2 字段，表单式收集）
- `currentStep.fields`：内部结构化数据，对客展示时只使用 `label`，**禁止展示 `name`（程序字段名）、`widget`（组件类型）、`type`（数据类型）等技术字段**
- 不含价格模块和协议模块

### 8.2 收集完成，可提交

```json
{
  "status": "ready_to_apply",
  "productName": "电脑网站支付",
  "summary": [
    {
      "title": "经营信息",
      "items": [
        { "label": "经营类目", "value": "零售-超市/便利店" }
      ]
    },
    {
      "title": "网站信息",
      "items": [
        { "label": "网站名称", "value": "我的商城" },
        { "label": "网站地址", "value": "https://example.com" }
      ]
    },
    {
      "title": "合约价格",
      "items": [
        { "label": "费率", "value": "0.6%" }
      ]
    },
    {
      "title": "协议",
      "items": [
        { "label": "支付宝支付服务合同", "value": "已确认" }
      ]
    }
  ],
  "pendingFields": [
    { "label": "店铺门头照", "reason": "待线上补充" }
  ]
}
```

- `summary`：按区块展示所有已收集信息，**包含**价格和协议
- `pendingFields`：V1 兜底跳过的字段（如图片上传），标注原因
- 敏感信息脱敏（手机号中间 4 位用 `*`，邮箱 `@` 前仅保留首尾）

### 8.3 提交完成

```json
{
  "status": "submitted",
  "orderNo": "ORD20260411160001",
  "message": "签约申请已提交，预计1~3个工作日完成审核。"
}
```

