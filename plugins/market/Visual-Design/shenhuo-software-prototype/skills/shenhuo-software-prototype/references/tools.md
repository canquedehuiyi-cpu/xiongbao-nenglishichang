# MCP工具合同

使用Qoder实际发现的神火设计师工具，不根据专家名称拼工具前缀。以当前工具Schema与回执为准，连接和授权由宿主管理。

| 工具 | 输入与用途 |
|---|---|
| get_account | 无参数；核验个人账号与实际积分 |
| get_designer | designer_id；核验固定设计师的输入要求、默认规格、公开档位 |
| create_upload | filename、mime_type、role、idempotency_key，可选label；获取原始字节上传票据 |
| get_upload | transfer_id；确认资产ID与哈希 |
| create_design | brief、designer_id、idempotency_key；可选asset_ids、target_image_count、image_spec；建项并提案 |
| get_task | kind=design／generation，task_id；查询原设计或生成任务 |
| answer_questions | design_request_id、answer、idempotency_key；可选新增asset_ids；真实追问回答 |
| quote_images | design_request_id、idempotency_key；取得当前整组报价 |
| generate_images | design_request_id、quote_id、idempotency_key、user_confirmed=true；仅在确认当前报价后生图 |
| get_result | variant_id、idempotency_key；领取已结算作品预览与下载凭证 |

固定设计师见 [身份](designer-profile.json)：`des_d652dc73d8ae`／`software_prototype_designer`。不调用match_designer，不传routing_evaluation_id；设计师不可用时说明并暂停图片制作，不自动换人。任务查询用实际 `drq_` 或 `gen_` 资源ID，不用project_id、job_id或run_代替。

手机默认 `image_spec={"resolution":"1.5K","aspect_ratio":"9:16"}`，PC默认16:9或16:10；明确规格在建项前确定，双端分别建项。将用户明确采纳的本次张数传整数，未明确传auto并保留原始数量意图；以服务返回清单核对是否符合用户需求。公开模型档位跟随设计师实时默认，只展示Pro／Flash等公开名称。

当前没有语义修改／重生成工具。改图走 [原图参考新任务](visual-iteration.md)，不编造revise_image，不调用图层分离代替。工具新增时先核验真实Schema和报价合同，不因为文档提及能力就假定可用。

权限不足优先由宿主刷新原连接；报价过期重新报价确认；余额不足按 [MCP流程](mcp-workflow.md) 暂停付费。不同写操作用不同稳定键，同一操作超时只能同键同参数重放或查询原ID。内容安全拒绝停止对应操作，不换服务或改写绕过。
