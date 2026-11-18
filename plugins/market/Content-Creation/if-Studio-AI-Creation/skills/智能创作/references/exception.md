# 异常管理模块 — 场景异常运行指导

执行中遇到异常才进本模块：按症状查对应小节处置，处置完回原流程继续；
不在开聊前做例行体检（门禁只用 `ifs_ping`，见 SKILL.md §3 原则 1）。
未授权偏好分流、三选一对话框与降级承接见 SKILL.md §5，连接器请求与降级语义细则见 [connector.md](connector.md)（连接器请求模块）；安装/激活步骤见 brand.md「激活插件」
与 CONNECTORS.md；正常流程与模块路由见 SKILL.md。

## 1. 连接与注册异常

| 症状 | 处置 |
|------|------|
| 连接器方法查不到 / 连接失败 | **先分清两件事**：懒加载宿主下 `ifs_*` 本来就不在会话工具列表里（要靠元工具取），所以「工具列表没有 ifs_*」**不等于**未授权——判定以 `mcp_list`（如 `keyword: "ifs"`）能否列出 iconfont-ifs 的方法为准。`mcp_list` 也查不到 = 连接器未挂载/未授权，或插件未启用、装改后未重启 Qoder → **先主动唤起授权页**（宿主有连接器管理工具时：取 iconfont-ifs 的 `serverId` → `action=authorize` → 用户在浏览器登录同意 → `action=retry` + `ifs_ping` 复验；细则 → connector.md §3）：通过即继续；唤起不可用或仍未授权 → **再查通道偏好**（connector.md §3「通道偏好记忆」）：偏好=CLI → 不再唤起、跳过对话框直接走降级承接；偏好=连接器 → 同样跳过对话框、直接降级承接并如实说明（唤起已试过；连接器暂不可用、可能授权过期；降级≠改选择、不写偏好）；**无偏好（从未选择过）→ 唤起失败后才弹三选一对话框**（唯一一次「如何运行」询问；connector.md §3），不自行降级；用户选「已完成连接器授权」复验仍查不到时进本判定链：iconfont-ifs 不在位 = 平台服务未在位或插件未启用（生产检查平台常驻服务；hooks 生效但 `mcp_list` 仍无 ifs 方法 = MCP 注册表是应用启动快照，装/改插件后须重启 Qoder，新开会话不够，实测）——排查后**再次弹出对话框**供用户改选；选「暂不授权」→ **先写偏好（channel=cli，跨会话不再询问）**再走降级通道承接（官方 ifs CLI 直连平台，不经连接器；首选内置 MCP 直通 `ifs mcp call <同名工具>`，链路校验用 `ifs mcp call ifs_ping --args '{}'`，环境诊断用 `ifs doctor --json`；细则 → [connector.md](connector.md) §4），选「取消任务」→ 停止任务并简要介绍插件能力与使用场景（未作答，下次仍询问一次） |
| 工具调用报 Not Found（404） | 服务端重启致 Mcp-Session-Id 失效：Qoder 不会自动重初始化，重开会话或重启应用让连接器重连；期间可用降级通道继续（CLI 独立于连接器会话，不受陈旧会话影响；细则 → connector.md §4） |
| CLI 降级模式任务受阻（未安装/登录不通/持续报错/能力缺失）且连接器可完成 | **反向升级**（降级期间唯一再提连接器的场景）：说明卡点 + 提示用户本人恢复（重新授权）连接器（引导正文 → SKILL.md §5，**不弹三选一对话框**）→ 授权后复验 `ifs_ping` 切回继续；拒绝 → 报阻塞结论 + 替代建议；同一任务至多提示一次（细则 → [connector.md](connector.md) §4.4） |

## 2. 授权异常

| 症状 | 处置 |
|------|------|
| 工具调用 401 / 提示未授权 | 连接器 OAuth 缺失或过期 → 先 `ifs_ping` 探活确认 → **先主动唤起授权页**（宿主有连接器管理工具时：取 iconfont-ifs 的 `serverId` → `action=authorize` → 用户在浏览器登录同意 → `action=retry` + `ifs_ping` 复验，通过即继续、不弹框；同一任务不反复唤起；细则 → [connector.md](connector.md) §3）→ 唤起不可用或仍未授权再查通道偏好：偏好=CLI → 不弹框、直接降级承接（→ connector.md §4）；偏好=连接器 → 不弹框、直接降级承接并如实说明（唤起已试过；可能授权过期；降级≠改选择、不写偏好；需要恢复随时走 §4.4 提示）；**无偏好（从未选择过）→ 唤起失败后才弹三选一对话框**（唯一一次「如何运行」询问；已完成连接器授权 / 暂不授权 / 取消任务；细则 → [connector.md](connector.md) §3、话术 → SKILL.md §5）：选「已完成连接器授权」→ 复验 `ifs_ping`，通过切回主通道并更新偏好为 connector、仍失败进本表 §1 判定链；选「暂不授权」→ **先写偏好（channel=cli）**再降级承接（→ connector.md §4）；选「取消任务」→ 停止任务并简要介绍插件能力与使用场景（不写偏好，未作答下次仍询问一次）。授权页可由助手唤起，但登录与同意必须用户本人，**绝不代点**（不代替用户走完 OAuth——实测限定名引用/PKCE 代走均不可行，见 CONNECTORS.md）；对话框只在从未做过通道选择时出现；「暂不授权」记入偏好后跨会话不再询问（偏好=CLI 时不弹框、不再唤起，直接降级） |

## 3. 调用异常

| 症状 | 处置 |
|------|------|
| 报 `MCP Call tool parameter validation failed: params must have required property 'toolName'` | **外层信封错，请求根本没出本机**（平台没收到、不扣算力，因此补齐后重发**同一次**调用不算重复发消息）：经元工具调用时 `toolName` 与 `arguments` 必须**平级**、业务参数只进 `arguments`；三种写错形态=`toolName` 写进 `arguments` 里 / 写成 `tool_name` / 把业务参数摊到顶层。修正信封后原样重发；全限定名回 `mcp_list`（如 `keyword: "ifs"`）实时取，**不凭记忆拼连接器 key**。细则 → [connector.md](connector.md) §1「先判调用形态」 |
| 报 `<方法名> (<…> MCP Server) tool parameter validation failed: params must NOT have additional properties`，**且多出来的字段就是 `toolName` / `arguments`（含值为 `null` 的空壳）** | **信封键混进了直调参数**（实测：向 `…__ifs_canvas_upload` 传完整信封、向 `…__ifs_canvas_create` 多带 `arguments: null`）：直调工具的入参就是业务参数本体——删掉 `toolName` / `arguments` 这两个键、业务参数摊平，**原样重发同一次调用**（同样没送达、不扣算力、不算重复发消息）。判形态：工具名已含方法名 = 直调，只有工具名本身是 `mcp_call` 才用信封（细则 → [connector.md](connector.md) §1「先判调用形态」） |
| 报 `<方法名> (<…> MCP Server) tool parameter validation failed: params must NOT have additional properties` / `must have required property 'x'`（多出的字段是**业务字段**） | **内层参数错**（同样没送达、同样原样重发同一次）：形态已对，按实时 inputSchema 核对参数名（snake_case，勿自转大小写）、必填项与多余字段——实时 schema 一律 `additionalProperties: false`，**多一个字段就被拒**；常见于把 `agent_code` / `skill` 这类不属于该方法的字段塞进参数，或给**无入参的方法**（`ifs_ping` / `ifs_canvas_models` / `ifs_balance`）传了东西——它们只传空对象 `{}`（2026-11-02 实测：给 `ifs_canvas_models` 传 `{"keyword":"video"}` 就是这么被拒的；2026-11-04 实测：给 `ifs_ping` 传 `{"keyword":"upload"}` 同样被拒——**探活不是方法检索入口，找方法用 `mcp_list` 的 `keyword`**；模型清单不收过滤参数，按图像/视频挑就在返回清单里自己筛，`mcp_list` 的 `keyword` 是元工具入参、不进业务参数）；**改参数，不改需求**（细则 → [connector.md](connector.md) §1「参数关」） |
| 报 `Tool "…" not found` / `MCP tool "…" not found` | **没载入会话工具表**（不是未授权、也不是参数错）：立刻回发现入口（`mcp_list` 或宿主工具搜索）取实时全限定名重发，**不按同名重试、不猜别名**（connector.md §1 ①） |
| 报 `No connected MCP server offers a tool named …` | **这个名字此刻不在宿主已发现的 MCP 工具面里**（宿主 `mcp_call` 的前置门禁判定，不是参数错）：先 `mcp_list`（`keyword: "ifs"`）复核——列得出 ifs 方法就用实时名重发；整个 iconfont-ifs 都列不出 = 服务器没连上 / 没被发现（插件装或改后没重启宿主、连接器没连）→ 转本表 §1 判定链（重启宿主 / 偏好分流）或降级 CLI。**别改名硬试**（`mcp__iconfont-ifs__…`、带冒号的变体都无效；名字随插件 `name` 派生、手拼必漂移，只取 `mcp_list` 实时结果）；**这条 ≠ 未授权**，不得只据此降级或弹三选一对话框 |
| MCP 工具调用报 -32603 | 原样重试一次；仍失败按本表处置（降级通道用 `ifs mcp tools --json --profile {cli.profile}` 核对参数与实时方法面，`ifs doctor --json` 诊断 CLI 环境/认证/网络），不绕过连接器直调平台 |
| create 报参数不合法 / 缺必填（含 -32603 形态） | **改参数，不改需求**：原样重试同一条一次 → 仍失败就按会话内实时 schema 核对必填项与参数名（snake_case，勿自转大小写）、`model` / `skill` 是否取自实时清单、参考媒体是不是上传返回的 URL；确认无误仍送不进才转 §1/§2 判定链。**期间绝不加发第二条内容相同或冲突的消息**（重复发消息 = 起两条线程、双份扣算力，chat.md 阶段 ①「准确送达」） |
| 降级期 `ifs mcp call` 报 `Unknown tool`（-32602） | 方法不在当前环境的实时工具面：先 `ifs mcp tools --json --profile {cli.profile}` 核对工具名（**不要改名反复重试**）；确实没有 → 按各模块口径如实提示「功能尚未就绪」（connector.md §4.2） |
| 降级期 `ifs_ping` 不通 / 未登录 / 401 / profile 不存在 | **先授权再执行（与连接器同节奏）**：发起 `ifs auth login --oauth --registry {cli.registry}/ --profile {cli.profile}`（后台执行，CLI 自己打开系统浏览器）→ 提示用户本人登录并点同意、**停下等用户确认** → 确认后再 `ifs_ping` 复验，通过才继续原任务；确认前不发消息、不轮询；同一任务最多发起两次登录，仍不通按 §4.4 说明卡点（细则 → [connector.md](connector.md) §4.1） |
| 降级期报 OAuth 会话失效 / profile 不存在，或 `ifs auth status --json` 里该 profile 的 registry 与 `{cli.registry}` 不一致 | **环境错配，不是 CLI 失效**：按 connector.md §4.1 用 `--registry {cli.registry}/ --profile {cli.profile}` 重新登录线上（登录页用户本人操作）；**不拿机器上的 current profile（可能是预发）把任务推下去**，也不把它的 registry 当插件环境（2026-11-04 线上包 CLI 落到预发就是这个原因） |
| 降级期原生命令（`canvas run` / `canvas poll` / `upload`）报 401 并提示重新登录 | **凭据分道，不是 CLI 失效**（2026-10-22 实测：原生命令走旧 Token 通道、`ifs mcp` 走 OAuth 通道，`--oauth` 登录的 profile 跑原生命令必然 401）→ **改走 MCP 直通继续任务**，不反复让用户重新登录、不因此触发反向升级（connector.md §4.3）；`IFS_TOKEN` 里残留 `sr_` 旧 Token 会让直通报错，先 `unset IFS_TOKEN` |
| 模型匹配不到 | `ifs_canvas_models` 拉实时清单，改用清单内的 `name` 字段（降级期 `ifs mcp call ifs_canvas_models` 同名字段；原生 `ifs models` 是 `display_name`/`id` 另一套字段，勿混用） |
| 本地素材直传被拒（超 5MB / 扩展名不在 `accepted_types` / 票据已用过或过期） | 按返回的 `max_bytes` 与 `accepted_types` 判定（允许类型按 `filename` 后缀给出，图/视频/音频三组不同）：压缩到上限内或换合规格式后**重新取票**（票据一次性，不复用旧票、不拿旧 upload_id 重试）；curl 报错先查 `-F 'ticket=…'` 是否排在 `-F 'file=@…'` 之前、Windows 是否把单引号换成双引号；仍不通 → 小图退 `data_base64`、或请用户给远程图片地址走 `url` 转传 |
| 上传拿不到参考媒体 URL（`ifs_canvas_upload` 报 -32603 且重试无效；2026-10-22 实测连接器通道三通道均出现过，票据链前两步取票与本地直传都正常） | **不编 URL、不把本地路径直接传给 create**：如实告知该素材这次传不上去（可能是服务端方法异常），给替代路径（压缩后重试 / 改给远程地址 / 稍后再试）；任务不因此停摆，其余无参考媒体的部分照常推进。**票据与 `upload_id` 是一次性凭据**——不复用、不进对话与日志（connector.md §1） |

## 4. Chat 异常

| 症状 | 处置 |
|------|------|
| 配额超限（quota_exceeded / 算力不足） | **先经连接器 `ifs_balance` 查余额复核，再决定**（细则 → [user.md](user.md)「算力不足：先复核再决定」）：余额确实不够 → 如实转述提示（含返回中携带的充值链接）+ 给平台充值入口引导，**不重试、不重发**；余额够（提示与余额对不上）→ 说明情况后在原会话续聊继续，仍报同样提示就停下如实说明；查不到余额 → 按 `quota_info` 原样转述 + 充值入口，不编造数字 |
| 轮询久等无产物 | 未完成只返回 `in_progress`（降级 MCP 直通同样返回 `in_progress`）：继续 poll 原会话、勿调大等待，禁止重复发消息；CLI 原生命令便利层可加大 `--timeout`；**这不是终态**——持续到 done / 出错 / 配额 / 取消，不提前收尾、不问"要不要继续等"；**但有判死口**（会话 ID 错 = 永远 in_progress，见下方两条） |
| 宿主提示"连续相同调用"并拦停 poll | **任务大概率还在跑，这不是终态**（实测 2026-10-22：同参数连着四次放行、第五次被硬拦并提示改参数或直接给结论；中间夹一次不同调用即重新计数）。按 chat.md 阶段 ②「轮询节奏」继续等：① `timeout_seconds` 在 55/45/35 轮换 ② 轮间夹一次不同调用 ③ 长任务改走一次 Bash 调用内的**终端等待循环**（单轮 50 秒 × 预算 100 秒、Bash 超时给 3 分钟）。**换的是等待的调用形态，不是通道**——主通道仍是连接器，这不叫降级，也不要对用户说"CLI 可用/直通可用"（chat.md「对话呈现」）。三条都用完仍被掐 → 报一句真实进度并说明继续盯同一会话，**用户下一句话立刻接着 poll**；**严禁**"跟我说声『看下好了没』"式收尾 |
| poll 一直 `in_progress`，画布上却早已出图（**会话 ID 错时 poll 不报错**：2026-11-03 实测，传一个不存在的 `session_id` 照样回 `in_progress` + `poll_again=true`，永远不会自己结束） | **先停轮询，别重跑循环**：① 核对 `session_id` 是不是本次 `create` 返回的原值（`l/I`、`0/O` 一抄错就中）；② 用 `ifs_assets`（近 7 天，**不收 `canvas_id` 过滤**，看返回里的画布名称/链接对）或画布页核实产物——**有产物就按已有产物交付**，如实说服务端没回报完成状态；没有就说明情况 + 给画布链接。判死细则 → [chat.md](chat.md) 阶段 ②「轮询不会自己结束」 |
| 续聊答复建议未生效（服务端未识别） | A2UI 建议必须发 `suggestions[].title` 原文一字不改；用户意见在建议之外 → 直接发用户原话续聊 |
| 用户要叫停但对话无响应 | 见 chat.md「停止对话」：立即停止轮询 + 引导用户到画布页手动停止（助手不代点） |
| 对话内视频黑屏 / 时长 0:00 播不出 | **不是产物损坏**：对话渲染面板 CSP 无 `media-src`（`default-src 'none'`），远程 https、`data:` 内嵌、`fetch` 造 `blob:` 三种写法实测全被拦。改走两条可播通道：① 画布页原生播放器（主呈现）② 落盘本地文件（默认工作区 `outputs/`）+ **回复里给文件链接与所在目录** + 拉起系统播放器（macOS `open`，定位用 `open -R`）；地址本身可用 `curl -I` 复核（`Content-Type: video/mp4`、支持 Range）。**别再往对话里挂 `<video>`**（细则 → chat.md 阶段 ⑤） |
| 对话内图片显示"图片无法显示，打开文件" | 消息正文写**本地路径**图片不渲染（2026-10-20 实测）→ 改用 `media[].url` **远程地址**渲染；远程图也拿不到时退到文件链接（落盘 + 绝对路径 + 所在目录）。对话内 HTML 渲染面板另有一层限制：只允许 `img-src data:`，该面板里远程图同样不出，要放图须 base64 成 `data:` 内嵌 |
| 会话没工作区，用户说"找不到文件" | 产物落在宿主给会话的临时工作目录 `<pwd>/outputs/`（实测形如 `~/.qoderwork/workspace/<id>/outputs`，**不在用户项目里**）→ 给完整路径 + 目录定位（macOS `open -R` / Windows `explorer /select,` / Linux 打开所在目录），并问要不要复制一份到用户指定目录；**不删除、不挪走、不自往家目录另写一份**；判定与口径 → chat.md 阶段 ⑤ step 6 |
| 服务端报错（`message` 携带错误信息） | 如实转述给用户，按症状查本表对应行；不编造原因与数据 |
| 用户追问"是不是降级到 CLI 了 / 直通是什么意思" | **多为内部话术泄漏导致的误解**（把等待技巧讲成了通道变化）。先照实核对：连接器是否仍正常（探活通过、发消息与续聊是否走的连接器），再一次性讲清"主通道是连接器 / 现在是否真的降级 / 任务行为有没有变化"三件事；确实降级了就说明原因与恢复方式，没降级就说"没有切换，只是换了等待方式，结果与进度不受影响"。之后按 chat.md「对话呈现」"通道术语不进对话"执行，不再输出这类词 |

## 5. 页面异常（内置浏览器）

| 症状 | 处置 |
|------|------|
| IFS 页面落到登录页 / 万相绑定页 / 内网版引导 | **正常边界**（走授权链接打开时本就会经过这几页）：停下提示用户自己在内置浏览器里完成一次登录或绑定，页面会自动回跳目标画布；**绝不代点、代输、代选身份**。用户点过一次后登录态持久，之后不再打断 |
| 取不到画布授权链接（`ifs_canvas_authorize` 未挂载 / 调用报错且重试无效 / 降级期实时方法面没有该方法——`ifs mcp tools --json` 核对） | **不卡流程**：跳过授权链接，直接打开标准形态画布地址；落点仍按 screen.md「3. 落点三判」判定。**不拼造登录地址**（登录域名是主站域、随版本变化，只能来自工具返回） |
| 打开后停在验证墙（按钮 disabled，用户也过不去） | 硬墙：放弃浏览器路径 → screen.md「5. 链接兜底」给画布链接 |

## 6. 环境自检（用户要求"体检"时）

依序执行并汇总：`ifs_ping`（连接探活）→ `ifs_canvas_models`（服务连通与模型清单）。
两步通过即告知"环境就绪，可以直接开始创作"；链路存疑或两步之外要深查时，
用降级通道 CLI 跑 `ifs doctor --json`（CLI 环境/认证/网络全貌，不经连接器）。
任何一步失败按上表对应行处置。连接器不可用而走降级时，自检改为：`ifs mcp ping --profile {cli.profile}` →
`ifs mcp call ifs_ping --args '{}' --profile {cli.profile}`
（授权身份 + scope）→ `ifs mcp call ifs_canvas_models --args '{}' --profile {cli.profile}`（服务连通与模型清单），
链路仍存疑再跑 `ifs doctor --json`（CLI 环境/认证/网络全貌，不经连接器；注意 §3 凭据分道）。

## 7. 降级模式（细则 → connector.md）

连接器授权异常的检测与分流、降级通道（官方 ifs CLI，**首选其内置 MCP 直通 `ifs mcp call`**——
与连接器同工具面同参数）的接入与调用细则、
与主通道的关系及红线，统一定义在 [connector.md](connector.md)（连接器请求模块）；
本表 §1/§2 的「降级通道承接」均指该模块。
