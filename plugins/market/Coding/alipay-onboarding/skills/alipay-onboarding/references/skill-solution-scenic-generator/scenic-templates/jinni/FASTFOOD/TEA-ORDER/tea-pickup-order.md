---
name: 【{{skillName}}】
description: 【{{brandName}}】到店自提技能，覆盖门店搜索、商品搜索、规格切换、订单预览、创建订单全流程。仅支持点单一类商品。当用户表达"喝【{{brandName}}】"、"点杯【{{brandName}}】【{{brandCategoryWord}}】"、"【{{brandName}}】拿铁"、"附近【{{brandName}}】"、"查询我的【{{brandName}}】订单"等意图时使用。
---

# 【{{brandName}}】技能

## 功能概述

- **订单查询/取消**：跳转【{{brandName}}】小程序订单列表页
- **点单流程**：会员授权 → 门店搜索 → 商品搜索 → 规格切换 → 订单预览 → 创建订单 → 支付 → 查询取餐码
- 仅支持到店自提模式(pick)，外送/拼单/取消订单引导至小程序

## 涉及到的工具
- **【{{authorizeMember}}】**：【{{brandName}}】会员授权绑定，未注册用户自动注册，点单和订单查询前必须调用
- **【{{queryShopList}}】**：根据经纬度查询附近【{{brandName}}】门店列表，支持门店名称模糊搜索
- **【{{searchProductForMcp}}】**：根据用户关键词和门店搜索推荐商品
- **【{{queryProductDetailInfo}}】**：查询商品详细信息，含完整规格属性和默认选中状态
- **【{{switchProduct}}】**：切换商品规格属性（杯型、温度、甜度等），返回新的SKU编码和价格
- **【{{previewOrder}}】**：订单预览，计算应付金额、可用优惠券和预计取餐时间
- **【{{createOrder}}】**：创建【{{brandName}}】订单，返回订单ID和支付信息
- **【{{queryOrderDetailInfo}}】**：查询订单详情，含订单状态和取餐码
- **AliTradePayTool**：支付宝端侧支付收银台，唤起用户完成支付
- **intent_clarification**：意图澄清工具，用于门店选择、商品选择、订单确认等交互
- **terminate**：流程终止工具，返回最终结果或异常

## 执行流程

【{{brandName}}】技能包含两个独立的主流程：**查询订单流程**和**点单流程**。系统通过步骤1检测用户意图后路由到对应流程。

### 步骤1：订单相关意图检测（前置路由）

分析用户输入，判断意图类型：
- **查询订单意图**：包含"【{{brandName}}】"或"【{{brandCategoryWord}}】" **且** 包含"订单"、"查询"、"我的订单"、"去哪看"、"在哪找"
- **取消订单意图**：包含"【{{brandName}}】"或"【{{brandCategoryWord}}】" **且** 包含"取消"、"退"、"不要了"、"删掉"
- **点单意图**：包含"点一杯"、"买一杯"、"来杯"、"喝"、"想要"等点单关键词，或直接表达想喝【{{brandName}}】商品名称
- 若检测到查询或取消订单意图 → 进入**查询订单流程**
- 若未检测到订单相关意图 → 进入**点单流程**

---

## 查询订单流程

### 步骤2：会员授权

调用 `【{{authorizeMember}}】()`
- 若授权失败 → 返回"【{{brandName}}】会员授权失败，请稍后重试"，流程终止
- 若授权成功（authorizeStatus=1）→ 进入步骤3

### 步骤3：跳转订单列表页

调用 `terminate` 工具，返回订单列表页跳转链接：
- summary_type：固定为 "resultPageService"
- status：固定为 "success"
- summary：`[{"title":"【{{brandName}}】 | 我的订单","logo":"【{{brandLogo}}】","url":"【{{miniAppOrderListUrl}}】","text":"点击进入【{{brandName}}】订单列表"}]`

---

## 点单流程

### 步骤2：多类商品意图检测（前置拦截）

检测用户输入是否包含点多类不同商品的意图：
- 关键词检测："和"、"再加一杯"、"再来一杯不同的"、"两杯不同"、"分别来"等（多杯同品类不拦截，如"3杯【{{hotProductName}}】"正常放行）
- 若检测到多商品意图 → 调用 `terminate`，status="failure"，summary为 "{"error":"true","message":"当前仅支持点单一类商品，如需点多种商品请分开下单或前往【{{brandName}}】小程序操作。"}"
- 若为单商品意图 → 进入步骤3

### 步骤3：会员授权

调用 `【{{authorizeMember}}】()`
- 若授权失败 → 返回"【{{brandName}}】会员授权失败，请稍后重试"，流程终止
- 若授权成功（authorizeStatus=1）→ 进入步骤4

### 步骤4：门店搜索

- 用户未提供具体地址（如"帮我点附近的【{{brandName}}】"、【{{frequencyProductQuery}}】） → 进入步骤4.1
- 用户提供了具体地址（如"帮我点杭州东站附近的【{{brandName}}】"、"帮我在武林广场点杯【{{brandName}}】咖啡"、【{{frequencyAddressQuery}}】） → 进入步骤4.2

**步骤4.1：查找当前位置门店**

直接调用 `【{{queryShopList}}】()`，**不需要传递经纬度参数**
- 若用户提供了门店名称且**未**提及"附近" → 同时传入 `deptName` 参数进行模糊匹配
- 若用户提及"附近" → 不传deptName，直接搜索周边门店

**步骤4.2：查找指定位置门店**

调用 `maps_geo_direct（address="具体地址", city="城市名"）`获取经纬度，直接取返回的 latitude/longitude 调用 `【{{queryShopList}}】(longitude, latitude)`
- 若用户提供了门店名称且未提及"附近" → 同时传入 deptName 参数进行模糊匹配
- 如果maps_geo_direct失败获取不到经纬度，需要传入 deptName 参数进行模糊匹配，如'外滩大会', "美宜佳AI便利店"

筛选返回结果中workStatus为"营业中"的门店，**必须剔除"打烊中"的门店**

**⚠️ 门店澄清铁律**：
| 条件 | 操作 |
|------|------|
| 调用了deptName参数 **且** 返回列表只有1个门店 | 跳过步骤5，直接进入步骤6 |
| 未传入deptName参数 | 必须进入步骤5让用户选择 |
| 传入了deptName但返回多个门店 | 必须进入步骤5让用户选择 |
| 返回门店列表为空或所有门店均为"打烊中" | 调用terminate，返回"message=附近暂无营业中的【{{brandName}}】门店" |

### 步骤5：意图澄清（用户选择门店）

选择距离最近的**前3个**营业中门店，调用 `intent_clarification`：
- intent_type: `clarifyShopChoice`
- missing_parameters 中设置一个参数对象:
  - parameter_name: 门店列表
  - candidate_values: [{deptId, deptName, address, distance}]
- clarification_phrase：基于缺失参数动态生成，如"已经帮你找到附近的【{{brandName}}】门店，看看想去哪一家呢～"
- confirmation_phrase："门店已确认，继续帮你找咖啡"

**⚠️ JSON安全处理**：门店名称中的双引号（"xxx"）必须替换为「xxx」

### 步骤6：商品搜索

调用 `【{{searchProductForMcp}}】(deptId=选定的门店ID, query=咖啡品的关键词，包括规格, delivery="pick")`
- **query参数**：咖啡品的关键词，如果用户query没有提及具体品直接给空字符""，如：帮我点一杯【{{brandName}}】拿铁 -> 拿铁；帮我点一杯【{{brandName}}】咖啡 -> ""；帮我点一杯少冰的【{{hotProductName}}】 -> 少冰的【{{hotProductName}}】。- delivery 固定为 "pick"

**⚠️ 商品澄清铁律**：
| 条件 | 操作 |
|------|------|
| 用户输入含明确商品名称 **且** 返回列表只有1个商品 | 跳过步骤7，直接进入步骤8 |
| 用户输入未包含明确商品名称 | 必须进入步骤7让用户选择 |
| 包含明确商品名称但返回多个商品 | 必须进入步骤7让用户选择 |
| 返回商品列表`products`为空 | 调用terminate工具，返回"message=该门店暂无相关商品" |

【特殊用户问句场景】
- 如果用户原始query包含"外滩大会"、"美宜佳AI便利店"关键词并且包含具体品，使用具体品搜索商品时候，`products`为空，需要调整**query参数**：直接给空字符创继续搜索。
- 除了一种情况需要两次尝试 `【{{searchProductForMcp}}】` 搜索，其他情况不需要多次搜索，即使没有商品列表`products`为空。

**商品关键词明确性判断**：
- **明确**：【{{hotProductName}}】
- **不明确**："推荐"、"咖啡"、"喝什么"、"来杯【{{brandName}}】"、"随便推荐一个"

### 步骤7：意图澄清（用户选择商品）

调用 `intent_clarification`：
- intent_type: `clarifyProductHtml`
- clarification_phrase: "已为您在xxx店找到了以下商品"
- configuration : 不需要传参
- missing_parameters 中设置一个参数对象:
  - parameter_name: 商品列表
  - candidate_values: 原样透传 `products`，格式为[{productId, productName, skuCode, initialPrice, estimatePrice, additionDesc, productAttrs}]，productAttrs可能为json列表也可能为"osskey"开头的缓存变量字符串，**所有参数包括productAttrs必须原样传递，不可缺失**

### 步骤8：订单预览

**步骤8.1：获取订单预览信息**

调用 `【{{previewOrder}}】(deptId=选定的门店ID, productList=[{productId, skuCode, amount, productAttrs=[{attributeId, attributeName, count, parentAttributeId, parentAttributeName}]}], delivery="pick")`
- amount：用户指定的数量，未指定则默认1
- delivery 固定为 "pick"
- **禁止**填写addressId参数

**步骤8.2：意图澄清（展示订单预览）**

调用 `intent_clarification` 让用户确认订单：
- intent_type 使用 `OB_tea-order-template_clarifyOrder`
- missing_parameters 固定空数组
- **confirmed_parameters 传递多个参数对象**：
  - 参数1：productInfoList，类型为列表，由于只支持单品，所以productInfoList只有一个元素。元素字段如下（**禁止包装为字符串**）：
    - productId：从`【{{previewOrder}}】`工具返回的 `productInfoList[].productId` 获取
    - name：从`【{{previewOrder}}】`工具返回的 `productInfoList[].name` 获取
    - breviaryPicUrl：从`【{{previewOrder}}】`工具返回的 `productInfoList[].breviaryPicUrl` 获取
    - skuCode：从`【{{previewOrder}}】`工具返回的 `productInfoList[].skuCode` 获取
    - additionDesc：从`【{{previewOrder}}】`工具返回的 `productInfoList[].additionDesc` 获取
    - initialPrice：从`【{{previewOrder}}】`工具返回的 `productInfoList[].initialPrice` 获取
    - estimatePrice：从`【{{previewOrder}}】`工具返回的 `productInfoList[].estimatePrice` 获取
    - productAttrs：从`【{{previewOrder}}】`工具返回的`productList[].productAttrs`获取
    - amount：从`【{{previewOrder}}】`工具返回的`productInfoList[].amount`获取
    - productDetailUrl：从`【{{previewOrder}}】`工具返回的`productDetailUrl[].productDetailUrl`获取
  - 参数2：shopInfo，类型为JSON对象，每个字段如下（**禁止包装为字符串**）：
    - deptId：从`【{{previewOrder}}】`工具返回的 `shopInfo.deptId` 获取
    - deptName：从`【{{previewOrder}}】`工具返回的 `shopInfo.deptName` 获取
  - 参数3：orderSummary，类型为JSON对象，每个字段如下（**禁止包装为字符串**）：
    - totalInitialPrice：从`【{{previewOrder}}】`工具返回的 `totalInitialPrice` 获取
    - totalEstimatePrice：从`【{{previewOrder}}】`工具返回的 `totalEstimatePrice` 获取
    - privilegeMoney：从`【{{previewOrder}}】`工具返回的 `privilegeMoney` 获取
    - couponCodeList：从`【{{previewOrder}}】`工具返回的 `couponCodeList` 获取

【强制必传】confirmed_parameter字段严格按照以上格式传递，不可不传也不可为空，否则将导致订单预览信息失败。

用户确认的最终商品数量为num_order_res.value

**用户确认后处理**：
- 若用户通过卡片点击确认（role:tool结果非空，**即使卡片回调里的商品数量发生变化也属于此路径，不回8.1**） → 直接进入步骤8.3，**禁止再次调用intent_clarification**
- 若用户通过文本请求（出现【用户澄清回复】）修改规格（杯型/温度/甜度）→ 进入步骤9
- 若用户通过文本请求（出现【用户澄清回复】）修改数量 → 使用新商品数量回到步骤8.1重新 `【{{previewOrder}}】`，并进入步骤8.2重新展示确认

**步骤8.3：创单前询价**

调用 `【{{previewOrder}}】(deptId=门店ID, productList=[{productId, skuCode, amount, productAttrs=[{attributeId, attributeName, count, parentAttributeId, parentAttributeName}]}], delivery="pick")`
- 更新amount为order_num_res.value，其它参数从用户澄清结果获取
- **不需要用户确认和澄清** → 下一步工具调用必须是 `【{{createOrder}}】`（步骤10），严禁回到8.2、严禁 intent_clarification、严禁 terminate

### 步骤9：规格切换（可选，出现【用户澄清回复】触发）

用户在订单预览阶段用文字请求修改规格时执行。**支持修改杯型/温度/甜度**，其它(奶类/加料/换商品等)一律拒答。

**步骤9.1：获取商品详情**

调用 `【{{queryProductDetailInfo}}】(deptId=门店ID, productId=商品ID, delivery="pick")`
- 获取商品完整属性集合（productAttrs），**以【{{queryProductDetailInfo}}】返回的skuCode为准**
- productAttrs 为扁平属性列表，需按 `parentAttributeName` 归类为温度/杯型/甜度维度

**步骤9.2：切换规格**

将用户的自然语言映射为杯型/温度/甜度的中文值，并分别在productAttrs中定位目标属性。用户未提及的维度**沿用当前已选值**。

**⚠️ 规格匹配铁律（强制）**：
- subAttr.attributeId **必须**从 【{{queryProductDetailInfo}}】 返回的 productAttrs 中精确匹配 attributeName 取得，**禁止虚构、猜测、拼接或借用相邻数字的 ID**
- 维度候选**仅 1 项**（如温度维度只返回"冰"一个可选项） → 该维度一定不支持其他值，直接走"不支持"分支
- 用户请求的中文值在 productAttrs 中**找不到 attributeName 完全一致的项** → 一律视为"不支持"，禁止调用 【{{switchProduct}}】
- 用户请求的是杯型/温度/甜度以外的规格（奶类/加料/换商品等） → 一律视为"非支持规格"，禁止调用 【{{switchProduct}}】
- 匹配维度时必须按 parentAttributeName 归类（温度/杯型/甜度），不可跨维度借用 attributeId

**步骤9.2A：不支持分支**（用户请求的规格在候选列表内找不到 attributeName 完全一致的项，或维度候选仅1项，或为非支持规格）

例如：要"热的"但温度维度只有"冰"一项；要"多糖"但候选只有"全糖/半糖/不另外加糖"；要"加燕麦奶"但不属于杯型/温度/甜度。

执行序列（严格按顺序，**不可跳步、不可并行**）：
1. **第一动作：必须重新调用 【{{previewOrder}}】**
  - 入参：原规格 deptId/productId/skuCode/amount/productAttrs=[{attributeId, attributeName, count, parentAttributeId, parentAttributeName}]，delivery="pick"
  - **即使历史已存在 【{{previewOrder}}】 返回值且 skuCode 未变化，本步骤仍必须重新发起 【{{previewOrder}}】 工具调用**
  - **禁止复用历史 【{{previewOrder}}】 返回值**，**禁止跳过本步直接调 intent_clarification**，**禁止用 terminate 收尾**
2. **第二动作：拿到 【{{previewOrder}}】 返回后，调用 `intent_clarification` 展示订单预览**
  - confirmed_parameters 的字段值**必须且只能从步骤1本次新返回的 【{{previewOrder}}】 结果中提取**（格式同步骤8.2，完整传递3个参数对象：productInfoList / shopInfo / orderSummary）
  - intent_type=`OB_tea-order-template_clarifyOrder`，function_name=`【{{previewOrder}}】`，missing_parameters 固定空数组
  - clarification_phrase：不支持规格用"该商品不支持{用户请求的规格}，如需修改请到【{{brandName}}】小程序完成"；非支持规格用"当前仅支持修改杯型、温度和甜度，{其他修改}请到【{{brandName}}】小程序完成"
3. 等待用户后续输入，进入后续流程

**步骤9.2B：支持分支**（用户请求的规格在候选列表内能找到 attributeName 完全一致的项）

⚠️ **调用 【{{switchProduct}}】 前的强制自检闸口（任一不满足即转 9.2A，禁止调用 【{{switchProduct}}】）**：

1. **候选数量自检**：目标维度（用户请求规格所属的 parentAttributeName，如"温度"/"杯型"/"甜度"）在本次 【{{queryProductDetailInfo}}】 返回的 productAttrs 中**候选数量 ≥ 2**。候选仅 1 项时该维度一定不支持其他值，**直接转 9.2A**，禁止调用 【{{switchProduct}}】。
2. **字面精确匹配自检**：用户请求的中文值在目标维度的 productAttrs 候选中**能找到 attributeName 完全一致的项**（字面精确相等，禁止同义词替代、禁止"热的"匹配到"冰"、禁止跨维度借用）。找不到时**直接转 9.2A**，禁止调用 【{{switchProduct}}】。
3. **attributeId 真实性自检**：待传入 【{{switchProduct}}】 的 `attrOperationParam.attributeId`（父属性ID）与 `subAttr.attributeId`（子属性ID）**均必须从本次 【{{queryProductDetailInfo}}】 返回的 productAttrs 中原样复制**，禁止拼接、相邻数字改造、跨维度借用或记忆臆造。
  - 自检方法：在 productAttrs 原文中按 attributeName 定位到目标项后，复制其 attributeId 与 parentAttributeId，**逐字符核对**与即将传入 【{{switchProduct}}】 的参数完全一致后再发起调用。若 ID 在 productAttrs 中找不到原文出处，**立即转 9.2A**，禁止凭记忆/相邻数字编造。
4. **维度归属自检**：用户请求的规格必须属于**杯型 / 温度 / 甜度**三类 parentAttributeName 之一，其它维度（奶类/加料/换商品等）**直接转 9.2A**。

任一自检未通过时：严禁调用 【{{switchProduct}}】，按 9.2A "不支持分支" 顺序执行（先重调 【{{previewOrder}}】 → 再 intent_clarification 拒答）。

调用 `【{{switchProduct}}】(deptId, productId, skuCode, attrOperationParam, amount, productAttrs)`
- attrOperationParam 结构：`{attributeId: "父属性ID（来自productAttrs.parentAttributeId）", subAttr: {attributeId: "目标子属性ID（必须来自productAttrs精确匹配attributeName）", operation: 3}}`
- operation含义：1=添加属性(加浓)，2=移除属性，3=选择属性(互斥切换)
- amount ：必填，来自前面【{{previewOrder}}】入参的 amount
- productAttrs：必填，来自前面【{{previewOrder}}】出参 的 productAttrs，可能为json列表也可能为"osskey"开头的缓存变量字符串
- 成功后用【{{switchProduct}}】返回的新skuCode以及新的productAttrs **回步骤8.1重新 `【{{previewOrder}}】(skuCode=新的skuCode, productAttrs=新的productAttrs)`** → 步骤8.2重新展示，clarification_phrase="已修改成您需要的规格，请确认订单信息"
  - 这里的 productAttrs **原样取自本次 【{{switchProduct}}】 的成功出参**（可能是 "osskey" 开头的缓存字符串，也可能是 JSON 列表，见核心铁律"productAttrs 透传不解析"），**直接透传，禁止自行解析/展开/重建**；**绝对禁止**取自其他任何工具的入参/出参，**也禁止沿用旧值**

### 步骤10：创建订单

调用 `【{{createOrder}}】(deptId, productList, longitude, latitude, couponCodeList, delivery="pick")`
- longitude/latitude使用门店位置
- **couponCodeList从`【{{previewOrder}}】`工具返回的 `couponCodeList` 获取，不为空时必须传入否则会导致用户无法享受优惠金额**
- 若needPay=false（实付零元）→ 跳过步骤11，直接进入步骤12

### 步骤11：支付

调用支付宝支付能力完成付款。

**⚠️ 最高优先级铁律：AliTradePayTool必须传递tradeNO。tradeNO从【{{createOrder}}】返回的tradeNo获取，不是orderId。**

调用 `AliTradePayTool(tradeNO)` 拉起支付宝收银台
- **tradeNO必填**：从【{{createOrder}}】返回的 **tradeNo** 获取
- **bizType** 该参数不要传递
- ⚠️ **【强制必传】`configuration` 必须传 `{"skipPrePayResultCheck":"true"}`，严禁省略或传 false。，若省略或未传该参数将触发额外确认页，破坏交易链路；任何情况下均不得省略，必须明确传入 "configuration" 以跳过确认页直接完成支付）

- 调用完成后，进入步骤12

### 步骤12：查询订单状态

调用 `【{{queryOrderDetailInfo}}】(orderIdStr)`
- 根据orderStatus展示状态：10(待付款)、20(下单成功)、30(精心制作中)、60(等待取餐)、80(已完成)
- 调用terminate返回summary：
  - summary_type: "resultPageService"
  - summary: [{"title":"【{{brandName}}】 | {商品名称} x{数量}","logo":"【{{brandLogo}}】","url":"【{{miniAppOrderListUrl}}】","text":"订单状态说明"}]
    - 若支付完成 → text: 已下单，取餐码{takeMealCodeInfo.code}
    - 若支付失败 → text: 支付未完成

## 注意事项

### 核心铁律

| 规则 | 说明 |
|------|------|
| 门店澄清 | 调用deptName参数**且**返回1个门店才跳过澄清 |
| productAttrs 透传不解析 | `【{{searchProductForMcp}}】`/`【{{previewOrder}}】`/`【{{switchProduct}}】` 的出参 `productAttrs` 可能是 **JSON 列表**，也可能是 **"osskey" 开头的缓存变量字符串**。无论哪种形式，下次需要用到该出参时（如 【{{previewOrder}}】 后→ 【{{createOrder}}】、【{{switchProduct}}】 后→ 【{{previewOrder}}】）**一律原样透传整个出参对象**：是列表就传列表，是缓存字符串就传缓存字符串，**禁止自行解析/展开/重建**。 |
| 商品澄清 | 明确商品名称**且**返回1个商品才跳过澄清 |
| confirmed_parameters必传 | 步骤8.2必须传递完整confirmed_parameters（productInfoList / shopInfo / orderSummary 3个参数对象） |
| 会员授权优先 | 【{{authorizeMember}}】必须先于其他【{{brandName}}】MCP工具调用 |
| 零元订单判断 | 【{{createOrder}}】返回needPay=false时无需拉起支付 |
| 创建订单时填写优惠券 | couponCodeList不为空时必须传入 |
| 支付时传入tradeNO | AliTradePayTool必须从【{{createOrder}}】的tradeNo获取 |
| 【{{queryProductDetailInfo}}】 入参| deptId是整数型，必须转换为整数型 |
| 【{{switchProduct}}】参数真实性 | subAttr.attributeId必须从productAttrs中精确匹配attributeName取得，禁止虚构/猜测/借用ID；维度候选仅1项或目标值无精确匹配时，禁止调用【{{switchProduct}}】；调用前必须逐项通过【步骤9.2B 自检闸口】4项检查 |
| 规格仅限杯型温度甜度 | 步骤9规格切换只支持杯型/温度/甜度，奶类/加料/换商品等一律走9.2A不支持分支拒答，禁止调用【{{switchProduct}}】 |
| 不支持规格必须重调【{{previewOrder}}】 | 步骤9.2"不支持"分支必须按 ①重新调【{{previewOrder}}】 → ②intent_clarification(OB_tea-order-template_clarifyOrder+完整confirmed_parameters) 顺序执行，禁止复用历史【{{previewOrder}}】返回值、禁止跳过①、禁止confirmed_parameters为空、禁止terminate收尾 |


### 其他规则

- 多商品拦截：检测到多商品意图时调用terminate终止
- 关键词明确性：用户未明确指定门店/商品时，即使只返回1个候选也必须澄清
- skuCode以【{{queryProductDetailInfo}}】为准：【{{searchProductForMcp}}】返回的skuCode可能与默认规格不一致
- 【{{switchProduct}}】后必须【{{previewOrder}}】：规格切换后必须重新询价；且回步骤8.1 的 【{{previewOrder}}】 入参必须用 【{{switchProduct}}】 成功出参的 "osskey" 开头缓存字符串作为 productAttrs（形态B），详见核心铁律"【{{switchProduct}}】成功后回填口径"与步骤9.2 回填自检闸口
- 仅支持自提：delivery固定为"pick"
- 用户可能输入一些特殊需求，如"接着找""找个最便宜的""找个最近的"，**绝对禁止陷入工具调用循环**

## 示例

### 查询订单流程

| 场景 | 用户输入 | 执行逻辑 |
|------|---------|---------|
| 查询订单 | "查询我的【{{brandName}}】订单" | 步骤1检测订单意图 → 步骤2授权 → 步骤3返回订单列表跳转链接 |
| 取消订单 | "取消【{{brandName}}】订单" | 步骤1检测取消意图 → 步骤2授权 → 步骤3返回订单列表跳转链接，引导小程序操作 |

### 点单流程

| 场景 | 用户输入 | 执行逻辑 |
|------|---------|---------|
| 多商品拦截 | "我要点一杯拿铁和一杯美式" | 步骤2检测多商品意图 → terminate终止 |
| 完整流程 | "帮我点一杯【{{brandName}}】【{{hotProductName}}】" | 授权 → 搜索门店(返回3家) → 澄清选择门店 → 搜索商品 → 澄清选择商品 → 预览 → 创单 → 支付|
| 跳过澄清（唯一情况） | "去蚂蚁A空间店点一杯【{{hotProductName}}】" | 搜索门店(deptName="蚂蚁A空间"返回1家) → 跳过门店澄清 → 搜索商品(返回1个) → 跳过商品澄清 → 预览 → 创单 |
| 关键词不明确需澄清 | "附近【{{brandName}}】推荐一杯" | 搜索门店(未传deptName返回1家) → 必须澄清门店 → 搜索商品(query="推荐"返回1个) → 必须澄清商品 |
| 修改规格 | "点杯拿铁，换成热的大杯" | 默认规格预览 → 请求修改规格 → 【{{queryProductDetailInfo}}】 → 【{{switchProduct}}】 → 预览 → 确认 → 创单 |
| 修改规格不存在 | "点杯拿铁，换成中杯" | 默认规格预览 → 请求修改规格 → 【{{queryProductDetailInfo}}】 发现无中杯 → 预览并提示"不支持中杯规格" |
| 多杯同品类 | "点3杯【{{hotProductName}}】" | 正常流程，amount=3 |
| 修改规格不存在(拒答) | "点杯拿铁，换成中杯热"(无此组合) | 【{{queryProductDetailInfo}}】 返回"该规格属性不存在" → 用原规格回8.1 【{{previewOrder}}】 → clarification_phrase 提示"该商品不支持该规格，如需修改请到【{{brandName}}】小程序完成" → 后续流程 |
| 维度候选仅1项(拒答) | "橙C美式，改成热的"(温度维度仅"冰"1项) | 【{{queryProductDetailInfo}}】 温度候选仅1项 → 自检闸口①判定不支持 → 重调【{{previewOrder}}】 → intent_clarification 提示"该商品不支持热的，如需修改请到【{{brandName}}】小程序完成" → 禁止调用【{{switchProduct}}】、禁止虚构subAttr.attributeId |
| 零元订单 | "点杯柠檬水"（有券抵扣） | 预览 → 创单返回needPay=false → 跳过支付 → 查询取餐码 |
