"""
checker.py —— 兴趣班排期核对判定核心(纯函数,判定权归代码)

C 族判据(构思方案 §3-A8):
    C1 时间重叠(high)   同一天两节课时段相交
    C2 衔接不足(medium) 相邻两节间隔低于通勤阈值且地点不同(或地点未知)
    C3 接送冲突(medium) 同一天同一接送人的两节课重叠或衔接不足

行格式:机构 + 星期/日期 + HH:MM-HH:MM + 地点[+接送人],字段序不拘。
星期方言:周六/星期六/周6;日期方言 M-D / M月D日。解析不了的行 → uncertain。
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date, timedelta

_RE_DATERANGE = re.compile(r"(\d{1,2})[:：](\d{2})\s*[-–—~至到]\s*(\d{1,2})[:：](\d{2})")
_RE_DATE = re.compile(r"(\d{1,2})[-/月](\d{1,2})[日号]?")
_RE_WEEK = re.compile(r"(?:周|星期)([一二三四五六日天6])")
_WEEKDAY = {"一": 0, "二": 1, "三": 2, "四": 3, "五": 4, "六": 5, "6": 5, "日": 6, "天": 6}
_TODAY = date(2026, 11, 1)  # 判定锚点:周日;周X 锚到未来最近

_TODAY_W = 6


@dataclass(frozen=True)
class Lesson:
    org: str
    day: str        # 日期 YYYY-MM-DD
    start: str      # HH:MM
    end: str
    place: str
    pickup: str     # 接送人(可空)
    line_no: int


@dataclass
class ParsedInput:
    lessons: list[Lesson] = field(default_factory=list)
    uncertain: list[tuple[int, str]] = field(default_factory=list)

    def counts(self) -> dict[str, int]:
        return {"lessons": len(self.lessons), "days": len({l.day for l in self.lessons}),
                "uncertain": len(self.uncertain)}

    def to_state(self) -> dict:
        return {"lessons": [l.__dict__ for l in self.lessons],
                "uncertain": [list(u) for u in self.uncertain]}

    def empty(self) -> bool:
        return not self.lessons


@dataclass(frozen=True)
class Thresholds:
    min_transfer_minutes: int = 30


@dataclass(frozen=True)
class Finding:
    rule: str
    severity: str
    target: str
    when: str
    detail: str


def _next_date_for_weekday(target: int) -> str:
    delta = (target - _TODAY.weekday()) % 7
    return (_TODAY + timedelta(days=delta)).isoformat()


def _parse_day(line: str) -> str | None:
    m = _RE_DATE.search(line)
    if m:
        mo, dy = int(m.group(1)), int(m.group(2))
        if 1 <= mo <= 12 and 1 <= dy <= 31:
            return f"{_TODAY.year:04d}-{mo:02d}-{dy:02d}"
    m = _RE_WEEK.search(line)
    if m:
        return _next_date_for_weekday(_WEEKDAY[m.group(1)])
    return None


def _parse_range(line: str) -> tuple[str, str] | None:
    m = _RE_DATERANGE.search(line)
    if not m:
        return None
    h1, m1, h2, m2 = int(m.group(1)), int(m.group(2)), int(m.group(3)), int(m.group(4))
    if not (0 <= h1 <= 23 and 0 <= h2 <= 23):
        return None
    return f"{h1:02d}:{m1:02d}", f"{h2:02d}:{m2:02d}"


def parse_all(text: str = "") -> ParsedInput:
    out = ParsedInput()
    for no, ln in enumerate([x.strip() for x in text.splitlines() if x.strip()], 1):
        day = _parse_day(ln)
        rng = _parse_range(ln)
        if not day or not rng:
            out.uncertain.append((no, ln))
            continue
        rest = _RE_DATERANGE.sub(" ", ln)
        rest = _RE_DATE.sub(" ", rest, count=1)
        rest = _RE_WEEK.sub(" ", rest)
        segs = [s.strip(" ,，;；:：|｜()()") for s in rest.split()]
        segs = [s for s in segs if s and not re.fullmatch(r"\d+", s)]
        pickup = ""
        mm = re.search(r"[（(]([^()（）]*)送[）)]|接送[:：]?(\S+)", ln)
        if mm:
            pickup = (mm.group(1) or mm.group(2) or "").strip()
            segs = [s for s in segs if s != pickup]
        org = segs[0] if segs else "未知机构"
        place = segs[1] if len(segs) > 1 else ""
        out.lessons.append(Lesson(org, day, rng[0], rng[1], place, pickup, no))
    return out


def from_state(state: dict) -> ParsedInput:
    out = ParsedInput()
    for d in state.get("lessons", []):
        out.lessons.append(Lesson(**d))
    out.uncertain = [tuple(u) for u in state.get("uncertain", [])]
    return out


def _mins(hhmm: str) -> int:
    h, m = hhmm.split(":")
    return int(h) * 60 + int(m)


def _overlap(a: Lesson, b: Lesson) -> bool:
    return _mins(a.start) < _mins(b.end) and _mins(b.start) < _mins(a.end)


def _gap(a: Lesson, b: Lesson) -> int:
    return _mins(b.start) - _mins(a.end)


def check_conflicts(parsed: ParsedInput, th: Thresholds) -> list[Finding]:
    """C1 + C2:同日逐对课程——重叠判 C1,衔接不足且地点不同判 C2。"""
    by_day: dict[str, list[Lesson]] = {}
    for l in parsed.lessons:
        by_day.setdefault(l.day, []).append(l)
    out: list[Finding] = []
    for day, ls in sorted(by_day.items()):
        seq = sorted(ls, key=lambda l: _mins(l.start))
        for a, b in zip(seq, seq[1:]):
            if _overlap(a, b):
                out.append(Finding("C1", "high", f"{a.org} × {b.org}", day,
                                   f"{a.start}-{a.end} 与 {b.start}-{b.end} 时间重叠,必须取舍一个"))
            elif 0 < _gap(a, b) < th.min_transfer_minutes and (
                    a.place != b.place or not a.place or not b.place):
                out.append(Finding("C2", "medium", f"{a.org} → {b.org}", day,
                                   f"间隔仅 {_gap(a, b)} 分钟(<{th.min_transfer_minutes} 通勤阈值)"
                                   f"{'且地点不同' if a.place and b.place and a.place != b.place else ''},赶场风险"))
    return out


def check_pickup(parsed: ParsedInput, th: Thresholds) -> list[Finding]:
    """C3:同一接送人同日两节重叠或衔接不足。"""
    by_day: dict[str, list[Lesson]] = {}
    for l in parsed.lessons:
        if l.pickup:
            by_day.setdefault(l.day, []).append(l)
    out: list[Finding] = []
    for day, ls in sorted(by_day.items()):
        by_person: dict[str, list[Lesson]] = {}
        for l in ls:
            by_person.setdefault(l.pickup, []).append(l)
        for person, mine in sorted(by_person.items()):
            seq = sorted(mine, key=lambda l: _mins(l.start))
            for a, b in zip(seq, seq[1:]):
                if _overlap(a, b) or 0 < _gap(a, b) < th.min_transfer_minutes:
                    out.append(Finding("C3", "medium", f"接送人 {person}", day,
                                       f"{a.org} 与 {b.org} 衔接不过来,接送撞车"))
    return out


def run_all_checks(parsed: ParsedInput,
                   th: Thresholds) -> tuple[list[Finding], dict]:
    findings: list[Finding] = []
    findings += check_conflicts(parsed, th)
    findings += check_pickup(parsed, th)
    findings.sort(key=lambda f: (f.rule, f.when, f.target))
    week: dict[str, list[str]] = {}
    for l in parsed.lessons:
        week.setdefault(l.day, []).append(f"{l.start}{l.org}")
    extras = {"days": {d: sorted(v) for d, v in sorted(week.items())}}
    return findings, extras
