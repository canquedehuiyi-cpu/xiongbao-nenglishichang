# 连接器请求模块 — 统一通信（调用约定 · 能力总览 · 授权异常降级 · 恢复）

> 本模块是**统一通信模块**：统一管理如何请求连接器（§1）、能力总览与调用时机（§2）、
> 授权异常的检测分流（§3）与降级接管（§4）、恢复与两通道关系（§5）。
> 底层被所有模块依赖、不占执行路径：约定常驻生效；出现授权异常时按本模块处置，处置完回原模块继续。

## 1. 如何请求连接器（主通道 iconfont-ifs）

- 形态：iconfont-ifs 连接器（MCP over HTTP + OAuth，插件 mcp.json 注册的 IFS 平台远程 MCP 服务），业务参数层面
  没有其他封装层；**但宿主暴露方式不固定**：Qoder 里两种都出现过——直接给成一等工具 `mcp__<server>__<方法>`，
  或懒加载（会话工具表里只有 `mcp_list` / `mcp_get` / `mcp_call`）。**先看会话里实际给的是哪种，再定参数怎么传**（下条）。
  实测多数会话是后者：`ifs_*` 一个都不在工具表里，**此时直接拿拼出来的名字直呼必报 `Tool "…" not found`**（2026-11-04 实例），
  所以**首次 IFS 调用前先发现一次**（`mcp_list` 或宿主工具搜索），把实时全限定名在本会话复用。
  判据只有一条：**看本次会话的工具表里有什么**，两种形态都支持、不预设。
- **调用顺序、调用形态与调用信封（宿主关，先于一切参数——顺序错了请求出不去）**：

  - **两步走，顺序不能反**：① 取实时名并确认已载入会话工具表 → ② 再调用。名字**只能**来自本次会话的
    实时工具面，**不许照本文档里的示例拼**（本文出现的全限定名只是格式示意，不是可调用的注册名）。
  - **①取名与载入**：按本次会话的工具表分两种形态——
    **只有 `mcp_list` / `mcp_get` / `mcp_call`（Qoder 懒加载实测）** → `mcp_list`（如 `{ keyword: "ifs" }`）发现方法、
    `mcp_get` 查 schema、`mcp_call` 调用，首次取到后本会话复用；
    **直接出现 `mcp__<server>__<方法>` 一等工具** → 先确认它**已载入会话工具表**（惰性宿主经宿主的搜索/加载入口载入，
    没载入就直呼会报 `Tool "…" not found`）——**这不是未授权、也不是连接器失效**：立刻回发现入口（`mcp_list` 或宿主工具搜索）
    取实时名重发，**不按同名重试、不猜别名**（→ exception.md §3）。
    全限定名由宿主按 `mcp__<server>__<方法>` 生成（server 名里的非法字符规范化为下划线）：Qoder 插件连接器的 server key
    由插件清单的 `name` 派生（当前 `plugin:if-Studio-AI-Creation:iconfont-ifs`，冒号变下划线、连字符保留），所以名字形如
    `mcp__plugin_<插件名>_iconfont-ifs__<方法>`——**以实时发现结果为准，不照本文或目录名拼**（派生来源是插件清单的 `name`，
    目录名与它无关、照目录名拼必错）；`mcp__iconfont-ifs__…`、带冒号的变体、别的前缀同样无效
    （2026-11-04 实测：这些变体一律报 `No connected MCP server offers a tool named …`）。
  - **② 先判调用形态，再定参数形状**（写错形态 = 请求根本出不去）：

    - **直调（会话里直接给了一等工具时，工具名本身就是全限定名）**：入口就是 `mcp__<server>__<方法>`（如
      `mcp__plugin_<插件名>_iconfont-ifs__ifs_canvas_create`，实际名以 `mcp_list` 返回为准）→ **参数就是业务参数本体**，直接摊平传：

      ```json
      { "media_type": "image", "media_url": "https://…", "prompt": "…" }
      ```

      参数对象的键**只能是该方法 inputSchema 里的业务字段**：`arguments` 与 `toolName` **一个都不能出现——
      连 `"arguments": null` 这种空壳也会被判 `params must NOT have additional properties`**。带了就删掉该键、
      业务参数摊平、原样重发同一次调用。
    - **经元工具（入口是 `mcp_call`，仅当工具名本身叫 `mcp_call`）**：才用 `toolName` + `arguments` 平级的信封，业务参数**只进
      `arguments`**：

      ```json
      { "toolName": "mcp__plugin_<插件名>_iconfont-ifs__ifs_canvas_poll",
        "arguments": { "session_id": "s_xxx", "canvas_id": "c_xxx", "timeout_seconds": 45 } }
      ```

      （`toolName` 的取值照抄 `mcp_list` 当次返回，不照本文示例拼。）

      三种高频写错形态：把 `toolName` 写进 `arguments` 里、写成 `tool_name`、把业务参数摊到顶层不带
      `toolName`——三者都只会被宿主判成「缺 `toolName`」。
    - **两形态混用是最常见的错**：直调工具的参数里混进了信封键（`arguments: null`、`{ toolName, arguments }`
      都算），报的正是 `params must NOT have additional properties`。**删掉这两个键、业务参数
      摊平原样重发同一次调用**即可。
  - **参数关（内层，紧跟着形态判断）**：实时 inputSchema 一律 `additionalProperties: false`——参数里
    **多一个字段就被宿主拒**（报 `params must NOT have additional properties`）。无入参的方法
    （`ifs_ping` / `ifs_canvas_models` / `ifs_balance`）**只传空对象 `{}`**——**找方法用 `mcp_list` 的 `keyword`，
    别拿 `ifs_ping` 当方法检索入口**（2026-11-04 实测：给 `ifs_ping` 传 `{"keyword":"upload"}` 被拒）；
    **模型清单不接受任何过滤参数**，要按图像或视频挑就在返回的清单里自己筛；`mcp_list` 的 `keyword` 是元工具
    自己的入参，永远不进业务方法的 `arguments`。字段有无与叫什么，以 `mcp_get` 实时 schema 为准。
  - **字段白名单（按方法查表，跨方法借字段必被拒）**：下表实测自 `ifs mcp tools --json`（2026-11-04，CLI 0.16.0），
    只列平台真有的字段；**实时 schema 与此不一致时以实时为准**，不按本表硬加、也不推测没写的参数：

    | 方法 | 可用字段 | 必填 |
    |------|---------|------|
    | `ifs_ping` / `ifs_canvas_models` / `ifs_balance` | 无（传 `{}`） | — |
    | `ifs_canvas_create` | `prompt` `media_url` `media_type` `model` `skill` `canvas_id` `session_id` `response_blocks` | 无 |
    | `ifs_canvas_poll` | `session_id` `canvas_id` `timeout_seconds` | `session_id` |
    | `ifs_canvas_upload` | `data_base64` `filename` `url` `upload_id` `canvas_id` | 无 |
    | `ifs_canvas_upload_ticket` | `filename` `size_bytes` `canvas_id` | `filename` |
    | `ifs_canvas_authorize` | `canvas_url` | `canvas_url` |
    | `ifs_canvas_list` | `keyword` `limit` `cursor` | 无 |
    | `ifs_assets` | `file_type` `source` `limit` `cursor`（**不接 `canvas_id`**） | 无 |
    | `ifs_inspirations` | `tag` `agent_code` `limit` `cursor` | 无 |

    `ifs_canvas_create` 传 `canvas_id` = 在该画布续聊，**不传 = 新建画布**——默认应传（定位顺序见 SKILL.md §3 原则 3），只有用户明确要求新建画布才省略。
    高频越界：给 `create` 传 `timeout_seconds` / `url` / `filename`（分别属于 poll 与 upload）；
    给 `ifs_assets` 传 `canvas_id` 当过滤条件（它只按类型/来源过滤，**每条返回里已经带 `canvas_id` / `canvas_name` / `canvas_url`**，画布归属直接看返回）；
    给 `ifs_ping` / `ifs_canvas_models` / `ifs_balance` 传任何过滤参数；
    把入参写成字符串数字（`limit` / `cursor` / `timeout_seconds` / `size_bytes` 都是 number，`"cursor": "1"` 会被拒）；
    `media_type` 枚举只有 `image` / `video`（传 `audio` / `png` 会被拒，音频参考素材不传它、留给缺省推断）。
    `cursor` 是**页码**（从 1 递增，不是不透明 token）；`ifs_assets` 默认只覆盖**最近 7 天**（返回里 `range.start` / `end` 就是窗口，`total` / `has_more` 判翻页），`ifs_canvas_list` 按更新时间倒序、无 `has_more`（`total` > 本页 `count` 就还能翻）。
  - **报错分三类，处置不同**（都在宿主侧、请求没出本机、平台没收到，因此**不算重复发消息**）：

    | 报错形态 | 判定与处置 |
    |---------|-----------|
    | `MCP Call tool parameter validation failed: params must have required property 'toolName'` | **外层信封错**：补齐 `toolName`（与 `arguments` 平级）后**原样重发同一次调用**；不改工具名、不改需求、不加发第二条消息 |
    | `<方法名> (<server> MCP Server) tool parameter validation failed: params must NOT have additional properties`，**被点名的多余字段是 `toolName` / `arguments`** | **信封键混进了直调参数**：这个方法是直调工具，参数只放业务字段 → 删掉 `toolName` / `arguments`（含值为 `null` 的空壳）、业务参数摊平**原样重发同一次调用**（实测：给 `ifs_canvas_upload` 套了完整信封、给 `ifs_canvas_create` 多了 `arguments: null`） |
    | `<方法名> (<server> MCP Server) tool parameter validation failed: params must …`（多出的字段是业务字段 / 缺必填） | **内层参数错**：形态已对，按上条「参数关」与实时 inputSchema 去掉多余字段或补齐必填，再原样重发同一次调用 |
    | `Tool "…" not found` / `MCP tool "…" not found` | **没载入会话工具表**（不是参数错、也不是未授权）：立刻回发现入口（`mcp_list` 或宿主工具搜索）取实时全限定名重发，**不按同名重试、不猜别名** |
    | `No connected MCP server offers a tool named …` | **这个名字此刻不在宿主已发现的 MCP 工具面里**（宿主元工具 `mcp_call` 的前置门禁判定，不是参数错）：① 立刻 `mcp_list`（`keyword: "ifs"`）复核——列得出 ifs 方法就用实时名列重发；② 整个 iconfont-ifs 都列不出 = 服务器没连上 / 没被发现（插件装或改后没重启宿主、连接器没连）→ 转到 §3 判定与偏好分流（提示用户重启宿主或连接连接器，或降级 CLI）；**别改名硬试**（2026-11-04 实测：`mcp__iconfont-ifs__ifs_ping`、带冒号的变体都无效；名字随插件 `name` 派生，手拼必漂移，只取实时发现结果） |

  - **实测边界（2026-11-02）**：把 800+ 字中文长 `prompt` 塞进 `arguments` **不影响**信封解析（宿主对
    `toolName` 与 `arguments` 各自做 JSON schema 校验，都在发出前）——信封出错跟文案长度、中文、数组
    都无关，唯一成因是**拼法**。连续同参被宿主的重复调用保护拦停是**另一件事**（按下方 poll 节奏条处置，
    不是信封问题）。症状排障表 → [exception.md](exception.md) §3。
- **门禁先行**（SKILL.md §3 原则 1）：每次会话首次 IFS 调用前先 `ifs_ping` 探活。
- 参数名以**会话内实时 schema（tools/list）为准**（本期实测为 snake_case，如 `media_url` / `canvas_id` /
  `timeout_seconds`——勿自行转换大小写），类型/必填/枚举同以实时 schema 为准；§1 的字段白名单只是防
  幻觉参数的实测快照、非参数手册，**与实时 schema 冲突时以实时为准**（能力范围与编排去向 → §2）。
- **请求内容就是用户的意思（发消息必守）**：`prompt` 按用户原话组织——用户提的主体、数量、画幅/尺寸、时长、
  画面文字原文、指定模型/技能、否定项**逐项带进消息**，不改写、不丢项、不加戏、不擅自换语言；用户给的多段文案
  **整段提交**，不摘成摘要、不用省略号收尾；`model` 取 `ifs_canvas_models` 的 `name`、`skill` 取实时技能名，
  不许凭记忆编参数值。返回里的受理态（`created` / `submitted`）+ `canvas_id` / `session_id` 齐全才算这条消息
  真的送出去；参数不合法 / -32603 → **原样重试同一条**，绝不加发第二条内容相同或冲突的消息
  （内容关与传输关的细则 → chat.md 阶段 ①「需求忠实」「准确送达」）。
- 工具返回 JSON 文本，**只解析 text content**（stderr 仅用于进程诊断）：`status`（poll 态：in_progress/
  done/summary_feedback/ask_user/quota_exceeded/canceled，以实时返回为准）/ `canvas_url` / `canvas_id` /
  `session_id` / `progress` / `media` / `planning_text` / `response_blocks` / `quota_info`（配额超限时）/
  `message`。
- `message` 是平台在对话里的**用户可见消息**：每轮 poll 有新内容就立即原意转述到对话框，与 status 分支
  并行处理（相同内容去重、不攒到 done）；没有新文本也仍补一句短进度（已等待时长 / `progress` 百分比）；
  A2UI/表单的 `planning_text` / `response_blocks` 同样先在对话里
  回显、再收集用户选择（细则 → chat.md「对话呈现」/阶段 ②③④）。
- **poll 的节奏要防宿主的重复调用保护**（2026-10-22 实测：同一工具连续四次同参放行、第五次被硬拦，
  中间夹一次不同调用即重新计数）：`timeout_seconds` 在 **55/45/35 之间轮换**（相邻两次不同值，定位参数不动）、
  轮间可夹一次不同调用；已知长任务把多轮 poll 收进**一次 Bash 调用**内的**终端等待循环**（§4.2 末条）。
  **被拦停不等于任务结束**，仍要持续等到终态（权威口径 → chat.md 阶段 ②「轮询节奏」）。
  **它也不是降级**：主通道仍是连接器，只是"等"这一步换个调用形态，不写偏好、不对用户播报
  （话术边界 → chat.md「对话呈现」"通道术语不进对话"）。
- 连接器 poll **无落盘参数**：done 回 `media[].url`（图片/视频/音频）或文本/其他素材内容，**本轮新生成的产物默认落盘**到工作区 `outputs/`（只下新成果，
  用户上传的原始素材 / 画布输入原图不重复下；Bash 下载；
  细则 → asset.md「产物落盘与整理」；**会话没绑定工作区时**以 `pwd` 的会话目录为根落它的 `outputs/`，
  交付时说明该目录不在用户项目里 → chat.md 阶段 ⑤ step 6）；
  降级期首选的 CLI MCP 直通同样只回 URL、落盘同样用 Bash（§4.2）；`--save-dir` 自动落盘是 CLI
  **原生命令便利层**独有的能力（§4.3，指向同一目录即可）。
- **本地素材优先走票据直传**（2026-10-22 实测链，三通道取舍见下）：文件在本机、只有本地路径时 →
  `ifs_canvas_upload_ticket`（`filename` 必填、`size_bytes` / `canvas_id` 可选）拿一次性票据 →
  按返回的 `command` 在本地执行（把 `LOCAL_FILE_PATH` 换成绝对路径，**`ticket` 字段必须排在 `file` 之前**；
  Windows cmd 把单引号换成双引号）→ 响应 `data.upload_id` 再交 `ifs_canvas_upload` 换参考媒体 URL。
  **文件字节全程不进对话**，这是它相对 base64 通道的决定性优势。三通道取舍：
  **本地文件 → 票据直传**；已有远程地址 → `url` 转传（服务端代取）；`data_base64` + `filename` →
  **只作小图兜底**（大图/视频会把整段 base64 灌进上下文，不要用）。
  边界与红线（均以实时返回为准）：单文件上限 5MB（超限在取票阶段直接拒）、票据一次性且**短时效**（服务端提示不同口径出现过，过期就重新取票，不拿旧票硬试）、
  `upload_id` 一次性（实测 10 分钟内有效）且**不是 URL**、允许的类型按 `filename` 后缀给出
  （实测图片 `png/jpg/jpeg/webp/gif/bmp`、视频 `mp4/mov/webm/m4v`、音频 `mp3/wav/wma`）、
  **票据与 upload_id 都按凭据对待**——不拼进地址、不写日志、不进对话（编排口径 → chat.md 阶段 ①「上传前置」）。
- 画布链接（返回的 `canvas_url` / 只剩 ID 时自构深链）**打开或输出前统一整形**：去掉 `sessionId`
  （画布页缺省即最新会话，定位具体会话靠 `session_id` 走续聊，不靠 URL）、在 `?` 后**整串照抄**平台配置段注入的标准后缀 `{canvas_link.query_suffix}`（hook 从 config/platform.json 的 `canvas_link` 段现场拼装：面板参数隐藏会话面板/左侧栏/顶栏，`top_actions` 为平台口径顶栏操作参数，`zawarudo_*` 为平台口径画布交互开关（开关个数与取值以 `canvas_link.fixed_params` 为准，本文档不写死字面值），`title` 为平台口径画布页标题（后缀里已是编码值，**不用带空格的明文**），`from` 标明访问来自本宿主/插件、供平台侧流量归因），不逐参数重拼，
  其余键保持原值——
  形态、域名与 `title` / `from` 取值细则 → screen.md「4. 地址来源」。
- 模型传 `ifs_canvas_models` 返回的 `name` 字段（支持模糊匹配）；拿不准先 `ifs_canvas_models`；
  用户未指定则不传（底层自动拉全量清单）。
- **打开画布页前先取授权链接**（2026-10-22 起为默认动作）：把**整形后的画布地址**作为 `canvas_url` 交
  `ifs_canvas_authorize`，用返回的 `login_url` 作为内置浏览器的导航目标——已登录时直接进画布，未登录时先出主站
  登录页、登录成功自动回跳该画布。`login_url` 只作导航目标，**不在对话里输出**（对话/兜底仍用标准形态画布地址）；
  它指向**主站登录域**（与画布域不同、随版本变化），只用工具返回值不拼不写死。
  方法未挂载 / 调用失败（-32603 重试一次仍失败）/ 降级期实时工具面没有该方法（`ifs mcp tools --json --profile {cli.profile}` 核对，§4.2）→
  **直接打开画布地址，不卡流程**
  （步骤、落点判定与实测 → screen.md「1. 唤起」「3. 落点三判」）。
- MCP 调用报 -32603 → 原样重试一次；仍失败转 [exception.md](exception.md) 排障表，
  不绕过连接器直调平台（SKILL.md §3 原则 5）。

## 2. 能力总览与调用时机

- **方法清单与参数 schema 由 tools/list 原生提供**（连接器自带各方法与用途描述；会话内取法 = `mcp_list`
  拿全限定名、`mcp_get` 拿某方法的 inputSchema，见 §1「先判调用形态」）——本文**不维护工具面**，
  连接器增删方法本文不随之更新（与 CONNECTORS.md 口径一致）；§1「字段白名单」只是防幻觉参数的实测快照，
  **实时 schema 优先**。
- 需要某项能力（画布历史 / 资产库 / 灵感 / 算力等管理查询类）时，以会话内实际挂载的方法为准：
  **有 → 直接用；没有 → 如实向用户提示「功能尚未就绪」**（各模块口径 → asset.md / user.md /
  help.md），不打开平台页面代查、不编造数据。
- 各能力的编排细则归执行模块：发消息 / 轮询 / 中断答复的主循环与状态分支 → [chat.md](chat.md)；
  选模型 → [help.md](help.md)；探活复验 → §3 / §5。

降级通道（连接器不可用时）怎么调同一套方法 → §4.2（CLI 内置 MCP 直通，工具名/参数/返回与本文一致）；
原生命令便利层 → §4.3。

## 3. 授权异常：检测与分流（主动唤起授权页 · 偏好记忆 · 三选一对话框）

| 信号 | 含义 |
|------|------|
| `mcp_list` 列不出 iconfont-ifs 的 `ifs_*` 方法 | 连接器未挂载/未授权，或插件未启用、装改后未重启 Qoder。**注意懒加载下 `ifs_*` 本就不在会话工具列表里**——工具列表没有不等于未授权，判定以 `mcp_list` 能否列出方法为准（§1）。**单个调用报 `Tool "…" not found` 不算这一条**：先按 §1 载入后原名重试；**`mcp_list` 也列不出 + 调用报 `No connected MCP server offers a tool named …` 就是这一条**（服务器没连上：装改后没重启、或连接器没连），按本表偏好分流处置 |
| 调用 401 / 提示未授权 | 连接器 OAuth 缺失或过期 |
| 服务连不通 | 平台常驻服务未在位 |
| 用户在对话框选「取消任务」 | 尊重决定：停止任务，不降级、不纠缠；向用户**简要介绍插件能力与使用场景**（口径 → [brand.md](brand.md)，两三句即可），让用户有需要时随时再发起 |

**判定**：主通道用 `ifs_ping`（探活，门禁豁免）；确认走降级后，CLI 侧用
`ifs mcp call ifs_ping --args '{}' --profile {cli.profile}`（**唯一有效的降级链路校验**——返回 `pong` + 身份 + scope 才算可用）复检，
`ifs auth status --json`（profile / registry）与 `ifs doctor --json`（CLI 环境/认证/网络全貌）只作补充诊断。

**主动唤起授权页（未授权第一动作，先于偏好分流）**：

会话工具表里有宿主自带的连接器管理工具时（Qoder 实测：`mcp__qoder-settings__manage_app_mcp`、方法
`manage_app_mcp`；工具名、方法名、动作与返回字段以会话内实时工具表与 schema 为准），未授权直接唤起授权页：

| 步骤 | 调用 | 判读 |
|------|------|------|
| 取 `serverId` | 宿主连接器列表 / `mcp_list` 返回条目里 iconfont-ifs 的 id | 每套安装不同，**实时取**；取不到就**不猜、不硬编 UUID**，直接走手动引导 |
| 唤起授权页 | `manage_app_mcp`，`action=authorize` + `serverId=<上一步的值>`（**只这两个键**） | 返回 `status=browser-opened` = 系统浏览器已打开 IFS 授权页；其它状态 / 报错 / 宿主拒绝该操作 = 唤起失败，走手动引导 |
| 等用户 | 回复里说一句「授权页已经帮您打开，用 IFS 账号登录后点同意授权，完成后回我一句」，然后停下等 | 浏览器里的登录与「同意授权」必须本人完成；**不紧跟 `retry`**（用户还没登录，重连必然失败，还多弹一次宿主确认） |
| 复验切回 | 用户说完成后 `action=retry` + 同一 `serverId` → `ifs_ping` | 通过 → 偏好更新为 connector、回原任务继续（**不弹三选一**）；仍不过 → 走偏好分流 / 三选一，**同一任务不再反复唤起** |

- 红线：只唤起、不代做——不代登录、不代同意、不代输账号、不探测用户身份；工具名、参数、`serverId`、
  返回 JSON 都不进对话。
- 动作名只用实测过的 `authorize` / `retry`；宿主多给的动作按实时 schema 走，**不猜名字硬试**；宿主没这个工具
  就直接走手动引导（下方对话框正文第 1 步），不臆造其它入口。
- 频率：同一任务最多唤起一次；用户明说「再打开一次授权页」才再调 `authorize`。

**通道偏好记忆（连接器不可用时，先查偏好再决定弹不弹框）**：

- 偏好文件：`~/.qoder/if-Studio-AI-Creation/preferences.json`——**由 agent 在用户做出选择时写入**
  （Bash `mkdir -p ~/.qoder/if-Studio-AI-Creation` 后以 Write 工具写入）；hooks 会把它注入每次会话；
  **目录随插件改名**（旧路径 `~/.qoder/if-studio-ai-expert/preferences.json` 已停用）：新路径缺失而旧路径存在时，
  先把旧文件复制到新路径再用（复制失败就直接读旧文件），老用户偏好不丢；
  文件缺失 = 用户还没做过通道选择。格式：

  ```json
  { "channel": "cli", "reason": "user_declined_connector", "decided_at": "<ISO8601 本地时间>" }
  ```

- 写入规则：

  | 时机 | 写入 |
  |------|------|
  | 对话框选「暂不授权」 | `channel=cli`（reason=user_declined_connector）——**先写偏好，再降级** |
  | 主动唤起授权页并 `ifs_ping` 复验通过 | `channel=connector`（reason=connector_authorized） |
  | 对话框选「已完成连接器授权」且 `ifs_ping` 复验通过 | `channel=connector`（reason=connector_authorized） |
  | 用户后续变更（自行授权切回连接器 / 明说改用另一通道） | 更新为对应值——**有变更及时更新**，保持记录与实际一致 |
  | 选「取消任务」 | 不写（未做出通道选择；下次遇到同一情形**仍会询问一次**） |
  | 连接器不可用时的自动降级 | **不写**（临时降级≠改选择，偏好保持原值） |

- 分流：**始终优先连接器，只有连接器不可用才降级**——连不上时先**主动唤起授权页**（上节），
  唤起不可用或仍未授权再查偏好：
  偏好=cli → **不再唤起、跳过对话框，直接走 §4 降级，不再询问**；
  偏好=connector → **同样跳过对话框**，直接走降级并如实说明（唤起已试过；连接器暂不可用、可能授权过期；
  需要恢复时按 §4.4 提示重新授权）；**降级≠改选择：自动降级不写偏好**；
  偏好缺失（从未做过通道选择）→ 唤起失败后才弹下方三选一——**唯一一次「如何运行」询问**。
- 连接器可用的任何时候都优先连接器（偏好此时不生效；若偏好=cli 而 `ifs_ping` 通过，
  顺手更新为 connector，保持记录与实际一致）。
- **兜底**：若某次会话未注入偏好段（hook 异常等），agent 在门禁处**直接读该文件判定**（路径与格式如上，
  文件很小）；判定结果与注入口径一致。
- **重置**：用户想恢复主动询问（重新三选一），删除该文件即可（`rm ~/.qoder/if-Studio-AI-Creation/preferences.json`，
  或让 agent 代删）——删后回到"未设置"分流；连接器可用时本机制整体不生效，用户随时可通过授权
  自行切回连接器（授权后下次门禁复验即切回，偏好随手更新）。

**三选一对话框（唯一一次「如何运行」询问——唤起授权页不可用且从未做过通道选择时的第一响应；推荐激活连接器、也支持先用 CLI 运行；SKILL.md §5 同一口径）**：
门禁失败（`mcp_list` 查不到 ifs 方法 / 401）、**唤起授权页不可用或仍未授权**且无偏好记录后**先停下，不自行降级**——先在回复里给出**具体执行步骤**（下方
引导正文，让用户知道每一步点哪里），再用 Qoder 问卷式提问交互（AskUserQuestion 一类宿主提问
工具，与 A2UI 收集同一机制）弹出三选一对话框，由用户直接选择。
**花括号 = 平台配置占位符**（单一来源 config/platform.json，经会话启动注入；注入缺失时自读该文件，
SKILL.md §1「配置读取兜底」；输出给用户前替换为注入值，勿原样输出花括号）：

> IFS 连接器还没完成授权，接下来的两步需要您本人完成：
> 1. 打开 {host.name}「{host.connector_entry}」，找到 **iconfont-ifs**（if Studio 智能设计）条目，点「{host.authorize_button}」
>    ——浏览器会打开 IFS 授权页（授权页第 2 步已自动弹出，无需手动输地址——平台域名随对内/对外版本不同，不向用户提供具体地址）；
> 2. 用您的 IFS 平台账号登录，核对账号无误后点「**同意授权**」；完成后回来说一声，
>    或直接在下面的选择框里选「已完成连接器授权」，我立刻复验并接着做。
>
> 授权页的登录与同意必须您本人点，我不能代替您登录或点授权。
> 注意：连接器列表里**找不到 iconfont-ifs** = 插件未安装或装后没重启 {host.name}（连接器列表是启动快照），
> 重启后再找；授权持久，复验通过即切回主通道继续创作。

| 用户选择 | 处置 |
|---------|------|
| 已完成连接器授权 | 宿主连接器管理工具可用时先 `action=retry`，再复验 `ifs_ping`：通过 → 切回主通道继续任务；仍不可见 → 按判定链排查（平台常驻服务 / 重启 Qoder → [exception.md](exception.md) §1），排查后**再次弹出本对话框**供用户重新选择 |
| 暂不授权 | **先写偏好**（上节「通道偏好记忆」，channel=cli）→ 立即走 §4 降级（官方 ifs CLI）继续任务；本次会话不再重复弹窗、**跨会话也不再询问**（偏好=cli 时直接降级、不弹框），过程中不反复劝授权 |
| 取消任务 | 停止任务：不降级、不重试；**简要介绍插件能力与使用场景**（口径 → [brand.md](brand.md)，两三句即可），告知"有需要随时发起任务；想用完整能力时随时按上面步骤授权"即可收尾 |

- 授权页的登录与同意永远由**用户本人**操作：授权页可由助手**唤起**（上节），但严禁代点提交、代选身份、代输账号；
  也不代替用户走完 OAuth（实测限定名引用 / PKCE 代走均不可行，见 CONNECTORS.md）。
- **唯一一次询问**：对话框只在"连接器不可用**且从未做过通道选择**"时出现；任一选择（授权/暂不授权）
  写入偏好后，本会话与跨会话都不再询问（偏好=cli 时直接走降级）；「取消任务」=未作答，下次遇到
  同一情形仍会询问一次；复验仍失败的重弹仅限「已完成连接器授权」分支（排查后供用户改选）。

## 4. 降级通道（官方 ifs CLI — 首选内置 MCP 直通）

降级通道 = 官方 `ifs` CLI（平台分发的单二进制，零依赖，全局命令）：用户在 §3 对话框选「暂不授权」、
授权异常或连接器不可用时，agent 经 Bash 调用 CLI 继续完成任务。CLI 已内置 `mcp` 子命令，**把连接器的同一套
工具面搬到命令行**（同工具名、同 snake_case 参数、同返回结构），因此降级期**不再需要能力翻译**——
§2 / chat.md 的主循环口径原样复用，只把「调用 `ifs_xxx`」换成「`ifs mcp call ifs_xxx`」。
原生命令（`canvas run` / `canvas poll` 等）保留为**便利 / 兜底层**（§4.3）。
管理查询类（画布历史 / 资产 / 灵感 / 算力充值）两通道都以实时方法面为准，无对应方法 → 按各模块口径
**如实提示「功能尚未就绪」**，**不编造**（有无以 `ifs mcp tools --json --profile {cli.profile}` 与 `ifs <命令> --help` 实测为准，
细则 → asset.md / user.md / help.md）。主通道可用时永远优先走连接器。

> **CLI 环境绑定（硬规则，先于本节所有命令）**：CLI 一律连线上服务——`{cli.registry}`、`{cli.profile}` 取自
> config/platform.json，**预发包里的 CLI 也打线上**，不跟画布/连接器切预发。CLI 默认用机器上的
> `config.current` profile（可能是别处登录的预发环境），所以**每条 CLI 命令都显式带 `--profile {cli.profile}`**；
> 降级开始与终端等待循环前用 `ifs auth status --json` 核对 `profiles[<profile>].registry` 与 `{cli.registry}`
> 一致（该 profile 不存在 / registry 不符 → 按 §4.1 重新登录线上，登录页用户本人操作），
> **不得拿 `current` 的 profile 顶替，也不得把它的 registry 当作插件所处环境**。

> **术语边界（勿与降级混用）**：本节所说"MCP 直通 / 降级"专指**连接器不可用时整条链路改由 CLI 承接**这一件事。
> §4.2 末条的**终端等待循环**虽然复用同一条 `ifs mcp call` 命令，但它发生在连接器正常工作时，只是把"等"
> 收进一次调用，**不是降级、不改偏好**；两套话术的对外口径 → chat.md「对话呈现」"通道术语不进对话"。

### 4.1 接入（首次使用，只做一次）

1. **安装与更新**：`command -v ifs` 检测；缺失则按平台安装（**多平台**，地址取 config/platform.json
   的 cli 段，经会话启动注入；本模块花括号 = 平台配置占位符，输出给用户前替换为注入值，同 §3 口径，
   勿原样输出花括号、勿写死；装完用 `ifs --version` 验证——打印版本号即成功）：
   - macOS / Linux：`curl -fsSL '{cli.registry}{cli.install_path}' | bash`
   - Windows（PowerShell）：`irm '{cli.registry}{cli.install_path_windows}' | iex`

   macOS / Linux 装在 `~/.local/bin/ifs`，不在 PATH 就 `export PATH="$HOME/.local/bin:$PATH"`。
   **版本门禁**：MCP 直通需要 `ifs mcp` 子命令（实测 0.16.0 提供）——`ifs mcp --help` 报 unknown command
   先 `ifs update`，仍没有才退到 §4.3 便利层。
   **CLI 安装不成功**（下载失败/网络受限等）→ 不硬走 CLI：**本任务仅能经连接器完成授权和执行**——
   按 §4.4 提示用户授权连接器（单点请求，不弹选项）。
   **每日一次 `ifs update`**（标记文件 `~/.ifs/.last_update`
   记录日期，当天已更新则跳过；更新失败不阻塞流程）——CLI 迭代频繁，过期版本可能工具面对不上
   或行为异常（报 unknown command / unknown flag 时先更新再重试）。
2. **登录（OAuth——MCP 直通只认它；与连接器授权同节奏：先授权 → 提示用户 → 停下等确认 → 复验 → 再执行）**：
   降级开工前先跑第 3 步的 `ifs_ping` 校验；**返回 `pong` 就直接执行、不发起登录**；
   未登录 / 401 / OAuth 失效 / 该 profile 不存在时才登录，且必须按下面的节奏执行：

   - 先清掉旧 Token 环境变量，再显式用 `--oauth` 发起登录（该命令会打开系统浏览器并等回调，
     **以后台方式执行**，否则前台阻塞期间无法与用户对话）：

     ```sh
     unset IFS_TOKEN
     ifs auth login --oauth --registry {cli.registry}/ --profile {cli.profile}
     ```

   - **发起后立刻回复并停下等确认**：只说「登录页已经帮您打开，请用 IFS 账号登录并点同意，完成后回我一句」，
     然后停下——**用户确认前不发消息、不轮询、不做任何 IFS 调用**；登录页在**系统浏览器**里完成
     （不是会话内置浏览器，助手不介入该页面），账号、身份与「同意」永远由用户本人操作
     （不代点、不代选、不代输账号）。
   - **用户回来说完成后**再调 `ifs_ping` 复验：`pong` → 继续原任务（授权持久，后续不再打断）；
     仍不通 → 先核对 profile / registry 与 config 一致（可能登录落到了别的 profile），请用户确认后
     **最多再发起一次登录**；两次仍不通 → 按 §4.4 说明卡点，不反复拉登录页。
   - 登录命令退出码为 0 **不等于**链路可用（只代表本地回调完成），一律以 `ifs_ping` 返回 `pong` 为准。

   `--oauth` = OAuth2 授权码 + PKCE（残留 `sr_` 旧 Token 的 `IFS_TOKEN` 会让直通直接报错：
   「MCP 需要 OAuth2 access token…IFS_TOKEN 若仍为 sr_ 请先移除」，退出码 1）；
   `--registry` = config cli.registry（**固定线上，与包所处环境无关**：外网 ifs.iconfont.cn、内网 ifs.alibaba-inc.com）；
   profile 的站点决定 `ifs mcp` 打哪个环境，所以登录必须显式带这两个值、不跟画布域名走；
   `--profile` = config cli.profile（**随发布版本注入，勿写死**：内网版=`mcp-canvas-inc`、外网版=`mcp-canvas`，
   由 scripts/build.sh 按版本写入 config/platform.json 的 cli.profile，会话启动注入后在此取值）；
   多账号再用 `--profile <name>` 区分、`ifs auth switch <profile>` 切换（环境变量 `IFS_PROFILE` 同效）；
   登录成功后 CLI 的 `current` 会切到该 profile，但**后续每条命令仍显式带 `--profile`**（机器上可能还有预发等其它 profile）；
   CLI 自动打开浏览器，**登录页由用户本人操作**（CLI 只在本地等回调，不碰账号密码；`--no-browser`
   只打印授权地址，仍需本人浏览器完成）；凭据默认存系统 keyring（`--credential-store file` 是显式明文，
   非必要不用）；撤销某次登录：`ifs auth logout --profile <name>`。
3. **校验**：`ifs mcp call ifs_ping --args '{}' --profile {cli.profile}`——返回 `pong` + `user` + `scopes` 即授权与链路真的可用
   （**降级期以此为准**）；`ifs auth status --json`（profile / registry / token 在位）、`ifs doctor --json`
   （环境/认证/网络全貌）只作补充诊断，两者都只输出状态、不输出令牌。

### 4.2 MCP 直通（降级首选：同工具面 · 同参数 · 同返回）

**连接器调用 ⇄ 降级命令是一一对应的同一件事**：`ifs_canvas_create { … }` →
`ifs mcp call ifs_canvas_create --args '{…}' --profile {cli.profile}`，参数名与返回字段都不变（下表为本期锚点，
方法面以 `ifs mcp tools --json` 实时为准，本文不维护硬数量）。

| 环节 | 降级命令 |
|------|---------|
| 协议连通 | `ifs mcp ping --profile {cli.profile}` |
| 探活 `ifs_ping` | `ifs mcp call ifs_ping --args '{}' --profile {cli.profile}`（返回身份与 scope） |
| 工具面与参数 schema | `ifs mcp tools --json --profile {cli.profile}`（= 连接器的 tools/list：工具名 + 完整 inputSchema） |
| 发消息 / 续聊 / 中断答复 `ifs_canvas_create` | `ifs mcp call ifs_canvas_create --args-file create.json --profile {cli.profile}`（`prompt` / `model` / `skill` / `media_url` + `media_type` / 续聊成对传 `canvas_id` + `session_id` / 表单回填带 `response_blocks`） |
| 等回复 `ifs_canvas_poll` | `ifs mcp call ifs_canvas_poll --args-file poll.json --profile {cli.profile}`（`session_id` 必填、`canvas_id` 可选、`timeout_seconds` 1-55） |
| 上传素材 `ifs_canvas_upload` | `ifs mcp call ifs_canvas_upload --args-file up.json --profile {cli.profile}`（三通道任选其一：`upload_id`（票据直传，首选）/ `data_base64` + `filename`（小图兜底）/ `url` 转传；返回的参考媒体 URL 即 create 的 `media_url` 取值） |
| 本地直传票据 `ifs_canvas_upload_ticket` | `ifs mcp call ifs_canvas_upload_ticket --args-file tk.json --profile {cli.profile}`（`filename` 必填）→ 取返回的 `command` 在本地执行 curl 拿 `data.upload_id`；**实时方法面没有该方法**（`ifs mcp tools --json` 核对）→ 退 `data_base64` / `url` 通道，或用便利层 `--image` 本地直传（§4.3） |
| 模型清单 `ifs_canvas_models` | `ifs mcp call ifs_canvas_models --args '{}' --profile {cli.profile}`（仍取 `name` 字段） |
| 算力余额 `ifs_balance` | `ifs mcp call ifs_balance --args '{}' --profile {cli.profile}`（无入参；**只在 create / poll 返回算力不足时复核余额用**，判定口径 → user.md；实时方法面没有就按 `quota_info` 兜底） |
| 画布授权链接 `ifs_canvas_authorize` | **实时工具面里有就同名 `mcp call`**（同样带 `--profile`）；没有 → 直接打开标准形态画布地址，落点按 screen.md「3. 落点三判」请用户本人操作一次 |

**调用约定**：

- **执行与呈现与连接器同口径（降级不豁免）**：降级只换调用形式，不减少任何呈现步骤——
  `created` 后同样**必须用会话内置浏览器打开画布页**（硬门禁，chat.md 阶段 ① 步骤 2）：
  地址同样整形（去 `sessionId`、补标准后缀），实时方法面有 `ifs_canvas_authorize` 就同名
  `ifs mcp call` 换 `login_url` 再导航，没有就直接打开标准形态画布地址；落到登录页按
  screen.md「落点」停手等用户本人登录。**CLI 的 OAuth 登录态与内置浏览器的网页登录态相互独立**——
  CLI 已授权不代表画布页已有登录态，落到登录页是正常分支，请用户本人登录一次即可（不要因此重复发起 CLI 登录）。
  轮询节奏、进度转述、A2UI / ask_user 问卷、产物落盘与验收与连接器逐项一致。

- **每条命令带 `--profile {cli.profile}`**（默认取 `config.current`，不带就会落到机器上上次登录的环境）；
  `--registry` 只在登录时用；**CLI 降级后不跨环境续聊**（预发包的画布/连接器在预发，CLI 提交到线上，
  两者产物与画布 ID 不互通，按本会话首次 create 的通道继续到底）。

- **参数走文件**：`prompt` 含中文、引号、换行，或要提交 `response_blocks` 数组时，**一律写 JSON 文件用
  `--args-file <path>`**（`-` = stdin），别在 shell 里拼 JSON（转义易错，还会把用户原文吃掉）；简单参数用 `--args '{…}'` 即可。
  写文件时 **`prompt` 用 Write 工具直接写完整原文**（JSON 字符串里的换行写成 `\n`，别用 heredoc 手拼），
  提交前 `wc -c` / 回读一眼确认整段没被截——降级期最常见的失真就是把长文案摘成摘要。
- **stdout 是 MCP envelope**：`{"content":[{"type":"text","text":"<业务 JSON>"}]}`——**解析两层**
  （先取 `content[].text`，再按 JSON 取 `status` / `media` / `message` / `canvas_url` …），
  业务字段与连接器返回完全一致；stderr 只有 `Error:` 行，不参与解析。
- **失败退出码非 0**（实测 1）：`Unknown tool: <name>`（-32602）= 方法不在当前工具面 → 先 `ifs mcp tools --json`
  核对名字，**不要改名反复重试**；参数不合法 / 缺必填实测也落 -32603 `Internal error` → 核对参数后原样重试一次，
  仍失败按 §4.4 / exception.md 处置（与连接器的 -32603 重试口径一致）。
- **未完成只回 `in_progress`**：继续调用同一会话，不调大等待（SKILL.md §3 原则 2）；`ifs mcp --timeout`
  是**命令总超时**（默认 6m，可 `--timeout 90s`），与工具参数 `timeout_seconds`（单次等待 1-55）是两件事。
  **但 `session_id` 错时 poll 不报错，同样回 `in_progress`**（2026-11-03 实测：不存在的 `session_id` 也回
  `poll_again=true`，永远不会自己结束）——`session_id` 只取本次 `create` 返回的原值，判死与收尾 →
  chat.md 阶段 ②「轮询不会自己结束」；`polls` / `elapsed_seconds` 是**单次调用内部**的轮询次数与耗时，不是任务进度。
- **终端等待循环**（长任务把多轮 poll 收进一次 Bash 调用，§1 与 chat.md 阶段 ②「轮询节奏」对策 ③）：
  用 `ifs mcp call ifs_canvas_poll` 在 shell 里 `while` 循环等待同一会话，绕开宿主的重复调用保护——
  **连接器通道下同样可用，但它只换"等"的调用形态，不改主通道、不是降级**：发消息 / 上传 / 答复中断仍走连接器，
  不写偏好、不对用户播报（话术边界 → chat.md「对话呈现」）。本机已有**与 `{cli.registry}` 一致**的 OAuth profile 时才用
  （`ifs mcp call ifs_ping --args '{}' --profile {cli.profile}` 返回 `pong`；不满足就用轮换 timeout 那两条）：`while` 里反复
  `ifs mcp call ifs_canvas_poll --args-file /tmp/ifs_poll.json --profile {cli.profile}`，用 python3 解 `content[].text` 取
  `status` / `progress` / `message` 逐轮打印，命中终态 `exit 0`、预算用尽 `exit 2`（再来一次同样的循环，
  但累计等超经验上限或 `progress` 一直为空就要判死停手）；
  单轮 `timeout_seconds: 50` × 预算 100 秒，**并把这次 Bash 调用的超时给到 3 分钟**（宿主默认 2 分钟先掐）。
  脚本形态 → chat.md 阶段 ②「轮询节奏」对策 ③。**循环里只 poll，绝不重复 `create`**。
- **落盘同连接器**：done 回 `media[].url`（图片/视频/音频）或文本/其他素材内容，用 Bash 下载/写入到工作区 `outputs/`（§4.3 便利层的 `--save-dir` 才自动落盘）。

> 实测 2026-10-22（同一个 OAuth profile 跑完整链路）：`ifs_ping`（`pong` / user / scopes）→
> `ifs_canvas_create`（新画布 `status=created` + `canvas_id` / `session_id` / `canvas_url`）→ poll `in_progress`
> （49 秒，带 `message`）→ poll `done`（`media[].url` 图片 + `markdown` + `canvas_url`）；
> 同画布**续聊**（成对传 `canvas_id` + `session_id`）返回 `status=submitted` + `baseline_msg_count`，
> 后续 poll 照常出现 `summary_feedback`（A2UI 中断，带 `message`）与 `done`——**中断态与连接器同一表达方式**，
> chat.md 阶段 ②-④ 的分支不用改；`ifs_canvas_upload` 以 `data_base64` 上传本地小图返回 `file_id` + `url`。
> 字段与语义与连接器逐项一致（仍以实时返回为准，别照抄本文猜字段）。
>
> **上传返回字段以实时 JSON 为准**：历史实测 base64 通道给 `file_id` + `url`，票据链的方法描述口径是
> 换取 `media_url`——取哪个字段看当次返回，**别照本文猜**；拿不到 URL 就是上传没成功，按 §1 -32603 重试口径
> 与 [exception.md](exception.md) §3 处置，**不编 URL、不把本地路径直接传给 create**。

### 4.3 原生命令便利层（`ifs canvas run` / `canvas poll` / `models` / `upload` / `doctor`）

只在两种情况下用：**① MCP 直通不可用**（CLI 过旧没有 `mcp` 子命令且 `ifs update` 无效）；
**② 便利层独有能力**——`--save-dir` 自动落盘、`--image` 本地路径直传、`--timeout <秒>` 单条命令长阻塞、
`ifs doctor` 链路诊断。**便利层命令同样带 `--profile {cli.profile}`**（环境绑定与 §4 开头硬规则一致）。

> **凭据分道（2026-10-22 实测，别踩坑）**：原生 `canvas run` / `canvas poll` / `upload` / `models` 走的是
> **旧 Token 通道**（认 `IFS_TOKEN` 环境变量或 `--legacy` 登录的 token），`ifs mcp` 走 **OAuth 通道**。
> 用 `--oauth` 登录的 profile 跑原生命令实测一律 401，报错文案还有误导（「Token 可能已过期，请运行 ifs auth login」）。
> **原生 401 ≠ CLI 不可用**——按 §4.2 改走 MCP 直通即可继续任务，**不要反复让用户重新登录**，
> 更不要因此触发 §4.4 反向升级；确实要用原生命令，按其 `--help` 以 `--legacy` 方式登录该 profile。
> `ifs doctor` / `ifs auth status` 在 OAuth profile 下正常（只报状态，不走旧业务端点）。

便利层沿用口径：

- **两阶段**：`canvas run --create-only` 立即返回 `status=created` + `canvas_id` / `session_id` /
  `canvas_url`（立即呈现画布链接——去掉 `sessionId`、在 `?` 后整串补齐标准后缀 `{canvas_link.query_suffix}`，见 §1 / screen.md「4. 地址来源」——
  并存 ID）→ `canvas poll` 阻塞到完成；简单场景可一步直跑。
- **多词 flag 一律 kebab-case**（`--canvas-id` / `--save-dir`），严禁下划线（报 unknown flag）。
- **交互态是正常分支（exit 0，非错误）**：每轮 poll / run 返回的 `message` 有新内容就即时原意转述到
  对话框（去重）；`summary_feedback` → **先在对话框转述** `planning_text` + 建议编号列出，再续聊发送确认
  （**严禁重复轮询**）；`ask_user` → **先在对话框呈现表单标题/说明/字段**，再按 §4.2 create 行回填表单
  （便利层写 form.json 走 `--response-blocks-file`）；`done` → 先回显 `message` / 总结再呈现产物；
  `quota_exceeded` → **先查余额复核**（`ifs mcp call ifs_balance --args '{}'`，判定口径 → user.md）再决定：
  不够 → 转述配额提示 + 充值入口，不重试；够 → 原会话续聊继续；
  `timeout` → **不是终态**：加大 `--timeout` 续 poll 原会话直到 done / 出错 / 配额 / 取消；
  不重复发消息、不提前结束、不问用户是否继续等。
- **本地文件**：主通道与直通层的参考素材都**必须先上传取 URL 再进 create**（chat.md 阶段 ①「上传前置」，
  严禁本地路径直传 create）；本地文件优先票据直传链（§1 / §4.2，直通工具面没有票据方法时小图退 `data_base64`）；
  便利层的 `--image` 可直传本地路径自动上传（本地路径或 URL 均可；
  图片与常见视频格式，等同先上传后提交），单独拿 URL 用 `ifs upload`（注意同样受上面的凭据分道约束）。
- **落盘**：便利层 `--download` 默认 true，`--save-dir` 传工作区 `outputs/` 的绝对路径（与主通道默认目录一致，
  自动落盘，`downloaded[].local_path` 即本地文件）；`media` / `planning_text` / `response_blocks` 等
  结果字段解析与主通道 §1 口径一致。
- **模型清单字段两套**：直通/连接器的 `ifs_canvas_models` 用 `name`；原生 `ifs models --json` 用
  `display_name` / `id`（且带本地缓存，可能在 401 提示行后仍吐缓存）——**降级期统一走直通取 `name`**，
  别把两套字段混用。
- 参数细节拿不准跑 `ifs <命令> --help`（如 `ifs canvas run --help`、`ifs mcp call --help`）。

### 4.4 反向升级：CLI 无法完成而连接器可完成时

CLI 降级使用期间（偏好=cli 用户，或偏好=connector 而连接器不可用时的自动降级），
CLI 跑得通就一直用到底；一旦 **CLI 无法完成任务**——
未安装且装不上（网络受限等）、OAuth 登录回调走不通（`ifs mcp call ifs_ping` 都起不来）、
持续报错（未知命令/版本缺陷且 `ifs update` 无效）、
或该能力 CLI 确实没有（`ifs mcp tools --json` 与原生命令都没有）——而任务本身**连接器通道可以完成**时
（**原生便利层报 401 而 MCP 直通可用不算无法完成**，换直通继续即可，§4.3 凭据分道）：

1. **停下，不硬撑**：向用户说明卡点（哪一步、什么表现）+ 替代路径（"这一步经连接器可以完成"）。
2. **提示恢复（重新授权）连接器**：输出 §3 同款引导正文（宿主入口、授权按钮、用户本人点同意——绝不代点），
   **但不弹三选一对话框**——这是单点授权请求，不是通道重选。
3. 用户授权后：`ifs_ping` 复验 → 通过则切回连接器继续本任务（ID 通用，直接续聊），
   并把偏好更新为 connector；用户拒绝 → 报阻塞结论 + 给替代建议（管理查询类如实提示功能尚未就绪），不纠缠。

频次：同一任务至多提示一次；不打扰原则与 §3 一致。

## 5. 与主通道的关系（ID 通用 · 不来回切 · 恢复）

- ID 通用：降级期间拿到的 `canvas_id` / `session_id` 与连接器通道完全互通，
  连接器恢复后直接切回 iconfont-ifs 续聊，无需迁移。
- 两套凭据相互独立：CLI 登录态（OAuth token 存系统 keyring，旧 Token 在 `~/.ifs/config.json`）与
  Qoder 连接器托管的 OAuth 互不影响——连接器失效不影响 CLI，CLI 登出也不动连接器。
  CLI 内部还分两条通道：**MCP 直通用 OAuth**、**原生命令用旧 Token**（§4.3 凭据分道），
  所以「原生 401」不代表降级通道失效。
- 同一次任务内**不要两通道来回切换**（选定一条跑到 done；§4.4「CLI 干不了换连接器」的反向升级
  是确有必要且已告知用户的例外）。
- 连接器授权恢复后：回门禁复验（`ifs_ping`）→ 切回 iconfont-ifs 通道继续（降级期间产生的
  canvas_id / session_id 同样有效，续聊沿用即可）。

**红线**：`~/.ifs/config.json` 含访问令牌——**不 cat、不读取、不外传**（插件 Bash 守卫已加拦截；
查授权态只用 `ifs auth status`）；IFS 登录页与连接器授权页永远用户本人操作；
充值仍只给入口，支付永远用户本人完成。
