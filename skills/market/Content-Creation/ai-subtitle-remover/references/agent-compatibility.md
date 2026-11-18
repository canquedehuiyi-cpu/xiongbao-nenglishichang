# 550W AI去字幕

仅用于用户本人制作、拥有完整处理权利的视频硬字幕擦除。本渠道不提供图片处理、视频水印处理或内容解析功能，不调用相关工具。

## 权利来源核对

提交前请用户说明素材来源：本人拍摄/制作，或权利人授予的完整处理授权。授权素材须确认授权覆盖字幕修改及处理结果的使用；记录用户对来源及授权范围的说明。公开可访问、持有文件或账户登录均不代表拥有处理权利。无法确认、来源不明或涉及去除第三方归属标识时停止。

确认素材权利后，向用户说明视频会上传550W、硬字幕擦除可能改变画面内容并按时长和分辨率扣积分。取得本次处理确认后传入 rightsConfirmed=true 和 confirmProcessing=true，不得自行推定确认。默认整帧；仅使用用户明确提供的完整矩形坐标。

## 接入

优先使用宿主已授权的国内OAuth MCP（https://www.550wai.cn/mcp/cn）。只允许 remove_video_subtitles、get_subtitle_task、list_subtitle_tasks、query_credits；删除本人任务仅在单独确认taskId后调用delete_subtitle_task。远程服务可能提供其他工具，本技能不使用它们；不能传入远程工具schema不存在的参数。

宿主允许Node.js18+及读取用户选择文件时，可用随包API Key入口。账户凭据从https://qzm.550wai.cn/api/取得，存储前说明本地保存位置并获同意，配置使用confirmCredentialStorage=true。每次请求明确params.region="cn"。将单条JSON通过标准输入发送到 node {baseDir}/dist/550w-skill.cjs；处理操作传入confirmProcessing=true和rightsConfirmed=true。本地处理使用workflow及用户指定的绝对filePath；不猜测视频元数据。不允许修改用户项目以取得权限。

OAuth视频上传读取scripts/550w-upload.cjs的inspect/upload契约：mediaType="video"，inspect先读取用户选定文件元数据；prepare_media_upload使用视频类型，依服务回执构建上传输入，upload须confirmProcessing=true。不得把令牌或密钥放命令行、公开文件或日志。云端宿主不能假设可访问本机路径，不能上传时引导https://qzm.550wai.cn/。

## 结果及异常

受理后记录taskId、账户及国内区域，轮询原任务。超时不代表失败，不重新提交收费任务；幂等键仅对相同输入复用。只有服务明确成功且提供结果URL才报告完成；失败如实返回原因和refundStatus，不推定退款。积分不足提供https://qzm.550wai.cn/purchase?tab=speed，不代充值。401及取消授权不切换账户或接入链路。删除任务须单独确认，已扣积分不退。

隐私：https://qzm.550wai.cn/privacy/；条款：https://qzm.550wai.cn/terms/。只发送用户选定视频，不读取无关文件。地区不随语言改变。
