#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""可选安装器：把 hooks.json 模板里的占位符替换成本机真实路径，产出 hooks.installed.json。

用法（方式 B）：
    python install_hooks.py                  # 用当前 Python 解释器与脚本所在目录
    python install_hooks.py --python /path/to/python --out my.json
默认 dry-run（只打印结果，不写文件）；加 --write 才真正落盘。
本脚本只读模板、只写一个新文件；不改动任何既有配置，不做自动部署。
"""
import argparse, json, os, sys


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--python', default=sys.executable, help='要写入配置的 Python 解释器路径')
    ap.add_argument('--out', default='hooks.installed.json', help='输出文件名')
    ap.add_argument('--write', action='store_true', help='真正写盘（默认只预览）')
    a = ap.parse_args()

    here = os.path.dirname(os.path.abspath(__file__))
    tpl = os.path.join(here, 'hooks.json')
    raw = open(tpl, encoding='utf-8').read()

    repl = {'{{PYTHON_BIN}}': a.python, '{{HOOKS_DIR}}': here}
    out = raw
    for k, v in repl.items():
        out = out.replace(k, v)

    data = json.loads(out)          # 校验 JSON 合法
    txt = json.dumps(data, ensure_ascii=False, indent=2)

    if not a.write:
        print('[预览] 以下是将要写入的内容（未落盘）：')
        print(txt)
        print('\n确认无误后，加 --write 重新执行即可落盘。')
        return 0

    dst = os.path.join(here, a.out)
    with open(dst, 'w', encoding='utf-8', newline='') as f:
        f.write(txt)
    print('[完成] 已写出：%s' % dst)
    print('下一步：把该文件的内容接入你所使用运行时的 hooks 配置入口（各运行时入口不同）。')
    return 0


if __name__ == '__main__':
    sys.exit(main())
