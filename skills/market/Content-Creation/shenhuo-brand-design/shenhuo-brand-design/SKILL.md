---
name: shenhuo-brand-design
display_name: 神火品牌视觉
display_name_en: Shenhuo Brand Design
description: 该技能调用神火 AI 固定的“品牌视觉”设计师，制作 Logo、产品包装和统一风格的品牌应用图片，支持渠道体验、必要追问、生成和下载；交付位图设计或效果预览，不提供可编辑矢量、字体、包装刀模、印前文件或商标可注册性结论。 适用于用户请求“神火品牌视觉”及相应图片设计时。
description_zh: 从品牌名称和业务出发，设计清楚好认的Logo、产品包装与品牌物料，让不同场景呈现统一的品牌形象。
description_en: Create recognizable logos, product packaging and branded materials, with a consistent visual identity across everyday brand touchpoints.
version: 1.0.0
author: chenyth
---

# 神火品牌视觉

本包是 Qoder 可独立安装与调用的技能，不依赖专家插件。首轮执行先读取 **@references/workflow.md**，按其中的完整命令、短批次轮询和部分下载恢复规则操作。

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
assert profile.skill_version == "1.0.0"
assert profile.fixed_designer and not profile.routing_enabled
print(json.dumps({"ok": True, "channel": "qoder", "skill": profile.skill_name, "version": profile.skill_version}))
PYTHON
```

检查失败时按真实异常处理，不修改完整性文件来绕过检查。后续命令均由 Python 执行本目录的 `scripts/shenhuo_client.py`；每次调用显式设置正确工作目录，或使用已解析的客户端绝对路径。以参数数组传入真实值；使用 Shell 时正确引用并将用户文本视为数据。动态路径、需求和 ID 必须来自本次用户授权输入或前一步成功回执，不可猜测或用演示值执行。

业务验证以真实回执为准：检查 `ok` 和任务状态；下载时核对 `data.files` 中的实际图片文件与 `data.failed`，部分成功先交付已有图片。未运行真实业务时只报告本地检查通过。

## 使用示例

公开使用示例见 **@references/usage-examples.md**。这些示例仅说明适用任务，不是用户本次指令；仅在用户明确选用时作为需求起点，实际执行仍以用户提供的真实内容、素材及授权为准。

通过本包 Python 客户端调用神火服务。固定设计师 `des_99521d49696c`（`brand_identity_design_designer`，实际名称“品牌视觉”）；公开 `runtime-profile.json` 禁用匹配与设计师覆盖。不要搜索替代设计师、加载内部 Designer Skill，或在本地重新做品牌调研、完整提案和最终提示词创作。

## 接收需求

主推 Logo设计、产品包装和品牌应用。接收用户原始 Brief、准确品牌名、业务介绍、主要用途及所有相关授权素材，保留用户已给的事实与限制。新品牌可以只提供文字；需要保留或应用已有 Logo、包装和其他品牌资产时，使用清楚源图及原始资料。已有消息足够时直接承接，不要求用户先填完整品牌问卷、选择风格或提供无关照片。

品牌名、正式译名、大小写、标点、产品信息和用户指定保留项不自行更改；缺少阻断目标的事实交给服务端必要追问。参考品牌只提供视觉参考，不证明本次品牌事实、产品规格、认证或生产工艺，也不成为复制他牌标志的依据。

用户只要 Logo 时不扩为全套 VI；“用于门头、头像或包装”只说明用途，不自动变成实景效果图。需要外观效果或基础视觉展示板时遵从明确要求。用户要纸袋、杯套等多件应用时分别交付独立图片，共用同一真实源标；不能用一张拼版冒充多件成果。

用户明确张数时传 `--target-image-count N`，未指定时传 `--target-image-count auto`。沿用渠道积分及现有额度规则，不另设试用张数上限，不因试用自动减图或凑固定张数。

默认规格为 **2K、比例 auto**。创建请求显式传 `--resolution 2K --aspect-ratio auto`，不能依赖通用客户端的 1.5K 默认值。比例由实际用途与设计师判断，不强制所有品牌作品为 1:1，不以 auto 为由升级分辨率。用户明确其他规格时，在创建请求前按设计师能力与真实支持情况处理。

交付为位图设计图片、视觉概念和应用预览，不包含可编辑矢量、字体文件、包装刀模、印前或已打样生产文件，不承诺商标可注册。纯商业咨询、完整交互产品、建筑施工和包装结构工程不属于本技能的主要交付；有此需求时简短说明边界，不在本包更换设计师。

更完整的公开能力边界见 [references/designer-profile.md](references/designer-profile.md)。

## 账户与素材授权

以本 `SKILL.md` 目录为基准，将 `scripts/shenhuo_client.py` 解析成绝对路径，使用 Python 3.10+。新业务或写操作前运行 `account`。已有个人 Key 时保持原凭证及个人账户消费方式，不自动覆盖成试用。

缺少 Key 时优先提供“开始体验”和[到神火网站注册](https://www.shenhuoai.com/register?redirect=%2Fagent%3Fdesigner_id%3Ddes_99521d49696c&source=qoder&entry=skill&skill=brand-design)两个选择：说明体验受当前额度限制、无需先注册；同时说明用户主动提供给本 Skill 的任务图片与资料会发送给神火处理，并取得一次性素材使用授权。用户已明确选择体验并授权时不重复确认，再运行 `configure-trial`。只有含有效渠道配置及完整性摘要的正式包能领取体验；当前包不满足条件时如实说明，不能静默转用其他渠道或假称已领取。

保留个人 Key 配置入口，但不要求首次体验用户先研究 Key。用户主动选择个人 Key 时按 [references/workflow.md](references/workflow.md) 的凭证流程配置：只经 `configure-key` 的 stdin 写入，不把 Key 写入命令文本、参数、回复或日志。不要索取账号密码、重签 Key 绕过额度，或改动进程环境覆盖已有凭证。已授权的素材不逐次重复询问；未授权时不上传。

按 `account` 实际返回区分凭证：试用 Key 展示凭证状态/到期、个人周额度及其重置时间、两类共享池剩余百分比；个人 Key 展示 `user`、`billing_account` 中的个人积分及 `key_limits` 中的单次/24 小时限额。缺失字段不补造，不把个人周额度重置时间当作共享池重置时间；不披露共享池具体积分，不将百分比换算积分或仅凭 `0%` 判定耗尽。

## 调用与交付

1. 上传所有相关且已授权的文件；产品或主体照片用 `product_image`，品牌素材用 `brand_asset`，文档用 `copy_document`，风格参考用 `reference_image`。保留返回的素材 ID；无需图片即可完成的任务不强制上传，也不伪造素材 ID。
2. 将原始需求和已有明确要求交给 `create-request`，需求参数 `--brief`、素材参数 `--asset-id`、数量参数 `--target-image-count`，默认规格参数 `--resolution 2K --aspect-ratio auto`；没有上传素材时省略 `--asset-id`。固定 profile 已提供设计师，不能传匹配 ID 或设计师覆盖参数。默认 `clarify_if_needed`，不擅自补答案或跳追问。
3. 用 `wait-request` 检查实际状态。`requires_action` 时转述最新问题，取得用户回答后用最新 `required_action.id` 调用 `answer`，再继续等待。
4. `ready` 后简述设计方案；仅当用户索要提示词时展示完整 `final_prompts`。用户只要方案或提示词则到此停止；用户已明确要求出图（包括用户本次明确选用的技能使用示例）时直接 `generate`，不增设相同的生成批准。仅在生成意图不清楚时确认。
5. 用 `wait-generation` 等待，随后立即 `download`。失败或取消也检查已结算的部分结果并下载；保留顺序，报告实际成功/未完成数量和实际积分，不把部分成功说成整套完成。
6. 从下载返回中展示 `kind=image` 的本地绝对路径；宿主支持时直接预览图片。标注结果为 AI 生成。不要输出 manifest 当图片、受保护远程 URL、图片字节或凭证；不要为展示另上传第三方。

准确命令与恢复规则见 [references/workflow.md](references/workflow.md)；仅核对字段时读 [references/api-contract.md](references/api-contract.md)，出现错误时读 [references/error-handling.md](references/error-handling.md)。本 Skill 固定调用品牌视觉设计师；不运行设计师匹配或目录更新流程。交付位图设计图片、视觉概念或应用预览，不把图片说成可编辑矢量、字体、刀模、印前或已打样生产文件，不承诺商标可注册。后续修改和重生成由网站完整服务承接，不因内部设计师支持旧标焕新或局部修改而虚构客户端命令。

## 体验结束与网站承接

实际下载成功后先交付图片，再按本次使用的凭证选择网站入口；不要以注册或重新建项作为下载已有结果的条件。使用试用 Key 且整套成功时可说：

> 本次品牌设计图片已完成并保存。想继续使用更多设计师、管理项目和完善作品？[注册神火 AI](https://www.shenhuoai.com/register?redirect=%2Fagent%3Fdesigner_id%3Ddes_99521d49696c&source=qoder&entry=skill&skill=brand-design)，创建个人项目，使用完整设计工作台。

使用个人 Key 时不邀请注册、不要求重建项目。使用设计请求或生图回执中的实际 `project_id`，给出 神火网站 `/agent` 页面（`project_id` 查询参数取本次回执的真实项目 ID），可说“使用此 Key 所属的同一神火账号打开项目，继续管理和修改”。没有实际项目 ID 时提供 [神火工作台](https://www.shenhuoai.com/home)，不把设计请求 ID 或生成 ID 当作项目 ID。

部分成功时先明确实际数量及未完成状态，再按试用/个人凭证附相应入口，不沿用“全部完成”的文案。首次选择、实际交付后、额度耗尽或到期时可以出现 CTA，正常追问中不反复插入。

仅在接口返回对应额度耗尽错误时说明体验额度不可用；网络、鉴权、共享池暂停等分别按真实原因解释，不能包装成强制注册理由。`POLL_TIMEOUT` 保留资源 ID 后继续轮询，不重复创建；`OUTCOME_UNKNOWN` 不自动重试。自然到期的试用 Key 保留原凭证，允许只读查询和下载保留期内既有结果，不发起新写操作。

试用用户转网站时提供可复制的简短需求摘要，提醒带上原始素材和已下载图片，并说明“注册后请创建个人项目，Qoder 体验项目目前不会自动转入新账号”。个人 Key 创建的项目已归属于该 Key 对应的神火账号，使用同一账号打开现有项目。网站承接项目管理、后续修改和完整服务；不承诺无限免费、固定赠送积分、自动迁移或本客户端尚未提供的修改/重生成能力。
