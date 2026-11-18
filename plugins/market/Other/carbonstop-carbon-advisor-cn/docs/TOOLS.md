# 工具清单与复现步骤

本连接器只提供两个只读工具，没有独立比较接口。以下参数说明用于交接，以授权后 `tools/list` 的实时 schema 为准；不要把业务参数直接作为 HTTP REST 正文提交。

## 工具参数

| 工具 | 参数 | 说明 |
| --- | --- | --- |
| `search_emission_factors` | `query` | 必填，具体材料或活动关键词 |
| 同上 | `language` | `zh` 或 `en`；国内版显式使用 `zh` |
| 同上 | `accountingType` | `product` 或 `enterprise`，按核算口径选择 |
| 同上 | `filters.country` | 可选字符串数组；按用户地区，不默认中国 |
| 同上 | `filters.year` | 可选年份数组，不混淆发布年与适用年 |
| 同上 | `filters.sourceLevel` | 可选来源等级字符串数组，值以服务支持范围为准 |
| 同上 | `limit` | 通常先取 5，按当前 schema 允许范围控制 |
| `get_emission_factor_detail` | `factorId` | 必填，搜索实际返回的字符串 ID；不能转为数字 |
| 同上 | `language` | `zh` 或 `en`；国内版显式使用 `zh` |

## 可复现任务

测试问题：查找中国电力排放因子，展示候选的单位、适用年份、系统边界、来源和详情链接；详情不足时选一个候选读取详情。

授权连接后先按 MCP 流程初始化并发现工具。以下是一次 `tools/call` 的 JSON-RPC 请求示例：

```json
{
  "jsonrpc": "2.0",
  "id": 3,
  "method": "tools/call",
  "params": {
    "name": "search_emission_factors",
    "arguments": {
      "query": "电力",
      "language": "zh",
      "accountingType": "product",
      "filters": { "country": ["中国"] },
      "limit": 5
    }
  }
}
```

如需详情，从实际搜索结果选择一个候选，将其字符串 ID 原样放入 `get_emission_factor_detail` 的 `factorId`，并设 `language: "zh"`。本包不提供可误执行的虚构因子 ID。

HTTP 请求发送到公开 MCP 地址，使用用户实际获得的 Bearer Token、`Content-Type: application/json` 和 `Accept: application/json, text/event-stream`；初始化后按协商结果携带 `MCP-Protocol-Version`，其他会话头以实际服务要求为准。Qoder 应执行 `initialize`、`notifications/initialized`、`tools/list`，随后再调用工具。本次没有运行带凭证的请求。

结果可能包含文本 JSON、`structuredContent` 和链接说明。保留服务返回的原始字段及包装层；不要把所有结果假定为裸数组。`isError` 或结构化 `error` 不能当作成功空结果。

## 验收清单（均待 Qoder 实测）

1. 国内回调被注册/授权/换票流程接受；用户同意授权后返回 Qoder，PKCE 成功。
2. 能发现上述两个工具，使用用户令牌完成一次小范围搜索，必要时读取一个真实候选详情。
3. 用中文解释因子适用条件，保留真实详情链接和受限值说明；空结果或受限值不自动判定为连接失败。
4. 刷新后仍能查询；撤权或令牌失效后按规范要求重新授权，不切共享身份或旧接口。
5. 保留 401/403/429 及可用的 requestId、Retry-After；限流时停止，不反复执行或批量消耗额度。

没有结果时说明数据覆盖或筛选条件，不为展示效果编造结果。只读工具仍可能消耗查询额度；测试使用经用户同意的个人账号并控制次数。
