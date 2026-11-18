"""
checker.py —— 孩子作业清单核对判定核心(纯函数,判定权归代码)

H 族判据(构思方案 §3-A4):
    H1 缺漏(high)        要求有而完成清单无对应项
    H2 易漏类型(medium)   完成项属于听读/背诵/签字/打卡类——提示家长当面确认
    H3 明日带物(low)      要求中含"明天带"类事项单独列清单

匹配算法(确定性):要求行与完成行各自归一(去标点/空白/前缀动词),
要求行中的实质词段(≥2 字)命中任一完成行 → 已完成;全不中 → H1。
解析不了的行 → uncertain,不臆造。
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

_EASY_MISS = ("听读", "朗读", "背诵", "签字", "打卡", "阅读")
# 完成行易漏判定:类型词常被简写("背完了/签了字"),按动词首字识别
_EASY_MISS_HEADS = frozenset(w[0] for w in _EASY_MISS)
_TOMORROW_CARRY = ("明天带", "明日带", "带回家", "带一个", "带好")

_STRIP = re.compile(r"[\s,，。.;；:：、!！?？()()【】\[\]\"'‘’“”~-]")
_PREFIX = ("已完成", "完成了", "完成", "已做", "做了", "做好", "已", "做了:")


@dataclass(frozen=True)
class Entry:
    raw: str
    norm: str          # 归一文本(去标点空白)
    subject: str       # 科目(可空)
    easy_miss: bool    # 命中易漏类型词
    carry: bool        # 明日带物
    line_no: int


@dataclass
class ParsedInput:
    plan: list[Entry] = field(default_factory=list)
    log: list[Entry] = field(default_factory=list)
    uncertain: list[tuple[int, str]] = field(default_factory=list)

    def counts(self) -> dict[str, int]:
        return {"plan": len(self.plan), "log": len(self.log),
                "uncertain": len(self.uncertain)}

    def to_state(self) -> dict:
        return {"plan": [e.__dict__ for e in self.plan],
                "log": [e.__dict__ for e in self.log],
                "uncertain": [list(u) for u in self.uncertain]}

    def empty(self) -> bool:
        return not self.plan and not self.log


@dataclass(frozen=True)
class Thresholds:
    """无外置阈值;保留契约位(rules-config 可空)。"""


@dataclass(frozen=True)
class Finding:
    rule: str
    severity: str
    target: str
    when: str
    detail: str


_SUBJECTS = ("语文", "数学", "英语", "科学", "道德", "体育", "美术", "音乐", "书法")


def _parse_entry(line: str, line_no: int) -> Entry:
    norm = _STRIP.sub("", line)
    for p in _PREFIX:
        if norm.startswith(p):
            norm = norm[len(p):]
            break
    subject = next((s for s in _SUBJECTS if norm.startswith(s) or line.startswith(s + ":")
                    or line.startswith(s + ":")), "")
    if subject:
        norm = norm[len(subject):] if norm.startswith(subject) else norm
    return Entry(line if len(line) <= 40 else line[:38] + "…", norm, subject,
                 any(w in line for w in _EASY_MISS)
                 or any(h in line for h in _EASY_MISS_HEADS),
                 any(w in line for w in _TOMORROW_CARRY), line_no)


def _split_terms(norm: str) -> tuple[list[str], list[str]]:
    """norm 切分 → (类型词, 内容词段)。科目词剔除(完成行常不写科目);
    易漏类型词整体摘出;剩余按非中文段切开,≥2 字段为内容词。"""
    kinds: list[str] = []
    rest = norm
    for w in sorted(list(_SUBJECTS) + list(_EASY_MISS), key=len, reverse=True):
        if w in rest:
            if w in _EASY_MISS:
                kinds.append(w)
            rest = rest.replace(w, "|", 1)
    contents: list[str] = []
    for seg in re.split(r"[|0-9a-zA-Z]+", rest):
        if len(seg) >= 2:
            contents.append(seg)
    return kinds, contents


def _matches(plan_e: Entry, log: list[Entry]) -> bool:
    """双通道:类型词全部动词首字命中,或任一内容词前 2 字命中。"""
    kinds, contents = _split_terms(plan_e.norm)
    for e in log:
        if kinds and all(k[0] in e.norm for k in kinds):
            return True
        if any(c[:2] in e.norm for c in contents):
            return True
        if not kinds and not contents and bool(plan_e.norm) and plan_e.norm in e.norm:
            return True
    return False


def parse_all(plan: str = "", log: str = "") -> ParsedInput:
    out = ParsedInput()
    for no, ln in enumerate([x.strip() for x in plan.splitlines() if x.strip()], 1):
        out.plan.append(_parse_entry(ln, no))
    for no, ln in enumerate([x.strip() for x in log.splitlines() if x.strip()], 1):
        out.log.append(_parse_entry(ln, no))
    return out


def from_state(state: dict) -> ParsedInput:
    out = ParsedInput()
    for key in ("plan", "log"):
        for d in state.get(key, []):
            getattr(out, key).append(Entry(**d))
    out.uncertain = [tuple(u) for u in state.get("uncertain", [])]
    return out


def check_missing(parsed: ParsedInput) -> list[Finding]:
    """H1:要求无完成对应。"""
    out = []
    for e in parsed.plan:
        if not _matches(e, parsed.log):
            out.append(Finding("H1", "high", e.raw, f"要求行{e.line_no}",
                               "要求项在完成清单中没有对应记录——疑似漏做或漏报"))
    return out


def check_easy_miss(parsed: ParsedInput) -> list[Finding]:
    """H2:完成项中属易漏类型,提示当面确认。"""
    return [Finding("H2", "info", e.raw, f"完成行{e.line_no}",
                    "听读/背诵/签字/打卡类最易\"口头说做了\"——建议当面复核")
            for e in parsed.log if e.easy_miss]


def check_carry(parsed: ParsedInput) -> list[Finding]:
    """H3:明日带物清单。"""
    return [Finding("H3", "low", e.raw, f"要求行{e.line_no}", "明日带物项——今晚整理书包时放进")
            for e in parsed.plan if e.carry]


def run_all_checks(parsed: ParsedInput,
                   th: Thresholds) -> tuple[list[Finding], dict]:
    findings: list[Finding] = []
    findings += check_missing(parsed)
    findings += check_easy_miss(parsed)
    findings += check_carry(parsed)
    findings.sort(key=lambda f: (f.rule, f.when, f.target))
    extras = {"plan": len(parsed.plan), "log": len(parsed.log)}
    return findings, extras
