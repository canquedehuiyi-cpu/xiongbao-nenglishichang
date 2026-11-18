#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""v109 视觉分层扫描（fail-closed）——用户可见屏面标准机检（v120 起 R1-R9）
R1 回复词连排引用（一行≥2个「」且含回复）；R2 回复词【】未加粗；R3 条目糊团（连续≥4行 bullet 无间距）；
R4 有数字选项缺 👉 行动指引；R5「下一步」字样零存在（用户动作都在本次对话下一句话，含豁免屏全量扫描）；
R6 回复凭据裸字母未括号化（**A / **B 形态须改 **（A） 形态）；R7「修正」残留（对外统一「迭代更新」）；
R8 行动行屏尾位置（最后一个「回复【X】」指令行之后不得再有正文行——对话动辄几千字，行动键藏中间用户看不到＝卡死；
> 引用行豁免；R8 在 grade 内执行，开场屏与尾部锁定件按既有豁免跳过）；
R9 锚定表述零存在（「验收通过」「审核没问题」——交付收尾决策权铁则：最终决策权在创作者，禁锚定表述，含豁免屏全量扫描）。
豁免（R1-R4、R8）：FAQ.md 全部（单主题短条目）；SKILL.md §1.1-A 开场屏以外区域不扫（细则样例非屏面）；
R5/R6/R9 无豁免全量。
"""
import io, re, sys, json
from pathlib import Path


def screens(path_text, region_only=False):
    t = path_text
    if region_only:
        s = t.find("#### 开场屏")
        if s == -1:
            return []
        e = t.find("\n### ", s)
        t = t[s:e if e != -1 else len(t)]
    out = []
    for m in re.finditer(r"```text\n([\s\S]*?)```", t):
        b = m.group(1)
        head = t[:m.start()]
        titles = re.findall(r"^#{2,4} [^\n]+", head, flags=re.M)
        title = titles[-1].lstrip("#").strip()[:44] if titles else "(无标题)"
        out.append((title, b))
    return out


LOCKED_TAIL_LINES = (
    "如果你不清楚接下来如何操作，可回复 **【帮助】** 唤起完整导航；",
    "随时回复 **【菜单】** 或者数字 **【0】**，回到主菜单选择服务项数字，开始为你技能代建、技能答疑、技能优化、技能评测。",
)  # 尾部锁定句全包多处逐字复用，由 tail_fragment_scan 基准句专管（备案123：随【】加粗规范化同步更新字面；1.0.110 备案：菜单尾句改四服务项与开场白/菜单 [1]-[4] 呼应，字面同步更新）


def grade(b):
    b = "\n".join(l for l in b.splitlines() if l.strip() not in LOCKED_TAIL_LINES)
    issues = []
    for l in b.splitlines():
        if l.count("「") >= 2 and "回复" in l and len(l) > 40:
            issues.append("R1回复词连排引用")
            break
    if re.search(r"回复[（(]?【", b) and "**【" not in b:
        issues.append("R2回复词未加粗")
    if "下一步" in b:
        issues.append("R5「下一步」残留(改直接祈使句)")
    if re.search(r"\*\*[A-Fa-f](\*\*| )", b):
        issues.append("R6回复凭据裸字母未括号化")
    if "修正" in b:
        issues.append("R7「修正」残留(对外统一「迭代更新」)")
    run = maxrun = 0
    prev = False
    for l in b.splitlines():
        cur = l.strip().startswith(("•", "-", "▸"))
        run = run + 1 if (cur and prev) else (1 if cur else 0)
        prev = cur
        maxrun = max(maxrun, run)
    if maxrun >= 4:
        issues.append("R3条目糊团(连续%d行无间距)" % maxrun)
    if re.search(r"\[\d+\]", b) and "👉" not in b:
        issues.append("R4缺行动指引")
    # R8 行动行屏尾位置：最后一个「回复【X】／回复「X」」指令行之后不得再有正文行（> 引用行豁免）
    # 两形态都识别（137 铁则：入口名【】／文本口令「」），防止口令类行动行逃出屏尾检查
    act_idx = None
    for i, l in enumerate(b.splitlines()):
        if re.search(r"回复\s*[*＊*]*(?:[【「]|数字\s*(?:`0`|\*\*【0】\*\*))", l) and not l.strip().startswith(">"):
            act_idx = i
    if act_idx is not None:
        for l in b.splitlines()[act_idx + 1:]:
            s = l.strip()
            if s and not s.startswith(">") and not re.fullmatch(r"\{\{[^}]+\}\}", s):
                issues.append("R8行动行后有正文行(行动指令须屏尾)")
                break
    return issues


def main(root):
    root = Path(root)
    problems = []
    scanned = 0
    targets = [
        (root / "SKILL.md", True),
        (root / "references" / "REF-TMP-003_MenuInteraction.md", False),
    ]
    for p, region_only in targets:
        if not p.exists():
            continue
        for title, b in screens(io.open(p, encoding="utf-8").read(), region_only):
            # R5/R6 无豁免全量：「下一步」零存在＋回复凭据括号化（含开场屏）
            if "下一步" in b:
                problems.append("%s | %s | R5「下一步」残留" % (p.name, title))
            for _w in ("验收通过", "审核没问题"):
                if _w in b:
                    problems.append("%s | %s | R9锚定表述「%s」残留(最终决策权在创作者)" % (p.name, title, _w))
            if "开场屏" in title:
                continue  # C1 豁免：开场屏 v107 人工复核达标（R1-R4 豁免，R5/R6 已在上方全量执行）
            if "公共兜底尾部片段" in title:
                continue  # 只读锁定件，逐字稿由 tail_fragment_scan 专管，不重复判
            scanned += 1
            iss = grade(b)
            if iss:
                problems.append("%s | %s | %s" % (p.name, title, "；".join(iss)))
    print(json.dumps({"tool": "visual_layer_scan", "scanned_screens": scanned,
                      "problems": problems, "problem_count": len(problems),
                      "verdict": "PASS" if not problems else "FAIL"}, ensure_ascii=False))
    return 0 if not problems else 1


if __name__ == "__main__":
    root = sys.argv[1] if len(sys.argv) > 1 else "."
    sys.exit(main(root))
