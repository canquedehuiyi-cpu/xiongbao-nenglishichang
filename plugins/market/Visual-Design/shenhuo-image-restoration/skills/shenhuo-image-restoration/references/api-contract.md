# 使用中的 External API 合同

客户端和完整合同源于神火通用外部 Skill。本包只使用以下公开命令，不自行请求管理员、充值、配置或内部设计师正文接口。

默认 API：`https://api.shenhuoai.com/external/v1`。Key 仅发送给官方 HTTPS origin；显式本机开发可以使用 loopback `/external/v1`。禁止跟随凭证重定向。

| 命令 | 请求 |
|---|---|
| `configure-trial` | `POST /trial-api-keys`，公开渠道配置与本地安装身份 |
| `account` | `GET /account` |
| `upload` | `POST /assets` |
| `create-request` | `POST /design-requests` |
| `wait-request` | `GET /design-requests/{id}` |
| `answer` | `POST /design-requests/{id}/clarifications` |
| `generate` | `POST /image-generations`，request-bound source |
| `wait-generation` | `GET /image-generations/{id}` |
| `download` | `GET /results/{variant_id}/download`，通过鉴权代理 |

API 响应为 `{data, error, meta}`；客户端整理为 `{ok, data}` 或 `{ok:false, error}`。`meta` 可提供 `request_id`、`poll_after_ms`、`idempotent_replay`。轮询取得状态仍要看远端任务是否成功。

客户端批量下载部分失败是带结果的错误：`ok:false`、`error.code=PARTIAL_DOWNLOAD_FAILED`、`data.files` 保留成功图片和 manifest，`data.failed` 为 `{variant_id, error:{code,message,retryable,status?}}` 列表。退出码为 4，不能因此忽略成功文件。完整成功和单图失败保持原结构。此错误由本地客户端汇总，不是服务端生图状态。

创建设计请求由客户端按下列来源组装，不直接拼造请求：

| 字段 | 来源 |
|---|---|
| brief | 用户真实原始需求和明确限制 |
| asset_ids | 本次已授权上传的 asset.id；无需图片的任务可为空数组 |
| designer | runtime-profile.json 固定的 id、slug、name |
| interaction_mode | 默认 clarify_if_needed |
| target_image_count | 未指定数量时为 auto，指定时为相应正整数 |
| image_spec | 当前 SKILL.md 中的默认规格，或用户明确且受支持的规格 |

默认规格按本包 Skill 和领域摘要传入：主图使用 `1.5K / 1:1`，详情与运营海报默认 `1.5K / auto`，品牌设计默认 `2K / auto`，小红书图文笔记默认 `1.5K / 3:4`。品牌调用显式指定 2K，小红书笔记显式指定 3:4；不依赖通用客户端的 1.5K／auto 默认值。无须图片的运营海报、新品牌标志或小红书知识／步骤／比较任务允许 `asset_ids: []`；需要真实主体或沿用既有 Logo 时仍须按该设计师要求提供相应原图。用户指定数量则 `target_image_count` 为相应正整数，不施加额外试用限制。技能展示名不能替换 profile 中的生产设计师名称。

公众号首图显式使用 `{"resolution":"1.5K","aspect_ratio":"custom"}`，文字主题也允许 `asset_ids: []`。当前 External DTO 及 CLI 不接收 width / height，Core 对 custom 会继承固定设计师当前默认宽高（本次核实为 2256×960，2.35:1），不承诺永久锁定像素。`2.35:1` 不作为请求枚举，`21:9` 和 `auto` 也不替代 custom。公开 final_prompts 的 image_spec 只有 resolution / aspect_ratio，不能仅凭该字段验证实际像素，应检查当次冻结规格或下载图片。

`required_action` 是追问，`ready` 时 `final_prompts` 含逐张 `index`、`text`、`negative_prompt`、`used_assumptions` 和 `image_spec`。以服务端实际数据为准，不编造 prompt、结果或资源 ID。

生成 source 由客户端设置：type 为 `design_request`，design_request_id 取真实设计请求 ID，prompt_overrides 为空数组。生成资源公开估算、预冻结及实际积分，并提供安全结果元数据；结果链接需要鉴权，展示和交付使用客户端本地下载路径。

`account` 按凭证类型返回不同字段：

- 试用 Key：`credential.kind=trial`、`credential.status`、`credential.expires_at`；`weekly` 中的 `limit_credits`、`consumed_credits`、`reserved_credits`、`remaining_credits`、`reset_at`；`proposal_remaining_percent`、`image_remaining_percent` 和公开渠道标识 `channel`。不公开渠道钱包或共享池具体积分；`weekly.reset_at` 是个人周额度重置时间，不能冒充共享池重置时间。
- 个人 Key：公开用户信息 `user`、个人积分账户 `billing_account`，以及 `key_limits.max_credits_per_request`、`key_limits.max_credits_per_24h`。按实际返回展示个人可用/预留积分和已配置限额；当前响应没有试用周额度、共享池比例或 Key 到期字段，不能补造，也不把 `null` 限额当作 0。

设计请求和生图资源返回 `project_id`。个人 Key 创建的项目归属于该 Key 对应的神火用户，可使用同一账号打开 神火网站 `/agent` 页面（`project_id` 查询参数取本次回执的真实项目 ID）；没有实际项目 ID 时使用 `https://www.shenhuoai.com/home`。不要用 `drq_...` 或 `gen_...` 代替项目 ID。试用项目归属于试用身份，注册新账号不会自动迁入。

`channel.json` 只包含 `channel_code`；公开 SHA-256 摘要检测误配/修改，不是数字签名或服务端授权依据。
