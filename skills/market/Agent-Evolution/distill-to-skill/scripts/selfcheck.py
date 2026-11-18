#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
selfcheck.py - Package self-check (nine scans + matrix declarations + wiring audit + optional gates)

Usage:
  python selfcheck.py [package_root]                 # nine scans + matrix + filename gate + wiring audit
  python selfcheck.py [package_root] --run-selftests  # + run every --self-test script
  python selfcheck.py [package_root] --full [--outline OUTLINE.json --artifacts A B ...]
  python selfcheck.py [package_root] --prove-gates    # negative controls for the gates

Checks (any FAIL -> exit 1; all PASS -> exit 0):
  1) Red-line word list: 8 banned groups (stored as code points, no literal form) 0 hits
  2) Single-char red line: 0 occurrences
  3) Design-layer residue: meta-narrative / design-side content markers 0 occurrences
  4) Terminology consistency: banned terms that must be 0 (see TERM_MUST_ZERO) 0 occurrences
  5) Newline discipline: every text file must be LF. CRLF -> FAIL.
  5b) Invisible-character discipline: no invisible code point (zero-width / Bidi controls /
     invisible letters / variation selectors / tag block) may appear anywhere in package text.
     Same predicate as the intake sanitizer (sanitize.is_invisible_codepoint) -- clear others'
     material, never inject into our own; the two must not drift.
  6) Version-number residue: this package's own version family may appear ONLY on a
     version-declaration line (SKILL.md frontmatter / _meta.json). Anywhere else -> FAIL.
     The gate also asserts its own family prefix still matches the _meta.json version, so a
     version bump can never silently turn this gate into a dead one.
  7) Audience-narrowing words: this package's own "no audience restriction" rule may not be
     narrowed by naming specific audience/identity groups or specific exams. Only
     exam/identity groups are scanned (not industry/job titles -- those collide with demo
     data). The line that states the rule itself is the whitelist. A word list shorter than
     AUDIENCE_FLOOR counts as a degraded (dead) gate and FAILs.
  8) Prohibited sales pitch: imperative-buy / guaranteed-return phrasings (PROSELL_MARKERS)
     must be 0 -- the machine judge for "do not sell / do not decide the spend for the user".
     A word list shorter than PROSELL_FLOOR counts as a degraded (dead) gate and FAILs.
  8b) Format x dimension matrix & decision<=3 declarations: the applicability matrix in
     references/mode-bc-guide.md must list all 7 formats and mark Excel-table / Excel-chart
     as "not applicable" for depth/style rows; the decision<=3 rule must be declared
     consistently in SKILL.md / popup-spec.md / mode-bc-guide.md.
  8c) Output-filename gate (癸-12): the naming formula anchor, the suffix enum
     (>= NAMING_SUFFIX_FLOOR) and the banned-name declaration must all be present in
     the spec; with --artifacts, every real artifact name is checked against the formula
     (suffix in enum / non-empty stem / half-width underscore). Judge only from the
     inspected objects, never from this checker.
  9) Script wiring audit: every scripts/*.py must either carry --self-test or have an
     entry in tests/exempt.json (each entry needs since/reason/revisit). Both missing -> FAIL.
     Exemptions are reported as WARN so they stay visible, never silent.
  10) Self-test residue review: snapshot the package tree before and after the
     self-test run; any net add/change/remove inside the package -> FAIL. Files landing in
     the caller CWD (outside the package) are reported as WARN.

--full : one command, one exit code. Chains the gates in ascending cost order
         (nine scans -> matrix declarations -> output-filename gate -> wiring -> compile
         -> --run-selftests -> self-test residue review -> render combos -> product contract
         -> ppt smoke -> golden baseline -> real-artifact verify) and prints a three-state
         table.
         SKIP means environment/inputs unavailable -- NOT a failure, but always
         counted and listed with a reason. PASS == no FAIL.
--prove-gates : negative controls (29 checks; the package-shipment gate contributes a
         red/green pair). In a throwaway copy, break one thing per
         gate and assert the gate fires. Proves the gates are able to fail.
         Then a meta-audit guards the control list itself: a count floor + a
         required-gate-name list + a drill (dropping one / clearing all must be
         caught) -- so a shrunken control set cannot keep printing GATES PROVEN.

Hits report only "file:line + masked fragment", never the literal banned word.
"""
import os
import sys
import re
import json
import shutil
import tempfile
import argparse
import subprocess as _sp

# ---------------------------------------------------------------
# 禁用词表一律从单一事实源 lexicon 取（本包所有词族只在那里定义一次）。
# 本包自身也在扫描范围内，故此处只 import 名字，不复述任何表内容。
# ---------------------------------------------------------------
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lexicon import (  # noqa: E402
    REDWORDS, PIT, DESIGN_MARKERS, TERM_MUST_ZERO,
    AUDIENCE_MARKERS, AUDIENCE_FLOOR, AUDIENCE_ANCHOR,
    PROSELL_MARKERS, PROSELL_FLOOR,
    INTERNAL_MARKERS, INTERNAL_BEGIN_MARK, PLACEHOLDER_MARK, INTERNAL_FLOOR,
)
from constants import WORK_DIR, DELIVERY_EXTS, PUBLISH_EXCLUDE  # noqa: E402

# 5) 版本号残留：本包版号族前缀（major.minor.）。
#    一致性断言：若 _meta.json 的版号不再以本前缀开头，整道门 FAIL。
VERSION_FAMILY_PREFIX = "1.2."

# 白名单：版本声明字段行（平台识别必需）—— 形如 `version: "…"` / `"version": "…"`
VERSION_FIELD_RE = re.compile(r'^\s*["\']?version["\']?\s*[:=]')

SKIP_EXT = {".pyc", ".zip", ".png", ".jpg", ".jpeg", ".gif", ".ico",
            ".woff", ".woff2", ".exe", ".dll", ".pdf", ".mp4"}

# 不参与包内自检的目录（元数据目录，与 assemble 的 SKIP_DIRS 口径一致）：
# release/ 是元数据目录（不进安装包），不参与包内自检。
EXCLUDE_DIRS = {"__pycache__", "release", "node_modules", ".git", ".svn", ".idea"}

EXEMPT_FIELDS = ("since", "reason")


def _ver_tuple(v):
    """把版本串解析成可比较的整数三元组（形如 a.b.c，取前 3 段）。"""
    out = []
    for part in str(v or "").strip().split("."):
        m = re.match(r"(\d+)", part)
        out.append(int(m.group(1)) if m else 0)
    while len(out) < 3:
        out.append(0)
    return tuple(out[:3])


def _cur_version(root):
    """读取包根 _meta.json 的 version（失败返回空串，此时不做到期判定）。"""
    try:
        d = json.load(open(os.path.join(root, "_meta.json"), encoding="utf-8"))
        return str(d.get("version", ""))
    except Exception:
        return ""


def has_selftest_support(src):
    """脚本是否真的声明了 --self-test 开关。

    仅看字面会把「注释/文档里提到 --self-test」误判为已接线（例如一个不需自测的
    联测脚本，说明文字里带了该字样，就被算作已接线，而它实际不接受该参数）。
    故要求同时具备参数解析痕迹（sys.argv / argparse）。
    """
    if "--self-test" not in src:
        return False
    return ("sys.argv" in src) or ("argparse" in src) or ("add_argument" in src)


def walk(root):
    if os.path.isfile(root):
        yield root
        return
    for dp, dns, fns in os.walk(root):
        dns[:] = [d for d in dns if d not in EXCLUDE_DIRS and not d.startswith(".")]
        for fn in fns:
            if os.path.splitext(fn)[1].lower() not in SKIP_EXT:
                yield os.path.join(dp, fn)


def mask(s, hit):
    return s.replace(hit, "\u3007" * len(hit))


def scan_roots(roots):
    files = []
    for r in roots:
        files.extend(walk(r))
    return files


def check_redwords(files):
    hits = []
    for p in files:
        try:
            t = open(p, "r", encoding="utf-8").read()
        except Exception:
            continue
        for ln, line in enumerate(t.splitlines(), 1):
            for cid, w in REDWORDS.items():
                if w in line:
                    hits.append((p, ln, cid, mask(line.strip()[:60], w)))
    return hits


def check_substr(files, needle, tag):
    hits = []
    for p in files:
        try:
            t = open(p, "r", encoding="utf-8").read()
        except Exception:
            continue
        for ln, line in enumerate(t.splitlines(), 1):
            if needle in line:
                hits.append((p, ln, tag, mask(line.strip()[:60], needle)))
    return hits


def check_design(files):
    hits = []
    for p in files:
        try:
            t = open(p, "r", encoding="utf-8").read()
        except Exception:
            continue
        for ln, line in enumerate(t.splitlines(), 1):
            for m in DESIGN_MARKERS:
                if m in line:
                    hits.append((p, ln, "design", mask(line.strip()[:60], m)))
    return hits


def check_newlines(files):
    """换行符纪律：包内文本文件一律 LF。

    含 CRLF 的文本文件即不合规，判 FAIL。
    返回 [(path, crlf_count, bare_cr_count)]。
    """
    bad = []
    for p in files:
        try:
            b = open(p, "rb").read()
        except Exception:
            continue
        crlf = b.count(b"\r\n")
        bare = b.count(b"\r") - crlf
        if crlf or bare:
            bad.append((p, crlf, bare))
    return bad


def check_invisible(files):
    """不可见字符纪律：包内文本文件一处不可见字符都不许有。

    与接料清洗层 sanitize.is_invisible_codepoint() 共用同一份判据（单一事实源）：
    那边清别人的材料、这边不许自己往自己的件里注 —— 两边一旦漂移，就是两层都没覆盖。
    返回 [(path, line_no, "U+XXXX", ctx)]。
    """
    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from sanitize import is_invisible_codepoint
    except Exception:
        return []
    hits = []
    for p in files:
        try:
            t = open(p, "r", encoding="utf-8").read()
        except Exception:
            continue
        for ln, line in enumerate(t.splitlines(), 1):
            for ch in line:
                if is_invisible_codepoint(ord(ch)):
                    hits.append((p, ln, "U+%04X" % ord(ch), line.strip()[:60]))
    return hits


def check_version_residue(root, files):
    """版本号残留：本包版号族只准出现在「版本声明字段」行，别处一处都不许有。

    - 命中口径 = 本包版号族（VERSION_FAMILY_PREFIX + 数字）的任意出现；
    - 白名单 = 该行是版本声明字段（`version:` / `"version":`），平台识别必需；
    - 一致性断言 = 若 _meta.json 的版号不再以本前缀开头，判 stale（调用方按 FAIL 处理）。
    返回 (hits, stale)，hits 为 (path, line, tag, ctx)。
    """
    rx = re.compile(re.escape(VERSION_FAMILY_PREFIX) + r"\d+")
    hits = []
    for p in files:
        try:
            t = open(p, "r", encoding="utf-8").read()
        except Exception:
            continue
        for ln, line in enumerate(t.splitlines(), 1):
            if not rx.search(line):
                continue
            if VERSION_FIELD_RE.match(line):
                continue
            hits.append((p, ln, "version", line.strip()[:70]))
    cur = _cur_version(root)
    stale = bool(cur) and not cur.startswith(VERSION_FAMILY_PREFIX)
    return hits, stale


def check_audience_words(files):
    """人群限定词残留：本包「不设人群限定」铁律的机器判据（第八道扫描）。

    - 口径与规则同源 = 只收「具体考试/备考词」与「具体人群身份词」两类；行业名 /
      职能名 / 职级名刻意不收（包内 demo 数据与职能词重名，收了会误伤）。
    - 白名单 = 写明「不设人群限定」的声明行（规则条文本身），且**只在声明层文件里认**
      （非 scripts/ 目录）—— 否则门禁脚本自身的说明文字会充当锚点，使「声明行是否还在」
      这道判据恒为真（门开了却没人知道它失效）。
    - 词表条数低于 AUDIENCE_FLOOR 时判 FAIL。
    返回 (hits, anchor_present)；hits 为 (path, line, tag, ctx)。
    """
    hits = []
    anchor_present = False
    for p in files:
        try:
            t = open(p, "r", encoding="utf-8").read()
        except Exception:
            continue
        _norm = p.replace("/", os.sep)
        in_scripts = (os.sep + "scripts" + os.sep) in _norm
        for ln, line in enumerate(t.splitlines(), 1):
            if AUDIENCE_ANCHOR in line:
                if not in_scripts:
                    anchor_present = True
                continue
            for m in AUDIENCE_MARKERS:
                if m in line:
                    hits.append((p, ln, "audience", mask(line.strip()[:60], m)))
    return hits, anchor_present


def check_prosell(files):
    """禁推销措辞残留：本包「不推销 / 不替用户决定掏钱」铁律的机器判据（第九道扫描）。

    口径 = 命令式购买话术 + 承诺收益话术（见 PROSELL_MARKERS）；词表条数低于
    PROSELL_FLOOR 时由调用方判 FAIL。返回 (path, line, tag, ctx)。
    """
    hits = []
    for p in files:
        try:
            t = open(p, "r", encoding="utf-8").read()
        except Exception:
            continue
        for ln, line in enumerate(t.splitlines(), 1):
            for m in PROSELL_MARKERS:
                if m in line:
                    hits.append((p, ln, "prosell", mask(line.strip()[:60], m)))
    return hits


# 「不适用」标记的等价写法（矩阵里用「–」表示该维度对该格式不适用）
_NOT_APPLICABLE = ("\u2013", "-", "\u2716", "\u2717", "\u00d7")


# ============================================================
# 产物出厂门禁专用检查（--product）
# 判的是「用户最终拿走的那件东西」—— 不含包结构类检查。
# ============================================================
def check_internal(files):
    """内部标记残留：模板层的改编说明与自检清单，不得跟着成品交付。

    只在产物门禁里跑 —— 模板自身含这些字样属正常，包内扫描不查这一项。
    返回 [(路径, 行号, 标签, 掩码片段)]。
    """
    hits = []
    for p in files:
        try:
            t = open(p, "r", encoding="utf-8").read()
        except Exception:
            continue
        for ln, line in enumerate(t.splitlines(), 1):
            if INTERNAL_BEGIN_MARK in line:
                hits.append((p, ln, "internal-block",
                             mask(line.strip()[:60], INTERNAL_BEGIN_MARK)))
                continue
            for m in INTERNAL_MARKERS:
                if m in line:
                    hits.append((p, ln, "internal", mask(line.strip()[:60], m)))
    return hits


# 出包排除件核对：包内「自我声明不参与 Agent 执行」的件，必须登记进 constants.PUBLISH_EXCLUDE。
# 标记串由码点拼出 —— 判据句里不出现被检字符串（免「判据自己满足自己」）。
_SELF_DECL = "".join(chr(c) for c in (
    0x4E0D, 0x53C2, 0x4E0E, 0x20, 0x41, 0x67, 0x65, 0x6E, 0x74, 0x20, 0x6267, 0x884C))
# 「自我声明」的判据形态：同一行里既自称（本文件 / 本文 / 本册 / 本手册），又带上面那串 ——
# 只带串、不带自称的，是在**转述别人的声明**，不算这件自己声明（否则把提到它的文档一并误伤）。
_SELF_WORDS = ("".join(chr(c) for c in (0x672C, 0x6587, 0x4EF6)),
               "".join(chr(c) for c in (0x672C, 0x6587)),
               "".join(chr(c) for c in (0x672C, 0x518C)),
               "".join(chr(c) for c in (0x672C, 0x624B, 0x518C)))


def check_internal_declared(root, head_lines=5):
    """按「读者」分类的机器判据：答不出用户用途、且自己声明不参与执行的件，不该进安装包。

    只读每件的**前 head_lines 行**（看它自己的声明），不扫全篇 —— 免得把
    「转述别人声明」的件误判；并要求「自称 + 短语」同行出现。
    锚点排除 scripts/（检查器自身源码不是被检对象）、release/（元数据目录）、
    tests/（门禁判据数据，非面向用户的件）。返回 [(相对路径, 原因)]。
    """
    issues = []
    skip_top = {"scripts", "release", "tests"}
    for p in scan_roots([root]):
        rel = os.path.relpath(p, root).replace(os.sep, "/")
        if rel.split("/")[0] in skip_top:
            continue
        try:
            with open(p, encoding="utf-8", errors="ignore") as f:
                head = [f.readline() for _ in range(head_lines)]
        except OSError:
            continue
        declared = any(_SELF_DECL in ln and any(w in ln for w in _SELF_WORDS)
                       for ln in head)
        if declared and rel not in PUBLISH_EXCLUDE:
            issues.append((rel, "自我声明不参与 Agent 执行，却未登记进 constants.PUBLISH_EXCLUDE"))
    return issues


def check_delivery_root(root):
    """交付根卫生：外层只允许「成品 + .work/ 隐藏夹」。

    成品后缀走白名单（constants.DELIVERY_EXTS）；出现别的文件或非 .work/
    的子目录，即视为中间件外露。返回 [(名字, 原因)]。

    ⚠️ 覆盖边界（写明，避免期待错位）：本检查按**后缀**判定，只能抓「后缀不在
    白名单里」的外露件（如 render.log / chunks_plan.json / 临时 .py）。
    与成品同后缀的中间件（如原始材料 source.txt 与 TXT 成品、媒体分段件
    xxx_seg001.wav 与音频成品）**抓不到** —— 那要靠「中间件一律进 .work/」的落盘规范保证，不在本检查范围内。
    """
    try:
        names = sorted(os.listdir(root))
    except Exception as e:
        return [(root, "不可读: %s" % e)]
    bad = []
    for name in names:
        full = os.path.join(root, name)
        if os.path.isdir(full):
            if name != WORK_DIR:
                bad.append((name + "/", "非 %s 的子目录" % WORK_DIR))
        else:
            ext = os.path.splitext(name)[1].lower()
            if ext not in DELIVERY_EXTS:
                bad.append((name, "非白名单后缀（疑为中间件外露）"))
    return bad


def run_product(root, args):
    """产物出厂门禁：对交付物跑与包性质无关的通用扫描。

    适用任意产物目录（技能包 / 文档集 / 交付目录），不依赖大纲与产物清单。
    返回 exit code（0 = 无 FAIL）。
    """
    print("product gate root: %s" % root)
    files = scan_roots([root])
    print("files scanned: %d" % len(files))
    print("")
    total = 0

    print("P1) Red-line words / single-char:")
    total += report("red-line 0 hits", check_redwords(files))
    total += report("single-char 0 hits", check_substr(files, PIT, "pit"))
    print("")
    print("P2) Design-layer residue:")
    total += report("design-layer 0 hits", check_design(files))
    print("")
    print("P3) Internal marks (template layer must not ship):")
    if len(INTERNAL_MARKERS) < INTERNAL_FLOOR:
        print("  [FAIL] internal-marks: 词表条数 %d 低于下限 %d" % (len(INTERNAL_MARKERS), INTERNAL_FLOOR))
        total += 1
    ih = check_internal(files)
    if ih:
        print("  [FAIL] internal-marks: %d hit(s)" % len(ih))
        for p, ln, tag, ctx in ih[:20]:
            print("      %s:%d  | %s" % (p, ln, ctx))
        if len(ih) > 20:
            print("      ... %d more omitted" % (len(ih) - 20))
        total += len(ih)
    elif len(INTERNAL_MARKERS) >= INTERNAL_FLOOR:
        print("  [PASS] internal-marks: 0 hits (%d file(s))" % len(files))
    print("")
    print("P4) Newline discipline (informational for products):")
    nl = check_newlines(files)
    if nl:
        # 换行符是仓库侧的内部纪律；用户拿到的产物在别处另存就可能变 CRLF，
        # 故此处只报 WARN（可见但不阻断），不判 FAIL —— 不误伤用户产物。
        print("  [WARN] newline: %d file(s) not LF（非阻断；产物可在别处被另存）" % len(nl))
        for p, crlf, bare in nl[:20]:
            print("      %s  | CRLF=%d bare-CR=%d" % (p, crlf, bare))
    else:
        print("  [PASS] newline: %d file(s) all LF" % len(files))
    print("")
    print("P4b) Invisible-character discipline (package text must contain none):")
    ih2 = check_invisible(files)
    if ih2:
        print("  [FAIL] invisible-char: %d hit(s)" % len(ih2))
        for p, ln, tag, ctx in ih2[:20]:
            print("      %s:%d  | %s" % (p, ln, tag))
        total += len(ih2)
    else:
        print("  [PASS] invisible-char: 0 hits (%d file(s))" % len(files))

    if getattr(args, "delivery_root", False):
        print("")
        print("P5) Delivery-root hygiene (products + %s/ only):" % WORK_DIR)
        bad = check_delivery_root(root)
        if bad:
            print("  [FAIL] delivery-root: %d item(s) outside whitelist" % len(bad))
            for name, why in bad[:20]:
                print("      %s  | %s" % (name, why))
            total += len(bad)
        else:
            print("  [PASS] delivery-root: only products + %s/" % WORK_DIR)

    print("")
    if total:
        print("PRODUCT VERDICT: FAIL (%d to fix) -> exit 1" % total)
        return 1
    print("PRODUCT VERDICT: PASS (product clean) -> exit 0")
    return 0


def check_matrix_declaration(root):
    """格式 × 维度适用矩阵 + 决策 ≤3 的**声明在位性**（辛-3 / 决策不过三 的机器判据）。

    只查「声明在不在、口径一不一致」，不猜语义：
      · `references/mode-bc-guide.md` 须有矩阵表头，7 种格式列齐全；
        且「用途文体」「内容深度」两行对 Excel 标准表 / Excel 图表两列必须标「不适用」；
      · 三处（SKILL.md / popup-spec.md / mode-bc-guide.md）须一致声明「决策 ≤3」。
    返回缺失项清单（空 = 全过）。
    """
    issues = []
    mp = os.path.join(root, "references", "mode-bc-guide.md")
    if not os.path.isfile(mp):
        issues.append("缺文件 references/mode-bc-guide.md")
    else:
        lines = open(mp, encoding="utf-8").read().splitlines()
        hdr = None
        hi = -1
        for i, ln in enumerate(lines):
            s = ln.strip()
            if s.startswith("|") and "Word" in s and "Excel" in s and "TXT" in s:
                hdr = [c.strip() for c in s.strip("|").split("|")]
                hi = i
                break
        if not hdr:
            issues.append("mode-bc-guide.md 未见「维度 × 格式适用矩阵」表头")
        else:
            for fmtk in ("Word", "PPT", "Excel 标准表", "Excel 图表", "PDF", "MD", "TXT"):
                if fmtk not in hdr:
                    issues.append("矩阵缺格式列：%s" % fmtk)
            for rowname in ("用途文体", "内容深度"):
                row = None
                # 只在本矩阵表内找行（表头之后、且以 | 开头的连续表行），
                # 避免误抓文件里另一张表（如「默认值 + 口头出口」表）的同名列。
                for ln in lines[hi + 1:]:
                    s = ln.strip()
                    if not s.startswith("|"):
                        break
                    cells = [c.strip() for c in s.strip("|").split("|")]
                    if cells and cells[0].strip("* ") == rowname:
                        row = cells
                        break
                if not row:
                    issues.append("矩阵缺行：%s" % rowname)
                    continue
                for fmtk in ("Excel 标准表", "Excel 图表"):
                    if fmtk not in hdr:
                        continue
                    j = hdr.index(fmtk)
                    if j >= len(row) or row[j] not in _NOT_APPLICABLE:
                        issues.append("矩阵 %s × %s 应标「不适用」" % (rowname, fmtk))
    need = {
        "SKILL.md": ["\u51b3\u7b56\u4e0d\u8fc7\u4e09", "\u7ef4\u5ea6 \u00d7 \u683c\u5f0f\u9002\u7528\u77e9\u9635"],
        "references/popup-spec.md": ["\u5168\u7a0b\u51b3\u7b56 \u22643", "\u7ef4\u5ea6 \u00d7 \u683c\u5f0f\u9002\u7528\u77e9\u9635", "\u4e0d\u5f39"],
        "references/mode-bc-guide.md": ["\u51b3\u7b56\u4e0d\u8fc7\u4e09", "\u7ef4\u5ea6 \u00d7 \u683c\u5f0f\u9002\u7528\u77e9\u9635"],
    }
    for rel, toks in need.items():
        p = os.path.join(root, rel)
        if not os.path.isfile(p):
            issues.append("缺文件 %s" % rel)
            continue
        t = open(p, encoding="utf-8").read()
        for tk in toks:
            if tk not in t:
                issues.append("%s 缺声明：%s" % (rel, tk))
    return issues


# 输出命名后缀枚举（与 references/bc-output-standards.md「输出文件命名硬规」同源 · 癸-6/癸-12）
NAMING_SUFFIXES = ("_数据表", "_汇总分析", "_图表分析", "_精华萃取", "_定向萃取")
NAMING_FORMULA_ANCHOR = "<材料名主干>_<动作后缀>"
NAMING_BANNED = ("Excel 标准数据表", "Excel 图表分析报告", "输出.xlsx", "输出.docx")
NAMING_SUFFIX_FLOOR = 5


def check_naming(root, files, artifacts=None):
    """癸-12 输出命名门禁。返回 issues（空 = 过）。

    静态（恒跑）——规范层三要件必须在位：
      a) 命名公式条文 `<材料名主干>_<动作后缀>`（癸-6）
      b) 后缀枚举 >= NAMING_SUFFIX_FLOOR 项（词表被删空即 FAIL，防判据失效）
      c) 禁用命名声明（包标签名 / 平台自拟名 / 无关联通用名）
    动态（给了 artifacts 时）——逐份比对真实产物名：
      d) 后缀须在枚举表内；e) 名干非空；f) 连接符半角（无全角 `＿` / 空格）

    判据只从被检对象（包内规范文件 + 真实产物）读取，不从本检查器自身读取。
    """
    issues = []
    parts = []
    for p in files:
        if p.endswith((".md", ".txt")):
            try:
                parts.append(open(p, "r", encoding="utf-8").read())
            except Exception:
                pass
    md = "\n".join(parts)
    if NAMING_FORMULA_ANCHOR not in md:
        issues.append("规范层缺命名公式条文：`%s`（癸-6）" % NAMING_FORMULA_ANCHOR)
    hit_sfx = [s for s in NAMING_SUFFIXES if s in md]
    if len(hit_sfx) < NAMING_SUFFIX_FLOOR:
        issues.append("后缀枚举不足（现 %d 项，应 >= %d 项）"
                      % (len(hit_sfx), NAMING_SUFFIX_FLOOR))
    if not any(b in md for b in NAMING_BANNED):
        issues.append("规范层缺「禁用命名」声明（包标签名 / 平台自拟名 / 无关联通用名）")
    for a in (artifacts or []):
        fn = os.path.basename(a)
        stem = os.path.splitext(fn)[0]
        if "\uff3f" in stem or " " in stem or "\u3000" in stem:
            issues.append("产物名含全角连接符 / 空格：%s" % fn)
        m = [s for s in NAMING_SUFFIXES if stem.endswith(s)]
        if not m:
            issues.append("产物名后缀不在枚举表内：%s" % fn)
        elif not stem[: -len(m[0])]:
            issues.append("产物名名干为空：%s" % fn)
    return issues


def report(name, hits):
    if hits:
        print("  [FAIL] %s: %d hit(s)" % (name, len(hits)))
        for p, ln, cid, ctx in hits[:20]:
            print("      [%s] %s:%d  | %s" % (cid, p, ln, ctx))
        if len(hits) > 20:
            print("      ... %d more omitted" % (len(hits) - 20))
    else:
        print("  [PASS] %s" % name)
    return len(hits)


# ---------------- wiring audit (script list completeness as a gate) ----------------

def load_exempt(root):
    """读取 tests/exempt.json -> {文件名: {since, reason, revisit}}。"""
    p = os.path.join(root, "tests", "exempt.json")
    if not os.path.isfile(p):
        return {}, p
    try:
        d = json.load(open(p, encoding="utf-8"))
    except Exception:
        return {}, p
    if isinstance(d, dict) and isinstance(d.get("exempt"), dict):
        return d["exempt"], p
    return (d if isinstance(d, dict) else {}), p


def check_script_wiring(root):
    """反向对账：scripts/*.py 每个要么带 --self-test，要么在 exempt.json 里且字段齐全。

    豁免准入：
      - 必填 since + reason；
      - 且必须二选一：expires_in=<版本>（到该版本仍无自测即 FAIL）
                      或 permanent=true（结构性常驻：入参/环境依赖，写死理由）；
      - 两者皆无 -> FAIL。到期未接线 -> FAIL，理由写明，不退化为 WARN。

    返回 (wired, exempt_used, unwired, expired)。expired = 已到期者名单。"""
    sd = os.path.join(root, "scripts")
    wired, used, unwired, expired = [], [], [], []
    if not os.path.isdir(sd):
        return wired, used, unwired, expired
    exempt, _ = load_exempt(root)
    cur = _cur_version(root)
    for fn in sorted(os.listdir(sd)):
        if not fn.endswith(".py"):
            continue
        if fn == "selfcheck.py":
            wired.append(fn)
            continue
        try:
            src = open(os.path.join(sd, fn), encoding="utf-8").read()
        except Exception:
            unwired.append((fn, "无法读取源码"))
            continue
        if has_selftest_support(src):
            wired.append(fn)
            continue
        e = exempt.get(fn)
        if not isinstance(e, dict):
            unwired.append((fn, "既无 --self-test 也无 tests/exempt.json 豁免"))
            continue
        miss = [k for k in EXEMPT_FIELDS if not str(e.get(k, "")).strip()]
        if miss:
            unwired.append((fn, "豁免条目缺字段: %s" % ",".join(miss)))
            continue
        exp = str(e.get("expires_in", "") or "").strip()
        perm = bool(e.get("permanent"))
        if not exp and not perm:
            unwired.append((fn, "豁免无期限且无常驻标记（须 expires_in=<版本> 或 permanent=true）"))
            continue
        if exp and cur and _ver_tuple(cur) >= _ver_tuple(exp):
            unwired.append((fn, "豁免已到期（expires_in=%s，当前 %s）——补 --self-test 或重申并顺延理由"
                            % (exp, cur)))
            expired.append(fn)
            continue
        used.append((fn, e))
    return wired, used, unwired, expired


# ---------------- subprocess helper (sandbox-aware) ----------------

def run_cmd(cmd):
    """返回 (rc, out, err, blocked)。blocked=True = 环境不允许起子进程（沙箱），
    调用方应判 SKIP 而非 FAIL —— 环境不具备不代表代码有病。"""
    try:
        p = _sp.run(cmd, capture_output=True, text=True,
                    encoding="utf-8", errors="replace")
        return p.returncode, p.stdout, p.stderr, False
    except OSError as e:
        return None, "", "%s: %s" % (type(e).__name__, e), True


def run_selftests(scripts_dir, quiet=False):
    """遍历 scripts/ 中含 --self-test 的脚本，逐个 subprocess 实跑，断言 exit=0。
    返回 (count, all_ok, blocked_count)。"""
    py = sys.executable
    count = 0
    all_ok = True
    blocked = 0
    for fn in sorted(os.listdir(scripts_dir)):
        if not fn.endswith(".py") or fn.startswith("_") or fn == "selfcheck.py":
            continue
        path = os.path.join(scripts_dir, fn)
        try:
            src = open(path, encoding="utf-8").read()
        except Exception:
            continue
        if not has_selftest_support(src):
            continue
        count += 1
        rc, out, err, is_blocked = run_cmd([py, path, "--self-test"])
        if is_blocked:
            blocked += 1
            if not quiet:
                print("  [SKIP] %s --self-test (环境不支持子进程: %s)" % (fn, err))
            continue
        if rc == 0:
            if not quiet:
                print("  [PASS] %s --self-test" % fn)
        else:
            all_ok = False
            if not quiet:
                print("  [FAIL] %s --self-test exit=%s" % (fn, rc))
                for line in (out + err).strip().splitlines()[-8:]:
                    print("      %s" % line[:110])
    return count, all_ok, blocked


# ---------------- 自测后残留复查 ----------------
# 跑完自测立刻比对包内文件快照，净新增/改动/减少一律 FAIL。

def snapshot_pkg(root):
    """包内文件快照：{相对路径: (size, mtime_ns)}。

    不按扩展名过滤 —— 任何扩展名都算。仅排除元数据目录（见 EXCLUDE_DIRS）与点开头目录
    （它们不进安装包，且 __pycache__ 是编译必然产物）。
    """
    snap = {}
    for dp, dns, fns in os.walk(root):
        dns[:] = [d for d in dns if d not in EXCLUDE_DIRS and not d.startswith(".")]
        for fn in fns:
            fp = os.path.join(dp, fn)
            try:
                st = os.stat(fp)
            except OSError:
                continue
            snap[os.path.relpath(fp, root).replace(os.sep, "/")] = (st.st_size, st.st_mtime_ns)
    return snap


def snapshot_dir_top(path):
    """目录顶层（不递归）快照：{文件名: (size, mtime_ns)}。

    只扫顶层：产物若落在「当前目录」，就是直接落顶层（body_1.txt 那样）；
    递归整个 CWD 既慢又会扫进与本包无关的文件，反而制造噪音。
    """
    snap = {}
    try:
        names = os.listdir(path)
    except OSError:
        return snap
    for fn in names:
        fp = os.path.join(path, fn)
        if not os.path.isfile(fp):
            continue
        try:
            st = os.stat(fp)
        except OSError:
            continue
        snap[fn] = (st.st_size, st.st_mtime_ns)
    return snap


def diff_snapshots(before, after):
    """比对两份快照，返回 (added, changed, removed)，均已排序。"""
    b, a = set(before), set(after)
    return (sorted(a - b),
            sorted(k for k in (a & b) if before[k] != after[k]),
            sorted(b - a))


def cwd_inside(root):
    """当前工作目录是否落在包根内（含相等）。落在包内时只需一处快照。"""
    cwd = os.path.abspath(os.getcwd())
    ra = os.path.abspath(root)
    return cwd == ra or cwd.startswith(ra + os.sep)


# ---------------- --full : one command, one exit code ----------------

def run_full(root, args):
    """按代价升序串门禁，输出 PASS/FAIL/SKIP 三态表。返回 exit code。"""
    py = sys.executable
    sd = os.path.join(root, "scripts")
    rows = []          # (state, label, detail)；state in PASS/FAIL/SKIP/WARN/DETAIL

    def add(state, label, detail=""):
        rows.append((state, label, detail))

    # 1) 九扫描
    files = scan_roots([root])
    n_red = len(check_redwords(files))
    n_pit = len(check_substr(files, PIT, "pit"))
    n_des = len(check_design(files))
    n_term = sum(len(check_substr(files, t, t)) for t in TERM_MUST_ZERO)
    n_nl = len(check_newlines(files))
    invis_hits = check_invisible(files)
    n_invis = len(invis_hits)
    ver_hits, ver_stale = check_version_residue(root, files)
    n_ver = len(ver_hits)
    aud_hits, aud_anchor = check_audience_words(files)
    n_aud = len(aud_hits)
    aud_thin = len(AUDIENCE_MARKERS) < AUDIENCE_FLOOR
    prosell_hits = check_prosell(files)
    n_prosell = len(prosell_hits)
    prosell_thin = len(PROSELL_MARKERS) < PROSELL_FLOOR
    n_scan = (n_red + n_pit + n_des + n_term + n_nl + n_invis + n_ver + n_aud + n_prosell
              + (1 if ver_stale else 0) + (1 if aud_thin else 0)
              + (1 if prosell_thin else 0))
    scan_label = "九扫描（红线词/单字/构思层/术语一致/换行符/不可见字符/版本号/人群限定词/禁推销）"
    if n_scan:
        add("FAIL", scan_label,
            "命中 %d（红线%d 单字%d 构思%d 术语%d 换行%d 隐形%d 版本%d 人群%d 推销%d）"
            % (n_scan, n_red, n_pit, n_des, n_term, n_nl, n_invis, n_ver, n_aud, n_prosell))
        for h in (check_redwords(files) + check_substr(files, PIT, "pit")
                  + check_design(files))[:8]:
            add("DETAIL", "  └ %s" % h[0], "%s:%s" % (h[1], h[3]))
        for p, crlf, bare in check_newlines(files)[:8]:
            add("DETAIL", "  └ %s" % p, "非 LF：CRLF=%d 裸CR=%d" % (crlf, bare))
        for p, ln, tag, ctx in invis_hits[:8]:
            add("DETAIL", "  └ %s" % p, "不可见字符 %s 在第 %s 行" % (tag, ln))
        if ver_stale:
            add("DETAIL", "  └ 版本号残留", "门禁版号族前缀未同步：当前 %s 不以 %s 开头 —— 请同步 selfcheck.VERSION_FAMILY_PREFIX"
                % (_cur_version(root), VERSION_FAMILY_PREFIX))
        for p, ln, tag, ctx in ver_hits[:8]:
            add("DETAIL", "  └ %s" % p, "%s:%s" % (ln, ctx))
        if aud_thin:
            add("DETAIL", "  └ 人群限定词",
                "词表条数 %d 低于下限 %d，请核对 AUDIENCE_MARKERS"
                % (len(AUDIENCE_MARKERS), AUDIENCE_FLOOR))
        for p, ln, tag, ctx in aud_hits[:8]:
            add("DETAIL", "  └ %s" % p, "%s:%s" % (ln, ctx))
        if prosell_thin:
            add("DETAIL", "  └ 禁推销措辞",
                "词表条数 %d 低于下限 %d，请核对 PROSELL_MARKERS"
                % (len(PROSELL_MARKERS), PROSELL_FLOOR))
        for p, ln, tag, ctx in prosell_hits[:8]:
            add("DETAIL", "  └ %s" % p, "%s:%s" % (ln, ctx))
    else:
        add("PASS", scan_label, "扫描 %d 文件，0 命中" % len(files))
    if not aud_anchor:
        add("WARN", "人群限定词白名单锚点",
            "包内未见「不设人群限定」声明行 —— 白名单口径可能失效，请核对 SKILL.md")

    # 1b) 格式 × 维度适用矩阵 + 决策 ≤3 的声明在位性（辛-3 / 决策不过三）
    mtx_issues = check_matrix_declaration(root)
    if mtx_issues:
        add("FAIL", "格式 × 维度适用矩阵 与 决策 ≤3 声明",
            "%d 处缺声明/口径不一致" % len(mtx_issues))
        for it in mtx_issues[:10]:
            add("DETAIL", "  └ ", it)
    else:
        add("PASS", "格式 × 维度适用矩阵 与 决策 ≤3 声明",
            "矩阵 7 列齐全，Excel 两列标不适用；三处决策 ≤3 一致")

    # 1c) 输出命名公式门禁（癸-12）
    nm_arts = getattr(args, "artifacts", None)
    nm_issues = check_naming(root, files, artifacts=nm_arts)
    if nm_issues:
        add("FAIL", "输出命名公式门禁（癸-12）", "%d 处不符" % len(nm_issues))
        for it in nm_issues[:10]:
            add("DETAIL", "  └ ", it)
    else:
        add("PASS", "输出命名公式门禁（癸-12）",
            ("静态三要件在位 + 真实产物 %d 份比对" % len(nm_arts)) if nm_arts
            else "静态三要件在位（产物层比对需 --artifacts）")

    # 2) 清单对账
    wired, used, unwired, expired = check_script_wiring(root)
    if unwired:
        add("FAIL", "脚本清单对账", "%d/%d 个脚本未接线%s"
            % (len(unwired), len(wired) + len(unwired),
               ("（含 %d 项豁免到期）" % len(expired)) if expired else ""))
        for fn, why in unwired[:10]:
            add("DETAIL", "  └ scripts/%s" % fn, why)
    else:
        add("PASS", "脚本清单对账", "%d 接线 / %d 常驻豁免" % (len(wired), len(used)))
    if used:
        add("WARN", "豁免台账（须逐条复核，见 tests/exempt.json）", "%d 项" % len(used))

    # 3) 全脚本编译
    if os.path.isdir(sd):
        targets = [os.path.join(sd, f) for f in sorted(os.listdir(sd)) if f.endswith(".py")]
        rc, out, err, blocked = run_cmd([py, "-m", "py_compile"] + targets)
        if blocked:
            add("SKIP", "全脚本编译", "环境不支持子进程：%s" % err)
        elif rc == 0:
            add("PASS", "全脚本编译", "%d 个脚本" % len(targets))
        else:
            add("FAIL", "全脚本编译", "exit=%s" % rc)
            for line in (out + err).strip().splitlines()[-6:]:
                add("DETAIL", "  └ ", line[:110])
    else:
        add("SKIP", "全脚本编译", "无 scripts/ 目录")

    # 4) 自带回归实跑（跑前先取包内快照，供 4b 复查比对）
    cwd_outside = not cwd_inside(root)
    pre_pkg = snapshot_pkg(root)
    pre_cwd = snapshot_dir_top(os.getcwd()) if cwd_outside else None
    n_self = 0
    self_blocked = False

    if os.path.isdir(sd):
        n, ok, blocked_n = run_selftests(sd, quiet=True)
        n_self = n
        self_blocked = bool(blocked_n and blocked_n == n)
        if self_blocked:
            add("SKIP", "自带回归实跑（--run-selftests）", "环境不支持子进程")
        elif ok:
            add("PASS", "自带回归实跑（--run-selftests）", "%d 个脚本，全部 exit=0" % n)
        else:
            add("FAIL", "自带回归实跑（--run-selftests）", "有脚本非 0 退出，见下方明细")
            for fn in sorted(os.listdir(sd)):
                if not fn.endswith(".py") or fn.startswith("_") or fn == "selfcheck.py":
                    continue
                p = os.path.join(sd, fn)
                try:
                    if not has_selftest_support(open(p, encoding="utf-8").read()):
                        continue
                except Exception:
                    continue
                rc2, o2, e2, b2 = run_cmd([py, p, "--self-test"])
                if not b2 and rc2 != 0:
                    add("DETAIL", "  └ %s --self-test" % fn, "exit=%s" % rc2)
                    for line in (o2 + e2).strip().splitlines()[-3:]:
                        add("DETAIL", "      ", line[:110])
    else:
        add("SKIP", "自带回归实跑（--run-selftests）", "无 scripts/ 目录")

    # 4b) 自测后残留复查 —— 判据贴在自测之后（详见函数区注释）
    post_pkg = snapshot_pkg(root)
    added, changed, removed = diff_snapshots(pre_pkg, post_pkg)
    if self_blocked:
        add("SKIP", "自测后残留复查", "自测未实跑（环境不支持子进程），无残留可比对")
    elif added or changed or removed:
        add("FAIL", "自测后残留复查",
            "跑完 %d 个自测后包内净变化：新增 %d / 改动 %d / 减少 %d"
            % (n_self, len(added), len(changed), len(removed)))
        for rel in added[:10]:
            add("DETAIL", "  └ %s" % rel, "新增 —— 自测产物不应落在包内")
        for rel in changed[:10]:
            add("DETAIL", "  └ %s" % rel, "被自测改写")
        for rel in removed[:10]:
            add("DETAIL", "  └ %s" % rel, "被自测删除")
    else:
        add("PASS", "自测后残留复查",
            "跑完 %d 个自测，包内 %d 个文件 0 新增 0 改动 0 减少" % (n_self, len(post_pkg)))
    if pre_cwd is not None:
        cwd_added, cwd_changed, _ = diff_snapshots(pre_cwd, snapshot_dir_top(os.getcwd()))
        if cwd_added or cwd_changed:
            add("WARN", "自测后残留复查（当前目录，包外）",
                "%d 个新文件 / %d 个改动落在当前目录" % (len(cwd_added), len(cwd_changed)))
            for fn in (cwd_added + cwd_changed)[:5]:
                add("DETAIL", "  └ %s" % fn, "疑似自测产物落在 CWD（未进包，故只告警）")

    # 5) 多格式组合联测（渲染环境）
    vrc = os.path.join(sd, "verify_render_combos.py") if os.path.isdir(sd) else None
    if vrc and os.path.isfile(vrc):
        rc, out, err, blocked = run_cmd([py, vrc])
        if blocked:
            add("SKIP", "多格式组合联测", "环境不支持子进程：%s" % err)
        elif rc == 0:
            add("PASS", "多格式组合联测（md+txt+docx+pptx / 双选 / 7 项全选）", "ALL OK")
        else:
            add("FAIL", "多格式组合联测", "exit=%s" % rc)
            for line in (out + err).strip().splitlines()[-5:]:
                add("DETAIL", "  └ ", line[:110])
    else:
        add("SKIP", "多格式组合联测", "无 scripts/verify_render_combos.py")

    # 5b) 产物契约联测（癸组：真跑 7 生成器，断言落款/免责/数字格式/筛选/冻结/图表色板进产物）
    vct = os.path.join(sd, "verify_contract.py") if os.path.isdir(sd) else None
    if vct and os.path.isfile(vct):
        rc, out, err, blocked = run_cmd([py, vct, "--self-test"])
        if blocked:
            add("SKIP", "产物契约联测（癸组 · 跨格式一致性）", "环境不支持子进程：%s" % err)
        elif rc == 0:
            add("PASS", "产物契约联测（癸组 · 跨格式一致性）",
                "7 生成器 × 落款/免责/数字格式/筛选/冻结/色板 全覆盖")
        else:
            add("FAIL", "产物契约联测（癸组 · 跨格式一致性）", "exit=%s" % rc)
            for line in (out + err).strip().splitlines()[-6:]:
                add("DETAIL", "  └ ", line[:110])
    else:
        add("SKIP", "产物契约联测（癸组 · 跨格式一致性）", "无 scripts/verify_contract.py")

    # 6) 7 版本 PPT 冒烟（渲染环境）
    vpv = os.path.join(sd, "verify_ppt_versions.py") if os.path.isdir(sd) else None
    if vpv and os.path.isfile(vpv):
        rc, out, err, blocked = run_cmd([py, vpv])
        if blocked:
            add("SKIP", "7 版本 PPT 冒烟", "环境不支持子进程：%s" % err)
        elif rc == 0:
            add("PASS", "7 版本 PPT 冒烟", "ALL OK")
        else:
            add("FAIL", "7 版本 PPT 冒烟", "exit=%s" % rc)
            for line in (out + err).strip().splitlines()[-5:]:
                add("DETAIL", "  └ ", line[:110])
    else:
        add("SKIP", "7 版本 PPT 冒烟", "无 scripts/verify_ppt_versions.py")

    # 7) golden 内容基线
    vb = os.path.join(sd, "verify_baseline.py") if os.path.isdir(sd) else None
    gb = os.path.join(root, "tests", "golden.json")
    if not (vb and os.path.isfile(vb)):
        add("SKIP", "golden 内容基线（抓内容漂移）", "无 scripts/verify_baseline.py")
    elif not os.path.isfile(gb):
        add("SKIP", "golden 内容基线（抓内容漂移）",
            "无 tests/golden.json —— 首版请先跑 verify_baseline.py --bless 建立基线")
    else:
        rc, out, err, blocked = run_cmd([py, vb, "--baseline", "--root", root])
        if blocked:
            add("SKIP", "golden 内容基线（抓内容漂移）", "环境不支持子进程：%s" % err)
        elif rc == 0:
            add("PASS", "golden 内容基线（抓内容漂移）", "指纹与基线一致")
        else:
            add("FAIL", "golden 内容基线（抓内容漂移）", "指纹漂移，exit=%s" % rc)
            for line in (out + err).strip().splitlines()[-8:]:
                add("DETAIL", "  └ ", line[:110])

    # 8) 真实产物一致性（需入参）
    vm = os.path.join(sd, "verify_multiformat.py") if os.path.isdir(sd) else None
    if args.outline and args.artifacts and vm and os.path.isfile(vm):
        cmd = [py, vm, "--outline", args.outline, "--files"] + list(args.artifacts)
        rc, out, err, blocked = run_cmd(cmd)
        if blocked:
            add("SKIP", "真实产物跨格式一致性", "环境不支持子进程：%s" % err)
        elif rc == 0:
            add("PASS", "真实产物跨格式一致性", "%d 个产物" % len(args.artifacts))
        else:
            add("FAIL", "真实产物跨格式一致性", "exit=%s" % rc)
            for line in (out + err).strip().splitlines()[-5:]:
                add("DETAIL", "  └ ", line[:110])
    else:
        add("SKIP", "真实产物跨格式一致性（verify_multiformat/verify_d3）",
            "未提供 --outline/--artifacts；出包前对真实产物单独跑")

    # ---- 三态表 ----
    print("")
    print("=" * 68)
    print("GATE TABLE (--full)   root: %s" % root)
    print("=" * 68)
    np_ = nf_ = ns_ = nw_ = 0
    for st, label, detail in rows:
        print("[%-6s] %s%s" % (st, label, ("  —— " + detail) if detail else ""))
        if st == "PASS":
            np_ += 1
        elif st == "FAIL":
            nf_ += 1
        elif st == "SKIP":
            ns_ += 1
        elif st == "WARN":
            nw_ += 1
    print("-" * 68)
    print("PASS %d / FAIL %d / SKIP %d / WARN %d" % (np_, nf_, ns_, nw_))
    if nf_:
        print("VERDICT: FAIL (%d) -> exit 1" % nf_)
        return 1
    tail = ("，其中 SKIP %d 项已逐条标注原因" % ns_) if ns_ else ""
    print("VERDICT: PASS（无 FAIL%s）-> exit 0" % tail)
    return 0


# ---------------- --prove-gates : negative controls ----------------

def _probe_pkg(root, td):
    """把源包复制成一次性探针包（改动只落在副本上）。

    ★ 判据面必须与主包一致：门禁扫描面 = scan_roots([root])（含 templates/），
      故探针包也要复制 templates/ —— 否则会出现「主包里更容易红、探针包里更容易绿」
      的口径差，探针证明的就不是主包那件事了。
    """
    pkg = os.path.join(td, "probe-skill")
    os.makedirs(pkg)
    for d in ("scripts", "references", "tests", "templates"):
        s = os.path.join(root, d)
        if os.path.isdir(s):
            shutil.copytree(s, os.path.join(pkg, d))
    for f in ("SKILL.md", "README.md", "_meta.json"):
        s = os.path.join(root, f)
        if os.path.isfile(s):
            shutil.copy2(s, os.path.join(pkg, f))
    return pkg


def _anchor_sources(pkg, token, exts=None, skip_top=()):
    """收集探针包内「含某个判据锚点串」的全部文件（= 该判据的全部来源）。

    用于阴性对照：一条判据的锚点可能同时落在主件与若干 references/templates 里，
    内容在册间搬迁时来源会变多 —— 只改一处时另一处仍满足要件，判据不响，
    对照会假绿。故探针一律**自动打全来源**，不硬编码路径。
    规则：判据有冗余时，阴性对照必须打全所有来源。
    """
    found = []
    for p in scan_roots([pkg]):
        rel = os.path.relpath(p, pkg).replace(os.sep, "/")
        if rel.split("/")[0] in skip_top:
            continue
        if exts is not None and not p.endswith(exts):
            continue
        try:
            t = open(p, encoding="utf-8").read()
        except Exception:
            continue
        if token in t:
            found.append(p)
    return sorted(found)


# ============ 元门禁自校验（阴性对照自身的守门） ============
# 守的是「证明门禁会红」这件事本身：阴性对照清单若被删条 / 被改小 / 被改坏，
# --prove-gates 仍可能照常打印 GATES PROVEN —— 那时它证明的已不是同一件事。
#
# 口径（写死，避免歧义）：「条数」= 运行时 results 的条数（= 打印行数），
#   不是源码里 append 的处数 —— 实测源码 40 处、运行时 29 条（部分组走 if/else 只执行一条）。
# 纪律：增 / 删 / 合并任何一条阴性对照，必须同步 NEG_CONTROLS_FLOOR 与 NEG_REQUIRED_GATES；
#   漏同步时自校验当场红 —— 这道红正是在问「你动了对照集合，是有意的吗」。
NEG_AUDIT_VERSION = 1
NEG_CONTROLS_FLOOR = 30
NEG_REQUIRED_FLOOR = 30
NEG_REQUIRED_GATES = (
    "扫描（红线词）",
    "自带回归实跑",
    "脚本清单对账",
    "多格式组合联测",
    "豁免到期拦截",
    "golden 内容基线",
    "换行符纪律（全 LF）",
    "自测后残留复查",
    "全脚本编译",
    "7 版本 PPT 冒烟",
    "真实产物跨格式一致性",
    "内部件登记核对",
    "版本号残留",
    "版本族前缀同步",
    "构思层扫描",
    "人群限定词扫描",
    "单字红线扫描",
    "术语一致扫描",
    "禁推销措辞扫描",
    "矩阵「不适用」标记",
    "矩阵表头缺列",
    "决策不过三声明",
    "产物契约联测（接线）",
    "免责声明全覆盖（底层）",
    "人群限定词白名单锚点",
    "输出命名公式门禁",
    "交付回执做法标签",
    "产物出厂门禁（内部标记）",
    "产物出厂门禁（干净放行）",
    "不可见字符扫描",
)


def _audit_neg_controls(results):
    """元门禁自校验：阴性对照清单本身有没有被削弱。返回问题列表（空 = 健康）。

    三条判据（任一条红，都说明「门禁会红」这件事不再被完整证明）：
      ① 实际条数低于下限 —— 有人删了 / 合并了对照；
      ② 必需门类名单本身被改小 —— 名单这个「锚」被动过；
      ③ 某个必需门类不再被覆盖 —— 对照还在，但换了个人不认得的名。
    """
    issues = []
    if len(results) < NEG_CONTROLS_FLOOR:
        issues.append("对照条数 %d < 下限 %d" % (len(results), NEG_CONTROLS_FLOOR))
    if len(NEG_REQUIRED_GATES) < NEG_REQUIRED_FLOOR:
        issues.append("必需门类名单 %d 条 < 下限 %d（名单被改小？）"
                      % (len(NEG_REQUIRED_GATES), NEG_REQUIRED_FLOOR))
    names = set(n for n, _h, _note in results)
    missing = [g for g in NEG_REQUIRED_GATES if g not in names]
    if missing:
        issues.append("必需门类缺失 %d 个：%s" % (len(missing), "、".join(missing)))
    return issues


def prove_gates(root):
    """阴性对照：每道门禁故意改坏一处，断言它必须报警。全部通过才算门禁可信。
    """
    py = sys.executable
    td = tempfile.mkdtemp()
    print("prove-gates root(源): %s" % root)
    print("prove-gates 副本: %s" % td)
    print("")
    results = []

    pkg = _probe_pkg(root, td)
    sc = os.path.join(pkg, "scripts", "selfcheck.py")

    # 阴性1：塞一个红线词 -> 扫描必须红
    red = "".join(chr(c) for c in (0x907f, 0x5751))
    rp = os.path.join(pkg, "references", "probe_red.md")
    open(rp, "w", encoding="utf-8").write("探针行：" + red + "\n")
    rc, out, err, blocked = run_cmd([py, sc, pkg])
    hit1 = ("[FAIL] red-line 0 hits" in out)
    os.remove(rp)
    results.append(("扫描（红线词）", hit1, "塞入红线词后 exit=%s" % rc))

    # 阴性2：一个脚本 --self-test 断言失败 -> --run-selftests 必须红
    p2 = os.path.join(pkg, "scripts", "probe_selftest.py")
    open(p2, "w", encoding="utf-8").write(
        "import sys\n"
        'if "--self-test" in sys.argv:\n'
        '    assert False, "probe: deliberate failure"\n')
    rc, out, err, blocked = run_cmd([py, sc, pkg, "--run-selftests"])
    hit2 = ("probe_selftest.py" in out) and (rc != 0)
    os.remove(p2)
    results.append(("自带回归实跑", hit2, "改坏一个自测后 exit=%s" % rc))

    # 阴性3：一个脚本既无自测又无豁免 -> 清单对账必须红
    p3 = os.path.join(pkg, "scripts", "probe_wiring.py")
    open(p3, "w", encoding="utf-8").write('print("probe")\n')
    rc, out, err, blocked = run_cmd([py, sc, pkg])
    hit3 = ("probe_wiring.py" in out) and (rc != 0)
    os.remove(p3)
    results.append(("脚本清单对账", hit3, "加入未接线脚本后 exit=%s" % rc))

    # 阴性4：把 PPT 分支签名改成错误版本 -> 组合联测必须红
    ds = os.path.join(pkg, "scripts", "distill_skeleton.py")
    src = open(ds, encoding="utf-8").read()
    broken = src.replace(
        "rppt(o, p, mode=mode, palette=palette, font=font, scale=scale)",
        "rppt(o, p, mode=mode, palette=palette, font=font, scale=scale, number=number)")
    if broken != src:
        open(ds, "w", encoding="utf-8").write(broken)
        vrc = os.path.join(pkg, "scripts", "verify_render_combos.py")
        rc, out, err, blocked = run_cmd([py, vrc])
        hit4 = (not blocked) and (rc != 0)
        results.append(("多格式组合联测", hit4, "改成错误签名后 exit=%s" % rc))
    else:
        results.append(("多格式组合联测", False, "探针注入点未命中（源码签名已变，需同步探针）"))

    # 阴性5：豁免已到期（expires_in 达当前版本仍无自测）-> 清单对账必须红
    ex_p = os.path.join(pkg, "tests", "exempt.json")
    ex_orig = open(ex_p, encoding="utf-8").read() if os.path.isfile(ex_p) else '{"exempt": {}}'
    pe = os.path.join(pkg, "scripts", "probe_expire.py")
    open(pe, "w", encoding="utf-8").write('print("probe")\n')
    try:
        dd = json.loads(ex_orig)
    except Exception:
        dd = {"exempt": {}}
    dd.setdefault("exempt", {})["probe_expire.py"] = {
        "since": "initial", "reason": "探针：故意设一个即到期的豁免",
        "expires_in": _cur_version(root) or "0.0.1"}
    open(ex_p, "w", encoding="utf-8").write(json.dumps(dd, ensure_ascii=False))
    rc, out, err, blocked = run_cmd([py, sc, pkg])
    hit5 = (not blocked) and ("probe_expire.py" in out) and ("到期" in out) and (rc != 0)
    open(ex_p, "w", encoding="utf-8").write(ex_orig)
    if os.path.exists(pe):
        os.remove(pe)
    results.append(("豁免到期拦截", hit5, "设即到期豁免后 exit=%s" % rc))

    # 阴性6：把 md 渲染器要点读键改错（内容整段丢）-> golden 基线必须红
    bm = os.path.join(pkg, "scripts", "build_md_standard.py")
    src2 = open(bm, encoding="utf-8").read()
    broken2 = src2.replace(
        'items = list(sec.get("items", [])) or list(sec.get("body", []))',
        'items = list(sec.get("items", []))')
    if broken2 != src2:
        open(bm, "w", encoding="utf-8").write(broken2)
        vb = os.path.join(pkg, "scripts", "verify_baseline.py")
        rc, out, err, blocked = run_cmd([py, vb, "--baseline", "--root", pkg])
        hit6 = (not blocked) and (rc != 0) and ("模块内容命中变化" in out)
        open(bm, "w", encoding="utf-8").write(src2)
        results.append(("golden 内容基线", hit6, "删 md 要点后 exit=%s" % rc))
    else:
        results.append(("golden 内容基线", False, "探针注入点未命中（build_md 读键已变，需同步探针）"))

    # 阴性7：注入一个 CRLF 文件 -> 换行符纪律必须红
    nl_p = os.path.join(pkg, "references", "probe_crlf.md")
    open(nl_p, "wb").write("探针行一\r\n探针行二\r\n".encode("utf-8"))
    rc, out, err, blocked = run_cmd([py, sc, pkg])
    hit7 = (not blocked) and (rc != 0) and ("newline" in out.lower()) and ("CRLF=" in out)
    os.remove(nl_p)
    results.append(("换行符纪律（全 LF）", hit7, "注入 CRLF 后 exit=%s" % rc))

    # 阴性8：某个脚本的自测把产物写进包根 -> 自测后残留复查必须红
    # 形态：脚本在 --self-test 下往包容器的根目录落一个文件。
    # 这条门禁与扫描独立：扫描跑在自测之前，看不到这个文件，只有复查能抓。
    rp8 = os.path.join(pkg, "scripts", "probe_residue.py")
    open(rp8, "w", encoding="utf-8").write(
        "import os, sys\n"
        'if "--self-test" in sys.argv:\n'
        '    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))\n'
        '    fp = os.path.join(root, "probe_leftover.txt")\n'
        '    open(fp, "w", encoding="utf-8", newline="\\n").write("probe residue\\n")\n')
    rc, out, err, blocked = run_cmd([py, sc, pkg, "--full"])
    hit8 = (not blocked) and (rc != 0) and bool(
        re.search(r"\[FAIL\s*\]\s*自测后残留复查", out))
    stray = os.path.join(pkg, "probe_leftover.txt")
    if os.path.exists(stray):
        os.remove(stray)
    os.remove(rp8)
    results.append(("自测后残留复查", hit8, "自测落包内产物后 exit=%s" % rc))

    # 阴性9：往 scripts/ 塞一个语法坏掉的脚本 -> 全脚本编译必须红
    #   登记为「常驻豁免」，让清单对账保持绿 —— 把红灯**只**打在这一道门上。
    ex_p9 = os.path.join(pkg, "tests", "exempt.json")
    ex_orig9 = open(ex_p9, encoding="utf-8").read() if os.path.isfile(ex_p9) else '{"exempt": {}}'
    ps_p = os.path.join(pkg, "scripts", "probe_syntax.py")
    open(ps_p, "w", encoding="utf-8", newline="\n").write("def broken(:\n    return 1\n")
    try:
        dd9 = json.loads(ex_orig9)
    except Exception:
        dd9 = {"exempt": {}}
    dd9.setdefault("exempt", {})["probe_syntax.py"] = {
        "since": "initial", "reason": "探针：故意放一个语法坏掉的脚本",
        "permanent": True}
    open(ex_p9, "w", encoding="utf-8", newline="\n").write(json.dumps(dd9, ensure_ascii=False))
    rc, out, err, blocked = run_cmd([py, sc, pkg, "--full"])
    hit9 = (not blocked) and (rc != 0) and bool(
        re.search(r"\[FAIL\s*\]\s*全脚本编译", out))
    open(ex_p9, "w", encoding="utf-8", newline="\n").write(ex_orig9)
    if os.path.exists(ps_p):
        os.remove(ps_p)
    results.append(("全脚本编译", hit9, "塞入语法坏脚本后 exit=%s" % rc))

    # 阴性10：把 minimal 版本的配色改掉 -> 7 版本 PPT 冒烟必须红
    dts = os.path.join(pkg, "scripts", "design_tokens.py")
    src10 = open(dts, encoding="utf-8").read()
    broken10 = src10.replace('"minimal":  {"palette": "sky",',
                             '"minimal":  {"palette": "amber",')
    if broken10 != src10:
        open(dts, "w", encoding="utf-8", newline="\n").write(broken10)
        vpv10 = os.path.join(pkg, "scripts", "verify_ppt_versions.py")
        rc, out, err, blocked = run_cmd([py, vpv10])
        hit10 = (not blocked) and (rc != 0)
        open(dts, "w", encoding="utf-8", newline="\n").write(src10)
        results.append(("7 版本 PPT 冒烟", hit10, "改错版本配色后 exit=%s" % rc))
    else:
        results.append(("7 版本 PPT 冒烟", False,
                        "探针注入点未命中（design_tokens VERSIONS 已变，需同步探针）"))

    # 阴性11：真实产物少一个模块 / 丢一段成段正文 -> 真实产物跨格式一致性必须红
    #   两条子探针都走 --full 接线（证明门禁在交付链里真的会发生）。
    #   段落探针的判定串由探针自己拼出、不写进脚本源码，避免判据句含被检字符串。
    para_probe = ("探针" + "成" + "段" + "正" + "文" + "片" + "段"
                  + "甲乙丙丁戊己庚辛")
    od = os.path.join(td, "probe_outline.json")
    with open(od, "w", encoding="utf-8", newline="\n") as f:
        json.dump({"sections": [
            {"heading": "01：模块甲", "paragraphs": [para_probe]},
            {"heading": "02：模块乙"}]}, f, ensure_ascii=False)
    # 子探针 A：少一个模块
    bad_art = os.path.join(td, "probe_missing_module.txt")
    with open(bad_art, "w", encoding="utf-8", newline="\n") as f:
        f.write("模块甲\n")
    rc, out, err, blocked = run_cmd([py, sc, pkg, "--full", "--outline", od,
                                     "--artifacts", bad_art])
    hit11a = (not blocked) and (rc != 0) and bool(
        re.search(r"\[FAIL\s*\]\s*真实产物跨格式一致性", out))
    # 子探针 B：模块标题齐全，只丢成段正文（隔离出新条判据）
    bad_art2 = os.path.join(td, "probe_lost_paragraph.txt")
    with open(bad_art2, "w", encoding="utf-8", newline="\n") as f:
        f.write("模块甲\n模块乙\n")
    rc2, out2, err2, blocked2 = run_cmd([py, sc, pkg, "--full", "--outline", od,
                                         "--artifacts", bad_art2])
    hit11b = (not blocked2) and (rc2 != 0) and bool(
        re.search(r"\[FAIL\s*\]\s*真实产物跨格式一致性", out2))
    results.append(("真实产物跨格式一致性", hit11a and hit11b,
                    "少模块 exit=%s / 丢成段正文 exit=%s" % (rc, rc2)))

    # 阴性11b：包根出现一个「自我声明不参与执行」却未登记的件 -> internal-declared 必须红
    #   （证明这道判据真的会红，而不是恒为真；标记串由码点拼出，不落进本文件字面）
    pp = os.path.join(pkg, "probe_log.md")
    with open(pp, "w", encoding="utf-8", newline="\n") as f:
        f.write("# 探针\n\n> 本文件" + _SELF_DECL + "、也不被 SKILL.md 加载。\n")
    rc, out, err, blocked = run_cmd([py, sc, pkg])
    hit11c = (not blocked) and (rc != 0) and ("[FAIL] internal-declared" in out)
    if os.path.exists(pp):
        os.remove(pp)
    results.append(("内部件登记核对", hit11c, "塞入未登记的内部件后 exit=%s" % rc))

    # 阴性12：在文档里留一处本包版号标注 -> 版本号残留必须红
    #   版号串由常量拼出，避免本文件自身命中该扫描。
    vp = os.path.join(pkg, "references", "probe_version.md")
    vres = VERSION_FAMILY_PREFIX + "99"
    with open(vp, "w", encoding="utf-8", newline="\n") as f:
        f.write("探针：版号标注（" + vres + " 立）\n")
    rc, out, err, blocked = run_cmd([py, sc, pkg])
    hit12 = (not blocked) and (rc != 0) and bool(
        re.search(r"\[FAIL\] version-residue: \d+ hit", out))
    os.remove(vp)
    results.append(("版本号残留", hit12, "留本包版号标注后 exit=%s" % rc))

    # 阴性13：把 _meta.json 的版号升出本族（不同步门禁前缀）-> 门禁须自报失配。
    mp = os.path.join(pkg, "_meta.json")
    mp_orig = open(mp, encoding="utf-8").read() if os.path.isfile(mp) else "{}"
    try:
        dj = json.loads(mp_orig)
    except Exception:
        dj = {}
    cur_major = re.sub(r"\D", "", str(dj.get("version", "") or "1").split(".")[0]) or "1"
    dj["version"] = "%d.0.0" % (int(cur_major) + 1)
    with open(mp, "w", encoding="utf-8", newline="\n") as f:
        json.dump(dj, f, ensure_ascii=False, indent=2)
    rc, out, err, blocked = run_cmd([py, sc, pkg])
    hit13 = (not blocked) and (rc != 0) and ("版号族前缀未同步" in out)
    with open(mp, "w", encoding="utf-8", newline="\n") as f:
        f.write(mp_orig)
    results.append(("版本族前缀同步", hit13, "版号升出本族后 exit=%s" % rc))

    # 阴性14：塞一处构思层措辞 -> 构思层扫描必须红
    #   命中词取新增族一员（见 marker14 码点），保证扩容后的词表真的在响。
    dm = os.path.join(pkg, "references", "probe_design.md")
    marker14 = "".join(chr(c) for c in (0x95EE, 0x9898, 0x80CC, 0x666F))
    with open(dm, "w", encoding="utf-8", newline="\n") as f:
        f.write("探针：" + marker14 + "：出过这个问题\n")
    rc, out, err, blocked = run_cmd([py, sc, pkg])
    hit14 = (not blocked) and (rc != 0) and bool(
        re.search(r"\[FAIL\] design-layer \d+ hit", out))
    os.remove(dm)
    results.append(("构思层扫描", hit14, "塞入构思层措辞后 exit=%s" % rc))

    # 阴性15：文档里塞一处人群限定词 -> 人群限定词扫描必须红
    #   命中词由常量取（AUDIENCE_MARKERS[0]），避免本文件自身命中该扫描。
    ap = os.path.join(pkg, "references", "probe_audience.md")
    aword = AUDIENCE_MARKERS[0]
    with open(ap, "w", encoding="utf-8", newline="\n") as f:
        f.write("探针：常用于" + aword + "。\n")
    rc, out, err, blocked = run_cmd([py, sc, pkg])
    hit15 = (not blocked) and (rc != 0) and bool(
        re.search(r"\[FAIL\] audience-words: \d+ hit", out))
    os.remove(ap)
    results.append(("人群限定词扫描", hit15, "塞入人群限定词后 exit=%s" % rc))

    # 阴性16：塞一个单字红线词 -> 单字扫描必须红
    pp = os.path.join(pkg, "references", "probe_pit.md")
    with open(pp, "w", encoding="utf-8", newline="\n") as f:
        f.write("探针：这里有个" + PIT + "。\n")
    rc, out, err, blocked = run_cmd([py, sc, pkg])
    hit16 = (not blocked) and (rc != 0) and ("[FAIL] single-char" in out)
    os.remove(pp)
    results.append(("单字红线扫描", hit16, "塞入单字后 exit=%s" % rc))

    # 阴性17：塞一个「术语必须为 0」的词 -> 术语一致扫描必须红
    #   命中词由常量取（TERM_MUST_ZERO[0]），避免本文件自身命中该扫描。
    tp = os.path.join(pkg, "references", "probe_term.md")
    termw = TERM_MUST_ZERO[0]
    with open(tp, "w", encoding="utf-8", newline="\n") as f:
        f.write("探针：此处出现术语 " + termw + "。\n")
    rc, out, err, blocked = run_cmd([py, sc, pkg])
    hit17 = (not blocked) and (rc != 0) and ("[FAIL] term 0 hits" in out)
    os.remove(tp)
    results.append(("术语一致扫描", hit17, "塞入禁用术语后 exit=%s" % rc))

    # 阴性18：塞一个推销话术词 -> 禁推销扫描（第九道）必须红
    #   命中词由常量取（PROSELL_MARKERS[0]），避免本文件自身命中该扫描。
    slp = os.path.join(pkg, "references", "probe_prosell.md")
    sellw = PROSELL_MARKERS[0]
    with open(slp, "w", encoding="utf-8", newline="\n") as f:
        f.write("探针：" + sellw + "，错过不再。\n")
    rc, out, err, blocked = run_cmd([py, sc, pkg])
    hit18 = (not blocked) and (rc != 0) and ("[FAIL] prosell" in out)
    os.remove(slp)
    results.append(("禁推销措辞扫描", hit18, "塞入推销话术词后 exit=%s" % rc))

    # 阴性19：把矩阵里 Excel 两列的「不适用」改成「适用」-> 矩阵声明门禁必须红
    mgp = os.path.join(pkg, "references", "mode-bc-guide.md")
    mg_orig = open(mgp, encoding="utf-8").read() if os.path.isfile(mgp) else ""
    row_wt = "| 用途文体 | \u2713 | \u2713 | \u2013 | \u2013 | \u2713 | \u2713 | \u2713 |"
    row_wt_bad = "| 用途文体 | \u2713 | \u2713 | \u2713 | \u2713 | \u2713 | \u2713 | \u2713 |"
    if row_wt in mg_orig:
        open(mgp, "w", encoding="utf-8", newline="\n").write(mg_orig.replace(row_wt, row_wt_bad))
        rc, out, err, blocked = run_cmd([py, sc, pkg])
        hit19 = (not blocked) and (rc != 0) and ("matrix-declaration" in out)
        open(mgp, "w", encoding="utf-8", newline="\n").write(mg_orig)
        results.append(("矩阵「不适用」标记", hit19, "把 Excel 列改成适用后 exit=%s" % rc))
    else:
        results.append(("矩阵「不适用」标记", False, "探针注入点未命中（矩阵行已变，需同步探针）"))

    # 阴性20：删掉矩阵表头一整列（Excel 图表）-> 矩阵声明门禁必须红
    hdr_wt = "| 维度 | Word | PPT | Excel 标准表 | Excel 图表 | PDF | MD | TXT |"
    hdr_bad = "| 维度 | Word | PPT | Excel 标准表 | PDF | MD | TXT |"
    mg_orig2 = open(mgp, encoding="utf-8").read() if os.path.isfile(mgp) else ""
    if hdr_wt in mg_orig2:
        open(mgp, "w", encoding="utf-8", newline="\n").write(mg_orig2.replace(hdr_wt, hdr_bad))
        rc, out, err, blocked = run_cmd([py, sc, pkg])
        hit20 = (not blocked) and (rc != 0) and ("矩阵缺格式列" in out)
        open(mgp, "w", encoding="utf-8", newline="\n").write(mg_orig2)
        results.append(("矩阵表头缺列", hit20, "删 Excel 图表列后 exit=%s" % rc))
    else:
        results.append(("矩阵表头缺列", False, "探针注入点未命中（矩阵表头已变，需同步探针）"))

    # 阴性21：删掉 SKILL.md 里的「决策不过三」声明 -> 声明一致性门禁必须红
    skp = os.path.join(pkg, "SKILL.md")
    sk_orig = open(skp, encoding="utf-8").read() if os.path.isfile(skp) else ""
    tok3 = "\u51b3\u7b56\u4e0d\u8fc7\u4e09"
    if tok3 in sk_orig:
        open(skp, "w", encoding="utf-8", newline="\n").write(sk_orig.replace(tok3, "\u51b3\u7b56\u9650\u4e09"))
        rc, out, err, blocked = run_cmd([py, sc, pkg])
        hit21 = (not blocked) and (rc != 0) and ("matrix-declaration" in out)
        open(skp, "w", encoding="utf-8", newline="\n").write(sk_orig)
        results.append(("决策不过三声明", hit21, "删 SKILL.md 声明后 exit=%s" % rc))
    else:
        results.append(("决策不过三声明", False, "探针注入点未命中（SKILL.md 已变，需同步探针）"))

    # 阴性22：把 txt 生成器的免责主句改没 -> 产物契约联测（门禁接线）必须红
    #   选此注入点的用意：txt 生成器的自测只断言标题/要点，不断言免责，
    #   故这条探针只打「产物契约联测」一道门（单点验证）。
    tb = os.path.join(pkg, "scripts", "build_txt_standard.py")
    tb_orig = open(tb, encoding="utf-8").read()
    tb_bad = tb_orig.replace(
        'L.append("\uff08%s\uff09" % constants.disclaimer(outline.get("topic")))',
        'L.append("")')
    if tb_bad != tb_orig:
        open(tb, "w", encoding="utf-8", newline="\n").write(tb_bad)
        rc, out, err, blocked = run_cmd([py, sc, pkg, "--full"])
        hit22 = (not blocked) and (rc != 0) and bool(
            re.search(r"\[FAIL\s*\]\s*产物契约联测", out))
        # 阴性23 复用同一注入点，但验证「底层检查」本身（直接跑 verify_contract）
        vc = os.path.join(pkg, "scripts", "verify_contract.py")
        rc23, out23, err23, blocked23 = run_cmd([py, vc, "--self-test"])
        hit23 = (not blocked23) and (rc23 != 0) and ("\u7f3a\u514d\u8d23\u58f0\u660e\u4e3b\u53e5" in out23)
        open(tb, "w", encoding="utf-8", newline="\n").write(tb_orig)
        results.append(("产物契约联测（接线）", hit22, "txt 免责丢失后 exit=%s" % rc))
        results.append(("免责声明全覆盖（底层）", hit23, "txt 免责丢失后 exit=%s" % rc23))
    else:
        results.append(("产物契约联测（接线）", False,
                        "探针注入点未命中（build_txt 免责行已变，需同步探针）"))
        results.append(("免责声明全覆盖（底层）", False, "同上，注入点未命中"))

    # 阴性24：把包内**所有**白名单锚点声明全部替换 -> 人群限定词白名单锚点必须转 WARN
    #   WARN 不阻断出包，故判据是「告警行出现」，不是 exit≠0。
    #   ★ 锚点来源有多处（主件 / references/*.md / templates/*），随内容下移会变多 ——
    #     本探针自动打全来源（只认非 scripts 层，与 check_audience_words 同口径）；
    #     只改一处时另一处仍满足「锚点在位」要件，判据不会响（探针要打全判据来源）。
    anchor_wt = "\u4e0d\u8bbe\u4eba\u7fa4\u9650\u5b9a"
    a_src = _anchor_sources(pkg, anchor_wt, skip_top=("scripts",))
    if a_src:
        a_orig = {}
        try:
            for f in a_src:
                t = open(f, encoding="utf-8").read()
                a_orig[f] = t
                open(f, "w", encoding="utf-8", newline="\n").write(
                    t.replace(anchor_wt, "\u4e0d\u8bbe\u9650\u5236"))
            rc, out, err, blocked = run_cmd([py, sc, pkg])
            hit24 = (not blocked) and ("[WARN] audience-words" in out)
        finally:
            for f, t in a_orig.items():
                open(f, "w", encoding="utf-8", newline="\n").write(t)
        results.append(("人群限定词白名单锚点", hit24,
                        "全部 %d 处锚点替换后 exit=%s" % (len(a_src), rc)))
    else:
        results.append(("人群限定词白名单锚点", False,
                        "探针注入点未命中（包内已无锚点声明，需同步探针）"))

    # 阴性25：改掉规范层**所有**命名公式锚点 -> 输出命名公式门禁（癸-12）必须红
    #   公式条文可同时落在主件与多册（内容下移后来源增多）—— 本探针自动打全来源
    #   （判据读的正是全部 .md/.txt）；只改一处时另一处仍满足「公式条文在位」要件，
    #   判据不会响。后缀枚举不动、不打其他门（单点验证）。命名门禁挂在 --full，故走 --full。
    nm_tok = "<\u6750\u6599\u540d\u4e3b\u5e72>_<\u52a8\u4f5c\u540e\u7f00>"
    n_src = _anchor_sources(pkg, nm_tok, exts=(".md", ".txt"))
    if n_src:
        n_orig = {}
        try:
            for f in n_src:
                t = open(f, encoding="utf-8").read()
                n_orig[f] = t
                open(f, "w", encoding="utf-8", newline="\n").write(
                    t.replace(nm_tok, "<\u6750\u6599\u540d>_<\u540e\u7f00>"))
            rc, out, err, blocked = run_cmd([py, sc, pkg, "--full"])
            hit25 = (not blocked) and (rc != 0) and bool(
                re.search(r"\[FAIL\s*\]\s*\u8f93\u51fa\u547d\u540d\u516c\u5f0f\u95e8\u7981", out))
        finally:
            for f, t in n_orig.items():
                open(f, "w", encoding="utf-8", newline="\n").write(t)
        results.append(("输出命名公式门禁", hit25,
                        "全部 %d 处公式锚点替换后 exit=%s" % (len(n_src), rc)))
    else:
        results.append(("输出命名公式门禁", False, "探针注入点未命中（公式锚点已变，需同步探针）"))

    # 阴性26：让 txt 生成器读错「做法标签」的键（receipt_tags -> 不存在的键）
    #   -> 产物契约联测必须红。
    #   选此注入点的用意：七个生成器的自测都不传 tags（走无标签分支），故不受影响；
    #   只有 verify_contract 传了 receipt_tags 并断言「做法标签」字样 —— 单点命中。
    #   这正是「适配层给 A 键、渲染器读 B 键 → 内容整段丢」的同一族缺陷。
    tb2 = os.path.join(pkg, "scripts", "build_txt_standard.py")
    tb2_orig = open(tb2, encoding="utf-8").read()
    tb2_bad = tb2_orig.replace(
        'constants.receipt_line(outline.get("receipt_tags"))',
        'constants.receipt_line(outline.get("receipt_tags_TYPO"))')
    if tb2_bad != tb2_orig:
        open(tb2, "w", encoding="utf-8", newline="\n").write(tb2_bad)
        rc, out, err, blocked = run_cmd([py, sc, pkg, "--full"])
        hit26 = (not blocked) and (rc != 0) and bool(
            re.search(r"\[FAIL\s*\]\s*产物契约联测", out))
        open(tb2, "w", encoding="utf-8", newline="\n").write(tb2_orig)
        results.append(("交付回执做法标签", hit26, "txt 读错标签键后 exit=%s" % rc))
    else:
        results.append(("交付回执做法标签", False, "探针注入点未命中（回执行已变，需同步探针）"))

    # 阴性27：产物出厂门禁（--product）—— 成对证明「真会红」且「真会绿」。
    #   a) 产物目录塞一处内部标记 -> 必须红
    #   b) 干净产物目录 -> 必须 PASS（证明这道门不是「永远报红」）
    mark = "<!-- INTER" + "NAL:BEGIN"
    prod = os.path.join(td, "probe_product_dirty")
    os.makedirs(prod, exist_ok=True)
    open(os.path.join(prod, "SKILL.md"), "w", encoding="utf-8", newline="\n").write(
        "---\nname: p\n---\n\n# p\n\n" + mark + "\n  内部说明\n-->\n")
    rc, out, err, blocked = run_cmd([py, sc, prod, "--product"])
    hit27 = ("[FAIL] internal-marks" in out) and (rc != 0)
    results.append(("产物出厂门禁（内部标记）", hit27, "塞内部标记后 exit=%s" % rc))

    clean = os.path.join(td, "probe_product_clean")
    os.makedirs(clean, exist_ok=True)
    open(os.path.join(clean, "SKILL.md"), "w", encoding="utf-8", newline="\n").write(
        "---\nname: c\n---\n\n# c\n\n正文\n")
    rc, out, err, blocked = run_cmd([py, sc, clean, "--product"])
    hit27b = ("PRODUCT VERDICT: PASS" in out) and (rc == 0)
    results.append(("产物出厂门禁（干净放行）", hit27b, "干净产物 exit=%s" % rc))

    # 阴性28：不可见字符扫描 —— 往包内文本塞一处零宽字符 -> 九扫描必须红
    #   零宽字符由 chr() 拼出，本文件自身不含该字面（否则探针会污染被检集）。
    ip = os.path.join(pkg, "references", "probe_invisible.md")
    with open(ip, "w", encoding="utf-8", newline="\n") as f:
        f.write("探针：一处零宽字符 " + chr(0x200B) + "\n")
    rc, out, err, blocked = run_cmd([py, sc, pkg])
    hit28 = (not blocked) and (rc != 0) and bool(
        re.search(r"\[FAIL\] invisible-char: \d+ hit", out))
    if os.path.exists(ip):
        os.remove(ip)
    results.append(("不可见字符扫描", hit28, "塞零宽字符后 exit=%s" % rc))

    print("---- 阴性对照结果（期望：全部「已报警」）----")
    ok_all = True
    for _idx, (name, hit, note) in enumerate(results, 1):
        ok_all = ok_all and hit
        print("  [%2d/%d] [%s] %-16s %s" % (_idx, len(results),
              "已报警" if hit else "未报警", name, note))
    print("")
    # ---- 元门禁自校验（阴性对照自身是否被削弱）----
    # 先对自己做「负向演练」：故意削一条 / 清空，自校验必须报出问题；
    # 报不出就说明这道自校验形同虚设，同样判 FAIL。
    issues = _audit_neg_controls(results)
    drill_short = _audit_neg_controls(results[:-1])
    drill_blank = _audit_neg_controls([])
    audit_ok = (not issues) and bool(drill_short) and bool(drill_blank)
    print("---- 元门禁自校验（阴性对照自身）----")
    print("  审计版本 v%d | 实际 %d 条（下限 %d）| 必需门类 %d 个（下限 %d）"
          % (NEG_AUDIT_VERSION, len(results), NEG_CONTROLS_FLOOR,
             len(NEG_REQUIRED_GATES), NEG_REQUIRED_FLOOR))
    if issues:
        for _s in issues:
            print("  [未守] %s" % _s)
    print("  负向演练：削一条 -> %s | 清空 -> %s"
          % ("已报出" if drill_short else "未报出",
             "已报出" if drill_blank else "未报出"))
    if not audit_ok:
        print("  [FAIL] 元门禁自校验未通过 —— 阴性对照清单可能已被削弱")
    print("RESULT:", "GATES PROVEN (each can fail)" if (ok_all and audit_ok) else "GATE PROOF FAILED")
    return ok_all and audit_ok


def main():
    ap = argparse.ArgumentParser(description="Package self-check")
    ap.add_argument("root", nargs="?", default=None,
                    help="技能包根目录（默认：本脚本上两级）")
    ap.add_argument("--run-selftests", action="store_true",
                    help="额外遍历 scripts/ 中带 --self-test 的脚本实跑断言 exit=0")
    ap.add_argument("--full", action="store_true",
                    help="一键门禁：九扫描→矩阵声明→命名门禁→清单对账→编译→实跑→残留复查→组合联测→产物契约→基线→真实产物，三态表")
    ap.add_argument("--prove-gates", action="store_true",
                    help="门禁自证：阴性对照逐条证明门禁会报警；并对阴性对照清单本身做元门禁自校验")
    ap.add_argument("--product", action="store_true",
                    help="产物出厂门禁：对交付物跑通用扫描（红线/单字/构思层/内部标记/换行符）")
    ap.add_argument("--delivery-root", action="store_true",
                    help="--product 用：额外检查交付根卫生（外层只允许成品 + .work/）")
    ap.add_argument("--outline", default=None, help="--full 用：真实产物对应的大纲 json")
    ap.add_argument("--artifacts", nargs="*", default=None,
                    help="--full 用：真实产物文件列表")
    args = ap.parse_args()
    if args.root:
        root = args.root
    else:
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    if args.prove_gates:
        sys.exit(0 if prove_gates(root) else 1)
    if args.product:
        sys.exit(run_product(root, args))
    if args.full:
        sys.exit(run_full(root, args))

    print("self-check root: %s" % root)
    files = scan_roots([root])
    print("files scanned: %d" % len(files))
    print("")

    total = 0
    print("1) Red-line word list (8 banned groups):")
    total += report("red-line 0 hits", check_redwords(files))
    print("")
    print("2) Single-char red line:")
    total += report("single-char 0 hits", check_substr(files, PIT, "pit"))
    print("")
    print("3) Design-layer residue (meta-narrative):")
    total += report("design-layer 0 hits", check_design(files))
    print("")
    print("4) Terminology consistency (must be 0):")
    for term in TERM_MUST_ZERO:
        total += report("term 0 hits", check_substr(files, term, term))

    # 5) 换行符纪律（全 LF）
    print("")
    print("5) Newline discipline (all LF):")
    nl = check_newlines(files)
    if nl:
        print("  [FAIL] newline: %d file(s) not LF" % len(nl))
        for p, crlf, bare in nl[:20]:
            print("      %s  | CRLF=%d bare-CR=%d" % (p, crlf, bare))
        if len(nl) > 20:
            print("      ... %d more omitted" % (len(nl) - 20))
        total += len(nl)
    else:
        print("  [PASS] newline: %d file(s) all LF" % len(files))

    # 5b) 不可见字符纪律（包内文本一处不许有；与接料清洗层同判据）
    print("")
    print("5b) Invisible-character discipline (must be 0):")
    ih3 = check_invisible(files)
    if ih3:
        print("  [FAIL] invisible-char: %d hit(s)" % len(ih3))
        for p, ln, tag, ctx in ih3[:20]:
            print("      %s:%d  | %s" % (p, ln, tag))
        if len(ih3) > 20:
            print("      ... %d more omitted" % (len(ih3) - 20))
        total += len(ih3)
    else:
        print("  [PASS] invisible-char: 0 hits (%d file(s))" % len(files))

    # 6) 版本号残留（本包版号族只准出现在版本声明字段行）
    print("")
    print("6) Version-number residue (only on version-declaration lines):")
    ver_hits, ver_stale = check_version_residue(root, files)
    if ver_stale:
        print("  [FAIL] version-residue: 门禁版号族前缀未同步（当前 %s 不以 %s 开头）"
              % (_cur_version(root), VERSION_FAMILY_PREFIX))
        total += 1
    if ver_hits:
        print("  [FAIL] version-residue: %d hit(s)" % len(ver_hits))
        for p, ln, tag, ctx in ver_hits[:20]:
            print("      %s:%d  | %s" % (p, ln, ctx))
        if len(ver_hits) > 20:
            print("      ... %d more omitted" % (len(ver_hits) - 20))
        total += len(ver_hits)
    if not ver_stale and not ver_hits:
        print("  [PASS] version-residue: 0 outside version fields (%d file(s))" % len(files))

    # 7) 人群限定词（本包「不设人群限定」铁律的机器判据）
    print("")
    print("7) Audience-narrowing words (exam / identity markers):")
    aud_hits, aud_anchor = check_audience_words(files)
    if len(AUDIENCE_MARKERS) < AUDIENCE_FLOOR:
        print("  [FAIL] audience-words: 词表条数 %d 低于下限 %d"
              % (len(AUDIENCE_MARKERS), AUDIENCE_FLOOR))
        total += 1
    if aud_hits:
        print("  [FAIL] audience-words: %d hit(s)" % len(aud_hits))
        for p, ln, tag, ctx in aud_hits[:20]:
            print("      %s:%d  | %s" % (p, ln, ctx))
        if len(aud_hits) > 20:
            print("      ... %d more omitted" % (len(aud_hits) - 20))
        total += len(aud_hits)
    if not aud_hits and len(AUDIENCE_MARKERS) >= AUDIENCE_FLOOR:
        print("  [PASS] audience-words: 0 hits (%d file(s))" % len(files))
    if not aud_anchor:
        print("  [WARN] audience-words: 白名单锚点「不设人群限定」声明行未见")

    # 8) 禁推销措辞（本包「不推销 / 不替用户决定掏钱」铁律的机器判据）
    print("")
    print("8) Prohibited sales pitch (imperative-buy / guaranteed-return):")
    if len(PROSELL_MARKERS) < PROSELL_FLOOR:
        print("  [FAIL] prosell: 词表条数 %d 低于下限 %d"
              % (len(PROSELL_MARKERS), PROSELL_FLOOR))
        total += 1
    ps_hits = check_prosell(files)
    if ps_hits:
        print("  [FAIL] prosell: %d hit(s)" % len(ps_hits))
        for p, ln, tag, ctx in ps_hits[:20]:
            print("      %s:%d  | %s" % (p, ln, ctx))
        if len(ps_hits) > 20:
            print("      ... %d more omitted" % (len(ps_hits) - 20))
        total += len(ps_hits)
    elif len(PROSELL_MARKERS) >= PROSELL_FLOOR:
        print("  [PASS] prosell: 0 hits (%d file(s))" % len(files))

    # 9) 格式 × 维度适用矩阵 与 决策 ≤3 声明（辛-3 / 决策不过三）
    print("")
    print("9) Format x dimension matrix & decision<=3 declarations:")
    mtx_issues = check_matrix_declaration(root)
    if mtx_issues:
        print("  [FAIL] matrix-declaration: %d issue(s)" % len(mtx_issues))
        for it in mtx_issues[:20]:
            print("      %s" % it)
        total += len(mtx_issues)
    else:
        print("  [PASS] matrix-declaration: 矩阵 7 列齐全，Excel 两列标不适用；三处决策 <=3 一致")

    # 9b) 出包排除件登记核对（按「读者」分类：不参与 Agent 执行的件不该进安装包）
    print("")
    print("9b) Publish-exclude reconciliation (self-declared internal files):")
    id_issues = check_internal_declared(root)
    if id_issues:
        print("  [FAIL] internal-declared: %d issue(s)" % len(id_issues))
        for rel, why in id_issues[:20]:
            print("      %s —— %s" % (rel, why))
        total += len(id_issues)
    else:
        print("  [PASS] internal-declared: 0 issue(s)（自我声明的内部件均已登记出包排除表，"
              "共 %d 项）" % len(PUBLISH_EXCLUDE))

    # 10) 脚本清单对账（反向对账：不留未接线的脚本）
    print("")
    print("10) Script wiring audit (--self-test or tests/exempt.json):")
    wired, used, unwired, expired = check_script_wiring(root)
    if unwired:
        print("  [FAIL] wiring: %d script(s) neither wired nor exempt%s"
              % (len(unwired), (" (%d expired)" % len(expired)) if expired else ""))
        for fn, why in unwired[:20]:
            print("      scripts/%s  | %s" % (fn, why))
        total += len(unwired)
    else:
        print("  [PASS] wiring: %d wired / %d permanent-exempt" % (len(wired), len(used)))
    if used:
        print("  [WARN] exempt ledger: %d entr(ies) — review tests/exempt.json" % len(used))
        for fn, e in used[:20]:
            if str(e.get("expires_in", "") or "").strip():
                tag = "expires_in %s" % e.get("expires_in")
            else:
                tag = "permanent"
            print("      scripts/%s  (since %s, %s, reason: %s)"
                  % (fn, e.get("since"), tag, str(e.get("reason", ""))[:60]))

    # 11) 自带回归脚本实跑（--run-selftests 时启用）+ 自测后残留复查
    if args.run_selftests:
        sd = os.path.join(root, "scripts")
        if os.path.isdir(sd):
            print("")
            print("11) 自带回归脚本实跑（--run-selftests）:")
            pre = snapshot_pkg(root)
            n, ok, blocked = run_selftests(sd)
            post = snapshot_pkg(root)
            added, changed, removed = diff_snapshots(pre, post)
            print("11b) 自测后残留复查（跑完立刻比对包内快照）:")
            if added or changed or removed:
                print("  [FAIL] selftest-residue: 新增 %d / 改动 %d / 减少 %d"
                      % (len(added), len(changed), len(removed)))
                for rel in (added + changed + removed)[:20]:
                    print("      %s" % rel)
                total += len(added) + len(changed) + len(removed)
            else:
                print("  [PASS] selftest-residue: 跑完 %d 个自测，包内 %d 个文件 0 变化"
                      % (n, len(post)))
            if n == 0:
                print("  [WARN] scripts/ 未发现任何带 --self-test 的脚本")
            if blocked:
                print("  [WARN] %d 个脚本因环境不支持子进程而 SKIP" % blocked)
            if not ok:
                total += 1

    print("")
    if total:
        print("VERDICT: FAIL (%d to fix) -> exit 1" % total)
        sys.exit(1)
    print("VERDICT: PASS (package clean) -> exit 0")


if __name__ == "__main__":
    main()
