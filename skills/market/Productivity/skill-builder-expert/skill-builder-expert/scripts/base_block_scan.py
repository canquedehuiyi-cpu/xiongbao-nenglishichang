#!/usr/bin/env python3
# base_block_scan.py — 标准化交付底座锚点块完整性扫描（fail-closed，实现 REF-BSE-047）
# 用途：扫描用户成品技能包（目录或 SKILL.md 路径），核验内联底座块齐整性：
#   B1 锚点标题存在且唯一（双底座/缺失均 FAIL）
#   B2 身份基线句在位
#   B3 九节标题齐（【一】~【九】）
#   B4 十项自检齐（□ 逐项，含版本管控机制项）
#   B5 收尾闭环边界句核验（真源文件级：载体为 REF-BSE-047 挂载规范第 4 条——
#      收尾两选项仅单任务办结之后展示，普通流程对话未展示收尾选项不判不达标；
#      定稿挂载件块内不含该边界句，故 B5 只查真源文件，不查成品包块）
#   B6 质检把关项齐（分隔标题行＋五维 □ 逐项：可信程度/可靠性/适用性/规范性/有效性）
# 任意一项缺失 → FAIL 并输出缺陷报告；未检出底座块 → FAIL（挂载缺失）。
# 真源校验：check_source(root) 抽取 REF-BSE-047 标记区文本跑同一核验，真源被改动即 FAIL。
import os
import re
import sys

ANCHOR = "🧩 REF-BSE-047｜标准化技能交付框架"
IDENT = "【基础身份基线】"
IDENT_SENT = "严格执行本节全套交付规范"
SECTIONS = [
    "【一、消息接收与开场白强制",
    "【二、意图确认与分流】",
    "【三、服务菜单与口令纪律】",
    "【四、输出排版与渲染",
    "【五、异常容错与迷路兜底】",
    "【六、分发模式配套",
    "【七、内置自检清单",
    "【八、能力范围说明】",
    "【九、版本迭代管控规范",
]
CHECK_ITEMS = [
    "标准开场白四件齐",
    "消息回执机制",
    "服务菜单与口令路由",
    "意图确认环节",
    "迷路兜底分支",
    "统一排版渲染",
    "边界应答话术",
    "收尾闭环",
    "统一落款",
    "版本管控机制",
]
CLOSING_BOUND = "仅在单任务办结之后展示"
VERSION_DUAL = "对外展示 V1.1.0"
QC_HEADER = "————**【技能质量评测分析｜前置质检把关项】**————"
# B7 术语一致性：固定术语清单在位＋内部代号零外泄（码点拼装，仅备注引言行可提及）
_INTERNAL_CODE = "\u5e95\u5ea7"
REQUIRED_TERMS = [
    "标准化技能交付框架",
    "技能质量评测分析",
    "前置质检把关项",
    "公开免费版",
    "公开收费版",
    "自用模式",
    "私域模式",
]
QC_ITEMS = [
    "□ 可信程度：核查是否存在高危安全风险",
    "□ 可靠性：核查全部异常处理逻辑",
    "□ 适用性：核查功能边界、使用限制是否清晰说明",
    "□ 规范性：核查文档结构、信息密度、术语口径",
    "□ 有效性：核查交互流程衔接、多轮跳转逻辑",
]
BLOCK_START = "<!-- BASE-BLOCK-START -->"
BLOCK_END = "<!-- BASE-BLOCK-END -->"


def extract_block(text):
    """从目标文本抽取底座块：锚点行起，至下一个一级标题或文末。返回 (块文本或None, 锚点数)。"""
    cnt = text.count(ANCHOR)
    if cnt == 0:
        return None, 0
    idx = text.find(ANCHOR)
    line_start = text.rfind("\n", 0, idx) + 1
    nxt = text.find("\n# ", idx)
    block = text[line_start:] if nxt < 0 else text[line_start:nxt]
    return block, cnt


def scan_text(text):
    """对含底座块的文本跑四查（B1-B4），返回缺陷清单（空 = 达标）。锚点缺失/重复也在此报。"""
    fails = []
    block, cnt = extract_block(text)
    if cnt == 0:
        return ["B1 底座锚点块缺失（挂载件未内联，实现 REF-BSE-047）"]
    if cnt > 1:
        fails.append("B1 底座锚点块重复 %d 处（防双底座，挂载规范第3条）" % cnt)
    if block is None:
        return fails + ["B1 底座锚点块无法定位"]
    if IDENT not in block:
        fails.append("B2 身份基线句缺失")
    elif IDENT_SENT not in block:
        fails.append("B2 身份基线约束句缺失（严格执行本节全套交付规范）")
    for s in SECTIONS:
        if s not in block:
            fails.append("B3 节标题缺失: %s】" % s.rstrip("】"))
    joined = block
    for item in CHECK_ITEMS:
        if item not in joined:
            fails.append("B4 自检项缺失: □ %s" % item)
    if QC_HEADER not in joined:
        fails.append("B6 质检把关项标题行缺失（技能质量评测分析·前置质检把关项）")
    for item in QC_ITEMS:
        if item not in joined:
            fails.append("B6 质检把关项缺失: %s…" % item[:14])
    body = "\n".join(l for l in block.split("\n") if not l.lstrip().startswith(">"))
    if _INTERNAL_CODE in body:
        fails.append("B7 对外挂载件正文出现内部代号（仅备注引言行可提及）")
    for t in REQUIRED_TERMS:
        if t not in block:
            fails.append("B7 固定术语缺失: %s" % t)
    return fails


def check_closing_bound(source_text):
    """B5 真源文件级：收尾闭环边界句必须在 REF-BSE-047 文件内（挂载规范第 4 条载体）。"""
    if CLOSING_BOUND not in source_text:
        return ["B5 收尾闭环边界句缺失（仅在单任务办结之后展示——载体: REF-BSE-047 挂载规范第4条）"]
    return []


def find_skill_md(root):
    if os.path.isfile(root) and os.path.basename(root) == "SKILL.md":
        return root
    for dirpath, _dirs, files in os.walk(root):
        if "SKILL.md" in files:
            return os.path.join(dirpath, "SKILL.md")
    return None


def scan_target(path):
    """扫描成品包目录或 SKILL.md 路径，返回缺陷清单。"""
    sk = find_skill_md(path)
    if not sk:
        return ["未找到 SKILL.md（fail-closed）"]
    try:
        text = open(sk, "rb").read().decode("utf-8", errors="replace")
    except OSError as e:
        return ["文件不可读: %s" % e]
    return scan_text(text)


def check_source(root, fails_out):
    """真源校验：抽取 REF-BSE-047 标记区文本跑同一核验＋B5 文件级，真源被改动即 FAIL。"""
    ref = os.path.join(str(root), "references", "REF-BSE-047_DeliveryBaseComponent.md")
    if not os.path.isfile(ref):
        fails_out.append("底座真源文件缺失: references/REF-BSE-047_DeliveryBaseComponent.md")
        return
    text = open(ref, "rb").read().decode("utf-8", errors="replace")
    if BLOCK_START not in text or BLOCK_END not in text:
        fails_out.append("底座真源标记区缺失（BASE-BLOCK-START/END）")
        return
    region = text.split(BLOCK_START, 1)[1].split(BLOCK_END, 1)[0]
    for m in scan_text(region):
        fails_out.append("底座真源校验: " + m)
    for m in check_closing_bound(text):
        fails_out.append(m)
    if VERSION_DUAL not in region:
        fails_out.append("底座真源校验: B4 版本双轨标识缺失（对外展示 V1.0.0）")


def self_test():
    ref = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..",
                       "references", "REF-BSE-047_DeliveryBaseComponent.md")
    results = []
    if not os.path.isfile(ref):
        print("FAIL 底座真源文件缺失，自测无法进行")
        sys.exit(1)
    text = open(ref, "rb").read().decode("utf-8", errors="replace")
    if BLOCK_START not in text or BLOCK_END not in text:
        print("FAIL 底座真源标记区缺失，自测无法进行")
        sys.exit(1)
    sample = text.split(BLOCK_START, 1)[1].split(BLOCK_END, 1)[0]
    # 阳例：真源全文应 PASS（B1-B4 块内四查）
    results.append(("阳例·真源全文应 PASS(B1-B4)", scan_text(sample) == [], "; ".join(scan_text(sample))[:80]))
    # 阳例：真源文件级 B5＋版本双轨标识应 PASS
    b5 = check_closing_bound(text)
    results.append(("阳例·真源文件级收尾边界＋版本双轨标识应 PASS", b5 == [] and VERSION_DUAL in sample,
                    "; ".join(b5)[:80]))
    # 阴例①：删一节 → FAIL(B3)
    bad1 = sample.replace("【三、服务菜单与口令纪律】", "")
    f1 = scan_text(bad1)
    results.append(("阴例①·删节标题应 FAIL(B3)", any("B3" in x for x in f1), "; ".join(f1[:2])))
    # 阴例②：删质检把关项标题行 → FAIL(B6)
    bad2 = sample.replace(QC_HEADER, "")
    f2 = scan_text(bad2)
    results.append(("阴例②·删质检把关项应 FAIL(B6)", any("B6" in x for x in f2), "; ".join(f2[:2])))
    # 阴例③：无锚点 → FAIL(挂载缺失)
    f3 = scan_text("业务正文，无底座块")
    results.append(("阴例③·未挂载应 FAIL", any("B1" in x for x in f3), "; ".join(f3[:2])))
    # 阴例④：双锚点 → FAIL(防双底座)
    f4 = scan_text(sample + "\n\n# 其他\n\n" + sample)
    results.append(("阴例④·双底座应 FAIL", any("B1" in x and "重复" in x for x in f4), "; ".join(f4[:2])))
    # 阴例⑤：正文注入内部代号（备注引言行之外）→ FAIL(B7)
    bad5 = sample.replace("【三、服务菜单与口令纪律】", "【三、服务菜单与口令纪律】\n内部底座说明行")
    f5 = scan_text(bad5)
    results.append(("阴例⑤·正文出现内部代号应 FAIL(B7)", any("B7" in x and "内部代号" in x for x in f5), "; ".join(f5[:2])))
    # 阴例⑥：固定术语被改写 → FAIL(B7)
    bad6 = sample.replace("公开收费版", "公开付费版")
    f6 = scan_text(bad6)
    results.append(("阴例⑥·固定术语改写应 FAIL(B7)", any("B7" in x and "固定术语缺失" in x for x in f6), "; ".join(f6[:2])))
    bad = [r for r in results if not r[1]]
    for name, ok, note in results:
        print(("PASS " if ok else "FAIL ") + name + ((" — " + note) if note else ""))
    if bad:
        sys.exit(1)
    print("PASS 底座锚点块扫描自测（2 阳 6 阴）")


def main():
    argv = sys.argv[1:]
    if "--self-test" in argv:
        self_test()
        return
    if not argv:
        print("用法: base_block_scan.py <成品包目录或SKILL.md路径> | --self-test")
        sys.exit(2)
    fails = scan_target(argv[0])
    if fails:
        print("FAIL 底座锚点块完整性 %d 项：" % len(fails))
        for f in fails:
            print("  - %s" % f)
        sys.exit(1)
    print("PASS 底座锚点块完整性：锚点唯一、身份基线、九节、十项自检、质检把关项五维全齐（含版本管控项·大写V标识）")


if __name__ == "__main__":
    main()
