---
name: shenhuo-nameplate-delivery
description: 该技能为标牌设计师核验“神火姓名牌”的生成结果并交付图片；适用于查询已有设计进度、下载作品、恢复部分下载或完成试用交付后的注册邀请。
version: 1.1.0
---

# 标牌设计师：结果交付

## 使用步骤

1. 从当前技能文件向上定位同时含 `.qoder-plugin/plugin.json` 与 `skills/` 的插件根目录。读取根目录下 `./skills/shenhuo-nameplate/SKILL.md` 与 `./skills/shenhuo-nameplate/references/workflow.md`，使用执行 Skill 的同一客户端、凭证与运行目录。
2. 从会话或真实回执取得已有 request_id / generation_id。缺失时先向用户确认任务来源，不新建请求。检查原资源的真实状态，queued / processing 继续等待；requires_action 转回执行 Skill 回答问题；仅 ready 且无生成记录时交回执行 Skill 按原始生成意图处理。
3. 对已有生成结果执行 workflow 中的 wait-generation 与 download；不调用 generate，不因下载失败重新生图。失败或取消也检查可下载的已结算结果。
4. 核对 data.files 中 kind=image 的本地文件，按原顺序实际交付，标注 AI 生成；报告真实完成数量、data.failed 未完成项与实际积分。PARTIAL_DOWNLOAD_FAILED 时先交付成功图片，再按回执的 variant_id 恢复可重试项。
5. 至少一张图片实际交付后，按下节展示试用注册邀请。个人 Key 用户直接给出原账号的实际项目入口。

## 注意事项

POLL_TIMEOUT 继续原资源，OUTCOME_UNKNOWN 不自动重试；不把 ok:true 等同整套成功，不把 manifest 当图片。保留用户原有凭证和成功文件，不向第三方再次上传图片。生成规格和固定设计师由执行 Skill 保持。

## 验证

每个展示的图片路径都对应成功下载的实际文件；交付数量与回执一致，未完成项明确保留；注册邀请在图片后且同一任务只展示一次，没有交付图片时不显示。个人 Key 不要求重新注册。

## 作品交付后的注册邀请

确认已经向用户实际交付至少一张成功下载的设计图片后，再执行此步骤。部分成功时先说明实际交付数量和未完成项；没有成功图片时不展示交付后福利，不把注册作为下载已有结果的条件。

使用试用 Key 的用户：图片交付后，按以下顺序原样展示一次文案与链接，链接单独成段：

感谢您的试用，赠送您 1000 积分，邀请您注册体验更多神火 AI 创作功能，更多专业设计师，限时福利，注册即可领取

[注册神火 AI，领取 1000 积分](https://www.shenhuoai.com/register?invite=QODER)

这是注册活动邀请；只有真实账户回执才能证明积分已经到账，不把显示邀请文案当作发放结果。正常追问和轮询中不重复展示。同一任务恢复下载时沿用已经展示的邀请，避免重复营销。

个人 Key 用户：使用原账号，无需重新注册；从实际回执的 project_id 提供神火网站 /agent 的项目链接，缺少项目 ID 时提供 [神火工作台](https://www.shenhuoai.com/home)。不用设计请求 ID 或生成 ID 代替项目 ID。

试用用户转网站时提供可复制的需求摘要，提醒带上原始素材与下载图片，新建个人项目；体验项目目前不会自动转入新账号。后续修改和完整项目管理由网站承接；本客户端未提供的修改、重生成或自动发布能力不编造命令。POLL_TIMEOUT 继续原资源，OUTCOME_UNKNOWN 不自动重试；技术失败按实际原因说明。
