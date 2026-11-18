# -*- coding: utf-8 -*-
"""成长因子库（6个）。

因子函数签名：factor_name(ctx) -> float | None
方向：正值表示高成长/看多，负值表示低成长/看空。
"""

import math

from ._common import numeric_series, chronological_series


def factor_revenue_growth(ctx):
    """营收同比增速%，高增速得分高。"""
    return (ctx.get("financial") or {}).get("revenue_growth")


def factor_profit_growth(ctx):
    """净利润同比增速%，高增速得分高。"""
    return (ctx.get("financial") or {}).get("net_profit_growth")


def factor_growth_acceleration(ctx):
    """成长加速：最近≥2期净利润增速的最新-最早期，正值表示加速（字典序列按年份升序对齐）。"""
    series = chronological_series((ctx.get("financial") or {}).get("profit_growth_history"))
    if len(series) < 2:
        return None
    return series[-1] - series[0]


def factor_growth_stability(ctx):
    """成长稳定性：最近≥3期增速标准差的负值，越稳定得分越高。"""
    series = numeric_series((ctx.get("financial") or {}).get("profit_growth_history"))
    if len(series) < 3:
        return None
    mean = sum(series) / len(series)
    var = sum((g - mean) ** 2 for g in series) / len(series)
    return -math.sqrt(var)


def factor_roe_change(ctx):
    """ROE变化：最近≥2期ROE的最新-最早期，正值表示ROE提升（字典序列按年份升序对齐）。"""
    series = chronological_series((ctx.get("financial") or {}).get("roe_history"))
    if len(series) < 2:
        return None
    return series[-1] - series[0]


def factor_growth_composite(ctx):
    """成长综合：营收增速+利润增速 等权，需至少1个有效。"""
    vals = [v for v in (factor_revenue_growth(ctx), factor_profit_growth(ctx)) if v is not None]
    if not vals:
        return None
    return sum(vals) / len(vals)


GROWTH_FACTORS = {
    "revenue_growth": (factor_revenue_growth, "成长", "营收增速"),
    "profit_growth": (factor_profit_growth, "成长", "净利润增速"),
    "growth_acceleration": (factor_growth_acceleration, "成长", "成长加速"),
    "growth_stability": (factor_growth_stability, "成长", "成长稳定性"),
    "roe_change": (factor_roe_change, "成长", "ROE变化"),
    "growth_composite": (factor_growth_composite, "成长", "成长综合"),
}
