---
name: shenhuo-wechat-cover
display_name: 公众号首图
display_name_en: WeChat Article Covers
description: 该技能调用神火 AI 固定的“公众号首图”设计师，依据文章主题、活动信息和真实素材制作独立宽幅首图，支持渠道体验、必要追问、生成和下载；不提供正文排版、次图、完整文章或自动发布，不承诺点击量和平台推荐。 适用于用户请求“公众号首图”及相应图片设计时。
description_zh: 根据文章主题、活动信息和真实素材，设计标题清楚、画面贴题的公众号宽幅首图，让读者快速看懂内容重点。
description_en: Create wide WeChat article covers from your topic, event details, and authentic materials, with clear titles and visuals that communicate
  the key message at a glance.
version: 1.1.0
author: chenyth
---

# 公众号首图

这是本 Qoder Plugin内嵌的调用 Skill。首轮执行先读取 **@references/workflow.md**，按其中的完整命令、短批次轮询和部分下载恢复规则操作。

## 岗位协作

本 Skill 负责固定设计师的服务执行，技能名称和设计师身份保留原值，Plugin 展示岗位为“封面设计师”。新任务先按同插件的 `shenhuo-wechat-cover-brief` 整理已有需求与素材；存在请求或生成 ID 时直接恢复原任务。取得生成回执后按 `shenhuo-wechat-cover-delivery` 下载、核验、交付并执行下文注册邀请。每个任务只创建一次请求，由本 Skill 保持唯一客户端、凭证与运行目录，辅助 Skill 不另建凭证或任务。

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

由神火 AI 提供设计服务，通过本包 Python 客户端调用。固定设计师 `des_73dfd41fc547`（`wechat_primary_cover_designer`，实际名称“公众号首图”）；公开 `runtime-profile.json` 禁用匹配与设计师覆盖。PRD 的 routing 状态不改变本技能的固定绑定。不要搜索替代设计师、加载内部 Designer Skill，或在本地重新执行完整研究、提案和最终提示词创作。不暗示微信官方身份。

## 接收需求

主推文章封面、活动推广和通知公告。接收用户原始 Brief、文章标题、正文或文档、公开文章链接及相关授权的照片、商品图和 Logo，保留所有已给事实与限制。只有文字主题时可用插画或概念场景；需要准确呈现真实人物、商品或场地时才补相应清楚原图。资料充分时直接承接，不要求用户先选择配色、风格或图文位置。

标题可以在不改变原意的前提下提炼；用户明确要求逐字保留时不得擅改。长标题与宽幅画面冲突时先减少装饰和非必要副句，仍无法清楚呈现再由服务端询问是否允许缩短。品牌信息、关键日期和改变优惠含义的条件以真实资料为准，不从模板补造价格、资质、效果、排名或官方背书。

原始公开文章链接随需求交给神火服务按正式规则处理；已有足够正文不要求再读链接。不能承诺所有链接可读，不能因提供 URL 就声称已经读完文章或看过网页图片。登录页、动态内容、PDF、图片型正文或读取失败且影响主题时，只补充必要的可读正文或摘要；非关键参考失败不阻断已有资料能完成的设计。URL 不是上传图片素材，不伪造素材 ID。

交付独立宽幅首图，多张需求中的每张都对应一个独立主题的完整首图，不自动增加次图、目录、总结、长图或九宫格，也不用首图加次图拼版冒充一张首图。用户明确张数传 `--target-image-count N`，未指定传 `--target-image-count auto`；试用只沿用渠道积分，不增加张数上限、不静默减图，内容不足的判断和沟通由神火设计师处理。

默认创建参数显式使用 `--resolution 1.5K --aspect-ratio custom`。当前设计师的服务端默认宽高为 **2256×960（准确 2.35:1）**，custom 请求沿用服务端当时默认尺寸；本客户端不永久锁定这组像素。不能用 auto、21:9 或把 2.35:1 当作 CLI 枚举代替 custom，也不传不存在的 width / height 参数。精确尺寸以当次任务冻结规格及实际下载文件为准，不能仅凭公开 final_prompts 的 resolution/aspect_ratio 字段宣布已核实像素。用户另有精确要求时在创建前核对支持情况，不用提示词改变冻结参数。

交付目标是文章入口，不包含次图、正文排版、完整文章写作、二维码名片、视频、印刷制版或后台自动发文。宽图不保证任意裁成正方形后保留全部标题；需要独立方形次图属于另一设计任务，发布者应在实际微信入口检查裁切。不能以首图加次图的展示模板代替实际平台预览。

更完整的公开能力边界见 [references/designer-profile.md](references/designer-profile.md)。

## 账户与素材授权

以本 `SKILL.md` 目录为基准，将 `scripts/shenhuo_client.py` 解析成绝对路径，使用 Python 3.10+。新业务或写操作前运行 `account`。已有个人 Key 时保持原凭证及个人账户消费方式，不自动覆盖成试用。

缺少 Key 时优先提供“开始体验”和[到神火网站注册](https://www.shenhuoai.com/register?redirect=%2Fagent%3Fdesigner_id%3Ddes_73dfd41fc547&source=qoder&entry=expert&expert=wechat-cover)两个选择：说明体验受当前额度限制、无需先注册；同时说明用户主动提供给本 Skill 的任务图片与资料会发送给神火处理，并取得一次性素材使用授权。用户已明确选择体验并授权时不重复确认，再运行 `configure-trial`。只有含有效渠道配置及完整性摘要的正式包能领取体验；当前包不满足条件时如实说明，不能静默转用其他渠道或假称已领取。

保留个人 Key 配置入口，但不要求首次体验用户先研究 Key。用户主动选择个人 Key 时按 [references/workflow.md](references/workflow.md) 的凭证流程配置：只经 `configure-key` 的 stdin 写入，不把 Key 写入命令文本、参数、回复或日志。不要索取账号密码、重签 Key 绕过额度，或改动进程环境覆盖已有凭证。已授权的素材不逐次重复询问；未授权时不上传。

按 `account` 实际返回区分凭证：试用 Key 展示凭证状态/到期、个人周额度及其重置时间、两类共享池剩余百分比；个人 Key 展示 `user`、`billing_account` 中的个人积分及 `key_limits` 中的单次/24 小时限额。缺失字段不补造，不把个人周额度重置时间当作共享池重置时间；不披露共享池具体积分，不将百分比换算积分或仅凭 `0%` 判定耗尽。

## 调用与交付

1. 上传所有相关且已授权的文件；产品或主体照片用 `product_image`，品牌素材用 `brand_asset`，文档用 `copy_document`，风格参考用 `reference_image`。保留返回的素材 ID；无需图片即可完成的任务不强制上传，也不伪造素材 ID。
2. 将原始需求和已有明确要求交给 `create-request`，需求参数 `--brief`、素材参数 `--asset-id`、数量参数 `--target-image-count`，默认规格参数 `--resolution 1.5K --aspect-ratio custom`；没有上传素材时省略 `--asset-id`。固定 profile 已提供设计师，不能传匹配 ID 或设计师覆盖参数。默认 `clarify_if_needed`，不擅自补答案或跳追问。
3. 用 `wait-request` 检查实际状态。`requires_action` 时转述最新问题，取得用户回答后用最新 `required_action.id` 调用 `answer`，再继续等待。
4. `ready` 后简述设计方案；仅当用户索要提示词时展示完整 `final_prompts`。用户只要方案或提示词则到此停止；用户已明确要求出图（包括用户本次明确选用的技能使用示例）时直接 `generate`，不增设相同的生成批准。仅在生成意图不清楚时确认。
5. 用 `wait-generation` 等待，随后立即 `download`。失败或取消也检查已结算的部分结果并下载；保留顺序，报告实际成功/未完成数量和实际积分，不把部分成功说成整套完成。
6. 从下载返回中展示 `kind=image` 的本地绝对路径；宿主支持时直接预览图片。标注结果为 AI 生成。不要输出 manifest 当图片、受保护远程 URL、图片字节或凭证；不要为展示另上传第三方。

准确命令与恢复规则见 [references/workflow.md](references/workflow.md)；仅核对字段时读 [references/api-contract.md](references/api-contract.md)，出现错误时读 [references/error-handling.md](references/error-handling.md)。本 Skill 固定调用公众号首图设计师；不运行设计师匹配或目录更新流程。交付可下载的独立宽幅首图，不提供正文、次图或自动发布，不模拟微信平台界面，不承诺点击量、推荐或审核结果。后续修改和重生成由网站完整服务承接，不因内部设计师有修改方法而虚构客户端命令。

## 作品交付后的注册邀请

确认已经向用户实际交付至少一张成功下载的设计图片后，再执行此步骤。部分成功时先说明实际交付数量和未完成项；没有成功图片时不展示交付后福利，不把注册作为下载已有结果的条件。

使用试用 Key 的用户：图片交付后，按以下顺序原样展示一次文案与链接，链接单独成段：

感谢您的试用，赠送您 1000 积分，邀请您注册体验更多神火 AI 创作功能，更多专业设计师，限时福利，注册即可领取

[注册神火 AI，领取 1000 积分](https://www.shenhuoai.com/register?invite=QODER)

这是注册活动邀请；只有真实账户回执才能证明积分已经到账，不把显示邀请文案当作发放结果。正常追问和轮询中不重复展示。同一任务恢复下载时沿用已经展示的邀请，避免重复营销。

个人 Key 用户：使用原账号，无需重新注册；从实际回执的 project_id 提供神火网站 /agent 的项目链接，缺少项目 ID 时提供 [神火工作台](https://www.shenhuoai.com/home)。不用设计请求 ID 或生成 ID 代替项目 ID。

试用用户转网站时提供可复制的需求摘要，提醒带上原始素材与下载图片，新建个人项目；体验项目目前不会自动转入新账号。后续修改和完整项目管理由网站承接；本客户端未提供的修改、重生成或自动发布能力不编造命令。POLL_TIMEOUT 继续原资源，OUTCOME_UNKNOWN 不自动重试；技术失败按实际原因说明。
