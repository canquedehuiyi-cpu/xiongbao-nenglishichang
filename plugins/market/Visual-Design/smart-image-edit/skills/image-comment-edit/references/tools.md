# 新画布工具

所有调用复用已有 `shenhuo-designers` MCP 和个人 OAuth。实际工具前缀以宿主发现结果为准。

| 工具 | 用途 |
| --- | --- |
| canvas_list_tools | 读取实时启用工具、Schema、积分与限制 |
| canvas_create_project / canvas_get_project | 创建或恢复本次同一个画布项目 |
| canvas_import_image | 导入一张本人上传图片，保留独立分组 |
| canvas_quote | 绑定已保存版本与配置的十分钟报价 |
| canvas_run | 用户确认报价后执行一次单图操作 |
| canvas_get_task / canvas_cancel_task | 查询原任务／响应明确取消要求 |
| canvas_get_editor | 浏览器工具定位与简单操作说明，无执行副作用 |
| canvas_export | 用户明确要求下载后，独立导出指定版本 |
| canvas_get_export | 查询已创建的导出任务，不重新生成 |
| canvas_get_result | 取得已有结果及短期下载入口，不创建导出 |

首次 API 能力包括评论修改、快速抠图、AI 去背景、扩图、超分、OCR／翻译／文字修改、图文分层、AI 图层分离、多角度、云端矢量化。裁剪、翻转旋转、调色、曲面贴图、本地矢量化走浏览器引导。实际集合受后台启用与发布控制。

`SOURCE_CHANGED` / `VERSION_CONFLICT`：读取当前已保存版本，重新确认。
`QUOTE_CHANGED`：重新报价，不沿用过期报价。
`IMAGE_LIMIT`：让用户决定是否拆项目。
`IMAGE_BUSY` / `EXPORT_BUSY`：查询原任务。
`INSUFFICIENT_CREDITS`：仅说明积分不足并保留任务记录，适用渠道规则。
`NO_TEXT_LAYERS` / `no_text`：没有识别到可分离文字，不伪造分层结果。
`DOWNLOAD_EXPIRED`：重新取得已有文件链接。
`OUTCOME_UNKNOWN`：等待核对，不重复处理、不自行判失败。
`OAUTH_REAUTHORIZATION_REQUIRED`：在原连接恢复授权，再查询原任务。

网页未保存草稿不属于本次输入。PSD 只支持服务端托管字体和已公布尺寸限制；本机字体请在原编辑设备导出，不以替换字体冒充完整保真。
