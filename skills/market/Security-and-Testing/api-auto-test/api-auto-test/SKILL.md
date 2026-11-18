---
name: api-auto-test
description: 从语雀需求文档或Swagger/Knife4j页面自动解析接口定义和业务规则，生成技术+业务双维度测试用例，用Python requests执行接口测试并生成HTML可视化报告。当用户说"接口测试"、"API测试"、"自动化测试接口"、"测试这个接口"、提供语雀文档链接或Swagger页面链接要求测试时使用。
version: 1.9.0
---

# 接口自动化测试

从语雀需求文档或 Swagger/Knife4j 页面中提取接口定义和业务规则，自动生成技术+业务双维度测试用例，用 Python 执行并输出 HTML 报告。

**双维度测试**：
- **技术维度**（始终生成）：正常、空值、缺参、类型错、边界 — 基于接口参数定义自动生成
- **业务维度**（用户提供需求文档时生成）：枚举覆盖、范围边界、格式校验、字段依赖、数量限制、唯一性约束、外键校验 — 基于需求文档中的业务规则生成

## 前置依赖

本 skill 在执行 Swagger/Knife4j 页面解析时依赖以下 skill：

- **swagger-api-parser** — 用于从 Swagger/Knife4j 页面提取接口定义

**使用前请确保已安装**：如果尚未安装 `swagger-api-parser`，请先通过 QoderWork 技能市场搜索并安装（设置 → 技能 → 市场 → 搜索 "swagger-api-parser" → 点击 "+" 安装）。如未安装且用户提供 Swagger 链接，任务将中断。

## 工作流

### Step 1: 收集信息

向用户收集以下信息（用 AskUserQuestion 或从对话中提取）：

| 信息 | 必填 | 说明 |
|------|------|------|
| 文档来源 | 是 | 语雀文档链接 **或** Swagger/Knife4j 页面链接（含 `doc.html`） |
| 接口域名 (base_url) | 是 | 如 https://api.example.com |
| 认证 Token | 是 | Bearer Token 或其他 header 值 |
| Token 所在 Header 名 | 否 | 默认 `Authorization`，值格式 `Bearer {token}` |
| 特殊测试要求 | 否 | 如只测某几个接口、关注特定场景 |

**文档来源判断**：根据链接特征自动识别：
- URL 含 `yuque.com` → 走 **Step 2A（语雀文档）**
- URL 含 `doc.html` → 走 **Step 2B（Swagger/Knife4j 页面）**

### Step 2A: 解析语雀文档

通过浏览器 MCP 读取语雀页面内容：

1. 用 `mcp__builtin_browser__navigate` 打开语雀链接
2. 等待页面加载完成（3-5秒）
3. 用 `mcp__builtin_browser__read_page` 或 `mcp__builtin_browser__get_page_text` 提取文本
4. 如果文档较长，用 `mcp__builtin_browser__javascript_tool` 滚动页面触发懒加载：
   ```javascript
   (function(){ document.querySelectorAll('.ne-image-hide').forEach(function(el){ el.scrollIntoView(); }); return 'scrolled'; })()
   ```
5. 再次读取页面获取完整内容

**从文档中提取两类信息**：

> **⚠️ 范围限定（重要）**
> 业务规则提取必须**限定在被测接口对应的需求模块范围内**，不是把整篇需求文档的所有内容都拿来生成用例。
>
> **定位方法**：
> 1. 根据被测接口的 URL 路径、接口名称、功能说明，在需求文档中找到**对应的模块/章节**
> 2. 只提取该模块内的业务规则（如：接口是"ABM SKU 新增"，就只读需求文档中关于"ABM SKU 新增/管理"的段落）
> 3. 文档中其他不相关模块的业务规则**不提取、不生成用例**
>
> **示例**：需求文档包含"商品管理"、"订单管理"、"售后管理"三个模块，用户只要求测试"ABM SKU 新增/删除/列表"接口，则只从"商品管理"模块中提取业务规则，忽略订单和售后部分。

#### A. 接口定义（技术维度）
识别以下模式：
- 表格形式的参数列表（参数名、类型、是否必填、说明）
- URL 路径（含 `/api/`、`/v1/` 等特征）
- HTTP 方法关键词（GET/POST/PUT/DELETE）
- 请求/响应 JSON 示例
- 参数标记（* 或"必填"表示 required）

#### B. 业务规则（需求维度）— 重要
从需求文档中提取以下业务约束，用于生成业务场景测试用例：

1. **字段值约束**
   - 枚举值/状态值（如：status=0/1/2，type=1/2/3）
   - 取值范围（如：金额>0，数量1-999，长度不超过50）
   - 格式要求（如：手机号11位，邮箱格式，日期格式）
   - 特殊值规则（如：不能为0、不能为负数、必须为整数）

2. **业务逻辑规则**
   - 字段依赖关系（如：type=1时category必填，type=2时category可为空）
   - 状态流转规则（如：待审核→已审核→已完成，不能跳过状态）
   - 权限控制（如：只有创建人可删除，只有管理员可审批）
   - 数量限制（如：最多添加10个、每天最多5次）
   - 时间约束（如：结束时间必须晚于开始时间，不能早于今天）

3. **业务流程场景**
   - 完整业务流程（如：创建→提交→审批→完成）
   - 分支流程（如：审批通过→执行，审批拒绝→退回修改）
   - 异常流程（如：取消订单、退款、作废）
   - 关联操作（如：创建订单后自动扣减库存）

4. **数据关联规则**
   - 外键依赖（如：orderId必须存在，userId必须有效）
   - 唯一性约束（如：订单号不能重复，手机号不能重复注册）
   - 级联影响（如：删除用户时关联删除其订单）

**提取格式**：将业务规则整理为结构化对象，供 Step 4 生成业务场景用例时使用：

```json
{
  "field_constraints": [
    {"field": "status", "rule": "枚举值", "values": [0, 1, 2], "desc": "0-待审核 1-已审核 2-已完成"},
    {"field": "amount", "rule": "范围", "constraint": ">0", "desc": "金额必须大于0"},
    {"field": "phone", "rule": "格式", "pattern": "^1[3-9]\\d{9}$", "desc": "11位手机号"}
  ],
  "business_rules": [
    {"type": "dependency", "condition": "type==1", "action": "category必填", "desc": "类型为1时分类必填"},
    {"type": "state_flow", "from": "待审核", "to": "已审核", "desc": "待审核可流转到已审核"},
    {"type": "limit", "field": "items", "constraint": "最多10个", "desc": "单次最多添加10项"}
  ],
  "workflows": [
    {"name": "正常流程", "steps": ["创建", "提交", "审批", "完成"]},
    {"name": "拒绝流程", "steps": ["创建", "提交", "审批拒绝", "退回修改"]}
  ]
}
```

### Step 2B: 解析 Swagger/Knife4j 页面

当用户提供的是 Swagger/Knife4j 页面链接（URL 含 `doc.html`），**调用 `swagger-api-parser` skill** 完成接口定义提取。

**调用方式**：使用 `Skill` 工具，`skill` 参数为 `swagger-api-parser`，`args` 传入 Swagger 页面链接。

**调用后流程**：
1. swagger-api-parser skill 会完成：打开页面 → fetch Swagger JSON → 按 Controller 过滤全部接口 → 提取参数详情（含嵌套 $ref 递归展开） → 输出结构化 API 定义 JSON
2. 该 skill 会向用户确认接口清单 — 沿用其确认结果
3. 确认后，将 swagger-api-parser 输出的结构化 API 定义直接传入 **Step 3** 继续后续流程

> **注意**：如果用户同时提供了需求文档链接，在 swagger-api-parser 执行期间可并行读取需求文档（Step 2A），提取对应模块的业务规则。

<!-- Step 2B 原有的 Swagger 解析细节（URL 解析、fetch JSON、按 tags 过滤、参数展开等）已迁移至 swagger-api-parser skill，不再重复维护 -->
### Step 3: 构造 API 定义

将提取的内容结构化为 API 定义数组：

```json
[
  {
    "name": "接口名称",
    "method": "POST",
    "path": "/api/xxx/create",
    "headers": {"Content-Type": "application/json"},
    "params": [
      {"name": "field1", "type": "string", "required": true, "desc": "字段说明"},
      {"name": "field2", "type": "number", "required": false, "desc": "字段说明"}
    ],
    "body_example": {"field1": "test_value"},
    "expected_status": 200,
    "expected_fields": ["code", "data", "message"]
  }
]
```

**解析完成后向用户确认**：列出识别到的接口清单（名称+方法+路径），让用户确认是否完整正确，再继续生成用例。

**识别新增/删除接口配对（用于自动清理）**：

在接口清单确认后，分析哪些接口是"新增类"（会写入数据），并在同 Controller 下找到对应的"删除类"接口，建立配对关系。

识别规则：
- **新增类接口**：名称含 `add`、`create`、`insert`、`save`、`batchAdd`、`batchCreate`
- **删除类接口**：名称含 `delete`、`remove`、`batchDelete`、`batchRemove`
- **配对逻辑**：同一 Controller 下，新增接口与删除接口按名称相似度配对（如 `addSku` ↔ `deleteSku`，`batchAddSkuManage` ↔ `deleteAbmSkuManage`）

配对完成后向用户确认：列出配对清单（新增接口 → 删除接口），用户可补充或跳过。若某个新增接口无对应删除接口，标记为"无法自动清理"，提醒用户手动处理。

### Step 4: 生成测试用例

为每个接口自动生成以下类型用例：

| 类型 | 策略 | 预期 |
|------|------|------|
| 正常 | 必填参数完整，类型正确 | HTTP 200 + errCode==0 && success==true（业务成功） |
| 空值 | 必填参数传空字符串/null | HTTP 200 + errCode!=0 && success!=true（业务拒绝） |
| 缺参 | 去掉一个必填参数 | HTTP 200 + errCode!=0 && success!=true（业务拒绝） |
| 类型错 | string 传 number，反之亦然 | HTTP 200 + errCode!=0 && success!=true（业务拒绝） |
| 边界 | 字符串255字符、数值0/-1/极大值 | HTTP 200 + 不能 HTTP 500，errCode/success 不做强制要求 |

**需求驱动的业务场景用例（当 Step 2A 提取到业务规则时生成）：**

如果 Step 2A 从需求文档中提取到了业务规则（`field_constraints` / `business_rules` / `workflows`），必须额外生成以下业务场景用例。

> **范围限定**：只使用与**当前被测接口直接相关**的业务规则生成用例。判断标准：业务规则中提到的字段、状态、流程是否出现在被测接口的参数或功能描述中。不相关的规则直接忽略。

| 类型 | 策略 | 预期 | 来源 |
|------|------|------|------|
| 枚举值覆盖 | 对 status/type 等枚举字段，每个枚举值生成一条正向用例 | errCode==0 && success==true | `field_constraints` 中 rule="枚举值" |
| 枚举非法值 | 传不在枚举范围内的值（如 status=99） | errCode!=0 && success!=true | `field_constraints` 中 rule="枚举值" |
| 范围边界 | 对数值范围字段，测试边界值（如 amount=0.01, amount=0, amount=999, amount=1000） | 边界内通过，边界外拒绝 | `field_constraints` 中 rule="范围" |
| 格式校验 | 对格式约束字段，传正确格式和错误格式（如 phone="abc", phone="123"） | 正确格式通过，错误格式拒绝 | `field_constraints` 中 rule="格式" |
| 字段依赖 | 按依赖规则构造数据（如 type=1 且 category 为空 → 拒绝；type=1 且 category 有值 → 通过） | 满足依赖通过，违反依赖拒绝 | `business_rules` 中 type="dependency" |
| 数量限制 | 测试上限值、上限+1、空数组 | 上限内通过，超限拒绝 | `business_rules` 中 type="limit" |
| 时间约束 | 按时间规则构造（如 endTime < startTime → 拒绝） | 合法时间通过，非法拒绝 | `business_rules` 中 type="time" |
| 唯一性 | 用已存在的唯一值再次提交（如重复的订单号） | errCode!=0 && success!=true | `business_rules` 中 type="unique" |
| 外键存在性 | 用不存在的关联ID提交（如 orderId=999999） | errCode!=0 && success!=true | `business_rules` 中 type="foreign_key" |

**业务场景用例 ID 命名规则**：在技术用例 ID 后追加业务用例，ID 格式为 `BIZ-{序号}`，如 `BIZ-001`、`BIZ-002`。

**业务场景用例的 name 命名规则**：`{业务规则描述}-{具体场景}`，如：
- `状态枚举-传合法值status=0`
- `状态枚举-传非法值status=99`
- `金额范围-边界值amount=0.01`
- `手机号格式-传非法格式abc`
- `类型依赖-type=1时category为空`
- `数量限制-超过上限11个`
- `唯一性约束-重复订单号`

**向用户确认业务用例**：生成业务场景用例后，向用户展示完整用例清单（技术用例 + 业务用例），标注哪些来自需求文档，让用户确认后再执行。

**IMPORTANT: 测试通过标准（必须同时满足两个条件）**
- `errCode == 0` **且** `success == true` → 判定为通过
- 否则（errCode != 0 或 success != true）→ 判定为失败

**断言规则**
- 每条用例必须通过 `expect_errCode` 字段声明预期的业务码：
  - 正向用例（正常、含有效数据的边界）：`"expect_errCode": 0`，同时要求 `success == true`
  - 反向用例（空值、缺参、类型错、不存在的资源、非法值）：`"expect_errCode": "non_zero"`，同时要求 `success != true`
  - 宽松边界用例（超大分页、极端数值等，服务端可能兼容也可能拒绝）：`"expect_errCode": "any"`，表示只要不 HTTP 500 即可，不校验 errCode 和 success
- 断言检查顺序：HTTP 状态码 → errCode + success 联合校验 → 响应字段存在性

**测试数据生成规则：**
- string → `"test_{paramName}"`，边界用 `"x" * 255`
- string(date-time) → **毫秒时间戳**（如 `1753776000000`），优先使用当前时间戳 `int(time.time() * 1000)`，边界用 `0`、`-1`、`9999999999999`
- number → `1`，边界用 `0`, `-1`, `99999999`
- boolean → `true`
- array → `[1]`
- object → `{}`
- 手机号 → `"13800138000"`
- 日期（非 date-time 格式的普通 date） → `"2026-01-01"`
- email → `"test@test.com"`

**动态数据提取（goodsCode / productNo 等关联字段）：**

当接口入参包含 `goodsCode`、`productNo` 等字样时，**优先从同组 `/page` 接口的响应中动态获取真实值**，而非硬编码。流程：

1. 在脚本开头先调用同组的 `/page` 接口（如 `configStartRentDay/page`、`configStartRentDayFp/page`），从 `data.records` 中提取第一条记录的 `goodsCode` 或 `productNo`
2. 将提取到的值作为后续用例的测试数据
3. 若 `/page` 接口无数据或调用失败，则使用硬编码兜底值：
   - `goodsCode` 兜底: `"CP8888012026032603"`
   - `productNo` 兜底: `"FP2026041700031"`

示例代码模式：
```python
# 动态获取真实 goodsCode / productNo
SAMPLE_GOODS_CODE = "CP8888012026032603"  # 兜底值
SAMPLE_PRODUCT_NO = "FP2026041700031"     # 兜底值

def fetch_sample_data():
    """从 /page 接口获取真实业务数据"""
    global SAMPLE_GOODS_CODE, SAMPLE_PRODUCT_NO
    ts = int(time.time() * 1000)
    # 尝试渠道商品编码维度
    try:
        resp = requests.post(
            f"{BASE_URL}{PREFIX}/configStartRentDay/page",
            headers=HEADERS,
            json={"pageNo": 1, "pageSize": 1},
            params={"permitUserId": 685, "permitUserName": "xuyuefeng", "t": ts},
            timeout=30
        )
        records = resp.json().get("data", {}).get("records", [])
        if records:
            SAMPLE_GOODS_CODE = records[0].get("goodsCode", SAMPLE_GOODS_CODE)
    except Exception:
        pass
    # 尝试 FP 编码维度
    try:
        resp = requests.post(
            f"{BASE_URL}{PREFIX}/configStartRentDayFp/page",
            headers=HEADERS,
            json={"pageNo": 1, "pageSize": 1},
            params={"permitUserId": 685, "permitUserName": "xuyuefeng", "t": ts},
            timeout=30
        )
        records = resp.json().get("data", {}).get("records", [])
        if records:
            SAMPLE_PRODUCT_NO = records[0].get("productNo", SAMPLE_PRODUCT_NO)
    except Exception:
        pass

fetch_sample_data()
print(f"动态数据: goodsCode={SAMPLE_GOODS_CODE}, productNo={SAMPLE_PRODUCT_NO}")
```

**动态获取真实订单号（rentRecordNo / orderSN / orderNo）：**

当接口入参包含 `rentRecordNo`、`orderSN`、`orderNo` 等订单号字段时，**禁止使用 "TEST_RECORD_NO" 等硬编码假值**，必须根据被测接口所属网关，调用对应的订单列表接口获取真实订单号。

**网关提取规则**：API 路径的第一段即为网关标识。
- `/salesBusinessBackend/inside_sales_business/api/aliOrder/xxx` → 网关 = `salesBusinessBackend`
- `/api/user/idCard/getNeedIdCard` → 网关 = `api`
- `/merchantTeamwork/inside_route_page/merchantOrder/orderList` → 网关 = `merchantTeamwork`

**网关 → 订单列表接口映射表**：

| 网关 | 订单列表接口 URL | 请求体 | 订单号字段路径 |
|------|-----------------|--------|---------------|
| `salesBusinessBackend` | `{BASE_URL}/salesBusinessBackend/inside_sales_business/api/aliOrder/queryClientOrderList` | `{"queryType":"0","spuUseType":1,"currPage":1,"pageSize":10}` | `data.records[0].rentRecordNo` |
| `merchantTeamwork` | `{BASE_URL}/merchantTeamwork/inside_route_page/merchantOrder/orderList` | `{"currPage":1,"pageSize":20}` | `data.records[0].rentRecordNo` |
| `order-backend` | `{BASE_URL}/order-backend/applet/queryRentRecordList` | `{"currPage":1,"pageSize":20}` | `data.records[0].rentRecordNo` |
| `teleApplication` | `{BASE_URL}/teleApplication/applet/queryRentRecordList` | `{"currPage":1,"pageSize":20}` | `data.records[0].rentRecordNo` |
| `api`（C端） | `https://api.woaizuji.com/api/xcxOrder/V2/pageQueryOrderStateList` | `{"queryType":"0","spuUseType":"1","currPage":1,"pageSize":10}` | `data.records[0].rentRecordNo` |

> **注意**：不同网关的 BASE_URL 和 Token 可能不同，需使用与被测接口相同的网关地址和认证信息。若映射表中无对应网关，可在 Swagger 中搜索 `queryRentRecordList` 或 `orderList` 等关键词定位订单列表接口。

**代码模板**：
```python
# 网关 → 订单列表接口映射
GATEWAY_ORDER_API = {
    "salesBusinessBackend": {
        "url": f"{BASE_URL}/salesBusinessBackend/inside_sales_business/api/aliOrder/queryClientOrderList",
        "body": {"queryType": "0", "spuUseType": 1, "currPage": 1, "pageSize": 10},
    },
    "merchantTeamwork": {
        "url": f"{BASE_URL}/merchantTeamwork/inside_route_page/merchantOrder/orderList",
        "body": {"currPage": 1, "pageSize": 20},
    },
    "order-backend": {
        "url": f"{BASE_URL}/order-backend/applet/queryRentRecordList",
        "body": {"currPage": 1, "pageSize": 20},
    },
    "teleApplication": {
        "url": f"{BASE_URL}/teleApplication/applet/queryRentRecordList",
        "body": {"currPage": 1, "pageSize": 20},
    },
}

SAMPLE_ORDER_NO = None  # 动态获取，不设硬编码兜底

def extract_gateway(api_path):
    """从 API 路径提取网关标识（第一段）"""
    parts = api_path.strip("/").split("/")
    return parts[0] if parts else ""

def fetch_real_order_no(gateway):
    """根据网关调用对应订单列表接口，获取真实订单号"""
    global SAMPLE_ORDER_NO
    config = GATEWAY_ORDER_API.get(gateway)
    if not config:
        print(f"[WARN] 网关 {gateway} 无对应订单列表接口配置")
        return
    try:
        resp = requests.post(config["url"], headers=HEADERS, json=config["body"], timeout=30)
        data = resp.json()
        records = data.get("data", {}).get("records", [])
        if records:
            SAMPLE_ORDER_NO = records[0].get("rentRecordNo") or records[0].get("orderSN") or records[0].get("orderNo")
            print(f"[OK] 从 {gateway} 获取到真实订单号: {SAMPLE_ORDER_NO}")
        else:
            print(f"[WARN] {gateway} 订单列表为空")
    except Exception as e:
        print(f"[ERROR] 获取订单号失败: {e}")

# 在生成用例前，根据被测接口的网关提取订单号
gateway = extract_gateway(test_api_path)  # 如 "/salesBusinessBackend/..." → "salesBusinessBackend"
fetch_real_order_no(gateway)
```

**优先级**：动态获取 > 用户指定 > 报错提示用户提供。绝不用 "TEST_RECORD_NO" 等假值填充订单号字段。

每条用例结构：

```json
{
  "id": "TC001",
  "api": "接口名称",
  "name": "正常创建-必填参数完整",
  "method": "POST",
  "url": "{base_url}/api/xxx/create",
  "headers": {"Content-Type": "application/json", "Authorization": "Bearer {token}"},
  "body": {"field1": "test_value"},
  "expect_errCode": 0,
  "assert": {"status": 200, "contains": ["errCode", "errMsg", "success"]}
}
```

**expect_errCode 取值说明：**
- `0` — 期望业务成功（正向用例）
- `"non_zero"` — 期望业务拒绝，errCode != 0（反向用例）
- `"any"` — 不校验 errCode，只要不 500 即可（宽松边界用例）

### Step 5: 编写并执行 Python 脚本

生成 Python 测试脚本，要求：

```python
# -*- coding: utf-8 -*-
import requests, json, time, sys
from datetime import datetime

BASE_URL = "用户指定的域名"
TOKEN = "用户提供的token"
HEADERS = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {TOKEN}"
}

# 测试用例列表
test_cases = [...]  # 从 Step 4 生成

def check_response(body, expect):
    """
    校验业务响应：errCode + success 联合断言。
    通过标准：errCode == 0 且 success == true
    expect 取值：
      0          — 正向用例，期望 errCode==0 且 success==true
      "non_zero" — 反向用例，期望 errCode!=0 且 success!=true
      "any"      — 不校验 errCode/success，直接通过
    返回 (passed: bool, detail: str)
    """
    if expect == "any":
        actual_err = body.get("errCode") if isinstance(body, dict) else None
        actual_ok = body.get("success") if isinstance(body, dict) else None
        return True, f"errCode={actual_err}, success={actual_ok}（未校验）"

    actual_err = body.get("errCode") if isinstance(body, dict) else None
    actual_ok = body.get("success") if isinstance(body, dict) else None

    if expect == "non_zero":
        # 反向用例：errCode 必须不为 0，success 必须不为 true
        err_ok = actual_err is not None and actual_err != 0
        suc_ok = actual_ok is not None and actual_ok is not True
        passed = err_ok and suc_ok
        detail = f"errCode={actual_err}({'!=0' if err_ok else '==0'}), success={actual_ok}({'!=true' if suc_ok else '==true'})"
        return passed, detail

    # 正向用例 (expect == 0)：errCode 必须为 0，success 必须为 true
    err_ok = actual_err == 0
    suc_ok = actual_ok is True
    passed = err_ok and suc_ok
    detail = f"errCode={actual_err}({'==0' if err_ok else '!=0'}), success={actual_ok}({'==true' if suc_ok else '!=true'})"
    return passed, detail

def run_test(case):
    """执行单条测试用例，返回结果字典"""
    result = {
        "id": case["id"],
        "api": case["api"],
        "name": case["name"],
        "method": case["method"],
        "url": case["url"],
        "request_body": case.get("body"),
        "status": None,
        "response": None,
        "duration_ms": 0,
        "passed": False,
        "error": None,
        "assert_detail": ""
    }
    try:
        start = time.time()
        resp = requests.request(
            case["method"],
            case["url"],
            headers=case.get("headers", HEADERS),
            json=case.get("body"),
            timeout=30
        )
        result["duration_ms"] = round((time.time() - start) * 1000, 2)
        result["status"] = resp.status_code
        try:
            result["response"] = resp.json()
        except Exception:
            result["response"] = resp.text[:2000]

        # ---- 断言检查（三层） ----
        asserts = case.get("assert", {})
        expect_err = case.get("expect_errCode", 0)  # 默认期望业务成功
        passed = True
        details = []

        # 第1层：HTTP 状态码
        if "status" in asserts:
            ok = resp.status_code == asserts["status"]
            passed = passed and ok
            details.append(f"HTTP状态码 {'==' if ok else '!='} 期望{asserts['status']} 实际{resp.status_code}")

        # 第2层：errCode + success 联合校验（核心断言）
        err_ok, err_detail = check_response(result["response"], expect_err)
        passed = passed and err_ok
        details.append(err_detail)

        # 第3层：响应字段存在性
        if "contains" in asserts:
            body = result["response"] if isinstance(result["response"], dict) else {}
            for field in asserts["contains"]:
                ok = field in body
                passed = passed and ok
                details.append(f"字段'{field}' {'存在' if ok else '不存在'}")

        result["passed"] = passed
        result["assert_detail"] = "; ".join(details)
    except Exception as e:
        result["error"] = str(e)
        result["passed"] = False
    return result

# 执行全部用例
results = []
for case in test_cases:
    r = run_test(case)
    results.append(r)
    icon = "PASS" if r["passed"] else "FAIL"
    print(f"[{icon}] {r['id']} {r['name']} ({r['duration_ms']}ms)")

# 输出 JSON 结果供报告使用
with open("test_results.json", "w", encoding="utf-8") as f:
    json.dump(results, f, ensure_ascii=False, indent=2)

total = len(results)
passed = sum(1 for r in results if r["passed"])
failed = total - passed
print(f"\n总计: {total} | 通过: {passed} | 失败: {failed} | 通过率: {passed/total*100:.1f}%")
```

**执行方式**：
- Windows 路径: `C:\Users\Administrator\.qoderworkcn\workspace\{workspace_id}\`
- 脚本保存到工作目录，用 `python` 命令执行
- 超时设置 30 秒/请求

### Step 5B: 自动清理测试数据

测试执行完成后，自动清理新增接口产生的测试数据。清理逻辑嵌入同一个 Python 脚本，在输出 `test_results.json` 之后、生成报告之前执行。

**清理流程**：

1. **识别需清理的用例**：遍历 `results`，筛选满足以下条件的用例：
   - 属于新增类接口的正向用例（`expect_errCode == 0`）
   - 实际执行成功（`passed == True`，即 `errCode==0 && success==true`）
   - 该用例的 API 在 Step 3 的配对清单中有对应删除接口

2. **提取被创建的数据 ID**：从成功用例的 `response` 中提取 ID，提取策略按优先级：
   - `response.data` 为数字/字符串 → 直接作为 ID
   - `response.data.id` → 取该值
   - `response.data` 为数组 → 提取每条记录的 `id` 字段
   - `response.data.list` / `response.data.records` 为数组 → 提取每条记录的 `id`
   - 以上均无 → 从请求体中提取关键标识字段（如 `skuCode`、`goodsCode`）

3. **调用删除接口**：根据配对关系，构造删除请求：
   - 单个 ID → `{"id": extracted_id}`
   - 多个 ID → `{"ids": [id1, id2, ...]}` 或按删除接口参数定义构造
   - 删除接口的 URL、headers、认证方式与被测接口相同

4. **记录清理结果**：每条清理操作记录到 `cleanup_results` 列表：

```python
cleanup_results = []  # 清理结果列表

# cleanup_results 元素结构：
{
    "test_id": "TC001",          # 来源用例 ID
    "api": "batchAddAbmSkuManage",  # 新增接口名
    "delete_api": "deleteAbmSkuManage",  # 删除接口名
    "extracted_ids": [1, 2, 3],  # 提取到的 ID
    "delete_status": 200,        # HTTP 状态码
    "delete_response": {...},    # 删除接口响应
    "cleanup_passed": True       # 清理是否成功
}
```

**清理代码模板**（追加在 `test_results.json` 输出之后）：

```python
# ============ 自动清理测试数据 ============

# 清理配对配置（Step 3 确定，动态生成）
CLEANUP_PAIRS = [
    {
        "create_api": "batchAddAbmSkuManage",
        "delete_api_name": "deleteAbmSkuManage",
        "delete_url": f"{BASE_URL}{PREFIX}/abm/skuManage/deleteAbmSkuManage",
        "delete_method": "POST",
        "id_extract_path": "data",  # 响应中 ID 的路径
        "delete_param": "ids",      # 删除接口的 ID 参数名
    },
    # ... 更多配对
]

def extract_ids_from_response(response, path):
    """从响应中提取被创建的 ID 列表"""
    if not isinstance(response, dict):
        return []
    data = response
    for key in path.split("."):
        if isinstance(data, dict):
            data = data.get(key)
        else:
            return []
    if data is None:
        return []
    if isinstance(data, (int, str)):
        return [data]
    if isinstance(data, list):
        ids = []
        for item in data:
            if isinstance(item, dict):
                ids.append(item.get("id") or item.get("skuId") or item.get("code"))
            else:
                ids.append(item)
        return [i for i in ids if i is not None]
    if isinstance(data, dict):
        return [data.get("id")] if data.get("id") else []
    return []

def run_cleanup(results, cleanup_pairs):
    """执行测试数据清理"""
    cleanup_results = []
    for pair in cleanup_pairs:
        create_api = pair["create_api"]
        # 找到该新增接口的所有成功正向用例
        success_cases = [
            r for r in results
            if r["api"] == create_api
            and r["passed"]
            and r.get("type") == "正向"
        ]
        if not success_cases:
            continue

        # 收集所有提取到的 ID
        all_ids = []
        for case_result in success_cases:
            ids = extract_ids_from_response(case_result["response"], pair.get("id_extract_path", "data"))
            all_ids.extend(ids)

        if not all_ids:
            print(f"[CLEANUP] {create_api}: 未提取到可清理的 ID，跳过")
            cleanup_results.append({
                "test_id": ", ".join(r["id"] for r in success_cases),
                "api": create_api,
                "delete_api": pair["delete_api_name"],
                "extracted_ids": [],
                "delete_status": None,
                "delete_response": None,
                "cleanup_passed": False,
                "reason": "未提取到 ID"
            })
            continue

        # 调用删除接口
        delete_body = {pair.get("delete_param", "ids"): all_ids}
        try:
            resp = requests.request(
                pair.get("delete_method", "POST"),
                pair["delete_url"],
                headers=HEADERS,
                json=delete_body,
                timeout=30
            )
            resp_body = resp.json()
            err_code = resp_body.get("errCode")
            success = resp_body.get("success")
            cleanup_ok = (err_code == 0 and success is True)
            print(f"[CLEANUP] {create_api} → {pair['delete_api_name']}: ids={all_ids}, {'OK' if cleanup_ok else 'FAIL'} (errCode={err_code})")
            cleanup_results.append({
                "test_id": ", ".join(r["id"] for r in success_cases),
                "api": create_api,
                "delete_api": pair["delete_api_name"],
                "extracted_ids": all_ids,
                "delete_status": resp.status_code,
                "delete_response": resp_body,
                "cleanup_passed": cleanup_ok
            })
        except Exception as e:
            print(f"[CLEANUP] {create_api} → {pair['delete_api_name']}: ERROR {e}")
            cleanup_results.append({
                "test_id": ", ".join(r["id"] for r in success_cases),
                "api": create_api,
                "delete_api": pair["delete_api_name"],
                "extracted_ids": all_ids,
                "delete_status": None,
                "delete_response": str(e),
                "cleanup_passed": False,
                "reason": str(e)
            })
    return cleanup_results

cleanup_results = run_cleanup(results, CLEANUP_PAIRS)

# 将清理结果追加到 test_results.json
with open("test_results.json", "w", encoding="utf-8") as f:
    json.dump({"results": results, "cleanup": cleanup_results}, f, ensure_ascii=False, indent=2)

cleanup_total = len(cleanup_results)
cleanup_ok = sum(1 for c in cleanup_results if c["cleanup_passed"])
if cleanup_total:
    print(f"\n清理: {cleanup_total} 项 | 成功: {cleanup_ok} | 失败: {cleanup_total - cleanup_ok}")
```

**注意事项**：
- 清理失败不阻塞报告生成，仅在报告中标注
- 若新增接口无对应删除接口（Step 3 标记为"无法自动清理"），在报告中提醒用户手动清理
- 删除接口可能也在使用范围内被测试，此时删除接口本身的测试数据也会被清理
- 清理请求使用与测试相同的认证信息和网关地址

### Step 6: 生成 HTML 报告

根据执行结果生成 HTML 报告，要求：

- **总览区**: 总数、通过、失败、错误数、总耗时、通过率（百分比+进度条）
- **Tab 分页**: 将用例分为三个 Tab 展示：
  - **全部用例**: 所有用例汇总 + 完整表格
  - **正向用例** (`expect_errCode==0`): 独立统计通过率 + 表格，每行标注"正向"标签
  - **反向用例** (`expect_errCode=="non_zero"` 或 `"any"`): 独立统计通过率 + 表格，每行标注"反向"标签
- **明细表格**: 每条用例的 ID、接口名、用例名、类型（正向/反向）、方法、状态码、耗时、结果、详情（可折叠请求/响应 JSON）
- **失败高亮**: 失败行红色背景，成功行绿色背景
- **数据清理结果**（当 Step 5B 有清理操作时展示）:
  - 在 Tab 分页下方、页脚上方插入"数据清理结果"区块
  - 展示清理总览：清理项数、成功数、失败数
  - 明细表格：来源用例 ID、新增接口、删除接口、提取的 ID 列表、删除状态码、清理结果（成功绿/失败红）
  - 若清理失败，展开显示删除接口的响应内容，方便排查
  - 若无清理操作（被测接口无新增类接口），不显示此区块
- **页脚**: 测试时间、环境域名、Token 前8位（脱敏）

报告保存为 `api_test_report_{YYYYMMDD_HHmmss}.html` 到输出目录。

**报告模板参考**：

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<title>接口测试报告 - {date}</title>
<style>
  body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; margin: 20px; background: #f5f5f5; color: #333; }
  h1 { margin-bottom: 4px; }
  .meta { color: #888; font-size: 13px; margin-bottom: 20px; }
  .summary { display: flex; gap: 16px; margin-bottom: 24px; flex-wrap: wrap; }
  .card { background: white; padding: 16px 24px; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,.1); min-width: 120px; }
  .card h3 { margin: 0; font-size: 13px; color: #888; font-weight: 500; }
  .card .value { font-size: 28px; font-weight: bold; margin-top: 4px; }
  .pass { color: #52c41a; } .fail { color: #ff4d4f; }
  table { width: 100%; border-collapse: collapse; background: white; border-radius: 8px; overflow: hidden; margin-bottom: 16px; }
  th { background: #fafafa; padding: 10px 12px; text-align: left; font-weight: 600; font-size: 13px; border-bottom: 2px solid #f0f0f0; }
  td { padding: 8px 12px; border-top: 1px solid #f0f0f0; font-size: 13px; vertical-align: top; }
  tr.row-pass { background: #f6ffed; } tr.row-fail { background: #fff2f0; }
  .badge { padding: 2px 8px; border-radius: 4px; font-size: 11px; font-weight: 500; }
  .badge-positive { background: #f6ffed; color: #52c41a; }
  .badge-negative { background: #fff7e6; color: #fa8c16; }
  .badge-boundary { background: #e6f7ff; color: #1890ff; }
  pre { background: #f5f5f5; padding: 8px; border-radius: 4px; overflow-x: auto; font-size: 11px; margin: 4px 0; white-space: pre-wrap; word-break: break-all; }
  .progress-bar { height: 8px; background: #f0f0f0; border-radius: 4px; overflow: hidden; margin-top: 6px; }
  .progress-fill { height: 100%; background: #52c41a; border-radius: 4px; transition: width .3s; }
  /* Tab — 禁止 inline onclick，用 data-tab + addEventListener */
  .tabs { display: flex; gap: 0; margin-bottom: 0; }
  .tab-btn { padding: 10px 24px; cursor: pointer; background: #e8e8e8; border: none;
    font-size: 14px; font-weight: 500; color: #666; border-radius: 8px 8px 0 0; outline: none; }
  .tab-btn.active { background: white; color: #1890ff; border-bottom: 2px solid white; margin-bottom: -1px; z-index: 1; position: relative; }
  .tab-btn .count { font-size: 11px; background: #f0f0f0; padding: 1px 6px; border-radius: 10px; margin-left: 6px; }
  .tab-btn.active .count { background: #e6f7ff; }
  .tab-panel { display: none; background: white; border-radius: 0 8px 8px 8px; padding: 20px; box-shadow: 0 1px 3px rgba(0,0,0,.1); }
  .tab-panel.active { display: block; }
  footer { margin-top: 24px; padding: 16px; color: #888; font-size: 12px; text-align: center; }
  /* 详情展开 — 原生 <details>，默认收起，行内流式布局，禁止 position:absolute */
  .detail-dropdown summary { cursor: pointer; color: #1890ff; font-size: 12px; list-style: none; user-select: none; }
  .detail-dropdown summary::-webkit-details-marker { display: none; }
  .detail-dropdown summary::before { content: '\25b6'; display: inline-block; margin-right: 4px; font-size: 10px; transition: transform .2s; }
  .detail-dropdown[open] summary::before { transform: rotate(90deg); }
  .detail-body { display: block; margin: 8px 0 4px 0; padding: 10px 12px; background: #fafafa; border-radius: 4px; border-left: 3px solid #1890ff; }
  .detail-body b { display: block; margin-bottom: 4px; color: #333; font-size: 12px; }
  .detail-body pre { margin: 0 0 10px 0; padding: 8px 12px; background: #f0f0f0; border-radius: 4px; font-size: 11px; white-space: pre-wrap; word-break: break-all; }
  .detail-body > div:last-child pre { margin-bottom: 0; }
  /* 全局展开/收起按钮 */
  .toggle-all-btn { display: inline-block; padding: 5px 14px; font-size: 12px; color: #1890ff; background: #e6f7ff; border: 1px solid #91d5ff; border-radius: 4px; cursor: pointer; margin-bottom: 12px; user-select: none; }
  .toggle-all-btn:hover { background: #bae7ff; }
</style>
</head>
<body>
<h1>接口测试报告</h1>
<p class="meta">测试时间: {datetime} | 环境: {base_url} | Token: {token_prefix}***</p>
<!-- 总览卡片 -->
<div class="summary">
  <div class="card"><h3>总计</h3><div class="value">{total}</div></div>
  <div class="card"><h3>通过</h3><div class="value pass">{passed}</div></div>
  <div class="card"><h3>失败</h3><div class="value fail">{failed}</div></div>
  <div class="card"><h3>通过率</h3><div class="value">{rate}%</div>
    <div class="progress-bar"><div class="progress-fill" style="width:{rate}%"></div></div>
  </div>
</div>
<!-- 全局展开/收起按钮 — addEventListener 绑定，禁止 inline onclick -->
<button class="toggle-all-btn" id="toggleAllBtn">全部展开</button>
<!-- Tab 导航 — 用 data-tab 属性，禁止 inline onclick -->
<div class="tabs">
  <button class="tab-btn active" data-tab="all">全部用例 <span class="count">{total}</span></button>
  <button class="tab-btn" data-tab="positive">正向用例 <span class="count">{pos_total}</span></button>
  <button class="tab-btn" data-tab="negative">反向用例 <span class="count">{neg_total}</span></button>
</div>
<!-- 每个 Tab 面板含独立统计 + 表格 -->
<div id="tab-all" class="tab-panel active">
  <!-- 独立统计卡片 + 全部用例行表格 -->
</div>
<div id="tab-positive" class="tab-panel">
  <!-- 独立统计卡片 + 正向用例行表格 -->
</div>
<div id="tab-negative" class="tab-panel">
  <!-- 独立统计卡片 + 反向用例行表格 -->
</div>
<footer>
  接口自动化测试 | 生成时间: {datetime}
</footer>
<script>
// Tab 切换 — addEventListener 绑定，禁止 inline onclick
function switchTab(name, btn) {
  document.querySelectorAll('.tab-panel').forEach(function(p) { p.classList.remove('active'); });
  document.querySelectorAll('.tab-btn').forEach(function(b) { b.classList.remove('active'); });
  document.getElementById('tab-' + name).classList.add('active');
  btn.classList.add('active');
}
document.querySelectorAll('.tab-btn').forEach(function(btn) {
  btn.addEventListener('click', function() { switchTab(this.getAttribute('data-tab'), this); });
});
// 全局展开/收起
(function() {
  var btn = document.getElementById('toggleAllBtn');
  var expanded = false;
  btn.addEventListener('click', function() {
    expanded = !expanded;
    document.querySelectorAll('.detail-dropdown').forEach(function(d) {
      d.open = expanded;
    });
    btn.textContent = expanded ? '全部收起' : '全部展开';
  });
})();
</script>
</body>
</html>
```

**详情列渲染模板**（每行用原生 `<details>`，默认收起，点击"全部展开"按钮可一键展开）：

```html
<td><details class="detail-dropdown"><summary>查看详情</summary><div class="detail-body"><b>请求URL:</b><pre>{method} {url}</pre><b>请求体:</b><pre>{请求JSON}</pre><b>响应体:</b><pre>{响应JSON}</pre></div></details></td>
```

## 注意事项

1. **语雀懒加载**: 图片/内容可能需要滚动才加载，先 scrollIntoView 再读取
2. **禅道文档**: 内容在 iframe 内，需通过 `javascript_tool` 访问 `iframe.contentDocument.body`
3. **编码**: Windows 下 Python 脚本必须声明 `# -*- coding: utf-8 -*-`
4. **大响应**: 响应体超过 2KB 时截断，报告中显示前 2KB + "...(truncated)"
5. **网络异常**: 捕获 timeout/connection 异常，记录到 error 字段，不中断后续用例
6. **敏感信息**: 报告中 Token 只显示前8位
7. **接口确认（重要）**: 解析完文档后**必须**向用户展示完整接口清单（含总数），让用户确认后再继续。绝不能只测试 URL 中提到的单个接口而忽略同 Controller 下的其他接口
8. **结果文件**: 最终报告通过 `present_files` 工具展示给用户
9. **HTML 预览沙箱兼容**: QoderWork HTML 预览会剥离 inline onclick/onchange 等内联事件处理器。必须遵守：(1) 详情展开用原生 `<details><summary>` 元素（默认收起），禁止 JS toggle；(2) 全局展开/收起按钮用 `addEventListener` 绑定，禁止 inline onclick；(3) Tab 切换等交互用 `addEventListener` 绑定，禁止 inline onclick；(4) 同一用例在多 Tab 重复渲染时禁止用 `getElementById`（ID 重复），用 DOM 相对定位或加 Tab 前缀
10. **Swagger/Knife4j 抓取要点**:
    - 直接 fetch `/{group}/v2/api-docs` 获取完整 Swagger JSON，**不要**逐一点击侧边栏
    - `javascript_tool` 返回 undefined 问题：必须用单行 IIFE + `window.__swaggerJSON` 暂存大数据，再分步提取
    - 只取当前展开 Controller 下的接口（按 `tags` 字段匹配 `controllerName`），不是全部接口
    - `definitions` 中的 model 可能互相引用（`$ref`），需递归展开嵌套 model 获取完整字段列表
    - Swagger JSON 可能很大（183+ definitions），不要一次性返回全部内容，分步提取
11. **接口数量合理性校验**: 按 Controller 过滤后，如果只得到 1~2 个接口，必须暂停排查。常见原因：(a) `controllerName` URL decode 不正确（如空格被编码为 `+` 而非 `%20`）；(b) Swagger JSON 中 `tags` 数组的值与预期不一致；(c) 错误地按 `operationId` 过滤而非按 `tags` 过滤。一个 Controller 通常有 5~30 个接口
12. **订单号必须用真实值**: 入参中的 `rentRecordNo`、`orderSN`、`orderNo` 等订单号字段，**禁止**使用 "TEST_RECORD_NO" 等假值。必须根据被测接口所属网关（API路径第一段），调用对应的订单列表接口动态获取。若映射表中无对应网关配置，提示用户补充
13. **自动清理测试数据**: 测试执行完成后自动清理新增接口产生的数据（Step 5B）。要点：(a) 清理配对在 Step 3 识别并向用户确认；(b) 只清理正向且执行成功的用例产生的数据；(c) 从响应中提取 ID 时注意多种路径格式（`data`/`data.id`/`data.list`）；(d) 清理失败不阻塞报告生成，在报告"数据清理结果"区块中标注；(e) 若新增接口无对应删除接口，提醒用户手动清理
