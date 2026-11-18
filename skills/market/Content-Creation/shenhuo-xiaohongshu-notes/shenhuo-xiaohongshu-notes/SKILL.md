---
name: shenhuo-xiaohongshu-notes
display_name: 小红书图文笔记
display_name_en: Xiaohongshu Visual Notes
description: 该技能调用神火 AI 固定的“小红书笔记”设计师，把生活分享、知识方法和真实商品资料做成小红书封面与正文图片，支持单张内页、连续图文、渠道体验、必要追问、生成和下载；不自动发帖，不模拟平台界面，不虚构体验或承诺流量。 适用于用户请求“小红书图文笔记”及相应图片设计时。
description_zh: 把分享内容、知识方法和真实商品资料，整理成手机上清楚好读的小红书图文笔记，支持封面与连续内页设计。
description_en: Turn everyday stories, practical knowledge and real product information into readable Xiaohongshu visual notes, from covers to connected
  content pages.
version: 1.0.0
author: chenyth
---

# 小红书图文笔记

本包是 Qoder 可独立安装与调用的技能，不依赖专家插件。

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

由神火 AI 提供设计服务，固定调用 `des_bcb5653e7316` / `xiaohongshu_notes_designer`（小红书笔记）。`runtime-profile.json` 禁用 routing 和身份覆盖，不搜索替代设计师、读取内部 Designer Skill 或重做本地完整提案。不暗示小红书官方身份。

## 任务范围与输入

主推生活分享、知识干货和产品介绍，接收用户原始 Brief、文字、文档、照片及真实商品或服务资料。知识、步骤和比较类内容没有图片也可开始；要保持真实人物、地点或商品时才补对应清楚原图。已有信息足够时直接提交，不先问配色、布局、实拍还是插画，也不要求重新填写设计问卷。

支持封面与连续内页、单张正文、问答、步骤、清单、比较及图文说明。只要内页不强制增加封面或总结页，每页解决不同问题。未指定数量传 auto，明确数量原样传 N；渠道试用不另限张数、不静默减页，内容不足由神火设计师判断和沟通。默认 **1.5K / 3:4**，当前对应1344×1792；这是设计师定位，不是平台统一强制尺寸。用户要求其他规格时先核对支持情况，不用提示词更改冻结参数。

保留原始事实与限制，不编造亲测、旅行经历、成绩、销量、功效或收益；名称、日期、价格、用量及条件以真实资料为准。必要缺口由服务端追问。专业内容只整理有依据的资料，不作个体诊断或决策。交付平面图片，不自动发帖，不模拟平台界面，不承诺视频、印刷长册、完整电商详情、可编辑源文件、流量或推荐。

## 1. 检查账户并取得必要授权

```bash
python3 scripts/shenhuo_client.py account
```

已有个人 Key 就沿用，不改成试用。缺 Key 时一次说明可选“开始体验”或[网站注册](https://www.shenhuoai.com/register?redirect=%2Fagent%3Fdesigner_id%3Ddes_bcb5653e7316&source=qoder&entry=skill&skill=xiaohongshu-notes)，体验受实际额度限制、无需先注册；说明任务资料会发给神火处理，并取得素材使用授权。用户已经明确选择体验并授权就继续，不重复询问。仅在这项授权成立后执行：

```bash
python3 scripts/shenhuo_client.py configure-trial
```

渠道从有效包读取，不追加渠道参数、不绕过完整性检查。个人 Key 配置按 workflow 使用 `configure-key` 的 stdin，不把 Key 放入命令、环境变量、临时文件、回复或日志，不索取密码或重签 Key 绕过额度。未授权文件不上传，已有授权不逐个重问。

账户展示只用实际字段：试用取 `credential`、`weekly` 和共享池百分比；个人 Key 取 `user`、`billing_account`、`key_limits`。不补造缺失字段，不披露或反推共享池积分，不把个人周重置时间当共享池重置时间，也不只凭 `0%` 判定耗尽。新业务及写操作前按 workflow 检查账户；自然到期凭证仅可只读收尾既有结果。

## 2. 可选上传，再创建原始需求

只上传相关且已授权的真实文件，保存返回的 `asset.id`。没有文件的文字任务跳过本步，不制造素材 ID。

执行 `upload`：`--file` 取本次已授权素材的实际绝对路径，`--role` 按下述素材角色选取。

人物、产品或主体照片用 `product_image`，品牌图用 `brand_asset`，文档用 `copy_document`，风格参考用 `reference_image`；有几份相关素材就分别上传。

创建请求时使用本次真实需求：

执行 `create-request`：`--brief` 使用用户原始需求；`--target-image-count` 未指定时传 `auto`，明确数量时传该正整数；本技能默认参数为 `--resolution 1.5K --aspect-ratio 3:4`。有素材时逐项追加真实 `--asset-id`。

命令参数合同为 `create-request`，需求参数 `--brief`、素材参数 `--asset-id`、数量参数 `--target-image-count`，默认规格参数 `--resolution 1.5K --aspect-ratio 3:4`。有已上传素材时为每个实际 ID 追加一次 `--asset-id`；无素材省略。明确 N 张时把 auto 改成该正整数。profile 已固定身份，不传设计师覆盖或匹配 ID。默认 `clarify_if_needed`，不擅自补答案或跳过必要追问。保存返回的实际设计请求 ID 和 project_id。

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

## 5. 网站承接

先交付成功图片，之后按本次凭证附简短入口，不在正常追问中反复营销：

- 试用 Key：整套完成时可说“本次笔记图片已完成并保存。想继续管理作品、调整内容，或使用更多设计师？[注册神火 AI](https://www.shenhuoai.com/register?redirect=%2Fagent%3Fdesigner_id%3Ddes_bcb5653e7316&source=qoder&entry=skill&skill=xiaohongshu-notes)，创建个人项目，使用完整设计工作台。”部分成功先说明实际状态。转网站时提供简短需求摘要，提醒带原始素材和下载图片，并说明体验项目不会自动迁入新账号，不承诺固定赠送或无限免费。
- 个人 Key：不邀请重新注册或重建。使用回执实际 `project_id`，提供 神火网站 `/agent` 页面（`project_id` 查询参数取本次回执的真实项目 ID），提醒用该 Key 所属同一账号；缺 project_id 时给[工作台](https://www.shenhuoai.com/home)。不得使用 request/generation ID 冒充。

网站承接后续修改和完整服务；不编造本客户端未提供的修改／重生成命令。渠道额度耗尽或到期按真实回执说明，并可给网站入口；成功下载始终不以注册为条件。
