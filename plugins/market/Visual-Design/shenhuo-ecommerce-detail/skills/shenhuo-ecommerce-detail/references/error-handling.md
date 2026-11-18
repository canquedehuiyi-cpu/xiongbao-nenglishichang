# 错误与中断恢复

先检查 `ok`，查询成功还要检查 `data.status` 和 `data.error`。只使用结构化错误码与公开响应字段，不输出请求头、环境变量、完整 Key、签名 URL 或受保护下载地址。

下载例外：无论退出码或 `ok` 值，先检查 `data.files` 并交付其中成功保存的图片，再说明错误和未完成项。

| 错误或状态 | 行为 |
|---|---|
| `SHENHUO_API_KEY_MISSING` | 提供开始体验/网站注册选择；用户明确选择体验后配置，不静默领取 |
| `CLIENT_USAGE_ERROR` | 根据安全错误说明核对客户端参数、有限正数超时、API 地址格式或安装目录写权限；不输出配置值，不把配置失败说成额度耗尽 |
| `TRIAL_CHANNEL_NOT_CONFIGURED`、`PACKAGE_INTEGRITY_ERROR` | 停止并联系发布方重新打包，不让用户猜渠道或跳过校验 |
| `SHENHUO_API_KEY_ALREADY_CONFIGURED` | 保留原凭证，不用试用替换个人 Key |
| `PROCESS_ENVIRONMENT_OVERRIDE` | 请用户自行处理覆盖项，不读取/展示其值 |
| `UNTRUSTED_API_ORIGIN`、`UNTRUSTED_TRIAL_API_ORIGIN` | 停止，不向非官方地址发送凭证 |
| `TRIAL_API_KEY_REPLAY_EXPIRED`、`TRIAL_INSTALLATION_EXISTS` | 停止领取，保留原状态；不换安装 ID、幂等键或删缓存重复领取 |
| `TRIAL_CHANNEL_NOT_ACTIVE`、`TRIAL_CHANNEL_PAUSED` | 如实说明渠道未启用或暂停，不归因用户额度已用完 |
| `TRIAL_KEY_WEEKLY_LIMIT_EXCEEDED` | 报告公开额度/重置时间，等待重置或引导网站注册 |
| `TRIAL_CHANNEL_PROPOSAL_QUOTA_EXHAUSTED`、`TRIAL_CHANNEL_IMAGE_QUOTA_EXHAUSTED` | 对应池额度不足；服务端明确提供该池重置时间时才转述，不用个人周额度重置时间替代；不推算或披露池积分，不自动减少图片 |
| `TRIAL_SPONSOR_INSUFFICIENT_CREDITS` | 说明渠道试用暂不可用，不公开渠道钱包 |
| `TRIAL_KEY_EXPIRED` | 停止新写操作，保留原 Key，只读收尾保留期内已有结果 |
| `TRIAL_KEY_REVOKED`、`UNAUTHORIZED`、`INVALID_API_KEY`、`KEY_REVOKED` | 停止，修复本地凭证；撤销不适用自然到期的收尾例外 |
| `FORBIDDEN`、`SCOPE_REQUIRED` | 当前身份无权访问，停止，不更换身份尝试读其他用户资源 |
| `DESIGNER_NOT_FOUND`、`DESIGNER_AMBIGUOUS`、`DESIGNER_MISMATCH` 或固定设计师不可用 | 停止并联系发布方核对 profile；不刷新目录换人或启用匹配 |
| `IMAGE_ASSET_REQUIRED` | 请用户提供必要素材；有既有上传授权时直接上传 |
| `ASSET_NOT_READY` | 等待素材完成处理，复用原请求，不重复上传 |
| `ASSET_REJECTED` 或内容策略拒绝 | 说明原因，停止，不绕过 |
| `INSUFFICIENT_CREDITS` 或个人 Key 限额 | 按实际身份及 `billing_account`/`key_limits` 解释余额或限额；个人用户可使用同一账号打开神火工作台，不要求重新注册；不把试用渠道问题说成用户钱包问题 |
| `IDEMPOTENCY_CONFLICT` | 保留原操作，核对是否确为新的独立任务，不自行换键 |
| `DESIGN_REQUEST_GENERATION_ALREADY_EXISTS` | 有现存 generation ID 时继续轮询，不重复创建 |
| `POLL_TIMEOUT`、`NETWORK_ERROR` | 保留资源 ID；稍后继续原操作，不创建第二份 |
| `RATE_LIMITED`、429、临时 5xx | 沿用客户端有限重试和 Retry-After，保持幂等键 |
| `OUTCOME_UNKNOWN` | 不自动重试，不换幂等键；请支持人员核对，不能承诺匿名试用任务会出现在注册账户里 |
| `RESULT_ARCHIVED`、`RESULT_EXPIRED` | 按实际原因说明结果不可用，当前客户端无恢复接口 |
| `PARTIAL_DOWNLOAD_FAILED` | 先交付 `data.files` 的成功图片，再按 `data.failed` 的逐项代码处理；仅对可恢复项使用对应 variant_id 下载，不新建生图，不丢弃成功文件 |

生成 `failed` 或 `canceled` 仍检查已结算的 `results`，有则下载，准确说明成功与未完成数量及实际积分。技术故障不是强制注册理由，成功图片也不需要额外注册才能下载。
