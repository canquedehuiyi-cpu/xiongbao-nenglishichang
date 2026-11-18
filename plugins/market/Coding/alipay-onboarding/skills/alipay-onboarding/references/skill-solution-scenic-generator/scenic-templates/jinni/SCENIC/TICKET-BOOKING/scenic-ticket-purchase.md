---
name: 【{{skillName}}】
description: >
  【{{scenicAreaName}}】景区购票全流程技能，覆盖搜索入口、查看详情、选择时段和票种、填写访客信息、下单、支付引导全流程。
  当用户表达任何与【{{scenicAreaName}}】门票相关的意图时使用，包括"门票多少钱"、"去【{{scenicAreaName}}】"、"买票"、"还有票吗"等。
  【{{scenicAreaName}}】有多个入口（SPU），不同入口的门票类型不同，需先选择入口再选购门票。
  退票/退款/取消订单、订单查询类意图不走购票流程，直接 terminate 跳转订单中心（详见 Step 0）。
---

## 功能介绍

【{{scenicAreaName}}】景区购票全流程。搜索关键词固定为"【{{scenicAreaName}}】"。流程：选择入口 → 查看详情选购票种和时段 → 填写访客信息 → 提交订单 → 支付引导。

## 涉及 MCP 工具

- **【{{mcpPrefix}}】$【{{searchProducts}}】**：搜索景区入口列表，keyword 固定为"【{{scenicAreaName}}】"
- **【{{mcpPrefix}}】$【{{getProductDetail}}】**：根据 spu_id + date + trip_time 获取商品详情（票型、价格、余票、推荐时段等）。`trip_time` 非必填，格式 `HH:MM`（补零）。`recommended.recommend_reason` 标识推荐原因（有票/超营业时间/售罄/无偏好）
- **【{{mcpPrefix}}】$【{{queryAvailableTimeSlots}}】**：根据 spu_id + date + time_slot_name + sku_list 验证余票并查询可用时段，返回 tickets_enough 和 available_time_slots（含 time_slot_id）
- **【{{mcpPrefix}}】$【{{createOrder}}】**：提交预约订单，返回订单号和支付信息
- **【{{mcpPrefix}}】$【{{getOrderDetail}}】**：根据 order_id 查询订单详情

## 涉及澄清卡片

- **clarifyLongTextChoice**：列表选择（入口选择 C1、替代时段选择 C4）
- **clarifyTicketPriceWithType**：票务信息展示+选购（C2）
- **clarifyTouristInformation**：游客信息+联系人信息收集（C3）
- **AliTradePayConfirmClarificationCard**：订单确认+支付卡片（C5）

## 铁律（最高优先级）

1. **MCP 先于卡片**：每步先调 MCP 获取数据，再构造卡片参数。禁止硬编码 mock 数据
2. **澄清节点必经**：每张卡片必须等用户交互完成后才进入下一步
3. **余票验证在创单前**：【{{queryAvailableTimeSlots}}】 必须在游客信息收集完成后、创单前调用（Step 4）
4. **数据透传**：MCP 返回字段原样透传，禁止修改、增删
5. **失败即终止**：【{{createOrder}}】 失败时 terminate，不做无限重试
6. **退票/查询优先预判**：进入购票前先做 Step 0 意图预判。命中退票/查询 → 直接 terminate 跳转订单中心
7. **游客信息必须用户填写**：禁止 AI 自行补充、猜测、编造任何游客信息。未填全 → 反复出 C3 卡片直到补全
8. **contact_identity_type=NONE 时禁止联系人槽位**：C3 卡片 missing_parameters 中绝对不允许出现 `parameter_name: "联系人"` 的项——无论任何情况，只要 contact_identity_type=NONE，missing_parameters 数组中就不得包含任何 parameter_name 为"联系人"的元素
9. **【铁律】任一票种数量>5立即终止，绝不继续**：两个校验点——①Step 0 人数预检时从 query 提取数量，②C2 卡片返回后检查 countPath value。任一票种>5 → 必须 terminate，禁止继续流程、禁止出后续卡片、禁止调 MCP
10. **时间判断以 recommend_reason 为准**：禁止自行做 business_hours 区间判断或本地时间推断
11. **C2 返回为唯一权威来源**：最终下单的日期、时段、人数一律以 C2 卡片返回为准，不得回退使用 query 中解析的值

---

## 执行流程

### Step 0：意图预判 —— 退票/订单查询直接终止

命中以下关键词时，不走购票流程，直接 terminate：

- **退票类**（退票、退款、取消订单、取消）→ text="进入订单中心退票"
- **查询类**（订单查询、查订单、我的订单、订单详情、查订单状态）→ text="进入订单中心查询"
- 两类同时命中 → 按退票处理

```json
{
  "summary": [{"logo": "", "text": "{退票:进入订单中心退票 / 查询:进入订单中心查询}", "title": "【{{scenicAreaName}}】景区订单中心", "url": "【{{orderCenterUrl}}】"}],
  "summary_type": "resultPageService",
  "status": "success"
}
```

未命中 → 进入人数预检。

#### 人数预检

> **⚠️ 铁律：任一票种数量 > 5 必须直接 terminate，绝不进入后续流程！**

从用户 query 提取数量：

| query 表达 | 门票类 |
|-----------|--------|
| "N个人""N人去""一共N人" | N |
| "N张门票""门票N张""订N张" | N |
| 既有"人"又有"张" | "张"的票种用N，另一类用"人"的数量 |
| 无任何数量 | 跳过检查，进入 Step 1 | — |

**任一列的值 > 5 → 必须 terminate**，示例："帮我订6张【{{scenicAreaName}}】门票" → 门票类=6 > 5 → terminate。

```json
{"summary": "你的游客人数过多，建议去小程序购票", "summary_type": "text", "status": "failure"}
```

---

### Step 1：搜索入口

固定调用 `【{{mcpPrefix}}】$【{{searchProducts}}】`，keyword 强制为"【{{scenicAreaName}}】"。

```json
{"keyword": "【{{scenicAreaName}}】"}
```

**结果处理**：
- **0 个结果** → terminate(status="failure", summary="未找到【{{scenicAreaName}}】景区入口，请稍后重试")
- **1 个结果** → 记录 spu_id，自动进入 Step 2
- **多个结果**：
  - 用户 query 指定了入口名称（如"北大门"）→ 与 spu_name 模糊匹配，唯一匹配 → 跳过 C1 直接进入 Step 2；多个/未匹配 → 出 C1
  - 用户 query 未指定 → 出 C1

#### 卡片 C1：入口选择（clarifyLongTextChoice）

```json
{
  "function_name": "【{{getProductDetail}}】",
  "intent_type": "clarifyLongTextChoice",
  "missing_parameters": [{
    "parameter_name": "",
    "candidate_values": [
      {"id": "{list[i].spu_id}", "name": "{list[i].spu_name}", "tags": ["{list[i].tags数组}"]}
    ],
    "default_value": ""
  }],
  "clarification_phrase": "【{{scenicAreaName}}】有多个入口，不同入口的门票类型不同，你想从哪个入口进入呢？",
  "confirmation_phrase": "已选择入口",
  "confirmed_parameters": []
}
```

---

### Step 2：获取入口详情 + 展示选购卡片

调用 `【{{mcpPrefix}}】$【{{getProductDetail}}】`。

```json
{"spu_id": "{spu_id}", "date": "{YYYY-MM-DD}", "trip_time": "{HH:MM，补零；未指定则省略}"}
```

**date 规则**：优先从用户 query 提取日期；未指定 → 默认今天。

**trip_time 规则**（非必填，HH:MM 补零）：
- 明确时间点（"7点""7:00"）→ 补零传入，如 `07:00`
- 模糊时间：上午→`10:00`，中午/午后→`12:00`，下午→`13:00`，傍晚→`16:00`，晚上→`18:00`
- 未提及时间 → **省略该字段**

**recommend_reason 判断**：

| 枚举值 | 含义 | clarification_phrase |
|--------|------|---------------------|
| `EXACT_MATCH` | 用户指定时间有票 | 使用默认问候语 |
| `PREFERRED_TIME_AFTER_CLOSE` | 超过营业时间 | `"你想要的 {trip_time} 不在景区营业时间（{business_hours}）内，已为你推荐最近的有票时段 {date} {time_slot_name}，请确认或重新选择"` |
| `PREFERRED_TIME_SOLD_OUT` | 售罄 | `"{trip_time} 时段已售罄，已为你推荐最近的有票时段 {date} {time_slot_name}，请确认或重新选择"` |
| `FIRST_AVAILABLE_SLOT` | 无偏好匹配 | 使用默认问候语 |

默认问候语（动态）：用户已说的不追问，未说的才问。`"好的，{未指定时间→你想什么时候去呢？}{未指定人数→同行的有多少人呢？}我帮你约票"`

示例：用户说"明天去"→`"好的，同行的有多少人呢？我帮你约票"`；用户说"3个人"→`"好的，你想什么时候去呢？我帮你约票"`；都说了→`"好的，我帮你约票"`

#### 卡片 C2：票务信息展示+选购（clarifyTicketPriceWithType）

```json
{
  "function_name": "【{{createOrder}}】",
  "intent_type": "clarifyTicketPriceWithType",
  "missing_parameters": [{
    "parameter_name": "认证方式",
    "candidate_values": [{
      "ticket_availability": "{【{{getProductDetail}}】返回的ticket_availability}",
      "recommend": {
        "date": "{recommended.date}",
        "time_slot_id": "{recommended.time_slot_id}",
        "time_slot_name": "{recommended.time_slot_name}",
        "business_hours": "{recommended.business_hours}",
        "recommend_reason": "{recommended.recommend_reason}",
        "skus": [{
          "sku_id": "{sku.sku_id}", "name": "{sku.name}", "description": "{sku.description}",
          "time_slot_type": "{sku.time_slot_type}", "price": "{sku.price}",
          "original_price": "{sku.original_price}",
          "people_num": "{必填，预填默认值；用户未指定数量时默认为0}"
        }]
      }
    }],
    "default_value": ""
  }],
  "clarification_phrase": "{按recommend_reason规则}",
  "confirmation_phrase": "时间人数已确定",
  "confirmed_parameters": []
}
```

> - `ticket_availability`：直接透传 【{{getProductDetail}}】 返回值
> - `recommend.skus[*].people_num`：必填，不在 MCP 返回中，需根据用户 query 判定（见下方规则）

---

#### people_num 判定规则

| 用户意图 | 门票类 people_num |
|-----------|--------|
| "N个人""N人去""一共N人" | N |
| "N张门票""门票N张""订N张" | N |
| 既有"人"又有"张" | "张"的票种用N，另一类用"人"的数量 |
| 未提及数量 | 0 |

> 关键：用"人"量词时两类都=N；用"张"量词+票种关键词时只指定票种=N；未提及数量时=0。people_num 为必填字段，预填默认值（用户未指定数量时默认为 0），用户在 C2 卡片中可修改。

---

#### C2 返回解析

从 C2 卡片返回 JSON 中提取：

- **visit_date**：`serviceTimeRes.picker.segments[i].value`（如 `"2026-06-12"`）
- **time_slot_name**：`serviceTimeRes.picker.segments[i].times[j].label`（如 `"06:40-07:00"`）
- **票种信息**：遍历 `ticket_items` 数组，每个含 `sku_id`、`name`、`identity_type` 等
- **购买数量**：每个 `ticket_items[i].countPath` 指向顶层 key，该 key 的 `.value` 即购买人数。**value=0 的票型跳过**，不参与后续所有步骤
- **time_slot_id**：此时尚未获取，需 Step 4 调用 【{{queryAvailableTimeSlots}}】 后获取

> **⚠️ 铁律：C2 返回后必须立即检查所有票型 countPath value，任一 > 5 → 必须 terminate，绝不继续后续步骤！**

---

### Step 3：收集游客信息

根据 `contact_identity_type` 判断是否需要联系人：
- **NONE**：⚠️ **坚决不传入联系人槽位**，【{{createOrder}}】 时 contact_name 取第一个游客的 visitor_name，contact_phone 取第一个游客的 visitor_phone，contact_id_type/contact_id_number 传空字符串
- **非 NONE**：按枚举要求收集，未填写不可跳过

#### 卡片 C3：游客信息+联系人收集（clarifyTouristInformation）

**构造规则**：
- 跳过 value=0 的票型
- 每种票型（value>0）对应一个 parameter_name（使用 C2 返回的 ticket_items[i].name）
- 每种票型的 default_value 数组长度 = C2 返回的该票型 countPath 对应的 value（购买人数），**人数必须与 C2 返回一致，禁止从用户 query 或其他来源推算**
- 每个游客对象始终包含全部 4 字段（name、id_type、id_number、phone），不用的传空字符串
- 已知信息回填到 default_value，不要全部留空

**联系人部分**按 contact_identity_type 决定：

| contact_identity_type | 联系人 default_value 字段 | 是否必填 |
|---|---|---|
| NONE | ⛔ **坚决不传入联系人槽位，missing_parameters 中不得出现 `parameter_name: "联系人"` 的项** | - |
| NAME_ID | name、id_type("ID_CARD")、id_number | 是 |
| NAME_PHONE | name、phone | 是 |
| NAME_PHONE_ID | name、phone、id_type("ID_CARD")、id_number | 是 |

**C3 构造示例**（contact_identity_type = "NAME_PHONE"，票型1买2人，票型2买2人）：

```json
{
  "function_name": "【{{createOrder}}】",
  "intent_type": "clarifyTouristInformation",
  "missing_parameters": [
    {
      "parameter_name": "【{{scenicAreaName}}】北大门测试门票",
      "candidate_values": [],
      "default_value": [
        {"name": "张三", "id_type": "ID_CARD", "id_number": "3307xxxxxxxxxxxx", "phone": "138xxxx0001"},
        {"name": "", "id_type": "ID_CARD", "id_number": "", "phone": ""}
      ]
    },
    {
      "parameter_name": "云谷索道上行测试门票",
      "candidate_values": [],
      "default_value": [
        {"name": "", "id_type": "ID_CARD", "id_number": "", "phone": ""},
        {"name": "", "id_type": "ID_CARD", "id_number": "", "phone": ""}
      ]
    },
    {
      "parameter_name": "联系人",
      "candidate_values": [],
      "default_value": [{"name": "张三", "phone": "138xxxx0001"}]
    }
  ],
  "clarification_phrase": "请填写游客信息",
  "confirmation_phrase": "游客信息已提交",
  "confirmed_parameters": []
}
```

**C3 返回解析**：key 命名为 `{票种名称}_{序号}_visitor_res` 和 `联系人_{序号}_contact_res`。

> **⛔ NONE 时 missing_parameters 只含票型项，严禁出现 `parameter_name: "联系人"`**

**字段映射**：

| C3 返回字段 | 【{{createOrder}}】 参数字段 |
|------------|---------------------|
| `contact.name` | `visitor_name` / `contact_name` |
| `contact.phone` | `visitor_phone` / `contact_phone` |
| `contact.certificateValue` | `visitor_id_number` / `contact_id_number` |
| `contact.certificateType: 0` | `visitor_id_type: "ID_CARD"` / `contact_id_type: "ID_CARD"` |

---

#### 信息完整性校验（C3 返回后）

- **游客必填字段**：永远校验，根据该票种的 `identity_type` 判断（见枚举映射）
- **联系人必填字段**：根据 `contact_identity_type` 判断（见枚举映射）；`contact_identity_type=NONE` 时不校验联系人

**全部必填字段已填写** → 进入 Step 4

**存在缺失或无返回信息** → 留在 Step 3，重新出 C3 卡片让用户填写/补全，**禁止进入 Step 4**：

1. **全量扫描、逐条点名**：遍历每个游客（按"{票种名称}第{序号}位游客"）和联系人的所有必填字段，一个不能漏
2. **逐条列出缺失**：在 clarification_phrase 中逐条列出，格式「{对象}的{字段}未填写/不正确」，多条用逗号连接
3. **判定规则**：为空→「未填写」；格式不正确（手机号非11位、证件号位数不对等）→「不正确」；已正确→不提示
4. **禁止合并/省略**：5个游客各缺1项也必须列出5条，不允许笼统提示
5. **保留已填**：default_value 回填已填信息，用户只需补全缺失部分，不得清空已填字段
6. **禁止跳过**：只要任一必填字段为空或无效，必须留在 Step 3 重新出 C3，绝不进入 Step 4
7. **禁止AI补充**：所有信息必须来自用户C3卡片输入，禁止AI自行补充、猜测、编造
8. **循环直到填全**：在 Step 3 内反复出 C3，直到所有必填信息齐全才可进入 Step 4

字段名映射：name→姓名，phone→手机号，id_number→证件号

示例："【{{scenicAreaName}}】北大门测试门票第1位游客的证件号未填写，云谷索道上行测试门票第2位游客的手机号不正确，联系人手机号未填写，请补充完整"

---

### Step 4：余票验证

调用 `【{{mcpPrefix}}】$【{{queryAvailableTimeSlots}}】`。

**time_slot_name 规则**：必传，取自 C2 返回的 `serviceTimeRes.picker.segments[i].times[j].label`，与 time_slot_type 无关。

```json
{
  "spu_id": "{spu_id}",
  "date": "{visit_date}",
  "time_slot_name": "{C2返回的时段label}",
  "sku_list": [
    {"sku_id": "{sku_id}", "quantity": "{countPath对应value，>0的票型}"}
  ]
}
```

**结果处理**：
- **tickets_enough = "true"** → 从 available_time_slots 找匹配时段，记录 time_slot_id，进入 Step 5
- **tickets_enough = "false"** → 出 C4 卡片让用户重选时段

#### 卡片 C4：替代时段选择（clarifyLongTextChoice）

```json
{
  "function_name": "【{{createOrder}}】",
  "intent_type": "clarifyLongTextChoice",
  "missing_parameters": [{
    "parameter_name": "",
    "candidate_values": [
      {"name": "{date} {time_from}-{time_to}"}
    ],
    "default_value": ""
  }],
  "clarification_phrase": "抱歉，刚刚票被抢完了，还有这些相近时段有票",
  "confirmation_phrase": "已选择新时段",
  "confirmed_parameters": [{"parameter_name": "choice_url", "parameter_value": "{app_url}"}]
}
```

> candidate_values 最多 3 个（有余票时段前 3 个）；choice_url 取自返回的 app_url

---

### Step 5：提交订单+支付

#### 5a：调用 【{{createOrder}}】

```json
{
  "spu_id": "{spu_id}",
  "contact_name": "{联系人姓名}",
  "contact_phone": "{联系人手机号}",
  "contact_id_type": "{联系人证件类型}",
  "contact_id_number": "{联系人证件号}",
  "ticket_items": [{
    "sku_id": "{sku_id}",
    "quantity": "{C2返回的countPath对应value}",
    "visit_date": "{visit_date}",
    "time_slot_id": "{【{{queryAvailableTimeSlots}}】返回，必填}",
    "time_slot_name": "{time_slot_name}",
    "visitors": [{
      "visitor_name": "{游客姓名}",
      "visitor_phone": "{identity_type含PHONE时必填，否则空字符串}",
      "visitor_id_type": "{identity_type含ID时填ID_CARD，否则空字符串}",
      "visitor_id_number": "{identity_type含ID时必填，否则空字符串}"
    }]
  }]
}
```

**联系人字段填写规则**：

| contact_identity_type | contact_name | contact_phone | contact_id_type | contact_id_number |
|---|---|---|---|---|
| NONE | 第一个游客的 visitor_name | 第一个游客的 visitor_phone | `""` | `""` |
| NAME_ID | C3 收集的联系人姓名 | `""` | `"ID_CARD"` | C3 收集的证件号 |
| NAME_PHONE | C3 收集的联系人姓名 | C3 收集的手机号 | `""` | `""` |
| NAME_PHONE_ID | C3 收集的联系人姓名 | C3 收集的手机号 | `"ID_CARD"` | C3 收集的证件号 |

> ⚠️ quantity 取自 C2 返回的 countPath 对应 value，**不从 C3 返回数据中重新计算人数**。

**返回数据**：standard=false 时解析 nonStandardResult JSON 获取 order_id 和 trade_no（用于支付卡片）。

- 成功 → 进入 5b
- 失败 → terminate(status="failure", summary="下单失败：{error_message}")

#### 5b：获取订单详情

```json
{"order_id": "{【{{createOrder}}】返回的order_id}"}
```

#### 5c：卡片 C5（AliTradePayConfirmClarificationCard）

```json
{
  "orderItems": [{
    "itemId": "{sku_id}", "itemName": "{sku_name}", "itemImageUrl": "",
    "specification": "{visitor_name} {visitor_phone}",
    "originalPrice": "{original_price，单位分}", "currentPrice": "{price，单位分}",
    "quantity": "{quantity}", "itemType": "TICKET", "shopName": "", "shopLogoUrl": ""
  }],
  "orderSummary": {
    "优惠金额": "-¥{discount_amount}",
    "应付金额": "¥{total_amount}",
    "下单须知": "{【{{getOrderDetail}}】返回的bookNoticeUrl}"
  },
  "aliTradePay": {"tradeNO": "{trade_no，来自【{{createOrder}}】}"},
  "templateType": "paymentTourist",
  "clarificationPhrase": "请确认订单并支付",
  "confirmationPhrase": "已支付"
}
```

> - 每个 visitor 展开为一条 orderItem；specification 优先从 【{{getOrderDetail}}】 取，为空则从 【{{createOrder}}】 请求参数取
> - itemImageUrl、shopLogoUrl、shopName 传空字符串
> - trade_no 从 【{{createOrder}}】 返回的 nonStandardResult 中获取
> - quantity 在这里值都为 1，这里都是用来展示的
---

### Step 6：返回订单结果

```json
{
  "summary": [{
    "logo": "",
    "text": "{visit_date} {time_slot_name}",
    "title": "【{{scenicAreaName}}】景区{N}张门票",
    "url": "{order_detail_url}"
  }],
  "summary_type": "resultPageService",
  "status": "success"
}
```

> N = 所有票种 quantity 之和；time_slot_name 取自 C2 返回的时段 label

---

## 日期解析规则

| 表达 | 日期 |
|------|------|
| 今天 | 当天日期 |
| 明天 | 当天+1天 |
| 后天 | 当天+2天 |
| X月X日/X号 | 对应日期（当年） |

输出格式：YYYY-MM-DD

---

## 枚举映射

### contact_identity_type（联系人实名要求，来自 【{{getProductDetail}}】）

| 枚举值 | 含义 | 【{{createOrder}}】 联系人字段 |
|--------|------|----------------------|
| NONE | 无实名要求 | contact_name=第一个游客visitor_name, contact_phone=第一个游客visitor_phone, id_type/id_number=空字符串 |
| NAME_ID | 需姓名+证件号 | contact_name + contact_id_type("ID_CARD") + contact_id_number 必填, contact_phone=空字符串 |
| NAME_PHONE | 需姓名+手机号 | contact_name + contact_phone 必填, id_type/id_number=空字符串 |
| NAME_PHONE_ID | 需姓名+手机号+证件号 | 全部必填 |

### identity_type（游客实名要求，来自 recommended.skus）

| 枚举值 | 含义 | 【{{createOrder}}】 游客字段 |
|--------|------|---------------------|
| NONE | 无实名要求 | name 必填, phone/id_type/id_number=空字符串 |
| NAME_ID | 需姓名+证件号 | name + id_type("ID_CARD") + id_number 必填, phone=空字符串 |
| NAME_PHONE | 需姓名+手机号 | name + phone 必填, id_type/id_number=空字符串 |
| NAME_PHONE_ID | 需姓名+手机号+证件号 | 全部必填 |

### recommend_reason

| 枚举值 | 含义 |
|--------|------|
| EXACT_MATCH | 推荐时段包含用户偏好时间 |
| PREFERRED_TIME_AFTER_CLOSE | 用户偏好时间超过闭园时间 |
| PREFERRED_TIME_SOLD_OUT | 用户偏好时间已售罄 |
| FIRST_AVAILABLE_SLOT | 无偏好匹配，推荐首个可用时段 |

### stock（库存）

| 值 | 含义 |
|----|------|
| 0 | 售罄 |
| -1 | 充足不限 |
| 正整数 | 剩余可购数量 |

---

## 关键注意事项

- **搜索关键词固定"【{{scenicAreaName}}】"**：不从用户输入提取
- **SPU = 入口**：每个 SPU 代表【{{scenicAreaName}}】一个入口
- **价格单位为分**：MCP 返回的 price/original_price 保持原样透传
- **C2 卡片必须调用**：【{{getProductDetail}}】 后必须出 C2，不可跳过
- **C3 联系人槽位**：NONE 时不传，非 NONE 时必填不可跳过
- **C3 信息缺失 → 全量逐条点名**：禁止只提示第一个缺失项，禁止 AI 自行补充信息
- **无票/超时不 terminate**：继续出 C2 卡片，通过 clarification_phrase 说明原因
- **C2 返回是唯一权威**：最终下单日期、时段、人数以 C2 返回为准
- **quantity 来自 C2**：不从 C3 返回数据推算人数