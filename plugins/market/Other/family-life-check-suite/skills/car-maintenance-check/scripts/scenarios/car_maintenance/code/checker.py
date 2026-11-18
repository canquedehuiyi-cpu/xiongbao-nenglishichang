"""
checker.py —— 车辆保养项目核对判定核心(纯函数,判定权归代码)

V 族判据(构思方案 §3-B2,判据=车型保养手册周期表):
    V1 手册必做(high)   到达周期而建议单未列的项目
    V2 过度保养(medium) 未到周期(超宽限里程)就建议更换的项目
    V3 手册外加价项(low) 手册周期表没有、仅建议单有的项目

行格式(CSV 优先):
    manual:项目,间隔km[,间隔月]         如:机油机滤,5000,6
    advice:项目,上次保养km,当前km[,报价]  如:机油机滤,42000,46500,480
内置规则表是通用周期不是某车型权威;以随车手册为准,工具只做勾稽。
脱敏纪律:车牌/车架号/发动机号不要贴。
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

_SPLIT = re.compile(r"[,，;；\t]|\s+")
_RE_NUM = re.compile(r"\d+(?:\.\d+)?")


@dataclass(frozen=True)
class ManualItem:
    name: str       # 归一项目名
    raw_name: str
    interval_km: float
    interval_month: float | None
    line_no: int


@dataclass(frozen=True)
class AdviceItem:
    name: str
    raw_name: str
    last_km: float
    now_km: float
    price: float | None
    line_no: int


@dataclass
class ParsedInput:
    manual: list[ManualItem] = field(default_factory=list)
    advice: list[AdviceItem] = field(default_factory=list)
    uncertain: list[tuple[int, str]] = field(default_factory=list)

    def counts(self) -> dict[str, int]:
        return {"manual": len(self.manual), "advice": len(self.advice),
                "uncertain": len(self.uncertain)}

    def to_state(self) -> dict:
        return {"manual": [m.__dict__ for m in self.manual],
                "advice": [a.__dict__ for a in self.advice],
                "uncertain": [list(u) for u in self.uncertain]}

    def empty(self) -> bool:
        return not self.manual and not self.advice


@dataclass(frozen=True)
class Thresholds:
    mileage_forgive_km: float = 500.0


@dataclass(frozen=True)
class Finding:
    rule: str
    severity: str
    target: str
    when: str
    detail: str


def norm_name(raw: str) -> str:
    return re.sub(r"[\s()（）【】\[\]/]", "", raw)


def _nums(parts: list[str]) -> list[float]:
    out: list[float] = []
    for p in parts:
        m = _RE_NUM.fullmatch(p.strip())
        if m:
            out.append(float(p))
    return out


def parse_all(manual: str = "", advice: str = "") -> ParsedInput:
    out = ParsedInput()
    for no, ln in enumerate([x.strip() for x in manual.splitlines() if x.strip()], 1):
        parts = [p for p in _SPLIT.split(ln) if p.strip()]
        nums = _nums(parts[1:])
        if not parts or not nums:
            out.uncertain.append((no, ln))
            continue
        out.manual.append(ManualItem(norm_name(parts[0]), parts[0], nums[0],
                                     nums[1] if len(nums) > 1 else None, no))
    for no, ln in enumerate([x.strip() for x in advice.splitlines() if x.strip()], 1):
        parts = [p for p in _SPLIT.split(ln) if p.strip()]
        nums = _nums(parts[1:])
        if not parts or len(nums) < 2:
            out.uncertain.append((no, ln))
            continue
        price = nums[2] if len(nums) > 2 else None
        out.advice.append(AdviceItem(norm_name(parts[0]), parts[0],
                                     nums[0], nums[1], price, no))
    return out


def from_state(state: dict) -> ParsedInput:
    out = ParsedInput()
    for key in ("manual", "advice"):
        cls = ManualItem if key == "manual" else AdviceItem
        for d in state.get(key, []):
            getattr(out, key).append(cls(**d))
    out.uncertain = [tuple(u) for u in state.get("uncertain", [])]
    return out


def check_must_do(parsed: ParsedInput, th: Thresholds) -> list[Finding]:
    """V1:到达周期(超出宽限)而建议单未列。"""
    advice_names = {a.name for a in parsed.advice}
    now_km = max((a.now_km for a in parsed.advice), default=None)
    out: list[Finding] = []
    if now_km is None:
        return out
    for m in parsed.manual:
        if m.name in advice_names:
            continue
        hit = next((a for a in parsed.advice if a.name == m.name), None)
        # 建议单没列该项目:用建议单最大当前里程估算距上次更换
        last = max((a.last_km for a in parsed.advice), default=now_km - m.interval_km)
        since = now_km - last
        if since >= m.interval_km - th.mileage_forgive_km:
            out.append(Finding("V1", "high", m.raw_name, f"当前 {now_km:.0f} km",
                               f"已行驶 {since:.0f} km ≥ 手册周期 {m.interval_km:.0f} km,"
                               "但建议单没列——手册必做项漏了"))
    return out


def check_over_maintenance(parsed: ParsedInput, th: Thresholds) -> list[Finding]:
    """V2:建议单列了但未到周期(含宽限)。"""
    manual_map = {m.name: m for m in parsed.manual}
    out: list[Finding] = []
    for a in parsed.advice:
        m = manual_map.get(a.name)
        if m is None:
            continue
        since = a.now_km - a.last_km
        if since < m.interval_km - th.mileage_forgive_km:
            out.append(Finding("V2", "medium", a.raw_name, f"当前 {a.now_km:.0f} km",
                               f"仅行驶 {since:.0f} km < 手册周期 {m.interval_km:.0f} km"
                               f"(宽限 {th.mileage_forgive_km:.0f} km)——过度保养,可以延后"))
    return out


def check_extra_items(parsed: ParsedInput) -> list[Finding]:
    """V3:手册周期表没有的项目(常见加价项:发动机清洗/油路/空调杀菌等)。"""
    manual_names = {m.name for m in parsed.manual}
    return [
        Finding("V3", "low", a.raw_name, f"当前 {a.now_km:.0f} km",
                "手册周期表没有该项目——加价推销高发区,非必做,按需决定"
                + (f"(报价 {a.price:.0f} 元)" if a.price else ""))
        for a in parsed.advice if a.name not in manual_names
    ]


def run_all_checks(parsed: ParsedInput,
                   th: Thresholds) -> tuple[list[Finding], dict]:
    findings: list[Finding] = []
    findings += check_must_do(parsed, th)
    findings += check_over_maintenance(parsed, th)
    findings += check_extra_items(parsed)
    findings.sort(key=lambda f: (f.rule, f.when, f.target))
    extras = {"manual_items": len(parsed.manual), "advice_items": len(parsed.advice),
              "current_km": max((a.now_km for a in parsed.advice), default=0)}
    return findings, extras
