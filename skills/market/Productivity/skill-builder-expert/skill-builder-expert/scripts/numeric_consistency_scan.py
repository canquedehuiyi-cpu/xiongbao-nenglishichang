#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""数字口径一致性扫描（fail-closed）——同一概念多文件数值漂移防回潮闸
背景：评测 R/C/E 三维扣分的共同病根＝同一概念（条目数/区间/题数）在多册给不同值，
用户无法判断以谁为准；根治＝定唯一真源＋本闸看守漂移。
三查（R1-R3）：
R1 直达表条目数：REF-DAT-057 表头声明的条目数与实际 `### DA-` 条目数、最大编号必须一致；
R2 漂移字面零存在：SKILL.md／FAQ.md／references 全部禁再现旧口径字面
  （「43 条目」「DA-01～DA-43」「DA-10～DA-43」「IC1–IC7」及非子集语境的「IC1–IC6」——
   「IC1–IC6 ＋ IC9」「IC1–IC6 必备件」子集展开语境豁免，全闸集真源＝interaction_closure_scan 实跑闸集）；
R3 FAQ 题数：各文件「六类 N 问」声明的 N 必须与 FAQ.md 实际条目数一致且全包同值。
支持 --self-test 阳/阴用例自测（1 阳 2 阴：旧口径字面回潮 / 表头与实数不符）。
"""
import io, re, sys, json, tempfile
from pathlib import Path

DRIFT_LITERALS = ["43 条目", "DA-01～DA-43", "DA-10～DA-43", "IC1–IC7", "IC1–IC10", "条目数恰十"]
IC_SUBSET_PAT = re.compile(r"IC1–IC6(?! ＋ IC9)(?! 必备件)")


def _scan_files(root):
    files = ["SKILL.md", "FAQ.md"] + sorted(str(p.relative_to(root)) for p in (root / "references").glob("*.md"))
    return files


def scan(root):
    root = Path(root)
    if not root.exists():
        return ["扫描根目录不存在"]
    problems = []
    scan_files = _scan_files(root)
    # R1 直达表条目数
    dat = root / "references" / "REF-DAT-057_DirectAnswerTable.md"
    if not dat.exists():
        return ["REF-DAT-057 缺失"]
    dt = io.open(dat, encoding="utf-8").read()
    m = re.search(r"本表共 (\d+) 条目（DA-01～DA-(\d+)）", dt)
    if not m:
        return ["REF-DAT-057 表头行缺条目数声明（真源行不在位）"]
    declared, max_declared = int(m.group(1)), int(m.group(2))
    ids = [int(x) for x in re.findall(r"(?m)^### DA-(\d{2})", dt)]
    actual, max_actual = len(ids), (max(ids) if ids else 0)
    if declared != actual:
        problems.append("R1 表头声明 %d 条目，实际 %d 条（真源行与实数不符）" % (declared, actual))
    if max_declared != max_actual:
        problems.append("R1 表头声明 DA-01～DA-%02d，实际最大编号 DA-%02d" % (max_declared, max_actual))
    # R2 漂移字面
    for rel in scan_files:
        p = root / rel
        if not p.exists():
            continue
        t = io.open(p, encoding="utf-8").read()
        for lit in DRIFT_LITERALS:
            if lit in t:
                problems.append("R2 旧口径字面「%s」残留于 %s" % (lit, rel))
        if IC_SUBSET_PAT.search(t):
            problems.append("R2 非子集语境「IC1–IC6」残留于 %s（子集语境须写「IC1–IC6 ＋ IC9」）" % rel)
    # R3 FAQ 题数
    faq = root / "FAQ.md"
    if faq.exists():
        ft = io.open(faq, encoding="utf-8").read()
        actual_faq = len(re.findall(r"(?m)^\*\*[A-F]\d{1,2}：", ft))
        stated = set()
        for rel in scan_files + ["references/REF-DAT-057_DirectAnswerTable.md"]:
            p = root / rel
            if not p.exists():
                continue
            for mm in re.finditer(r"六类 (\d+) 问", io.open(p, encoding="utf-8").read()):
                stated.add((rel, int(mm.group(1))))
        bad = [(r, n) for r, n in stated if n != actual_faq]
        if bad:
            problems.append("R3 FAQ 题数漂移：实际 %d 题，声明不符 → %s" %
                            (actual_faq, "、".join("%s=%d" % (r, n) for r, n in sorted(bad))))
    return problems


def main(root):
    problems = scan(root)
    verdict = "PASS" if not problems else "FAIL"
    print(json.dumps({"tool": "numeric_consistency_scan", "problems": problems,
                      "problem_count": len(problems), "verdict": verdict}, ensure_ascii=False))
    return 0 if not problems else 1


def self_test():
    ok = True
    with tempfile.TemporaryDirectory() as td:
        r = Path(td)
        (r / "references").mkdir(parents=True)
        faq_items = "".join("**A%d：问%d**\n答。\n\n" % (i, i) for i in range(1, 59))
        (r / "FAQ.md").write_text(faq_items, encoding="utf-8")
        dat_rows = "".join("### DA-%02d ｜条目%d\n\n| 字段 | 内容 |\n|---|---|\n| 信号族 | x |\n| 答案指针 | y |\n| 挂载标记 | z |\n| 回落条件 | w |\n\n"
                           % (i, i) for i in range(1, 47))
        (r / "references" / "REF-DAT-057_DirectAnswerTable.md").write_text(
            "**本表共 46 条目（DA-01～DA-46），五节组织，一次读取全表。**\n" + dat_rows, encoding="utf-8")
        (r / "SKILL.md").write_text("六类 58 问；五节 46 条目一次读取全表；对话闭环 IC1–IC14。\n", encoding="utf-8")
        problems = scan(r)
        if problems:
            ok = False
            print("阳例未过:", problems)
        # 阴1：旧口径字面回潮
        (r / "SKILL.md").write_text("五节 43 条目一次读取全表；对话闭环出厂必查 IC1–IC6；六类 58 问。\n", encoding="utf-8")
        if not scan(r):
            ok = False
            print("阴1（旧口径回潮应 FAIL）未过")
        # 阴2：表头与实数不符
        (r / "SKILL.md").write_text("六类 58 问。\n", encoding="utf-8")
        (r / "references" / "REF-DAT-057_DirectAnswerTable.md").write_text(
            "**本表共 44 条目（DA-01～DA-44），五节组织，一次读取全表。**\n" + dat_rows, encoding="utf-8")
        if not scan(r):
            ok = False
            print("阴2（表头失真应 FAIL）未过")
    print(json.dumps({"tool": "numeric_consistency_scan", "self_test": "PASS" if ok else "FAIL"},
                     ensure_ascii=False))
    return 0 if ok else 1


if __name__ == "__main__":
    if "--self-test" in sys.argv:
        sys.exit(self_test())
    root = sys.argv[1] if len(sys.argv) > 1 else "."
    sys.exit(main(root))
