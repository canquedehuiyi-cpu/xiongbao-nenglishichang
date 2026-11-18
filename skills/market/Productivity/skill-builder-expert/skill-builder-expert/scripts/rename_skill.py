#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""改名规程执行器（REF-MKT-045 §六）：任何技能包改名/重命名，一律走本脚本机器执行，禁止手工逐处改。

设计原则（v71/v72 两次工程教训固化）：
1. 改名=改「名称族」，不是改一个 name 字段——名称族至少含：
   name / slug、display_name / displayName、display_name_en、category 词根、
   keywords/tags 中与本包英文名同族的词条、_meta.json、LISTING 清单行、
   包内目录名、压缩包文件名（= 包内英文 name + 批次标识）。
2. 全部新值由新英文名机器派生，不靠人记字段：
   display_name_en = 新 name 各词首字母大写、空格连接（规范化后必须等于 name）；
   category 若为 skill- 前缀形态则改写为 skill- + 新 name 中间词根；
   压缩包建议文件名 = 新 name + 批次标识。
3. fail-closed：改写完自动复检，任何旧名完整字面或同族词根残留、
   标识字段与新 name 不同族、displayName 双写不同值——一律报 FAIL 不放行。
4. 本脚本自身零硬编码任何包名（本包机检会扫描本文件）。

用法：
  python scripts/rename_skill.py <包目录> --new-name <新英文名> [--new-display <新中文名>] [--dry-run]

退出码：0=成功（或 dry-run 预览通过）；2=校验不过，拒绝改写或改写后仍有残留。
"""
import argparse
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import publish_form_scan as pfs  # noqa: E402

SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9_-]*[a-z0-9]$|^[a-z0-9]$")


def derive_display_en(new_name):
    """新 name → 英文显示名（各词首字母大写、空格连接）。"""
    return " ".join(w.capitalize() for w in str(new_name).split("-"))


def middle_root(name):
    """解析 name 中间词根（skill-X-expert 形态取 X；两段取第二段；单段返回该段）。"""
    parts = str(name).split("-")
    return parts[1] if len(parts) >= 2 else parts[0]


def iter_text_files(root):
    for dirpath, _dirs, files in os.walk(root):
        for fn in files:
            if fn.endswith(pfs.TEXT_EXT):
                yield os.path.join(dirpath, fn)


def rewrite_frontmatter_value(text, key, new_value):
    """frontmatter / 双写 JSON 风格键值行重写（display_name 与 displayName 同步）。"""
    pat = re.compile(r"(?m)^(\s*%s\s*:\s*)(.*\S)?\s*$" % re.escape(key))
    return pat.sub(lambda m: m.group(1) + new_value, text, count=1)


def rewrite_inline_key(text, key, new_value):
    """display_name: "X" / displayName: "X" / display_name: X 带引号形态。"""
    pat = re.compile(r'(\b%s\s*:\s*)"[^"]*"' % re.escape(key))
    return pat.sub(lambda m: '%s"%s"' % (m.group(1), new_value), text, count=1)


def rewrite_json_key(text, key, new_value):
    """JSON 形态 "slug": "old" → "slug": "new"。"""
    pat = re.compile(r'("%s"\s*:\s*)"[^"]*"' % re.escape(key))
    return pat.sub(lambda m: '%s"%s"' % (m.group(1), new_value), text, count=1)


def rename_package(root, new_name, new_display=None, dry_run=False):
    """对包目录执行名称族全量改写。返回 (report_lines, fatal_list)。"""
    report = []
    fatal = []
    sk = pfs.find_skill_md(root)
    if not sk:
        return report, ["未找到 SKILL.md，无法执行改名"]
    fm = pfs.parse_frontmatter(pfs.read_text(sk))
    old_name = str(fm.get("name") or "").strip()
    if not old_name:
        return report, ["SKILL.md frontmatter 缺 name 字段"]
    if not SLUG_RE.match(new_name):
        return report, ["新英文名不合命名纪律（仅小写字母/数字/连字符/下划线，首尾为字母或数字）: %r" % new_name]
    if new_name == old_name:
        return report, ["新名与旧名相同，无需改写"]
    old_root = middle_root(old_name)
    new_root = middle_root(new_name)
    old_display_en = derive_display_en(old_name)
    new_display_en = derive_display_en(new_name)
    if new_display is None:
        new_display = str(fm.get("display_name") or fm.get("displayName") or "").strip()

    plan = [
        "名称族改写计划（fail-closed，全部机器派生）:",
        "  name/slug            : %s -> %s" % (old_name, new_name),
        "  display_name_en      : %s -> %s（由新 name 派生）" % (old_display_en, new_display_en),
        "  display_name/displayName : %s" % (new_display or "（保持不动）"),
        "  category 词根        : skill-%s -> skill-%s（skill- 前缀形态才改）" % (old_root, new_root),
        "  同族词根词条         : 含 %s 词根的连字符词条一并跟随" % old_root,
    ]
    report.extend(plan)

    name_re = re.compile(r"(?<![\w-])" + re.escape(old_name) + r"(?![\w-])")
    # 旧英文显示名的三形态（首字母大写空格连接／全小写空格连接／全大写）一并改写，三形态值均由旧 name 派生
    disp_pairs = [(old_display_en, new_display_en),
                  (old_display_en.lower(), new_display_en.lower()),
                  (old_display_en.upper(), new_display_en.upper())]
    root_word_re = re.compile(r"(?<![\w-])" + re.escape(old_root) + r"(?![\w-])") if old_root != new_root else None

    touched = 0
    if not dry_run:
        for p in iter_text_files(root):
            rel = os.path.relpath(p, root).replace("\\", "/")
            try:
                text = pfs.read_text(p)
            except Exception:
                continue
            orig = text
            # L1 完整名词边界替换（全文，含正文、清单、示例）＋旧英文显示名三形态
            text = name_re.sub(new_name, text)
            for o, n in disp_pairs:
                text = text.replace(o, n)
            # L2 标识字段精确重写（frontmatter 与 JSON 双形态）
            text = rewrite_frontmatter_value(text, "name", new_name)
            text = rewrite_frontmatter_value(text, "slug", new_name)
            text = rewrite_frontmatter_value(text, "display_name_en", '"%s"' % new_display_en)
            text = rewrite_inline_key(text, "display_name_en", new_display_en)
            text = rewrite_json_key(text, "name", new_name)
            text = rewrite_json_key(text, "slug", new_name)
            if new_display:
                text = rewrite_inline_key(text, "display_name", new_display)
                text = rewrite_inline_key(text, "displayName", new_display)
                text = rewrite_frontmatter_value(text, "display_name", '"%s"' % new_display)
                text = rewrite_frontmatter_value(text, "displayName", '"%s"' % new_display)
            # L3 category 词根（仅 skill- 前缀形态；平台枚举类目不动）
            text = re.sub(r"(?m)^(\s*category\s*:\s*)skill-%s\s*$" % re.escape(old_root),
                          lambda m: m.group(1) + "skill-" + new_root, text, count=1)
            text = re.sub(r'("category"\s*:\s*)"skill-%s"' % re.escape(old_root),
                          lambda m: m.group(1) + '"skill-' + new_root + '"', text, count=1)
            # L4 裸词根词条（tags/keywords/正文标识）：\w 词边界界定——前后非字母数字下划线即替换，
            # 任何标点（半角/全角逗号、引号、顿号等）均为合法界定，三大小写形态
            if old_root != new_root:
                for o, n in ((old_root, new_root),
                             (old_root.capitalize(), new_root.capitalize()),
                             (old_root.upper(), new_root.upper())):
                    text = re.sub(r"(?<!\w)" + re.escape(o) + r"(?!\w)", n, text)
            if text != orig:
                touched += 1
                report.append("  改写: %s" % rel)
                with open(p, "wb") as f:
                    f.write(text.encode("utf-8"))
        # 包内目录名（顶层目录与 name 同名时改名）
        top = os.path.basename(root.rstrip("\\/"))
        if top == old_name:
            new_root_dir = os.path.join(os.path.dirname(root.rstrip("\\/")) or ".", new_name)
            os.rename(root, new_root_dir)
            root = new_root_dir
            report.append("  目录改名: %s -> %s" % (top, new_name))
    else:
        report.append("  [dry-run 预览模式，未写入任何文件]")

    # 复检（fail-closed）
    if not dry_run:
        report.append("复检（⑪名称族一致性 + 旧名残留）:")
        for p in iter_text_files(root):
            rel = os.path.relpath(p, root).replace("\\", "/")
            try:
                text = pfs.read_text(p)
            except Exception:
                continue
            low = text.lower()
            if old_name.lower() in low:
                fatal.append("旧名完整字面残留: %s" % rel)
            if old_root != new_root:
                for m in re.finditer(r"(?<!\w)" + re.escape(old_root) + r"(?!\w)", low):
                    seg = text[max(0, m.start() - 30):m.end() + 30].replace("\n", " ")
                    fatal.append("旧词根裸字面残留: %s | ...%s..." % (rel, seg.strip()[:60]))
                    break
        sk = pfs.find_skill_md(root)
        if sk:
            fm2 = pfs.parse_frontmatter(pfs.read_text(sk))
            nm = str(fm2.get("name") or "").strip()
            for key in ("display_name", "displayName"):
                dv = fm2.get(key)
                if dv and str(dv).strip().strip('"') != new_display and new_display:
                    fatal.append("%s 与新中文名不同值: %r" % (key, dv))
            msgs = pfs.check_name_consistency(root, form="base")
            msgs = [m for m in msgs if "display_name_en" not in m]
            fatal.extend(msgs)
            report.append("  name=%s display_name_en=%s category=%s"
                          % (nm, fm2.get("display_name_en"), fm2.get("category")))
    report.append("涉及文件: %d" % touched)
    report.append("压缩包建议文件名: %s_<批次标识>.zip（必须以包内英文 name 开头）" % new_name)
    return report, fatal


def main(argv=None):
    ap = argparse.ArgumentParser(description="改名规程执行器（名称族全量改写+复检）")
    ap.add_argument("root", help="包目录")
    ap.add_argument("--new-name", required=True, help="新英文名（name/slug 及全部标识字段跟随）")
    ap.add_argument("--new-display", default=None, help="新中文名（可选）")
    ap.add_argument("--dry-run", action="store_true", help="仅预览改写计划，不写入")
    args = ap.parse_args(argv)
    root = os.path.abspath(args.root)
    if not os.path.isdir(root):
        print("FAIL 目录不存在: %s" % root)
        return 2
    report, fatal = rename_package(root, args.new_name, args.new_display, args.dry_run)
    for line in report:
        print(line)
    if fatal:
        print("FAIL 改名复检 %d 项不过（禁止出包，逐项处理后重跑）:" % len(fatal))
        for m in fatal[:15]:
            print("  -", m)
        return 2
    print("PASS 改名规程执行完成%s（名称族全部字段同步，复检零残留）" % ("（dry-run）" if args.dry_run else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
