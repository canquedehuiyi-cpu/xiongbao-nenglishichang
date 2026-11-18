---
name: superun-create
description: 使用 superun-ai 创建或继续应用，处理需求、风格、研发、质量检查和运营；业务结果由 superun 生成。
---

# superun 云端创作

读取 [云端执行流程](cloud-generation.md)，按当前项目和真实 CLI 状态执行。需要提问、预览和长命令时读取 [宿主工具](host-tools.md)。自然语言新诉求与原交互答案分别处理。

**新建应用走 `chat create`；已有项目的继续或修改走 `chat send <sessionId>`，把用户原话放进 `content`，不重新创建。** 完整参数见 [命令表](commands.md)。

用户提供页面截图、设计稿、品牌素材、HTML 等与需求相关的附件时，宿主在本次 `chat create` 或 `chat send` 调用中一并上传，让 superun 结合素材生成或修改页面。按[命令表的附件规则](commands.md#json-消息输入)取得本地可读文件并逐个传 `--file <path>`；仅在正文提及附件或传文件路径给 `content` 不等于上传。

`chat create` 和 `chat send` 执行后，CLI 会在本地保留 sessionId，判断本轮是新建还是继续时可以参照；它不是强制检查，也不代替本轮 CLI 回执。

当前宿主按阶段直接执行。

用户反馈 superun 平台、CLI 或专家自身的问题时，如实说明当前状态并保留真实错误；此类问题不作为应用需求提交给 `chat create/send`，也不声称已代为提交反馈。
