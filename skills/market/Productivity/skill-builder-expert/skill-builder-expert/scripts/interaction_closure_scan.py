#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
interaction_closure_scan.py — 对话闭环出厂扫描（IC1–IC14 机检，fail-closed）
实现 REF-STD-032 第八节。扫描目标技能Skill的交互文本，核对话闭环必备件齐备性。

平台前提：双向隔离——创作者与终端用户互不可达，全部交互问题只能靠
产物内置话术与数字路由自闭环。产物交互文本必备件缺失 = FAIL。

必备件（对应 IC1–IC6、IC9）＋ 违例扫描（IC7 预期承诺/权属宣称，运行时拼接词表）＋ 数字号段唯一（IC8，仅扫菜单交互模板册）＋ 落款与接住承接落位（IC9，仅扫菜单交互模板册）＋ 直达表规矩查（IC10，仅扫直达表 REF-DAT-057）：
  IC1 开场白：身份自述 / 数字序号菜单 / 【帮助】引导 / 首响接住承接
  IC2 数字路由：存在数字序号菜单；字母口令菜单（回 A/B/C 类）判 FAIL
  IC3 意图模糊兜底
  IC4 求助入口 + 自查三步（一字不差 / 多余文字 / 会话入口）+ 无人工通道声明
  IC5 输入异常兜底 / 降级重试 / 高危拦截 / 重置
  IC6 收尾返回菜单（开启新任务 / 结束会话）
  IC9 落款收口：统一落款随尾部片段挂载、接住承接定稿句在册（模板册落位校验）
  IC10 直达表规矩查：条目数恰 46（DA-01～DA-46）、每条目四字段齐且挂载标记非空、答案指针在位（指针式单真相）、总则锚点在位

禁止表述（引导联系外部支持）：请联系客服 / 联系人工客服 / 转人工 /
提交工单 / 拨打客服 / 客服热线。
注意：「无人工客服」类平台隔离客观声明属必备件，不算违规。

用法：python interaction_closure_scan.py <目标目录> [--self-test]
退出码：0 = PASS，1 = FAIL，2 = 用法 / 输入错误（fail-closed）
"""

import re
import sys
from pathlib import Path

# 必备件清单：名称 → 正则（对全部扫描文本做存在性判定）
REQUIRED = [
    ("IC1 身份自述", r"(我是|欢迎使用|您好，我是|你好，我是)"),
    ("IC1 数字序号菜单", r"\[\s*[0-9]\s*\]"),
    ("IC1 帮助引导", r"(【帮助】|回复.{0,8}帮助)"),
    ("IC3 意图模糊兜底", r"(意图模糊|没有完全理解|暂时没有.{0,8}理解|无法判定|没看懂|没读出来)"),
    ("IC5 输入异常兜底", r"(输入非法|输入异常|无法识别|格式不支持|文件损坏|内容异常|检测到传入的内容)"),
    ("IC5 降级重试", r"(降级|内部异常|重试)"),
    ("IC5 高危拦截", r"(无法继续执行|任务终止|不支持该类|高危)"),
    ("IC4 自查三步", r"(一字不差|多余文字|会话入口)"),
    ("IC5 重置", r"(重置|重新开始|从头再来)"),
    ("IC6 收尾返回", r"(开启新|结束当前会话|结束会话|返回主菜单|回到主菜单)"),
    ("IC4 无人工通道声明", r"(无人工|全程自助|不设任何人工)"),
    ("IC1 接住承接", r"(收到.{0,6}发来的内容|已经接收.{0,6}提供的资料)"),
    ("IC9 落款收口", r"(?m)^—— ?\S{2,24}\s*$"),
]

# 字母口令菜单（禁用）：形如「回 A / B」「回复 A｜B｜C」的字母选择引导
LETTER_MENU = re.compile(r"[回选]\s*复?\s*[A-Za-z]\s*[/／|｜、]\s*[A-Za-z]")

# 禁止表述（引导联系外部支持）
FORBIDDEN = [
    "请联系客服", "联系人工客服", "联系客服", "转人工",
    "提交工单", "拨打客服", "客服热线",
]

# IC7 预期承诺/权属宣称违例词（运行时拼接，源文件不留完整字面防自咬）
_IC7_PARTS = [
    ["帮你做到", "高分"], ["帮你拿到", "高分"], ["更容易被搜", "到"],
    ["保证曝光"], ["保证检索排名"], ["曝光更好"],
    ["自", "研"], ["自创一套评测"],
    ["雷达", "图"], ["体系", "代号"],
    ["做得很", "差"], ["严重错", "误"], ["设计不合", "理"],
    ["存在重大缺", "陷"], ["你这个技能", "不行"], ["一定要整", "改"],
]
EXPECTATION_VIOLATIONS = ["".join(parts) for parts in _IC7_PARTS]

# 扫描范围与上限
TEXT_EXTS = {".md", ".txt"}
SKIP_DIRS = {"logs", "node_modules", ".git", "__pycache__"}
MAX_FILE_BYTES = 2 * 1024 * 1024


def check_text(text):
    """对一段交互文本做全套核验，返回 fails 列表（可复用于自测）。"""
    fails = []
    for name, pattern in REQUIRED:
        if not re.search(pattern, text):
            fails.append("必备件缺失: %s" % name)
    if LETTER_MENU.search(text):
        fails.append("命中字母口令菜单（数字铁规：固定入口一律数字序号）")
    for term in FORBIDDEN:
        if term in text:
            fails.append("命中引导外部支持表述: %s" % term)
    for term in EXPECTATION_VIOLATIONS:
        if term in text:
            fails.append("命中预期承诺/权属宣称表述(IC7): %s" % term)
    return fails


def collect_files(root):
    """收集目标根目录下全部待扫文本文件；无文件返回空列表。"""
    found = []
    if root.is_file():
        return [root] if root.suffix in TEXT_EXTS else []
    for p in sorted(root.rglob("*")):
        if not p.is_file() or p.suffix not in TEXT_EXTS:
            continue
        if any(part in SKIP_DIRS for part in p.parts):
            continue
        if p.stat().st_size > MAX_FILE_BYTES:
            continue
        found.append(p)
    return found


# ---------- IC8 数字号段唯一性（仅对模板册 REF-TMP-003 生效） ----------
import re as _re
_OPT_LINE = _re.compile(r"^\s*\[(\d)\]", _re.M)
_ENTRY_OK_TITLES = ("欢迎启动菜单", "链路收尾", "意图模糊", "统一求助导航", "连续未成功", "空白 / 乱码", "空白/乱码")


def check_number_segments(tmp_text):
    """模板册按 '## ' 分块；每块提取行首 [N] 选项定义，校验全链路数字唯一含义：
    [0] 全局同义；[1]-[4] 仅业务入口屏；[5]-[9] 仅配置确认屏；其余屏面禁止数字选项。"""
    fails = []
    for b in _re.split(r"^## ", tmp_text, flags=_re.M):
        if not b.strip():
            continue
        title = b.split("\n", 1)[0].strip()
        nums = set(_OPT_LINE.findall(b))
        nums.discard("0")
        if not nums:
            continue
        if ("配置确认" in title) or ("配置汇总" in title):
            bad = sorted(n for n in nums if n not in "56789")
            if bad:
                fails.append("IC8 配置屏出现非专用号段 [%s]: %s" % ("".join(bad), title[:40]))
        elif any(k in title for k in _ENTRY_OK_TITLES):
            bad = sorted(n for n in nums if n not in "1234")
            if bad:
                fails.append("IC8 业务入口屏出现非入口号段 [%s]: %s" % ("".join(bad), title[:40]))
        else:
            fails.append("IC8 非菜单屏出现数字选项 [%s]（应改文本口令）: %s" % ("".join(sorted(nums)), title[:40]))
    return fails


# ---------- IC9 落款收口与接住承接落位（仅对模板册 REF-TMP-003 生效） ----------
SIGNOFF = "—— Skill技能搭建专家"
CATCH_PHRASE = "收到您发来的内容啦"
_FRAG_HEAD = "【公共兜底尾部片段 REF-TMP-TAIL-001】"


def check_signoff(tmp_text):
    """模板册落位校验：①接住承接定稿句在册；②统一落款位于尾部片段块内且唯一（防双落款）。"""
    fails = []
    if CATCH_PHRASE not in tmp_text:
        fails.append("IC9 接住承接定稿句缺失（模板册）")
    frag = None
    for b in _re.split(r"^## ", tmp_text, flags=_re.M):
        if b.startswith(_FRAG_HEAD):
            frag = b
            break
    if frag is None:
        fails.append("IC9 尾部片段块缺失（无法校验落款落位）")
        return fails
    cnt = len(_re.findall(r"(?m)^—— Skill技能搭建专家\s*$", frag))
    if cnt == 0:
        fails.append("IC9 落款件缺失（尾部片段末行）")
    elif cnt > 1:
        fails.append("IC9 落款件重复（片段块内 %d 处，防双落款）" % cnt)
    return fails


# ---------- IC10 直达表规矩查（仅对直达表 REF-DAT-057 生效） ----------
_DAT_FIELDS = ("信号族", "答案指针", "挂载标记", "回落条件")
_DAT_ANCHORS = (
    "命中三条件", "回落四类", "指针式", "逐字同文",
    "尾部片段挂载、统一落款收口、红线词纪律",
)


def check_direct_answer_table(dat_text):
    """直达表落位校验（快路径不丢规矩）：
    ①条目数恰 46（DA-01～DA-46 全集合在位）；②每条目四字段齐；③挂载标记字段非空；
    ④每条目答案指针在位（指向模板册／内联区／FAQ）；⑤总则锚点在位。"""
    fails = []
    ids = _re.findall(r"(?m)^### (DA-\d{2})", dat_text)
    expect = {f"DA-0{i}" for i in range(1, 10)} | {f"DA-{i}" for i in range(10, 47)}
    got = set(ids)
    if len(ids) != 46 or "DA-01" not in got or not expect <= got:
        miss = sorted(expect - got)
        fails.append("IC10 条目数异常（实测 %d 条，须 DA-01～DA-46 恰 46 条；缺 %s）" % (len(ids), "、".join(miss) or "无"))
    for b in _re.split(r"(?m)^### ", dat_text):
        m = _re.match(r"(DA-\d{2})", b)
        if not m:
            continue
        miss_f = [f for f in _DAT_FIELDS if not _re.search(r"^\|\s*%s\s*\|" % f, b, _re.M)]
        if miss_f:
            fails.append("IC10 %s 缺字段: %s" % (m.group(1), "、".join(miss_f)))
        mk = _re.search(r"^\|\s*挂载标记\s*\|\s*([^|\r\n]*?)\s*\|", b, _re.M)
        if not mk or not mk.group(1).strip():
            fails.append("IC10 %s 挂载标记字段为空（快路径不丢规矩）" % m.group(1))
        if "REF-TMP-003#【" not in b and "SKILL.md §1.1-A" not in b and "FAQ.md" not in b:
            fails.append("IC10 %s 无有效答案指针（指针式单真相）" % m.group(1))
    for k in _DAT_ANCHORS:
        if k not in dat_text:
            fails.append("IC10 总则锚点缺失: %s" % k)
    return fails


# ---------- IC11–IC14 产物自守纪律闸（教训固化 2026-11-10：屏尾制/锚定词/标点健康/回复词落点） ----------
# 设计口径：「」引用段豁免（规则定义引用禁词属合法语境，同 IC7 词表拼装防自咬机理）；
# IC11 落款行豁免（IC9 落款随尾部片段必至，行动行后跟落款属合规）。
ANCHOR_TERMS = ["验收通过", "审核没问题"]
DBL_PUNCT = re.compile(r"(。。|，，|！！|？？|、、)")
_QSPAN = re.compile(r"「[^」]*」")
_SIGNOFF_LINE = re.compile(r"^—— ?\S{2,24}\s*$")
_MOUNT_MARK = re.compile(r"^\{\{[^}]+\}\}$")


def _strip_quoted(text):
    """剥离「」引用段——规则定义引用禁词/瑕疵样例属合法语境。"""
    return _QSPAN.sub("", text)


def check_anchor_words(text):
    """IC12 锚定表述零存在：最终决策权在用户，禁「验收通过」「审核没问题」类锚定（引用段豁免）。"""
    bare = _strip_quoted(text)
    return [w for w in ANCHOR_TERMS if w in bare]


def check_double_punct(text):
    """IC13 标点健康：重复标点（拼接类瑕疵，如文案拼装引入的双句号）零存在（引用段豁免）。"""
    return [m.group(0) for m in DBL_PUNCT.finditer(_strip_quoted(text))]


def check_screen_tail(text):
    """IC11 行动行屏尾：围栏块内最后一个「回复＋【入口名】／「口令」」指令行之后，仅允许空行／引用行（>）／
    挂载标记／统一落款行；其余正文行即 FAIL——行动指令藏中间＝用户看不到＝卡死。
    两形态都识别（137 铁则：入口名【】／文本口令「」），防止口令类行动行逃出屏尾检查。"""
    fails = []
    for bm in re.finditer(r"```[^\n]*\n(.*?)```", text, re.S):
        blines = bm.group(1).splitlines()
        act_idx = None
        for i, l in enumerate(blines):
            if re.search(r"回复\s*[*＊*]*(?:[【「]|数字\s*(?:`0`|\*\*【0】\*\*))", l) and not l.strip().startswith(">"):
                act_idx = i
        if act_idx is None:
            continue
        for l in blines[act_idx + 1:]:
            s = l.strip()
            if not s or s.startswith(">") or _MOUNT_MARK.fullmatch(s) or _SIGNOFF_LINE.match(s):
                continue
            fails.append("行动行后有正文行(行动指令须屏尾): %s" % s[:40])
            break
    return fails


def check_keyword_landing(combined):
    """IC14 回复词映射：屏内每个指令关键词须在全文出现≥2处【词】（行动行之外另有菜单/说明落点）——
    配了词没反应＝用户卡死。关键词采集自剥引文本（规则定义引用豁免），计数用全文。"""
    bare = _strip_quoted(combined)
    kws = set(re.findall(r"回复\s*[*＊*]*【([^】]{1,14})】", bare))
    kws |= set(re.findall(r"回复\s*[*＊*]*「([^」]{1,14})」", bare))
    fails = []
    for k in sorted(kws):
        if combined.count("【%s】" % k) + combined.count("「%s」" % k) < 2:
            fails.append("回复词无落点: 【%s】全文仅1处出现（配词无反应即卡死）" % k)
    return fails


def scan_target(root):
    """扫描目标目录，返回 (fails, scanned_count)。"""
    files = collect_files(root)
    if not files:
        return ["未找到任何可扫描文本（fail-closed）"], 0
    fails = []
    combined = []
    for p in files:
        try:
            text = p.read_text(encoding="utf-8", errors="ignore")
        except OSError as e:
            fails.append("文件不可读: %s (%s)" % (p.name, e))
            continue
        # 唯一豁免区：REF-BSE-047 标记区（用户下发定稿逐字有效，fail-closed——双锚点不齐照扫全文）。
        # 定稿原文含「自研」等权属语境字面（工程规则主语），属用户定稿字面，不属产物对外宣称；
        # 标记区外文本照扫不豁免。注意：违例扫描仅对剥离后文本跑，必备件检查不受影响。
        scan_text_p = text
        if "REF-BSE-047" in p.name:
            _bs, _be = "<!-- BASE-BLOCK-START -->", "<!-- BASE-BLOCK-END -->"
            if _bs in text and _be in text:
                scan_text_p = text.split(_bs, 1)[0] + text.split(_be, 1)[1]
        combined.append(scan_text_p)
        if "REF-TMP-003" in p.name:
            fails.extend(check_number_segments(text))
            fails.extend(check_signoff(text))
        if "REF-DAT-057" in p.name:
            fails.extend(check_direct_answer_table(text))
        for term in FORBIDDEN:
            if term in scan_text_p:
                fails.append("禁止表述 [%s] 出现于: %s" % (term, p.name))
        for term in EXPECTATION_VIOLATIONS:
            if term in scan_text_p:
                fails.append("预期承诺/权属宣称 [%s] 出现于: %s" % (term, p.name))
        for w in check_anchor_words(scan_text_p):
            fails.append("IC12 锚定表述 [%s] 出现于: %s" % (w, p.name))
        for d in check_double_punct(scan_text_p):
            fails.append("IC13 重复标点 [%s] 出现于: %s" % (d, p.name))
        for f in check_screen_tail(text):
            fails.append("IC11 %s（%s）" % (f, p.name))
    if combined:
        corpus = "\n".join(combined)
        fails.extend(check_text(corpus))
        fails.extend(check_keyword_landing(corpus))
    return fails, len(files)


# ---------- 自测（阳/阴用例：证明本引擎自己会红） ----------

_POSITIVE = """
您好，我是 交付示例技能。欢迎使用本工具。
请回复数字选择：[1] 开始任务 [2] 查看说明 [0] 结束当前会话。
找不到功能？直接回复【帮助】。
【意图模糊兜底】暂时没有完全理解你的需求，请回复序号。
【输入异常】检测到传入的内容存在异常，请重新提供。
引擎内部异常时可重试（降级）；高危请求无法继续执行，任务终止。
回复【帮助】可看自查三步：数字是否一字不差、有无多余文字、会话入口是否正确。
多次未成功可重置，重新开始；完成后可开启新任务或结束会话。
收到你发来的内容，我已经接收到你提供的资料。
本工具全程自助，无人工客服通道。

—— 交付示例技能
"""

_NEGATIVE = """
你好，请回复 A / B 选择模式。
有问题请联系客服提交工单。
"""

# IC8 自测样例
_IC8_POS = "## 【欢迎启动菜单】\n[1] 代建\n[2] 答疑\n[3] 调整\n[4] 评测\n## 【配置确认 · 第一步：部署形态】\n[5] 轻量\n[6] API\n## 【答疑入口导航模板】\n[10] 开发咨询\n[13] 常见问题目录\n## 【调整范围确认模板】\n[14] 确认执行\n[15] 补充意见\n## 【评测报告后处置选择】\n[16] 留存报告\n[17] 转入调整\n[18] 转入重构\n"
_IC8_NEG = "## 【疲惫暂停共情模板】\n[1] 暂停\n[2] 继续\n## 【答疑入口导航模板】\n[5] 错号\n## 【评测报告后处置选择】\n[1] 错号\n"

# IC9 自测样例（模板册落位）
_IC9_HEAD = "## 【公共兜底尾部片段 REF-TMP-TAIL-001】\n```text\n💡小提示：\n随时回复【菜单】。\n"
_IC9_TAIL = "```\n"
_IC9_CATCH = "## 【首响接住承接件】\n收到您发来的内容啦，我已经接收到您提供的资料。\n"
_IC9_POS = _IC9_HEAD + "—— Skill技能搭建专家\n" + _IC9_TAIL + _IC9_CATCH
_IC9_NEG_NOSIGN = _IC9_HEAD + _IC9_TAIL + _IC9_CATCH
_IC9_NEG_DUP = _IC9_HEAD + "—— Skill技能搭建专家\n—— Skill技能搭建专家\n" + _IC9_TAIL + _IC9_CATCH
_IC9_NEG_NOCATCH = _IC9_HEAD + "—— Skill技能搭建专家\n" + _IC9_TAIL

# IC10 自测样例（直达表落位）
_IC10_RULES = (
    "> 命中三条件与回落四类见总则；指针式＋DA-10 内联副本与 FAQ.md 逐字同文，"
    "三件不可免——尾部片段挂载、统一落款收口、红线词纪律。\n"
)


def _dat_entry(idx):
    return (
        "### DA-%02d ｜示例条目\n"
        "| 字段 | 内容 |\n|---|---|\n"
        "| 信号族 | 示例信号 |\n"
        "| 答案指针 | REF-TMP-003#【示例模板】 |\n"
        "| 挂载标记 | 尾部片段照挂 |\n"
        "| 回落条件 | 示例回落 |\n" % idx
    )


_IC10_POS = _IC10_RULES + "".join(_dat_entry(i) for i in range(1, 44))
_IC10_NEG_EMPTY_MARK = _IC10_POS.replace(
    "| 挂载标记 | 尾部片段照挂 |", "| 挂载标记 |  |", 1)
_IC10_NEG_MISS_FIELD = _IC10_POS.replace("\n| 回落条件 | 示例回落 |", "", 1)
_IC10_NEG_NINE = _IC10_POS.replace(_dat_entry(43), "")


def self_test():
    results = []
    pos = check_text(_POSITIVE)
    results.append(("阳例·全必备件应 PASS", not pos, "; ".join(pos[:3])))
    neg = check_text(_NEGATIVE)
    ok_neg = bool(neg) and any("字母口令" in x for x in neg) and any("联系客服" in x or "外部支持" in x for x in neg)
    results.append(("阴例·字母口令+外部支持应 FAIL", ok_neg, "; ".join(neg[:3])))
    neg2 = check_text(_POSITIVE.replace("【帮助】", ""))
    results.append(("阴例②·删帮助引导应 FAIL", bool(neg2) and any("帮助引导" in x for x in neg2), "; ".join(neg2[:3])))
    neg3 = check_text("我们对技能开展质检评测分析，排查缺陷并输出优化方案。" + "承诺帮你做到" + "高分，保证" + "曝光更好。")
    ok3 = any("IC7" in x for x in neg3)
    results.append(("阴例③·预期承诺/权属宣称应 FAIL(IC7)", ok3, "; ".join(neg3[:3])))
    ok_pos8 = check_number_segments(_IC8_POS) == []
    results.append(("阳例·号段合规应 PASS(IC8)", ok_pos8, "; ".join(check_number_segments(_IC8_POS)[:2])))
    neg8 = check_number_segments(_IC8_NEG)
    ok8 = bool(neg8) and any("IC8" in x for x in neg8)
    results.append(("阴例④·非菜单屏数字选项应 FAIL(IC8)", ok8, "; ".join(neg8[:3])))
    neg9a = check_text(_POSITIVE.replace("—— 交付示例技能\n", ""))
    results.append(("阴例⑤·删落款应 FAIL(IC9)", bool(neg9a) and any("落款" in x for x in neg9a), "; ".join(neg9a[:3])))
    ok9pos = check_signoff(_IC9_POS) == []
    results.append(("阳例·落款与接住承接落位应 PASS(IC9)", ok9pos, "; ".join(check_signoff(_IC9_POS)[:2])))
    neg9b = check_signoff(_IC9_NEG_NOSIGN)
    results.append(("阴例⑥·片段缺落款应 FAIL(IC9)", bool(neg9b) and any("落款件缺失" in x for x in neg9b), "; ".join(neg9b[:3])))
    neg9c = check_signoff(_IC9_NEG_DUP)
    results.append(("阴例⑦·片段双落款应 FAIL(IC9)", bool(neg9c) and any("落款件重复" in x for x in neg9c), "; ".join(neg9c[:3])))
    neg9d = check_signoff(_IC9_NEG_NOCATCH)
    results.append(("阴例⑧·接住承接句缺失应 FAIL(IC9)", bool(neg9d) and any("接住承接" in x for x in neg9d), "; ".join(neg9d[:3])))
    ok10pos = check_direct_answer_table(_IC10_POS) == []
    results.append(("阳例·直达表46条目落位应 PASS(IC10)", ok10pos, "; ".join(check_direct_answer_table(_IC10_POS)[:3])))
    neg10a = check_direct_answer_table(_IC10_NEG_EMPTY_MARK)
    results.append(("阴例⑨·挂载标记空应 FAIL(IC10)", bool(neg10a) and any("挂载标记字段为空" in x for x in neg10a), "; ".join(neg10a[:3])))
    neg10b = check_direct_answer_table(_IC10_NEG_MISS_FIELD)
    results.append(("阴例⑩·缺回落字段应 FAIL(IC10)", bool(neg10b) and any("缺字段" in x for x in neg10b), "; ".join(neg10b[:3])))
    neg10c = check_direct_answer_table(_IC10_NEG_NINE)
    results.append(("阴例⑪·条目缺号应 FAIL(IC10)", bool(neg10c) and any("条目数异常" in x for x in neg10c), "; ".join(neg10c[:3])))
    # IC11-IC14 产物自守纪律闸自测
    _IC11_NEG = "```text\n请选择：[1] 开始 [2] 说明。\n👉 回复【确认】继续。\n备注：本屏为示例屏。\n```"
    neg11 = check_screen_tail(_IC11_NEG)
    results.append(("阴例⑫·行动行后有正文行应 FAIL(IC11)", bool(neg11) and any("屏尾" in x for x in neg11), "; ".join(neg11[:2])))
    _IC11_POS = "```text\n请选择：[1] 开始 [2] 说明。\n👉 回复【确认】继续。\n\n—— 交付示例技能\n```"
    r11p = check_screen_tail(_IC11_POS)
    results.append(("阳例·行动行屏尾＋落款应 PASS(IC11)", r11p == [], "; ".join(r11p[:2])))
    neg12 = check_anchor_words("本步骤验收通过即可交付。")
    results.append(("阴例⑬·锚定表述裸露应 FAIL(IC12)", bool(neg12), "; ".join(neg12[:2])))
    ok12 = check_anchor_words("交付收尾禁用「验收通过」类锚定表述。") == []
    results.append(("阳例·锚定词引用形态应 PASS(IC12)", ok12, ""))
    neg13 = check_double_punct("素材已收到。。请继续。")
    results.append(("阴例⑭·双句号应 FAIL(IC13)", bool(neg13) and neg13[0] == "。。", "; ".join(neg13[:2])))
    ok13 = check_double_punct("素材已收到。请继续。（瑕疵登记：「。。」样例存档）") == []
    results.append(("阳例·引用形态重复标点豁免应 PASS(IC13)", ok13, ""))
    _IC14_NEG = "👉 回复【续费】继续使用。\n\n—— 交付示例技能\n"
    neg14 = check_keyword_landing(_IC14_NEG)
    results.append(("阴例⑮·回复词无落点应 FAIL(IC14)", bool(neg14) and any("续费" in x for x in neg14), "; ".join(neg14[:2])))
    _IC14_POS = "[1] 续费操作说明：回复【续费】进入续费流程。\n👉 回复【续费】继续使用。\n"
    r14p = check_keyword_landing(_IC14_POS)
    results.append(("阳例·回复词有落点应 PASS(IC14)", r14p == [], "; ".join(r14p[:2])))
    all_ok = True
    for name, ok, detail in results:
        print(("PASS " if ok else "FAIL ") + name + ((" — " + detail) if not ok else ""))
        all_ok = all_ok and ok
    return 0 if all_ok else 1


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if "--self-test" in sys.argv:
        return self_test()
    if not args:
        print("用法: python interaction_closure_scan.py <目标目录或文件> [--self-test]")
        return 2
    root = Path(args[0]).expanduser().resolve()
    if not root.exists():
        print("路径不存在: %s" % root)
        return 2
    fails, count = scan_target(root)
    if fails:
        print("FAIL 对话闭环出厂扫描（IC1–IC14）— %d 项问题：" % len(fails))
        for f in fails:
            print("  - %s" % f)
        return 1
    print("PASS 对话闭环出厂扫描（IC1–IC14）：%d 个文本文件，必备件齐备、零字母口令、零外部支持表述、零预期承诺与权属宣称、数字号段唯一、落款与接住承接落位合规、直达表规矩查通过" % count)
    return 0


if __name__ == "__main__":
    sys.exit(main())
