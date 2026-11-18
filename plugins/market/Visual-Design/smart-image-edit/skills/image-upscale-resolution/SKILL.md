---
name: "image-upscale-resolution"
description: "按目标分辨率提升图片清晰度，支持当前目录公布的 2K、4K、8K。适合指定输出档位的图片放大。"
version: "1.0.0"
---

# WaveSpeed 超分

按目标分辨率提升图片清晰度，支持当前目录公布的 2K、4K、8K。适合指定输出档位的图片放大。

## 开始前

读取本目录随包的 [连接与渠道规则](./references/channel.md)、[画布流程](./references/canvas.md)、[报价轮询与文件](./references/runtime.md)、[领域方法](./references/method.md) 和 [素材边界](./references/safety.md)。错误恢复见 [工具说明](./references/tools.md)，多图或多步骤见 [批量调度](./references/batch.md)。这些文件都在本 Skill 内，不要求另外安装技能。

主操作为 `upscale_wavespeed`，制作时执行模式为 `api`；每次通过 `get_account` 与 `canvas_list_tools` 核实连接、工具、实时模式、参数和限制。未发布时停止并说明不可用；模式改变时按真实 mode 分流，不强行执行旧路径。只处理用户给出的图片编辑需求，不匹配设计师或发起创作提案。

同一请求先恢复已有画布项目，使用明确的图片及保存版本。上传原始字节并取得真实资产，不把链接当已上传文件。不读取网页草稿或接管编辑租约。

## 素材诊断与参数

确认用户需要的分辨率档位与用途，必填 resolution，当前取 2k、4k、8k。先查实时输入限制、规格与 alpha 能力；当前不保留 alpha，透明背景需先说明并确认。不要把档位理解为宽高都等于固定值，展示实际报价。

上面的数值是本版制作时已核实的参数范围；运行时以 `canvas_list_tools` 返回的 Schema、限制和报价为准。能力变化后不猜参数或固定价格。领域方法内的其他工具用于方法比较；未经用户要求和确认，不能自动串联或另收费重试。

## 执行与交付

对 `upscale_wavespeed` 使用 `canvas_quote(project_id, image_id, revision_id, tool, parameters, idempotency_key)`，展示范围、参数及本次积分。用户明确确认有效报价后才调用 `canvas_run`，传真实 quote_id、稳定幂等键和 user_confirmed=true。先等 15 秒，第一分钟每 10 秒、第二分钟每 15 秒、之后每 20 秒查询同一任务，遵守更长服务退避；直到真实终态再 `canvas_get_result(task_id=...)`。结果未知不换键重做。积分不足只提示并暂停。

核对实际长宽、画面比例与视觉细节；检查新增纹理、锐化光晕、文字扭曲及主体是否变形。没有查看成品时不得声称细节验证通过。

## 示例需求

“把这张插画提升到 4K 档位，保留比例和主要色彩。”

按以上诊断、参数与确认流程处理。本示例是使用说明，不能作为已实测记录。追加操作、变更图片版本或价格时重新确认；只读查看入口不代表用户同意后续付费操作。
