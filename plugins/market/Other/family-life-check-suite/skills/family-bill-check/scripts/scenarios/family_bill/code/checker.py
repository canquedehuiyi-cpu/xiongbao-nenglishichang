"""
checker.py —— 家庭多渠道账单核对判定核心(纯函数,判定权归代码)

F 族判据(构思方案 §3-A6):
    F1 疑似重记(medium)  同成员同日同金额同事项出现 ≥2 笔
    F2 重复会员(high)    同一会员服务同月被两个不同成员各扣一次
    F3 异常大额(medium)  单笔金额 ≥ 大额阈值

行格式:成员 + 日期 + 事项 + 金额[+渠道],字段序不拘;成员代号在
"成员:A/B" 首行声明(缺省把行首 1-2 个字母/汉字当成员)。
服务归一:事项去"会员/连续包月/自动续费/VIP"等方言后做匹配键。
脱敏纪律:卡号/尾号类 token 不使用不回显。
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

_RE_DATE = re.compile(r"(\d{4})[-/年.](\d{1,2})[-/月.](\d{1,2})|(\d{1,2})[-/月](\d{1,2})")
_RE_AMOUNT = re.compile(r"[¥￥]\s*(\d+(?:\.\d{1,2})?)|(\d+(?:\.\d{1,2})?)\s*(?:元|块)")
_RE_MEMBER_DECL = re.compile(r"成员\s*[:：]\s*([A-Za-z一-鿿])(?:\s*[,、/]\s*([A-Za-z一-鿿]))?")
_CHANNELS = ("微信", "支付宝", "云闪付", "京东", "美团", "抖音", "Apple", "AppStore")
_STRIP_WORDS = ("自动续费", "自动续订", "连续包月", "连续包季", "连续包年", "会员", "VIP", "vip")


@dataclass(frozen=True)
class BillLine:
    member: str
    date: str      # YYYY-MM-DD
    service: str   # 归一事项
    raw_service: str
    amount: float
    channel: str
    line_no: int


@dataclass
class ParsedInput:
    members: list[str] = field(default_factory=list)
    lines: list[BillLine] = field(default_factory=list)
    uncertain: list[tuple[int, str]] = field(default_factory=list)

    def counts(self) -> dict[str, int]:
        return {"lines": len(self.lines), "members": len(self.members),
                "uncertain": len(self.uncertain)}

    def to_state(self) -> dict:
        return {"members": self.members,
                "lines": [b.__dict__ for b in self.lines],
                "uncertain": [list(u) for u in self.uncertain]}

    def empty(self) -> bool:
        return not self.lines


@dataclass(frozen=True)
class Thresholds:
    dup_window_minutes: int = 10   # 保留键:同流水中同事项最短合理间隔(月付场景不细分)
    big_amount: float = 1000.0


@dataclass(frozen=True)
class Finding:
    rule: str
    severity: str
    target: str
    when: str
    detail: str


def norm_service(raw: str) -> str:
    key = raw.strip()
    for w in _STRIP_WORDS:
        key = key.replace(w, "")
    return key.strip() or raw.strip()


def _is_member_token(tok: str, declared: list[str]) -> bool:
    return bool(re.fullmatch(r"[A-Za-z一-鿿]{1,2}", tok)) and (
        not declared or tok in declared)


def parse_all(text: str = "") -> ParsedInput:
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    out = ParsedInput()
    declared: list[str] = []
    body: list[tuple[int, str]] = []
    for no, ln in enumerate(lines, 1):
        m = _RE_MEMBER_DECL.search(ln)
        if m and ("成员" in ln) and _RE_DATE.search(ln) is None and _RE_AMOUNT.search(ln) is None:
            declared.extend(x for x in (m.group(1), m.group(2)) if x)
            continue
        body.append((no, ln))
    out.members = declared
    year_hint = 2026
    years = [int(m.group(1)) for _, ln in body
             for m in [_RE_DATE.search(ln)] if m and m.group(1)]
    if years:
        year_hint = min(years)
    for no, ln in body:
        md = _RE_DATE.search(ln)
        ma = _RE_AMOUNT.search(ln)
        if not md or not ma:
            out.uncertain.append((no, ln))
            continue
        if md.group(1):
            date = f"{int(md.group(1)):04d}-{int(md.group(2)):02d}-{int(md.group(3)):02d}"
        else:
            mo, dy = int(md.group(4)), int(md.group(5))
            if not (1 <= mo <= 12 and 1 <= dy <= 31):
                out.uncertain.append((no, ln))
                continue
            date = f"{year_hint:04d}-{mo:02d}-{dy:02d}"
        amount = float(ma.group(1) or ma.group(2))
        if amount <= 0:
            out.uncertain.append((no, ln))
            continue
        rest = _RE_AMOUNT.sub(" ", ln)
        rest = _RE_DATE.sub(" ", rest)
        segs = [s.strip(" ,，;；:：|｜") for s in rest.split()]
        segs = [s for s in segs if s]
        channel = next((c for c in _CHANNELS if c in ln), "")
        segs = [s for s in segs if s != channel]
        member = ""
        if segs and _is_member_token(segs[0], declared):
            member = segs.pop(0)
        elif declared:
            hit = [d for d in declared if d in ln]
            member = hit[0] if hit else ""
        else:
            # 未声明成员:行内孤立的单字母/单汉字 token 视作成员代号
            for idx, s in enumerate(segs):
                if re.fullmatch(r"[A-Za-z]", s):
                    member = segs.pop(idx)
                    break
        if not segs:
            out.uncertain.append((no, ln))
            continue
        raw_service = max(segs, key=len)
        out.lines.append(BillLine(member, date, norm_service(raw_service),
                                  raw_service, amount, channel, no))
    return out


def from_state(state: dict) -> ParsedInput:
    out = ParsedInput()
    out.members = list(state.get("members", []))
    for d in state.get("lines", []):
        out.lines.append(BillLine(**d))
    out.uncertain = [tuple(u) for u in state.get("uncertain", [])]
    return out


def _month(date: str) -> str:
    return date[:7]


def check_dup_same_day(parsed: ParsedInput, th: Thresholds) -> list[Finding]:
    """F1:同成员同日同金额同事项 ≥2 笔。"""
    by_key: dict[tuple, list[BillLine]] = {}
    for b in parsed.lines:
        by_key.setdefault((b.member, b.date, b.service, b.amount), []).append(b)
    return [
        Finding("F1", "medium", f"{k[0] or '未注名'} {k[2]}", k[1],
                f"同日同金额({k[3]:.2f}元)出现 {len(v)} 笔——疑似重复记账,请人工确认")
        for k, v in sorted(by_key.items(), key=lambda kv: (kv[0][1], kv[0][2]))
        if len(v) >= 2
    ]


def check_member_dup(parsed: ParsedInput) -> list[Finding]:
    """F2:同月两个不同成员各扣同一服务。"""
    by_key: dict[tuple[str, str], set[str]] = {}
    for b in parsed.lines:
        if b.member:
            by_key.setdefault((b.service, _month(b.date)), set()).add(b.member)
    return [
        Finding("F2", "high", svc, month,
                f"{'、'.join(sorted(members))} 同月各扣一次——疑似重复购买会员,合计可省一份")
        for (svc, month), members in sorted(by_key.items())
        if len(members) >= 2
    ]


def check_big_amount(parsed: ParsedInput, th: Thresholds) -> list[Finding]:
    return [
        Finding("F3", "medium", b.raw_service, b.date,
                f"{b.member or '未注名'} {b.date} 扣 {b.amount:.2f} 元 ≥ 大额阈值 {th.big_amount:.0f} 元")
        for b in parsed.lines if b.amount >= th.big_amount
    ]


def run_all_checks(parsed: ParsedInput,
                   th: Thresholds) -> tuple[list[Finding], dict]:
    findings: list[Finding] = []
    findings += check_dup_same_day(parsed, th)
    findings += check_member_dup(parsed)
    findings += check_big_amount(parsed, th)
    findings.sort(key=lambda f: (f.rule, f.when, f.target))
    by_member: dict[str, float] = {}
    for b in parsed.lines:
        k = b.member or "未注名"
        by_member[k] = by_member.get(k, 0.0) + b.amount
    extras = {"member_totals": {k: round(v, 2) for k, v in sorted(by_member.items())},
              "total": round(sum(b.amount for b in parsed.lines), 2)}
    return findings, extras
