"""风险管理模块：ATR 止损止盈位计算与组合风险指标。

基于真实日K线的 ATR（平均真实波幅）计算每只标的的止损位、止盈位与波动率，
为入选标的提供可执行的风险参考（非投资建议，不构成收益承诺）。

止损止盈口径：
- 止损位 = 最新收盘价 - STOP_ATR_MULTIPLIER × ATR(14)（默认 2 倍 ATR）
- 止盈位 = 最新收盘价 + TAKE_PROFIT_ATR_MULTIPLIER × ATR(14)（默认 3 倍 ATR，盈亏比 1.5:1）
- 波动率 = ATR(14) / 最新收盘价（年化波动参考）

组合风险指标：
- 行业分散度：入选标的的行业分布（行业数 / 总标的数）
- 建议持仓数：基于分散度的参考区间
"""

from typing import Optional
from indicators import calc_atr

STOP_ATR_MULTIPLIER = 2.0
TAKE_PROFIT_ATR_MULTIPLIER = 3.0
ATR_PERIOD = 14


def calc_atr_stops(klines: list[dict]) -> Optional[dict]:
    """计算单只标的的 ATR 止损止盈位。

    Args:
        klines: 日K线列表（需 >= ATR_PERIOD+1 根）

    Returns:
        dict: {stop_loss, take_profit, atr, volatility_pct, risk_reward_ratio} 或 None（数据不足）
    """
    if not klines or len(klines) < ATR_PERIOD + 1:
        return None

    atr_series = calc_atr(klines, ATR_PERIOD)
    atr = atr_series[-1] if atr_series else 0
    if not atr or atr <= 0:
        return None

    close = klines[-1].get("close", 0) or 0
    if close <= 0:
        return None

    stop_loss = round(close - STOP_ATR_MULTIPLIER * atr, 2)
    take_profit = round(close + TAKE_PROFIT_ATR_MULTIPLIER * atr, 2)
    volatility = round(atr / close, 4)
    risk_per_unit = close - stop_loss
    reward_per_unit = take_profit - close
    rr_ratio = round(reward_per_unit / risk_per_unit, 2) if risk_per_unit > 0 else None

    return {
        "stop_loss": stop_loss,
        "take_profit": take_profit,
        "atr": round(atr, 2),
        "atr_period": ATR_PERIOD,
        "stop_multiplier": STOP_ATR_MULTIPLIER,
        "take_profit_multiplier": TAKE_PROFIT_ATR_MULTIPLIER,
        "volatility_pct": f"{volatility * 100:.2f}%",
        "volatility": volatility,
        "risk_reward_ratio": rr_ratio,
    }


def portfolio_risk_metrics(results: list[dict]) -> dict:
    """计算组合层面的风险指标（行业分散度等）。

    Args:
        results: 入选标的列表（每只需含 industry 字段）

    Returns:
        dict: {industry_count, industry_diversity, top_industry, top_industry_count,
               suggested_position_min, suggested_position_max}
    """
    if not results:
        return {"industry_count": 0, "industry_diversity": 0, "total": 0}

    industries = {}
    for r in results:
        ind = r.get("industry") or "未知"
        industries[ind] = industries.get(ind, 0) + 1

    total = len(results)
    industry_count = len(industries)
    diversity = round(industry_count / total, 4) if total > 0 else 0
    top_industry = max(industries, key=industries.get) if industries else ""
    top_count = industries.get(top_industry, 0)

    # 建议持仓数：行业分散度高时可适当集中，分散度低时需更分散
    if diversity >= 0.7:
        pos_min, pos_max = 8, 15
    elif diversity >= 0.4:
        pos_min, pos_max = 10, 20
    else:
        pos_min, pos_max = 15, 30

    return {
        "total": total,
        "industry_count": industry_count,
        "industry_diversity": diversity,
        "industry_diversity_pct": f"{diversity * 100:.1f}%",
        "top_industry": top_industry,
        "top_industry_count": top_count,
        "top_industry_concentration": f"{round(top_count / total * 100, 1)}%" if total > 0 else "0%",
        "suggested_position_min": pos_min,
        "suggested_position_max": pos_max,
        "industry_distribution": industries,
    }


__all__ = ["calc_atr_stops", "portfolio_risk_metrics"]
