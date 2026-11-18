# -*- coding: utf-8 -*-
"""价值因子库（9个）。

因子函数签名：factor_name(ctx) -> float | None
ctx 包含 valuation（估值）、financial（财务）等数据。
方向：正值表示低估/看多，负值表示高估/看空。
"""


def factor_ep(ctx):
    """盈利收益率 EP = 1/PE(TTM)，低PE得分高。"""
    pe = (ctx.get("valuation") or {}).get("pe_ttm")
    if pe is None or pe <= 0:
        return None
    return 1.0 / pe * 100


def factor_bp(ctx):
    """账面市值比 BP = 1/PB，低PB得分高。"""
    pb = (ctx.get("valuation") or {}).get("pb")
    if pb is None or pb <= 0:
        return None
    return 1.0 / pb


def factor_sp(ctx):
    """销售收益率 SP = 1/PS(TTM)，低PS得分高。"""
    ps = (ctx.get("valuation") or {}).get("ps_ttm")
    if ps is None or ps <= 0:
        return None
    return 1.0 / ps


def factor_dividend_yield(ctx):
    """股息率%，高股息得分高。"""
    return (ctx.get("valuation") or {}).get("dividend_yield")


def factor_pe_reverse(ctx):
    """PE反向：PE越低得分越高（标准化：50-PE，PE=50为中性）。"""
    pe = (ctx.get("valuation") or {}).get("pe_ttm")
    if pe is None or pe <= 0:
        return None
    return 50 - pe


def factor_pb_reverse(ctx):
    """PB反向：PB越低得分越高（标准化：5-PB，PB=5为中性）。"""
    pb = (ctx.get("valuation") or {}).get("pb")
    if pb is None or pb <= 0:
        return None
    return 5 - pb


def factor_pcf_reverse(ctx):
    """市现率反向：PCF越低越好（用每股经营现金流/价格近似）。"""
    cfps = (ctx.get("financial") or {}).get("operating_cfps")
    klines = ctx.get("klines") or []
    if cfps is None or not klines:
        return None
    price = klines[-1].get("close", 0)
    if price == 0:
        return None
    return cfps / price * 100


def factor_peg_reverse(ctx):
    """PEG反向：PEG=PE/利润增速，越低越好（增速>0时有效）。"""
    pe = (ctx.get("valuation") or {}).get("pe_ttm")
    growth = (ctx.get("financial") or {}).get("net_profit_growth")
    if pe is None or growth is None or growth <= 0 or pe <= 0:
        return None
    peg = pe / growth
    return 1.0 / peg if peg > 0 else None


def factor_value_composite(ctx):
    """价值综合：盈利收益率/账面市值比/销售收益率/股息率统一为百分比口径后等权（需至少2个有效）。"""
    valuation = ctx.get("valuation") or {}
    pe = valuation.get("pe_ttm")
    pb = valuation.get("pb")
    ps = valuation.get("ps_ttm")
    dividend = valuation.get("dividend_yield")
    vals = []
    if pe and pe > 0:
        vals.append(100.0 / pe)   # 盈利收益率 %
    if pb and pb > 0:
        vals.append(100.0 / pb)   # 账面市值比 %
    if ps and ps > 0:
        vals.append(100.0 / ps)   # 销售收益率 %
    if dividend is not None:
        vals.append(dividend)     # 股息率本身即 %
    if len(vals) < 2:
        return None
    return sum(vals) / len(vals)


VALUE_FACTORS = {
    "ep": (factor_ep, "价值", "盈利收益率"),
    "bp": (factor_bp, "价值", "账面市值比"),
    "sp": (factor_sp, "价值", "销售收益率"),
    "dividend_yield": (factor_dividend_yield, "价值", "股息率"),
    "pe_reverse": (factor_pe_reverse, "价值", "PE反向"),
    "pb_reverse": (factor_pb_reverse, "价值", "PB反向"),
    "pcf_reverse": (factor_pcf_reverse, "价值", "市现率反向"),
    "peg_reverse": (factor_peg_reverse, "价值", "PEG反向"),
    "value_composite": (factor_value_composite, "价值", "价值综合"),
}
