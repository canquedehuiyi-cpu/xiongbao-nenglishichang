# -*- coding: utf-8 -*-
"""质量因子库（9个）。

因子函数签名：factor_name(ctx) -> float | None
方向：正值表示高质量/看多，负值表示低质量/看空。
"""

import math

from ._common import numeric_series, chronological_series


def factor_roe(ctx):
    """ROE(平均)%，高ROE得分高。"""
    return (ctx.get("financial") or {}).get("roe")


def factor_gross_margin(ctx):
    """毛利率%，高毛利率得分高。"""
    return (ctx.get("financial") or {}).get("profit_gross")


def factor_net_margin(ctx):
    """净利率%，高净利率得分高。"""
    return (ctx.get("financial") or {}).get("net_profit_rate")


def factor_debt_ratio_reverse(ctx):
    """资产负债率反向：低负债得分高（50-负债率，50%为中性）。"""
    debt = (ctx.get("financial") or {}).get("debt_ratio")
    if debt is None:
        return None
    return 50 - debt


def factor_operating_cf_quality(ctx):
    """经营现金流质量：每股经营现金流/每股收益，>1说明利润有现金流支撑。"""
    cfps = (ctx.get("financial") or {}).get("operating_cfps")
    eps = (ctx.get("financial") or {}).get("per_eps")
    if cfps is None or eps is None or eps == 0:
        return None
    return cfps / eps


def factor_roe_stability(ctx):
    """ROE稳定性：最近≥3个完整年度ROE标准差的负值（越稳定得分越高），数据不足返回None。"""
    series = numeric_series((ctx.get("financial") or {}).get("roe_history"))
    if len(series) < 3:
        return None
    mean = sum(series) / len(series)
    var = sum((r - mean) ** 2 for r in series) / len(series)
    return -math.sqrt(var)


def factor_margin_expansion(ctx):
    """毛利率扩张：最近≥2个完整年度毛利率的最新-最早期，正值表示毛利率提升（字典序列按年份升序对齐）。"""
    series = chronological_series((ctx.get("financial") or {}).get("gross_margin_history"))
    if len(series) < 2:
        return None
    return series[-1] - series[0]


def factor_asset_quality(ctx):
    """资产质量综合：ROE/毛利率/净利率/负债反向（均为百分比量纲）等权，需至少2个有效。"""
    vals = [v for v in (factor_roe(ctx), factor_gross_margin(ctx),
                        factor_net_margin(ctx), factor_debt_ratio_reverse(ctx))
            if v is not None]
    if len(vals) < 2:
        return None
    return sum(vals) / len(vals)


def factor_earnings_quality(ctx):
    """盈利质量：净利率(%)与利润现金含金量（现金含量超过全额覆盖的百分点）等权，需至少1个有效。"""
    nm = factor_net_margin(ctx)
    cfq = factor_operating_cf_quality(ctx)
    vals = []
    if nm is not None:
        vals.append(nm)
    if cfq is not None:
        # CFPS/EPS=1 为利润全额现金覆盖，超出部分换算为百分点，与净利率同量纲
        vals.append((cfq - 1.0) * 100.0)
    if not vals:
        return None
    return sum(vals) / len(vals)


QUALITY_FACTORS = {
    "roe": (factor_roe, "质量", "净资产收益率"),
    "gross_margin": (factor_gross_margin, "质量", "毛利率"),
    "net_margin": (factor_net_margin, "质量", "净利率"),
    "debt_ratio_reverse": (factor_debt_ratio_reverse, "质量", "资产负债率反向"),
    "operating_cf_quality": (factor_operating_cf_quality, "质量", "经营现金流质量"),
    "roe_stability": (factor_roe_stability, "质量", "ROE稳定性"),
    "margin_expansion": (factor_margin_expansion, "质量", "毛利率扩张"),
    "asset_quality": (factor_asset_quality, "质量", "资产质量综合"),
    "earnings_quality": (factor_earnings_quality, "质量", "盈利质量"),
}
