#!/bin/sh
# ifs-suite-hook.sh — if Studio AI 智能创作（if-Studio-AI-Creation）插件 hooks 入口
#
# 用法（由 hooks/hooks.json 调用，不手工执行）：
#   ifs-suite-hook.sh session-start   SessionStart  → 注入模块地图与连接器约定
#   ifs-suite-hook.sh guard            PreToolUse:Bash → 拦截凭据外泄/状态破坏（可阻断）
#   ifs-suite-hook.sh audit            PostToolUse  → 异步落审计（非阻断）
#
# 契约：stdin 收 JSON；退出码 0 放行 / 2 阻断 / 其他非阻断错误。
# 设计原则：fail-safe —— hook 自身故障一律放行，绝不因自身问题挡住用户；
#           但窄规则（凭据外泄 / 状态破坏）命中时仍阻断，且不依赖外部命令。
# 载体（跨系统，0.11.10）：hooks.json 以 shell 形态经 bash -c 调 polyglot 入口
#           ifs-suite-hook.cmd（cmd/sh 双语，模式同官方 qodersec-launch.cmd）——
#           类 Unix 直接委派到本脚本；Windows 委派到 Git Bash 的 bash 再跑本脚本
#           （Qoder 在 Windows 的 shell 基座即 Git Bash）；找不到 bash 时排空 stdin
#           退 0 静默降级。本脚本自身只依赖 POSIX sh 内建 + /bin、/usr/bin 基座命令，
#           python3 是可选增强（三处 command -v 探测，缺失整段跳过）；
#           空 PATH / 无 HOME 实测：主体注入照常、守卫照常阻断、全程无外部命令硬依赖。
#           hooks 是增强层不是功能依赖：全部载体失效时 hook 静默不执行（非阻断），
#           配置与偏好由 agent 自读文件兜底（SKILL.md §1「配置读取兜底」）。
# 登录门禁不在 hooks：连接器走 OAuth（未授权时表现为连接器未连接 / 调用 401；懒加载宿主下会话工具
#           列表本就不含 ifs_*，判定以 mcp_list 能否列出方法为准），授权页可由助手唤起（宿主连接器管理工具），
#           但登录与同意由用户本人操作。

set -u

mode="${1:-}"
[ -n "$mode" ] || exit 0

# 没有 stdin（交互式运行）时直接放行，避免挂住
[ -t 0 ] && exit 0

# 只用 shell 内建 read 收集 stdin —— 不依赖 cat，PATH 异常时守卫依然生效
payload=''
while IFS= read -r __line || [ -n "$__line" ]; do
  payload="$payload$__line
"
done
[ -n "$payload" ] || exit 0

# 调试日志固定落盘路径，不依赖 Qoder 内部变量
state_dir="/tmp/.ifs-suite-hook"

# ---------------------------------------------------------------- 工具函数

# json_field <点分路径> —— 取 stdin JSON 里的字段；python3 不可用时退化为 grep
json_field() {
  if command -v python3 >/dev/null 2>&1; then
    printf '%s' "$payload" | python3 -c '
import json, sys
path = sys.argv[1].split(".")
try:
    node = json.loads(sys.stdin.read())
except Exception:
    sys.exit(0)
for key in path:
    if isinstance(node, dict) and key in node:
        node = node[key]
    else:
        sys.exit(0)
if isinstance(node, str):
    sys.stdout.write(node)
' "$1" 2>/dev/null && return 0
  fi
  printf '%s' "$payload" \
    | grep -o "\"${1##*.}\"[[:space:]]*:[[:space:]]*\"[^\"]*\"" 2>/dev/null \
    | tail -n 1 2>/dev/null \
    | sed 's/.*:[[:space:]]*"//; s/"$//' 2>/dev/null
}

# is_ifs_logged_in 已退役：连接器改为 OAuth（Qoder 运行时托管 Bearer），本地无 token 文件可判；
# 未授权时工具在传输层即不可用/401，插件 hook 不再做本地登录拦截。

# redact —— 审计日志落盘前抹掉疑似凭据
redact() {
  sed -e 's/sr_[A-Za-z0-9]\{8,\}/sr_<redacted>/g' \
      -e 's/\([Bb]earer[[:space:]]\{1,\}\)[A-Za-z0-9._-]\{12,\}/\1<redacted>/g' \
      -e 's/\([Aa]uthorization:[[:space:]]*\)[^"'"'"']*/\1<redacted>/g'
}

log_line() {
  if mkdir -p "$state_dir" 2>/dev/null; then
    printf '%s event=%s %s\n' "$(date -u '+%Y-%m-%dT%H:%M:%SZ' 2>/dev/null || echo '-')" "$1" "$2" \
      >>"$state_dir/hook.log" 2>/dev/null
  fi
}

# ---------------------------------------------------------------- 各模式实现

case "$mode" in
  session-start)
    session_id=$(json_field session_id)
    log_line session-start "session=${session_id:-unknown}"
    # 平台配置单一来源（config/platform.json）：拼一行注入；fail-safe——缺文件/缺 python3 跳过该段，
    # 不阻塞（agent 侧兜底=自读该文件，SKILL.md §1「配置读取兜底」）
    pc_line=''
    pc_cfg="${0%/*}/../../config/platform.json"
    if [ -f "$pc_cfg" ] && command -v python3 >/dev/null 2>&1; then
      pc_line=$(python3 -c '
import json, sys, urllib.parse
try:
    cfg = json.load(open(sys.argv[1], encoding="utf-8"))
    h, p = cfg.get("host", {}), cfg.get("platform", {})
    v, c, a = cfg.get("vendor", {}), cfg.get("cli", {}), cfg.get("account", {})
    cl = cfg.get("canvas_link", {})
    dom = p.get("domain") or "未指定（以连接器注册配置 mcp.json 的 url 为准，勿写死勿向用户提供）"
    reg = c.get("registry") or "未指定（同上）"
    inst = c.get("install_path", "")
    win = c.get("install_path_windows", "")
    if win:
        inst = "%s（windows: %s）" % (inst, win)
    ver = c.get("verify", "")
    prof = c.get("profile") or "未指定（默认 profile，未区分内网/外网）"
    cli_seg = "%s（registry %s；认证 profile=%s；安装脚本路径=%s%s；CLI 恒走线上不随环境，每条命令须带 --profile；降级与 MCP 同节奏：开工前先用 ifs mcp call ifs_ping 校验，未登录/401/凭据过期就 ifs auth login --oauth 后台发起（CLI 自开浏览器）、提示用户本人登录并同意、**停下等其确认**，确认后 ping 复验通过再执行；created 后同样打开内置浏览器画布页）" % (c.get("command", ""), reg, prof, inst, ("；验证=%s" % ver) if ver else "")
    # 标准后缀现场拼装：fixed_params + 编码 title + from；配置文件不存后缀/编码副本（副本必漂移）
    title_q = urllib.parse.quote(cl.get("title", ""))
    suffix = "%s&title=%s&from=%s" % (cl.get("fixed_params", ""), title_q, cl.get("from", ""))
    print("平台配置（单一来源 config/platform.json，改后重启生效）：宿主=%s；连接器入口=%s；授权按钮=%s；平台=%s（%s）；平台域名=%s；品牌出品=%s（%s）；降级CLI=%s；CLI 登录=ifs auth login --oauth --registry <registry> --profile <认证 profile>（registry/profile 同上，随发布版本注入，勿写死；登录与调用均走线上，不复用机器上的 current profile）；画布链接标准后缀 query_suffix=%s（拼画布地址时整串照抄接在 ? 后，不逐参数重拼、不抄写字面值；后缀 = 平台口径固定参数组（隐藏会话面板/左侧栏/顶栏 + 顶栏操作 + 画布交互开关，取值以本注入为准）+ title=标题明文的 URL 编码值 + from=流量归因来源标注；文件只存组件明文（canvas_link.fixed_params/from/title），编码与拼接由 hook 现场计算，改配置重启即全链生效；链接里 title 只能用编码值，带空格/中文的明文会截断 Markdown 链接）；账号=%s" % (h.get("name", ""), h.get("connector_entry", ""), h.get("authorize_button", ""), p.get("name", ""), p.get("display_name", ""), dom, v.get("name", ""), v.get("site", ""), cli_seg, suffix, a.get("note", "")))
except Exception:
    pass
' "$pc_cfg" 2>/dev/null | tr -d '"')
    fi
    # 通道偏好（~/.qoder/if-Studio-AI-Creation/preferences.json）：用户对「连接器/CLI」的明确选择，跨会话记忆；
    # 目录随插件改名（if-studio-ai-expert → if-Studio-AI-Creation）：新路径优先，新路径缺失而旧路径存在时
    # 复制一份到新路径（迁移失败就继续读旧文件），老用户偏好不丢；fail-safe——缺文件/缺 python3 跳过该段
    pref_line=''
    pref_dir="${HOME:-}/.qoder/if-Studio-AI-Creation"
    pref_cfg="$pref_dir/preferences.json"
    legacy_cfg="${HOME:-}/.qoder/if-studio-ai-expert/preferences.json"
    if [ ! -f "$pref_cfg" ] && [ -f "$legacy_cfg" ]; then
      if mkdir -p "$pref_dir" 2>/dev/null && cp "$legacy_cfg" "$pref_cfg" 2>/dev/null; then
        log_line migrate "preferences=legacy-to-new"
      else
        pref_cfg="$legacy_cfg"
      fi
    fi
    if [ -f "$pref_cfg" ] && command -v python3 >/dev/null 2>&1; then
      pref_line=$(python3 -c '
import json, sys
try:
    cfg = json.load(open(sys.argv[1], encoding="utf-8"))
    ch, at = cfg.get("channel", ""), cfg.get("decided_at", "")
    if ch == "cli":
        print("通道偏好（~/.qoder/if-Studio-AI-Creation/preferences.json，用户已选定且跨会话记忆）：连接器不可用时直接走官方 ifs CLI——**不弹三选一对话框**；连接器一旦可用（ifs_ping 通过）永远优先连接器，并把偏好更新为 connector；仅当 CLI 无法完成任务而连接器可完成时，再提示用户授权连接器（SKILL.md §5）；决定时间=%s" % at)
    elif ch == "connector":
        print("通道偏好（同上）：用户已选定连接器（决定时间=%s）——连接器不可用时**不弹三选一**（选择已记录、不再询问），但**先唤起一次授权页**（宿主有 mcp__qoder-settings__manage_app_mcp 时取 iconfont-ifs 的 serverId 调 action=authorize，用户在浏览器完成登录同意后 action=retry + ifs_ping 复验，通过即继续；不紧跟 retry、同一任务不反复唤起），唤起不可用或仍未授权直接按降级承接（CLI）继续并向用户如实说明（唤起已试过；可能授权过期；降级≠改选择、不写偏好）；仅当 CLI 无法完成任务而连接器可完成时，再提示用户恢复（重新授权）连接器（SKILL.md §5）" % at)
except Exception:
    pass
' "$pref_cfg" 2>/dev/null | tr -d '"')
    fi
    additionalContext="${pc_line:+$pc_line }${pref_line:+$pref_line }「if Studio AI 智能创作」插件已启用（多技能模式：通用技能 ifs-ai-design + 26 个 IFS 技能中心专业技能）。通用技能负责通用任务执行与专业技能的任务代理；专业技能（故事板生视频、视频深度重拍、视频抽帧、商品创意图、商品套图、商品图文笔记、服饰试穿、试穿戴、服饰套图、服饰图文笔记、数字人形象生成、数字人口播视频、矢量图标、图片编辑、语音合成、音乐生成、语音ASR识别、服饰展示、SKU图、商品外观展示广告、商品图文视频、内容种草短视频、造型改造、图片/视频转GIF工具、视频添加字幕、视频裁剪）只准备专项业务规则与素材、并指定 skill 参数值，具体任务提交与执行一律转通用技能 Chat 主循环，发消息时 skill 参数带对应专项技能名（多技能架构、代理协议与专业技能索引见技能 references/pro-skills.md）；**技能匹配硬门禁（先专项、后通用）**：收到请求先按技能 SKILL.md §0 判定表匹配专业技能，命中就先用 Skill 工具激活对应专业技能、读它的 SKILL.md 再执行，未完成该判定前不得探活、查模型清单或发消息；只有未命中才由通用技能直接承接（视频生成一律先走「故事板生视频」；未命中任何技能的生图请求同样由通用技能发消息到平台生成、不带 skill，禁止在本地用 HTML/CSS/Canvas/绘图库排版或浏览器截图自行出图）。任何图像/视频生成、改图、导出、算力资产、品牌口径需求都优先走该插件技能，模块细则在技能 references/ 内。连接层为 iconfont-ifs 连接器（MCP over HTTP + OAuth，插件 mcp.json 注册的 IFS 平台远程 MCP 服务），方法面以会话内实时 tools/list 为准（智能体对话 + 画布授权链接 + 灵感案例查询 + 探活）。**会话内调用形式（首次 IFS 调用前先发现一次，早于探活与业务调用）**：工具表里只有 mcp_list / mcp_get / mcp_call（Qoder 实测懒加载常态）→ 先 mcp_list（keyword 传 ifs）或宿主工具搜索发现方法，拿实时全限定名并在本会话复用，再 mcp_call 传平级 toolName + arguments；工具表里已经有一等工具 mcp__…__ifs_x 才直调（参数摊平）。**全限定名只取实时发现结果，不照本文或记忆拼**：前缀随插件名派生（形如 mcp__plugin_<插件名>_iconfont-ifs__方法名），名字不对或工具未载入都只会报 Tool not found / No connected MCP server offers …；遇到就立刻回发现入口取实时名重发，不按同名重试、不猜别名。直调的参数对象只能用本方法自己的字段（字段以当次 schema 为准）：create=prompt/media_url/media_type/model/skill/canvas_id/session_id/response_blocks；poll=session_id/canvas_id/timeout_seconds；upload=url/data_base64/filename/upload_id/canvas_id；upload_ticket=filename/size_bytes/canvas_id；canvas_list=keyword/limit/cursor；assets=file_type/source/limit/cursor（不收 canvas_id）；inspirations=tag/agent_code/limit/cursor；authorize=canvas_url；ping/models/balance 传空对象（limit / cursor / timeout_seconds / size_bytes 都是 number，别写成字符串；cursor 是页码从 1 递增；media_type 只有 image/video，传 audio 或扩展名会被拒）。跨方法借字段（如给 create 传 timeout_seconds、给 assets 传 canvas_id）会被判 params must NOT have additional properties；**arguments 与 toolName 这两个键永远不带，哪怕写成 arguments: null 也算多余字段**。这类报错请求没出本机、不扣算力：删掉多余键、业务参数摊平、原样重发同一次调用即可，不算重复发消息。只有工具名本身是 mcp_call 的元工具才用 toolName 与 arguments 平级信封（业务参数只进 arguments，不写成 tool_name；报缺 toolName 就是信封没拼对，补齐重发）；报 方法名 (… MCP Server) tool parameter validation failed 且多出来的是业务字段 = 内层参数错，实时 schema 一律不收多余字段、多一个键就被宿主拒，按实时 schema 去掉多余字段或补齐必填再重发；无入参方法（ifs_ping、ifs_canvas_models、ifs_balance）参数传空对象、不带任何过滤字段（2026-11-02 实例：给 ifs_canvas_models 传 keyword 被拒——模型清单不接受任何过滤参数，图像还是视频在返回清单里自己筛；mcp_list 的 keyword 是元工具入参，既不进业务方法参数、也不能给 ifs_ping 用）；**探活 ifs_ping 也只传空对象，它不是方法检索入口——找方法用 mcp_list 的 keyword**（2026-11-04 实例：给 ifs_ping 传 keyword=upload 被拒）；报 Tool not found / MCP tool not found = 工具还没载入本会话工具表（不是未授权、不是参数错）：立刻回发现入口（mcp_list 或宿主工具搜索）取实时名重发，不按同名重试；报 No connected MCP server offers a tool named = 这个名字此刻不在宿主已发现的 MCP 工具面里（不是参数错，也先别判未授权）：立刻用 mcp_list（keyword=ifs）复核——列得出 ifs 方法就用原名重发；整个 iconfont-ifs 都列不出 = 插件 MCP 没连上（装/改后没重启宿主、或连接器没连），按通道偏好处置（提示重启宿主/连接器连接，或降级 CLI），别改名硬试；会话工具列表里没有 ifs_* 本身不等于未授权，以 mcp_list 能否列出方法为准（细则 connector.md §1「先判调用形态」、exception.md §3）。方法清单：发消息 ifs_canvas_create（新开/续聊/中断答复三合一——续聊传画布与会话 ID，A2UI 中断续聊发送建议原文，ask_user 表单回填 response_blocks 随消息提交）；发消息前两关自查（内容关=用户提的主体、数量、画幅与尺寸、时长、画面文字原文、指定的模型与垂直技能、否定项逐项原样进消息，不改写、不丢项、不加戏、不擅自换语言，只补必需的空白维度，长文案整段提交不摘成摘要，有歧义先问不猜着发；传输关=参数名按 tools/list 实时 snake_case、model 取模型清单 name、续聊与答复中断的定位 ID 一律用台账值、prompt 一次传完整，返回 created 或 submitted 且 ID 齐全才算送达，失败原样重试同一条、绝不加发第二条内容相同或冲突的消息，细则 chat.md 阶段 ①「需求忠实」「准确送达」），等回复 ifs_canvas_poll（单次等待约 30 秒上限 55，未完成返回 in_progress 继续调用勿靠调大等待收尾——慢任务持续等到完成或出错，不提前收尾；等待节奏防拦停见下；产物经 media[].url 只把本轮新生成的落盘到工作区 outputs/，用户上传的原始素材与画布输入原图/原视频不重复下），上传素材 ifs_canvas_upload（用户上传本地图/视频/音频必须先上传取 URL 再发消息，严禁本地路径直传——本地文件首选票据直传：ifs_canvas_upload_ticket 取一次性票据（filename 必填，单文件上限 5MB），按返回的 command 在本地执行 curl（把 LOCAL_FILE_PATH 换成绝对路径、ticket 字段排在 file 之前、Windows cmd 用双引号），拿响应 data.upload_id 再调 ifs_canvas_upload 换参考媒体 URL，文件字节全程不进对话；已有远程地址走 url 转传，data_base64 只作小图兜底；票据与 upload_id 是一次性凭据，不复用、不进对话与日志），模型清单 ifs_canvas_models（name 字段唯一来源），灵感案例 ifs_inspirations（卡片四件套呈现见下「管理查询类」），画布授权链接 ifs_canvas_authorize（入参 canvas_url 传整形后的画布地址，返回 login_url 作内置浏览器导航目标），探活 ifs_ping。可用性门禁：**先发现方法面（mcp_list 或宿主工具搜索）→ 再用 ifs_ping 探活**——始终优先连接器，只有连接器不可用才降级；未发现前不拿拼出来的名字直呼。mcp_list 列不出 ifs 方法或调用 401 = 连接器未授权/授权过期（懒加载下会话工具列表本就不含 ifs_*，别据此判未授权）——先看上方通道偏好段（若有）：偏好=CLI（用户已选暂不授权）→ 不弹框、直接按 SKILL §5 走 CLI 降级；偏好=连接器 → 同样不弹框，**先唤起一次授权页**（宿主有 mcp__qoder-settings__manage_app_mcp 时：取 iconfont-ifs 的 serverId 调 action=authorize，返回 status=browser-opened 即浏览器已开；用户本人登录同意后回话，再 action=retry + 同一 serverId 并复验 ifs_ping，通过即继续；不紧跟 retry、同一任务不反复唤起），唤起不可用或仍未授权再直接走 CLI 降级并向用户如实说明（唤起已试过；连接器暂不可用、可能授权过期；降级≠改选择、不写偏好）；未设置（从未做过通道选择）→ 先按 SKILL §5 主动唤起授权页（宿主有 mcp__qoder-settings__manage_app_mcp 时：取 iconfont-ifs 的 serverId，调 action=authorize + serverId，返回 status=browser-opened 即系统浏览器已打开授权页；用户本人登录并同意后回话，再调 action=retry + 同一 serverId 并复验 ifs_ping，通过即把偏好更新为 connector 继续任务、**不弹框**；取不到 serverId 不猜不硬编；同一任务不反复唤起、不紧跟 retry），唤起不可用或仍未授权再停下不自行降级，按 SKILL §5 用 Qoder 问卷式提问交互弹出三选一对话框（唯一一次「如何运行」询问，推荐激活并使用连接器、也支持先用 CLI 运行）由用户直接选择：已完成连接器授权（复验 ifs_ping 通过即切回主通道并把偏好更新为 connector，仍不可见进判定链排查后重弹对话框）/ 暂不授权（**先写偏好 ~/.qoder/if-Studio-AI-Creation/preferences.json（channel=cli，跨会话记忆）**，再降级到官方 ifs CLI 继续任务——平台分发单二进制，**首选其内置 MCP 直通**：ifs mcp tools --json 取实时方法面与参数 schema，ifs mcp call 后接同名工具（ifs_canvas_create 发消息/续聊/中断答复、ifs_canvas_poll 等回复、ifs_canvas_upload 上传（含 ifs_canvas_upload_ticket 票据直传，票据方法在不在面内以 tools --json 实时为准，没有就退 base64/URL 通道或便利层 --image）、ifs_canvas_models 模型、ifs_ping 探活），与连接器同工具名同 snake_case 参数同返回，主循环口径不变；stdout 是 MCP 信封，业务 JSON 在 content[].text 里要解两层，失败退出码非 0（Unknown tool 先核对 tools 清单勿改名重试）；含中文/引号/数组的参数一律写 JSON 文件走 --args-file（- 表示 stdin），别在 shell 里拼 JSON；ifs canvas run/poll 等原生命令只作便利层（--save-dir 自动落盘、--image 本地直传、--timeout 长阻塞、ifs doctor 诊断）；凭据分道：原生命令走旧 Token 通道、ifs mcp 走 OAuth 通道，用 --oauth 登录的 profile 跑原生命令必 401（报错还会提示重新登录），这不是 CLI 失效——改走 MCP 直通继续，勿反复让用户登录、勿因此提示授权连接器；首次 unset IFS_TOKEN 后 ifs auth login --oauth 由用户本人操作登录页，链路校验用 ifs mcp call ifs_ping，CLI 凭据独立于连接器，接入与调用约定见 references/connector.md §4）/ 取消任务（停止，不降级不纠缠，向用户简要介绍插件能力与使用场景，有需要随时再发起）；弹框前先在回复里给出具体执行步骤（授权页优先由助手唤起；唤起不了才让用户走 Qoder 设置→扩展管理→连接器，找到 iconfont-ifs 点「授权/连接」；浏览器授权页由用户本人登录并点同意，严禁代点提交、代选身份、代输账号——**可代为唤起授权页，但登录与同意必须本人**；列表里找不到 iconfont-ifs=插件未装或装后没重启 Qoder）；对话框只在「连接器不可用且从未做过通道选择」时出现（唯一一次询问）：任一选择（授权/暂不授权）都会写入偏好、此后跨会话不再询问；「取消任务」=未选择、不写偏好、下次遇到同一情形仍会询问一次；降级期间仅当 CLI 无法完成任务而连接器可完成时，再提示用户恢复（重新授权）连接器（SKILL §5）；token 文件 ~/.ifs/config.json 含访问令牌，不 cat 不读取不外传，查授权态只用 ifs auth status 或 ifs doctor，降级链路是否真的可用以 ifs mcp call ifs_ping 返回 pong 与 scope 为准。画布历史、资产库、灵感广场、算力充值等管理查询类以会话内实时方法面为准：有对应方法就直接查、按模块口径呈现，没有才如实提示功能尚未就绪——不打开平台管理页代查、不编造数据。**算力不足（create 或 poll 返回 quota_exceeded / 提示配额、积分不足）必先复核**：经连接器查一次余额（ifs_balance，无入参传空对象）再决定——不够才提示充值（只给入口、用户本人支付、绝不代充），余额够就在原会话续聊继续，查不到余额就按 quota_info 原样转述 + 充值入口、不编造数字。**一直 in_progress 不等于任务在跑**：会话 ID 错时 poll 不报错、永远回 in_progress——连续 3 轮 message 一致且 progress 为空、或超经验上限（图 5 分钟、套图 8 分钟、视频 20 分钟）就停轮询，先用 ifs_assets（不收 canvas_id，看返回里的画布名称/链接对）核实产物：有产物直接交付，没有就说明情况并给画布链接。灵感案例（方法面内有则用，当前为 ifs_inspirations；参数 tag 分类、agent_code design 或 video、limit 默认10 上限50、cursor 翻页；返回 cards 数组，每条含 description、cover、video_url、author_name、tags、canvas_id、canvas_url）呈现红线：**每条案例一次给全四件套——描述 description 原文、示意图 cover 用远程地址内嵌渲染（本地路径在对话里不渲染，也别为展示去下载）、画布地址 canvas_url 作可点开的 Markdown 链接、作者与分类跟在描述后一行**，只列标题不给图和地址=不合格；design 卡地址按画布标准形态整串补上标准后缀、去掉 sessionId，video 卡地址用返回原值不加参（该路由本就没有面板容器，正文直接是完整流程文本，正适合打开看具体内容）；有 video_url 就是视频案例，对话里播不出来，只标形态并用封面预览；一次呈现 3~5 条，用户要更多再翻页，不把一页十条一次倒完；命中较多时平台按近期更新取样后页内排序（非全量推荐序），不说「这就是全部」；用户挑定案例后想回看完整过程，按 screen.md 先取授权链接再打开该案例页（没要求打开就只给链接）。外挂屏（内置浏览器）只用于画布页呈现（**降级期同样每次 created 都打开**；「ifs_canvas_authorize」不在实时方法面就直接开标准形态画布地址，不省画布呈现）：发消息 created 时**先取授权链接再打开**——整形后的画布地址交 ifs_canvas_authorize 换回 login_url，浏览器打开 login_url（已登录直接进画布；未登录先出主站登录页，用户本人登录一次即自动回跳该画布；取不到授权链接就直接开画布地址、不卡流程）；已有同画布标签页只复用聚焦、不重复取链；画布页自带 WebSocket 实时更新，**打开后从 created 到 done 都不要 reload**（整页重载会把用户的缩放/视图重置回平台保存值、没有新内容收益），轮询期间同样不动浏览器；画布地址统一在 ? 后整串照抄上方平台配置段注入的画布链接标准后缀（query_suffix，含平台口径固定参数组（取值以本注入的 query_suffix 整串为准，本文案不逐参数列举字面值）与 title=标题编码值、from=流量归因来源；不逐参数重拼、不拼带空格/中文的明文——会截断 Markdown 链接；输出前自检 title= 后必须是 URL 编码形态、无裸空格与中文）且**不带 sessionId**（画布页缺省即最新会话，定位会话靠 session_id 续聊；工具返回的 canvas_url 含 sessionId 就去掉、缺标准后缀就整串补上，细则 screen.md「4. 地址来源」），**地址链接只作兜底、只在面板走不通时给一次：画布页已在面板打开并正常渲染时，回复里不再附画布链接、也不单起「画布回看 / 在 if Studio 打开画布」这类入口行**；内置浏览器落到登录页/身份验证页时立即停止——不点提交、不选身份、不输账号，由用户自己点一次登录（走授权链接时登录或万相绑定、内网版引导完成后页面自己跳回画布，不要再导航第二次）。对话呈现（对用户可见）：执行任务时只向用户呈现任务进展与结果（百分比、需确认或补充的问题、产物预览、需要本人操作的步骤、异常的结论与下一步），发送消息后回一句带关键要点的进度（如「正在按您说的出 3 张 16:9 主图，画面文案用您给的原文」）让用户当场能确认理解没偏——只带要点、不贴整条消息、不提参数名；done 呈现前把用户的硬要求逐项对着产物核对，交付话术分开说已满足与仍不符，不符就同会话续聊点名区域纠正，不笼统说「已按您的要求完成」；每轮 poll 返回的 message/planning_text/response_blocks 有新内容就即时转述到对话框（相同内容去重、不攒到 done），没有新文本也每轮固定补一句短进度（已等待约几分钟 + progress 百分比，不静默、不编造数字），A2UI 与 ask_user 先在对话里呈现规划要点/选项/表单字段、再用问卷收集；不输出工具名、调用参数、返回 JSON、URL 参数、浏览器/配置/降级等内部机制；**通道术语不进对话**——连接器/降级/官方 CLI/MCP 直通/终端等待循环/探活都不写进回复，采用终端等待循环时什么都不播报，严禁「CLI 直通可用」这类句式（用户会理解成已降级，2026-10-27 实例）；只有真降级（连接器不可用、整条链路改由 CLI 承接）才用大白话说一句「主连接暂不可用，我换了备用方式继续，任务不中断」，用户主动问是否降级才讲清「主通道是连接器/现在是否真的降级/任务行为有无变化」（chat.md「对话呈现」）；Canvas/Session ID 存台账、默认不展示（用户问起或排障才给）；画布页自行实时更新，无需向用户解释刷新机制（细则 chat.md「对话呈现」）；不播报执行实现（探活/加载细则/确认参数/组织 prompt/轮询/台账/落盘直接做），不使用内部模块名与流程名（如 Chat 主循环、外挂屏）作为对话措辞；长任务（视频合成/高清出图/套图）必须持续等待到完成或出错——轮询不设次数上限，不提前收尾、不询问用户是否继续（如「回一句继续」「跟我说声『看下好了没』」）——对话重点是任务本身。**等待节奏要防宿主的重复调用保护**（2026-10-22 实测：同一工具连续四次同参放行、第五次被硬拦并提示改参数或直接给结论；中间夹一次不同调用即重新计数）——poll 最容易撞上而单次等待又锁在 55 秒，**被拦停不等于任务结束**：① timeout_seconds 在 55/45/35 之间轮换（相邻两次不同值，session_id/canvas_id 不动）② 轮间夹一次不同调用 ③ 已知长任务把多轮 poll 收进一次 Bash 调用内的终端等待循环（ifs mcp call ifs_canvas_poll 反复调，python3 解 content[].text 取 status，终态退 0、预算用尽退 2 就再来一次；单轮 50 秒 × 预算 100 秒、把这次 Bash 调用的超时给到 3 分钟；循环里只 poll 绝不重复 create；前提本机已有可用 OAuth profile，不为此要求用户新登录，不满足回落 ①②；发消息与上传仍走连接器）——细则 chat.md 阶段 ②「轮询节奏」。**终端等待循环只是等待技巧、不是降级**：主通道仍是连接器，不写偏好、也不对此向用户播报。产物呈现：**本轮新生成的产物一律默认落盘**（图片、视频与任何其他 media 成果，不等用户开口；与用户上传素材、画布输入原图/原视频同源的不重复下载，分不清就只落 message 点名的）——先建目录，再用 Bash 把 media[].url 下载到工作区 outputs/（重名加序号、不覆盖已有文件；用户指定其他目录时按用户的）；**会话没绑定工作区时**以当前工作目录为根落它的 outputs/（宿主给会话临时开的目录已预建 outputs，实测形如「~/.qoderwork/workspace/…/outputs」），此时交付要说明该目录不在用户项目里、并问要不要复制一份到指定目录，不往家目录乱写也不擅自删移 → 回复里给**可点开的文件链接 + 所在目录**（不要只说「已保存」）；**图片在对话里仍只能用 media[].url 远程地址渲染**（消息正文写本地路径不渲染，实测显示「图片无法显示，打开文件」，落盘文件是交付物与兜底）；**视频在对话内播不出来**（对话渲染面板 CSP 无 media-src，远程/data:/blob: 三种写法实测全黑屏 0:00，不是文件损坏）→ 对落盘的本地文件拉起系统播放器（macOS open / Windows start / Linux xdg-open，一次任务只拉一次）；用户问文件在哪就定位（macOS open -R / Windows explorer /select, / Linux 打开所在目录）；画面预览只用远程封面图地址，别抽本地图往对话里塞；画布页原生播放器仍是主呈现通道，别再往对话里挂 video 标签（细则 chat.md 阶段 ⑤）。"
    printf '%s\n' "{
  \"hookSpecificOutput\": {
    \"hookEventName\": \"SessionStart\",
    \"additionalContext\": \"$additionalContext\"
  }
}"
    exit 0
    ;;

  mcp-guard)
    # 已退役（保留空壳防误配）：登录门禁由连接器 OAuth 传输层承担，本地无可判状态
    exit 0
    ;;

  guard)
    tool=$(json_field tool_name)
    case "$tool" in
      '')   ;;          # 解析不出工具名（如环境缺依赖）→ 不误判，继续用整段 payload 匹配窄规则
      Bash) ;;          # 本 hook 的目标工具
      *)    exit 0 ;;   # 明确是别的工具 → 放行
    esac

    cmd=$(json_field tool_input.command)
    [ -n "$cmd" ] || cmd="$payload"   # 退化：拿不到字段就在整段 payload 上匹配

    # 规则 1：不要把 IFS 凭据打印/外传（token 在 ~/.ifs/config.json 与连接器托管凭据内）
    case "$cmd" in
      *'.ifs/config.json'* | *'.ifs/config'*)
        case "$cmd" in
          *cat*|*less*|*more*|*head*|*tail*|*strings*|*base64*|*cp*|*scp*|*rsync*|*curl*|*wget*|*nc*|*tar*|*zip*|*grep*)
            echo "已阻断：不要读取或外传 IFS 凭据（~/.ifs/config.json 内含访问令牌）。检查授权态请用 ifs_ping（连接器）或 ifs auth status / ifs doctor（CLI），它们只输出状态不输出令牌。" >&2
            log_line guard "blocked=credential-read tool=Bash"
            exit 2
            ;;
        esac
        ;;
    esac

    # 规则 2：不要破坏 IFS 本地状态
    case "$cmd" in
      *'rm -rf'*'.ifs'* | *'rm -fr'*'.ifs'* | *'rm -r'*'.ifs/config'*)
        echo "已阻断：该命令会删除 IFS 本地状态目录（~/.ifs），令牌与模型缓存都会丢失，需重新登录。确认要清理时请手动执行。" >&2
        log_line guard "blocked=destroy-state tool=Bash"
        exit 2
        ;;
    esac

    exit 0
    ;;

  audit)
    # PostToolUse 落审计（异步、非阻断、绝不 exit 2）
    tool=$(json_field tool_name)
    cmd=$(json_field tool_input.command)
    input=$(json_field tool_input)
    case "$cmd$input" in
      *ifs*|*task_*|*canvas_*|*asset_*)
        line=$(printf '%s' "$cmd$input" | tr '\n' ' ' | cut -c1-300 | redact)
        log_line audit "tool=${tool:-?} detail=${line}"
        ;;
    esac
    exit 0
    ;;

  *)
    exit 0
    ;;
esac
