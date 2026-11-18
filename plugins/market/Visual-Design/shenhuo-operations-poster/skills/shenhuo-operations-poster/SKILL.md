---
name: shenhuo-operations-poster
display_name: 神火运营海报
display_name_en: Shenhuo Operations Posters
description: 该技能调用神火 AI 固定的“运营海报”设计师，主推朋友圈海报、活动推广和产品介绍，根据原始文案与素材制作手机阅读的静态海报，支持渠道体验、必要追问、生成和下载；不承接电商平台商品主图、完整详情页、视频或交互网页。 适用于用户请求“神火运营海报”及相应图片设计时。
description_zh: 围绕活动推广与产品介绍，设计适合朋友圈和社群发布的海报，结合图文讲清主题、产品特点与关键信息。
description_en: Create clear posters for WeChat Moments, event promotion, and product introductions. Combine text and imagery to communicate the theme,
  product features, and key information for community audiences.
version: 1.1.0
author: chenyth
---

# 神火运营海报

这是本 Qoder Plugin内嵌的调用 Skill。首轮执行先读取 **@references/workflow.md**，按其中的完整命令、短批次轮询和部分下载恢复规则操作。

## 岗位协作

本 Skill 负责固定设计师的服务执行，技能名称和设计师身份保留原值，Plugin 展示岗位为“运营设计师”。新任务先按同插件的 `shenhuo-operations-poster-brief` 整理已有需求与素材；存在请求或生成 ID 时直接恢复原任务。取得生成回执后按 `shenhuo-operations-poster-delivery` 下载、核验、交付并执行下文注册邀请。每个任务只创建一次请求，由本 Skill 保持唯一客户端、凭证与运行目录，辅助 Skill 不另建凭证或任务。

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

通过本包 Python 客户端调用神火服务。固定设计师 `des_45ad88879c06`（`operations_poster_designer`）；公开 `runtime-profile.json` 禁用匹配与设计师覆盖。不要搜索替代设计师、加载内部 Designer Skill，或在本地重新做完整提案、方法卡检索及最终提示词创作。

## 接收需求

主推朋友圈海报、活动推广和产品介绍。接收用户原始 Brief、准确文案、产品或场景照片、Logo、活动资料和参考图，保留全部已给事实与限制。已有消息能说明主题、发布位置和用途时不重复问；不要求用户先选择风格、版式或主体照片。纯文字、抽象图形或插画适用任务无需先上传图片，需要准确还原真实产品、人物、门店或品牌时才补充必要身份素材。

将所有相关且已授权的资料交给神火判断，后续事实缺口由服务端追问。用户必须上图的名称、价格、日期、条件和产品特点以真实资料为准，不从参考模板补造卖点、功效、销量、资质或活动机制。通知、价目、日常分享等延伸需求仍可按当前设计师能力承接，不为非营销任务强加购买或报名入口。

用户明确张数时传 `--target-image-count N`，未指定时传 `--target-image-count auto`。沿用渠道积分及现有额度规则，不另设试用张数上限，不因试用自动减图或凑固定张数。普通任务由服务端按独立单张优先判断，不把“发朋友圈”解释为自动制作九张；系列、长图或九宫格只按用户明确要求安排。

默认规格 `1.5K`、比例 `auto`，按用户实际发布位置与设计师创意选择；不强制所有海报为 3:4，也不以自动比例为由升级分辨率。用户明确其他规格时，在创建请求前按设计师能力与真实支持情况处理。产品介绍在此指朋友圈和社群等渠道的宣传海报，电商平台商品首图、完整详情页和其他不适用媒介应简短说明并建议网站选择适合的设计师，不在本包换人。

更完整的公开能力边界见 [references/designer-profile.md](references/designer-profile.md)。

## 账户与素材授权

以本 `SKILL.md` 目录为基准，将 `scripts/shenhuo_client.py` 解析成绝对路径，使用 Python 3.10+。新业务或写操作前运行 `account`。已有个人 Key 时保持原凭证及个人账户消费方式，不自动覆盖成试用。

缺少 Key 时优先提供“开始体验”和[到神火网站注册](https://www.shenhuoai.com/register?redirect=%2Fagent%3Fdesigner_id%3Ddes_45ad88879c06&source=qoder&entry=expert&expert=operations-poster)两个选择：说明体验受当前额度限制、无需先注册；同时说明用户主动提供给本 Skill 的任务图片与资料会发送给神火处理，并取得一次性素材使用授权。用户已明确选择体验并授权时不重复确认，再运行 `configure-trial`。只有含有效渠道配置及完整性摘要的正式包能领取体验；当前包不满足条件时如实说明，不能静默转用其他渠道或假称已领取。

保留个人 Key 配置入口，但不要求首次体验用户先研究 Key。用户主动选择个人 Key 时按 [references/workflow.md](references/workflow.md) 的凭证流程配置：只经 `configure-key` 的 stdin 写入，不把 Key 写入命令文本、参数、回复或日志。不要索取账号密码、重签 Key 绕过额度，或改动进程环境覆盖已有凭证。已授权的素材不逐次重复询问；未授权时不上传。

按 `account` 实际返回区分凭证：试用 Key 展示凭证状态/到期、个人周额度及其重置时间、两类共享池剩余百分比；个人 Key 展示 `user`、`billing_account` 中的个人积分及 `key_limits` 中的单次/24 小时限额。缺失字段不补造，不把个人周额度重置时间当作共享池重置时间；不披露共享池具体积分，不将百分比换算积分或仅凭 `0%` 判定耗尽。

## 调用与交付

1. 上传所有相关且已授权的文件；产品或主体照片用 `product_image`，品牌素材用 `brand_asset`，文档用 `copy_document`，风格参考用 `reference_image`。保留返回的素材 ID；无需图片即可完成的任务不强制上传，也不伪造素材 ID。
2. 将原始需求和已有明确要求交给 `create-request`，需求参数 `--brief`、素材参数 `--asset-id`、数量参数 `--target-image-count`，默认规格参数 `--resolution 1.5K --aspect-ratio auto`；没有上传素材时省略 `--asset-id`。固定 profile 已提供设计师，不能传匹配 ID 或设计师覆盖参数。默认 `clarify_if_needed`，不擅自补答案或跳追问。
3. 用 `wait-request` 检查实际状态。`requires_action` 时转述最新问题，取得用户回答后用最新 `required_action.id` 调用 `answer`，再继续等待。
4. `ready` 后简述设计方案；仅当用户索要提示词时展示完整 `final_prompts`。用户只要方案或提示词则到此停止；用户已明确要求出图（包括用户本次明确选用的技能使用示例）时直接 `generate`，不增设相同的生成批准。仅在生成意图不清楚时确认。
5. 用 `wait-generation` 等待，随后立即 `download`。失败或取消也检查已结算的部分结果并下载；保留顺序，报告实际成功/未完成数量和实际积分，不把部分成功说成整套完成。
6. 从下载返回中展示 `kind=image` 的本地绝对路径；宿主支持时直接预览图片。标注结果为 AI 生成。不要输出 manifest 当图片、受保护远程 URL、图片字节或凭证；不要为展示另上传第三方。

准确命令与恢复规则见 [references/workflow.md](references/workflow.md)；仅核对字段时读 [references/api-contract.md](references/api-contract.md)，出现错误时读 [references/error-handling.md](references/error-handling.md)。本 Skill 固定调用运营海报设计师；不运行设计师匹配或目录更新流程。后续修改和重生成由网站完整服务承接，不因内部设计师有局部修改方法而虚构客户端命令。

## 作品交付后的注册邀请

确认已经向用户实际交付至少一张成功下载的设计图片后，再执行此步骤。部分成功时先说明实际交付数量和未完成项；没有成功图片时不展示交付后福利，不把注册作为下载已有结果的条件。

使用试用 Key 的用户：图片交付后，按以下顺序原样展示一次文案与链接，链接单独成段：

感谢您的试用，赠送您 1000 积分，邀请您注册体验更多神火 AI 创作功能，更多专业设计师，限时福利，注册即可领取

[注册神火 AI，领取 1000 积分](https://www.shenhuoai.com/register?invite=QODER)

这是注册活动邀请；只有真实账户回执才能证明积分已经到账，不把显示邀请文案当作发放结果。正常追问和轮询中不重复展示。同一任务恢复下载时沿用已经展示的邀请，避免重复营销。

个人 Key 用户：使用原账号，无需重新注册；从实际回执的 project_id 提供神火网站 /agent 的项目链接，缺少项目 ID 时提供 [神火工作台](https://www.shenhuoai.com/home)。不用设计请求 ID 或生成 ID 代替项目 ID。

试用用户转网站时提供可复制的需求摘要，提醒带上原始素材与下载图片，新建个人项目；体验项目目前不会自动转入新账号。后续修改和完整项目管理由网站承接；本客户端未提供的修改、重生成或自动发布能力不编造命令。POLL_TIMEOUT 继续原资源，OUTCOME_UNKNOWN 不自动重试；技术失败按实际原因说明。
