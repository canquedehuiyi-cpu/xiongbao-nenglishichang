---
name: meitu-ai-game
display_name: MeituHub 接入
description: 为游戏资产生成·MeituHub处理 MeituHub 登录、工具发现、任务取回与账户入口。业务制作由本插件对应技能负责。
---

# MeituHub 调用入口

本技能只负责当前插件的 MeituHub 登录、工具发现、生成/编辑/理解调用、任务取回和账户入口。业务规则见当前插件的岗位技能。通过包内启动器调用 meitu-cli，不需要 MCP。

## 启动与认证

从 Qoder 实际加载的本 SKILL.md 位置取得技能目录的绝对路径，不能依赖当前工作目录。macOS/Linux 调用该目录下的 `scripts/meitu.sh`（使用 /bin/sh）；Windows 调用 `scripts/meitu.ps1`（使用 powershell.exe -NoProfile -File）。后文 `meitu` 仅为启动器的简写，不能运行全局 meitu、直接运行 meitu.cjs 或借用其他宿主入口。路径、提示词、URL 都作为独立 argv 安全传入。

1. 先运行 `info`，内部核对区域、客户端配置和运行状态。包固定中国区，不能按语言换区；未配置则停止登录和业务提交。
2. 启动器复用可用 Node；需要时自行下载并校验私有 Node/npm 和 meitu-cli@qoder。业务命令可自动准备运行时，`setup` 可主动准备。不让普通用户手装 Node/npm，不改系统安全设置。运行 `--version` 核对实际 CLI 版本。
3. `auth status --json` 检查真实会话与本包分区和客户端相符；不相符或过期时运行 `auth login --force --no-open-browser --no-poll-progress`，及时展示返回的真实登录链接，用宿主后台执行机制等待用户授权，再检查 status。禁止复制其他渠道会话；只在用户要求退出时 logout。
4. 登录后运行 `tools list --json`，选能力再读取命令 `--help`。工具列表、参数、图片数量、模型枚举均以当前帮助为准，不照抄历史缓存。`AUTH_REQUIRED` 是未登录，不是运行时损坏。

## 能力与调用

已知基础命令：从零生图 `text-to-image`；原图/参考图编辑 `image-edit`；透明抠图 `image-cutout`；超清 `image-superres-enhance`；带排版的海报 `image-poster-generate`；图生视频 `image-to-video`。其它命令先发现，不编造 `ppt-generate`、`photo-culling` 等接口。

`text-generate` 的历史能力资料支持图片参考输入，但这不证明当前 Qoder 账号具有专用选片接口。摄影选片先检查当前工具列表与帮助是否接受图片并可完成视觉理解；可用时向它提交真实照片及逐张观察任务，取得可追溯的文字判断。若不支持、无法读图或只返回泛化文案，停止该阶段，不把本地判断包装成美图结果。

重复业务流程可先检查 `workflow update --json`、`workflow list --json`；匹配后读取 `workflow info` 和该工作流帮助。只执行当前账号可见、已发布的工作流；CLI 不负责创建或发布工作流，不虚构工作流编号。

业务命令用 `--json`；产物使用 `--download-dir` 保存到本次任务的输出目录。多图参数按当前帮助提供，例如复数参数后跟多个独立图片路径。只上传完成请求所需的图片；源文件保持不变。解析真实返回的 ok、code、message、task_id、data.result.urls、downloaded_files。优先交付可打开的本地文件。

长任务已有 task_id 时运行 `task wait` 等待该任务（interval-ms 2000、timeout-ms 600000，附 --json 和 --download-dir），不要重复创建。批量先读 `batch --help` 与业务命令帮助；逐项保存任务状态，无现成批量入口就按单项执行，不能猜批量格式。

## 失败处理

- 参数错：重读帮助，修正后执行。已受理、超时或状态不明：先找回原任务。只有确定未受理的临时服务错误最多重试一次；合规拒绝不重试。
- 认证失败：重新连接本包账号，不索取 Token、AK、SK。
- 余额/积分/权益不足，包括 77110、RIGHTS_LIMIT_EXCEEDED、ORDER_REQUIRED、quota exhausted：停止新提交，不换服务、账号或通道。提示“账户积分为0或不足，想怎么继续？”。已提交任务仍可等待并取回；列清已完成、未完成和未提交项。
- 错误实际带 action.url/action_url 时保留其完整目标，以“MeituHub 账户”文字链接展示。不拼接充值地址，不把配置入口说成服务端错误返回。
- 能力不存在或生成不合格：保留已完成的独立工作，说明缺口，不宣称完整交付。

## 单独索要账户入口

用户只问充值/账户链接时，此分支优先于 info、auth 和工具发现。通过启动器直接运行 `account entry --json`，无需登录或试生成。成功使用返回的展示内容和原始目标，中文使用“打开充值页：”前缀与“MeituHub 账户”链接标签，目标完整沿用返回值；这是 CLI 配置的网站入口，不是登录状态证明。若 CLI_UPDATE_REQUIRED，回复“账户入口功能需要更新，当前暂时无法提供链接。”，不搜索或猜旧地址。其它失败简述实际错误。

## 结果与内部信息

仅保存任务需要的状态、产物路径、能力名和任务 ID；不记录登录 URL、Token、凭证文件、请求认证头。普通回复写结果和下一步，不展示客户端标识、分区路由或内部配置。引用诊断前去除客户端标识和凭证；服务端链接目标原参数保持完整。配置文件不包含 client_secret。素材生成成功、文件下载成功、实际接入、视觉检查和用户认可分别记录。
