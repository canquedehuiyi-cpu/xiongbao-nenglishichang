"""
checker.py —— 用药打卡核对判定核心(纯函数,判定权归代码)

M 族判据(构思方案 §3-A1):
    M1 漏服(medium)   计划的某次服药,当天窗口内无打卡
    M2 重复服用(high) 同药两次打卡间隔过近(疑似重复服用/重复记录)
    M3 间隔不足(medium) 同药相邻两次打卡间隔低于最小间隔(默认按每日次数推导)
    M4 同服禁忌(medium) 同一天实际服用了规则表中不宜同服的两种药(提示核对,以医嘱为准)
    M5 疗程断档(low)  计划疗程内整天完全没打卡

本模块不碰 IO、不碰引擎:输入字符串,输出结构化事实。
解析不了的行 → UncertainLine,不臆造结论(UNCERTAIN 转人工)。

日期方言:YYYY-M-D / YYYY/M/D / M-D / M月D日;缺年 → 取全量输入中最早完整日期的年,
再无则 DEFAULT_YEAR。时间方言:HH:MM(含全角冒号)/H点/H点半 + 时段前缀
(凌晨/早上/上午/中午/下午/傍晚/晚上/睡前)。
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

DEFAULT_YEAR = 2026
DEFAULT_GRACE_MINUTES = 30        # M1:计划时间 ±N 分钟内算已服
DEFAULT_DUP_WINDOW_MINUTES = 30   # M2:同药两次打卡 ≤N 分钟判重复
DEFAULT_MIN_INTERVAL_MINUTES = 240  # M3:兜底最小间隔(计划未写每日次数时)
# M4 默认同服禁忌表(常见组合提示,最终以医嘱与药品说明书为准;可经 rules-config 扩展)
DEFAULT_FORBIDDEN_PAIRS: tuple[tuple[str, str], ...] = (
    ("头孢", "酒精"),
    ("头孢", "酒"),
    ("华法林", "阿司匹林"),
)

# ---------------------------------------------------------------- 数据模型


@dataclass(frozen=True)
class PlanDose:
    """一次计划服药:药名 + 日期 + 时间(+剂量)。"""

    drug: str
    date: str  # YYYY-MM-DD(已归一)
    time: str  # HH:MM(已归一)
    dose: str = ""
    line_no: int = 0


@dataclass(frozen=True)
class LogTake:
    """一次实际打卡:药名 + 日期 + 时间(+剂量)。"""

    drug: str
    date: str
    time: str
    dose: str = ""
    line_no: int = 0


@dataclass(frozen=True)
class DrugPlan:
    """口语式计划行的归一结果:药名 + 每日次数 + 时刻表 + 疗程范围。"""

    drug: str
    times: tuple[str, ...]  # HH:MM 列表
    date_from: str  # YYYY-MM-DD(含)
    date_to: str  # YYYY-MM-DD(含)
    dose: str = ""
    daily_n: int = 0
    line_no: int = 0


@dataclass(frozen=True)
class Finding:
    """一条判据命中。severity ∈ {high, medium, low, info}。"""

    rule: str
    severity: str
    drug: str
    date: str
    detail: str


@dataclass
class ParsedInput:
    """P1 归一产物:计划面/打卡面/口语计划/未解析行。"""

    plan_doses: list[PlanDose] = field(default_factory=list)
    drug_plans: list[DrugPlan] = field(default_factory=list)
    log_takes: list[LogTake] = field(default_factory=list)
    uncertain: list[tuple[str, int, str]] = field(default_factory=list)  # (面, 行号, 原文)
    reference_year: int = DEFAULT_YEAR


@dataclass(frozen=True)
class Thresholds:
    """判定阈值(默认值在代码;rules-config 外置覆盖)。"""

    grace_minutes: int = DEFAULT_GRACE_MINUTES
    dup_window_minutes: int = DEFAULT_DUP_WINDOW_MINUTES
    min_interval_minutes: int = DEFAULT_MIN_INTERVAL_MINUTES
    forbidden_pairs: tuple[tuple[str, str], ...] = DEFAULT_FORBIDDEN_PAIRS


# ---------------------------------------------------------------- 方言解析

_RE_FULL_DATE = re.compile(r"(\d{4})[-/年.](\d{1,2})[-/月.](\d{1,2})日?")
_RE_MD_DATE = re.compile(r"(\d{1,2})[-/月](\d{1,2})日?")
_RE_HM = re.compile(r"(\d{1,2})[:：时点](\d{2})?")
_RE_HOUR_POINT = re.compile(r"(\d{1,2})点半?")
_PERIOD_PREFIX = (
    ("凌晨", 0), ("清晨", 0), ("早上", 0), ("早晨", 0), ("上午", 0),
    ("中午", 12), ("午后", 12), ("下午", 12),
    ("傍晚", 12), ("晚上", 12), ("今晚", 12), ("夜里", 12), ("睡前", 22),
)


def _pad2(n: int) -> str:
    return f"{n:02d}"


def parse_date_token(dstr: str, year: int) -> str | None:
    """日期方言 → YYYY-MM-DD;认不出返回 None。"""
    dstr = dstr.strip()
    m = _RE_FULL_DATE.search(dstr)
    if m:
        y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
    else:
        m2 = _RE_MD_DATE.search(dstr)
        if not m2:
            return None
        y, mo, d = year, int(m2.group(1)), int(m2.group(2))
    if not (1 <= mo <= 12 and 1 <= d <= 31):
        return None
    return f"{y:04d}-{mo:02d}-{d:02d}"


def parse_time_token(dstr: str) -> str | None:
    """时间方言 → HH:MM;认不出返回 None。

    支持冒号(含全角)、H点/H点半、时段前缀(下午3点→15:00,睡前→22:00)。
    """
    dstr = dstr.strip()
    prefix_shift = 0
    consumed = dstr
    for word, base in _PERIOD_PREFIX:
        if dstr.startswith(word):
            if word == "睡前":
                return "22:00"
            prefix_shift = base
            consumed = dstr[len(word):]
            break
    m = re.search(r"(\d{1,2})[:：时点](\d{1,2})?", consumed)
    if m:
        h, mi = int(m.group(1)), int(m.group(2) or 0)
    else:
        return None
    if consumed.rstrip().endswith("半"):
        mi = 30
    if prefix_shift and h < 12:
        h += prefix_shift
    if not (0 <= h <= 23 and 0 <= mi <= 59):
        return None
    return f"{_pad2(h)}:{_pad2(mi)}"


def _infer_year(plan_text: str, log_text: str) -> int:
    """缺年日期的基准年:全量输入最早完整日期的年,无则 DEFAULT_YEAR。"""
    years = [int(m.group(1)) for m in _RE_FULL_DATE.finditer(plan_text + "\n" + log_text)]
    return min(years) if years else DEFAULT_YEAR


def _split_csv_or_ws(line: str) -> list[str]:
    """CSV 优先(≥3 逗号/分号/制表符分段),否则按空白切。"""
    for sep in (",", ";", "，", "；", "\t"):
        parts = [p.strip() for p in line.split(sep) if p.strip()]
        if len(parts) >= 3:
            return parts
    return [p for p in line.split() if p]


def parse_plan_line(line: str, line_no: int, year: int, out: ParsedInput) -> None:
    """计划行两方言:CSV 行(药名,日期,时间[,剂量])或口语行(每日N次+时刻表+疗程)。"""
    if m := re.search(r"每日\s*(\d+)\s*次", line):
        out.drug_plans.append(_parse_colloquial_plan(line, line_no, int(m.group(1))))
        return
    parts = _split_csv_or_ws(line)
    if len(parts) < 3:
        out.uncertain.append(("plan", line_no, line))
        return
    drug = parts[0]
    date = next((parse_date_token(p, year) for p in parts[1:] if parse_date_token(p, year)), None)
    time_ = next((parse_time_token(p) for p in parts[1:] if parse_time_token(p)), None)
    if not date or not time_:
        out.uncertain.append(("plan", line_no, line))
        return
    dose = parts[-1] if parts[-1] not in (date, time_) and not _looks_like_datetime(parts[-1]) else ""
    out.plan_doses.append(PlanDose(drug, date, time_, dose, line_no))


def _looks_like_datetime(dstr: str) -> bool:
    return bool(_RE_FULL_DATE.search(dstr) or _RE_MD_DATE.search(dstr)
                or _RE_HM.search(dstr))


def _parse_colloquial_plan(line: str, line_no: int, daily_n: int) -> DrugPlan:
    """口语计划行:『阿莫西林 每日3次(08:00/14:00/20:00) 每次1粒 10-28至11-04』"""
    drug = line.split()[0] if line.split() else line.strip()
    m_drug = re.match(r"([^\s,，;；()（）]+)", line.strip())
    if m_drug:
        drug = m_drug.group(1)
    times: list[str] = []
    m_times = re.search(r"[（(]([^()（）]*)[)）]", line)
    if m_times:
        for tok in re.split(r"[/、,，\s]+", m_times.group(1)):
            if t := parse_time_token(tok):
                times.append(t)
    dose = ""
    if m_dose := re.search(r"每次\s*([^\s,，;；()（）]+)", line):
        dose = m_dose.group(1)
    date_from = date_to = ""
    if m_range := re.search(
        r"(\d{1,2}[-/月]\d{1,2}日?|\d{4}[-/年.]\d{1,2}[-/月.]\d{1,2}日?)\s*[至到~—-]\s*"
        r"(\d{1,2}[-/月]\d{1,2}日?|\d{4}[-/年.]\d{1,2}[-/月.]\d{1,2}日?)", line
    ):
        date_from = parse_date_token(m_range.group(1), DEFAULT_YEAR) or ""
        date_to = parse_date_token(m_range.group(2), DEFAULT_YEAR) or ""
    elif m_from := re.search(
        r"(\d{1,2}[-/月]\d{1,2}日?|\d{4}[-/年.]\d{1,2}[-/月.]\d{1,2}日?)\s*起", line
    ):
        date_from = parse_date_token(m_from.group(1), DEFAULT_YEAR) or ""
    return DrugPlan(drug=drug, times=tuple(times) or (("", ) * 0), date_from=date_from,
                    date_to=date_to, dose=dose, daily_n=daily_n, line_no=line_no)


def parse_log_line(line: str, line_no: int, year: int, out: ParsedInput) -> None:
    """打卡行:字段序不固定,按 dstr 形态识别日期/时间,剩余首段为药名。"""
    parts = _split_csv_or_ws(line)
    if len(parts) < 2:
        out.uncertain.append(("log", line_no, line))
        return
    date = time_ = None
    drug = dose = ""
    for idx, p in enumerate(parts):
        if date is None and parse_date_token(p, year):
            date = parse_date_token(p, year)
            continue
        if time_ is None and parse_time_token(p):
            time_ = parse_time_token(p)
            continue
        if not drug:
            drug = p
        elif not _looks_like_datetime(p):
            dose = p
    if not drug or not date or not time_:
        out.uncertain.append(("log", line_no, line))
        return
    out.log_takes.append(LogTake(drug, date, time_, dose, line_no))


def parse_all(plan_text: str, log_text: str) -> ParsedInput:
    """两段粘贴文本 → ParsedInput;逐行 fail-soft,坏行进 uncertain。"""
    year = _infer_year(plan_text, log_text)
    out = ParsedInput(reference_year=year)
    for no, ln in enumerate(_nonempty(plan_text), 1):
        parse_plan_line(ln, no, year, out)
    for no, ln in enumerate(_nonempty(log_text), 1):
        parse_log_line(ln, no, year, out)
    return out


def _nonempty(text: str) -> list[str]:
    return [ln.strip() for ln in text.splitlines() if ln.strip()]


# ---------------------------------------------------------------- 判据计算


def _minutes(hhmm: str) -> int:
    h, m = hhmm.split(":")
    return int(h) * 60 + int(m)


def expand_drug_plans(parsed: ParsedInput, last_log_date: str) -> list[PlanDose]:
    """口语计划(药名+时刻表+疗程范围)展开成逐日逐次的 PlanDose。

    date_to 为空时以最后打卡日封口(再无则 date_from 当天);两端都空则跳过
    (信息不足以展开,原行已在解析面留下事实,由 M 族不消费)。
    """
    from datetime import date as _date, timedelta as _td

    doses: list[PlanDose] = []
    for dp in parsed.drug_plans:
        if not dp.date_from or not dp.times:
            continue
        start = _date.fromisoformat(dp.date_from)
        end = _date.fromisoformat(dp.date_to) if dp.date_to else (
            _date.fromisoformat(last_log_date) if last_log_date else start)
        d = start
        while d <= end:
            for t in dp.times:
                doses.append(PlanDose(dp.drug, d.isoformat(), t, dp.dose, dp.line_no))
            d += _td(days=1)
    return doses


def check_missed(parsed: ParsedInput, plan_doses: list[PlanDose],
                 th: Thresholds) -> list[Finding]:
    """M1 漏服:计划时刻 ±grace 内无同药打卡。"""
    takes_by_key: dict[tuple[str, str], list[int]] = {}
    for tk in parsed.log_takes:
        takes_by_key.setdefault((tk.drug, tk.date), []).append(_minutes(tk.time))
    out: list[Finding] = []
    for pd in plan_doses:
        window = takes_by_key.get((pd.drug, pd.date), [])
        if not any(abs(t - _minutes(pd.time)) <= th.grace_minutes for t in window):
            out.append(Finding("M1", "medium", pd.drug, pd.date,
                               f"计划 {_fmt(pd)} 无打卡(±{th.grace_minutes}分钟窗口)"))
    return out


def check_duplicate(parsed: ParsedInput, th: Thresholds) -> list[Finding]:
    """M2 重复服用:同药同日两次打卡 ≤dup_window 分钟。"""
    out: list[Finding] = []
    by_key: dict[tuple[str, str], list[LogTake]] = {}
    for tk in parsed.log_takes:
        by_key.setdefault((tk.drug, tk.date), []).append(tk)
    for (drug, date), takes in by_key.items():
        takes = sorted(takes, key=lambda t: _minutes(t.time))
        for a, b in zip(takes, takes[1:]):
            gap = _minutes(b.time) - _minutes(a.time)
            if gap <= th.dup_window_minutes:
                out.append(Finding(
                    "M2", "high", drug, date,
                    f"{a.time} 与 {b.time} 间隔 {gap} 分钟(≤{th.dup_window_minutes}),"
                    "疑似重复服用或重复记录——请人工确认实际次数"))
    return out


def _min_interval_for(drug: str, parsed: ParsedInput, th: Thresholds) -> int:
    """最小间隔:计划声明每日N次 → 24h/N×0.75;否则用兜底阈值。"""
    for dp in parsed.drug_plans:
        if dp.drug == drug and dp.daily_n >= 2:
            return max(60, int(1440 / dp.daily_n * 0.75))
    return th.min_interval_minutes


def check_interval(parsed: ParsedInput, th: Thresholds) -> list[Finding]:
    """M3 间隔不足:同药同日相邻打卡间隔 < 最小间隔(且 > dup_window,否则归 M2)。"""
    out: list[Finding] = []
    by_key: dict[tuple[str, str], list[LogTake]] = {}
    for tk in parsed.log_takes:
        by_key.setdefault((tk.drug, tk.date), []).append(tk)
    for (drug, date), takes in by_key.items():
        takes = sorted(takes, key=lambda t: _minutes(t.time))
        floor = _min_interval_for(drug, parsed, th)
        for a, b in zip(takes, takes[1:]):
            gap = _minutes(b.time) - _minutes(a.time)
            if th.dup_window_minutes < gap < floor:
                out.append(Finding("M3", "medium", drug, date,
                                   f"{a.time} 与 {b.time} 间隔 {gap} 分钟(<{floor}),"
                                   "低于该药最小间隔"))
    return out


def check_forbidden(parsed: ParsedInput, th: Thresholds) -> list[Finding]:
    """M4 同服禁忌:同日实际打卡出现规则表同组两种药(提示核对,以医嘱为准)。"""
    day_drugs: dict[str, set[str]] = {}
    for tk in parsed.log_takes:
        day_drugs.setdefault(tk.date, set()).add(tk.drug)
    out: list[Finding] = []
    for date, drugs in day_drugs.items():
        for a, b in th.forbidden_pairs:
            hit_a = next((d for d in drugs if a in d), None)
            hit_b = next((d for d in drugs if b in d), None)
            if hit_a and hit_b and hit_a != hit_b:
                out.append(Finding("M4", "medium", f"{hit_a}+{hit_b}", date,
                                   "同服禁忌提示(默认规则表,非诊疗意见):"
                                   "请核对医嘱与药品说明书"))
    return out


def check_course_gap(parsed: ParsedInput, plan_doses: list[PlanDose]) -> list[Finding]:
    """M5 疗程断档:计划疗程内整天无该药任何打卡(逐药聚合列出断档日)。"""
    plan_days: dict[str, set[str]] = {}
    for pd in plan_doses:
        plan_days.setdefault(pd.drug, set()).add(pd.date)
    take_days: dict[str, set[str]] = {}
    for tk in parsed.log_takes:
        take_days.setdefault(tk.drug, set()).add(tk.date)
    out: list[Finding] = []
    for drug, days in plan_days.items():
        gaps = sorted(d for d in days if d not in take_days.get(drug, set()))
        if gaps:
            span = f"{min(days)}~{max(days)}"
            out.append(Finding("M5", "low", drug, span,
                               f"疗程内 {len(gaps)} 天全天无打卡:"
                               + "、".join(gaps[:5]) + ("…" if len(gaps) > 5 else "")))
    return out


def run_all_checks(parsed: ParsedInput, th: Thresholds) -> tuple[list[Finding], list[PlanDose]]:
    """M1~M5 全链。返回 (findings, 展开后的完整计划面)。"""
    last_log = max((tk.date for tk in parsed.log_takes), default="")
    plan_doses = list(parsed.plan_doses) + expand_drug_plans(parsed, last_log)
    findings: list[Finding] = []
    findings += check_missed(parsed, plan_doses, th)
    findings += check_duplicate(parsed, th)
    findings += check_interval(parsed, th)
    findings += check_forbidden(parsed, th)
    findings += check_course_gap(parsed, plan_doses)
    findings.sort(key=lambda f: (f.date, f.rule, f.drug))
    return findings, plan_doses


def _fmt(pd: PlanDose) -> str:
    return f"{pd.date} {pd.time}" + (f" {pd.dose}" if pd.dose else "")
