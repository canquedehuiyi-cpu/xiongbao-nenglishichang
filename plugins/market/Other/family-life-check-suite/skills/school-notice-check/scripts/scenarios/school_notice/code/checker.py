"""
checker.py —— 家长群通知要求核对判定核心(纯函数,判定权归代码)

N 族判据(构思方案 §3-A3):
    N1 要求提取(info)   含截止/带物/缴费/接龙信号词的消息提取为要求条目
    N2 截止冲突(medium)  两条要求截止同一天(时刻都有且间隔≤阈值,或只有日期同日)
    N3 已过期(low)      截止日期早于系统当天——标记防误传

解析:逐行识别要求类型(带物/缴费/接龙/作业/其他)+ 截止时间。
日期方言:今天/明天/后天(锚系统日)、周X/星期X(未来最近)、M月D日、M-D、YYYY-M-D;
时间方言同产品族(HH:MM/H点)。解析不了的行 → uncertain,不臆造。
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date, timedelta

# ---------------------------------------------------------------- 数据模型


@dataclass(frozen=True)
class Requirement:
    item: str          # 事项摘要(原行截断)
    kind: str          # 带物/缴费/接龙/作业/其他
    deadline: str      # YYYY-MM-DD(解析到)或 ""
    deadline_time: str  # HH:MM 或 ""
    line_no: int


@dataclass
class ParsedInput:
    requirements: list[Requirement] = field(default_factory=list)
    uncertain: list[tuple[int, str]] = field(default_factory=list)

    def counts(self) -> dict[str, int]:
        by_kind: dict[str, int] = {}
        for r in self.requirements:
            by_kind[r.kind] = by_kind.get(r.kind, 0) + 1
        by_kind["uncertain"] = len(self.uncertain)
        return by_kind

    def to_state(self) -> dict:
        return {"requirements": [r.__dict__ for r in self.requirements],
                "uncertain": [list(u) for u in self.uncertain]}

    def empty(self) -> bool:
        return not self.requirements


@dataclass(frozen=True)
class Thresholds:
    deadline_conflict_minutes: int = 0


@dataclass(frozen=True)
class Finding:
    rule: str
    severity: str
    target: str
    when: str
    detail: str


# ---------------------------------------------------------------- 信号词

_KIND_SIGNALS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("缴费", ("缴费", "缴", "交费", "费用", "收款", "转账", "支付宝", "微信收款")),
    ("接龙", ("接龙", "统计", "报名", "填表", "问卷")),
    ("带物", ("带", "准备", "带来", "穿", "交回", "交")),
    ("作业", ("作业", "背诵", "听读", "朗读", "打卡", "练习")),
)
_EXCLUDE = ("退订", "回T")

_RE_YMD = re.compile(r"(\d{4})[-/年.](\d{1,2})[-/月.](\d{1,2})")
_RE_MD = re.compile(r"(\d{1,2})月(\d{1,2})[日号]?|(\d{1,2})[-/](\d{1,2})[日号]?")
_RE_WEEK = re.compile(r"(?:本|下)?(?:周|星期)([一二三四五六日天])")
_RE_REL = re.compile(r"(今天|今晚|明天|后天)")
_RE_TIME = re.compile(r"(\d{1,2})[:：点时](\d{2})?|(上午|下午|晚上)?(\d{1,2})点半?")
_WEEKDAY = {"一": 0, "二": 1, "三": 2, "四": 3, "五": 4, "六": 5, "日": 6, "天": 6}

TODAY = date.today()  # 判定锚点:系统当天(N3 过期判据;单次运行内一致)


def _classify(line: str) -> str | None:
    if any(w in line for w in _EXCLUDE):
        return None
    for kind, words in _KIND_SIGNALS:
        if any(w in line for w in words):
            return kind
    return None


def _next_weekday(target: int) -> date:
    """未来最近的 target(0=周一);今天是 target 则算今天。"""
    delta = (target - TODAY.weekday()) % 7
    return TODAY + timedelta(days=delta)


def parse_deadline(line: str) -> tuple[str, str]:
    """截止时间解析 → (YYYY-MM-DD | "", HH:MM | "")。"""
    m = _RE_YMD.search(line)
    if m:
        d = f"{int(m.group(1)):04d}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"
        return d, _parse_time(line) or ""
    m = _RE_MD.search(line)
    if m:
        if m.group(1):
            mo, dy = int(m.group(1)), int(m.group(2))
        else:
            mo, dy = int(m.group(3)), int(m.group(4))
        if 1 <= mo <= 12 and 1 <= dy <= 31:
            year = TODAY.year if mo >= TODAY.month else TODAY.year + 1
            return f"{year:04d}-{mo:02d}-{dy:02d}", _parse_time(line) or ""
    m = _RE_WEEK.search(line)
    if m:
        target = _WEEKDAY[m.group(1)]
        if "上周" in line:   # 负向方言:过去最近的该 weekday
            delta = (TODAY.weekday() - target) % 7 or 7
            d = TODAY - timedelta(days=delta)
        else:
            d = _next_weekday(target)
        return d.isoformat(), _parse_time(line) or ""
    m = _RE_REL.search(line)
    if m:
        offset = {"今天": 0, "今晚": 0, "明天": 1, "后天": 2}[m.group(1)]
        return (TODAY + timedelta(days=offset)).isoformat(), _parse_time(line) or ""
    return "", ""


def _parse_time(line: str) -> str | None:
    m = re.search(r"(上午|下午|晚上)?(\d{1,2})[:：](\d{2})", line)
    if m:
        h, mi = int(m.group(2)), int(m.group(3))
        if m.group(1) in ("下午", "晚上") and h < 12:
            h += 12
        if 0 <= h <= 23:
            return f"{h:02d}:{mi:02d}"
    m = re.search(r"(上午|下午|晚上)?(\d{1,2})点(半)?", line)
    if m:
        h = int(m.group(2))
        if m.group(1) in ("下午", "晚上") and h < 12:
            h += 12
        mi = 30 if m.group(3) else 0
        if 0 <= h <= 23:
            return f"{h:02d}:{mi:02d}"
    return None


def parse_all(text: str = "") -> ParsedInput:
    out = ParsedInput()
    for no, ln in enumerate([x.strip() for x in text.splitlines() if x.strip()], 1):
        kind = _classify(ln)
        if not kind:
            out.uncertain.append((no, ln))
            continue
        dl, tm = parse_deadline(ln)
        item = ln if len(ln) <= 40 else ln[:38] + "…"
        out.requirements.append(Requirement(item, kind, dl, tm, no))
    return out


def from_state(state: dict) -> ParsedInput:
    out = ParsedInput()
    for r in state.get("requirements", []):
        out.requirements.append(Requirement(**r))
    out.uncertain = [tuple(u) for u in state.get("uncertain", [])]
    return out


# ---------------------------------------------------------------- 判据


def check_conflict(parsed: ParsedInput, th: Thresholds) -> list[Finding]:
    """N2:截止同一天的两条要求——时刻都有比分钟差,否则同日即提示。"""
    by_date: dict[str, list[Requirement]] = {}
    for r in parsed.requirements:
        if r.deadline:
            by_date.setdefault(r.deadline, []).append(r)
    out: list[Finding] = []
    for dl, rs in sorted(by_date.items()):
        if len(rs) < 2:
            continue
        times = [(r, r.deadline_time) for r in rs if r.deadline_time]
        if len(times) >= 2 and th.deadline_conflict_minutes > 0:
            base = times[0]
            close = [x for x in times[1:]
                     if abs(_mins(x[1]) - _mins(base[1])) <= th.deadline_conflict_minutes]
            if close:
                out.append(Finding("N2", "medium", f"{len(close)+1} 条同刻截止", dl,
                                   f"{base[0].item} 与 {close[0][0].item} 截止时刻相近,注意排期"))
        else:
            items = " / ".join(r.item for r in rs[:3])
            out.append(Finding("N2", "medium", f"{len(rs)} 条同日截止", dl,
                               f"同一天截止:{items}——注意排期"))
    return out


def _mins(hhmm: str) -> int:
    h, m = hhmm.split(":")
    return int(h) * 60 + int(m)


def check_expired(parsed: ParsedInput) -> list[Finding]:
    """N3:截止早于系统当天(防过期误传)。"""
    out: list[Finding] = []
    for r in parsed.requirements:
        if r.deadline and r.deadline < TODAY.isoformat():
            out.append(Finding("N3", "low", r.item, r.deadline,
                               "截止已过——若群内仍被顶起误传,提醒家长忽略"))
    return out


def run_all_checks(parsed: ParsedInput,
                   th: Thresholds) -> tuple[list[Finding], dict]:
    findings: list[Finding] = []
    by_kind = parsed.counts()
    findings.append(Finding(
        "N1", "info", f"{len(parsed.requirements)} 条要求",
        f"锚点日 {TODAY.isoformat()}",
        "要求提取:" + "、".join(f"{k}×{v}" for k, v in sorted(by_kind.items())
                                if k != "uncertain" and v)))
    findings += check_conflict(parsed, th)
    findings += check_expired(parsed)
    findings.sort(key=lambda f: (f.rule, f.when, f.target))
    extras = {"today": TODAY.isoformat(), "kinds": by_kind}
    return findings, extras
