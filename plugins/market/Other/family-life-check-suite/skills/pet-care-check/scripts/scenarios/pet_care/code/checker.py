"""
checker.py —— 宠物喂养打卡核对判定核心(纯函数,判定权归代码)

P 族判据(构思方案 §3-A7):
    P1 重复喂(high)   同类喂食间隔低于最小阈值(如 ≤4 小时两次正餐)
    P2 喂食间隔异常(low) 相邻喂食间隔超长(>2 倍阈值)提醒确认
    P3 分工不均(low)   全天打卡全是一个成员

行格式:成员代号 + 类型 + 时间[+量],字段序不拘;成员 = 行内 1-2 字
字母/汉字 token(代号,不需要真名)。类型词:喂饭/狗粮/猫粮/喂/零食/罐头/
水/遛/驱虫/疫苗。解析不了的行 → uncertain。
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

_RE_TIME = re.compile(r"(\d{1,2})[:：点](\d{2})?|(\d{1,2})点(半)?")
_FEED = ("喂饭", "喂", "狗粮", "猫粮", "主粮", "罐头", "零食", "冻干", "饭")
_CARE = ("遛", "散步", "驱虫", "疫苗", "洗澡", "剪指甲")
_RE_MEMBER = re.compile(r"(?:^|\s)([A-Za-z甲乙丙丁爸妈爸妈]{1,2})(?:\s|$)")


@dataclass(frozen=True)
class CareItem:
    member: str
    kind: str       # feed/care
    raw_kind: str
    time: str       # HH:MM
    date: str
    line_no: int


@dataclass
class ParsedInput:
    items: list[CareItem] = field(default_factory=list)
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
    min_feed_gap_hours: int = 4


@dataclass(frozen=True)
class Finding:
    rule: str
    severity: str
    target: str
    when: str
    detail: str


def _classify(line: str) -> str | None:
    if any(w in line for w in _CARE):
        return "care"
    if any(w in line for w in _FEED):
        return "feed"
    return None


def _parse_time(line: str) -> str | None:
    m = _RE_TIME.search(line)
    if not m:
        return None
    if m.group(1):
        h, mi = int(m.group(1)), int(m.group(2) or 0)
    else:
        h, mi = int(m.group(3)), 30 if m.group(4) else 0
    if 0 <= h <= 23 and 0 <= mi <= 59:
        return f"{h:02d}:{mi:02d}"
    return None


def parse_all(text: str = "") -> ParsedInput:
    out = ParsedInput()
    today = "2026-11-01"
    for no, ln in enumerate([x.strip() for x in text.splitlines() if x.strip()], 1):
        kind = _classify(ln)
        tm = _parse_time(ln)
        if not kind or not tm:
            out.uncertain.append((no, ln))
            continue
        mm = _RE_MEMBER.search(ln)
        member = mm.group(1) if mm else ""
        raw_kind = next((w for w in (_FEED + _CARE) if w in ln), ln[:6])
        out.items.append(CareItem(member, kind, raw_kind, tm, today, no))
    return out


def from_state(state: dict) -> ParsedInput:
    out = ParsedInput()
    for d in state.get("items", []):
        out.items.append(CareItem(**d))
    out.uncertain = [tuple(u) for u in state.get("uncertain", [])]
    return out


def _mins(hhmm: str) -> int:
    h, m = hhmm.split(":")
    return int(h) * 60 + int(m)


def check_double_feed(parsed: ParsedInput, th: Thresholds) -> list[Finding]:
    """P1:相邻喂食间隔 ≤ 阈值(默认 4h)——全家最容易发生的重复喂。"""
    feeds = sorted((it for it in parsed.items if it.kind == "feed"),
                   key=lambda x: _mins(x.time))
    out: list[Finding] = []
    for a, b in zip(feeds, feeds[1:]):
        gap_h = (_mins(b.time) - _mins(a.time)) / 60
        if gap_h * 60 <= th.min_feed_gap_hours * 60 and gap_h >= 0:
            who = "+".join(sorted({a.member, b.member} - {""})) or "未注名"
            out.append(Finding(
                "P1", "high", f"{a.time}({a.member or '?'})/{b.time}({b.member or '?'})",
                a.time,
                f"间隔 {gap_h:.1f} 小时(≤{th.min_feed_gap_hours})疑似重复喂——"
                f"确认它到底吃了几顿,喂多易出事"))
    return out


def check_long_gap(parsed: ParsedInput, th: Thresholds) -> list[Finding]:
    """P2:相邻喂食间隔 > 2 倍阈值,提醒确认(漏喂或漏记)。"""
    feeds = sorted((it for it in parsed.items if it.kind == "feed"),
                   key=lambda x: _mins(x.time))
    out: list[Finding] = []
    for a, b in zip(feeds, feeds[1:]):
        gap_h = (_mins(b.time) - _mins(a.time)) / 60
        if gap_h > th.min_feed_gap_hours * 2:
            out.append(Finding("P2", "low", f"{a.time}~{b.time}", b.time,
                               f"两餐间隔 {gap_h:.1f} 小时偏长,确认是否漏喂或漏记"))
    return out


def check_chores_balance(parsed: ParsedInput) -> list[Finding]:
    """P3:全天打卡全是一个成员(分工不均提醒)。"""
    members = {it.member for it in parsed.items if it.member}
    if len(parsed.items) >= 3 and len(members) == 1:
        who = members.pop()
        return [Finding("P3", "low", who, "全天",
                        f"今天 {len(parsed.items)} 条打卡全部来自 {who}——"
                        "轮换一下,别让一个人包场")]
    return []


def run_all_checks(parsed: ParsedInput,
                   th: Thresholds) -> tuple[list[Finding], dict]:
    findings: list[Finding] = []
    findings += check_double_feed(parsed, th)
    findings += check_long_gap(parsed, th)
    findings += check_chores_balance(parsed)
    findings.sort(key=lambda f: (f.rule, f.when, f.target))
    by_member: dict[str, int] = {}
    for it in parsed.items:
        k = it.member or "未注名"
        by_member[k] = by_member.get(k, 0) + 1
    extras = {"member_counts": by_member, "kinds": parsed.counts()}
    return findings, extras
