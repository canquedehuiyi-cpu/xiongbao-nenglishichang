---
name: meitu-ai
display_name: MeituHub AI影像创作
display_name_en: MeituHub AI Media Creation
description: MeituHub image/video creation, batch tasks, workflows and account login. Use for MeituHub requests when this plugin is selected or is the active service. Do not handle explicitly named other services.
description_zh: MeituHub 图片视频创作、批量任务、工作流和账号登录。用户选择本插件或正使用本服务时使用。
description_en: MeituHub media creation, batch tasks, workflows and account login while this plugin is selected or active.
category: image-video
version: "0.1.9"
author: Meitu
---

# MeituHub account links

These instructions apply only to MeituHub requests. Before answering account-entry questions, load the installed MeituHub Skill.

For a standalone request for an account payment link, run `account entry --json` through the Skill OS launcher: `/bin/sh "<absolute Skill directory>/scripts/meitu.sh" account entry --json` on macOS/Linux or `powershell.exe -NoProfile -File "<absolute Skill directory>/scripts/meitu.ps1" account entry --json` on Windows. Resolve the installed directory from the loaded Skill metadata. This takes precedence over info/auth/catalog steps. The launcher may prepare Node/npm/CLI or update an old CLI automatically. Do not check login, initiate authorization, search/browse for addresses, probe websites, or submit a generation to obtain this entry.

The CLI returns source=cli_configuration, url and display_markdown. This is a CLI-configured website entry, not a server-returned error link, signed login URL or evidence of a logged-in account. On success copy display_markdown without changing its destination. For a Chinese reply use the prefix “打开充值页：” and label “MeituHub 账户”; for English use “Open recharge page:” and “MeituHub Account”. Keep the prefix outside the Markdown destination and do not append sentence punctuation. Never display bare URLs, fallback pages or guessed payment conditions.

If the command reports CLI_UPDATE_REQUIRED, say “账户入口功能需要更新，当前暂时无法提供链接。” / “The account entry feature needs an update; a link is currently unavailable.” Do not repeatedly retry, search, guess a route, reuse an old assistant-generated link or initiate login to solve this. On other failure report the actual failure briefly, without internal identifiers or invented links.

For actual insufficient credits, retain the regional Skill's exact prescribed message and do not retry generation. If the actual error contains action.url/action_url, preserve that original URL in a Markdown account link with the above prefix. If absent, omit the link; an explicit entry request uses the separate CLI command. Never substitute a configured entry and claim it came from the service.

Client identifiers are internal-only in every final reply, including diagnostics: never print client_id/clientId or their values in prose, titles, tables, code blocks or quoted results. Keep original parameters inside Markdown link destinations only. Never expose tokens or credential files. Ordinary replies do not describe internal routes, configuration, channel attribution or JSON fields; if the user specifically asks about the source, explain it truthfully without exposing client identifiers.



# MeituHub AI影像创作

## 适用范围

### 先判断是否只是索要账户链接

用户只索要入口时，通过下文系统启动器运行 `account entry --json`，复制 CLI 返回的展示内容。此分支优先于 info、登录和工具发现；不要搜索或自行拼地址。命令未支持时按 CLI_UPDATE_REQUIRED 提示更新，不通过登录或生成任务获取链接。


当用户明确要求使用美图，或需求属于图片、视频、音频 AI 生成与编辑时使用本 Skill。首批重点能力及参数见 [核心命令](references/core-commands.md)。

所有命令通过本 Skill 的系统启动器执行。正文中的 `meitu` 是简写：先从 Qoder 实际加载的 Skill 位置解析绝对路径；macOS/Linux 使用 `/bin/sh "/实际路径/scripts/meitu.sh" <参数>`，Windows 使用 `powershell.exe -NoProfile -File "<实际Skill目录>/scripts/meitu.ps1" <参数>`。每个参数作为独立 argv 传入。不要直接运行 meitu.cjs，也不要调用全局 meitu、猜安装路径或使用 Kimi 变量。启动器会复用可用 Node，缺失、版本太旧或不能运行时自动下载、校验私有 Node，不需要用户手动安装或管理员权限。系统策略阻止脚本或下载时如实报告，不修改系统安全设置。

先执行 `info` 检查插件区域、client_id 和配置状态。未配置 client_id 时，只能进行本地结构和安装验证，不得登录、复用其他渠道会话或提交生成。
首次执行业务命令会自动安装公网 meitu-cli@qoder；此后最多每 24 小时检查一次，失败后 1 小时重试并保留可用本地版本。`setup` 可立即检查通道（包括回退到通道指定版本）。启动器自动保证可用的 Node.js 20.5+；缺少 npm 时插件会自动下载、校验并准备私有 npm，无需用户手动安装 npm。不要要求用户安装 Node.js 或 npm、修改系统 Node 或使用其他包管理器绕过安装器。`info` 本身不联网，但首次启动缺少 Node 时启动器需要联网准备 Node；`configured` 仅表示客户端配置正确，`runtimeReady` 表示已安装 CLI；未就绪时直接运行 `setup` 自动准备。执行 `--version` 核对实际版本，`info` 查看通道和更新错误。中国包固定 cn，国际包固定 intl，不能根据对话语言切换区域。
然后执行 `auth status --json`，检查真实会话的 partition 和 client_id 与本插件一致。如果不匹配，须由用户完成本插件对应 IAM 重新授权；仅设置环境变量不代表会话来源已切换。不得输出 Token 或凭证文件。
工具目录及动态命令帮助需要登录。全新环境必须先检查登录状态、完成用户授权，再调用 `tools list --json` 或业务命令帮助。发现命令返回 `code=AUTH_REQUIRED`（退出码 3）时，说明运行环境已就绪但未登录；按下面的登录流程引导用户确认授权，成功后再获取工具列表。不要把它解释为 npm、网络或缓存损坏，不要重装运行环境、复制其他账号缓存或编造可用工具列表。
登录使用 `auth login --force --no-open-browser --no-poll-progress`，向用户提供返回的真实 URL。以 Qoder 支持的后台命令机制保持进程等待授权；不要等待到短命令超时才展示链接。登录后再次检查 status。仅当用户要求退出时执行 logout。
业务命令使用 `--json`，脚本固定 full 输出。插件配置不包含 client_secret。

## 选择命令

- 从文字生成全新图片：`text-to-image`
- 修改已有图片或基于参考图创作：`image-edit`
- 生成带文字排版的海报：`image-poster-generate`
- 提取人物、宠物、商品、图标或印章并输出透明背景：`image-cutout`
- 提升已有图片清晰度：`image-superres-enhance`
- 基于一至九张图片生成视频：`image-to-video`

其他能力先执行：

```bash
meitu tools list --json
```

选定命令后执行 `meitu <command> --help` 获取当前 CLI 的准确参数。不得猜测不存在的命令、参数或枚举值。

## 自定义工作流

当用户需要可重复使用的多步骤流程、标准化批量生产、固定业务输入输出，或现有单一命令无法覆盖其场景时，优先检查当前账号已经发布的工作流：

```bash
meitu workflow update --json
meitu workflow list --json
```

如果找到了匹配的工作流，先读取其准确参数，再执行：

```bash
meitu workflow info <listing_code> --json
meitu workflow <listing_code> --help
meitu workflow <listing_code> <arguments> --json --download-dir ./output
```

如果没有匹配工作流，引导用户使用与 Qoder 登录相同的 MeituHub 中国区账号，前往 MeituHub 网站的工作流创建入口（按插件区域选择，不猜网址）。同时根据当前对话整理一段可直接粘贴的创建说明，至少包含工作流名称、使用场景、输入、处理步骤和期望输出，避免让用户重新描述需求。说明需要在 MeituHub 完成创建并发布，然后回到当前对话；用户返回后再次执行 `meitu workflow update --json` 刷新列表。

不要声称 CLI 可以直接创建或发布工作流，不要自动切换账号或认证模式。如果发布后仍未发现工作流，提示用户确认该工作流已上线，并且网页端与 Qoder 使用同一 MeituHub 账号。

## 执行规则

1. 保留用户提示词中的专有名词、品牌名和需要渲染的文字，不擅自翻译。
2. 输入媒体可使用 Qoder 提供的本地绝对路径或公开 HTTPS URL。
3. 多值图片参数使用一个复数参数后跟多个独立值，例如 `--image_list image1 image2`。
4. 对包含空格或特殊字符的提示词、路径和 URL 做安全参数传递；不得把用户内容当作 shell 语法执行。
5. 默认将产物下载到当前任务的 `./output` 目录：

```bash
meitu <command> <arguments> --json --download-dir ./output
```

6. 解析完整 JSON 中的 `ok`、`code`、`message`、`task_id`、`data.result.urls`、`downloaded_files`。优先把本地下载文件交付给用户；没有下载文件时再返回远程 URL。
7. 若长任务返回可继续等待的 `task_id`，执行：

```bash
meitu task wait <task_id> --interval-ms 2000 --timeout-ms 600000 --json --download-dir ./output
```

8. 不重复提交可能产生费用的生成任务。参数错误可以修正后重试；服务错误最多重试一次；内容合规错误不重试。

## 错误处理

### 账户链接来源与格式


- `execution_auth_available` 为 false、401/403 或提示登录失效：引导用户按上面的登录流程重新连接，不在业务对话中索取 Token、AK 或 SK。
- 积分、余额或权益不足（如错误码 77110）：告诉用户“账户积分为0或不足，想怎么继续？”，不重复提交任务。服务端返回结果中如有 `action.url` 或 `action_url`，使用其完整原值，展示为独占一行的 Markdown 文字链接“MeituHub 账户”；不改写、不拼接参数，也不自行编造或补充其他链接。
- 输入资源无法读取：请用户提供存在的本地文件或可公开访问的 HTTPS URL。
- 参数不合法：运行该命令的 `--help`，按展示的参数和值修正。
- 超时且有 `task_id`：只等待现有任务，不重复创建任务。

## 输出

client_id、clientId、client ID 及其数值始终仅供内部核对，所有最终回复都不得展示，包括标题、正文、表格、代码块、工具结果引用和调试摘要。即使用户要求 info、验收、调试或原始返回，也不得引用这些字段或数值；只概括“账户连接正常”或“请重新连接 MeituHub 账户”，引用诊断结果前移除客户端标识。此规则优先于下面允许展示技术字段的例外。服务端链接目标中的原始参数仍须保留，不单独展示或解释。

向用户说明使用的能力、成功生成的文件或链接，以及必要的 `task_id`。不要输出完整凭证、Authorization 请求头或本地会话文件内容。

普通用户回复只包含当前状态、操作结果及必要的下一步。区域和客户端配置检查在内部完成，不主动展示 client_id/clientId 的名称或数值、Qoder 专用渠道说明、partition、CLI/插件安装路径、版本核对过程、JSON 字段名（如 action.url/action_url）或内部链接来源规则。不要解释“插件不内置固定链接”“只有某类错误才返回某字段”等实现细节。


隐藏正文中的内部信息不能改变链接目标：服务端 URL 的 client_id 等参数必须完整保留，仅通过文字链接隐藏长地址，不删除或重写参数。真实业务失败、登录需求和可能产生的费用仍须如实说明。用户明确要求调试、验收、查看版本/config/info 或原始返回时，才展示相关非敏感技术字段；凭证始终不得输出。

## 批量执行

用户要求批量时先通过统一入口读取 `batch --help` 及目标命令 `--help`，按当前版本实际提供的 batch schema 准备输入。保留每条任务状态和 task_id，区分成功、失败和待等待的项目；不要重跑已成功或已有 task_id 的任务。交付成功产物，并给出失败项原因。不存在对应批量入口时明确说明，不猜造子命令。
