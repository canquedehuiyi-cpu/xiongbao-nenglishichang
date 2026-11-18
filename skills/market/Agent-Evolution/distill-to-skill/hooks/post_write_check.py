#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""PostToolUse optional check: scan local markdown broken links after a write.

Reads JSON from stdin (tool_name / tool_input); hints only, never blocks (exit 0).
Read-only, no network, stdlib only. Disabled by default; skill works without it.
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
        msg = '[check] %s has %d broken local link(s): %s\n' % (
            os.path.basename(path), len(bad), ' '.join(bad[:5]))
        sys.stderr.write(msg)
    return 0


if __name__ == '__main__':
    sys.exit(main())
