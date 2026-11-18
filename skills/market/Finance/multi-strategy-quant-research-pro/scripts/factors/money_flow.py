# -*- coding: utf-8 -*-
"""资金因子库（5个）。

因子函数签名：factor_name(ctx) -> float | None
方向：正值表示资金流入/看多，负值表示资金流出/看空。
"""


def factor_main_inflow_rate(ctx):
    """近10日主力净流入率：主力净流入总和 / 区间成交额 * 100。"""
    flows = ctx.get("money_flow") or []
    klines = ctx.get("klines") or []
    if not flows or not klines:
        return None
    recent = flows[-10:] if len(flows) >= 10 else flows
    total_inflow = sum(f.get("main_net_inflow", 0) or 0 for f in recent)
    # 用近10日成交额近似（收盘价*成交量）
    n = min(len(klines), len(recent))
    total_amount = sum(klines[-i-1].get("close", 0) * klines[-i-1].get("volume", 0)
                       for i in range(n))
    if total_amount == 0:
        return None
    return total_inflow / total_amount * 100


def factor_consecutive_inflow(ctx):
    """连续主力净流入天数：从最近一天往前数，连续净流入的天数。"""
    flows = ctx.get("money_flow") or []
    if not flows:
        return None
    count = 0
    for f in reversed(flows):
        if (f.get("main_net_inflow") or 0) > 0:
            count += 1
        else:
            break
    return float(count)


def factor_northbound_change(ctx):
    """北向持股变化：近10日北向持股变化率%（需扩展数据，无则None）。"""
    ext = ctx.get("extended") or {}
    nb = ext.get("northbound") or []
    if len(nb) < 2:
        return None
    recent = nb[-1].get("hold_shares", 0) or 0
    prev = nb[-min(10, len(nb))].get("hold_shares", 0) or 0
    if prev == 0:
        return None
    return (recent - prev) / prev * 100


def factor_margin_change(ctx):
    """融资余额变化：近10日融资余额变化率%（需扩展数据，无则None）。"""
    ext = ctx.get("extended") or {}
    margin = ext.get("margin_trading") or []
    if len(margin) < 2:
        return None
    recent = margin[-1].get("rzye", 0) or 0
    prev = margin[-min(10, len(margin))].get("rzye", 0) or 0
    if prev == 0:
        return None
    return (recent - prev) / prev * 100


def factor_dragon_tiger_signal(ctx):
    """龙虎榜信号：近5日龙虎榜净买入总和（万元），需扩展数据，无则None。"""
    ext = ctx.get("extended") or {}
    dt = ext.get("dragon_tiger") or []
    if not dt:
        return None
    recent = dt[-5:] if len(dt) >= 5 else dt
    total = sum(d.get("net_buy", 0) or 0 for d in recent)
    return total / 10000  # 元转万元


MONEY_FLOW_FACTORS = {
    "main_inflow_rate": (factor_main_inflow_rate, "资金", "主力净流入率"),
    "consecutive_inflow": (factor_consecutive_inflow, "资金", "连续流入天数"),
    "northbound_change": (factor_northbound_change, "资金", "北向持股变化"),
    "margin_change": (factor_margin_change, "资金", "融资余额变化"),
    "dragon_tiger_signal": (factor_dragon_tiger_signal, "资金", "龙虎榜净买入"),
}
