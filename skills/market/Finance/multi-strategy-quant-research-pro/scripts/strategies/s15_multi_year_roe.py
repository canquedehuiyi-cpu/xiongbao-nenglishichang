"""S18 多年度ROE严格校验策略（进阶策略）

算法核心（严格语义）：
基于公开财务摘要数据的**多年度年度 ROE 序列**逐年校验：
1. 最近 S18_YEARS 个完整自然年的年度 ROE **逐年** >= 配置下限（核心通过条件）
   - 严格校验：任一年数据缺失或任一年不达标，均如实不通过；
   - 年度 ROE 取自该自然年报告期最新的 ROE（年报 12-31 优先，缺失用该年最新季报）。
2. 最新报告期 ROE >= 配置下限（S18_REQUIRE_LATEST=True 时计入通过判定，默认开启）
3. 价格在配置周期均线上方（技术面趋势确认，辅助加分，不参与通过判定）

与 S13（单期 ROE 杜邦）的区别：
- S13 仅用最新报告期单一 ROE 值做杜邦拆解（ROE+净利率+负债率+毛利率）；
- S18 强调"多年度持续性"——连续多个财年 ROE 均达标的盈利质量才通过，
  用于排除单年偶然高 ROE 或盈利质量不稳定的标的，是对"白马/优质"更严格的确认。

数据源：日K线 + 东方财富公开财务API多期报表（fundamental.fetch_annual_roe_series，
三市场真实可用：A股 RPT_F10_FINANCE_MAINFINADATA / 港股美股 GMAININDICATOR）。
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from typing import Optional
from .base import make_result, clean_klines, clean_fundamental
from indicators import calc_sma
import config  # noqa: F401

S18_ROE_MIN = getattr(config, "S18_ROE_MIN", 15.0)          # 每年度ROE最低要求(%)
S18_YEARS = getattr(config, "S18_YEARS", 3)                 # 校验的完整自然年数
S18_REQUIRE_LATEST = getattr(config, "S18_REQUIRE_LATEST", True)  # 是否同时要求最新期达标
S18_TECH_MA_PERIOD = getattr(config, "S18_TECH_MA_PERIOD", 20)    # 技术面确认均线周期


def check_s18_multi_year_roe(
    klines: list[dict],
    fundamental: Optional[dict] = None,
    money_flow: Optional[dict] = None,
) -> dict:
    """S18 多年度ROE严格校验策略判定。

    Args:
        klines: 日K线列表
        fundamental: 基本面数据字典，含 roe_history（年度ROE序列）与 roe（最新报告期ROE）
        money_flow: 资金流数据字典（本策略不使用）

    Returns:
        {score: float, reasons: list[str], details: dict}
    """
    reasons = []
    details = {}
    score = 0.0

    klines = clean_klines(klines)

    # roe_history 为列表结构，先于 clean_fundamental 取出（clean 仅数值化标量字段）
    raw_fundamental = fundamental if isinstance(fundamental, dict) else {}
    raw_roe_history = raw_fundamental.get("roe_history") or []
    fundamental = clean_fundamental(fundamental)

    if not klines or len(klines) < 30:
        return make_result(
            code="S18", name="多年度ROE严格校验",
            passed=False,
            score=0,
            reasons=[f"K线数据不足（{len(klines) if klines else 0}条，需≥30）"],
            details={},
        )

    closes = [k["close"] for k in klines]

    latest_roe = fundamental.get("roe")

    # ── 清洗年度 ROE 序列（防御异常/非数值项，口径与数据层一致）──
    annual = []
    for x in raw_roe_history:
        if not isinstance(x, dict):
            continue
        yr = x.get("year")
        roe = x.get("roe")
        if (isinstance(yr, (int, float)) and not isinstance(yr, bool)
                and isinstance(roe, (int, float)) and not isinstance(roe, bool)):
            annual.append({
                "year": int(yr),
                "roe": float(roe),
                "report_date": str(x.get("report_date") or "")[:10],
            })
    # 按年倒序（数据层已倒序，此处再排序保证确定性）
    annual.sort(key=lambda x: x["year"], reverse=True)
    details["annual_roe"] = [
        {"year": a["year"], "roe": a["roe"]} for a in annual
    ]

    needed = annual[:S18_YEARS]
    has_fundamental = bool(annual) or latest_roe is not None
    details["has_fundamental"] = has_fundamental
    details["required_years"] = S18_YEARS
    details["roe_threshold"] = S18_ROE_MIN

    # ── 条件一：最近 S18_YEARS 个自然年年度 ROE 逐年达标（核心通过条件）──
    year_pass = False
    if len(needed) < S18_YEARS:
        reasons.append(
            f"年度ROE数据不足（仅{len(needed)}/{S18_YEARS}个完整自然年），无法严格逐年校验"
        )
    else:
        year_vals = [(a["year"], a["roe"]) for a in needed]
        # 严格校验：逐年均需达标
        all_ok = all(roe >= S18_ROE_MIN for _y, roe in year_vals)
        if all_ok:
            year_pass = True
            years_str = "、".join(
                f"{y}年{roe:.2f}%" for y, roe in year_vals
            )
            reasons.append(f"近{S18_YEARS}个年度ROE逐年达标: {years_str}")
        else:
            fail = [f"{y}年{roe:.2f}%" for y, roe in year_vals if roe < S18_ROE_MIN]
            reasons.append(
                f"近{S18_YEARS}个年度ROE未逐年达标（不达标年度: {'、'.join(fail)}）"
            )
    details["year_pass"] = year_pass

    # ── 条件二：最新报告期 ROE 达标（S18_REQUIRE_LATEST 时计入通过判定）──
    latest_pass = False
    if latest_roe is not None:
        details["latest_roe"] = latest_roe
        if latest_roe >= S18_ROE_MIN:
            latest_pass = True
            reasons.append(f"最新报告期ROE {latest_roe:.2f}% >= {S18_ROE_MIN}%")
        else:
            reasons.append(f"最新报告期ROE {latest_roe:.2f}% < {S18_ROE_MIN}% 不达标")
    else:
        details["latest_roe"] = None
        if S18_REQUIRE_LATEST:
            reasons.append("无最新报告期ROE数据，无法完成最新期校验")

    # ── 条件三：技术面趋势确认（辅助加分，不参与通过判定）──
    tech_pass = False
    ma20 = calc_sma(closes, S18_TECH_MA_PERIOD)
    if ma20 and len(ma20) > 0:
        if closes[-1] > ma20[-1]:
            tech_pass = True
    details["tech_pass"] = tech_pass

    details["conditions"] = {
        "year_pass": year_pass,
        "latest_pass": latest_pass,
        "tech_pass": tech_pass,
    }

    # 评分：年度达标为主（0.6），最新期达标（0.25），技术面确认（0.15）
    if year_pass:
        score += 0.6
    if latest_pass:
        score += 0.25
    if tech_pass:
        score += 0.15

    # 严格通过判定：年度逐年达标 且（按配置）最新期达标
    if S18_REQUIRE_LATEST:
        passed = year_pass and latest_pass
    else:
        passed = year_pass

    return make_result(
        code="S18", name="多年度ROE严格校验",
        passed=passed,
        score=score,
        reasons=reasons,
        details=details,
    )


__all__ = ["check_s18_multi_year_roe"]
