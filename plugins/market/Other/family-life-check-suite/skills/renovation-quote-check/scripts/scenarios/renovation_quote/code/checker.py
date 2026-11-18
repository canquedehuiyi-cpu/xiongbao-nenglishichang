"""
checker.py —— 装修报价预算核对判定核心(纯函数,判定权归代码)

R 族判据(构思方案 §3-B1):
    R1 漏项(high)        预算表有而报价单无的项目
    R2 增项(medium)      报价单有而预算表无的项目
    R3 单表勾稽(medium)  量×价 ≠ 合计(容差 0.01 元)
    R4 单价偏差(medium)  同项目预算价与报价价偏差超阈值百分比

行格式:项目名[,数量,单位,单价,合计](CSV 优先,≥3 段按 CSV 切;
不足按空格切,数量/单价/合计取行内数字序列)。项目名归一:去空白与
括注。解析不了的行 → uncertain。输入不含个人身份信息。
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

_RE_NUM = re.compile(r"-?\d+(?:\.\d+)?")
_SPLIT = re.compile(r"[,，;；\t]|\s+")


@dataclass(frozen=True)
class QuoteItem:
    name: str       # 归一项目名
    raw_name: str
    qty: float | None
    unit: str
    price: float | None   # 单价
    total: float | None   # 合计
    line_no: int


@dataclass
class ParsedInput:
    budget: list[QuoteItem] = field(default_factory=list)
    quote: list[QuoteItem] = field(default_factory=list)
    uncertain: list[tuple[int, str]] = field(default_factory=list)

    def counts(self) -> dict[str, int]:
        return {"budget": len(self.budget), "quote": len(self.quote),
                "uncertain": len(self.uncertain)}

    def to_state(self) -> dict:
        return {"budget": [i.__dict__ for i in self.budget],
                "quote": [i.__dict__ for i in self.quote],
                "uncertain": [list(u) for u in self.uncertain]}

    def empty(self) -> bool:
        return not self.budget and not self.quote


@dataclass(frozen=True)
class Thresholds:
    unit_price_deviation_pct: float = 20.0


@dataclass(frozen=True)
class Finding:
    rule: str
    severity: str
    target: str
    when: str
    detail: str


def norm_name(raw: str) -> str:
    return re.sub(r"[\s()（）【】\[\]]", "", raw)


def _parse_item(line: str, line_no: int) -> QuoteItem | None:
    parts = [p for p in _SPLIT.split(line) if p.strip()]
    if len(parts) < 2:
        return None
    name_raw = parts[0]
    nums: list[float] = []
    unit = ""
    for p in parts[1:]:
        p = p.strip()
        if re.fullmatch(r"-?\d+(?:\.\d+)?", p):
            nums.append(float(p))
        else:
            m = _RE_NUM.search(p)
            if m and not re.search(r"[一-鿿]", p.replace(m.group(0), "")):
                nums.append(float(m.group(0)))
            elif not nums or re.search(r"[一-鿿]", p):
                unit = p if re.fullmatch(r"[一-鿿㎡m²个台项次张块米平米]", p) or len(p) <= 4 else unit
    if len(nums) == 1:
        return QuoteItem(norm_name(name_raw), name_raw, None, unit or "项",
                         nums[0], None, line_no)
    if len(nums) == 2:
        return QuoteItem(norm_name(name_raw), name_raw, nums[0], unit or "项",
                         nums[1], None, line_no)
    if len(nums) >= 3:
        return QuoteItem(norm_name(name_raw), name_raw, nums[0], unit or "项",
                         nums[1], nums[2], line_no)
    return None


def _parse_section(text: str, out: ParsedInput, attr: str) -> None:
    for no, ln in enumerate([x.strip() for x in text.splitlines() if x.strip()], 1):
        item = _parse_item(ln, no)
        if item is None or not item.name:
            out.uncertain.append((no, ln))
            continue
        getattr(out, attr).append(item)


def parse_all(budget: str = "", quote: str = "") -> ParsedInput:
    out = ParsedInput()
    _parse_section(budget, out, "budget")
    _parse_section(quote, out, "quote")
    return out


def from_state(state: dict) -> ParsedInput:
    out = ParsedInput()
    for key in ("budget", "quote"):
        for d in state.get(key, []):
            getattr(out, key).append(QuoteItem(**d))
    out.uncertain = [tuple(u) for u in state.get("uncertain", [])]
    return out


def check_missing_items(parsed: ParsedInput) -> list[Finding]:
    """R1 + R2:两侧项目名对照。"""
    budget_names = {i.name for i in parsed.budget}
    quote_names = {i.name for i in parsed.quote}
    out: list[Finding] = []
    for i in parsed.budget:
        if i.name not in quote_names:
            out.append(Finding("R1", "high", i.raw_name, "预算有/报价无",
                               "预算表里的项目报价单没报——签约后最典型的加项来源"))
    for i in parsed.quote:
        if i.name not in budget_names:
            out.append(Finding("R2", "medium", i.raw_name, "报价有/预算无",
                               "报价单多出的项目——确认是否真需要,预算外支出"))
    return out


def check_arithmetic(parsed: ParsedInput) -> list[Finding]:
    """R3:量×价≠合计(容差 0.01)。"""
    out: list[Finding] = []
    for side, items in (("预算", parsed.budget), ("报价", parsed.quote)):
        for i in items:
            if i.qty is None or i.price is None or i.total is None:
                continue
            expect = round(i.qty * i.price, 2)
            if abs(expect - i.total) > 0.01:
                out.append(Finding("R3", "medium", i.raw_name, f"{side}单第{i.line_no}行",
                                   f"{i.qty}×{i.price}={expect} ≠ 合计 {i.total}(差 {i.total - expect:+.2f} 元)"))
    return out


def check_price_deviation(parsed: ParsedInput, th: Thresholds) -> list[Finding]:
    """R4:同项目单价偏差超阈值百分比。"""
    budget_map = {i.name: i.price for i in parsed.budget if i.price is not None}
    out: list[Finding] = []
    for i in parsed.quote:
        base = budget_map.get(i.name)
        if base is None or i.price is None or base <= 0:
            continue
        dev = (i.price - base) / base * 100
        if abs(dev) > th.unit_price_deviation_pct:
            out.append(Finding("R4", "medium", i.raw_name, "单价横评",
                               f"预算 {base:.2f} → 报价 {i.price:.2f}({dev:+.1f}%),"
                               f"超 ±{th.unit_price_deviation_pct}% 阈值"))
    return out


def run_all_checks(parsed: ParsedInput,
                   th: Thresholds) -> tuple[list[Finding], dict]:
    findings: list[Finding] = []
    findings += check_missing_items(parsed)
    findings += check_arithmetic(parsed)
    findings += check_price_deviation(parsed, th)
    findings.sort(key=lambda f: (f.rule, f.when, f.target))
    totals = {
        "budget_total": round(sum(i.total or 0 for i in parsed.budget), 2),
        "quote_total": round(sum(i.total or 0 for i in parsed.quote), 2),
    }
    extras = {"totals": totals,
              "items": {"budget": len(parsed.budget), "quote": len(parsed.quote)}}
    return findings, extras
