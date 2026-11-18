# 契约文档模板

生成契约文档时严格套用以下骨架。`{}` 为占位，其余结构（含小节顺序）不得增删。

## 文档骨架

````markdown
# {模块中文名} 接口契约

> 依据后端接口清单（{清单来源/日期}）生成，字段以 {后端代码仓 / 对接明细文件} 为准。
> 面向前端（salt-data-web）联调使用。

## 1. 全局声明

### 1.1 Envelope（已定稿：ApiResponse，规范 §2.3）

| 项 | 本模块约定 |
|---|---|
| 成功 | `{ "success": true, "data": <T>, "error": null, "traceId": "...", "timestamp": "..." }` |
| 失败 | `{ "success": false, "data": null, "error": { "code", "message", "details" }, "traceId": "...", "timestamp": "..." }` |
| HTTP 状态 | 语义化：200/201 成功；400/401/403/404/409/422/500 按语义 |
| 204 | 无响应体，仅限无返回值接口，前端不按 ApiResponse 解析 |
| 错误码 | 语义化字符串置于 `error.code`；前端只按 `success` 与 `error.code` 分支，禁止依赖 message 文案 |
| `details` | 字段级错误明细（如有） |
| mock 例外 | 契约不覆盖 mock；mock 接口仍用 `{code:'00000', message, data}` 风格（规范 §2.3） |

{若后端明细/代码与上述定稿不一致（如出现 `{success:false, errorCode, message}` 旧形态），照实记录并标 `【待确认】`，汇总文末}

### 1.2 通用字段约定

| 项 | 本模块约定 |
|---|---|
| 鉴权 | Bearer token；租户/企业由 token 解析，前端不另传 tenantId/enterpriseId |
| ID | 雪花 ID 等 string 传输，前端按字符串保存 |
| 时间 | `yyyy-MM-dd HH:mm:ss`（Asia/Shanghai）；日期入参 `yyyy-MM-dd` |
| 金额 | string，两位小数 |
| 可空语义 | null / 键省略（逐字段在表中标注） |
| 分页 | pageNum（从 1）+ pageSize；非法值处理：{填写} |

### 1.3 环境地址（{{baseUrl}}）

| 环境 | baseUrl |
|---|---|
| 联调 | {填写} |
| 测试/pre/生产 | {填写} |

## 2. 接口清单

| 编号 | 接口名称 | 方法 | 完整路径 | 状态 |
|---|---|---|---|---|
| {编号} | {中文名} | GET/POST | /api/v1/... | 已就绪/开发中 |

## 3. 接口明细

{按下方单接口模板逐个输出，仅"已就绪"接口}

## 4. 缺口提示

{清单外被依赖但未列入的接口、需后端补充的项；无则写"无"}

## 5. 待确认清单

| 项 | 所在接口 | 问题 |
|---|---|---|
| {失败响应形态} | {编号} | {描述} |

{无则写"无"}
````

## 单接口模板

````markdown
### {编号} {接口中文名}

- **接口路径**：`{METHOD} {完整路径}`
- **所属模块**：{模块名}
- **调用时机**：{前端调用场景；可留空待前端补}
- **鉴权**：是（Bearer token）
- **幂等**：是——`Idempotency-Key` header，{重复提交返回首次结果/报错} / 否
- **HTTP 状态**：成功 {200/201}；失败 {填写语义化状态，如 400/404/409}

#### 请求示例

```http
{METHOD} {{baseUrl}}{完整路径}
Authorization: Bearer {{token}}
Content-Type: application/json
{其他 header}

{body JSON；GET 无 body 则省略}
```

#### 请求字段

| 位置(Header/Path/Query/Body) | 字段 | 类型 | 必填 | 含义 |
|---|---|---|---|---|
| | | | | {枚举全量、默认值、校验规则、防混淆注记写在此列} |

#### 响应示例

成功：

```json
{ "success": true, "data": { "...": "业务 payload 完整字段" }, "error": null, "traceId": "...", "timestamp": "..." }
```

失败（HTTP {语义化状态}）：

```json
{ "success": false, "data": null, "error": { "code": "{语义化错误码}", "message": "{用户可读原因}", "details": null }, "traceId": "...", "timestamp": "..." }
```

{后端明细为旧形态或缺失时，标 `【待确认】`，禁止照抄旧形态}

#### 响应字段

| 字段 | 类型 | 可空性(null/省略) | 中文注释 |
|---|---|---|---|
| data.xxx | | | {枚举全量、语义边界、防混淆、ID 来源} |

#### 错误码

| error.code | HTTP 状态 | message 示例 | 场景 | 可重试 |
|---|---|---|---|---|
| | | | | |

#### 备注

- 异步任务：{创建后状态流转、前端轮询接口与间隔、终态枚举；无则省略本条}
- 状态机/字段联动：{如"仅 processingStatus=SUCCEEDED 可调本接口"；无则省略}
````

## 字段注释写法示例（对齐 U02 明细，新文档保持同风格）

| 场景 | 示例注释 |
|---|---|
| 防混淆 | 批次雪花 ID，来自 B01 的 `data.list[].id`；不是 SRC 开头的 batchNo |
| 防混淆 | 非空文件 ID 列表，取通用上传接口返回的 fileId；不是控件 uid、OSS URL 或本地路径 |
| 语义边界 | 预估收益两位小数；省略 = 未计价，不等同于 0 元 |
| 语义边界 | 待补充授权数，按协议类型/主体/被授权方去重，不是影响的数据行数 |
| 枚举全量 | RECEIVED 已接收、PROCESSING 处理中、SUCCEEDED 成功、FAILED 失败、UNKNOWN 未知 |
| 兼容别名 | PENDING_SETTLEMENT 待结算、SETTLED 已结算；兼容 PENDING 表示待结算 |
| 非法值处理 | pageSize 默认 10；允许 10、50、100，其他值按 10 处理 |
| ID 序列化 | 批次雪花 ID，前端按字符串保存，避免数值精度丢失 |
| 错误码分段 | 前缀按模块：`AUTH_` 用户认证、`AGREEMENT_` 协议/合同、`BATCH_` 数据批次 |
