# 神火工具导航

真实名称、前缀、字段、枚举和可用能力以当前宿主加载的 MCP Schema 为准。下列是流程角色，不是可直接复制的参数 Schema。工具缺失先恢复市场连接，不用 HTTP 直连替代。

| 工具 | 使用时机 |
|---|---|
| get_account | 图片阶段核验神火个人账号和积分；费用只引真实字段 |
| list_designers | 读取当前目录，不代替付费匹配结果 |
| get_designer | 指定/选定设计师的素材要求、默认规格与公开档位 |
| create_upload / get_upload | 原始素材上传与核验 |
| match_designer | 未指定设计师时真实匹配，可能消费积分，保留 routing_evaluation_id |
| create_design | 原始需求、真实素材、用户选定设计师与原匹配记录建项 |
| answer_questions | 只提交用户对真实 required_action 的回答与新增素材 |
| get_task | 按正确 kind 和原资源 ID 查询/恢复，不以查询创建新任务 |
| quote_images | 获取当前有效整组报价，区分 prior_consumed_credits、预估和 reservation_credits |
| generate_images | 用户确认当前报价后提交，同参数同幂等键恢复 |
| get_result | 领取原 variant_id 的已结算作品，短期原始回执交文件工具 |

`rte_` 匹配、`drq_` 设计请求、`gen_` 生图任务、project_id 与内部工作流 ID 不混用。详细执行顺序、状态、轮询、费用及安全拒绝见 [设计合同](./design-contract.md)。只有 actual_credits 或真实结算回执证明对应费用；恢复旧任务不代表新增消费，不能用余额差推算。

本插件工作台使用上述设计工具；服务可能另外提供图层能力，但首版不会自动调用。内容安全拒绝如 CONTENT_SECURITY_REJECTED 应保留真实原因，不能换工具绕过。宿主的检索、文件、浏览器能力按实际发现结果使用，不在包内编造统一工具名。
