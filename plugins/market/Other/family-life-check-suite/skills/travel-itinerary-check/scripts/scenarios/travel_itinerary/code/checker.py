"""
checker.py —— 旅行行程单核对判定核心(纯函数,判定权归代码)

T 族判据(构思方案 §3-B3):
    T1 衔接不足(high)   相邻行程间隔低于阈值(默认国内 90 分钟;标注"国际/出境"用 150)
    T2 重复预订(medium) 同日同类型同城市两段行程
    T3 时间倒挂(high)   后一段行程时间早于前一段(输入顺序即行程序)

行格式:日期时间 + 类型词 + 城市[+平台],字段序不拘。
类型词:机票/航班/火车/高铁/酒店/入住/民宿/门票/景点。
日期:M-D / M月D日 / YYYY-M-D;时间 HH:MM(缺省:入住类 14:00,交通类须有)。
脱敏纪律:证件号/护照号不要贴。
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date, datetime

_RE_YMD = re.compile(r"(\d{4})[-/年.](\d{1,2})[-/月.](\d{1,2})")
_RE_MD = re.compile(r"(\d{1,2})[-/月](\d{1,2})[日号]?")
_RE_TIME = re.compile(r"(\d{1,2})[:：](\d{2})|(\d{1,2})点(半)?")
_TYPE_WORDS = ("机票", "航班", "火车", "高铁", "动车", "酒店", "入住", "民宿", "门票", "景点")
_INTL_MARK = ("国际", "出境", "入境", "港澳", "国外")
_DEFAULT_CHECKIN = "14:00"
_TODAY = date(2026, 11, 1)


@dataclass(frozen=True)
class Leg:
    when: str       # YYYY-MM-DD HH:MM
    kind: str       # 交通(transit)/住宿(stay)/活动(activity)
    raw_kind: str
    city: str
    intl: bool
    line_no: int


@dataclass
class ParsedInput:
    legs: list[Leg] = field(default_factory=list)
    uncertain: list[tuple[int, str]] = field(default_factory=list)

    def counts(self) -> dict[str, int]:
        by: dict[str, int] = {}
        for l in self.legs:
            by[l.kind] = by.get(l.kind, 0) + 1
        by["uncertain"] = len(self.uncertain)
        return by

    def to_state(self) -> dict:
        return {"legs": [l.__dict__ for l in self.legs],
                "uncertain": [list(u) for u in self.uncertain]}

    def empty(self) -> bool:
        return not self.legs


@dataclass(frozen=True)
class Thresholds:
    domestic_transfer_minutes: int = 90
    intl_transfer_minutes: int = 150


@dataclass(frozen=True)
class Finding:
    rule: str
    severity: str
    target: str
    when: str
    detail: str


def _classify(line: str) -> str:
    if any(w in line for w in ("酒店", "入住", "民宿")):
        return "stay"
    if any(w in line for w in ("门票", "景点")):
        return "activity"
    return "transit"


def _parse_when(line: str, year_hint: int) -> str | None:
    my = _RE_YMD.search(line)
    if my:
        d = date(int(my.group(1)), int(my.group(2)), int(my.group(3)))
    else:
        md = _RE_MD.search(line)
        if not md:
            return None
        try:
            d = date(year_hint, int(md.group(1)), int(md.group(2)))
        except ValueError:
            return None
    mt = _RE_TIME.search(line)
    if mt:
        if mt.group(1):
            hh, mm = int(mt.group(1)), int(mt.group(2))
        else:
            hh, mm = int(mt.group(3)), 30 if mt.group(4) else 0
        if not (0 <= hh <= 23 and 0 <= mm <= 59):
            return None
    elif _classify(line) == "stay":
        hh, mm = 14, 0
    else:
        return None
    return f"{d.isoformat()} {hh:02d}:{mm:02d}"


def _parse_city(line: str) -> str:
    m = re.search(r"(?:抵达|到达|飞往|前往|去|从)\s*([一-鿿]{2,6})", line)
    if m:
        return m.group(1)
    segs = [s for s in re.split(r"[,，;；\s]+", line) if s]
    for s in segs:
        if re.fullmatch(r"[一-鿿]{2,4}(?:市|站|机场)?", s) and not any(w in s for w in _TYPE_WORDS):
            return s
    return ""


def parse_all(text: str = "") -> ParsedInput:
    out = ParsedInput()
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    years = [int(m.group(1)) for ln in lines for m in [_RE_YMD.search(ln)] if m]
    year_hint = min(years) if years else _TODAY.year
    for no, ln in enumerate(lines, 1):
        when = _parse_when(ln, year_hint)
        if not when or not any(w in ln for w in _TYPE_WORDS):
            out.uncertain.append((no, ln))
            continue
        out.legs.append(Leg(when, _classify(ln),
                            next(w for w in _TYPE_WORDS if w in ln),
                            _parse_city(ln), any(w in ln for w in _INTL_MARK), no))
    return out


def from_state(state: dict) -> ParsedInput:
    out = ParsedInput()
    for d in state.get("legs", []):
        out.legs.append(Leg(**d))
    out.uncertain = [tuple(u) for u in state.get("uncertain", [])]
    return out


def _dt(when: str) -> datetime:
    return datetime.fromisoformat(when)


def check_transfers(parsed: ParsedInput, th: Thresholds) -> list[Finding]:
    """T1:相邻行程衔接间隔低于阈值。"""
    out: list[Finding] = []
    seq = parsed.legs
    for a, b in zip(seq, seq[1:]):
        gap = (_dt(b.when) - _dt(a.when)).total_seconds() / 60
        if gap < 0:
            continue   # 倒挂归 T3
        need = th.intl_transfer_minutes if (a.intl or b.intl) else th.domestic_transfer_minutes
        if 0 <= gap < need:
            out.append(Finding(
                "T1", "high", f"{a.raw_kind}→{b.raw_kind}", a.when,
                f"衔接仅 {gap:.0f} 分钟(<{need}"
                f"{' 国际段' if (a.intl or b.intl) else ''})——误机/误车风险"))
    return out


def check_duplicates(parsed: ParsedInput) -> list[Finding]:
    """T2:同日同类型同城市两段。"""
    by_key: dict[tuple, list[Leg]] = {}
    for l in parsed.legs:
        by_key.setdefault((l.when[:10], l.kind, l.city), []).append(l)
    return [
        Finding("T2", "medium", f"{k[1]} {k[2]}", k[0],
                f"同日同城市 {len(v)} 段{k[1]}——疑似重复预订({', '.join(x.when[11:] for x in v)})")
        for k, v in sorted(by_key.items(), key=lambda kv: kv[0][0]) if len(v) >= 2
    ]


def check_order(parsed: ParsedInput) -> list[Finding]:
    """T3:后一段早于前一段(输入顺序即行程序)。"""
    out: list[Finding] = []
    for a, b in zip(parsed.legs, parsed.legs[1:]):
        gap = (_dt(b.when) - _dt(a.when)).total_seconds() / 60
        if gap < 0:
            out.append(Finding("T3", "high", f"{a.raw_kind}→{b.raw_kind}", b.when,
                               f"时间倒挂:{a.when} 之后是 {b.when}(早 {-gap:.0f} 分钟)——"
                               "核对日期是否填错"))
    return out


def run_all_checks(parsed: ParsedInput,
                   th: Thresholds) -> tuple[list[Finding], dict]:
    findings: list[Finding] = []
    findings += check_transfers(parsed, th)
    findings += check_duplicates(parsed)
    findings += check_order(parsed)
    findings.sort(key=lambda f: (f.rule, f.when, f.target))
    timeline = [f"{l.when} {l.raw_kind} {l.city}".strip() for l in parsed.legs]
    extras = {"timeline": timeline, "legs": len(parsed.legs)}
    return findings, extras
