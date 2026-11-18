---
name: "image-ai-background-remove"
description: "对复杂背景图片进行 AI 去背景和主体提取。适合复杂边缘处理；可能重绘细节，需要与强调保留原像素的快速抠图区分。"
version: "1.0.0"
---

# AI 去背景

对复杂背景图片进行 AI 去背景和主体提取。适合复杂边缘处理；可能重绘细节，需要与强调保留原像素的快速抠图区分。

## 开始前

读取本目录随包的 [连接与渠道规则](./references/channel.md)、[画布流程](./references/canvas.md)、[报价轮询与文件](./references/runtime.md)、[领域方法](./references/method.md) 和 [素材边界](./references/safety.md)。错误恢复见 [工具说明](./references/tools.md)，多图或多步骤见 [批量调度](./references/batch.md)。这些文件都在本 Skill 内，不要求另外安装技能。

主操作为 `remove`，制作时执行模式为 `api`；每次通过 `get_account` 与 `canvas_list_tools` 核实连接、工具、实时模式、参数和限制。未发布时停止并说明不可用；模式改变时按真实 mode 分流，不强行执行旧路径。只处理用户给出的图片编辑需求，不匹配设计师或发起创作提案。

同一请求先恢复已有画布项目，使用明确的图片及保存版本。上传原始字节并取得真实资产，不把链接当已上传文件。不读取网页草稿或接管编辑租约。

## 素材诊断与参数

先说明可能重绘主体细节，确认用户接受。可选 prompt、softness（0–30）、background（transparent/warm/custom）及 color（六位 HEX），当前不支持手绘遮罩参数。不要因快速抠图失败而未经确认自动调用本工具。

上面的数值是本版制作时已核实的参数范围；运行时以 `canvas_list_tools` 返回的 Schema、限制和报价为准。能力变化后不猜参数或固定价格。领域方法内的其他工具用于方法比较；未经用户要求和确认，不能自动串联或另收费重试。

## 执行与交付

对 `remove` 使用 `canvas_quote(project_id, image_id, revision_id, tool, parameters, idempotency_key)`，展示范围、参数及本次积分。用户明确确认有效报价后才调用 `canvas_run`，传真实 quote_id、稳定幂等键和 user_confirmed=true。先等 15 秒，第一分钟每 10 秒、第二分钟每 15 秒、之后每 20 秒查询同一任务，遵守更长服务退避；直到真实终态再 `canvas_get_result(task_id=...)`。结果未知不换键重做。积分不足只提示并暂停。

比较主体结构、文字标志、发丝、透明材质、边缘和阴影；报告重绘或细节变化。需要完全保真的商品标识时不能用合理猜测冒充原图细节。

## 示例需求

“去掉这张复杂背景，尽量保留人物发丝；先说明可能变化的细节和费用。”

按以上诊断、参数与确认流程处理。本示例是使用说明，不能作为已实测记录。追加操作、变更图片版本或价格时重新确认；只读查看入口不代表用户同意后续付费操作。
