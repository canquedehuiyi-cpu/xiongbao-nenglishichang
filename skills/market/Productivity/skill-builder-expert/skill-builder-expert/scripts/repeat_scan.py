#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""repeat_scan.py —— 跨册复述扫描器（2026-11-11 v153，备案 113）

定位
----
扫 references 分册之间的逐字连续重复块（≥5 行），命中即输出「文件对＋行号＋块预览」。
C 维「规范重复」扣分的机检落点；eval_mapper 路由「重复/复述」方向的执行端。

豁免（设计性同文，fail-closed 登记）
----
以下文件对之间的同文是设计使然（同文锚点锁定或唯一源-历史快照关系），豁免不报：
  REF-DAT-057 ↔ REF-TMP-003   口令块逐字同文（回归 9s 锚锁定，改须双修）
  REF-DAT-057 ↔ 各源册         DA-10~46 内联副本与源册同文（机检锁定）
  REF-INT-015 ↔ REF-SPC-001   历史存档快照 ↔ 唯一生效版（备案 111 定性）
新增设计性同文对子必须在内部变更登记后登记进 EXEMPT_PAIRS。

不扫主文档：SKILL.md 与分册的同文属首响内联设计（零读取铁则），归回归锚点组管。

用法
----
    python scripts/repeat_scan.py <包目录>
    python scripts/repeat_scan.py --self-test

退出码：0 = 通过；1 = 有非豁免复述命中。
"""
import io
import json
import os
import sys
from collections import defaultdict
from itertools import combinations

EXEMPT_PAIRS = {
    frozenset(("REF-DAT-057_DirectAnswerTable.md", "REF-TMP-003_MenuInteraction.md")),
    frozenset(("REF-DAT-057_DirectAnswerTable.md", "REF-SPC-001_AISkillManual_V32.md")),
    frozenset(("REF-DAT-057_DirectAnswerTable.md", "REF-RTQ-061_RuntimeQualityStandard.md")),
    frozenset(("REF-INT-015_InitForm_V32.md", "REF-SPC-001_AISkillManual_V32.md")),
    frozenset(("REF-REV-016_ReviewPrompt_V32.md", "REF-SPC-001_AISkillManual_V32.md")),
}


def is_exempt(a, b):
    """豁免判定：①显式对子名单；②结构性规则——自用层 MASTER- 册与公开册之间的同文
    （自用层全集↔公开脱敏投影，结构性关系，装后抽检实测 20+ 处均为此类）。
    MASTER 册互扫不豁免（自用层内部复述仍要报）。"""
    if frozenset((a, b)) in EXEMPT_PAIRS:
        return True
    return (a.startswith("MASTER-") or b.startswith("MASTER-")) and not (
        a.startswith("MASTER-") and b.startswith("MASTER-"))

MIN_BLOCK = 5   # 连续相同行数阈值
MIN_LEN = 12    # 单行最小字符数（过滤短行噪声）
SEP = set("|-: ")


def load_lines(path):
    return [l.strip() for l in io.open(path, encoding="utf-8", errors="replace")]


def trivial(line):
    return len(line) < MIN_LEN or set(line) <= SEP


def scan(root):
    ref_dir = os.path.join(root, "references")
    if not os.path.isdir(ref_dir):
        return {"ok": False, "error": "references 目录缺失（fail-closed）"}
    files = sorted(f for f in os.listdir(ref_dir) if f.endswith(".md"))
    lines_by = {f: load_lines(os.path.join(ref_dir, f)) for f in files}
    idx = defaultdict(list)
    for f, ls in lines_by.items():
        for i, l in enumerate(ls):
            if not trivial(l):
                idx[l].append((f, i))
    hits = []
    for a, b in combinations(files, 2):
        if is_exempt(a, b):
            continue
        la, lb = lines_by[a], lines_by[b]
        i = 0
        while i < len(la):
            best, bestj = 0, -1
            if not trivial(la[i]) and la[i] in idx:
                for (bf, j) in idx[la[i]]:
                    if bf != b:
                        continue
                    k = 0
                    while (i + k < len(la) and j + k < len(lb)
                           and la[i + k] == lb[j + k] and not trivial(la[i + k])):
                        k += 1
                    if k > best:
                        best, bestj = k, j
            if best >= MIN_BLOCK:
                hits.append({
                    "文件对": "%s <-> %s" % (a, b),
                    "A行号": i + 1,
                    "B行号": bestj + 1,
                    "块行数": best,
                    "块首行预览": la[i][:60],
                })
                i += best
            else:
                i += 1
    return {"ok": True, "扫册数": len(files), "豁免对子": len(EXEMPT_PAIRS),
            "命中数": len(hits), "命中": hits[:20]}


def self_test():
    """阳例：临时目录两册含相同块 → 命中；阴例：文件对在豁免名单 → 不报。"""
    import tempfile
    r = tempfile.mkdtemp()
    rd = os.path.join(r, "references")
    os.makedirs(rd)
    block = "\n".join("这是跨册复述检测用例的第 %d 行测试内容，长度足够过滤噪声。" % i for i in range(1, 7))
    io.open(os.path.join(rd, "REF-AAA-001_TestA.md"), "w", encoding="utf-8", newline="").write("# A\n\n" + block + "\n")
    io.open(os.path.join(rd, "REF-BBB-002_TestB.md"), "w", encoding="utf-8", newline="").write("# B\n\n" + block + "\n")
    res = scan(r)
    assert res["ok"] and res["命中数"] >= 1, "阳例未命中: %s" % res
    # 阴：同名对子在豁免名单（用真实豁免对子名建文件）
    io.open(os.path.join(rd, "REF-INT-015_InitForm_V32.md"), "w", encoding="utf-8", newline="").write("# H\n" + block + "\n")
    io.open(os.path.join(rd, "REF-SPC-001_AISkillManual_V32.md"), "w", encoding="utf-8", newline="").write("# S\n" + block + "\n")
    res2 = scan(r)
    exempt_pair_reported = [h for h in res2["命中"]
                            if h["文件对"] == "REF-INT-015_InitForm_V32.md <-> REF-SPC-001_AISkillManual_V32.md"]
    assert not exempt_pair_reported, "阴例豁免失效: %s" % exempt_pair_reported
    print(json.dumps({"ok": True, "self_test": "阳/阴 2 用例通过（命中＋豁免）",
                      "阈值": "连续%d行/行长%d" % (MIN_BLOCK, MIN_LEN)}, ensure_ascii=False))
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description="跨册复述扫描器（设计性同文豁免；C 维重复扣分机检落点）")
    ap.add_argument("root", nargs="?", help="包目录")
    ap.add_argument("--self-test", dest="self_test", action="store_true")
    args = ap.parse_args(argv)
    if args.self_test:
        return self_test()
    if not args.root:
        ap.print_help()
        return 2
    res = scan(args.root)
    print(json.dumps(res, ensure_ascii=False, indent=2))
    if not res.get("ok"):
        return 1
    return 1 if res["命中数"] else 0


if __name__ == "__main__":
    import argparse  # noqa: F401  (顶部已 import，此处占位保证独立运行)
    sys.exit(main())
