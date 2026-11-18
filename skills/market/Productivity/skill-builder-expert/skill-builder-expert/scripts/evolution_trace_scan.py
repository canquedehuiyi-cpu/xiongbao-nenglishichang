#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""evolution_trace_scan.py —— 演进痕迹零出口扫描（对外交付闸，fail-closed）

定位
----
对外交付的技能包、配套文档、交互文本中，禁止携带内部迭代痕迹与研发思考链路。
文档内的版本沿革标记、迭代记录、研发过程叙述、内部管控称谓，会暴露整套生产思路、
调整过程、方案取舍与迭代轨迹，等同于向外泄露内部生产流水线。本扫描器在打包前对
「入包视图」做最后一道过滤，检出即拦截（退出码 1），清扫完成才允许打包交付。

扫描四类目标特征（词面运行时拼接，本文件不复述完整违例字面，防自咬）：
  T1 版本沿革标记：两位及以上数字的迭代版本号字面（产品语义版本号 x.y.z 不受影响）；
  T2 构建计数痕迹：构建编号字段与构建计数表述；
  T3 迭代句式：版本级新增/修改/沿革/复盘类表述；
  T4 内部管控称谓：仅限内部治理角色字面，对外一律中性化。

判定口径（与用户确认的规范一致）：
  - 内容功能编号（章节序号、条目序号、菜单序号）一律保留——那是 Agent 调用与路由的
    必需结构，本扫描器绝不触碰；
  - 序号 + 迭代历史描述的条目属沿革，须整条清理（清理动作由维护流程执行，本扫描器
    负责检出拦截）；
  - 讲「现在这个功能是什么、怎么用」的成品说明保留；讲「过去是什么样、哪一版改了
    什么、当初怎么调」的迭代沿革检出拦截。

用法
----
    python scripts/evolution_trace_scan.py <目录|文件...>          # 扫描，0=通过 1=检出
    python scripts/evolution_trace_scan.py --self-test             # 阳/阴用例自测

排除规则
----
扫描默认跳过内部私有区（维护看板、生产日志、构建计数器、写防护机件目录）——这些
文件按规范永不入包，属内部私有存储区域，仅限内部母本升级与问题溯源使用。

零外部依赖，纯标准库，不发起任何网络请求。
"""
import json
import os
import re
import sys
from pathlib import Path

TEXT_EXT = {".md", ".txt", ".json", ".yaml", ".yml", ".html", ".csv", ".xml"}
# 内部私有区（永不入包，扫描跳过）：目录与文件名
PRIVATE_DIRS = {"scripts", "hooks", "logs", "__pycache__"}
PRIVATE_FILES = {"MAINTAINER.md", "_build_seq.json"}

# ---- 指向式词表：违例字面运行时拼接，防本文件自咬 ----
# T1：拦截两位以上迭代版本号字面；负向断言豁免带点语义版本号（v13.3.78 类案例产品名）
_T1_HEAD = "[" + "vV" + "]"
_T1_PAT = r"(?<![A-Za-z0-9_.])" + _T1_HEAD + r"\d{2,}\b(?![\d.])"
# T1b：V3.2 形态的沿革版本号（大写 V 前缀 + 点分双段；小写语义版本号与文件名版本段不受影响）
_T1B_PAT = r"(?<![A-Za-z0-9_./`])" + _T1_HEAD + r"\d+\.\d+(?![\d.])"
# T2：拦截「构建编号赋值且带具体数字」形态；裸字段名（机制功能描述）放行
_T2_PATS = [
    r"\b" + "bui" + r"ld[_ ]?no" + r"\s*[\"']?\s*[:=]\s*[\"']?\s*\d+",
    r"\b" + "bui" + r"ld\s+\d+\b",
]
_T3_WORDS = [
    "起" + "生效",
    "变更" + "记录",
    "修订" + "历史",
    "修订" + "】",
    "上一版" + "存在",
    "上一版" + "缺陷",
    "本版" + "新增",
    "版本" + "新增",
    "版本" + "优化",
    "版本" + "变更",
    "沿革",
    "实弹" + "测试",
    "润色" + "稿",
    "主" + "理人",
    "MAI" + "NTAINER",
    "配" + "方",
]
_T4_PAT = None  # 预留扩展位

# 文件名版本标识剥离（产品版本标识：文件名内嵌版本段属标准件命名，不属沿革叙述）
_FILENAME_VER = re.compile(r"[A-Za-z0-9_\-./`]*_[Vv]\d+\.[A-Za-z]+")
# 反引号代码/路径段剥离（代码段与文件路径不扫）
_CODE_SPAN = re.compile(r"`[^`\n]*`")


def _scan_text(text: str):
    """返回 [(类别, 命中字面, 行号), ...]"""
    hits = []
    stripped = _FILENAME_VER.sub(" ", text)
    stripped = _CODE_SPAN.sub(" ", stripped)
    lines = stripped.split("\n")
    for idx, ln in enumerate(lines, 1):
        for m in re.finditer(_T1_PAT, ln):
            hits.append(("T1版本沿革标记", m.group(0), idx))
        for m in re.finditer(_T1B_PAT, ln):
            hits.append(("T1版本沿革标记", m.group(0), idx))
        for pat in _T2_PATS:
            for m in re.finditer(pat, ln, re.I):
                hits.append(("T2构建计数痕迹", m.group(0), idx))
        for w in _T3_WORDS:
            if w in ln:
                hits.append(("T3迭代句式", w, idx))
    return hits


def iter_targets(paths):
    for p in paths:
        p = Path(p)
        if p.is_file():
            if p.name not in PRIVATE_FILES and p.suffix.lower() in TEXT_EXT:
                yield p
        elif p.is_dir():
            for dp, dns, fns in os.walk(p):
                dns[:] = [d for d in dns if d not in PRIVATE_DIRS and not d.startswith(".")]
                for fn in sorted(fns):
                    if fn in PRIVATE_FILES or fn.startswith("."):
                        continue
                    fp = Path(dp) / fn
                    if fp.suffix.lower() in TEXT_EXT:
                        yield fp


# 唯一豁免区：REF-BSE-047 标记区（用户下发定稿逐字有效，fail-closed——双锚点不齐不豁免照扫全文）。
# 定稿原文含 T3 词面（如版本变更类工程规则表述），属用户定稿字面，不属本包演进痕迹；
# 标记区外文本照扫不豁免。run_scan 与 package_zip 入包视图检查共用本函数。
_NOTICE_REF_KEY = "REF-BSE-047"
_NOTICE_BS = "<!-- BASE-BLOCK-START -->"
_NOTICE_BE = "<!-- BASE-BLOCK-END -->"


def strip_notice_region(filename: str, text: str) -> str:
    if _NOTICE_REF_KEY not in filename:
        return text
    if _NOTICE_BS in text and _NOTICE_BE in text:
        return text.split(_NOTICE_BS, 1)[0] + text.split(_NOTICE_BE, 1)[1]
    return text


def run_scan(paths):
    findings = {}
    for fp in iter_targets(paths):
        try:
            text = fp.read_bytes().decode("utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        text = strip_notice_region(fp.name, text)
        hits = _scan_text(text)
        if hits:
            findings[str(fp)] = hits
    return findings


def self_test() -> int:
    pos_cases = [
        ("（" + "v45" + " 铁规）规则正文", "T1版本沿革标记"),
        ("buil" + "d_no: 45", "T2构建计数痕迹"),
        ("\"buil" + "d_no\": 45", "T2构建计数痕迹"),
        ("buil" + "d 27 起效", "T2构建计数痕迹"),
        ("版本说" + "明：V31 在 V30 基础上新增", "T1版本沿革标记"),
        ("变更" + "记录：v28 → v29", "T3迭代句式"),
        ("主理" + "人定稿", "T3迭代句式"),
        ("【V31" + " 修订】条款", "T1版本沿革标记"),
        ("（权属红线 · v4" + "5）宣称", "T1版本沿革标记"),
        ("《标准手册（V" + "3.2）》附录A 同步", "T1版本沿革标记"),
    ]
    neg_cases = [
        "正常功能条款：章节 3.1、3.2、12.8 等内容编号保留，Agent 依序号路由调用。",
        "产品语义版本号 version: \"1.0.0\" 与 2.5.10 不受影响。",
        "标准件文件名字样：`references/REF-SPC-001_AISkillManual_V32.md`。",
        "恢复使用第 5 版属于版本管理功能语境，非迭代替换叙述。",
        "菜单序号定向进入、条目序号 21.4 高危清单，均为内容编号。",
        "案例产品名：商业参谋 v13.3.78 — 免费版本（带点语义版本号，功能语境）。",
        "机制功能描述（裸字段名，不带编号值）：报告落点 logs/QUALITY_<" + "build_no" + "_<时间戳>.json。",
        "小写语义版本字面 3.2 与 frontmatter version \"2.5\" 不拦截（仅大写 V 前缀的迭代版本形态拦截）。",
    ]
    ok = True
    for text, want in pos_cases:
        got = {h[0] for h in _scan_text(text)}
        if want not in got:
            print(json.dumps({"ok": False, "self_test": "阳性未命中", "want": want,
                              "got": sorted(got), "text": text}, ensure_ascii=False))
            ok = False
    for text in neg_cases:
        got = _scan_text(text)
        if got:
            print(json.dumps({"ok": False, "self_test": "阴性误报", "hits": got,
                              "text": text}, ensure_ascii=False))
            ok = False
    if ok:
        print(json.dumps({"ok": True, "self_test": "%d阳%d阴 全部通过（阳性必拦/阴性必放）"
                          % (len(pos_cases), len(neg_cases))}, ensure_ascii=False))
        return 0
    return 4


def main() -> int:
    args = [a for a in sys.argv[1:]]
    if "--self-test" in args:
        args.remove("--self-test")
        return self_test()
    if not args:
        print(json.dumps({"ok": False, "error": "用法: evolution_trace_scan.py <目录|文件...> 或 --self-test"},
                         ensure_ascii=False))
        return 2
    findings = run_scan(args)
    total = sum(len(v) for v in findings.values())
    if findings:
        print(json.dumps({"ok": False, "gate": "blocked", "total": total,
                          "detail": {k: v[:20] for k, v in findings.items()},
                          "reason": "检出演进痕迹（版本沿革标记/构建计数/迭代句式/内部称谓），"
                                    "清扫完成前禁止打包交付（fail-closed）"}, ensure_ascii=False))
        return 1
    print(json.dumps({"ok": True, "gate": "pass", "total": 0,
                      "reason": "演进痕迹零出口检查通过"}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
