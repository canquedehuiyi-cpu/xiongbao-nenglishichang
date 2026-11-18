---
name: swagger-api-parser
description: 从 Swagger/Knife4j 页面提取接口定义，通过 fetch Swagger JSON 获取指定 Controller 下的全部接口及完整参数（含嵌套 $ref 递归展开），输出结构化 API 定义。当用户说"解析接口"、"提取接口"、"读取Swagger"、"Knife4j接口"、"获取API定义"、提供 doc.html 链接要求提取接口信息时使用。
version: 1.0.0
---

# Swagger/Knife4j 接口定义提取

从 Swagger/Knife4j 页面中，通过直接获取 Swagger JSON 来提取指定 Controller 下的全部接口定义及完整参数结构。

## 适用场景

- 用户提供 Swagger/Knife4j 页面链接（URL 含 `doc.html`），需要提取接口定义
- 需要获取某个 Controller 下所有接口的完整参数（含嵌套 model 展开）
- 需要将接口信息输出为结构化格式供后续使用（如生成文档、测试用例、前端代码等）

## 工作流

### Step 1: 收集信息

向用户收集以下信息（用 AskUserQuestion 或从对话中提取）：

| 信息 | 必填 | 说明 |
|------|------|------|
| Swagger/Knife4j 页面链接 | 是 | URL 含 `doc.html` 的页面地址 |
| 提取范围 | 否 | 默认提取 URL 中当前展开 Controller 的全部接口；也可指定其他 Controller 或全部接口 |

### Step 2: 打开页面并解析 URL

1. **用 `mcp__builtin_browser__navigate` 打开 Swagger 页面**
   - 确保页面加载完成（等待 3-5 秒）
   - 从 URL hash 中提取 `group` 和 `controllerName`

**URL 结构解析**：

Knife4j URL 格式：`http://{host}/doc.html#/{group}/{controllerName}/{operationId}`

示例：
```
http://backend.dev2.com/doc.html#/loverent-sales-business-backend/loverent-aliorder-api-boot%20接入服务/prepaymentOrderUsingPOST
```
- `group` = `loverent-sales-business-backend`（用于构造 Swagger JSON 端点）
- `controllerName` = `loverent-aliorder-api-boot 接入服务`（URL decode 后，用于按 `tags` 过滤）
- `operationId` = `prepaymentOrderUsingPOST`（当前展开的具体接口）

### Step 3: 获取 Swagger JSON

> **关键：全量接口发现**
> URL hash 中的 `operationId`（如 `prepaymentSimpleOrderUsingPOST`）只是用户当前展开的 **一个** 接口。
> 你必须按 `controllerName`（即 `tags` 字段）过滤出该 Controller 下的 **全部接口**，而不是只提取 URL 中提到的那一个。
> 一个 Controller 通常包含 5~30 个接口，只取 1 个是严重遗漏。

**直接 fetch Swagger JSON**：

用 `mcp__builtin_browser__javascript_tool` 执行 fetch 请求：
```javascript
(function(){ return fetch('/{group}/v2/api-docs').then(function(r){ return r.json(); }).then(function(j){ window.__swaggerJSON = j; return JSON.stringify({pathsCount: Object.keys(j.paths||{}).length, defsCount: Object.keys(j.definitions||{}).length, tagsCount: (j.tags||[]).length}); })()
```

注意：
- `javascript_tool` 多行脚本返回 undefined，必须用单行 IIFE + `window.__swaggerJSON` 暂存
- Swagger JSON 可能很大（183+ definitions），不要一次性返回全部内容，分步提取

**Swagger JSON 端点规律**：
- 端点格式：`/{servicePrefix}/v2/api-docs`
- URL hash 中的 `group` 名 **不等于** `servicePrefix`（如 group=`loverent-sales-business-backend` 但端点是 `/salesBusinessBackend/v2/api-docs`）
- 如果 `/{group}/v2/api-docs` 返回 404，需要从网络请求中发现实际端点
- 可用 `mcp__builtin_browser__read_network_requests` 查看页面加载时发出的请求来定位正确的端点

### Step 4: 按 Controller 过滤接口

从 `window.__swaggerJSON` 中提取当前 Controller 的所有接口：
```javascript
(function(){ var j = window.__swaggerJSON; var ctrl = decodeURIComponent('{controllerName_from_url}'); var apis = []; for (var path in j.paths) { for (var method in j.paths[path]) { var api = j.paths[path][method]; if (api.tags && api.tags.indexOf(ctrl) !== -1) { apis.push({path: path, method: method.toUpperCase(), summary: api.summary, operationId: api.operationId}); } } } window.__filteredAPIs = apis; return JSON.stringify({controller: ctrl, count: apis.length, apis: apis}); })()
```

**重要规则**：
- **只取当前展开 Controller 下的接口**，不是全部接口（除非用户要求全部）
- **强制校验**：过滤完成后，必须输出接口数量。如果一个 Controller 只过滤出 1~2 个接口，极有可能是 tags 匹配有误（如 URL encode/decode 不一致），需要排查
- 典型 Controller 包含 5~30 个接口，若数量明显偏少则停止并检查

**接口数量合理性校验**：
按 Controller 过滤后，如果只得到 1~2 个接口，必须暂停排查。常见原因：
- `controllerName` URL decode 不正确（如空格被编码为 `+` 而非 `%20`）
- Swagger JSON 中 `tags` 数组的值与预期不一致
- 错误地按 `operationId` 过滤而非按 `tags` 过滤

### Step 5: 向用户确认接口清单

将过滤出的全部接口以编号列表展示（序号 + 方法 + 路径 + 说明），并标注总数。

**必须**让用户确认清单是否完整正确，再继续提取参数详情。

示例输出格式：
```
从 Controller「loverent-aliorder-api-boot 接入服务」中共发现 14 个接口：
1. POST /inside_sales_business/api/aliOrder/applyBySale — 企租销售人员申请下单
2. POST /inside_sales_business/api/aliOrder/companyBindPrepayInfo — 绑定预付单信息
... (共14个)
请确认是否完整，是否需要排除某些接口？
```

### Step 6: 提取每个接口的参数详情

对每个接口，从 `parameters` 中找 `$ref` 指向的 model，再从 `definitions` 中展开：

```javascript
(function(){ var j = window.__swaggerJSON; var api = j.paths['{path}']['{method}']; var params = api.parameters || []; var result = []; for (var i = 0; i < params.length; i++) { var p = params[i]; if (p['in'] === 'body' && p.schema && p.schema['$ref']) { var modelName = p.schema['$ref'].replace('#/definitions/', ''); var model = j.definitions[modelName]; if (model) { var fields = []; var required = model.required || []; for (var fname in model.properties) { var f = model.properties[fname]; fields.push({name: fname, type: f.type || (f['$ref'] ? f['$ref'].replace('#/definitions/','') : 'object'), format: f.format || '', description: f.description || '', required: required.indexOf(fname) !== -1}); } result.push({name: p.name, modelName: modelName, fields: fields}); } } else { result.push({name: p.name, in: p['in'], type: p.type || '', required: p.required || false, description: p.description || ''}); } } return JSON.stringify(result); })()
```

**递归展开嵌套 model**：
- 如果字段的 `type` 是 `array` 且 `items` 含 `$ref`，需递归展开嵌套 model
- 如果字段本身是 `$ref`（非 array），也需递归展开
- 递归时注意避免循环引用（同一 model 不要重复展开超过 2 层）

### Step 7: 输出结构化 API 定义

将提取的内容结构化为 API 定义数组：

```json
[
  {
    "name": "接口名称/summary",
    "method": "POST",
    "path": "/api/xxx/create",
    "operationId": "createUsingPOST",
    "headers": {"Content-Type": "application/json"},
    "params": [
      {"name": "field1", "type": "string", "required": true, "desc": "字段说明"},
      {"name": "field2", "type": "number", "required": false, "desc": "字段说明"},
      {"name": "nestedObj", "type": "object", "required": false, "desc": "嵌套对象说明", "fields": [
        {"name": "subField1", "type": "string", "required": true, "desc": "嵌套字段说明"},
        {"name": "subField2", "type": "integer", "format": "int64", "required": false, "desc": "嵌套字段说明"}
      ]},
      {"name": "itemList", "type": "array", "required": false, "desc": "列表字段说明", "items": {
        "type": "object",
        "fields": [
          {"name": "itemField1", "type": "string", "required": true, "desc": "列表元素字段"}
        ]
      }}
    ],
    "tags": ["controllerName"],
    "consumes": ["application/json"],
    "produces": ["*/*"]
  }
]
```

**输出方式**（根据用户需求选择）：
- 直接在对话中以 JSON 格式展示
- 保存为 `.json` 文件供后续使用
- 转换为 Markdown 表格形式的接口文档
- 其他用户指定的格式

## Swagger JSON 关键结构参考

- `paths`: 所有接口定义，key 为路径，value 为方法对象（含 `tags`, `summary`, `parameters`, `operationId`）
- `definitions`: 所有 model 定义，key 为 model 名，value 含 `required`（必填字段数组）和 `properties`（字段详情）
- `tags`: Controller 分组名称数组
- 参数中 `in: "body"` 的 `schema.$ref` 指向请求体 model
- 字段中 `$ref` 指向嵌套 model，`items.$ref` 指向数组元素 model
- `format: "date-time"` 表示日期时间类型（对应毫秒时间戳），`format: "int32"/"int64"` 表示整数类型

## 注意事项

1. **直接 fetch JSON，不要逐一点击侧边栏**：通过 `/{servicePrefix}/v2/api-docs` 获取完整 Swagger JSON 比逐页点击高效准确得多
2. **javascript_tool 返回 undefined 问题**：必须用单行 IIFE + `window.__swaggerJSON` 暂存大数据，再分步提取。直接赋值 `window.x = val` 返回 undefined，须用 IIFE 显式 return
3. **大 JSON 分步提取**：Swagger JSON 可能很大（183+ definitions），不要一次性返回全部内容，先存 `window.__swaggerJSON`，再按需分步提取
4. **group ≠ servicePrefix**：URL hash 中的 group 名不等于 Swagger JSON 端点的 servicePrefix，需要从网络请求中发现实际端点
5. **按 tags 过滤而非 operationId**：要获取 Controller 下全部接口，必须按 `tags` 字段匹配 `controllerName`，不能按 `operationId` 过滤
6. **URL decode 注意**：`controllerName` 从 URL hash 中提取时需要 `decodeURIComponent`，注意空格可能被编码为 `%20` 或 `+`
7. **嵌套 model 递归展开**：`definitions` 中的 model 可能互相引用（`$ref`），需递归展开嵌套 model 获取完整字段列表，注意避免循环引用
8. **接口清单必须用户确认**：过滤出接口列表后，必须展示完整清单（含总数）让用户确认，再继续提取参数详情
