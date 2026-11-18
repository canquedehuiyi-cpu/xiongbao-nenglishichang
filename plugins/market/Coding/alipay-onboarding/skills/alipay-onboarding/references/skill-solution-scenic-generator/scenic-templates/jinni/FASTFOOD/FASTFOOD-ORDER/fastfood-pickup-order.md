---
name: 【{{skillName}}】
description: >
  【{{brandName}}】到店自提点单技能，覆盖门店搜索、商品搜索、订单预览、创建订单全流程。
  当用户表达"吃【{{brandName}}】"、"点【{{brandName}}】"、"【{{brandName}}】三件套"、"附近【{{brandName}}】"、"来个【{{brandCategoryWord}}】"等意图时使用。
  支持单品和套餐下单，支持即时下单模式（多商品）和选品模式。
  仅支持到店自提模式（packType=1外带），修改规格/取消订单等操作引导至【{{brandName}}】小程序。
  订单查询和取消引导功能：查询用户的到店自提订单列表，当用户表达"查询我的【{{brandName}}】订单"、"我的【{{brandName}}】订单"、"【{{brandName}}】订单列表""取消【{{brandName}}】订单"等意图时使用。
---

# 【{{brandName}}】点单技能

## 功能概述

支持以下功能：
- **订单查询和取消引导**：跳转到【{{brandName}}】小程序订单列表页面查看所有订单
- **点单功能**：
  - 门店搜索：根据位置搜索附近【{{brandName}}】门店
  - 商品搜索：在指定门店搜索商品，支持单品和套餐
  - 订单预览：确认价格、优惠信息
  - 创建订单：下单并返回支付信息
  - 订单查询：查询订单状态和取餐码

仅支持到店自提模式（packType=1外带），不支持外送。修改规格、取消订单等操作引导至【{{brandName}}】小程序。

## 依赖工具

### 一方服务（支付宝侧）

| server code | tool name | 说明 |
| --- | --- | --- |
| jsapi | AliTradePayTool | 支付宝端侧支付收银台 |

### 三方服务（【{{brandName}}】侧）

| server code | tool name | 说明 |
| --- | --- | --- |
| 【{{mcpPrefix}}】 | 【{{storeList}}】 | 根据经纬度查询附近【{{brandName}}】门店列表，按距离排序 |
| 【{{mcpPrefix}}】 | 【{{itemList}}】 | 根据关键词和门店搜索推荐商品，返回商品列表含默认规格和价格 |
| 【{{mcpPrefix}}】 | 【{{updateCart}}】 | 更新购物车（加购+预览），返回购物车ID和价格信息 |
| 【{{mcpPrefix}}】 | 【{{orderSubmit}}】 | 提交订单，使用购物车ID创建【{{brandName}}】订单 |
| 【{{mcpPrefix}}】 | 【{{queryOrderDetail}}】 | 查询订单详情，含订单状态、商品信息和门店信息 |
| 【{{mcpPrefix}}】 | intent_clarification | 意图澄清工具，用于让用户选择门店或商品 |
| 【{{mcpPrefix}}】 | terminate | 流程终止工具，用于异常场景拦截 |
| 【{{mcpPrefix}}】 | 【{{kb-knowledge-base-batch-search}}】 | 【{{brandName}}】餐品知识库召回，将用户query中的餐品名称转换为品牌可识别的关键字 |

## 执行流程

【{{brandName}}】技能包含两个独立的主流程：查询订单流程和点单流程。系统首先通过步骤1检测用户意图，然后路由到对应流程。

### 步骤1：订单相关意图检测（前置路由）

检测用户输入是否包含查询订单或取消订单的意图：
- 关键词检测："查询"、"我的"、"订单"、"取消"、"退"等
- **若检测到订单相关意图**（查询订单或取消订单）→ 进入**查询订单流程**（从步骤2开始）
- **若未检测到订单相关意图**→ 进入**点单流程**（从步骤2开始）

**订单相关意图判断规则**：
- **查询订单意图**：用户输入包含"【{{brandName}}】"/"【{{brandCategoryWord}}】"相关关键词 **且** 包含"订单"/"查询"/"我的订单"/"去哪"/"在哪"相关关键词
  - 示例："查询我的【{{brandName}}】订单"、"我的【{{brandName}}】订单"、"【{{brandName}}】订单列表"、"查询【{{brandCategoryWord}}】订单"、"我的【{{brandName}}】订单去哪了"、"【{{brandName}}】订单在哪里"
- **取消订单意图**：用户输入包含"【{{brandName}}】"/"【{{brandCategoryWord}}】"相关关键词 **且** 包含"取消"/"退"/"不要了"相关关键词
  - 示例："取消【{{brandName}}】订单"、"退款"、"我想退掉【{{brandName}}】的订单"、"【{{brandName}}】订单不要了"
  - **注意**：取消订单和退款功能不在MCP范围内，引导用户跳转到【{{brandName}}】小程序订单列表页自行操作
- **点单意图**：用户输入包含点单相关关键词（"点"、"买"、"吃"、"来个"等）
  - 示例："点【{{brandName}}】"、"来个【{{brandCategoryWord}}】"、"【{{brandName}}】三件套"、"附近【{{brandName}}】"

---

## 查询订单流程

**适用意图**：查询订单、取消订单、退款等订单相关操作

### 步骤2：跳转订单列表页

调用 `terminate` 工具，返回订单列表页跳转链接，summary_type 为"resultPageService"
- summary：以 dict list 格式返回跳转信息 [{"title":"xxx","logo":"xxxx","url":"xxx","text":"xxxx"}]
  - title：标题，固定为 "【{{brandName}}】 | 我的订单"
  - logo：【{{brandLogo}}】
  - url：跳转到【{{brandName}}】小程序订单列表页的链接，固定为"【{{miniAppOrderListUrl}}】"
  - text：提示文本，固定为 `"点击进入【{{brandName}}】订单列表"`

**查询订单流程注意事项**：
- **仅跳转订单列表**：此技能仅支持跳转到【{{brandName}}】小程序订单列表页面，不支持查询具体订单详情
- **固定URL**：订单列表页URL固定，不支持跳转到具体订单详情页
- **terminate必须调用**：必须调用terminate工具返回跳转链接，不能直接返回文本

---

## 点单流程

### 步骤2：门店搜索

**在这一步之前不得调用intent_clarification**

调用 `【{{storeList}}】(keyword?, platformType)`

**⚠️ 门店关键词过滤铁律（强制执行）**：
- **禁止将品牌名作为关键词**：以下关键词**绝对禁止**作为keyword参数传入，因为它们不是有效的门店搜索关键词：
  - "【{{brandName}}】"、品牌英文缩写、品牌别名
  - "【{{brandName}}】到店点单"、"【{{brandName}}】点单"、"点【{{brandName}}】"
  - "【{{brandName}}】外卖"、"【{{brandName}}】下单"
- **允许的关键词类型**：
  - 具体门店名称："西湖店"、"银泰店"、"万达店"
  - 地址信息："西溪银泰"、"滨江宝龙"、"城西银泰"
  - 地标建筑："西湖"、"钱江新城"
- **关键词为空时**：若用户未提供有效的门店关键词，**不传keyword参数**，接口会返回附近的【{{brandName}}】门店列表

**正确示例**：
- 用户输入："去西湖店吃【{{brandName}}】"→ keyword="西湖店" ✓
- 用户输入："【{{brandName}}】到店点单"→ **不传keyword** ✓
- 用户输入："附近【{{brandName}}】"→ **不传keyword** ✓

**错误示例**：
- 用户输入："【{{brandName}}】到店点单"→ keyword="【{{brandName}}】" ✗（禁止）
- 用户输入："点【{{brandName}}】"→ keyword="【{{brandName}}】" ✗（禁止）

调用参数说明：
- 若用户提供了有效门店名称或地址关键词→ 传入 keyword 参数进行模糊匹配
- 若未提供有效门店关键词→ **不传keyword参数**
- 若接口失败→ 返回"查询门店失败，请稍后再试"，流程终止
- 若返回门店列表为空→ 返回"附近暂无正在营业中的【{{brandName}}】门店，请尝试其他区域"，流程终止
- 若返回门店列表不为空→ 进入步骤3

### 步骤3：意图澄清（用户选择门店）

门店列表返回后，选择距离最近的**前3个**，调用 `intent_clarification` 让用户选择门店：
- intent_type 使用 `clarifyShopChoice`
- missing_parameters 中设置一个参数对象：
  - parameter_name：门店列表
  - candidate_values：将【{{storeList}}】返回的每个门店的JSON字符串解析为**JSON对象**放入列表，**不允许直接传入JSON字符串**，每个对象包含以下字段：
    - deptId：门店ID（从shop_id获取）
    - deptName：门店名称（从name获取），**注意：若门店名中含有双引号，请用「」替换，避免JSON解析错误**
    - address：门店地址
    - distance：距离（从distance获取，如"1.1km"）
  - 示例 candidate_values 单项：
    ```json
    {
      "deptId": "HZ3138",
      "deptName": "西湖店",
      "address": "杭州市西湖区...",
      "distance": "1.1km"
    }
    ```
- 等待用户选择具体的门店
- 用户选择后，进入步骤4

### 步骤4：餐品关键字转换

**⚠️ 餐品名称抽取铁律（强制执行）**：
- **禁止抽取品牌名**：以下关键词**绝对禁止**作为餐品名称抽取：
  - "【{{brandName}}】"、品牌英文缩写、品牌别名
- **示例说明**：
  - 用户输入："【{{brandName}}】到店取" → 无法提取有效餐品名称 → 跳过知识库检索，keyword传空值
  - 用户输入："点【{{brandName}}】" → 无法提取有效餐品名称 → 跳过知识库检索，keyword传空值
  - 用户输入："吃【{{brandName}}】【{{brandCategoryWord}}】"→ 提取"【{{brandCategoryWord}}】"，禁止提取"【{{brandName}}】"→ 调用知识库检索
  - 用户输入："【{{brandName}}】三件套" → 提取"三件套"，禁止提取"【{{brandName}}】"→ 调用知识库检索

**处理流程（强制执行）**：
1. **若未从用户原始query中解析出有效餐品名称（或只解析出品牌名/品牌英文缩写/品牌别名）**：
   - **跳过知识库检索**，不调用`【{{kb-knowledge-base-batch-search}}】`
   - **直接进入步骤5**，【{{itemList}}】的keyword参数传空值：`{"keywords": []}`
   - **禁止调用`intent_clarification`工具让用户输入餐品名称**
2. **若解析出有效餐品名称**：
   - 调用 `【{{kb-knowledge-base-batch-search}}】(request)` 进行关键字转换

**⚠️ 最高优先级铁律：步骤5的keyword参数必须且只能使用本步骤【{{kb-knowledge-base-batch-search}}】返回的show_name作为检索词，绝对禁止使用用户原始输入中的任何关键字。**

调用 `【{{kb-knowledge-base-batch-search}}】(request)` 将用户输入的餐品名称转换为品牌可识别的检索词，可从用户原始query中提取的餐品名包括【{{brandCategoryWord}}】等。
- request调用示例
  ```json
  {
    "queryList": [
      "汉堡包",
      "套餐"
    ],
    "knowledgeBaseId":"202606189*****H00473014",
    "topK":1
  }
  ```
- query必须**原样透传**用户原始query，不得进行改动
- 返回结果解析：
  ```json
  {
    "data": {
      "汉堡包": {
        "hits": [
          {"content": "{\"priority\":\"1\",\"show_name\":\"汉堡\"}"}
        ]
      },
      "薯条": {
        "hits": [
          {"content": "{\"priority\":\"1\",\"show_name\":\"薯条\"}"}
        ]
      }
    }
  }
  ```
- 解析方式：
  1. 遍历 `data` 对象的所有**一级键**（如"汉堡包"、"冰可乐"），这些是从用户query中提取的关键词
  2. 对每个关键词，检查其对应的 `hits` 数组是否有元素
  3. 若有hits，解析第一个hit的 `content` 字段（JSON字符串），提取 `show_name` 字段作为检索词
  4. 若无hits或解析失败，则该关键词无对应检索词
- **检索词使用规则（强制执行）**：
  - **有show_name**：必须使用show_name作为【{{itemList}}】的检索词，**绝对禁止**使用用户原始输入中的任何关键字
  - **无show_name**：若某关键词在data中无对应检索词，则使用该关键词本身作为检索词
  - **禁止补全**：如果data中只包含部分关键词的映射，**绝对禁止**从用户原始输入中补全缺失的关键词
  - **禁止遗漏**：data中的每个关键词都必须处理，不能遗漏
- **执行流程传递**：将解析出的检索词列表传递到步骤5，用于构建【{{itemList}}】的keyword参数
- **数量提取**：从用户原始输入中提取每个关键词对应的数量，用于步骤5的num字段

**⚠️ 示例说明（重要）**：
| 用户原始输入 | 处理方式 | 步骤5可用的keyword |
|-------------|---------|-------------------|
| "【{{brandName}}】到店取" | 跳过知识库检索 | `{"keywords": []}` ✓ 品牌名禁止抽取，keyword传空值 |
| "点【{{brandName}}】" | 跳过知识库检索 | `{"keywords": []}` ✓ 品牌名禁止抽取，keyword传空值 |
| "【{{brandName}}】【{{brandCategoryWord}}】" | 调用知识库，返回`{"【{{brandCategoryWord}}】":{"hits":[{"content":"{\"show_name\":\"【{{brandCategoryWord}}】\"}"}]}}` | `[{"keyword":"【{{brandCategoryWord}}】","num":1}]` ✓ 提取品类词，禁止提取品牌名 |
| "2个汉堡和1杯可乐" | 调用知识库，返回`{"汉堡":{"hits":[{"content":"{\"show_name\":\"汉堡\"}"}]},"可乐":{"hits":[{"content":"{\"show_name\":\"可乐\"}"}]}}` | `[{"keyword":"汉堡","num":2}, {"keyword":"可乐","num":1}]` ✓ 全部使用show_name，**禁止遗漏** |
| "2个汉堡和1杯可乐" | 调用知识库，返回`{"汉堡":{"hits":[{"content":"{\"show_name\":\"汉堡\"}"}]}}` | `[{"keyword":"汉堡","num":2}]` ✓ 只用汉堡，**禁止补全可乐** |
| "汉堡可乐蛋挞" | 调用知识库，返回`{"汉堡":{"hits":[{"content":"{\"show_name\":\"汉堡\"}"}]},"可乐":{"hits":[{"content":"{\"show_name\":\"可乐\"}"}]}}` | `[{"keyword":"汉堡","num":1}, {"keyword":"可乐","num":1}]` ✓ 只用汉堡可乐，**禁止补全蛋挞** |
| "蛋挞可乐" | 调用知识库，返回`{"蛋挞":{"hits":[]},"可乐":{"hits":[{"content":"{\"show_name\":\"可乐\"}"}]}}` | `[{"keyword":"蛋挞","num":1}, {"keyword":"可乐","num":1}]` ✓ 蛋挞无show_name用原词，可乐用show_name |
| "三件套" | 调用知识库，返回`{}` 空对象 | 使用用户输入中抽取的`[{"keyword":"三件套","num":1}]`|

### 步骤5：商品搜索

**⚠️ 最高优先级铁律：【{{itemList}}】工具只能调用一次，绝对禁止根据返回结果多次调用。无论返回的商品是否完全匹配用户需求，都只根据instant_order字段决定下一步流程，不得重新搜索。**

**keyword参数规则（强制执行）**：
- **若步骤4跳过知识库检索**：keyword参数传空值 `{"keywords": []}`
- **若步骤4调用了知识库**：keyword参数必须且只能使用步骤4解析出的检索词（show_name或关键词本身），绝对禁止从用户原始输入(original_query)中抽取或补全任何检索词，也禁止遗漏步骤4中解析出的关键词

调用 `【{{itemList}}】(shop_id, keyword, original_query, platformType)`

- **必填参数**：
  - shop_id（门店ID）：门店ID
  - keyword（商品关键词，JSON格式）：若步骤4跳过知识库检索则传空值，否则使用步骤4解析的检索词
  - original_query（用户原始query）：用户原始输入，用于日志记录
  - platformType：固定为"【{{platformType}}】"

- **keyword构建规则（强制执行）**：
  - **步骤4跳过知识库检索时**：keyword传空值 `{"keywords": []}`
  - **步骤4调用知识库时**：
    - **keyword字段**：必须且只能来自步骤4解析的show_name或关键词本身，**绝对禁止**从original_query中抽取
    - **num字段**：从用户原始输入中提取对应关键词的数量
    - **禁止补全**：如果步骤4只返回了部分关键词的映射，**绝对禁止**从original_query中补全缺失的关键词

- keyword参数格式（必须以JSON对象格式）：
  ```json
  {
    "keywords": [
      {"keyword": "汉堡", "num": 2},
      {"keyword": "可乐", "num": 1}
    ]
  }
  ```

- 返回结果包含：
  - instant_order：是否即时下单模式（true=即时下单，false=选品模式）
  - item_list：商品列表
  - satisfaction_level：满足度（fully完全满足/partially部分满足/none不满足）
  - hint：关键词匹配提示信息（如`{"keywords":{"三件套":"不满足","薯条":"满足"}}`）

**⚠️ 返回结果处理铁律（强制执行）**：
- **只能调用一次**：【{{itemList}}】工具在整个流程中只能调用一次，**绝对禁止**根据返回结果（如satisfaction_level、hint等字段）重新调用【{{itemList}}】
- **忽略satisfaction_level和hint字段**：即使satisfaction_level为"partially"（部分满足）或hint显示某些关键词"不满足"，也**必须忽略**这些信息，不再补充搜索
- **仅根据instant_order决定流程**：无论返回的商品是否符合用户预期，都只根据instant_order字段决定下一步

- 若商品列表为空→ 调用terminate工具，返回"未找到相关商品，请前往【{{brandName}}】小程序操作"
- 若商品列表不为空→ **只判断instant_order字段**：
  - **instant_order=true（即时下单模式）**：**无条件直接进入步骤7订单预览**，使用item_list中返回的商品下单，不管是否完全匹配用户需求
    - **⚠️ 商品独立性铁律**：item_list中的每个商品必须**独立处理**，即使多个商品的item_id相同但其他字段（sale_price、origin_price、ext_info等）不同，也**绝对禁止合并或修改数量**
    - **原样透传**：item_list中的所有商品必须原样透传到步骤7，保持每个商品的完整独立性
  - **instant_order=false（选品模式）**：直接进入步骤6让用户选择商品

**⚠️ 错误示例（绝对禁止）**：
- 用户输入"帮我点一份三件套和一份薯条"，知识库返回["三件套","薯条"]
- 调用【{{itemList}}】后返回instant_order=true，但item_list只有薯条，hint显示`{"keywords":{"三件套":"不满足","薯条":"满足"}}`
- **错误做法**：再次调用【{{itemList}}】分别搜索三件套和薯条 ❌
- **正确做法**：直接进入步骤7，将item_list中的薯条加入购物车下单 ✓

### 步骤6：意图澄清（用户选择商品）

调用 `intent_clarification` 让用户选择商品：
- intent_type 使用 `clarifyProductHtml`
- 如果【{{itemList}}】搜索出的商品包含用户实际希望的商品或有类似商品，clarification_phrase应提示 `已搜索到xx，为你推荐以下商品`
- 如果【{{itemList}}】搜索出的商品不包含用户实际希望的商品，clarification_phrase应提示 `未搜索到xx，推荐了以下商品`
- missing_parameters 中设置一个参数对象：
  - parameter_name：商品列表
  - candidate_values：将 itemList 返回的每个商品的JSON字符串解析为**JSON对象**放入列表，**不允许直接传入JSON字符串**，每个对象包含以下字段：
    - productId：商品ID（从item_id获取）
    - productName：商品名称（从name获取），**注意：若商品名中含有双引号，请用「」替换，避免JSON解析错误**
    - pictureUrl：商品主图URL（从image_url获取）
    - estimatePrice：商品预估到手价（从sale_price获取，**必须移除货币符号**，如果有"起"字需保留，表示最低价）
    - initialPrice：商品面价（从origin_price获取，**必须移除货币符号**，如果有"起"字需保留，表示最低价）
    - subitems：**套餐专属字段**，仅当type="bundle"时存在，包含套餐子商品列表，**JSON格式，从items原样透传**
- confirmed_parameters 中设置多个参数对象，格式如下：
 ```json
  {
    "confirmed_parameters": [
      {
        "parameter_name": "appUrl",
        "parameter_value": "小程序菜单页跳转链接"
      },
      {
        "parameter_name": "deptId",
        "parameter_value": "门店Id（从shop_id获取）"
      }
    ]
  }
  ```
- appUrl的格式为：`【{{miniAppMenuPath}}】`，其中shop_id即为用户从【{{storeList}}】选择的shop_id
- **单品与套餐区分**：
  - type="product"（单品）：不包含subitems字段
  - type="bundle"（套餐）：必须包含subitems字段
- 用户选择商品后，进入步骤7
- 若用户以自然语言形式更换商品、添加不在预览页中的商品（如"我想换成汉堡""另外加一份蛋挞"）→ 进入步骤4重新拼接原有关键词检索

### 步骤7：订单预览

**⚠️ 【{{updateCart}}】阶段的商品组合限制（强制规则）**

由于【{{brandName}}】技能的多商品下单机制，**【{{updateCart}}】阶段仅支持以下三种商品组合情况**：

| 序号 | 场景 | instant_order值 | 商品选择流程 | 商品组合说明 |
|------|------|----------------|-------------|-------------|
| 1 | 即时下单模式（单品） | true | 跳过商品选择，直接进入订单预览 | 【{{itemList}}】返回的商品列表包含1个商品（单品或套餐） |
| 2 | 即时下单模式（多品） | true | 跳过商品选择，直接进入订单预览 | 【{{itemList}}】返回的商品列表包含多个商品（多个单品、多个套餐、或单品+套餐混合） |
| 3 | 选品模式（单品） | false | 用户选择1次商品后进入订单预览 | 用户从商品列表中选择1个商品（单品或套餐） |

**⚠️ 不支持的商品组合情况**：
- 在订单预览阶段（步骤7.3），用户要求添加新商品、更换商品、修改规格等操作，**无法在当前流程中完成**，因为这些操作会破坏上述三种允许的商品组合情况。
- 若用户需要修改商品组合，必须重新开始点单流程或在【{{brandName}}】小程序中操作。

**步骤7.1：构建请求参数**

**⚠️ 最高优先级铁律：商品独立性（强制执行）**
- **instant_order=true时**：【{{itemList}}】返回的item_list必须**原样透传**到【{{updateCart}}】，**绝对禁止合并相同item_id的商品**
- **商品独立性**：即使多个商品的item_id相同，只要其他任何字段（name、sale_price、origin_price、ext_info等）不同，都必须保持为**独立的商品项**
- **禁止修改数量**：每个商品的quantity必须保持【{{itemList}}】返回的原始值（通常为1），**禁止通过合并来累加数量**

基本参数包含：
- **shop_id**：门店ID
- **item_list**：商品列表，每项需包含：
  - item_id：商品ID
  - name：商品名称
  - type：商品类型（bundle套餐/product单品）
  - quantity：商品数量（**保持【{{itemList}}】返回的原始值，禁止修改**）
  - origin_price：原始价格
  - sale_price：优惠后价格
  - ext_info：扩展信息，**必须从【{{itemList}}】返回结果中原样透传**
  - items：子品列表，**必须从【{{itemList}}】返回结果中原样透传**

**⚠️ 错误示例（绝对禁止）**：
- 【{{itemList}}】返回：`[{"item_id":"A001","name":"和牛堡套餐","sale_price":"¥20","ext_info":{...}}, {"item_id":"A001","name":"和牛堡套餐","sale_price":"¥30","ext_info":{...}}]`（相同item_id但价格不同）
- **错误做法**：合并为一个商品，quantity=2，使用更高价格¥30 ❌
- **正确做法**：保持两个独立商品项，分别透传 ¥20和¥30的商品 ✓

如果是instant_order=true即时下单模式，从【{{itemList}}】原样透传所有商品项，保持每个商品的独立性和完整性。

**步骤7.2：调用 【{{updateCart}}】**

调用 `【{{updateCart}}】(shop_id, item_list, platformType)`
- 请求参数格式：
  ```json
  {
    "shop_id": "HZ3138",
    "item_list": [
      {
        "item_id": "商品ID",
        "name": "商品名称",
        "type": "是否为套餐",
        "quantity": 1,
        "items": [],
        "origin_price": "¥21",
        "sale_price": "¥10.5",
        "ext_info": {
          "menuFlag": "...",
          "menuFlagType": "...",
          "payload": "...",
          "promotionCode": "...",
          "promotionPriceFlag": "..."
        },
      },
    ],
    "platformType": "【{{platformType}}】"
  }
  ```
- **必填参数**：shop_id、item_list、platformType
- **商品独立性铁律（强制执行）**：
  - item_list必须保持步骤7.1构建的商品列表结构，**绝对禁止合并相同item_id的商品**
  - 每个商品项必须独立存在，即使item_id相同但价格、ext_info等字段不同
  - **禁止修改quantity字段**：必须使用【{{itemList}}】返回的原始quantity值
- **ext_info 必须透传**：item_list中的ext_info必须从【{{itemList}}】返回结果中原样透传
- 若接口失败→ 返回"更新购物车失败，原因是：${resultMsg}"
- 成功→ 返回购物车信息，进入步骤7.3

**步骤7.3：意图澄清（展示订单预览）**

**⚠️ 最高优先级铁律：confirmed_parameters是必传参数，绝对禁止缺失。若intent_clarification调用时confirmed_parameters为空或未传递，将导致订单预览页面无法正确展示。**

调用 `intent_clarification` 让用户确认订单：
- intent_type 使用 `clarifyOrderPrice`
- clarification_phrase 使用默认提示语（不传或传空）
- missing_parameters 固定传空数组 `[]`
- **confirmed_parameters（强制必传，格式如下）**：
  ```json
  {
    "confirmation_phrase": "订单信息已确认，帮我继续支付",
    "clarification_phrase": "",
    "function_name": "【{{skillName}}】",
    "missing_parameters": [],
    "intent_type": "clarifyOrderPrice",
    "confirmed_parameters": [
      {
        "parameter_name": "orderItems",
        "parameter_value": [
          {
            "itemId": "100125470",
            "itemName": "鸡鸡鸭鸭宝宝蛋挞(2只)",
            "itemImageUrl": "https://pcp-pic.hwwt8.com/1/01012/images/100125470__ALL__S__20260604154121775.jpg",
            "originalPrice": "¥10",
            "currentPrice": "¥10",
            "quantity": 1,
            "subitems": "套餐子商品列表（仅套餐有，格式同步骤6）",
            "deptId": "HZ1400",
            "deptName": "蚂蚁A空间店",
            "ext_info": {
              "menuFlag": "S",
              "menuFlagType": "2",
              "payload": "19",
              "promotionCode": "7YY41B70C6.1",
              "promotionPriceFlag": "P"
            },
            "type": "product"
          }
        ]
      },
      {
        "parameter_name": "orderSummary",
        "parameter_value": {
          "totalOriginalAmount": "¥10",
          "totalDiscountAmount": "¥0",
          "payableAmount": "¥10",
          "couponCodeList": "优惠券编码列表（如有）"
        }
      },
      {
        "parameter_name": "skillName",
        "parameter_value": "【{{skillName}}】"
      },
      {
        "parameter_name": "appUrl",
        "parameter_value": "小程序内跳转链接，如果orderItems只有一个item，跳转商品修改详情页，如果orderItems有多个item，跳转购物车详情页"
      }
    ]
  }
  ```

**⚠️ originalPrice必填铁律（强制执行）**：
- originalPrice字段**绝对不可为空字符串""或null**
- 如果`【{{updateCart}}】`返回的`item_list[].origin_price`为空、null或不存在，**必须**使用`item_list[].sale_price`作为值
- 此字段影响订单预览页面的价格展示，必须确保有值

**confirmed_parameters 数据提取规则（强制执行）**：
1. **orderItems（必传）**：
  - itemId：从`【{{updateCart}}】`工具返回的 `item_list[].item_id` 获取
  - itemName：从`【{{updateCart}}】`工具返回的 `item_list[].name` 获取
  - itemImageUrl：从`【{{updateCart}}】`工具返回的 `item_list[].image_url` 获取
  - **originalPrice（强制必填，绝对不可为空）**：
    - 优先从`【{{updateCart}}】`工具返回的 `item_list[].origin_price` 获取
    - **若origin_price为空或不存在，必须使用`item_list[].sale_price`作为fallback**
    - **绝对禁止传递空字符串""或null**，会影响订单预览页面展示
  - currentPrice：从`【{{updateCart}}】`工具返回的 `item_list[].sale_price` 获取
  - quantity：从`【{{updateCart}}】`工具返回的 `item_list[].quantity` 获取
  - subitems：从`【{{updateCart}}】`工具返回的 `item_list[].items` 获取（仅套餐有）
  - deptId：从`【{{updateCart}}】`工具返回的 `shop_detail.name` 获取
  - deptName：从`【{{updateCart}}】`工具返回的 `shop_detail.shop_id` 获取
  - ext_info：从`【{{itemList}}】`工具返回的 `item_list[].ext_info` 获取，**不得从updateCart的结果中获取，且必须原样透传，不能缺失**
  - type：从`【{{updateCart}}】`工具返回的 `item_list[].type` 获取

2. **orderSummary（必传）**：
  - totalOriginalAmount：
    - 优先从`【{{updateCart}}】`工具返回的 `origin_price` 获取
    - **若origin_price为空或不存在，必须使用`sale_price`作为fallback**
    - **绝对禁止传递空字符串""或null**，会影响订单预览页面展示
  - totalDiscountAmount：
    - 优先从`【{{updateCart}}】`工具返回的 `coupon_desc` 获取，提取具体金额，如"已优惠¥{discount_amount}"，应提取discount_amount
    - 若无 `coupon_desc` 字段，则取0
  - payableAmount：从返回结果的 `sale_price` 字段获取
  - couponCodeList：如有优惠券则传入

3. **skillName（必传）**：固定为 `"【{{skillName}}】"`

4. **appUrl（必传）**：小程序内跳转链接
  - 如果orderItems只有一个item，跳转商品修改详情页，格式为`【{{miniAppProductDetailPath}}】`，其中`{shop_id}`为门店ID，`{item_id}`为商品ID，
  - 如果orderItems有多个item，跳转菜单页，格式为`【{{miniAppMenuPath}}】`，其中`{shop_id}`为门店ID。

**用户响应处理规则（强制执行）**：

**⚠️ 响应类型判断铁律（最高优先级）**：
判断依据为澄清工具返回的`nonStandardResult`字段和`clarifyReplyMode`字段：
- **结构化响应**：`clarifyReplyMode="CARD_CLICK"` **且** `nonStandardResult`为JSON字符串（包含itemId、quantity等结构化字段）
- **自然语言响应**：`clarifyReplyMode="TEXT"` **或** `nonStandardResult`为纯文本（如"换成2份"、"我要3个"等）

**响应示例**：

结构化响应示例（直接进入步骤8）：
```json
{
  "standardResult": null,
  "nonStandardResult": "{\"itemId\":\"16513\",\"quantity\":{\"mode\":0,\"value\":1},\"totalDiscountAmount\":\"-¥0\",\"deptId\":\"1231234273\",\"skuCode\":\"SP11392-00010\",\"payableAmount\":\"¥0.01\"}",
  "standard": false,
  "clarifyReplyMode": "CARD_CLICK",
  "requestId": null,
  "stageDuration": null
}
```

自然语言响应示例（需重新展示订单预览）：
```json
{
  "standardResult": null,
  "nonStandardResult": "换成2份",
  "standard": false,
  "clarifyReplyMode": "TEXT",
  "requestId": null,
  "stageDuration": null
}
```

**处理规则**：

1. **结构化响应（clarifyReplyMode="CARD_CLICK" 且 nonStandardResult为JSON字符串）**：
   - **直接进入步骤8**，使用用户确认的数量作为入参传递
   - **禁止再次调用intent_clarification展示订单预览**

2. **自然语言响应（clarifyReplyMode="TEXT" 或 nonStandardResult为纯文本）更换数量**：
   - **必须返回步骤7.2**，调用【{{updateCart}}】重新询价
   - **然后进入步骤7.3**，调用intent_clarification重新展示订单预览让用户再次确认
   - **禁止直接进入步骤8**

3. **用户以自然语言响应请求修改规格、更换商品、添加不在预览页中的商品**：
   - **示例请求**："可乐换成大杯"、"我想换成汉堡"、"另外加一份蛋挞"、"把汉堡换成不辣的"
   - **处理方式（强制执行）**：
     - **重新调用 intent_clarification**
     - **必须设置 clarification_phrase 字段**，告知用户不支持该操作，示例内容：
       ```
       "clarification_phrase": "抱歉，暂不支持在订单预览阶段修改规格、更换商品或添加新商品。如需调整订单，请前往【{{brandName}}】小程序操作，或确认当前订单后下单。"
       ```
     - **原样展示当前订单预览内容**（confirmed_parameters不变）
     - **禁止重新进行商品搜索或调用【{{itemList}}】**
     - **禁止修改confirmed_parameters中的商品信息**

   - **原因说明**：
     - 【{{updateCart}}】阶段仅支持上述三种允许的商品组合情况：即时下单单品、即时下单多品、选品模式单品
     - 用户在订单预览阶段的修改请求会导致商品组合变化，超出当前流程支持范围
     - 例如：用户已选择1个汉堡（即时下单模式单品），现要求"加一份蛋挞"，这会变成多品组合，需要重新调用【{{itemList}}】判断是否支持instant_order=true的多品模式，但【{{itemList}}】只能调用一次，因此无法支持

### 步骤8：创单前询价

**⚠️ 最高优先级铁律：本步骤绝对禁止调用intent_clarification工具让用户确认。无论用户是否修改数量，调用【{{updateCart}}】询价后都必须直接进入步骤9创建订单，不得再次展示订单预览。**

调用【{{updateCart}}】，进行创单前的最后一次询价：
- 若用户在步骤7.3确认订单（未修改数量）→ 使用用户最终确认的ext_info、quantity、items等参数调用【{{updateCart}}】
- 若用户在步骤7.3确认订单（修改数量）→ 使用用户最终确认的ext_info、quantity、items等参数调用【{{updateCart}}】
- **调用【{{updateCart}}】后直接进入步骤9，禁止调用intent_clarification展示订单预览**

### 步骤9：创建订单

调用 `【{{orderSubmit}}】(shop_id, cart_id, item_list, origin_price, sale_price, ext_info, packType, platformType)`
- 请求参数格式：
  ```json
  {
    "shop_id": "HZ3138",
    "cart_id": "购物车ID，来自【{{updateCart}}】返回",
    "item_list": "从【{{updateCart}}】返回的item_list透传",
    "ext_info": {
      "transToken": "事务Token，来自【{{updateCart}}】返回的ext_info.transToken"
    },
    "packType": "1",
    "platformType": "【{{platformType}}】"
  }
  ```
- **必填参数**：shop_id、cart_id、packType、platformType
- **transToken 必传**：从【{{updateCart}}】返回的ext_info.transToken获取，确保价格一致
- **item_list 透传**：从【{{updateCart}}】返回的item_list原样透传，**如item_list[]有items字段必须原样透传，不可丢失**
- 若接口失败→ 返回"创建订单失败，原因是：${resultMsg}"
- 若成功→ 获取返回的order_id、prepay_id，进入步骤10

### 步骤10：支付

**⚠️ 最高优先级铁律：AliTradePayTool必须传递prepareId，绝对禁止传递orderId。prepareId从orderSubmit返回的prepay_id获取，不是order_id。**

调用 `AliTradePayTool(prepareId)` 拉起支付宝收银台
- **prepareId必填**：从orderSubmit返回的 **prepay_id** 获取
- **bizType** 该参数不要传递
- ⚠️ **【强制必传】`configuration` 必须传 `{"skipPrePayResultCheck":"true"}`，严禁省略或传 false。，若省略或未传该参数将触发额外确认页，破坏交易链路；任何情况下均不得省略，必须明确传入 "configuration" 以跳过确认页直接完成支付）

**⚠️ 参数传递铁律（强制执行）**：
- **正确做法**：AliTradePayTool(prepareId=prepay_id) ✓
- **错误做法**：AliTradePayTool(prepareId=order_id) ✗ **绝对禁止**
- **错误做法**：AliTradePayTool(orderId=order_id) ✗ **绝对禁止**

- 跳转至步骤11


### 步骤11：查询订单状态与取餐码

调用 `【{{queryOrderDetail}}】(order_id, platformType)`
- **必填参数**：order_id（订单编号）、platformType
- 若接口失败→ 返回"查询订单状态失败，请稍后重试"
- 根据订单状态（order_status）展示不同信息：
  - PENDING_PAYMENT：待支付
  - PAID：已支付，等待制作
  - PREPARING：制作中
  - READY：请取餐，展示取餐码
  - COMPLETED：已完成
  - CANCELLED：已取消
- 调用terminate，返回summary结果：
  - 支付成功时返回"您已成功下单{商品名称}x{数量}，请到下方订单中心查看订单详情，或进入【{{brandName}}】小程序登录查看更多餐品"
  - 支付失败时返回"支付未完成，如需继续下单，请进入【{{brandName}}】小程序登录后完成"

## 注意事项

- **订单相关意图检测**：在步骤1检测到查询订单或取消订单意图时，跳转到查询订单流程（步骤2）
- **订单列表跳转**：查询订单流程仅支持跳转到【{{brandName}}】小程序订单列表页，不支持查询具体订单详情
- **取消订单/退款处理**：取消订单和退款功能不在MCP范围内，当用户表达取消订单或退款意图时，引导用户跳转到【{{brandName}}】小程序订单列表页自行操作
- **餐品名称抽取铁律（强制规则）**：**绝对禁止**抽取品牌名/品牌英文缩写/品牌别名作为餐品名称。若用户原始query中只包含品牌名（如"【{{brandName}}】到店取"、"点【{{brandName}}】"），无法提取有效餐品名称时，**跳过知识库检索**，【{{itemList}}】的keyword参数传空值 `{"keywords": []}`。
- **餐品关键字转换（强制规则）**：**只能**使用【{{kb-knowledge-base-batch-search}}】返回的show_name作为检索词（无show_name时用关键词本身），**绝对禁止**从用户原始输入中抽取或补全任何额外的检索词。即使【{{kb-knowledge-base-batch-search}}】只返回部分关键词的映射，也不能自行补全。
- **【{{itemList}}】只调用一次（强制规则）**：**【{{itemList}}】工具在整个流程中只能调用一次**，无论返回结果是否完全满足用户需求，都**绝对禁止**重新调用【{{itemList}}】。即使satisfaction_level为"partially"或hint显示某些关键词"不满足"，也必须忽略这些字段，只根据instant_order字段决定下一步流程。
- **商品独立性铁律（强制规则）**：**instant_order=true时，【{{itemList}}】返回的商品必须保持独立性，绝对禁止合并相同item_id的商品**。即使多个商品的item_id相同但其他字段（sale_price、origin_price、ext_info等）不同，也必须保持为独立的商品项，不得通过合并来累加数量或修改价格。
- **【{{updateCart}}】阶段的商品组合限制（强制规则）**：【{{updateCart}}】阶段仅支持三种商品组合情况：（1）instant_order=true单品（2）instant_order=true多品（3）instant_order=false单品。在订单预览阶段，用户请求添加新商品、更换商品、修改规格等操作**无法支持**，必须设置clarification_phrase告知用户并在【{{brandName}}】小程序中操作。
- **创单前询价禁止展示订单预览（强制规则）**：步骤8调用【{{updateCart}}】后，**绝对禁止**再次调用intent_clarification展示订单预览。无论用户是否在步骤7.3修改了数量，都必须直接进入步骤9创建订单。
- **AliTradePayTool参数传递铁律（强制规则）**：AliTradePayTool必须传递**prepareId**（从【{{orderSubmit}}】返回的prepay_id获取），**绝对禁止传递orderId**作为支付参数。传递错误的参数会导致支付失败。
- **即时下单与选品模式区分**：【{{itemList}}】返回的instant_order字段决定流程，true跳过商品选择直接预览，false需要用户选择商品
- **多商品支持**：【{{brandName}}】支持多商品下单（多个单品、多个套餐、单品+套餐），keyword参数需包含所有商品关键词
- **套餐与单品区分**：type="bundle"表示套餐，需处理subitems子商品；type="product"表示单品
- **ext_info 透传**：item_list中的ext_info必须从【{{itemList}}】返回结果中原样透传给【{{updateCart}}】
- **transToken 必传**：【{{orderSubmit}}】的ext_info.transToken必须从【{{updateCart}}】返回的ext_info.transToken获取
- **固定参数**：packType 固定为"1"（表示外带），platformType 固定为"【{{platformType}}】"
- **澄清必要性**：门店和商品列表（选品模式）必须通过intent_clarification让用户选择
- **confirmed_parameters必传**：步骤7.3的intent_clarification调用必须包含完整的confirmed_parameters，缺失将导致订单预览页面无法展示
- **originalPrice必填（强制规则）**：订单预览中orderItems的originalPrice字段**绝对不可为空字符串""或null**。若【{{updateCart}}】返回的origin_price为空，**必须使用sale_price作为fallback值**。此字段直接影响订单预览页面的价格展示，必须确保有值。
- **JSON安全处理（强制）**：门店名称(deptName)和商品名称(productName)中若含有双引号（中文`"`、`"`或英文`"`），**必须替换为中文书名号「」**
- **距离单位处理**：如distance字段已经是格式化字符串（如"1.1km"），直接使用即可
- **intent_clarification中的价格格式**：在调用intent_clarification工具时，需移除价格字段中的货币符号，并保留"起"字（如"¥21起"->"21起"），其它工具保留原始格式
- **修改规格限制**：不支持修改商品规格，用户要求修改时引导至【{{brandName}}】小程序
- **禁止调用普通澄清**：禁止使用类型为`clarify`的intent_clarification工具

## 枚举映射

### type（商品类型）

| 枚举值 | 显示名 | 说明 |
|--------|--------|------|
| bundle | 套餐 | 包含多个子商品，需处理subitems |
| product | 单品 | 单个商品，无子商品 |

### order_status（订单状态）

| 枚举值 | 显示名 | 说明 |
|--------|--------|------|
| PENDING_PAYMENT | 待支付 | 等待支付 |
| PAID | 已支付 | 等待制作 |
| PREPARING | 制作中 | 正在制作 |
| READY | 请取餐 | 制作完成等待取餐 |
| COMPLETED | 已完成 | 订单完成 |
| CANCELLED | 已取消 | 订单取消 |

### satisfaction_level（满足度）

| 枚举值 | 显示名 | 说明 |
|--------|--------|------|
| fully | 完全满足 | 商品完全匹配用户需求 |
| partially | 部分满足 | 部分商品匹配用户需求 |
| none | 不满足 | 无匹配商品 |

## 示例

### 查询订单流程示例

#### 场景一：查询【{{brandName}}】订单列表

- 用户输入：查询我的【{{brandName}}】订单
- 执行逻辑：
  1. 步骤1：检测到查询订单意图（包含"【{{brandName}}】"和"订单"/"查询"关键词）→ 进入查询订单流程
  2. 查询订单步骤2：调用terminate，summary_type为resultPageService，展示订单页入口

#### 场景二：查看我的【{{brandName}}】订单

- 用户输入：我的【{{brandName}}】订单
- 执行逻辑：
  1. 步骤1：检测到查询订单意图→ 进入查询订单流程
  2. 查询订单步骤2：terminate返回订单列表跳转链接

#### 场景三：取消订单

- 用户输入：我要取消【{{brandName}}】订单
- 执行逻辑：
  1. 步骤1：检测到取消订单意图（包含"【{{brandName}}】"和"取消"）→ 进入查询订单流程
  2. 查询订单步骤2：terminate返回订单列表跳转链接，引导用户在小程序中自行操作取消订单

#### 场景四：退款请求

- 用户输入：我想退掉【{{brandName}}】的订单
- 执行逻辑：
  1. 步骤1：检测到取消订单/退款意图（包含"【{{brandName}}】"和"退"）→ 进入查询订单流程
  2. 查询订单步骤2：terminate返回订单列表跳转链接，引导用户在小程序中自行操作退款

### 点单流程示例

#### 场景五：用户输入仅包含品牌名（跳过知识库检索，keyword传空值）

- 用户输入：【{{brandName}}】到店取
- 执行逻辑：
  1. 步骤1：未检测到订单相关意图→ 进入点单流程
  2. 点单步骤2：【{{storeList}}】(platformType="【{{platformType}}】")（不传keyword）→ intent_clarification 选择门店
  3. 点单步骤3：选择门店
  4. 点单步骤4：从用户query中无法提取有效餐品名称（品牌名禁止抽取）→ **跳过知识库检索**
  5. 点单步骤5：【{{itemList}}】(shop_id, keyword={"keywords":[]}, platformType="【{{platformType}}】")（keyword传空值）
  6. **instant_order=false**，返回默认商品列表→ 进入步骤6商品选择
  7. 用户选择商品→ 【{{updateCart}}】→ intent_clarification 展示订单预览
  8. 用户确认→ 【{{updateCart}}】 再次询价→ 【{{orderSubmit}}】→ AliTradePayTool(prepareId=prepay_id)→ 【{{queryOrderDetail}}】

#### 场景六：单品下单（即时模式）

- 用户输入：我要一个香辣鸡腿堡
- 执行逻辑：
  1. 步骤1：未检测到订单相关意图→ 进入点单流程
  2. 点单步骤2：【{{storeList}}】(platformType="【{{platformType}}】")→ intent_clarification 选择门店
  3. 点单步骤3：选择门店
  4. 点单步骤4：【{{kb-knowledge-base-batch-search}}】(queryList=["香辣鸡腿堡"])→ 返回`{"香辣鸡腿堡":{"hits":[{"content":"{\"show_name\":\"香辣鸡腿堡\"}"}]}}`
  5. 点单步骤5：【{{itemList}}】(shop_id, keyword={"keywords":[{"keyword":"香辣鸡腿堡","num":1}]}, platformType="【{{platformType}}】")
  6. **instant_order=true**→ 直接进入步骤7订单预览，跳过步骤6商品选择
  7. 点单步骤7.2：【{{updateCart}}】(shop_id, item_list, platformType="【{{platformType}}】")
  8. 点单步骤7.3：intent_clarification 展示订单预览（**confirmed_parameters必须传递**）
  9. 用户确认→ 点单步骤8：【{{updateCart}}】 再次询价（**禁止再次展示订单预览**）
  10. 点单步骤9：【{{orderSubmit}}】→ 点单步骤10：AliTradePayTool(prepareId=prepay_id)→ 点单步骤11：【{{queryOrderDetail}}】

#### 场景七：套餐下单（即时模式）

- 用户输入：来一份三件套
- 执行逻辑：
  1. 步骤1：未检测到订单相关意图→ 进入点单流程
  2. 点单步骤2：【{{storeList}}】(platformType="【{{platformType}}】")→ intent_clarification 选择门店
  3. 点单步骤3：选择门店
  4. 点单步骤4：【{{kb-knowledge-base-batch-search}}】(queryList=["三件套"])→ 返回`{"三件套":{"hits":[{"content":"{\"show_name\":\"三件套\"}"}]}}`
  5. 点单步骤5：【{{itemList}}】(shop_id, keyword={"keywords":[{"keyword":"三件套","num":1}]}, platformType="【{{platformType}}】")
  6. **instant_order=true**，返回套餐商品（type=bundle，含subitems）
  7. 点单步骤7.2：【{{updateCart}}】→ 点单步骤7.3：intent_clarification 展示订单预览（显示子商品，**confirmed_parameters必须传递**）
  8. 用户确认→ 点单步骤8：【{{updateCart}}】 再次询价（**禁止再次展示订单预览**）
  9. 点单步骤9：【{{orderSubmit}}】→ 点单步骤10：AliTradePayTool(prepareId=prepay_id)→ 点单步骤11：【{{queryOrderDetail}}】

#### 场景八：多商品下单（即时模式）

- 用户输入：我要两个汉堡和一杯可乐
- 执行逻辑：
  1. 步骤1：未检测到订单相关意图→ 进入点单流程
  2. 点单步骤2：【{{storeList}}】(platformType="【{{platformType}}】")→ intent_clarification 选择门店
  3. 点单步骤3：选择门店
  4. 点单步骤4：【{{kb-knowledge-base-batch-search}}】(queryList=["汉堡","可乐"])→ 返回`{"汉堡":{"hits":[{"content":"{\"show_name\":\"汉堡\"}"}]},"可乐":{"hits":[{"content":"{\"show_name\":\"可乐\"}"}]}}`
  5. 点单步骤5：【{{itemList}}】(shop_id, keyword={"keywords":[{"keyword":"汉堡","num":2},{"keyword":"可乐","num":1}]}, platformType="【{{platformType}}】")
  6. **instant_order=true**，返回多个商品
  7. 点单步骤7.2：【{{updateCart}}】→ 点单步骤7.3：intent_clarification 展示订单预览（显示多个商品，**confirmed_parameters必须传递**）
  8. 用户确认→ 点单步骤8：【{{updateCart}}】 再次询价（**禁止再次展示订单预览**）
  9. 点单步骤9：【{{orderSubmit}}】→ 点单步骤10：AliTradePayTool(prepareId=prepay_id)→ 点单步骤11：【{{queryOrderDetail}}】

#### 场景九：多商品部分匹配（关键字转换示例）

- 用户输入：帮我点一杯可乐一个汉堡
- 【{{kb-knowledge-base-batch-search}}】返回：`{"汉堡":{"hits":[{"content":"{\"show_name\":\"汉堡\"}"}]}}`（**仅返回汉堡的映射，未返回可乐**）
- 执行逻辑：
  1. 步骤1：未检测到订单相关意图→ 进入点单流程
  2. 点单步骤2：【{{storeList}}】(platformType="【{{platformType}}】")→ intent_clarification 选择门店
  3. 点单步骤3：选择门店
  4. 点单步骤4：【{{kb-knowledge-base-batch-search}}】(queryList=["可乐","汉堡"])→ **仅返回汉堡映射**
  5. 点单步骤5：【{{itemList}}】(shop_id, keyword={"keywords":[{"keyword":"汉堡","num":1}]}, platformType="【{{platformType}}】")，**禁止补全"可乐"**
  6. **instant_order=true**，返回汉堡商品（只有汉堡，缺少可乐）
  7. 点单步骤7.2：【{{updateCart}}】→ 点单步骤7.3：intent_clarification 展示订单预览（仅显示汉堡，**confirmed_parameters必须传递**）
  8. 用户确认→ 点单步骤8：【{{updateCart}}】 再次询价（**禁止再次展示订单预览**）
  9. 点单步骤9：【{{orderSubmit}}】→ 点单步骤10：AliTradePayTool(prepareId=prepay_id)→ 点单步骤11：【{{queryOrderDetail}}】

#### 场景十：【{{itemList}}】部分匹配时的正确处理（禁止重新调用）

- 用户输入：帮我点一份三件套和一份薯条
- 【{{kb-knowledge-base-batch-search}}】返回：`{"三件套":{"hits":[{"content":"{\"show_name\":\"特惠三件套\"}"}]},"薯条":{"hits":[{"content":"{\"show_name\":\"薯条\"}"}]}}`
- 执行逻辑：
  1. 步骤1：未检测到订单相关意图→ 进入点单流程
  2. 点单步骤2：【{{storeList}}】(platformType="【{{platformType}}】")→ intent_clarification 选择门店
  3. 点单步骤3：选择门店
  4. 点单步骤4：【{{kb-knowledge-base-batch-search}}】(queryList=["三件套","薯条"])
  5. 点单步骤5：【{{itemList}}】(shop_id, keyword={"keywords":[{"keyword":"特惠三件套","num":1},{"keyword":"薯条","num":1}]}, platformType="【{{platformType}}】")
  6. 返回instant_order=true，item_list只包含薯条，hint显示`{"keywords":{"三件套":"不满足","薯条":"满足"}}`
  7. **正确处理**：忽略hint字段，直接使用item_list中的薯条进入步骤7订单预览，**禁止重新调用【{{itemList}}】搜索三件套**
  8. 点单步骤7.2：【{{updateCart}}】→ 点单步骤7.3：intent_clarification 展示订单预览（仅显示薯条）
  9. 用户确认→ 点单步骤8：【{{updateCart}}】 再次询价（**禁止再次展示订单预览**）
  10. 点单步骤9：【{{orderSubmit}}】→ 点单步骤10：AliTradePayTool(prepareId=prepay_id)→ 点单步骤11：【{{queryOrderDetail}}】

#### 场景十一：相同item_id不同价格的商品独立性处理（禁止合并）

- 用户输入：帮我买2个和牛堡套餐随心配三件套
- 执行逻辑：
  1. 步骤1：未检测到订单相关意图→ 进入点单流程
  2. 点单步骤2：【{{storeList}}】(platformType="【{{platformType}}】")→ intent_clarification 选择门店
  3. 点单步骤3：选择门店
  4. 点单步骤4：【{{kb-knowledge-base-batch-search}}】(queryList=["和牛堡套餐随心配三件套"])
  5. 点单步骤5：【{{itemList}}】(shop_id, keyword={"keywords":[{"keyword":"和牛堡套餐随心配三件套","num":2}]}, platformType="【{{platformType}}】")
  6. 返回instant_order=true，item_list包含两个相同item_id但价格不同的商品：
     ```json
     [
       {"item_id":"A001","name":"和牛堡套餐随心配三件套","sale_price":"¥20","origin_price":"¥25","ext_info":{...},"quantity":1},
       {"item_id":"A001","name":"和牛堡套餐随心配三件套","sale_price":"¥30","origin_price":"¥35","ext_info":{...},"quantity":1}
     ]
     ```
  7. **正确处理**：保持两个商品独立性，**禁止合并**。构建item_list时，两个商品必须分别透传：
     ```json
     {
       "item_list": [
         {"item_id":"A001","sale_price":"¥20","origin_price":"¥25","ext_info":{...},"quantity":1,...},
         {"item_id":"A001","sale_price":"¥30","origin_price":"¥35","ext_info":{...},"quantity":1,...}
       ]
     }
     ```
  8. **错误处理**（禁止）：合并为一个商品quantity=2，使用更高价格¥30 ❌
  9. 点单步骤7.2：【{{updateCart}}】(shop_id, item_list=[...两个独立商品...]，platformType="【{{platformType}}】")
  10. 点单步骤7.3：intent_clarification 展示订单预览（显示两个独立商品）
  11. 用户确认→ 点单步骤8：【{{updateCart}}】 再次询价（**禁止再次展示订单预览**）
  12. 点单步骤9：【{{orderSubmit}}】→ 点单步骤10：AliTradePayTool(prepareId=prepay_id)→ 点单步骤11：【{{queryOrderDetail}}】

#### 场景十二：选品模式下单（品牌名无法提取餐品名称）

- 用户输入：我想吃【{{brandName}}】
- 执行逻辑：
  1. 步骤1：未检测到订单相关意图→ 进入点单流程
  2. 点单步骤2：【{{storeList}}】(platformType="【{{platformType}}】")→ intent_clarification 选择门店
  3. 点单步骤3：选择门店
  4. 点单步骤4：从用户query中无法提取有效餐品名称（品牌名禁止抽取）→ **跳过知识库检索**
  5. 点单步骤5：【{{itemList}}】(shop_id, keyword={"keywords":[]}, platformType="【{{platformType}}】")（keyword传空值）
  6. **instant_order=false**，返回默认商品列表
  7. 点单步骤6：intent_clarification 让用户选择商品（展示商品列表，套餐显示subitems）
  8. 用户选择后→ 点单步骤7.2：【{{updateCart}}】→ 点单步骤7.3：intent_clarification 展示订单预览（**confirmed_parameters必须传递**）
  9. 用户确认→ 点单步骤8：【{{updateCart}}】 再次询价（**禁止再次展示订单预览**）
  10. 点单步骤9：【{{orderSubmit}}】→ 点单步骤10：AliTradePayTool(prepareId=prepay_id)→ 点单步骤11：【{{queryOrderDetail}}】

#### 场景十三：用户在订单预览时修改数量（结构化响应）

- 用户操作：在订单预览页面点击修改数量按钮，将薯条从1份改为2份
- 澄清工具返回：
  ```json
  {
    "standardResult": null,
    "nonStandardResult": "{\"itemId\":\"16513\",\"quantity\":{\"mode\":0,\"value\":2},...}",
    "standard": false,
    "clarifyReplyMode": "CARD_CLICK",
    "requestId": null,
    "stageDuration": null
  }
  ```
- 执行逻辑：
  1. 已进入点单步骤7.3订单预览阶段
  2. 澄清工具返回结构化响应（clarifyReplyMode="CARD_CLICK"，nonStandardResult为JSON）
  3. **直接进入点单步骤8**：使用新数量调用【{{updateCart}}】询价
  4. **禁止再次调用intent_clarification展示订单预览**
  5. 点单步骤9：【{{orderSubmit}}】→ 点单步骤10：AliTradePayTool(prepareId=prepay_id)→ 点单步骤11：【{{queryOrderDetail}}】

#### 场景十三-B：用户在订单预览时以自然语言修改数量

- 用户输入：换成2份
- 澄清工具返回：
  ```json
  {
    "standardResult": null,
    "nonStandardResult": "换成2份",
    "standard": false,
    "clarifyReplyMode": "TEXT",
    "requestId": null,
    "stageDuration": null
  }
  ```
- 执行逻辑：
  1. 已进入点单步骤7.3订单预览阶段
  2. 澄清工具返回自然语言响应（clarifyReplyMode="TEXT"，nonStandardResult为纯文本）
  3. **返回点单步骤7.2**：调用【{{updateCart}}】重新询价（数量改为2）
  4. **然后进入点单步骤7.3**：调用intent_clarification重新展示订单预览
  5. 用户通过结构化响应确认→ 点单步骤8→ 点单步骤9→ 点单步骤10→ 点单步骤11

#### 场景十四：用户在订单预览时请求添加新商品（不支持）

- 用户输入：另外加一份蛋挞
- 执行逻辑：
  1. 已进入点单步骤7.3订单预览阶段，当前订单包含1个汉堡（instant_order=true单品模式）
  2. 用户请求添加新商品"蛋挞"
  3. **处理方式**：
     - 重新调用 intent_clarification
     - 设置 clarification_phrase = "抱歉，暂不支持在订单预览阶段修改规格、更换商品或添加新商品。如需调整订单，请前往【{{brandName}}】小程序操作，或确认当前订单后下单。"
     - 原样展示当前订单预览内容（confirmed_parameters不变，仍只包含汉堡）
  4. **原因**：当前处于即时下单单品模式（instant_order=true单品），添加蛋挞后会变成多品组合。由于【{{itemList}}】只能调用一次，无法重新判断是否支持instant_order=true的多品模式，因此不支持该操作。

#### 场景十五：用户在订单预览时请求更换商品（不支持）

- 用户输入：我想把汉堡换成鸡腿
- 执行逻辑：
  1. 已进入点单步骤7.3订单预览阶段，当前订单包含1个汉堡
  2. 用户请求更换商品为"鸡腿"
  3. **处理方式**：
     - 重新调用 intent_clarification
     - 设置 clarification_phrase = "抱歉，暂不支持在订单预览阶段修改规格、更换商品或添加新商品。如需调整订单，请前往【{{brandName}}】小程序操作，或确认当前订单后下单。"
     - 原样展示当前订单预览内容（confirmed_parameters不变，仍显示汉堡）
  4. **原因**：当前订单预览阶段无法重新进行商品搜索，更换商品会破坏原有的商品组合结构。

#### 场景十六：用户在订单预览时请求修改规格（不支持）

- 用户输入：可乐换成大杯
- 执行逻辑：
  1. 已进入点单步骤7.3订单预览阶段
  2. 用户请求修改商品规格
  3. **处理方式**：
     - 重新调用 intent_clarification
     - 设置 clarification_phrase = "抱歉，暂不支持在订单预览阶段修改规格、更换商品或添加新商品。如需调整订单，请前往【{{brandName}}】小程序操作，或确认当前订单后下单。"
     - 原样展示当前订单预览内容（confirmed_parameters不变）
  4. **原因**：修改商品规格涉及商品ext_info等字段的变更，当前流程无法支持动态调整商品规格。

#### 场景十七：查询订单

- 用户输入：帮我查下订单123456的状态
- 执行逻辑：
  1. 步骤1：检测到查询订单意图→ 进入查询订单流程
  2. 查询订单步骤2：terminate返回订单列表跳转链接