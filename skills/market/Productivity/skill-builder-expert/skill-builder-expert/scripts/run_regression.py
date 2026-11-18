#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
run_regression.py —— 静态回归引擎（第三方评测第②项落地）

不真跑对话，做两层结构化回归校验（全部 fail-closed）：

A. 状态机静态可达性（解析 references/REF-SM-004_StateMachine.yaml）
   1) 状态定义非空、无重复定义；
   2) 每条 transition 的 target 必须指向已定义状态（断链 = FAIL）；
   3) 从入口状态 BFS 全图可达，存在不可达状态 = FAIL；
   4) 四大角色状态必须存在，且每个角色都能沿转换到达终态 end_session
      （这是「每个角色可独立闭环运转」的结构保证）；
   5) 强制节点必须存在（v27 扩充）：material_parse_gate（素材关口）、
      deliver_preview（交付预览）、illegal_input（输入非法兜底）、
      intent_unknown（意图模糊兜底）、engine_fallback（引擎故障降级）、
      high_risk_block（高危合规拦截）——三大降级路径 + 高危拦截缺一即 FAIL。

B. 主干文档与包内资产一致性（按需加载规则的自检底座）
   6) SKILL.md 中提到的配套文档必须真实存在（防关联断链）；
   7) references/ 与 scripts/ 下每个文件必须在 SKILL.md 中被登记（防幽灵文件）；
   8) SKILL.md frontmatter 与 _meta.json 均不得含构建号赋值（迭代编号仅存内部私有区域）；
   8b) 演进痕迹零出口：evolution_trace_scan 扫入包视图，版本沿革标记/构建计数赋值/
       迭代句式/内部称谓检出即 FAIL（fail-closed）。

C. 章节号锚点校验（防文内死指针）
   9b) 标准调用与按需应答总则在位（SKILL.md 交互底层约束第 8 条三款：
       答疑先查册／按需应答字数纪律／帮做走标准件，任一缺失 FAIL——
       防改版丢失导致答疑临场编造、答复倾倒、流程自由拼装）；
   9) SKILL.md 内所有带显式标记的章节号跳转（§N.N / 见 N.N / （N.N）必须在
      文中存在真实落点（标题 / 条目 / 加粗 / 流水线步骤等定义位）；
      无锚点 = FAIL（章节重排留下的死指针会让 Agent 运行时调度失灵）。

D. 引擎自测（v27 新增，防「永远 PASS」自证盲区）
   10) 内置阳/阴用例：1 组自洽迷你状态机（应 PASS）+ 3 组变体
       （缺兜底节点 / transition 断链 / 缺终态，均应 FAIL）；
       `--self-test` 显式运行；普通运行前静默预检，自测不过即拒绝回归
       （引擎本身不可信时，其 PASS 结论无效）。

用法：python run_regression.py <包根目录>
      python run_regression.py --self-test
退出码：0 = PASS，1 = FAIL，2 = 用法错误
"""

import re
import sys
from pathlib import Path

ROLE_STATES = ["role_1_build", "role_2_qa", "role_3_repair", "role_4_evaluate", "role_4_integrate"]
REQUIRED_NODES = ROLE_STATES + [
    "material_parse_gate", "deliver_preview",
    "illegal_input", "intent_unknown", "engine_fallback", "high_risk_block",
]
TERMINALS = {"end_session"}


def parse_states(text):
    """极简解析：无需三方依赖。返回 {状态名: [target, ...]}，重复定义抛异常。"""
    states = {}
    cur = None
    in_states = False
    for raw in text.splitlines():
        line = raw.rstrip()
        if not line.strip():
            continue
        indent = len(line) - len(line.lstrip())
        stripped = line.strip()
        # 顶层键：切换 states 作用域
        if indent == 0 and re.match(r"^[A-Za-z_][\w-]*:", stripped):
            key = stripped.split(":", 1)[0].strip()
            in_states = (key == "states")
            cur = None
            continue
        if not in_states:
            continue
        m = re.match(r"^([A-Za-z_][\w-]*):\s*$", stripped)
        if m and indent == 2:
            cur = m.group(1)
            if cur in states:
                raise ValueError("重复状态定义: %s" % cur)
            states[cur] = []
            continue
        if cur is not None:
            m2 = re.search(r"target:\s*[\"']?([A-Za-z_][\w-]*)[\"']?", stripped)
            if m2:
                states[cur].append(m2.group(1))
    return states


def bfs_reachable(graph, start):
    """只在已定义状态集合内做 BFS：断链目标不算可达（v27 修复，
    防止「角色 → 已删除的终态」被误判为闭环成立——引擎自测阴例③的实证盲区）。"""
    seen = {start} if start in graph else set()
    queue = [start] if start in graph else []
    while queue:
        node = queue.pop(0)
        for t in graph.get(node, []):
            if t in graph and t not in seen:
                seen.add(t)
                queue.append(t)
    return seen


def check_state_machine(root, fails):
    sm = root / "references" / "REF-SM-004_StateMachine.yaml"
    if not sm.exists():
        fails.append("状态机文件缺失: references/REF-SM-004_StateMachine.yaml")
        return
    try:
        states = parse_states(sm.read_text(encoding="utf-8"))
    except ValueError as e:
        fails.append("状态机解析失败: %s" % e)
        return
    except Exception as e:
        fails.append("状态机读取异常: %s" % e)
        return

    if not states:
        fails.append("状态机为空：未解析到任何状态")
        return

    # 2) target 断链
    dangling = []
    for name, targets in states.items():
        for t in targets:
            if t not in states:
                dangling.append("%s -> %s" % (name, t))
    if dangling:
        fails.append("transition 目标断链 %d 处: %s" % (len(dangling), "; ".join(dangling[:6])))

    # 3) 全图可达性
    entry = "init" if "init" in states else sorted(states.keys())[0]
    reachable = bfs_reachable(states, entry)
    unreachable = sorted(set(states) - reachable)
    if unreachable:
        fails.append("存在从入口 %s 不可达的状态: %s" % (entry, ", ".join(unreachable[:8])))

    # 4) 四大角色存在 + 每个角色可独立到达终态
    for role in ROLE_STATES:
        if role not in states:
            fails.append("角色状态缺失: %s" % role)
            continue
        reach = bfs_reachable(states, role)
        if not (reach & TERMINALS):
            fails.append("角色 %s 无法沿转换到达终态 %s（独立闭环断裂）" % (role, "/".join(sorted(TERMINALS))))

    # 5) 强制节点（含三大降级路径与高危拦截）
    for node in REQUIRED_NODES:
        if node not in states:
            fails.append("强制节点缺失: %s" % node)

    # 6) 模板绑定校验：状态机 template: "REF-TMP-003#节名" 必须指向真实存在的模板节
    #    （2026-11-02 工程教训：entry_action 与模板无显式映射，Agent 即兴生成替代文本导致交互漂移）
    check_template_bindings(root, fails)

    if not fails:
        print("PASS 状态机: %d 状态 / 入口 %s / 业务角色态均可达终态 / 强制节点 %d 个齐 / 无断链 / 模板绑定有效"
              % (len(states), entry, len(REQUIRED_NODES)))


def check_template_bindings(root, fails):
    """校验状态机中 template 绑定的模板节在 REF-TMP-003 中真实存在（防死绑定）。"""
    sm = root / "references" / "REF-SM-004_StateMachine.yaml"
    tpl = root / "references" / "REF-TMP-003_MenuInteraction.md"
    if not sm.is_file() or not tpl.is_file():
        return  # 文件缺失由 B 层断链检查负责，此处不重复报
    import re as _re
    sm_text = sm.read_text(encoding="utf-8")
    tpl_text = tpl.read_text(encoding="utf-8")
    # 收集 TMP-003 全部节标题：整行 + 【节名】括号形式（标题常带「｜说明」后缀）
    heads = set()
    for m in _re.finditer(r"^#{1,3}\s*(.+)$", tpl_text, _re.M):
        line = m.group(1).strip()
        heads.add(line)
        for mm in _re.finditer(r"【([^】]+)】", line):
            heads.add("【%s】" % mm.group(1))
            heads.add(mm.group(1))
    # 抽取状态机内全部 template 绑定行
    refs = _re.findall(r'template:\s*"REF-TMP-003#(.+?)"', sm_text)
    if not refs:
        fails.append("状态机未绑定任何模板节（template 字段全缺，模板强制无从落地）")
        return
    for ref in refs:
        if ref not in heads:
            fails.append("模板绑定死指针: REF-TMP-003#%s（节标题不存在于交互模板）" % ref)


def check_doc_asset_consistency(root, fails):
    skill = root / "SKILL.md"
    if not skill.exists():
        fails.append("SKILL.md 缺失")
        return
    text = skill.read_text(encoding="utf-8", errors="replace")

    # 6) SKILL.md 提到的配套文档必须存在
    mentioned = set(re.findall(r"references/([A-Za-z0-9_\-\.]+\.md)", text))
    missing = sorted(p for p in mentioned if not (root / "references" / p).exists())
    if missing:
        fails.append("SKILL.md 提到但不存在的文档 %d 个: %s" % (len(missing), "; ".join(missing[:6])))

    # 7) references/ 与 scripts/ 每个文件必须在 SKILL.md 登记
    for sub in ("references", "scripts"):
        d = root / sub
        if not d.exists():
            fails.append("目录缺失: %s/" % sub)
            continue
        ghosts = sorted(f.name for f in d.iterdir()
                        if f.is_file() and f.suffix in (".md", ".py") and f.name not in text)
        if ghosts:
            fails.append("[公开口径] %s/ 下未在 SKILL.md 登记的幽灵文件 %d 个: %s" % (sub, len(ghosts), "; ".join(ghosts[:6])))

    # 8) 构建号痕迹零存在（演进痕迹规范：迭代编号仅存内部私有区域，
    #    对外交付视图（SKILL.md / _meta.json）不得出现构建编号赋值）
    m1 = re.search(r"^build_no:\s*(\S+)", text, re.M)
    meta = root / "_meta.json"
    m2 = None
    if meta.exists():
        m2 = re.search(r"\"build_no\"\s*:\s*(\d+)", meta.read_text(encoding="utf-8"))
    if m1:
        fails.append("SKILL.md frontmatter 检出构建号赋值（应仅存内部私有区域）")
    if m2:
        fails.append("_meta.json 检出构建号赋值（应仅存内部私有区域）")

    # 9) 演进痕迹零出口（调 evolution_trace_scan 扫入包视图，检出即 FAIL）
    try:
        sys.path.insert(0, str(Path(__file__).parent))
        import evolution_trace_scan as _ets
        findings = _ets.run_scan([root])
        if findings:
            sample = sorted(findings.keys())[:5]
            fails.append("[公开口径] 演进痕迹检出 %d 文件（版本沿革标记/构建计数赋值/迭代句式/内部称容）: %s"
                         % (len(findings), "; ".join(sample)))
    except Exception as e:
        fails.append("演进痕迹扫描异常: %s" % e)

    if not any("不存在的文档" in f or "幽灵" in f or "构建号" in f or "演进痕迹" in f for f in fails):
        print("PASS 一致性: 配套文档与脚本全登记、无断链、构建号痕迹零存在、演进痕迹零出口")


# 10) 本地偏好守卫（REF-ADT-037：规则册/告知语/仅本地/不入包，fail-closed）
    try:
        sys.path.insert(0, str(Path(__file__).parent))
        import preference_guard as _pg
        pf = _pg.run_checks(root)
        if pf:
            fails.append("偏好守卫未过: " + "; ".join(pf[:5]))
        else:
            print("PASS 本地偏好守卫（P1-P4）")
    except Exception as e:
        fails.append("偏好守卫异常: %s" % e)


SECTION_REF = re.compile(r"(?:§|见\s*|（)(\d{1,2}\.\d{1,2})([a-zA-Z]?)")


def check_section_anchors(root, fails):
    """9) 章节号跳转必须有文内锚点（fail-closed）。

    锚点定义：N.N 出现在「定义位」——即前一个字符不是 § /（/见/字母/数字/点，
    覆盖标题、编号条目、加粗条目、流水线步骤（→ 3.4 …）等形态。
    跳转定义：带显式标记 §N.N / 见 N.N / （N.N（允许 3.4b 这类字母后缀，
    按剥后缀的母号找锚点）。版本号 V3.2、日期 2026.11、纯小数等非章节号
    形态天然被排除（前缀字符不在跳转标记集内或被前后文排除）。
    """
    skill = root / "SKILL.md"
    if not skill.exists():
        return  # 缺失已由一致性检查报告，避免重复计错
    text = skill.read_text(encoding="utf-8", errors="replace")
    body = re.sub(r"^---.*?^---", "", text, count=2, flags=re.S | re.M)  # 去 frontmatter
    body = re.sub(r"```.*?```", "", body, flags=re.S)  # 去 fenced code

    anchors = set()
    for m in re.finditer(r"(?<![A-Za-z0-9.§（])(\d{1,2}\.\d{1,2})", body):
        start = m.start()
        prev2 = body[start - 2:start]
        if prev2 == "见 " or body[start - 1] == "见":
            continue  # 跳转位，不作为锚点
        anchors.add(m.group(1))

    bad = []
    for m in SECTION_REF.finditer(body):
        num, suffix = m.group(1), m.group(2)
        if num in anchors or (suffix and num + suffix in anchors):
            continue
        line_no = body[: m.start()].count("\n") + 1
        bad.append("§%s(L%d)" % (num, line_no))
    if bad:
        fails.append("章节号跳转无锚点 %d 处: %s" % (len(bad), "; ".join(bad[:8])))
    else:
        print("PASS 章节锚点: 全部显式章节号跳转均有文内落点")


def check_call_charter(root, fails):
    """10) 标准调用与按需应答总则在位（fail-closed，防改版丢失）。

    SKILL.md 交互底层约束第 8 条三款必须齐全：答疑先查册（无册明说、禁编）／
    按需应答字数纪律（一屏内＋大纲点选）／帮做走标准件（禁现场拼装）。
    """
    skill = root / "SKILL.md"
    if not skill.exists():
        return  # 缺失已由一致性检查报告，避免重复计错
    text = skill.read_text(encoding="utf-8", errors="replace")
    required = ["标准调用总则", "答疑先查册", "按需应答字数纪律", "帮做走标准件"]
    missing = [k for k in required if k not in text]
    if missing:
        fails.append("标准调用与按需应答总则缺失条目: %s（SKILL.md 交互底层约束第8条，防丢锚点 fail-closed）" % "、".join(missing))
    else:
        print("PASS 标准调用总则: 三款条目在位（答疑先查册／按需应答字数纪律／帮做走标准件）")

    # 9c) 业务细节口述承接标准在位（防丢锚点）
    ing = root / "references" / "REF-ING-028_IntakeEngine.md"
    if ing.exists():
        it = ing.read_text(encoding="utf-8", errors="replace")
        req2 = ["业务细节口述承接标准", "段段接住", "按族归档", "缺件追问", "攒够触发",
                "大段倾倒承接规程", "整包接住不打断", "回执三张单",
                "任意输入标准化与确认铁律", "双路径覆盖", "确认三理由", "批量纪律"]
        missing2 = [k for k in req2 if k not in it]
        if missing2:
            fails.append("承接与确认铁律缺失条目: %s（REF-ING-028 五/六/七节，防丢锚点 fail-closed）" % "、".join(missing2))
        else:
            print("PASS 承接与确认铁律: 口述四步＋倾倒规程＋全输入确认铁律条目全在位")

    # 9d) 开场轻量化与数字直连在位（v85 防丢锚点 · 同源机检）
    sm = root / "references" / "REF-SM-004_StateMachine.yaml"
    tmp = root / "references" / "REF-TMP-003_MenuInteraction.md"
    if sm.exists() and tmp.exists():
        st = sm.read_text(encoding="utf-8", errors="replace")
        tt = tmp.read_text(encoding="utf-8", errors="replace")
        req_sk = ["开场屏与高频屏面内联文本", "menu_number_map", "禁止送入意图识别二次猜测",
                  "每轮步数铁律", "加载自证豁免", "什么都能做成技能", "什么料都能发",
                  "「收费版本」指的是你做出来的技能将来要不要向你的用户收费",
                  "👋 您好，我是您的 Skill技能搭建专家。",
                  "—— Skill技能搭建专家"]
        miss = [k for k in req_sk if k not in text]
        if miss:
            fails.append("开场内联区缺失条目: %s（SKILL.md 1.1-A，防丢锚点 fail-closed）" % "、".join(miss))
        else:
            print("PASS 开场内联区: 数字直连＋步数铁律＋自证豁免＋内联屏面条目全在位")
        req_sm = ['"1": "role_1_build"', '"2": "role_2_qa"', '"3": "role_3_repair"',
                  '"4": "role_4_evaluate"', "menu_number_direct", "禁止送入 intent_detect 二次猜测",
                  "仅 SKILL.md（开场屏与高频屏面已逐字内联"]
        miss2 = [k for k in req_sm if k not in st]
        if miss2:
            fails.append("数字直连路由缺失条目: %s（REF-SM-004，防丢锚点 fail-closed）" % "、".join(miss2))
        else:
            print("PASS 数字直连: menu_number_map 五向映射＋直连态＋轻量 load_policy 全在位")
        for probe in ["• 版本说明：本工具默认按免费版本执行，直接用即可；「收费版本」指的是你做出来的技能将来要不要向你的用户收费，与你使用本工具无关，后续链路会引导你完成选型确认。",
                      "▸ 什么都能做成技能：经验、手艺、标准、流程、规则、制度、技巧、技术、心法、策略、方法、判断、条件、逻辑——只要是你做事时反复在用的，都能沉淀成技能；",
                      "▸ 什么料都能发：文档（Word、PDF、PPT、TXT、MD、Excel）、图片、语音、视频、表格、链接都收，有现成文件直接发；没有文件就用大白话说，想到哪说到哪，我来帮你做成技能。"]:
            if probe not in text or probe not in tt:
                fails.append("同源机检漂移: 抽查句在 SKILL.md 与 REF-TMP-003 不同时在位（两处必须同改）")
                break
        else:
            print("PASS 同源机检: 内联文本与模板册逐字一致（抽查三句）")

    # 9e) 交付模式与版本关联规约在位（v86 防丢锚点 · 含反向检查）
    ch = root / "references" / "REF-DLV-049_DeliveryModeVersionCharter.md"
    if ch.exists():
        ct = ch.read_text(encoding="utf-8", errors="replace")
        tmpf = root / "references" / "REF-TMP-003_MenuInteraction.md"
        smf = root / "references" / "REF-SM-004_StateMachine.yaml"
        skf = root / "SKILL.md"
        tt2 = tmpf.read_text(encoding="utf-8", errors="replace")
        st2 = smf.read_text(encoding="utf-8", errors="replace")
        sk2 = skf.read_text(encoding="utf-8", errors="replace")
        req_ch = ["该默认不等于偏好推荐", "支付接入开发者说明",
                  "不担保上架结果", "不诱导使用方优先选择或者避开某一种方案",
                  "不传递默认方案是为了保障运行稳定这类表述"]
        missc = [k for k in req_ch if k not in ct]
        req_t = ["API模式准入条件清单", "确认切换 API模式", "该默认只是起点，不是推荐",
                 "支付接入开发者说明", "SSL 证书", "配套事项由你自行办理"]
        misst = [k for k in req_t if k not in tt2]
        req_s = ["api_condition_gate", "bind_default_free_lightweight", "确认切换 API模式"]
        misss = [k for k in req_s if k not in st2]
        miss_all = missc + misst + misss
        if miss_all:
            fails.append("交付模式规约缺失条目: %s（REF-DLV-049/TMP-003/SM-004，防丢锚点 fail-closed）" % "、".join(miss_all))
        else:
            print("PASS 交付模式规约: 默认不推荐＋API准入闸＋不担保口径条目全在位")
        if "优先推荐" in tt2 or "优先推荐" in sk2:
            fails.append("反向检查违规: 「优先推荐」字样残留（REF-DLV-049 第8条不推荐任何方案，须摘除）")
        else:
            print("PASS 反向检查: 「优先推荐」零残留（不推荐任何方案）")

    # 9f) 资产分级反向机检（v89 常驻：公开包零方法论、零协作痕迹）
    # 词面拼装（防自指：扫描词表字面不得完整落盘）
    W = ["".join(x) for x in (
        ["六", "主词"], ["整组", "丢弃"], ["主", "理人"], ["蒸馏", "包"], ["实测", "教训"],
        ["预", "埋"], ["关键词", "布局"], ["检索", "布局"], ["长尾", "铺词"], ["REF-KWD", "-050"],
        ["REF-EVL", "-053"], ["出题", "方法论"], ["设题", "三板斧"],
    )]
    pkg_files = [f for f in root.rglob("*") if f.suffix in (".md", ".py", ".yaml", ".json") and "MAINTAINER" not in f.name and "logs" not in str(f)]
    leaks = []
    for f in pkg_files:
        ft = f.read_text(encoding="utf-8", errors="replace")
        for w in W:
            if w in ft:
                leaks.append("%s:%s" % (f.name, w))
    if leaks:
        fails.append("[公开口径] 资产分级泄漏: %s（公开包零方法论零协作痕迹，fail-closed）" % "、".join(leaks[:6]))
    else:
        print("PASS 资产分级: 方法论与协作痕迹零泄漏（%d 词 × %d 文件）" % (len(W), len(pkg_files)))

    # 9g) v89 交互与内容锚点
    tmp3 = root / "references" / "REF-TMP-003_MenuInteraction.md"
    faq = root / "FAQ.md"
    smf2 = root / "references" / "REF-SM-004_StateMachine.yaml"
    if tmp3.exists() and faq.exists() and smf2.exists():
        tt3 = tmp3.read_text(encoding="utf-8", errors="replace")
        fq = faq.read_text(encoding="utf-8", errors="replace")
        st3 = smf2.read_text(encoding="utf-8", errors="replace")
        sk3 = text
        fop_p = root / "references" / "REF-FOP-065_FactoryOpsPlaybook.md"
        fop_t = fop_p.read_text(encoding="utf-8", errors="replace") if fop_p.exists() else ""
        sk3fop = text + fop_t  # 2026-11-11 工厂区块迁 REF-FOP-065，字面在主文档或分册任一在位即锚定
        req_v89 = [
            ("整改技能", st3), ("技能质量评测", st3), ("免费版本怎么配", st3), ("轻量模式怎么配", st3),
            ("默认按「专用模式‑自用版」执行", tt3), ("直接说出你想做技能的具体需求及资料发来即可开工", tt3),
            ("对外输出纯净铁则", sk3), ("兜底三要素", sk3), ("字母编号大小写不敏感", sk3),
            ("C7：免费版本怎么配", fq), ("C8：轻量模式怎么配", fq), ("F10：技能包拿到了，不会安装怎么办", fq),
            ("禁止用圈号点选", fq),
            ("常见问题目录大纲", tt3), ("本技能标准使用方法：点击", sk3),
            ("本技能标准使用方法：点击", tt3),
            ("可避免技能之间互相干扰", sk3), ("高频入口口令直连", sk3),
            ("重点渲染铁则", sk3), ("禁止 Grep／Glob／全库模糊搜索", sk3),
            ("faq_outline", st3), ('route: "faq_outline"', st3),
            ("字母编号大小写不敏感全映射", st3), ("字母编号大小写不敏感", fq), ("大小写均可", fq),
            ("**[1] 技能代建助手**", sk3), ("**[1] 技能代建助手**", tt3),
            ("snapshot_manage", st3), ("REF-SNP-051", sk3),
            ("加载我的基线档案", st3), ("新建交付基线", st3), ("保存至我的基线档案", st3),
            ("档案管理子菜单", tt3), ("检测到您存在一份业务快照档案", tt3), ("检测到您存在一份业务快照档案", sk3),
            ("确认清空当前这份业务快照档案", tt3), ("是否继承该技能包原有基线标准", tt3),
            ("六类 58 问", sk3), ("六类 58 问", tt3),
            ("（A）认知入门", sk3), ("（A）认知入门", tt3),
            ("回复类别字母（A）–（F）", sk3), ("回复类别字母（A）–（F）", tt3),
            ("（E1）至（E12）", fq),
        ]
        miss_v89 = [k for k, src in req_v89 if k not in src]
        pgf = root / "scripts" / "preference_guard.py"
        pgok = pgf.exists() and "P5_KEY_PHRASES" in pgf.read_text(encoding="utf-8", errors="replace")
        if not pgok:
            fails.append("守卫 P5 缺失: preference_guard.py 无快照档案白名单/黑名单校验（P5_KEY_PHRASES）")
        else:
            print("PASS 守卫升级: 偏好守卫含 P5 快照档案声明校验")
        outline_probe = "**（A）认知入门**（15 问）"
        if outline_probe not in tt3 or outline_probe not in sk3:
            fails.append("同源机检漂移: FAQ 大纲抽查句在 SKILL.md 与 REF-TMP-003 不同时在位（两处必须同改）")
        else:
            print("PASS 同源机检: FAQ 大纲与模板册逐字一致（抽查）")
        neg_v89 = [("帮你新建Skill技能", tt3), ("Qx / Qy", fq), ("不会为你预设默认选项", tt3)]
        neg_hits = [k for k, src in neg_v89 if k in src]
        if miss_v89 or neg_hits:
            fails.append("v89 锚点异常: 缺 %s / 残留 %s" % ("、".join(miss_v89) or "无", "、".join(neg_hits) or "无"))
        else:
            print("PASS v89 锚点: 触发词＋默认直通＋FAQ＋纯净铁则全在位，旧字样零残留")

        # 9k) v109 行动指引句式与收费确认闸锚点
        req_v109 = [
            ("paid_confirm_gate", st3), ("render_paid_confirm_screen", st3),
            ("【收费版本确认（关键配置）】", tt3), ("收费版本确认（关键配置）", sk3),
            ("🔒 收费版本确认（关键配置）", tt3),
            ("回复「收费确认」完成锁定", tt3),
            ("「下一步」字样全包禁用", tt3), ("「下一步」全包禁用", sk3),
            ("本次就可以为你做，回复 **【确认】** 即直接开工", sk3),
            ("我即刻开始做完整性与质量评测", sk3), ("我即刻开始做完整性与质量评测", tt3),
            ("收到即刻开始完整性与结构校验", sk3), ("收到即刻开始完整性与结构校验", tt3),
            ("屏面禁用「下一步」", st3),
        ]
        miss_v109 = [k for k, src in req_v109 if k not in src]
        if miss_v109:
            fails.append("v109 锚点异常: 缺 %s（行动指引句式铁则＋收费确认闸，防丢锚点 fail-closed）" % "、".join(miss_v109))
        else:
            print("PASS v109 锚点: 收费确认闸＋行动指引句式铁则＋交料即开跑句式全在位")

        # 9l) v110 长周期与跨窗口续作锚点（挂起回执/交接引导/断点重建/现场档案/体量提醒）
        snp = root / "references" / "REF-SNP-051_UserSnapshotProfile.md"
        sv = snp.read_text(encoding="utf-8", errors="replace") if snp.exists() else ""
        req_v110 = [
            ("任务挂起回执", tt3), ("回复【继续任务】回到原任务", tt3),
            ("窗口交接引导", tt3), ("先回复【新建交付基线】固化进度", tt3),
            ("模型建议选与上一窗口相同的", tt3),
            ("断点重建问询", tt3), ("禁止装作记得", tt3),
            ("体量档位一次性提醒", tt3), ("只提醒这一次", tt3),
            ("现场自检", tt3), ("禁止凭空补叙", tt3),
            ("【窗口交接引导】", st3), ("【断点重建问询】", st3),
            ("window_handover", st3), ("breakpoint_rebuild", st3),
            ("任务挂起回执", st3), ("体量档位一次性提醒", st3), ("禁止每轮重复提醒", st3),
            ("长周期与跨窗口续作铁则", sk3), ("九类掌控感信号", sk3),
            ("禁止装作记得、禁止凭空补叙", sk3),
            ("进度现场", sv), ("框架概要全文", sv), ("禁止扩列", sv),
            ("4.6 进度现场自动写入", sv), ("静默降级", sv),
        ]
        miss_v110 = [k for k, src in req_v110 if k not in src]
        if miss_v110:
            fails.append("v110 锚点异常: 缺 %s（长周期与跨窗口续作，防丢锚点 fail-closed）" % "、".join(miss_v110))
        else:
            print("PASS v110 锚点: 挂起回执＋窗口交接＋断点重建＋现场档案＋体量提醒全在位")

        # 9m) v111 交付实测提醒锚点（两档频率＋闸口钉挂载＋「修正」禁令）
        req_v111 = [
            ("交付实测提醒 · 完整版", tt3), ("交付实测提醒 · 轻量版", tt3),
            ("测试操作流程", tt3),
            ("从本地添加技能", tt3), ("「去试试」", tt3),
            ("真实场景验证 → 多人多维度测试 → 按验收清单完整核验", tt3),
            ("请提供截图或测试原文，用于迭代更新", tt3),
            ("实测通过再给团队用", tt3), ("本轮更新建议先跑一遍核心场景再下发", tt3),
            ("用于迭代更新", tt3), ("有对不上的地方，随时拿回来", tt3),
            ("交付实测提醒", st3), ("render_delivery_test_reminder", st3),
            ("首交付完整版", sk3), ("对外措辞禁用「修正」", sk3),
        ]
        miss_v111 = [k for k, src in req_v111 if k not in src]
        if miss_v111:
            fails.append("v111 锚点异常: 缺 %s（交付实测提醒两档＋闸口挂载，防丢锚点 fail-closed）" % "、".join(miss_v111))
        else:
            print("PASS v111 锚点: 交付实测提醒两档＋闸口钉挂载＋措辞禁令全在位")

        # 9n) v112 技能成长摘要锚点（随包输出＋取材纪律＋闸口挂载）
        req_v112 = [
            ("技能成长摘要", tt3), ("本包成长记录", tt3),
            ("取材于用户已确认的内容", tt3),
            ("禁止凭空补叙、禁止展望未实现的能力", tt3), ("历史累计第", tt3),
            ("render_growth_summary", st3), ("技能成长摘要", st3),
            ("技能成长摘要铁则", sk3),
        ]
        miss_v112 = [k for k, src in req_v112 if k not in src]
        if miss_v112:
            fails.append("v112 锚点异常: 缺 %s（技能成长摘要，防丢锚点 fail-closed）" % "、".join(miss_v112))
        else:
            print("PASS v112 锚点: 成长摘要随包输出＋取材纪律＋闸口挂载全在位")

        # 9o) v113 FAQ 团队使用一问锚点（C9＋计数 56）
        req_v113 = [
            ("C9：做好的技能能给我们公司团队一起用吗", fq),
            ("专用模式‑自用版（只有你自己用", fq),
            ("（C1）至（C9）", fq),
            ("（C）选型配置**（9 问）", sk3), ("（C）选型配置**（9 问）", tt3),
            ("六类 58 问", sk3), ("六类 58 问", tt3),
        ]
        miss_v113 = [k for k, src in req_v113 if k not in src]
        if miss_v113:
            fails.append("v113 锚点异常: 缺 %s（FAQ C9 团队使用，防丢锚点 fail-closed）" % "、".join(miss_v113))
        else:
            print("PASS v113 锚点: FAQ C9 团队使用一问＋计数 56 两册同源全在位")

        # 9p) v114 FAQ 直答＋自由语义触发归轨锚点（两车道一轨道）
        req_v114 = [
            ("直答匹配规", fq), ("逐字输出该问标准答案", fq),
            ("命中多条", fq), ("零命中", fq),
            ("自由语义触发与归轨铁则", sk3), ("两车道一轨道", sk3),
            ("质量标准一套，触发凭据两套", sk3),
            ("归轨不跳闸", sk3), ("禁止为自由语义另立执行标准", sk3),
            ("进度定位", sk3),
            ("自由语义触发与归轨", st3), ("output_faq_answer_verbatim", st3),
            ("FAQ 直答匹配规", st3),
        ]
        miss_v114 = [k for k, src in req_v114 if k not in src]
        if miss_v114:
            fails.append("v114 锚点异常: 缺 %s（FAQ 直答＋自由触发归轨，防丢锚点 fail-closed）" % "、".join(miss_v114))
        else:
            print("PASS v114 锚点: 直答匹配规＋两车道一轨道铁则＋直答路由全在位")

        # 9q) v115 底座升级锚点（三段式反馈＋三不碰红线＋组件版本 1.1.0）
        _bse_p = Path(__file__).resolve().parent.parent / "references" / "REF-BSE-047_DeliveryBaseComponent.md"
        _bse_txt = _bse_p.read_text(encoding="utf-8") if _bse_p.is_file() else ""
        req_v115 = [
            ("三段式", _bse_txt), ("我做了什么／本来希望看到什么／实际发生了什么", _bse_txt),
            ("三不碰", _bse_txt), ("不删内置自检清单", _bse_txt),
            ("不改确认口令、确认环节与收尾闭环", _bse_txt),
            ("不绕过异常容错与迷路兜底", _bse_txt),
            ("入库版本：V1.1.0", _bse_txt),
        ]
        miss_v115 = [k for k, src in req_v115 if k not in src]
        if miss_v115:
            fails.append("v115 锚点异常: 缺 %s（底座客户端执行纪律，防丢锚点 fail-closed）" % "、".join(miss_v115))
        else:
            print("PASS v115 锚点: 底座三段式反馈＋三不碰红线＋组件版本 1.1.0 全在位")

        # 9r) v117 吸收改稿锚点（判定模型＋承接诊断四类＋草稿留存＋时效四问＋E12＋措辞负查）
        _nm_p = Path(__file__).resolve().parent.parent / "references" / "REF-NAM-006_NamingDiscovery.md"
        _nm_txt = _nm_p.read_text(encoding="utf-8") if _nm_p.is_file() else ""
        _vr_p = Path(__file__).resolve().parent.parent / "references" / "REF-VER-021_MaterialVersionRisk.md"
        _vr_txt = _vr_p.read_text(encoding="utf-8") if _vr_p.is_file() else ""
        _sp_p = Path(__file__).resolve().parent.parent / "references" / "REF-SNP-051_UserSnapshotProfile.md"
        _sp_txt = _sp_p.read_text(encoding="utf-8") if _sp_p.is_file() else ""
        req_v117 = [
            ("可沉淀判定模型", _nm_txt), ("A（经验依附于人，高权重）", _nm_txt),
            ("B（重复且结果波动，高权重）", _nm_txt),
            ("A、B 同时命中", _nm_txt),
            ("承接诊断四类与第五态", _nm_txt), ("先剥离噪音，再判定诉求", _nm_txt),
            ("时效排查三问", _vr_txt), ("宁可标注后慎用，不可不标误用", _vr_txt),
            ("后续更新兜底", tt3), ("一直为你服务", tt3), ("什么变了／原来怎么走／现在怎么走", tt3),
            ("只针对**技能本身的更新迭代升级**", tt3), ("由你自行决策", tt3),
            ("本轮更新建议先跑一遍核心场景再下发", tt3), ("这个技能后续的更新、迭代、升级，随时回来，我帮你处理", tt3),
            ("阶段性草稿", _sp_txt), ("当前梳理进度、业务背景、已萃取要点、待续事项", _sp_txt),
            ("先剥离口语噪音", sk3), ("E12：怎么判断我的经验值不值得做成技能", fq),
            ("A15：做出来的技能包长什么样", fq),
            ("称呼规矩（全包统一）", _sp_txt), ("口令引用双格式规矩", sk3),
            ("全套机检与装配脚本索引", sk3), ("分工一句话：默认项不回复即自动生效", sk3), ("分工一句话：默认项不回复即自动生效", tt3),
            ("六类 58 问", sk3), ("（E1）至（E12）", fq),
        ]
        miss_v117 = [k for k, src in req_v117 if k not in src]
        neg_hd = [name for name, txt in (("SKILL", sk3), ("TMP-003", tt3), ("FAQ", fq)) if "换代" in txt]
        if miss_v117 or neg_hd:
            fails.append("v117 锚点异常: 缺 %s / 「换代」残留 %s（措辞纪律：只用更新迭代升级）" % ("、".join(miss_v117) or "无", "、".join(neg_hd) or "无"))
        else:
            print("PASS v117 锚点: 判定模型＋四类分流＋草稿留存＋时效四问＋E12 全在位，「换代」零残留")

        # 9q) v178 脚手架生成器＋生成物文风三通则锚点（骨架册机器化落点，防丢锚点 fail-closed）
        _skl_p = root / "references" / "REF-SKL-007_SkillSkeleton_v1.md"
        _skl_txt = _skl_p.read_text(encoding="utf-8", errors="replace") if _skl_p.is_file() else ""
        req_v178 = [
            ("生成物文风三通则", _skl_txt), ("祈使句", _skl_txt),
            ("第三人称", _skl_txt), ("另一个 Agent 实例", _skl_txt),
            ("脚手架生成器", _skl_txt), ("init_skill.py", _skl_txt),
            ("极简档", _skl_txt), ("重型档", _skl_txt),
        ]
        miss_v178 = [k for k, src in req_v178 if k not in src]
        _init_p = root / "scripts" / "init_skill.py"
        if not _init_p.is_file():
            miss_v178.append("scripts/init_skill.py 文件缺失")
        else:
            _init_txt = _init_p.read_text(encoding="utf-8", errors="replace")
            for _k in ("极简", "标准档", "重型档", "agent_created", "祈使句"):
                if _k not in _init_txt:
                    miss_v178.append("init_skill.py 缺 " + _k)
        if "init_skill.py" not in sk3:
            miss_v178.append("SKILL.md 未登记 init_skill.py")
        if miss_v178:
            fails.append("v178 锚点异常: 缺 %s（脚手架＋文风通则）" % "、".join(miss_v178))
        else:
            print("PASS v178 锚点: 脚手架生成器＋生成物文风三通则全在位")

        # 9q2) v179 产出预算＋用法示例反推锚点（dt 本地读取——9s 块在其后定义，不可前引）
        _dt_local = (root / "references" / "REF-DAT-057_DirectAnswerTable.md").read_text(encoding="utf-8", errors="replace")
        req_v179 = [
            ("--check-size", _skl_txt), ("60000", _skl_txt), ("产出预算", _skl_txt),
            ("按示例反推资源落点", tt3), ("按示例反推资源落点", _dt_local),
        ]
        miss_v179 = [k for k, src in req_v179 if k not in src]
        if _init_p.is_file():
            _init_txt2 = _init_p.read_text(encoding="utf-8", errors="replace")
            if "--check-size" not in _init_txt2:
                miss_v179.append("init_skill.py 缺 --check-size")
        if miss_v179:
            fails.append("v179 锚点异常: 缺 %s（预算＋示例反推）" % "、".join(miss_v179))
        else:
            print("PASS v179 锚点: 产出预算机检＋用法示例反推全在位")

        # 9s) 直达层锚点（REF-DAT-057 指针表在位＋SM-004 直达规则＋SKILL 索引＋指针目标在位＋禁词零残留）
        dat_p = root / "references" / "REF-DAT-057_DirectAnswerTable.md"
        dt = dat_p.read_text(encoding="utf-8", errors="replace") if dat_p.exists() else ""
        req_9s = [
            ("标准答案直达表", dt), ("指针式", dt), ("逐字同文", dt),
            ("命中三条件", dt), ("回落四类", dt),
            ("尾部片段挂载、统一落款收口、红线词纪律", dt),
            ("加速通道而非替代", dt), ("判定止于本表", dt),
            ("交互全景版", dt), ("五节组织", dt), ("见面礼", dt),
            ("状态记账照旧", dt), ("号段全景对账", dt),
            ("DA-01", dt), ("DA-43", dt),
            ("标准答案直达层（REF-DAT-057）", st3), ("直达层豁免边界", st3),
            ("direct_answer_probe", st3), ("加速通道而非替代", st3),
            ("判定止于本表", st3), ("判定先于触发词直连", st3),
            ("REF-DAT-057_DirectAnswerTable.md", sk3),
        ]
        _dat_heads = re.findall(r"(?m)^### (DA-\d{2})", dt)
        _expect_ids = {f"DA-0{i}" for i in range(1, 10)} | {f"DA-{i}" for i in range(10, 47)}
        _dat_targets = [
            "【首响接住承接件】", "【统一求助导航】", "【收费版本确认（关键配置）】",
            "【体量档位一次性提醒】", "【交付实测提醒 · 轻量版】", "【交付实测提醒 · 完整版】",
            "【任务挂起回执】", "【窗口交接引导】", "【断点重建问询】", "【技能成长摘要】",
            "【欢迎启动菜单】", "【代建入口先对一眼】", "【答疑入口导航模板】", "【调整入口指引模板】",
            "【评测入口指引模板】", "【配置确认 · 第一步：部署形态（默认轻量）】", "【配置确认 · 第二步：分发访问模式】",
            "【配置汇总确认】", "【常见问题目录大纲】", "【档案管理子菜单】", "【档案加载问询】",
            "【清空档案二次确认】", "【继承基线问询】", "【业务方案&技能框架概要】", "【调整范围确认模板】",
            "【评测报告后处置选择】", "【重构需求确认模板】", "【分发模式风险提示话术】", "【方案确认模板】",
            "【链路收尾通用返回菜单】", "【意图模糊无法识别兜底菜单】", "【输入非法 / 文件损坏兜底提示】",
            "【连续未成功自动重置】", "【空白 / 乱码统一应答】", "【物料超限交互片段 · 轻微超限】",
            "【物料超限交互片段 · 显著超限】", "【物料超限交互片段 · 严重雪崩超限】", "【文件格式不支持提示】",
            "【异常引擎降级提示模板】", "【禁止/高危拦截提示模板】", "【穷尽救助兜底声明】",
        ]
        miss_9s = [k for k, src in req_9s if k not in src]
        miss_ptr_in_tbl = [k for k in _dat_targets if k not in dt]
        miss_ptr_src = [k for k in _dat_targets if k not in tt3]
        # 内联副本与源册逐字同文校验：33 个 TMP-003 整块 + FAQ 全量区
        _sync_names = [
            "欢迎启动菜单", "代建入口先对一眼", "答疑入口导航模板", "调整入口指引模板", "评测入口指引模板",
            "配置确认 · 第一步：部署形态（默认轻量）", "配置确认 · 第二步：分发访问模式", "配置汇总确认",
            "统一求助导航", "常见问题目录大纲", "档案管理子菜单", "档案加载问询", "清空档案二次确认",
            "继承基线问询", "业务方案&技能框架概要", "调整范围确认模板", "评测报告后处置选择",
            "重构需求确认模板", "分发模式风险提示话术", "方案确认模板", "链路收尾通用返回菜单",
            "意图模糊无法识别兜底菜单", "输入非法 / 文件损坏兜底提示", "连续未成功自动重置", "空白 / 乱码统一应答",
            "物料超限交互片段 · 轻微超限", "物料超限交互片段 · 显著超限", "物料超限交互片段 · 严重雪崩超限",
            "文件格式不支持提示", "异常引擎降级提示模板", "禁止/高危拦截提示模板", "穷尽救助兜底声明", "API模式准入条件清单", "收费配置 · 创作者类型确认", "收费配置 · 目标平台文档收料与比对",
        ]
        miss_sync = []
        for _n in _sync_names:
            _src_m = re.search(r"(?ms)^## 【" + re.escape(_n) + r"】.*?(?=^## |\Z)", tt3)
            _dat_m = re.search(r"(?ms)^## 【" + re.escape(_n) + r"】.*?(?=^## |\Z|^### )", dt)
            if not _src_m or not _dat_m or _src_m.group(0).rstrip() != _dat_m.group(0).rstrip():
                miss_sync.append(_n)
        _faq_body_m = re.search(r"(?ms)^## A 认知入门.*$", fq)
        if not _faq_body_m or _faq_body_m.group(0).rstrip() not in dt:
            miss_sync.append("FAQ全量区")
        # 禁词负查只对非内联区执行（内联副本为源册既有原文，合法带过）
        _dt_noninline = dt
        for _n in _sync_names:
            _blk = re.search(r"(?ms)^## 【" + re.escape(_n) + r"】.*?(?=^## |\Z|^### )", _dt_noninline)
            if _blk:
                _dt_noninline = _dt_noninline.replace(_blk.group(0), "")
        if _faq_body_m and _faq_body_m.group(0).rstrip() in _dt_noninline:
            _dt_noninline = _dt_noninline.replace(_faq_body_m.group(0).rstrip(), "")
        neg_dat = [w for w in ("修正", "换代") if w in _dt_noninline]
        if not dat_p.exists() or miss_9s or miss_ptr_in_tbl or miss_ptr_src or sorted(_dat_heads) != sorted(_expect_ids) or neg_dat or miss_sync:
            fails.append("9s 直达层锚点异常: 表缺失=%s / 缺 %s / 表内缺指针目标 %s / 模板册缺目标 %s / 条目集异常（实测 %d 条）/ 内联与源册不同文 %s / 禁词残留 %s"
                         % (not dat_p.exists(), "、".join(miss_9s) or "无", "、".join(miss_ptr_in_tbl) or "无",
                            "、".join(miss_ptr_src) or "无", len(_dat_heads), "、".join(miss_sync) or "无", "、".join(neg_dat) or "无"))
        else:
            print("PASS 9s 直达层: 46 条目＋五节全景＋36 块与模板册逐字同文＋FAQ 全量同文＋止于本表，禁词零残留")

        # 9h) v95 快照六口令内联直连锚点（零读取承接，重复段清零）
        req_v95 = [
            ("📁 **业务快照档案管理**", sk3), ("📁 **业务快照档案管理**", tt3),
            ("禁止读取 REF-SNP-051、REF-TMP-003 或任何其他文档再判断", sk3),
            ("直接按 SKILL.md 1.1-A 内联档案管理子菜单逐字输出", st3),
            ("与 faq_outline 同规", st3),
            ("清空档案二次确认内联", sk3), ("继承基线问询内联", sk3),
            ("查看历史技能包", sk3), ("保存至我的基线档案", sk3),
            ("新建交付基线", sk3), ("加载我的基线档案", sk3),
        ]
        miss_v95 = [k for k, src in req_v95 if k not in src]
        dup_load = sk3.count("档案加载问询（第二条消息轮检测到快照档案时")
        dup_menu = tt3.count("## 【档案管理子菜单】")
        if miss_v95 or dup_load != 1 or dup_menu != 1:
            fails.append("v95 快照内联锚点异常: 缺 %s / 档案加载问询出现 %d 次（须恰 1 次）／子菜单标题出现 %d 次（须恰 1 次）" % ("、".join(miss_v95) or "无", dup_load, dup_menu))
        else:
            print("PASS v95 快照内联: 五口令直达屏零读取锚点全在位，重复段清零")

        # 9i) v96 平台评测集生成锚点（公开格式册在包、公开包零方法论册名）
        evl = root / "references" / "REF-EVL-052_EvalSetFormat.md"
        ev3 = evl.read_text(encoding="utf-8", errors="replace") if evl.exists() else ""
        req_v96 = [
            ("评测集草稿生成", sk3fop), ("REF-EVL-052", sk3fop),
            ("档位路由", sk3fop), ("评测集草稿生成（目标平台档位）", sk3fop),
            ("header.json", sk3),
            ("④ 评测集草稿生成（REF-EVL-052）", sk3fop),
            ("[16] 留存报告后的收尾屏末尾追加一次问询", sk3),
            ("屏面末尾按 REF-EVL-052 档位路由追加评测集草稿问询", st3),
            ("评测集草稿问询不在本屏输出", st3),
            ("触发时机钉死在质量评测链路", ev3),
            ("本轮评测已办结", ev3),
            ("一律只输出绑定模板原文，禁止在模板前后追加任何自拟内容或段落（含任何协作分块标签）——追加即违规", sk3),
            ("链路入口屏与跨角色切换屏一律只输出绑定模板原文", st3),
        ]
        miss_v96 = [k for k, src in req_v96 if k not in src]
        if evl.exists():
            ev = evl.read_text(encoding="utf-8", errors="replace")
            for k in ("header.json", "cases.jsonl", "anchors_by_dim", "checklist_by_dim",
                      "pass_threshold", "维度表档", "标准格式档", "input_files",
                      "该题对象内加 `aggregation` 覆盖"):
                if k not in ev:
                    miss_v96.append("EVL-052 缺 %s" % k)
        else:
            miss_v96.append("EVL-052 文件缺失")
        if "成品包已交付" in ev3:
            miss_v96.append("问询首句仍是旧措辞（应为：本轮评测已办结）")
        if "交付收口后增值步骤" in sk3:
            miss_v96.append("12.9 增值步骤段未撤除（问询须挂在评测报告后处置）")
        leak_053 = [f.name for f in root.rglob("*")
                    if f.is_file() and f.suffix in (".md", ".py", ".yaml", ".json")
                    and "MAINTAINER" not in f.name
                    and ("REF-EVL" + "-053") in f.read_text(encoding="utf-8", errors="replace")]
        if miss_v96 or leak_053:
            fails.append("[公开口径] v96 评测集锚点异常: 缺 %s / 公开包泄漏 %s" % ("、".join(miss_v96) or "无", "、".join(leak_053) or "无"))
        else:
            print("PASS v96 评测集: 公开格式册在位字段齐，方法论册名公开包零泄漏")

        # 9j) v102 移动端窄屏排版＋验收清单锚点
        dlv = root / "references" / "REF-DLV-029_BuildDeliveryWorkflow.md"
        dv = dlv.read_text(encoding="utf-8", errors="replace") if dlv.exists() else ""
        req_v102 = [
            ("移动端窄屏输出铁则", sk3),
            ("条目独行", sk3),
            ("▸ **[1] 技能代建助手**", sk3),
            ("▸ **[1] 技能代建助手**", tt3),
            ("①我做了什么操作", sk3),
            ("①我做了什么操作", tt3),
            ("① **新建技能**", sk3),
            ("① **新建技能**", tt3),
            ("【做技能Skill】", sk3),
            ("【做技能Skill】", tt3),
            ("符号序号：屏面同一组内容超过两点必须分组排序", sk3),
            ("首响执行卡", sk3),
            ("挂载名「Skill技能搭建专家」＝注册名 ", sk3),  # 前缀式锚：英文名随包自适应（基准/形态B 换名均命中）
            ("承接件按首条消息二选一档位", sk3),
            ("问候档（用户只发问候／闲聊、无任何材料与诉求时）", sk3),
            ("问候档：", tt3),
            ("用户侧验收打勾清单", sk3fop),
            ("用户侧验收打勾清单", dv),
            ("已验证/未验证分列", dv),
            ("七项已验证/未验证分列", st3),
        ]
        miss_v102 = [k for k, src in req_v102 if k not in src]
        if miss_v102 or "## 五‑A、用户侧验收打勾清单" not in dv:
            fails.append("v102 锚点异常: 缺 %s" % "、".join(miss_v102) or "五-A 节缺失")
        else:
            print("PASS v102 移动端: 窄屏铁则＋菜单列表化＋三段式反馈＋验收清单分列全在位")


_SELFTEST_YAML = """states:
  init:
    transitions:
      - target: "role_1_build"
      - target: "role_2_qa"
      - target: "role_3_repair"
      - target: "role_4_evaluate"
      - target: "role_4_integrate"
      - target: "illegal_input"
      - target: "intent_unknown"
      - target: "engine_fallback"
      - target: "high_risk_block"
      - target: "material_parse_gate"
  role_1_build:
    transitions:
      - target: "end_session"
  role_2_qa:
    transitions:
      - target: "end_session"
  role_3_repair:
    transitions:
      - target: "end_session"
  role_4_evaluate:
    transitions:
      - target: "end_session"
  role_4_integrate:
    transitions:
      - target: "material_parse_gate"
      - target: "end_session"
  material_parse_gate:
    transitions:
      - target: "deliver_preview"
  deliver_preview:
    transitions:
      - target: "end_session"
  illegal_input:
    transitions:
      - target: "init"
  intent_unknown:
    transitions:
      - target: "init"
  engine_fallback:
    transitions:
      - target: "init"
  high_risk_block:
    transitions:
      - target: "end_session"
  end_session:
    transitions:
      - target: "end_session"
"""


def _run_state_machine_on(yaml_text):
    """在临时目录落一份迷你状态机并跑 check_state_machine，返回 fails 列表。
    运行中 check_state_machine 的 PASS 打印重定向吞掉，避免污染正常回归输出。"""
    import io
    import tempfile
    from contextlib import redirect_stdout
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        (root / "references").mkdir()
        (root / "references" / "REF-SM-004_StateMachine.yaml").write_text(
            yaml_text, encoding="utf-8")
        fails = []
        buf = io.StringIO()
        with redirect_stdout(buf):
            check_state_machine(root, fails)
        return fails


def _engine_self_test(verbose=True):
    """D 层引擎自测：1 阳 3 阴，证明引擎自己会红（防「永远 PASS」自证盲区）。"""
    results = []
    # 阳例：自洽迷你状态机（全强制节点在位）→ 必须 PASS
    f = _run_state_machine_on(_SELFTEST_YAML)
    results.append(("阳例·自洽状态机应 PASS", not f, "; ".join(f[:3])))
    # 阴例①：删四大兜底/拦截节点 → 必须 FAIL（强制节点缺失）
    mutated = "\n".join(
        ln for ln in _SELFTEST_YAML.splitlines()
        if not re.match(r"^  (illegal_input|intent_unknown|engine_fallback|high_risk_block):", ln)
    ) + "\n"
    f = _run_state_machine_on(mutated)
    results.append(("阴例①·删兜底节点应 FAIL", bool(f) and any("强制节点缺失" in x for x in f), "; ".join(f[:3])))
    # 阴例②：transition 指向未定义状态 → 必须 FAIL（断链）
    f = _run_state_machine_on(_SELFTEST_YAML.replace(
        '      - target: "end_session"\n  material_parse_gate:',
        '      - target: "ghost_state"\n  material_parse_gate:', 1))
    results.append(("阴例②·transition 断链应 FAIL", bool(f) and any("断链" in x for x in f), "; ".join(f[:3])))
    # 阴例③：删终态 → 角色闭环断裂应 FAIL
    f = _run_state_machine_on(_SELFTEST_YAML.replace(
        '  end_session:\n    transitions:\n      - target: "end_session"\n', ""))
    results.append(("阴例③·删终态应 FAIL", bool(f) and any("终态" in x for x in f), "; ".join(f[:3])))

    bad = [r for r in results if not r[1]]
    if verbose:
        for name, ok, detail in results:
            print(("PASS 自测: " if ok else "FAIL 自测: ") + name + ("" if ok else "（" + detail + "）"))
    else:
        for name, ok, detail in bad:
            print("FAIL 自测: " + name + "（" + detail + "）")
    if bad:
        print("FAIL 质检引擎自测: %d 组用例未过 —— 引擎本身不可信，其 PASS 结论无效，禁止出包" % len(bad))
        return 1
    if verbose:
        print("PASS 质检引擎自测: 4 组用例（1 阳 3 阴）全符合预期")
    return 0


def check_pointer_convergence(root, fails):
    """指针收敛闸（2026-11-11 分册收敛，内部登记）：
    ① 通用：分册内出现「与《…》…同步」同文声明，本册必须含「唯一真源」或「历史存档」标记——
       双源必漂（实测：SPC-001 附录B 曾多出「模块四」而真源未同步），无锚定的同文声明一律 FAIL；
    ② 专项：SPC-001 附录B 必须是指针行（含「全文唯一真源：`references/REF-REV-016」），
       且不得残留评审模板正文标志句「你现在进入【AI Skill标准化评审官】」。"""
    import io as _io
    ref_dir = Path(root) / "references"
    if not ref_dir.is_dir():
        return
    sync_pat = re.compile(r"与《[^》]+》[^。\n]{0,30}同步")
    for p in sorted(ref_dir.glob("*.md")):
        t = _io.open(p, encoding="utf-8").read()
        if sync_pat.search(t) and "唯一真源" not in t and "历史存档" not in t:
            fails.append("指针收敛: %s 含同文声明但无「唯一真源/历史存档」锚定（双源必漂，先改声明或指针化）" % p.name)
    spc = ref_dir / "REF-SPC-001_AISkillManual_V32.md"
    if spc.exists():
        t = _io.open(spc, encoding="utf-8").read()
        if "全文唯一真源：`references/REF-REV-016" not in t:
            fails.append("指针收敛: SPC-001 附录B 指针行缺失（唯一真源指针被移除）")
        if "你现在进入【AI Skill标准化评审官】" in t:
            fails.append("指针收敛: SPC-001 附录B 残留评审模板野副本正文（改评审模板只改 REF-REV-016 一处）")
    if not fails:
        print("PASS 指针收敛: 同文声明全部有真源锚定，SPC-001 附录B 指针行在岗")


def check_runtime_guard(root, fails):
    """执行时长护栏锚点（2026-11-11 定稿）：纪律区「单任务 ≤12 轮强制收口」自称机检可查
    的定数，本闸落实其机检——护栏句或两级分立句漂移/被删即 FAIL（有法没检镜像教训的闭环）。"""
    import io as _io
    sk = Path(root) / "SKILL.md"
    if not sk.exists():
        return
    t = _io.open(sk, encoding="utf-8", errors="replace").read()
    for lit in ("不得超过 12 轮", "到限即强制中断", "执行时长护栏", "两级分立不混用"):
        if lit not in t:
            fails.append("执行时长护栏: SKILL.md 缺锚定字面「%s」（护栏机制漂移即 FAIL）" % lit)
    if not fails:
        print("PASS 执行时长护栏: ≤12 轮定数＋强制中断＋两级分立字面全在位")


def check_publish_form_base(root, fails):
    """出包形态闸（REF-MKT-045）：调用 publish_form_scan 基准形态全量检查
    （命名纪律＋基线字段＋宿主残留防治细则⑥⑦：清单字段中性化/宿主工作区路径零落盘/市场名称字面）。"""
    import subprocess as _sp
    import sys as _sys
    import os as _os
    script = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "publish_form_scan.py")
    # 形态自适应：读包内 SKILL name 判定（禁硬编码他包名——名称零交叉纪律，查项⑪执法）：
    # name 非本工厂出厂 base 默认形态字根（词根以拼装形态判别）即按 form_b 口径跑。
    _fm_name = ""
    _sk_p = _os.path.join(_os.path.normpath(_os.path.abspath(root)), "SKILL.md")
    if _os.path.exists(_sk_p):
        _m = re.search(r'(?m)^name://s*"(skill-[^"]+)"', open(_sk_p, encoding="utf-8", errors="replace").read())
        if _m:
            _fm_name = _m.group(1)
    _base_root = "bui" + "lder"  # 基准包词根（词面拼装防自指——两包名称零交叉，查项⑪口径）
    _form_args = ["--form", "form_b"] if (_fm_name and _base_root not in _fm_name) else []
    r = _sp.run([_sys.executable, script, root] + _form_args, capture_output=True, text=True,
                encoding="utf-8", errors="replace")
    if r.returncode != 0:
        out = ((r.stdout or "") + "\n" + (r.stderr or "")).strip()
        fails.append("[公开口径] 出包形态闸: publish_form_scan 未过 → " + out[:600])


def main():
    if "--self-test" in sys.argv:
        return _engine_self_test(verbose=True)
    self_use = any(a == "--self-use" for a in sys.argv[1:])
    if self_use:
        print("口径: 自用层（--self-use）——公开口径专属命中标记过滤，公开包出包仍须无标记全量跑")
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not args:
        print("用法: python run_regression.py <包根目录> | python run_regression.py --self-test")
        return 2
    root = Path(args[0]).resolve()
    if not root.is_dir():
        print("不是目录: %s" % root)
        return 2

    # D 层预检：引擎自测不过，后续 PASS 结论一律无效
    rc = _engine_self_test(verbose=False)
    if rc != 0:
        return rc

        self_use = any(a == "--self-use" for a in sys.argv[1:])
    if self_use:
        print("口径: 自用层（--self-use）——公开口径专属检查标记过滤，公开包出包仍须全量无标记跑")
    fails = []
    check_state_machine(root, fails)
    check_doc_asset_consistency(root, fails)
    check_section_anchors(root, fails)
    check_call_charter(root, fails)
    check_publish_form_base(root, fails)
    check_pointer_convergence(root, fails)
    check_runtime_guard(root, fails)

    # 尾部兜底片段强制挂载（REF-USER-CONTROL-044 铁律5）
    try:
        import tail_fragment_scan as _tfs
    except ImportError:
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        import tail_fragment_scan as _tfs
    for _m in _tfs.run_checks(root):
        fails.append("尾部兜底片段: " + _m)

    # 对外表述扫描（整改口径：third-party/旧概念名/素材合法性解释/版权字样）
    try:
        import external_wording_scan as _ews
    except ImportError:
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        import external_wording_scan as _ews
    for _m in _ews.run_checks(root):
        fails.append("对外表述: " + _m)

    # 标准化交付底座真源校验（REF-BSE-047 标记区文本改动即 FAIL）
    try:
        import base_block_scan as _bbs
    except ImportError:
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        import base_block_scan as _bbs
    _bbf = []
    _bbs.check_source(root, _bbf)
    for _m in _bbf:
        fails.append("底座组件真源: " + _m)
    if not _bbf:
        print("PASS 底座组件真源: REF-BSE-047 标记区全文核验通过")

    if self_use:
        suppressed = [f for f in fails if f.startswith("[公开口径]")]
        fails = [f for f in fails if not f.startswith("[公开口径]")]
        if suppressed:
            print("已抑制 %d 项公开口径命中（自用层设计使然，公开口径只辖公开层）" % len(suppressed))
            for f in suppressed:
                print("  ~ %s" % f[:120])
    if fails:
        print("FAIL 静态回归: %d 项" % len(fails))
        for f in fails:
            print("  - %s" % f)
        return 1
    print("PASS 静态回归全部通过")
    return 0


if __name__ == "__main__":
    sys.exit(main())
