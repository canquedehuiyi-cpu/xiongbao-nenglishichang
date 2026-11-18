#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""术语裸用消歧闸（term_bare_scan）

把「术语歧义」纳入机检体系（与数字口径漂移同等对待）：
包内「四件套」「三问」必须携带唯一限定前缀，裸用零存在——防同词异义回潮。

规范名（唯一合法形态）：
  四件套：运行时四件套｜验收证据四件套｜报错排查材料四件套｜开场白四件套
  三问：立项三问｜新规则落地三问｜自验证三问｜时效排查三问｜主词判定三问

口径：扫描 SKILL.md ＋ references/*.md（排除本脚本自身与 logs）；
      「四件套/三问」出现时，其紧邻前缀必须命中规范名之一，否则计一次裸用。
fail-closed：任一裸用即 FAIL，报告列出 文件:行。

用法：python term_bare_scan.py [根目录]（默认当前目录）
      python term_bare_scan.py --self-test
"""
import io
import json
import re
import sys
from pathlib import Path

CANON_4 = ["运行时", "验收证据", "报错排查材料", "开场白"]
CANON_3 = ["立项", "新规则落地", "自验证", "时效排查", "主词判定"]
TERMS = {"四件套": CANON_4, "三问": CANON_3}

# 异名禁字面（真源：REF-TER-035 标准写法；本表字面自身豁免——保留旧字面才能拦截它，禁止被任何统一替换波及）
FORBIDDEN_LITERALS = ["API 模式", "轻量内置模式", "API调用模式", "主文件"]


def scan(root):
    """返回问题列表（空 = PASS）。"""
    root = Path(root)
    problems = []
    targets = ["SKILL.md"] + sorted(
        str(p.relative_to(root)).replace("\\", "/")
        for p in root.glob("references/*.md")
    )
    for rel in targets:
        p = root / rel
        if not p.exists():
            continue
        try:
            lines = io.open(p, encoding="utf-8", errors="replace").read().split("\n")
        except OSError:
            continue
        for i, line in enumerate(lines, 1):
            for lit in FORBIDDEN_LITERALS:
                if lit in line:
                    problems.append(
                        "异名禁字面 [%s] 于 %s:%d（按 REF-TER-035 标准写法整改）"
                        % (lit, rel, i)
                    )
            for term, prefixes in TERMS.items():
                for m in re.finditer(re.escape(term), line):
                    head = line[: m.start()]
                    if not any(head.endswith(px) for px in prefixes):
                        problems.append(
                            "术语裸用 [%s] 于 %s:%d（须带限定前缀：%s）"
                            % (term, rel, i, "／".join(prefixes))
                        )
    return problems


def _self_test():
    ok = True
    import tempfile

    with tempfile.TemporaryDirectory() as td:
        r = Path(td)
        (r / "references").mkdir()
        (r / "SKILL.md").write_text(
            "运行时四件套齐备；交付前必跑自验证三问。\n", encoding="utf-8"
        )
        (r / "references" / "a.md").write_text(
            "验收证据四件套逐件留证；立项三问全过。\n", encoding="utf-8"
        )
        # 阳：全带前缀应 PASS
        p = scan(r)
        if p:
            ok = False
            print("阳例（带前缀）应 PASS，实测:", p)
        # 阴1：四件套裸用应 FAIL
        (r / "references" / "a.md").write_text("四件套齐备即进入排查。\n", encoding="utf-8")
        p = scan(r)
        if not p or "四件套" not in p[0]:
            ok = False
            print("阴1（四件套裸用应 FAIL）未过:", p)
        # 阴2：三问裸用应 FAIL
        (r / "references" / "a.md").write_text("对主题过三问。\n", encoding="utf-8")
        p = scan(r)
        if not p or "三问" not in p[0]:
            ok = False
            print("阴2（三问裸用应 FAIL）未过:", p)
        # 阴3：伪前缀（前缀词不在白名单）应 FAIL
        (r / "references" / "a.md").write_text("证据化四件套留证。\n", encoding="utf-8")
        p = scan(r)
        if not p:
            ok = False
            print("阴3（非规范前缀应 FAIL）未过:", p)
    print("PASS term_bare_scan 自测（阳/阴1/阴2/阴3）" if ok else "FAIL term_bare_scan 自测")
    return ok


def main():
    if "--self-test" in sys.argv:
        sys.exit(0 if _self_test() else 1)
    root = sys.argv[1] if len(sys.argv) > 1 else "."
    problems = scan(root)
    out = {
        "tool": "term_bare_scan",
        "problem_count": len(problems),
        "problems": problems[:20],
        "verdict": "PASS" if not problems else "FAIL",
    }
    print(json.dumps(out, ensure_ascii=False))
    sys.exit(0 if not problems else 1)


if __name__ == "__main__":
    main()
