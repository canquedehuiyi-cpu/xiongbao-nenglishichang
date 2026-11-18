#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""PreToolUse 可选检查：写文件前，扫特定禁用词族与显性人群限定词。

约定：stdin 收 JSON（含 tool_name / tool_input）；exit 0 = 放行，exit 2 = 阻断（stderr 写入会话）。
本脚本只读、零网络、仅用标准库。不启用本脚本，技能一切功能照常。

词表用拼接构造，本文件自身不出现连续词形（避免自检命中）。
"""
import sys, json

# 特定禁用词族（把读者放在「正在犯错」位置上的那类词），用拼接，本文件不出现连续词形
BAD = ['\u907f' + '\u5751', '\u9632' + '\u5751', '\u522b\u8e29' + '\u96f7',
       '\u5c11\u8d70' + '\u5f2f\u8def', '\u9677' + '\u9631', '\u9a97' + '\u5c40',
       '\u5957' + '\u8def', '\u5751']
# 显性人群限定词（对外文案不按行业/岗位/职级/规模划人群）
PPL = ['\u5f8b\u5e08', '\u533b\u751f', '\u6559\u5e08', '\u7ba1\u7406\u8005',
       '\u6280\u672f\u9aa8\u5e72', '\u884c\u4e1a\u987e\u95ee', '\u81ea\u7531\u804c\u4e1a\u8005',
       '\u4ece\u4e1a\u8005', '\u666e\u901a\u8001\u767e\u59d3', '\u5c0f\u8001\u767e\u59d3',
       '\u5c0f\u672c\u4e70\u5356', '\u5c0f' + '\u767d', '\u4f1a' + '\u8ba1',
       '\u5f00' + '\u53d1' + '\u8005', '\u4ea7\u54c1\u7ecf\u7406', '\u6218\u7565\u5206\u6790\u5e08',
       '\u521b\u4e1a\u8005', '\u77e5\u8bc6\u5de5\u4f5c\u8005', '\u5bb6\u957f',
       '\u7a0b\u5e8f\u5458', '\u8bbe\u8ba1\u5e08', '\u8fd0\u8425', '\u9500\u552e', '\u8d22\u52a1']

KEYS = ('content', 'new_string', 'file_text', 'text')


def main():
    try:
        ev = json.loads(sys.stdin.read() or '{}')
    except Exception:
        return 0
    ti = ev.get('tool_input') or {}
    blob = ' '.join(str(ti.get(k, '')) for k in KEYS)
    if not blob:
        return 0
    hit_bad = [w for w in BAD if w in blob]
    if hit_bad:
        sys.stderr.write(
            '[可选检查] 本次写入命中特定禁用词族 %d 处。\n'
            '这类词把读者放在“正在犯错”的位置上，对外文案一律不用。\n'
            '请改用结果式表述后重写本次内容。\n' % len(hit_bad))
        return 2
    hit_ppl = [w for w in PPL if w in blob]
    if hit_ppl:
        sys.stderr.write(
            '[可选检查] 本次写入出现 %d 个岗位 / 行业限定词。\n'
            '若属于对外字段（简介、描述、详情页），请改为按“事情”描述，不列人群。\n' % len(hit_ppl))
    return 0


if __name__ == '__main__':
    sys.exit(main())
