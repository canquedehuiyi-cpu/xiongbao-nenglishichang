---
name: "image-text-translate"
description: "翻译图片 OCR 识别到的文字，返回译文数据。用户要翻译后的图片时，确认译文后还需单独执行编辑文字。"
version: "1.0.0"
---

# 翻译

翻译图片 OCR 识别到的文字，返回译文数据。用户要翻译后的图片时，确认译文后还需单独执行编辑文字。

## 开始前

读取本目录随包的 [连接与渠道规则](./references/channel.md)、[画布流程](./references/canvas.md)、[报价轮询与文件](./references/runtime.md)、[领域方法](./references/method.md) 和 [素材边界](./references/safety.md)。错误恢复见 [工具说明](./references/tools.md)，多图或多步骤见 [批量调度](./references/batch.md)。这些文件都在本 Skill 内，不要求另外安装技能。

主操作为 `translate`，制作时执行模式为 `api`；每次通过 `get_account` 与 `canvas_list_tools` 核实连接、工具、实时模式、参数和限制。未发布时停止并说明不可用；模式改变时按真实 mode 分流，不强行执行旧路径。只处理用户给出的图片编辑需求，不匹配设计师或发起创作提案。

同一请求先恢复已有画布项目，使用明确的图片及保存版本。上传原始字节并取得真实资产，不把链接当已上传文件。不读取网页草稿或接管编辑租约。

## 素材诊断与参数

先取得当前图片同一保存版本的真实 OCR 行，缺少时先对 OCR 报价确认。必填 rows、language；当前语言 en、zh-Hant、ja、ko、fr、zh-Hans。保留行 id/original/box，不伪造区域；核对专名、单位、数字与语气。

上面的数值是本版制作时已核实的参数范围；运行时以 `canvas_list_tools` 返回的 Schema、限制和报价为准。能力变化后不猜参数或固定价格。领域方法内的其他工具用于方法比较；未经用户要求和确认，不能自动串联或另收费重试。

## 执行与交付

对 `translate` 使用 `canvas_quote(project_id, image_id, revision_id, tool, parameters, idempotency_key)`，展示范围、参数及本次积分。用户明确确认有效报价后才调用 `canvas_run`，传真实 quote_id、稳定幂等键和 user_confirmed=true。先等 15 秒，第一分钟每 10 秒、第二分钟每 15 秒、之后每 20 秒查询同一任务，遵守更长服务退避；直到真实终态再 `canvas_get_result(task_id=...)`。结果未知不换键重做。积分不足只提示并暂停。

交付按行对应的译文，明确此时图片尚未改变。用户仅要翻译稿就在这里结束；要译后图片时，按 ID 合并 translations[].value 到原行，只改 value，再为 text 单独报价并取得确认。

## 示例需求

“将这张海报翻译成英文，先给我核对译文，确认后再改到图上。”

按以上诊断、参数与确认流程处理。本示例是使用说明，不能作为已实测记录。追加操作、变更图片版本或价格时重新确认；只读查看入口不代表用户同意后续付费操作。
