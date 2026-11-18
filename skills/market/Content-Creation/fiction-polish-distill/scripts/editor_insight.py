#!/usr/bin/env python3
"""editor_insight.py — 补充引擎（1.0.6 新增：X-1~X-3）

    outline  <大纲.md> <正文.md>     大纲↔正文对照：大纲要点在正文中的覆盖情况（X-1）
    title    <标题> [<简介.md>]      标题/简介/章名钩子检测（X-2）
    read     <正文.md>               模拟编辑试读：编辑视角的快速评估（X-3）

说明: 全部为确定性本地规则（零外部依赖），输出为自查参考，非权威判定。
"""

import json
import re
import sys

from common import VERSION, read_text


# ---------- X-1 大纲↔正文对照 ----------

def outline_check(outline, body):
    """大纲要点在正文中的覆盖检测。"""
    o_points = [p.strip() for p in re.split(r"\n+", outline) if p.strip()]
    o_points = [re.sub(r"^[\d一二三四五六七八九十、.．\-*•·\s]+", "", p) for p in o_points]
    o_points = [p for p in o_points if len(p) >= 2]
    if not o_points:
        return {"status": "skip", "reason": "大纲为空"}
    body_clean = re.sub(r"\s", "", body)
    missing = []
    for p in o_points:
        key = re.sub(r"\s", "", p)
        # 取要点前 6 字作关键词；过短则整条判断
        kw = key[:6]
        if kw and kw not in body_clean:
            missing.append(p)
    total = len(o_points)
    covered = total - len(missing)
    rate = round(covered / total * 100, 1) if total else 0
    return {
        "status": "ok",
        "version": VERSION,
        "outline_points": total,
        "covered": covered,
        "coverage_rate": rate,
        "missing_points": missing[:8],
        "advice": ("大纲要点已基本覆盖" if rate >= 80
                   else f"以下大纲要点在正文中未找到对应内容（覆盖率 {rate}%），建议补写或调整章节: " + "；".join(missing[:5])),
    }


# ---------- X-2 标题/简介钩子 ----------

_TITLE_HOOK = re.compile(r"死|杀|血|夜|暗|谜|局|王|帝|仙|魔|龙|战|惊|诡|罪|囚|誓|劫|逆|重生|穿越|系统|大佬|他?她?终于")


def title_check(title, blurb=""):
    """标题钩子检测。"""
    if not title:
        return {"status": "skip", "reason": "未提供标题"}
    hooks = _TITLE_HOOK.findall(title)
    ok = len(hooks) >= 1
    issues = []
    if len(title) < 2:
        issues.append("标题过短（<2字），信息量不足")
    if not ok:
        issues.append("标题缺乏钩子词（冲突/悬念/卖点），建议含冲突或卖点关键词")
    blurb_ok = None
    if blurb:
        sents = [s.strip() for s in re.split(r"(?<=[。！？；.!?])", blurb) if s.strip()]
        blurb_ok = len(sents) >= 2
        if not blurb_ok:
            issues.append("简介过短（<2句），建议用 2-3 句呈现冲突与看点")
        if not re.search(r"[?？]|却|但|竟然|没想到|反转", blurb):
            issues.append("简介缺少悬念钩子，建议以'冲突+转折+悬念'收尾")
    return {
        "status": "ok",
        "version": VERSION,
        "title": title,
        "hook_words": list(set(hooks)),
        "title_pass": ok,
        "blurb_pass": blurb_ok,
        "issues": issues,
        "advice": "标题达标" if ok and not issues else "标题/简介需优化: " + "；".join(issues),
    }


# ---------- X-3 模拟编辑试读 ----------

def editor_read(text):
    """模拟编辑试读：编辑视角快速评估（开篇/节奏/对白/收尾）。"""
    sents = [s.strip() for s in re.split(r"(?<=[。！？；.!?])", text) if s.strip()]
    if not sents:
        return {"status": "skip", "reason": "空文本"}
    notes = []
    score = 70  # 编辑基础分
    # 开篇
    head = "".join(sents[:3])
    if re.search(r"众所周知|在当今|随着.{0,8}的发展|这是一个", head):
        notes.append("开篇有铺垫式开场，编辑通常偏好'直接进入场景'")
        score -= 10
    else:
        notes.append("开篇直接切入场景，符合编辑偏好")
        score += 5
    # 节奏：段落/句长
    lens = [len(s) for s in sents]
    if len(lens) >= 6:
        mid = sum(1 for l in lens if 8 <= l <= 30) / len(lens)
        if mid > 0.8:
            notes.append("句式过于均匀，节奏平缓，建议长短交错")
            score -= 8
    # 对白
    if any(("“" in s or '"' in s or "「" in s) for s in sents):
        notes.append("含对白，注意对白需伴随动作/神态")
    else:
        notes.append("全文无对白，独白/叙述占比过高，建议加入对话增强可读性")
        score -= 5
    # 收尾
    tail = sents[-1] if sents else ""
    if re.search(r"[?？]|却|但|没想到|然而", tail):
        notes.append("结尾带钩子/悬念，适合连载")
        score += 5
    else:
        notes.append("结尾为平铺收束，连载场景建议留钩子")
        score -= 3
    score = max(0, min(100, score))
    return {
        "status": "ok",
        "version": VERSION,
        "editor_score": score,
        "notes": notes,
        "verdict": "建议修改后提交" if score < 75 else "可提交（编辑视角）",
        "disclaimer": "模拟编辑试读为本地规则评估，不代表真实编辑意见。",
    }


def main(argv):
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__)
        return 0
    cmd = argv[0]
    args = [a for a in argv[1:] if not a.startswith("--")]
    if cmd == "outline" and len(args) >= 2:
        print(json.dumps(outline_check(read_text(args[0]), read_text(args[1])), ensure_ascii=False, indent=2))
        return 0
    if cmd == "title" and args:
        blurb = read_text(args[1]) if len(args) >= 2 else ""
        print(json.dumps(title_check(args[0], blurb), ensure_ascii=False, indent=2))
        return 0
    if cmd == "read" and args:
        print(json.dumps(editor_read(read_text(args[0])), ensure_ascii=False, indent=2))
        return 0
    print(f"未知命令: {cmd}（可用: outline/title/read）")
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
