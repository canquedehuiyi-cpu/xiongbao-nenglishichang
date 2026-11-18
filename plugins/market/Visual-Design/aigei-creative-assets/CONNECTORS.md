# 爱给素材连接器

三个技能共享 `aigei-assets`，通过 HTTPS Streamable HTTP 调用 `https://www.aigei.com/mcp`。首次连接时，按 Qoder 的授权提示登录爱给。OAuth 范围为 `mcp.access`，服务依当前用户的授权处理请求。

| 用途 | 工具 |
| --- | --- |
| 找音效和配乐、查文件规格、获取试听或正式音频 | `audio-search`、`audio-detail`、`audio-download` |
| 找背景、图标和图片元素、查规格、获取水印预览图或正式图片 | `image-search`、`image-detail`、`image-preview-download`、`image-download` |
| 找视频镜头、查规格、获取封面或试看、获取正式视频 | `video-search`、`video-detail`、`video-preview-download`、`video-download` |

PPT 技能主要使用图片工具。游戏技能组合音频与图片工具。视频技能按分镜使用视频、音频及图片工具。实际可用项以客户端完成授权后发现的工具为准。

选材请求使用任务中提取的关键词、筛选条件和服务向当前用户返回的素材或文件编号。搜索与详情可返回素材标题、可用预览和文件规格。用户确认获取所选版本后，服务处理对应条目并返回限时链接。作品在用户授权的工作区制作，来源清单记录项目内的使用位置。

首次连接可调用 `audio-search`，参数为 `{"keyword":"雨声","cat":"sound","pageNumber":1}`。成功后可查看音频标题、时长及可用格式。此查询无需获取文件。账号授权与数据使用说明见[隐私协议](https://www.aigei.com/about/partner)和[用户声明](https://www.aigei.com/about/register)。
