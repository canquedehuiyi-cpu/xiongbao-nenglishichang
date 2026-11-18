"""
checker.py —— 会员订阅体检判定核心(纯函数,判定权归代码)

S 族判据(构思方案 §3-A2):
    S1 续费形态标记(info) 扣费名含自动续费方言(连续包月/自动续费/自动续订…),列全景
    S2 重复会员(high)    同一服务同月被扣 ≥2 次(双渠道或同渠道重复)
    S3 涨价检测(medium)  同一服务相邻月扣费上涨超容差(默认 0:涨 1 分也算,列涨幅)
    S4 僵尸订阅提醒(low) 同一服务连续扣费 ≥N 个月(默认 3)——"还在用吗"提醒,不是结论
    S5 大额扣费(medium)  单笔扣费 ≥ 大额阈值(默认 200 元)

本模块不碰 IO、不碰引擎:输入字符串,输出结构化事实。
坏行 → UncertainLine,不臆造结论。脱敏纪律:插件不消费卡号/姓名字段,
解析时遇到疑似卡号/姓名 token 不使用也不回显(原行只在 UNCERTAIN 清单出现)。
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

# ---------------------------------------------------------------- 阈值(默认在代码)

DEFAULT_PRICE_TOLERANCE = 0.0    # S3:涨幅超过该值(元)算涨价
DEFAULT_ZOMBIE_MONTHS = 3        # S4:连续扣费月数下限
DEFAULT_BIG_AMOUNT = 200.0       # S5:大额阈值(元)

# S1 自动续费方言(出现在服务名/摘要里即标记)
_RENEWAL_DIALECT = ("连续包月", "连续包季", "连续包年", "自动续费", "自动续订", "续费")

# 服务名归一:去掉这些词后做匹配键(同一家"腾讯视频VIP连续包月"与"腾讯视频会员"归一)
_STRIP_WORDS = (
    "自动续费", "自动续订", "连续包月", "连续包季", "连续包年",
    "会员", "VIP", "vip", "超级影视", "联合会员",
)
# 渠道方言
_CHANNEL_WORDS = ("微信", "支付宝", "Apple", "App Store", "苹果", "云闪付", "京东", "美团", "抖音")

_RE_DATE = re.compile(r"(\d{4})[-/年.](\d{1,2})[-/月.](\d{1,2})日?|(\d{1,2})[-/月](\d{1,2})日?")
_RE_AMOUNT = re.compile(r"[¥￥]?\s*(\d+(?:\.\d{1,2})?)\s*(?:元|块)?")

# ---------------------------------------------------------------- 数据模型


@dataclass(frozen=True)
class Charge:
    """一笔扣费:日期 + 服务名(归一键) + 金额 + 渠道(可空)。"""

    date: str      # YYYY-MM-DD
    service: str   # 归一后的服务名(匹配键)
    raw_service: str  # 原文服务名(报告展示用)
    amount: float
    channel: str   # 可空
    line_no: int


@dataclass
class ParsedInput:
    charges: list[Charge] = field(default_factory=list)
    uncertain: list[tuple[int, str]] = field(default_factory=list)  # (行号, 原文)


@dataclass(frozen=True)
class Thresholds:
    price_tolerance: float = DEFAULT_PRICE_TOLERANCE
    zombie_months: int = DEFAULT_ZOMBIE_MONTHS
    big_amount: float = DEFAULT_BIG_AMOUNT


@dataclass(frozen=True)
class Finding:
    rule: str
    severity: str
    service: str
    month: str  # YYYY-MM 或跨度
    detail: str


# ---------------------------------------------------------------- 解析


def _norm_date(token: str, year_hint: int) -> str | None:
    m = _RE_DATE.search(token)
    if not m:
        return None
    if m.group(1):
        y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
    else:
        y, mo, d = year_hint, int(m.group(4)), int(m.group(5))
    if not (1 <= mo <= 12 and 1 <= d <= 31):
        return None
    return f"{y:04d}-{mo:02d}-{d:02d}"


_RE_AMOUNT_MARKED_PRE = re.compile(r"[¥￥]\s*(\d+(?:\.\d{1,2})?)")       # ¥25
_RE_AMOUNT_MARKED_POST = re.compile(r"(\d+(?:\.\d{1,2})?)\s*(?:元|块)")  # 25元


def _norm_amount(token: str) -> float | None:
    """金额:优先带货币标记(¥25 / 25元);无标记时剔除日期后取首个正数。"""
    m = _RE_AMOUNT_MARKED_PRE.search(token) or _RE_AMOUNT_MARKED_POST.search(token)
    if m:
        v = float(m.group(1))
        return v if v > 0 else None
    stripped = _RE_DATE.sub(" ", token)   # 2026-10-12 里的 2026 不是金额
    m = _RE_AMOUNT.search(stripped)
    if not m:
        return None
    v = float(m.group(1))
    return v if v > 0 else None


def norm_service(raw: str) -> str:
    """服务名归一:去续费方言与会员后缀词,剩余做匹配键。"""
    key = raw.strip()
    for w in _STRIP_WORDS:
        key = key.replace(w, "")
    return key.strip() or raw.strip()


def _detect_channel(line: str) -> str:
    for ch in _CHANNEL_WORDS:
        if ch in line:
            return "Apple" if ch in ("Apple", "App Store", "苹果") else ch
    return ""


def parse_line(line: str, line_no: int, year_hint: int, out: ParsedInput) -> None:
    """一行流水:日期 + 金额 + 剩余为服务名(渠道顺带识别)。字段序不拘。"""
    date = _norm_date(line, year_hint)
    amount = _norm_amount(line)
    if not date or amount is None:
        out.uncertain.append((line_no, line))
        return
    # 服务名 = 去掉日期 token 与金额 token 后的最长剩余段
    rest = _RE_AMOUNT_MARKED_PRE.sub(" ", line)
    rest = _RE_AMOUNT_MARKED_POST.sub(" ", rest)
    rest = _RE_DATE.sub(" ", rest)
    if _RE_AMOUNT_MARKED_PRE.search(line) or _RE_AMOUNT_MARKED_POST.search(line):
        pass  # 金额已带标记剔除;无标记金额由下方通用剔除兜底
    else:
        rest = _RE_AMOUNT.sub(" ", rest, count=1)
    segs = [s.strip(" ,，;；:：|｜") for s in rest.split()]
    segs = [s for s in segs if s]
    channel = _detect_channel(line)
    if channel:
        segs = [s for s in segs if s != channel]
    if not segs:
        out.uncertain.append((line_no, line))
        return
    raw_service = max(segs, key=len)
    out.charges.append(Charge(date, norm_service(raw_service), raw_service,
                              amount, channel, line_no))


def parse_all(text: str) -> ParsedInput:
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    year_hint = 2026  # 缺年日期的基准年;有完整日期时取输入中最早年份
    years = [int(m.group(1)) for ln in lines
             for m in [_RE_DATE.search(ln)] if m and m.group(1)]
    if years:
        year_hint = min(years)
    out = ParsedInput()
    for no, ln in enumerate(lines, 1):
        parse_line(ln, no, year_hint, out)
    return out


# ---------------------------------------------------------------- 判据


def _month(date: str) -> str:
    return date[:7]


def check_renewal_marks(parsed: ParsedInput) -> list[Finding]:
    """S1:含续费方言的扣费,聚合成一张"自动续费中"全景清单(info 级)。"""
    hits: dict[str, list[Charge]] = {}
    for c in parsed.charges:
        if any(w in c.raw_service for w in _RENEWAL_DIALECT):
            hits.setdefault(c.service, []).append(c)
    return [
        Finding("S1", "info", svc,
                f"{min(_month(c.date) for c in cs)}~{max(_month(c.date) for c in cs)}",
                f"自动续费形态扣费 {len(cs)} 笔(最近 {_fmt_charge(cs[-1])})——确认还在用")
        for svc, cs in sorted(hits.items())
    ]


def check_duplicate_month(parsed: ParsedInput) -> list[Finding]:
    """S2:同一服务同月扣 ≥2 次(重复会员/重复扣费)。"""
    by_key: dict[tuple[str, str], list[Charge]] = {}
    for c in parsed.charges:
        by_key.setdefault((c.service, _month(c.date)), []).append(c)
    out: list[Finding] = []
    for (svc, month), cs in sorted(by_key.items()):
        if len(cs) < 2:
            continue
        channels = {c.channel for c in cs if c.channel}
        total = sum(c.amount for c in cs)
        chan_txt = "、".join(sorted(channels)) if channels else "渠道未标注"
        sev = "high"
        out.append(Finding(
            "S2", sev, svc, month,
            f"同月扣费 {len(cs)} 笔共 {total:.2f} 元({chan_txt})——"
            + ("双渠道重复购买会员" if len(channels) >= 2 else "重复扣费,请人工确认")))
    return out


def check_price_rise(parsed: ParsedInput, th: Thresholds) -> list[Finding]:
    """S3:同一服务相邻月单笔金额上涨超容差(取每月第一笔做基准,同月多笔记 S2)。"""
    by_key: dict[str, dict[str, float]] = {}
    for c in parsed.charges:
        by_key.setdefault(c.service, {}).setdefault(_month(c.date), c.amount)
    out: list[Finding] = []
    for svc, months in sorted(by_key.items()):
        seq = sorted(months.items())
        for (m1, a1), (m2, a2) in zip(seq, seq[1:]):
            if a2 - a1 > th.price_tolerance:
                out.append(Finding(
                    "S3", "medium", svc, m2,
                    f"{m1} {a1:.2f} 元 → {m2} {a2:.2f} 元,"
                    f"涨 {a2 - a1:.2f} 元/月"))
    return out


def check_zombie(parsed: ParsedInput, th: Thresholds) -> list[Finding]:
    """S4:同一服务连续扣费 ≥N 个月(提醒不是结论)。"""
    by_key: dict[str, set[str]] = {}
    for c in parsed.charges:
        by_key.setdefault(c.service, set()).add(_month(c.date))
    out: list[Finding] = []
    for svc, months in sorted(by_key.items()):
        seq = _consecutive(sorted(months))
        for span in seq:
            if len(span) >= th.zombie_months:
                out.append(Finding(
                    "S4", "low", svc, f"{span[0]}~{span[-1]}",
                    f"已连续 {len(span)} 个月扣费——还在用吗?(提醒,非结论)"))
    return out


def _consecutive(months: list[str]) -> list[list[str]]:
    """把 YYYY-MM 列表切成连续段(跨年按月份差算)。"""
    def idx(m: str) -> int:
        y, mm = m.split("-")
        return int(y) * 12 + int(mm)
    spans: list[list[str]] = []
    for m in months:
        if not spans or idx(m) != idx(spans[-1][-1]) + 1:
            spans.append([m])
        else:
            spans[-1].append(m)
    return spans


def check_big_amount(parsed: ParsedInput, th: Thresholds) -> list[Finding]:
    """S5:单笔大额扣费。"""
    return [
        Finding("S5", "medium", c.raw_service, _month(c.date),
                f"{c.date} 扣 {c.amount:.2f} 元 ≥ 大额阈值 {th.big_amount:.0f} 元")
        for c in parsed.charges if c.amount >= th.big_amount
    ]


def _fmt_charge(c: Charge) -> str:
    chan = f"/{c.channel}" if c.channel else ""
    return f"{c.date} {c.amount:.2f}元{chan}"


def run_all_checks(parsed: ParsedInput,
                   th: Thresholds) -> tuple[list[Finding], dict[str, float]]:
    """S1~S5 全链。返回 (findings, 服务×月度总额聚合)。"""
    findings: list[Finding] = []
    findings += check_renewal_marks(parsed)
    findings += check_duplicate_month(parsed)
    findings += check_price_rise(parsed, th)
    findings += check_zombie(parsed, th)
    findings += check_big_amount(parsed, th)
    findings.sort(key=lambda f: (f.rule, f.service, f.month))
    monthly: dict[str, float] = {}
    for c in parsed.charges:
        monthly[c.service] = monthly.get(c.service, 0.0) + c.amount
    return findings, monthly
