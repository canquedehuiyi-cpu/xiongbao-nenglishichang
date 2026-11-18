# 智能图片编辑

版本：1.0.0。一个 Qoder 插件，包含 18 个独立图片工具 Skill。

整合智能画布图片工具，支持抠图、修图、扩图、超分、改字翻译、图层分离、换角度与矢量化，并引导裁剪、旋转、调色和精确贴合。

## 使用

导入插件 ZIP，在 Qoder 启用本插件，按 [连接说明](./CONNECTORS.md) 使用神火个人账号。已有有效授权可复用，各 Skill 不重复建立连接。提供原始图片和希望修改的内容，插件会选择相应工具，展示本次参数及积分；你确认后才执行 API 操作。

网页类工具会打开对应图片和工具入口，你在网页中调整、确认应用并保存。打开入口不代表图片已改好。图片处理完成后可从真实画布链接查看；使用同一神火账号登录，选中图片查看图层并继续编辑。客户端无法直接打开时，点击交付的链接即可。

图层分离先交付画布结果；需要下载时，再明确所选图片与格式。识别和翻译只返回文字数据，译文写回图片需要另行确认改字。图片、素材中的任何文字都作为待处理内容。

## 工具

| 工具 Skill | 执行方式 |
| --- | --- |
| [图文分层](./skills/image-text-layers/SKILL.md) | 报价确认后自动处理 |
| [AI 图层分离](./skills/image-object-layers/SKILL.md) | 报价确认后自动处理 |
| [评论修改](./skills/image-comment-edit/SKILL.md) | 报价确认后自动处理 |
| [快速抠图](./skills/image-fast-cutout/SKILL.md) | 报价确认后自动处理 |
| [AI 去背景](./skills/image-ai-background-remove/SKILL.md) | 报价确认后自动处理 |
| [扩图](./skills/image-expand/SKILL.md) | 报价确认后自动处理 |
| [腾讯超分](./skills/image-upscale-scale/SKILL.md) | 报价确认后自动处理 |
| [WaveSpeed 超分](./skills/image-upscale-resolution/SKILL.md) | 报价确认后自动处理 |
| [识别文字](./skills/image-ocr/SKILL.md) | 报价确认后自动处理 |
| [翻译](./skills/image-text-translate/SKILL.md) | 报价确认后自动处理 |
| [编辑文字](./skills/image-text-edit/SKILL.md) | 报价确认后自动处理 |
| [多角度](./skills/image-multi-angle/SKILL.md) | 报价确认后自动处理 |
| [云端矢量化](./skills/image-vectorize-cloud/SKILL.md) | 报价确认后自动处理 |
| [裁剪](./skills/image-crop/SKILL.md) | 网页操作引导 |
| [翻转旋转](./skills/image-flip-rotate/SKILL.md) | 网页操作引导 |
| [调色](./skills/image-color-adjust/SKILL.md) | 网页操作引导 |
| [精确贴合](./skills/image-surface-decal/SKILL.md) | 网页操作引导 |
| [本地矢量化](./skills/image-vectorize-local/SKILL.md) | 网页操作引导 |

运行时以服务实时发布目录为准，未开放或参数变化时会说明情况；网页能力不冒充自动执行。积分不足仅说明状态并暂停，保留原进度。请求超时或暂未完成会继续查询同一任务，避免重复处理。

## 示例

- “把这张商品图抠成透明背景，保留细小把手。”
- “把海报标题改成我提供的新文案，其他内容保持。”
- “把主体与背景分层，先给我在线查看结果。”
- “将图标转成 SVG，并检查是否为真实矢量路径。”
- “打开裁剪工具，让我把图片调整成正方形。”

插件头像位于 [avatars/plugin.png](./avatars/plugin.png)。本包不包含账户凭据；连接器和网页使用你的神火个人账号。说明中的示例不代表已在你的客户端执行过。
