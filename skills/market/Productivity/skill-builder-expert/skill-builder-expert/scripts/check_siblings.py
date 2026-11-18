#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
check_siblings.py —— 姊妹包保真对账（同一技能的多平台变体）

为什么需要它
------------
单包体检，天生看不见"**两个包之间**"的问题。
真实的失效形态不是"一个包不合格"，而是：

    一个变体被"合规清洗"了、另一个没动 → 两个包各自 pass，合起来是坏的。

已知失效案例：某技能的"平台适配版"把业务词洗了一遍——
`元` 4→0、`价格` 27→0、`分析` 7→0（"分析"被替换成"研判"）、
`50 元/件` 变成 `50 /件`（单位被抹掉）。两个包单独跑质检**全是 pass**。

它查三件事
----------
① **业务正文逐字一致**：同名文件逐行 diff，只放行白名单（平台元数据行）与
   "平台专属段"（章节标题含平台标识、或含通用平台标记词的段落）。
② **业务词保真**：数字+单位组合（"50 元/件"）不得被抹；业务实词不得归零。
③ **修复批次一致**：打印每个文件的 mtime，暴露"只改了一半"。

平台标识怎么来（重要 · 本脚本不出现任何具体平台名）
--------------------------------------------------
**硬编码平台名 = 把不属于本包的平台引进包内**，这是本包明令禁止的
（已知失效：一张硬编码的平台名单被忠实执行，连带把用户业务词一起洗掉）。
所以平台标识只从下面两处动态获得：

  ① **从目录名推断**：变体目录名相对主包目录名的"差异片段"。
     例：主包 `my-skill`、变体 `my-skill-vendor-b` → 平台标识 = `vendor-b`。
  ② **显式指定**：`--tag=<标识>` 覆盖推断结果（目录名看不出差异时用）。

"平台专属段" = 标题里含该标识、或含 `PLATFORM_SECTION_MARKERS` 里通用标记词的整段。
那些段落本就该随平台不同，不算失真。

用法
----
    python scripts/check_siblings.py <主包目录> <变体包目录> [更多变体...] [--tag=<平台标识>]
    python scripts/check_siblings.py --self-test      # 内置样本自测，不碰任何真实包

退出码：0=一致，1=发现失真。

零外部依赖，纯标准库，不发起任何网络请求。
"""

import json
import re
import sys
from collections import Counter
from pathlib import Path

# ---- 白名单：平台元数据行本就该不同，不算失真 ----
WHITELIST_LINE = re.compile(
    r"^\s*-?\s*(name|slug|displayName|version|ownerId|publishedAt)\s*:"
)

# ---- 数字 + 单位：抓"50 元/件"里的单位被抹掉那种伤 ----
NUM_UNIT = re.compile(
    r"\d+(?:\.\d+)?\s*(?:元|万元|千元|万|千|百|件|箱|瓶|包|个|台|套|天|周|月|年|次|人|单|条|页|分|角|%|％)"
)

# ---- 默认业务实词表（可用 --terms 覆盖）----
# 判据：主包里出现过的业务词，变体里**不得归零**。
DEFAULT_BUSINESS_TERMS = (
    "价格", "报价", "元", "金额", "成本", "利润", "折扣", "付款", "账期",
    "分析", "研判", "客户", "服务", "质量", "库存", "发货", "售后",
)

# ---- "平台专属段"的**通用**标记词（不硬编码任何平台名）----
# 章节标题里出现这些词，即认定该段随平台不同、放行其差异。
PLATFORM_SECTION_MARKERS = (
    "平台专属", "平台差异", "平台说明", "platform:",
)


def load(p: Path) -> str:
    return p.read_text(encoding="utf-8")


def platform_tag(main_dir: Path, variant_dir: Path) -> str:
    """从"变体目录名 vs 主包目录名"的差异片段推断平台标识。

    不硬编码任何平台名——名字从现场拿来，包内因此不出现任何具体平台。
    （主包 `my-skill` / 变体 `my-skill-vendor-b` → `vendor-b`）
    """
    m = [s for s in re.split(r"[-_]", main_dir.name.lower()) if s]
    v = [s for s in re.split(r"[-_]", variant_dir.name.lower()) if s]
    i = 0
    while i < len(m) and i < len(v) and m[i] == v[i]:
        i += 1
    return "-".join(v[i:]) if i < len(v) else ""


def strip_platform_sections(text: str, tag: str) -> str:
    """去掉"平台专属段"——标题含平台标识、或含通用平台标记词的整段。"""
    keep, drop = [], False
    for ln in text.splitlines(keepends=True):
        if ln.startswith("## "):
            low = ln.lower()
            drop = bool(tag) and tag in low
            if not drop:
                drop = any(mk in low for mk in PLATFORM_SECTION_MARKERS)
        if not drop:
            keep.append(ln)
    return "".join(keep)


def diff_lines(a: str, b: str):
    """返回 (仅主包有, 仅变体有) 的非白名单差异行（去重计数）。"""
    ca = Counter(l.strip() for l in a.splitlines() if l.strip())
    cb = Counter(l.strip() for l in b.splitlines() if l.strip())
    only_a = [l for l in (ca - cb).elements() if not WHITELIST_LINE.match(l)]
    only_b = [l for l in (cb - ca).elements() if not WHITELIST_LINE.match(l)]
    return only_a, only_b


def business_term_issues(main_text: str, var_text: str, terms) -> list:
    """业务词归零 / 腰斩检测。"""
    issues = []
    for t in terms:
        a = main_text.count(t)
        b = var_text.count(t)
        if a >= 3 and b == 0:
            issues.append(f"业务词「{t}」在主包出现 {a} 次、在变体里 **归零** → 疑被替换或删除")
        elif a >= 6 and b * 2 < a:
            issues.append(f"业务词「{t}」主包 {a} 次 → 变体只剩 {b} 次（腰斩）→ 疑被批量替换")
    return issues


def num_unit_issues(main_text: str, var_text: str) -> list:
    """数字+单位组合丢失检测：'50 元/件' → '50 /件' 这类。"""
    a = Counter(NUM_UNIT.findall(main_text))
    b = Counter(NUM_UNIT.findall(var_text))
    missing = [k for k in a if k not in b]
    if missing:
        show = "、".join(sorted(missing)[:8])
        more = f"（共 {len(missing)} 处）" if len(missing) > 8 else ""
        return [f"数字+单位组合在主包有、变体里消失：{show}{more} → 数字成了'裸数字'（单位被抹）"]
    return []


def mtime_table(main: Path, variant: Path) -> list:
    """修复批次一致性：同一文件两包 mtime 差得很远 = 只改了一个。"""
    rows = []
    for p in sorted(main.rglob("*")):
        if not p.is_file():
            continue
        rel = p.relative_to(main)
        q = variant / rel
        if not q.exists():
            rows.append(f"  ⚠️ 变体缺文件: {rel.as_posix()}")
            continue
        ta, tb = p.stat().st_mtime, q.stat().st_mtime
        flag = "✏️ 批次不一致" if abs(ta - tb) > 300 else "  "
        rows.append(f"  {flag} {rel.as_posix()}")
    return rows


def compare(main: Path, variant: Path, terms, tag_override: str = "") -> dict:
    tag = tag_override or platform_tag(main, variant)
    md_main = {p.relative_to(main): p for p in sorted(main.rglob("*.md"))}

    diffs, only_a_cnt, only_b_cnt = [], 0, 0
    for rel, p in md_main.items():
        q = variant / rel
        if not q.exists():
            diffs.append({"file": rel.as_posix(), "note": "变体缺此文件"})
            continue
        a = strip_platform_sections(load(p), tag)
        b = strip_platform_sections(load(q), tag)
        oa, ob = diff_lines(a, b)
        if oa or ob:
            only_a_cnt += len(oa)
            only_b_cnt += len(ob)
            diffs.append({
                "file": rel.as_posix(),
                "only_main": oa[:12],
                "only_variant": ob[:12],
                "n_only_main": len(oa),
                "n_only_variant": len(ob),
            })

    main_all = "\n".join(load(p) for p in md_main.values())
    var_all = "\n".join(load(variant / r) for r in md_main if (variant / r).exists())

    term_issues = business_term_issues(main_all, var_all, terms)
    nu_issues = num_unit_issues(main_all, var_all)

    ok = not (diffs or term_issues or nu_issues)
    return {
        "main": str(main),
        "variant": str(variant),
        "platform_tag": tag or "(未识别)",
        "diff_files": diffs,
        "diff_line_count": {"only_main": only_a_cnt, "only_variant": only_b_cnt},
        "business_term_issues": term_issues,
        "num_unit_issues": nu_issues,
        "mtime_table": mtime_table(main, variant),
        "pass": ok,
    }


def render(report: dict) -> str:
    L = []
    L.append("=" * 78)
    L.append("姊妹包保真对账 · check_siblings.py")
    L.append("=" * 78)
    L.append(f"主包  : {report['main']}")
    L.append(f"变体  : {report['variant']}   (平台标识: {report['platform_tag']})")
    L.append("")
    L.append(f"[A] 业务正文逐字一致：非白名单差异行 "
             f"仅主包 {report['diff_line_count']['only_main']} / "
             f"仅变体 {report['diff_line_count']['only_variant']}")
    for d in report["diff_files"]:
        L.append(f"  ▼ {d['file']}  "
                 f"(仅主包 {d.get('n_only_main', 0)} / 仅变体 {d.get('n_only_variant', 0)})")
        for x in d.get("only_main", []):
            L.append(f"      - 主包: {x[:96]}")
        for x in d.get("only_variant", []):
            L.append(f"      + 变体: {x[:96]}")
    if not report["diff_files"]:
        L.append("  ✅ 无实质差异（除平台元数据与平台专属段）")
    L.append("")
    L.append("[B] 业务词保真")
    if report["business_term_issues"]:
        for x in report["business_term_issues"]:
            L.append(f"  ❌ {x}")
    else:
        L.append("  ✅ 无业务词归零 / 腰斩")
    L.append("")
    L.append("[C] 数字+单位保真")
    if report["num_unit_issues"]:
        for x in report["num_unit_issues"]:
            L.append(f"  ❌ {x}")
    else:
        L.append("  ✅ 无数字单位丢失")
    L.append("")
    L.append("[D] 修复批次一致性（mtime）")
    L.extend(report["mtime_table"])
    L.append("")
    L.append("=" * 78)
    L.append(f"结论：{'✅ 姊妹包一致' if report['pass'] else '❌ 发现失真（同一技能的多变体内容对不上）'}")
    L.append("=" * 78)
    return "\n".join(L)


# ---------------------------------------------------------------- self-test
SELF_MAIN = (
    "纯牛奶他平时 50 元/件、卖 55-58 元。\n"
    "一箱 24 瓶，单价 2 元 出头。\n"
    "价格优势 = 比他现有渠道便宜。价格体系 + 议价能力 + 谈判空间。\n"
    "门店的采购价格是核心。你要知道到什么价格可以找谁申请。\n"
    "我先帮你分析这个客户。分析显性需求与隐性需求。分析完再报价。\n"
)
SELF_BAD = (
    "纯牛奶他平时 50 /件、卖 55-58 。\n"
    "一箱 24 瓶，单价 2 出头。\n"
    "报价优势 = 比他现有渠道便宜。报价体系 + 议价能力 + 谈判空间。\n"
    "门店的采购报价是核心。你要知道到什么报价可以找谁申请。\n"
    "我先帮你研判这个客户。研判显性需求与隐性需求。研判完再报价。\n"
)


def self_test() -> int:
    print("— self-test：用一对内置样本证明本脚本抓得住「合规清洗」式失真 —")
    a = NUM_UNIT.findall(SELF_MAIN)
    b = NUM_UNIT.findall(SELF_BAD)
    print(f"  样本主包数字+单位: {a}")
    print(f"  样本变体数字+单位: {b}")
    lost = [k for k in Counter(a) if k not in Counter(b)]
    print(f"  应检出丢失: {lost}")
    terms = business_term_issues(SELF_MAIN, SELF_BAD, ("价格", "报价", "分析", "研判", "元"))
    nu = num_unit_issues(SELF_MAIN, SELF_BAD)
    tag = platform_tag(Path("my-skill"), Path("my-skill-vendor-b"))
    print(f"  平台标识推断（my-skill / my-skill-vendor-b）: {tag!r}")
    caught = bool(lost) and bool(terms) and bool(nu) and tag == "vendor-b"
    for x in terms:
        print(f"  ❌ {x}")
    for x in nu:
        print(f"  ❌ {x}")
    print(f"  self-test: {'✅ 通过（能抓到）' if caught else '❌ 失败（漏报）'}")
    return 0 if caught else 1


def main() -> int:
    args = sys.argv[1:]
    if args and args[0] == "--self-test":
        return self_test()

    tag_override, rest = "", []
    for a in args:
        if a.startswith("--tag="):
            tag_override = a.split("=", 1)[1].strip()
        else:
            rest.append(a)
    args = rest

    if len(args) < 2:
        print(json.dumps(
            {"error": "用法: python scripts/check_siblings.py <主包目录> <变体包目录> [更多变体...] "
                      "[--tag=<平台标识>]；或 --self-test"},
            ensure_ascii=False))
        return 1

    main_dir = Path(args[0]).resolve()
    if not main_dir.is_dir():
        print(json.dumps({"error": f"主包目录不存在: {main_dir}"}, ensure_ascii=False))
        return 1

    terms = DEFAULT_BUSINESS_TERMS
    reports, ok = [], True
    for raw in args[1:]:
        v = Path(raw).resolve()
        if not v.is_dir():
            reports.append({"variant": str(v), "pass": False,
                            "business_term_issues": [f"变体目录不存在: {v}"],
                            "diff_files": [], "num_unit_issues": [],
                            "diff_line_count": {"only_main": 0, "only_variant": 0},
                            "mtime_table": [], "main": str(main_dir), "platform_tag": "-"})
            ok = False
            continue
        r = compare(main_dir, v, terms, tag_override)
        reports.append(r)
        ok = ok and r["pass"]

    for r in reports:
        print(render(r))
        print()

    print(json.dumps(
        {"main": str(main_dir), "variants": len(reports),
         "pass": ok,
         "note": "pass=true = 各变体的业务正文与业务词均与主包一致；"
                 "平台元数据行与平台专属段差异已放行。"
                 "平台标识由目录名差异片段动态推断，或由 --tag 指定——本脚本不硬编码任何平台名。"},
        ensure_ascii=False, indent=2))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
