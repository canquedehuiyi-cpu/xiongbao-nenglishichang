# 依赖与授权

本 Plugin 未声明 MCP Connector，市场 Connector 依赖为 0。它通过内嵌 Python 客户端使用神火 AI 的公开 HTTPS API；这是外部服务依赖，不是已上架 Connector，也不伪造市场条目。

| Skill | 外部访问 | 资源与用途 |
|---|---|---|
| shenhuo-wechat-follow-card-brief | 无 | 整理用户主动提供的需求和素材路径 |
| shenhuo-wechat-follow-card | 神火 AI HTTPS API | 验证账户、领取用户选择的试用凭证、上传授权素材、创建固定设计师请求、追问与生成 |
| shenhuo-wechat-follow-card-delivery | 复用执行 Skill 客户端 | 查询原任务、下载已结算图片，不创建新任务 |

## 配置与权限

需要 Python 3.10+ 标准库、可访问 `https://www.shenhuoai.com/external/v1` 的网络，以及 Skill 持久运行目录的写权限。个人 Key 只通过 configure-key 的 stdin 配置；渠道体验只在用户明确选择并授权后运行 configure-trial。渠道为 qoder，资格、可用额度与错误以服务端回执为准。

发送的数据是本次需求、用户授权的图片/附件及运行所需任务标识。下载地址仅取可信服务端回执；公开说明不包含 API Key、用户文件或生产配置。凭证保存规则、账户状态与失败恢复见 [执行流程](./skills/shenhuo-wechat-follow-card/references/workflow.md)。

若 Python、网络或目录权限不满足，应报告实际问题并停止相应动作；不自动安装运行环境，不改用其他渠道，不重复领取凭证。QoderWork 的实际脚本执行、目录权限及市场审核仍需在宿主内验证。
