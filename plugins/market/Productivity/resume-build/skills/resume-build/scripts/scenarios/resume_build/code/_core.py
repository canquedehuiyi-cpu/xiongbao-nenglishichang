"""_core.py —— 简历制作的验据内核（纯函数，零 IO；验据规则与阈值只住本文件顶部）

本件的判定权体现：**素材里没有的经历，不进终稿。**
- 锚点（日期/数字）必须全部在素材中找到（含 %↔小数/万·亿换算变体）——一条不符即 FLAG；
- 实义词覆盖率 ≥ TOKEN_COVERAGE 才放行——低于即 FLAG；
- 引擎不得「放行一条看起来合理的」（硬约束）。

五态口径：
  PASS      该条经历锚点全中且覆盖率达标 → 进终稿,带素材定位
  WARNING   时间线断档 > GAP_MONTHS 或区间重叠（逐条点名,人工裁决）
  MISSING   JD 硬性要求在终稿找不到 → 「未提及」（不判"不满足"）
  CONFLICT  不使用（本场景无双侧对照）
  UNKNOWN   草稿解析不出结构（节全认不出）→ 整体转人工,不硬判
"""

from __future__ import annotations

import re
from typing import Any

# ── 验据阈值（命名常量；改这里 = 改产品口径，须过 INTENT §2 登记）──
# 取值依据：
#   TOKEN_COVERAGE = 0.7：实义词七成能在素材找到即放行——同义改写(主导/牵头)不该
#     打回,但三成以上实词无据大概率是编的。锚点(日期/数字)不享受折扣,全中才行。
#   GAP_MONTHS = 6：简历时间线断档超过 6 个月是 HR 常见追问点;更短的职业间隙
#     属正常流动,不报。
#   停用词表：通用动词/连接词不构成事实主张,不计入覆盖率分母。
TOKEN_COVERAGE = 0.7
GAP_MONTHS = 6
_ROUND = 6

STOPWORDS = {
    "负责", "主导", "参与", "完成", "实现", "设计", "开发", "优化", "提升", "推动",
    "支持", "包括", "以及", "具有", "熟悉", "掌握", "精通", "了解", "善于", "沟通",
    "协作", "团队", "能力", "经验", "工作", "项目", "系统", "平台", "相关", "各类",
    "多种", "多个", "主要", "核心", "重点", "持续", "深入", "扎实", "良好", "优秀",
    "认真", "踏实", "学习", "能力强", "牵头", "统筹", "搭建", "排查", "修复", "编写",
    "组织", "协调",
}

_NUM_ANCHOR = re.compile(r"\d+(?:\.\d+)?\s*[%万亿]?")
_DATE_RANGE = re.compile(
    r"((?:19|20)\d{2})\s*[./年]\s*(\d{1,2})\s*[-–—~至到]\s*((?:19|20)\d{2}\s*[./年]?\s*(?:\d{1,2})?|至今)"
)
_UNIT_SCALE = {"万": 1e4, "亿": 1e8}

# ── 中文数字归一（0.2.0，误打回治理）─────────────────────────────────────
# 素材常写「五十万/四成/百分之三十」，草稿常写「50万/40%/30%」——不归一必然误打回。
# 只做确定性转换：数字字符按位值解析，不带任何语义猜测。
_CN_DIGIT = {"零": 0, "〇": 0, "一": 1, "二": 2, "两": 2, "三": 3, "四": 4,
             "五": 5, "六": 6, "七": 7, "八": 8, "九": 9}
_CN_UNIT = {"十": 10, "百": 100, "千": 1000}
_CN_BIG = {"万": 10**4, "亿": 10**8}
_CN_RUN = re.compile(r"[零〇一二两三四五六七八九十百千万亿]+")
_CN_SOLO_NEXT = "万个年人位次份项张篇家笔倍"


def _parse_cn_int(s: str) -> int:
    total = section = 0
    digit: int | None = None
    for ch in s:
        if ch in _CN_DIGIT:
            digit = _CN_DIGIT[ch]
        elif ch in _CN_UNIT:
            section += (digit or 1) * _CN_UNIT[ch]
            digit = None
        elif ch in _CN_BIG:
            total = (total + section + (digit or 0)) * _CN_BIG[ch]
            section, digit = 0, None
    return total + section + (digit or 0)


def _cn2num(text: str) -> str:
    """百分之X→X%、X成→X0%、中文数字串→阿拉伯(保留万亿后缀)。
    防误伤：单字数字只在后跟量纲字(万个年人…)时才转；「第」后的不转(第一/第二是序数词)。"""

    def _num_repl(m: re.Match) -> str:
        s = m.group(0)
        core, suffix = s, ""
        if s[-1] in _CN_BIG:
            core, suffix = s[:-1], s[-1]
        val = _parse_cn_int(core)
        return f"{val}{suffix}" if val else s

    text = re.sub(r"百分之([零〇一二两三四五六七八九十百]+)",
                  lambda m: f"{_parse_cn_int(m.group(1))}%", text)
    text = re.sub(r"([零〇一二两三四五六七八九十]+)成",
                  lambda m: f"{_parse_cn_int(m.group(1)) * 10}%", text)

    def _run_repl(m: re.Match) -> str:
        s = m.group(0)
        start, end = m.span()
        before = text[start - 1] if start > 0 else ""
        if len(s) == 1:
            if before == "第":
                return s
            after = text[end] if end < len(text) else ""
            if after not in _CN_SOLO_NEXT:
                return s
        return _num_repl(m)

    return _CN_RUN.sub(_run_repl, text)


def normalize_for_match(text: str) -> str:
    """匹配基准态:中文数字归一 + 去所有空白(中文子串匹配不受排版影响)。"""
    return re.sub(r"\s+", "", _cn2num(text))


def _content_units(line: str) -> list[str]:
    """实义计量单元:中文按二字组(bigram)、拉丁按整词;停用词先作分隔剔除。

    中文没有空格,整句 token 化会让任何同义改写必然打回;二字组粒度下
    「订单系统开发」与素材「负责订单系统」共享订单/单系/系统三个组,
    改写不误伤,而整句编造(千万级日活架构)的组几乎全缺,拦得住。
    """
    s = line
    for w in STOPWORDS:
        s = s.replace(w, " ")
    units: list[str] = []
    for run in re.findall(r"[一-龥]+", s):
        if len(run) >= 2:
            units.extend(run[i:i + 2] for i in range(len(run) - 1))
        else:
            units.append(run)
    units.extend(re.findall(r"[A-Za-z][A-Za-z0-9+.#-]{1,}", s))
    return units


def extract_anchors(line: str) -> list[str]:
    """锚点:日期区间原文 + 数字(含单位)。这些必须逐字(或换算)在素材出现。"""
    out: list[str] = []
    for m in _DATE_RANGE.finditer(line):
        out.append(re.sub(r"\s+", "", m.group(0)))
    for m in _NUM_ANCHOR.finditer(line):
        out.append(re.sub(r"\s+", "", m.group(0)))
    return out


def _num_variants(raw: str) -> set[str]:
    """数字锚点的等值写法变体:45% ↔ 0.45;300万 ↔ 3000000。"""
    s = raw.strip()
    m = re.match(r"(\d+(?:\.\d+)?)\s*(.*)$", s)
    if not m:
        return {s}
    val = float(m.group(1))
    unit = m.group(2).strip()
    outs = {s, m.group(1)}
    if unit == "%":
        dec = round(val / 100.0, _ROUND)
        outs.update({f"{dec:g}", f"{dec:g}%"})
    if unit in _UNIT_SCALE:
        full = val * _UNIT_SCALE[unit]
        outs.update({f"{full:.0f}", f"{full:g}"})
    return {re.sub(r"\s+", "", x) for x in outs}


def _date_variants(anchor: str) -> set[str]:
    """日期锚点双写法变体:2019.07-2022.03 ↔ 2019年7月-2022年3月(去前导零)。"""
    m = _DATE_RANGE.search(anchor)
    if not m:
        return set()
    sy, sm = int(m.group(1)), int(m.group(2))
    end = re.sub(r"\s+", "", m.group(3))
    if end == "至今":
        variants = {f"{sy}.{sm:02d}-至今", f"{sy}.{sm}-至今", f"{sy}年{sm}月-至今"}
    else:
        parts = re.findall(r"\d+", end)
        ey, em = int(parts[0]), int(parts[1]) if len(parts) > 1 else 1
        variants = {
            f"{sy}.{sm:02d}-{ey}.{em:02d}",
            f"{sy}.{sm}-{ey}.{em}",
            f"{sy}年{sm}月-{ey}年{em}月",
        }
    return {re.sub(r"\s+", "", v) for v in variants}


def anchor_in_material(anchor: str, material_norm: str) -> bool:
    if anchor in material_norm:
        return True
    if any(v in material_norm for v in _date_variants(anchor)):
        return True
    return any(v in material_norm for v in _num_variants(anchor))


def verify_line(line: str, material_norm: str) -> dict[str, Any]:
    """单条经历/技能行验据。返回 {status, coverage, missing_tokens, missing_anchors}。

    锚点(日期/数字)全中 + 实义单元覆盖率达标 → PASS;否则 FLAG(打回不进终稿)。
    行内中文数字先归一(五十万→50万、四成→40%),与素材同基准再比。
    """
    line = _cn2num(line)
    units = _content_units(line)
    mat_lower = material_norm.lower()
    missing_units = [u for u in units if u not in material_norm and u.lower() not in mat_lower]
    coverage = 1.0 if not units else round(1 - len(missing_units) / len(units), 4)
    missing_anchors = [a for a in extract_anchors(line) if not anchor_in_material(a, material_norm)]
    ok = (not missing_anchors) and coverage >= TOKEN_COVERAGE
    return {
        "status": "PASS" if ok else "FLAG",
        "coverage": coverage,
        "missing_tokens": missing_units,
        "missing_anchors": missing_anchors,
    }


def parse_draft(lines: list[str], verify_sections: list[str]) -> list[dict[str, Any]]:
    """草稿 → 待验条目(验证节内的全部内容行,含 ### 公司/时间子标题——它们也是事实主张)。

    节标题行(含节名的 markdown 标题,或 ≤12 字的裸节名行)只设定语境、自身不作为条目;
    节识别只认 verify_sections 清单;一个节都认不出 → 空(适配层据此整体转人工)。
    """
    entries: list[dict[str, Any]] = []
    current: str | None = None
    for no, raw in enumerate(lines, start=1):
        s = raw.strip()
        if not s:
            continue
        hit = next((sec for sec in verify_sections if sec in s), None)
        md = re.match(r"^(#{1,6})\s", raw)
        if md:
            level = len(md.group(1))
            if level <= 2:
                current = hit  # ## 级:命中验据节则切换,否则重置(如「自我评价」不核)
                continue
            if current is not None:  # ### 及更深:公司/时间子标题也是事实主张,作为条目
                entries.append({"line_no": no, "section": current, "text": s})
            continue
        if hit and len(s) <= 12:
            current = hit
            continue
        if current is None:
            continue
        entries.append({"line_no": no, "section": current, "text": s})
    return entries


def parse_timeline(entries: list[dict[str, Any]]) -> list[tuple[int, int, int, int, int]]:
    """从过验条目抽时间区间 → [(sy, sm, ey, em, line_no)]。"""
    out: list[tuple[int, int, int, int, int]] = []
    for e in entries:
        for m in _DATE_RANGE.finditer(e["text"]):
            sy, sm = int(m.group(1)), int(m.group(2))
            end = re.sub(r"\s+", "", m.group(3))
            if end == "至今":
                import datetime as _dt

                t = _dt.date.today()
                ey, em = t.year, t.month
            else:
                parts = re.findall(r"\d+", end)
                ey = int(parts[0])
                em = int(parts[1]) if len(parts) > 1 else 12
            out.append((sy, sm, ey, em, e["line_no"]))
    return sorted(out)


def check_timeline(ranges: list[tuple[int, int, int, int, int]], gap_months: int = GAP_MONTHS) -> list[dict[str, Any]]:
    """断档/重叠点名。只报事实(月份差),不下解释。"""
    issues: list[dict[str, Any]] = []
    for i in range(1, len(ranges)):
        ps, pm, pey, pem, pno = ranges[i - 1]
        cs, cm, cey, cem, cno = ranges[i]
        prev_end = pey * 12 + pem
        cur_start = cs * 12 + cm
        gap = cur_start - prev_end
        if gap > gap_months:
            issues.append(
                {
                    "type": "断档",
                    "detail": f"{pey}.{pem:02d} 结束后到 {cs}.{cm:02d} 才开始,间隔 {gap} 个月",
                    "lines": [pno, cno],
                }
            )
        elif gap < 0:
            issues.append(
                {
                    "type": "重叠",
                    "detail": f"{cs}.{cm:02d} 开始时,上一段({pey}.{pem:02d} 结束)尚未结束",
                    "lines": [pno, cno],
                }
            )
    return issues


def extract_jd_requirements(jd_text: str, degree_words: list[str], cert_words: list[str], tool_words: list[str]) -> list[dict[str, str]]:
    """JD 硬性要求抽取:学历词/证书工具词/年限(N 年)。逐条可指回 JD 原词。

    工具词按长度降序消费命中段——否则「MySQL」会因子串让「SQL」也成要求。
    """
    reqs: list[dict[str, str]] = []
    jdn = normalize_for_match(jd_text)
    for w in degree_words:
        if w in jdn:
            reqs.append({"kind": "学历", "word": w})
    for w in sorted(cert_words + tool_words, key=len, reverse=True):
        pos = jdn.find(w)
        if pos >= 0:
            reqs.append({"kind": "证书/工具", "word": w})
            jdn = jdn[:pos] + "\u0000" * len(w) + jdn[pos + len(w):]  # 消费命中段,短词不再蹭长词
    for m in re.finditer(r"(\d+)\s*年(?:以上)?", jdn):
        reqs.append({"kind": "年限", "word": f"{m.group(1)}年"})
    return reqs
