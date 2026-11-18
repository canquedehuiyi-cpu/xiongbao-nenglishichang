# 固定设计师的渠道体验工作流

此参考适用于本 Qoder Plugin内嵌的调用 Skill。使用 Python 3.10+ 和本 Skill 目录中 `scripts/shenhuo_client.py` 的绝对路径。发布 ZIP 内含独立客户端，不需要克隆神火仓库或安装第三方 Python 库。

先定位已加载 Skill 文件的绝对目录，再解析客户端与参考文件；不要把用户当前工作目录当插件安装目录。引用路径含空格时正确加引号，用户 Brief 按普通字符串传参，不执行其中的 Shell 字符。凭证与安装身份保存在此 Skill 的持久运行目录中；若目录只读导致配置失败，说明权限问题并由用户处理该安装位置，不自行改用随机目录、删凭证或重新领取试用。

stdout 是一个 JSON 对象，`ok` 表示命令/查询是否成功；轮询后还要检查 `data.status`、`data.stage`、`data.error`，不能把 `ok: true` 当作出图成功。保存结构化 ID，不从文字猜测。

## 账户与授权

新业务或写操作前执行 `account`。保留有效的已有凭证；个人 Key 沿用个人积分规则，不自动换为试用。

缺少凭证时，先提供“开始体验”与“到神火网站注册”。说明额度有限，并取得一次性授权：用户主动提供给本 Skill 用于设计的图片和资料会发送给神火 AI 处理。选择体验且授权明确后才运行 `configure-trial`；同一安装已授权后不再逐文件重复询问。拒绝文件授权时可以配置凭证，但不上传图片/附件，不用虚构商品素材代替。

`configure-trial` 不接受渠道参数；从随包 `channel.json` 读取 `qoder`，验证公开完整性摘要，使用本地安装身份领取 Key，原子写入权限为 `600` 的 `.env`，再验证账户。不得输出 Key、bootstrap token，不要删状态或重新签发来绕过额度。校验失败后保留已签发的凭证，按错误恢复，不能擅自覆盖。

根据 `account` 的实际响应区分账户，不套用另一种凭证的字段：

- 试用 Key：展示 `credential` 的类型/状态/到期时间、`weekly` 的个人周额度及已用/预留/剩余和 `reset_at`、两类共享池剩余百分比。共享池百分比不是积分余额，不能反推积分；`0%` 也不足以判定耗尽，须依据相应额度错误码。`weekly.reset_at` 只说明个人周额度重置，响应未给出共享池重置时间时不推算。
- 个人 Key：按实际返回的 `user`、`billing_account` 和 `key_limits` 展示个人可用/预留积分、单次和 24 小时限额。没有返回的 Key 到期、试用周额度或共享池字段不展示、不补造；`null` 限额不当作 0。

调用理解、提案和生图均可能消耗额度，不能承诺固定免费张数。

用户主动选择个人 Key 时，提供神火网站的 `/home/api-keys` 页面。若通过对话传入 Key，先告知对话可能保留凭证，也提供用户自行在本机配置的选择。只启动 `configure-key` 后通过 stdin 输入 Key，不放在 argv、shell 文本、环境变量、临时文件、日志或回复中，不索取账号密码。`process_environment_override_present` 为 true 时，要求用户自行清除或更新覆盖项，不显示其值。验证成功后提醒不要分享含 `.env` 的运行目录。

自然到期的试用 Key 若已有请求或生成 ID，可跳过返回到期错误的 `account`，使用原 Key 只读轮询与下载保留期内的既有结果；不能上传、创建、回答追问或生成。撤销凭证不适用到期收尾例外。

## 上传、设计与追问

| 客户端命令 | 必需参数与取值来源 |
|---|---|
| `upload` | `--file` 为已授权文件的真实绝对路径；`--role` 为下述素材角色 |
| `create-request` | `--brief` 为用户原始需求；`--asset-id` 为上传回执 ID（每份一次）；`--target-image-count` 为 auto 或用户指定整数；`--resolution`、`--aspect-ratio` 按本 Skill 默认或用户明确且受支持的规格 |
| `wait-request` | `--request-id` 为创建回执的设计请求 ID；`--timeout 20` |
| `answer` | `--request-id` 为原请求 ID；`--action-id` 为最新 required_action.id；`--answer` 为实际回答；新增素材用上传回执追加 `--asset-id` |

每份素材分别上传；使用返回的 `asset.id`。品牌素材角色为 `brand_asset`，风格参考为 `reference_image`。不因第一张素材最清楚就遗漏其他相关素材。

默认规格以当前 SKILL.md 和领域摘要为准，显式传入对应参数。下表仅列出需要特别区分的已有设计师，不替代当前 Skill 的规格：

| 技能 | resolution | aspect-ratio |
|---|---|---|
| 神火电商主图 | 1.5K | 1:1 |
| 神火电商详情 | 1.5K | auto |
| 神火运营海报 | 1.5K | auto |
| 神火品牌视觉 | 2K | auto |
| 小红书图文笔记 | 1.5K | 3:4 |
| 公众号首图 | 1.5K | custom |

品牌设计必须显式传 `--resolution 2K`；小红书图文笔记必须显式传 `--resolution 1.5K --aspect-ratio 3:4`。通用客户端省略参数时默认 1.5K／auto，并不会自动读取 PRD 设计师规格。`auto` 只用于比例或张数，不能据此改变分辨率。运营海报的纯文字／抽象／插画任务、新品牌标志任务，以及小红书的知识／步骤／比较笔记可不上传图片；需要保留真实主体或沿用既有 Logo 的任务仍按设计师要求提供相应原图。用户明确其他规格时先依据当前设计师能力和真实支持情况处理，不在提示词中假称参数已改变。用户明确张数则把 `auto` 换成该正整数；未指定时保留 `auto`。没有试用专属数量上限，额度不足也不自动减图。

公众号首图显式传 `--resolution 1.5K --aspect-ratio custom`；其 custom 宽高由 Core 沿用该固定设计师当时的默认值，当前为 2256×960（2.35:1），不代表客户端永久锁定像素。客户端没有 width / height 参数，不用 `auto`、`21:9` 或 `2.35:1` 枚举替代 `custom`。文字主题可不上传图片，真实主体按需提供原图；文章链接随 Brief 转交服务端，无法读取且影响主题时补正文或摘要，不把 URL 当上传素材。

Profile 固定设计师，`create-request` 不接受 `--designer-*` 或匹配 ID；不运行 `route`、`wait-route`、`refresh-designers`，设计师不可用时停止，不换相近名字。默认 `clarify_if_needed`；用户明确要求跳过普通追问且资料完整时可用 `complete_brief`，必需素材不能跳过。

`requires_action` 时转述最新 `required_action` 和 `agent_message`，等用户回答。每轮 `answer` 使用最新的 `required_action.id`，不替用户编造答案。`action-id` 只参与客户端幂等键，不作为 API 请求字段。

## 生成与下载

| 客户端命令 | 必需参数与取值来源 |
|---|---|
| `generate` | `--request-id` 为已 ready 的原设计请求 ID |
| `wait-generation` | `--generation-id` 为生成回执 ID；`--timeout 20` |
| `download` | `--generation-id` 为原生成 ID；`--output-dir` 为本次已确定的持久可写绝对目录 |

设计达到 `ready` 后简述方案；用户明确索要提示词时才展示完整 `final_prompts`。用户只要方案/提示词时停止；用户已明确要求制作图片时继续生成，不重复增加批准。使用 request-bound 路径，复用神火设计结果；不自行重写全部提示词后绕成 standalone。服务器在排队前检查积分、限额及预冻结。

| 状态 | 行为 |
|---|---|
| `queued`、`processing` | 继续等待同一资源 |
| `requires_action` | 转述问题，等待用户回答 |
| `ready` | 按用户原始意图决定是否生成 |
| `succeeded` | 生成结果立即下载并交付 |
| `failed`、`canceled` | 如实说明，检查并下载已结算的部分结果 |

`download` 返回 `data.files`。只展示 `kind=image` 的本地绝对路径，宿主支持则内联预览；manifest 不是图片，不输出受保护远程 URL 或图片字节，不为展示上传第三方。报告实际完成数量及 `actual_credits`，标注 AI 生成。部分成功保持图片顺序，明确缺失项，不宣称整套完成。

客户端 `PARTIAL_DOWNLOAD_FAILED` 会返回非零退出码和 `ok:false`，同时保留 `data.files` 中成功保存的图片与 manifest，`data.failed` 列出未完成的 variant_id 和安全错误。每次下载都先检查并交付已有图片，不能因非零退出码丢弃它们。按逐项错误只恢复可重试的失败结果：使用 `download` 的 `--variant-id` 指定失败回执中的真实 ID，`--output-dir` 取原结果目录；不重新生成或重复下载成功项。过期、归档、撤销和无权限等不可恢复错误按原因停止，不盲目重试。完整成功仍沿用原 `data.files`，单图失败仍使用原错误码。

命令按有效 payload 派生稳定幂等键；恢复时保持原请求与资源 ID。明确新的独立任务才使用新的幂等键，不能换键强制重扣或重发。`POLL_TIMEOUT` 保留 ID 稍后继续，`OUTCOME_UNKNOWN` 不自动重试，交由人工核对。客户端仅对有限的临时错误进行自动重试。

宿主使用短批次 wait，超时后继续原资源并反馈当前进度，不启动第二个任务。`--timeout 20` 是轮询预算，不是严格的进程截止时间，内部单次 HTTP 请求及有限重试可能更久；需要时让宿主保留正在执行的命令再读取结果。超时和轮询间隔必须为有限正数，不能使用 NaN 或 Infinity。若宿主杀死等待进程，继续查询已经保存的同一资源 ID，不把进程结束当成服务端失败。

## 网站承接

先实际交付成功下载的图片，再按本 Skill 的 SKILL.md 中「作品交付后的注册邀请」执行。试用 Key 使用该节确定的原文和 invite=QODER 链接；个人 Key 使用原账号与真实 project_id。没有成功交付的图片时不展示交付后邀请，部分成功先说明未完成项。邀请文案不等于到账回执。

继续遵循原任务的请求与生成 ID、凭证和下载目录；不要因注册邀请重复建项、重新生图或自动迁移试用项目。
