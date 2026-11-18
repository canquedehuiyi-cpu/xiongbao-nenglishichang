"""
checker.py —— 育儿打卡核对判定核心(纯函数,判定权归代码)

B 族判据(构思方案 §3-A5):
    B1 间隔异常(medium)  相邻两次喂奶间隔低于最小或高于最大阈值
    B2 漏记窗口(low)     清醒时段(7:00-23:00)连续超过最大间隔无任何打卡
    B3 辅食观察期冲突(medium) 两种新辅食首次引入间隔短于观察期(默认 3 天)

行格式:类型词 + 时间(HH:MM / H点半 / 时段前缀)[+量];日期行可写
"11-01" 单独一行,其后打卡归该日;全无日期 = 同一天(取系统日)。
输出是核对提示不是医疗意见;解析不了的行 → uncertain。
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date, timedelta

TODAY = date.today()

_MILK = ("喂奶", "母乳", "奶粉", "奶", "亲喂")
_SOLID = ("辅食", "米糊", "米粉", "果泥", "菜泥", "蛋黄", "肉泥")
_SLEEP = ("睡眠", "睡", "午睡", "夜觉")
_DIAPER = ("换尿布", "尿布", "换裤", "大便", "小便", "便便")
_NEW_FOOD_MARK = ("新加", "新加辅食", "第一次", "首次", "新引入")

_RE_TIME = re.compile(r"(凌晨|早上|上午|中午|下午|傍晚|晚上)?(\d{1,2})[:：点](\d{2})?|(凌晨|早上|上午|中午|下午|傍晚|晚上)(\d{1,2})点(半)?")
_RE_DATE = re.compile(r"(\d{4})[-/年.](\d{1,2})[-/月.](\d{1,2})|(\d{1,2})[-/月](\d{1,2})")
_RE_AMOUNT = re.compile(r"(\d+(?:\.\d+)?)\s*(ml|ML|毫升|分钟)")
_SHIFT = {"凌晨": 0, "早上": 0, "上午": 0, "中午": 12, "下午": 12, "傍晚": 12, "晚上": 12}


@dataclass(frozen=True)
class LogItem:
    kind: str       # milk/solid/sleep/diaper
    raw_kind: str
    date: str       # YYYY-MM-DD
    time: str       # HH:MM
    amount: str     # 原文量(可空)
    new_food: bool  # 新辅食标记
    line_no: int


@dataclass
class ParsedInput:
    items: list[LogItem] = field(default_factory=list)
    uncertain: list[tuple[int, str]] = field(default_factory=list)

    def counts(self) -> dict[str, int]:
        by: dict[str, int] = {}
        for it in self.items:
            by[it.kind] = by.get(it.kind, 0) + 1
        by["uncertain"] = len(self.uncertain)
        return by

    def to_state(self) -> dict:
        return {"items": [it.__dict__ for it in self.items],
                "uncertain": [list(u) for u in self.uncertain]}

    def empty(self) -> bool:
        return not self.items


@dataclass(frozen=True)
class Thresholds:
    min_gap_minutes: int = 120
    max_gap_minutes: int = 300
    allergy_watch_days: int = 3


@dataclass(frozen=True)
class Finding:
    rule: str
    severity: str
    target: str
    when: str
    detail: str


def _classify(line: str) -> str | None:
    for k, words in (("milk", _MILK), ("solid", _SOLID),
                     ("sleep", _SLEEP), ("diaper", _DIAPER)):
        if any(w in line for w in words):
            return k
    return None


def _parse_time(line: str) -> str | None:
    m = _RE_TIME.search(line)
    if not m:
        return None
    if m.group(2):
        h, mi = int(m.group(2)), int(m.group(3) or 0)
        if m.group(1) in _SHIFT and h < 12:
            h += _SHIFT[m.group(1)]
        if mi == 0 and line[m.end():m.end() + 1] == "半":
            mi = 30                       # "3点半" 被 "3点" 抢匹配的补救
    else:
        h, mi = int(m.group(5)), 30 if m.group(6) else 0
        if m.group(4) in _SHIFT and h < 12:
            h += _SHIFT[m.group(4)]
    if 0 <= h <= 23 and 0 <= mi <= 59:
        return f"{h:02d}:{mi:02d}"
    return None


def _parse_amount(line: str) -> str:
    m = _RE_AMOUNT.search(line)
    return m.group(0) if m else ""


def parse_all(text: str = "") -> ParsedInput:
    out = ParsedInput()
    cur_date = TODAY.isoformat()
    for no, ln in enumerate([x.strip() for x in text.splitlines() if x.strip()], 1):
        md = _RE_DATE.search(ln)
        is_pure_date = md and _classify(ln) is None and not _parse_time(ln)
        if is_pure_date:
            if md.group(1):
                cur_date = f"{int(md.group(1)):04d}-{int(md.group(2)):02d}-{int(md.group(3)):02d}"
            else:
                mo, dy = int(md.group(4)), int(md.group(5))
                if 1 <= mo <= 12 and 1 <= dy <= 31:
                    cur_date = f"{TODAY.year:04d}-{mo:02d}-{dy:02d}"
            continue
        kind = _classify(ln)
        tm = _parse_time(ln)
        if not kind or not tm:
            out.uncertain.append((no, ln))
            continue
        out.items.append(LogItem(kind, ln.split()[0] if ln.split() else ln, cur_date,
                                 tm, _parse_amount(ln),
                                 any(w in ln for w in _NEW_FOOD_MARK), no))
    return out


def from_state(state: dict) -> ParsedInput:
    out = ParsedInput()
    for d in state.get("items", []):
        out.items.append(LogItem(**d))
    out.uncertain = [tuple(u) for u in state.get("uncertain", [])]
    return out


def _mins(hhmm: str) -> int:
    h, m = hhmm.split(":")
    return int(h) * 60 + int(m)


def check_milk_gaps(parsed: ParsedInput, th: Thresholds) -> list[Finding]:
    """B1:同日相邻喂奶间隔异常(跨日不做,阈值口径限单日)。"""
    by_date: dict[str, list[LogItem]] = {}
    for it in parsed.items:
        if it.kind == "milk":
            by_date.setdefault(it.date, []).append(it)
    out: list[Finding] = []
    for d, items in sorted(by_date.items()):
        seq = sorted(items, key=lambda x: _mins(x.time))
        for a, b in zip(seq, seq[1:]):
            gap = _mins(b.time) - _mins(a.time)
            if gap < th.min_gap_minutes:
                out.append(Finding("B1", "medium", f"{a.time}~{b.time}", d,
                                   f"喂奶间隔仅 {gap} 分钟(<{th.min_gap_minutes}),确认是否记重"))
            elif gap > th.max_gap_minutes:
                out.append(Finding("B1", "medium", f"{a.time}~{b.time}", d,
                                   f"喂奶间隔 {gap} 分钟(>{th.max_gap_minutes}),确认是否漏记"))
    return out


def check_record_gap(parsed: ParsedInput, th: Thresholds) -> list[Finding]:
    """B2:清醒时段(7:00-23:00)内相邻任意打卡间隔超最大阈值。"""
    by_date: dict[str, list[LogItem]] = {}
    for it in parsed.items:
        by_date.setdefault(it.date, []).append(it)
    out: list[Finding] = []
    for d, items in sorted(by_date.items()):
        seq = sorted((_mins(it.time) for it in items if 420 <= _mins(it.time) <= 1380))
        for a, b in zip(seq, seq[1:]):
            if b - a > th.max_gap_minutes:
                out.append(Finding("B2", "low", f"{a//60:02d}:{a%60:02d}~{b//60:02d}:{b%60:02d}",
                                   d, f"清醒时段 {b - a} 分钟无任何打卡记录,确认是否漏记"))
    return out


def check_solid_watch(parsed: ParsedInput, th: Thresholds) -> list[Finding]:
    """B3:新辅食首次引入间隔 < 观察期(跨日)或同日引入 ≥2 种。"""
    firsts: dict[str, str] = {}   # raw_kind(辅食行专属词) → 首次日期
    for it in sorted(parsed.items, key=lambda x: (x.date, x.time)):
        if it.kind != "solid" or not it.new_food:
            continue
        firsts.setdefault(it.raw_kind, it.date)
    out: list[Finding] = []
    same_day: dict[str, list[str]] = {}
    for kind, d in firsts.items():
        same_day.setdefault(d, []).append(kind)
    for d, kinds in sorted(same_day.items()):
        if len(kinds) >= 2:
            out.append(Finding("B3", "medium", "+".join(kinds), d,
                               f"同日引入 {len(kinds)} 种新辅食,短于 {th.allergy_watch_days} 天观察期——"
                               "过敏源将无法定位,建议一次只加一种"))
    entry_seq = sorted(firsts.items(), key=lambda kv: kv[1])
    for (ka, da), (kb, db) in zip(entry_seq, entry_seq[1:]):
        gap = (date.fromisoformat(db) - date.fromisoformat(da)).days
        if 0 < gap < th.allergy_watch_days:
            out.append(Finding("B3", "medium", f"{ka}+{kb}", f"{da}~{db}",
                               f"两种新辅食引入仅隔 {gap} 天(<{th.allergy_watch_days} 天观察期)"))
    return out


def run_all_checks(parsed: ParsedInput,
                   th: Thresholds) -> tuple[list[Finding], dict]:
    findings: list[Finding] = []
    findings += check_milk_gaps(parsed, th)
    findings += check_record_gap(parsed, th)
    findings += check_solid_watch(parsed, th)
    findings.sort(key=lambda f: (f.rule, f.when, f.target))
    extras = {"kinds": parsed.counts(), "days": len({it.date for it in parsed.items})}
    return findings, extras
