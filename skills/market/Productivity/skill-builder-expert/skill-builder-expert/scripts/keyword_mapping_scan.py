#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""v120 关键词-反应映射扫描（fail-closed）——屏内每个让用户回复的关键词必须有对应反应
背景：屏内配了关键词而用户回复后无对应反应＝用户卡死；关键词与反应映射必须逐一配齐并由机检看守。
规则：屏面指令「回复【X】」（X≤14 字、非占位符）中的 X 必须在 REF-SM-004_StateMachine.yaml、
REF-DAT-057_DirectAnswerTable.md、SKILL.md 任一文件字面出现——否则判定无映射 FAIL。
扫描范围：REF-TMP-003 全部 text 块 ＋ SKILL.md §1.1-A 开场屏区 text 块（与 visual_layer_scan 同口径）。
范围外：数字选项（回复 [n]）由状态机 menu_number_map 专管，不在本扫描范围；FAQ 问法关键词不属屏面指令，不扫。
支持 --self-test 阳/阴用例自测（1 阳 2 阴：映射缺失 / 扫描目标缺失）。
"""
import io, re, sys, json, tempfile
from pathlib import Path

SCAN_TARGETS = [
    ("references/REF-TMP-003_MenuInteraction.md", False),
    ("SKILL.md", True),  # region_only：仅 §1.1-A 开场屏区
]
MAPPING_TARGETS = [
    "references/REF-SM-004_StateMachine.yaml",
    "references/REF-DAT-057_DirectAnswerTable.md",
    "SKILL.md",
]
KW_PAT = re.compile(r"回复\s*[*＊*]*【([^【】{}]{1,14})】")


def _blocks(text, region_only):
    t = text
    if region_only:
        s = t.find("#### 开场屏")
        if s == -1:
            return []
        e = t.find("\n### ", s)
        t = t[s:e if e != -1 else len(t)]
    return [m.group(1) for m in re.finditer(r"```text\n([\s\S]*?)```", t)]


def scan(root):
    root = Path(root)
    if not root.exists():
        return None, ["扫描根目录不存在"]
    pool = ""
    for rel in MAPPING_TARGETS:
        p = root / rel
        if p.exists():
            pool += io.open(p, encoding="utf-8").read()
    if not pool:
        return None, ["映射目标文件全部缺失"]
    problems = []
    kws = {}
    for rel, region_only in SCAN_TARGETS:
        p = root / rel
        if not p.exists():
            problems.append("%s 缺失" % rel)
            continue
        for b in _blocks(io.open(p, encoding="utf-8").read(), region_only):
            for m in KW_PAT.finditer(b):
                kws.setdefault(m.group(1), []).append(rel)
    for kw in sorted(kws):
        if kw not in pool:
            problems.append("关键词【%s】出现在 %s 但状态机/直达表/SKILL 均无字面映射（用户回复无反应即卡死）"
                            % (kw, "、".join(sorted(set(kws[kw])))))
    return len(kws), problems


def main(root):
    n, problems = scan(root)
    verdict = "PASS" if not problems else "FAIL"
    print(json.dumps({"tool": "keyword_mapping_scan", "keywords": n or 0,
                      "problems": problems, "problem_count": len(problems),
                      "verdict": verdict}, ensure_ascii=False))
    return 0 if not problems else 1


def self_test():
    ok = True
    with tempfile.TemporaryDirectory() as td:
        r = Path(td)
        (r / "references").mkdir(parents=True)
        # 阳：屏内关键词在状态机有映射 → PASS
        (r / "references" / "REF-TMP-003_MenuInteraction.md").write_text(
            "## 【屏A】\n```text\n👉 回复 **【确认框架】** 继续。\n```\n", encoding="utf-8")
        (r / "references" / "REF-SM-004_StateMachine.yaml").write_text(
            'desc: "用户回复【确认框架】后进入构建"\n', encoding="utf-8")
        (r / "SKILL.md").write_text("#### 开场屏\n```text\n占位\n```\n", encoding="utf-8")
        n, problems = scan(r)
        if problems or n != 1:
            ok = False
            print("阳例未过:", n, problems)
        # 阴1：关键词无任何映射 → FAIL
        (r / "references" / "REF-TMP-003_MenuInteraction.md").write_text(
            "## 【屏B】\n```text\n👉 回复 **【幽灵词】** 继续。\n```\n", encoding="utf-8")
        n, problems = scan(r)
        if not problems:
            ok = False
            print("阴1（映射缺失应 FAIL）未过")
        # 阴2：映射目标全缺 → FAIL
        (r / "references" / "REF-SM-004_StateMachine.yaml").unlink()
        n, problems = scan(r)
        if not problems:
            ok = False
            print("阴2（映射目标缺失应 FAIL）未过")
    print(json.dumps({"tool": "keyword_mapping_scan", "self_test": "PASS" if ok else "FAIL"},
                     ensure_ascii=False))
    return 0 if ok else 1


if __name__ == "__main__":
    if "--self-test" in sys.argv:
        sys.exit(self_test())
    root = sys.argv[1] if len(sys.argv) > 1 else "."
    sys.exit(main(root))
