---
name: shenhuo-main-image-marketing
display_name: 电商主图营销包装
display_name_en: Ecommerce Main Image Marketing
description: 该技能调用神火 AI 固定的“电商主图营销包装”设计师。在现有商品主图上整理卖点、价格优惠与服务权益，保留商品身份，制作商品清楚、条件完整的营销图片。支持渠道体验、必要追问、图片生成和下载。 适用于用户请求“电商主图营销包装”及相应图片设计时。
description_zh: 在现有商品主图上整理卖点、价格优惠与服务权益，保留商品身份，制作商品清楚、条件完整的营销图片。
description_en: Add organized selling points, prices and service benefits to an existing product image while preserving product identity and offer terms.
version: 1.1.0
author: chenyth
---

# 电商主图营销包装

这是本 Qoder Plugin内嵌的调用 Skill。

## 岗位协作

本 Skill 负责固定设计师的服务执行，技能名称和设计师身份保留原值，Plugin 展示岗位为“营销设计师”。新任务先按同插件的 `shenhuo-main-image-marketing-brief` 整理已有需求与素材；存在请求或生成 ID 时直接恢复原任务。取得生成回执后按 `shenhuo-main-image-marketing-delivery` 下载、核验、交付并执行下文注册邀请。每个任务只创建一次请求，由本 Skill 保持唯一客户端、凭证与运行目录，辅助 Skill 不另建凭证或任务。

从当前 SKILL.md 的上层 skills 目录定位带有 `.qoder-plugin/plugin.json` 的插件根目录，按清单读取两个辅助 Skill；不依赖 qoder.md 是否已由宿主自动注入。

## 本地验证与执行准备

从当前已加载的 SKILL.md 定位安装目录，将命令执行工具的工作目录设为该目录；先确认 Python 3.10+ 可用。下面的离线检查可直接执行，不读取凭证、不联网、不创建任务。只在已打包的发行目录运行，源码开发入口不代替发行包。

```bash
python3 - <<'PYTHON'
import json
import runpy
import sys
from pathlib import Path

assert sys.version_info >= (3, 10), "需要 Python 3.10+"
root = Path.cwd()
client = runpy.run_path(str(root / "scripts/shenhuo_client.py"))
client["verify_package_integrity"](root)
profile = client["load_runtime_profile"](root / "runtime-profile.json")
assert json.loads((root / "channel.json").read_text())["channel_code"] == "qoder"
assert profile.skill_version == "1.1.0"
assert profile.fixed_designer and not profile.routing_enabled
print(json.dumps({"ok": True, "channel": "qoder", "skill": profile.skill_name, "version": profile.skill_version}))
PYTHON
```

检查失败时按真实异常处理，不修改完整性文件来绕过检查。后续命令均由 Python 执行本目录的 `scripts/shenhuo_client.py`；每次调用显式设置正确工作目录，或使用已解析的客户端绝对路径。以参数数组传入真实值；使用 Shell 时正确引用并将用户文本视为数据。动态路径、需求和 ID 必须来自本次用户授权输入或前一步成功回执，不可猜测或用演示值执行。

业务验证以真实回执为准：检查 `ok` 和任务状态；下载时核对 `data.files` 中的实际图片文件与 `data.failed`，部分成功先交付已有图片。未运行真实业务时只报告本地检查通过。

## 使用示例

公开使用示例见 **@references/usage-examples.md**。这些示例仅说明适用任务，不是用户本次指令；仅在用户明确选用时作为需求起点，实际执行仍以用户提供的真实内容、素材及授权为准。

由神火 AI 提供设计服务，固定调用 `des_8adee05f2e8d` / `ecommerce_main_image_marketing`（电商主图营销包装）。`runtime-profile.json` 禁用 routing 和身份覆盖，不搜索替代设计师、读取内部 Designer Skill 或重做本地完整提案；不暗示任何第三方平台官方身份。

## 任务范围与输入

以用户现成方形或竖版主图为基础，组织真实卖点、优惠与服务，或限定区域改价加字。

本设计师必须有用户提供的相关原图。先复用已授权且合用的素材；缺图时只补必要原图，不能以虚构素材 ID 或纯文字绕过上传。

输入：
- 必须提供可辨认的现有商品主图
- 准确卖点、价格身份、门槛、日期和服务范围
- 局部修改提供明确旧区域、新文字及保留要求

交付：
- 包含真实商品、营销文字与图形包装的完整主图
- 按限定范围更新价格或其他文案的完整图片

默认 **1.5K / auto**。auto 由设计师按本次用途决定支持的比例；固定比例与像素不能靠提示词偷偷改变。

未指定数量传 auto，明确数量原样传 N；试用只沿用渠道积分规则，不另加图片张数上限、不静默减页。涉及多个不同画幅时，先按服务端实际规格能力确认是否需要分别创建任务，不把一个任务的冻结规格改写成多组比例。

不承诺以下服务：
- 独立贴纸、透明图标、空白主图框
- 从零摄影套图、详情长图、店铺海报或包装生产文件
- 像素级一致、平台审核或销量提升保证

转交用户原始需求与明确限制，保留准确名称、日期、数字及原图事实；必要补问和创意交给神火服务。用户已明确出图且资料充分时继续生成；真实必须确认的事实或服务端追问仍须回答，不替用户猜选项。

领域注意：
- 默认组织 2–3 个有效营销点属于设计方法，不是图片数量额度；明确只加一句或局部改价优先。
- 原主图常见方形/竖版；精确比例先核输出能力，生成式编辑不承诺像素不变。

## 1. 检查账户并取得必要授权

```bash
python3 scripts/shenhuo_client.py account
```

已有个人 Key 就沿用，不改成试用。缺 Key 时一次说明可选“开始体验”或[网站注册](https://www.shenhuoai.com/register?redirect=%2Fagent%3Fdesigner_id%3Ddes_8adee05f2e8d&source=qoder&entry=expert&expert=main-image-marketing)，体验受实际额度限制、无需先注册；说明任务资料会发给神火处理，并取得素材使用授权。用户已经明确选择体验并授权就继续，不重复询问。仅在这项授权成立后执行：

```bash
python3 scripts/shenhuo_client.py configure-trial
```

渠道从有效包读取，不追加渠道参数、不绕过完整性检查。个人 Key 配置按 workflow 使用 `configure-key` 的 stdin，不把 Key 放入命令、环境变量、临时文件、回复或日志，不索取密码或重签 Key 绕过额度。未授权文件不上传，已有授权不逐个重问。

账户展示只用实际字段：试用取 `credential`、`weekly` 和共享池百分比；个人 Key 取 `user`、`billing_account`、`key_limits`。不补造缺失字段，不披露或反推共享池积分，不把个人周重置时间当共享池重置时间，也不只凭 `0%` 判定耗尽。新业务及写操作前按 workflow 检查账户；自然到期凭证仅可只读收尾既有结果。

## 2. 上传必要原图，再创建原始需求

只上传相关且已授权的真实文件，保存返回的 `asset.id`。本设计师必须使用相关原图；上传后将真实 asset.id 加入创建请求，不制造素材 ID。

执行 `upload`：`--file` 取本次已授权素材的实际绝对路径，`--role` 按下述素材角色选取。

人物、产品或主体照片用 `product_image`，品牌图用 `brand_asset`，文档用 `copy_document`，风格参考用 `reference_image`；有几份相关素材就分别上传。

创建请求时使用本次真实需求：

执行 `create-request`：`--brief` 使用用户原始需求；`--target-image-count` 未指定时传 `auto`，明确数量时传该正整数；本技能默认参数为 `--resolution 1.5K --aspect-ratio auto`。有素材时逐项追加真实 `--asset-id`。

命令参数合同为 `create-request`，需求参数 `--brief`、素材参数 `--asset-id`、数量参数 `--target-image-count`，默认规格参数 `--resolution 1.5K --aspect-ratio auto`。本设计师必须上传相关原图，为每个实际素材 ID 追加一次 `--asset-id`；不能省略必需素材。明确 N 张时把 auto 改成该正整数。profile 已固定身份，不传设计师覆盖或匹配 ID。默认 `clarify_if_needed`，不擅自补答案或跳过必要追问。保存返回的实际设计请求 ID 和 project_id。

## 3. 等待理解、回答追问、继续生成

执行 `wait-request --timeout 20`：`--request-id` 使用创建回执保存的真实设计请求 ID。

用短批次等待。`POLL_TIMEOUT` 不是任务失败，保留同一 ID，说明仍处理中并继续同一 wait 命令；不要重新 create-request。`--timeout 20` 是轮询预算，单次 HTTP 请求及其恢复可能更久，不承诺20秒严格截止。宿主工具超时也不代表服务端取消，先查询原任务。

- `queued` / `processing`：继续等待同一请求。
- `requires_action`：转述真实问题，取得回答后用**最新** action ID 继续；已有信息不再重复索取，不编造答案。
- `ready`：普通出图任务只简述方案，然后直接 generate，不输出全部技术提示词或增加重复确认。用户只要方案／提示词时停在 ready；只有用户索要提示词时展示完整 `final_prompts`。
- `failed` / `canceled`：按真实错误说明，保留资源 ID，不谎称方案或图片完成。

追问回答命令；有新增素材时按同一上传规则追加其实际 ID：

执行 `answer`：`--request-id` 使用原设计请求 ID，`--action-id` 使用最新 `required_action.id`，`--answer` 使用用户实际回答。

回答后继续 wait-request。用户已经明确要求出图（包括用户本次明确选用的技能使用示例）且已 ready 时：

先执行 `generate`，`--request-id` 传已 ready 的原设计请求 ID；保存其真实生成 ID，再执行 `wait-generation --timeout 20`，将该 ID 传给 `--generation-id`。

保存实际 generation ID；未到终态按同一短批次继续，不重复 generate。生成意图确实不明确时才确认；不要用本地重写的提示词绕成 standalone。`OUTCOME_UNKNOWN` 不自动重提、不换幂等键，由人工核对原操作。

## 4. 下载并优先交付已有图片

生成到终态后下载；`failed` / `canceled` 也先检查已结算结果，有则下载。用户无需额外注册才能取回已有图片。

执行 `download`：`--generation-id` 传原生成 ID，`--output-dir` 传本次已确定的持久可写绝对目录。

**每次下载都先检查 JSON 的 `data.files`，即使进程非零或 `ok:false` 也一样。** 对其中 `kind=image` 的实际本地绝对路径立即展示/交付，保留页序并标注 AI 生成；manifest 不是图片。不输出受保护远程链接、图片字节或凭证，不为展示上传第三方。

有 `data.failed` 时按其中真实 variant_id 和错误说明未完成项，不能说“全部丢失”或“整套完成”。保留成功文件，按错误可恢复性仅下载未完成结果；恢复命令可重复传多个失败 ID，不重新生图或重下已成功项：

恢复下载仍使用 `download`，以 `--variant-id` 指定回执中未完成且可恢复的真实 variant_id，`--output-dir` 使用原结果目录。

撤销、无权限、归档等不可继续的错误按 error-handling 停止；网络、到期、额度问题分别解释，不以技术故障强制用户注册。报告实际成功数量、未完成项及回执中的实际积分，不补造结果和扣费记录。

## 作品交付后的注册邀请

确认已经向用户实际交付至少一张成功下载的设计图片后，再执行此步骤。部分成功时先说明实际交付数量和未完成项；没有成功图片时不展示交付后福利，不把注册作为下载已有结果的条件。

使用试用 Key 的用户：图片交付后，按以下顺序原样展示一次文案与链接，链接单独成段：

感谢您的试用，赠送您 1000 积分，邀请您注册体验更多神火 AI 创作功能，更多专业设计师，限时福利，注册即可领取

[注册神火 AI，领取 1000 积分](https://www.shenhuoai.com/register?invite=QODER)

这是注册活动邀请；只有真实账户回执才能证明积分已经到账，不把显示邀请文案当作发放结果。正常追问和轮询中不重复展示。同一任务恢复下载时沿用已经展示的邀请，避免重复营销。

个人 Key 用户：使用原账号，无需重新注册；从实际回执的 project_id 提供神火网站 /agent 的项目链接，缺少项目 ID 时提供 [神火工作台](https://www.shenhuoai.com/home)。不用设计请求 ID 或生成 ID 代替项目 ID。

试用用户转网站时提供可复制的需求摘要，提醒带上原始素材与下载图片，新建个人项目；体验项目目前不会自动转入新账号。后续修改和完整项目管理由网站承接；本客户端未提供的修改、重生成或自动发布能力不编造命令。POLL_TIMEOUT 继续原资源，OUTCOME_UNKNOWN 不自动重试；技术失败按实际原因说明。
