# -*- coding: utf-8 -*-
"""
verify_d3.py —— D3「只留骨架」产出自检（纯标准库·零第三方依赖）

D3 = 框架自用（只留模型/结构/清单/行动项），不保留原文长句与金句。
本脚本对文本类产物做启发式扫描：
  - 含中文引号（""「」『』）且超长 → 疑似原文引用
  - 超长无引号行文 → 疑似原文长句
命中即告警；默认 WARN（exit 0），--strict 时 exit≠1 便于门禁拦截。

用法:
  python verify_d3.py --files out/outline.md out/outline.txt [--strict]
"""
import sys, os, argparse

QUOTES = ("“", "”", "「", "」", "『", "』", '"', "'")
MAX_Q = 60      # 带引号的超长阈值（字符）
MAX_PLAIN = 120  # 无引号超长阈值（字符）


def scan(path, max_q=MAX_Q, max_plain=MAX_PLAIN):
    low = path.lower()
    if low.endswith((".md", ".txt")):
        text = open(path, encoding="utf-8", errors="replace").read()
    elif low.endswith(".docx"):
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from docx_ingest import extract_docx
        text = "\n".join(extract_docx(path))
    else:
        return []
    hits = []
    for ln in text.splitlines():
        ln = ln.strip()
        core = ln.lstrip("-•*0123456789.、（）() \t")
        if not core:
            continue
        has_q = any(q in core for q in QUOTES)
        if has_q and len(core) > max_q:
            hits.append(core[:80])
        elif len(core) > max_plain:
            hits.append(core[:80])
    return hits


def main():
    ap = argparse.ArgumentParser(description="D3 只留骨架自检")
    ap.add_argument("--files", required=True, nargs="+")
    ap.add_argument("--strict", action="store_true",
                    help="命中即 exit≠0（门禁拦截）")
    args = ap.parse_args()
    all_hits = []
    for f in args.files:
        hits = scan(f)
        if hits:
            print("D3-WARN %s 命中疑似原文长句/金句 %d 处:" % (f, len(hits)))
            for h in hits[:10]:
                print("   - %s" % h)
            all_hits += hits
        else:
            print("OK %s 无长句/金句" % f)
    if args.strict and all_hits:
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
