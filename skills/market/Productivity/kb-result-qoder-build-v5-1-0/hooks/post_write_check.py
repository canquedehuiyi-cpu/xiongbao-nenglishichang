#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""PostToolUse 可选检查：写文件后，扫本地 markdown 断链。

约定：stdin 收 JSON（含 tool_name / tool_input）；只提示、不阻断（恒 exit 0）。
本脚本只读、零网络、仅用标准库。不启用本脚本，技能一切功能照常。
"""
import sys, json, os, re, io

LINK = re.compile(r'\]\((\./[^)\#\s]+)')


def main():
    try:
        ev = json.loads(sys.stdin.read() or '{}')
    except Exception:
        return 0
    ti = ev.get('tool_input') or {}
    path = ti.get('path') or ti.get('file_path') or ''
    if not path or not path.lower().endswith('.md') or not os.path.isfile(path):
        return 0
    try:
        txt = io.open(path, encoding='utf-8').read()
    except Exception:
        return 0
    base = os.path.dirname(os.path.abspath(path))
    bad = []
    for m in LINK.finditer(txt):
        rel = m.group(1)[2:]
        if not os.path.exists(os.path.join(base, rel)):
            bad.append(rel)
    if bad:
        sys.stderr.write('[可选检查] %s 有 %d 处本地链接指向不存在的文件：%s\n'
                         % (os.path.basename(path), len(bad), '、'.join(bad[:5])))
    return 0


if __name__ == '__main__':
    sys.exit(main())
