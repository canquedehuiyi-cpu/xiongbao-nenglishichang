# -*- coding: utf-8 -*-
"""市场宽度指标：衡量市场整体健康度。

四大指标：
1. 涨跌家数比（Advance/Decline Ratio）
2. 新高新低指数（New Highs - New Lows）
3. ADL腾落指数（累计涨跌家数差）
4. 均线以上个股占比（MA20/MA60以上占比）

市场宽度评分：综合上述指标，0-100分，>60为健康，<40为虚弱。
"""



def calc_advance_decline_ratio(stocks: list[dict]) -> dict:
    """涨跌家数比。

    Args:
        stocks: 股票列表，每项含 change_pct（涨跌幅%）

    Returns:
        dict: {advances, declines, unchanged, ratio, ad_line}
    """
    advances = sum(1 for s in stocks if s.get("change_pct", 0) > 0)
    declines = sum(1 for s in stocks if s.get("change_pct", 0) < 0)
    unchanged = sum(1 for s in stocks if s.get("change_pct", 0) == 0)

    ratio = advances / declines if declines > 0 else float("inf")
    ad_line = advances - declines

    return {
        "advances": advances,
        "declines": declines,
        "unchanged": unchanged,
        "total": len(stocks),
        "ratio": round(ratio, 2) if declines > 0 else None,
        "ad_line": ad_line,
        "advance_pct": round(advances / len(stocks) * 100, 1) if stocks else 0,
        "description": f"上涨{advances}家/下跌{declines}家，涨跌比{ratio:.2f}" if declines > 0 else f"上涨{advances}家/下跌0家",
    }


def calc_new_high_low_index(stocks: list[dict], lookback: int = 250) -> dict:
    """新高新低指数（NH-NL）。

    Args:
        stocks: 股票列表，每项含 close, high_52w, low_52w（或high/low历史）
        lookback: 回望周期（默认250个交易日≈52周）

    Returns:
        dict: {new_highs, new_lows, nhnl_index, nhnl_ratio}
    """
    new_highs = 0
    new_lows = 0
    for s in stocks:
        close = s.get("close", 0)
        high = s.get("high_52w", s.get("high", 0))
        low = s.get("low_52w", s.get("low", 0))
        if close > 0 and high > 0 and close >= high * 0.98:
            new_highs += 1
        if close > 0 and low > 0 and close <= low * 1.02:
            new_lows += 1

    nhnl = new_highs - new_lows
    ratio = new_highs / new_lows if new_lows > 0 else float("inf")

    return {
        "new_highs": new_highs,
        "new_lows": new_lows,
        "nhnl_index": nhnl,
        "nhnl_ratio": round(ratio, 2) if new_lows > 0 else None,
        "new_high_pct": round(new_highs / len(stocks) * 100, 1) if stocks else 0,
        "description": f"新高{new_highs}家/新低{new_lows}家，NH-NL={nhnl}",
    }


def calc_adl_index(daily_ad_lines: list[int]) -> dict:
    """ADL腾落指数（累计涨跌家数差）。

    Args:
        daily_ad_lines: 每日AD Line列表（按时间排序）

    Returns:
        dict: {adl_current, adl_ma5, adl_ma20, trend, description}
    """
    if not daily_ad_lines:
        return {"adl_current": 0, "trend": "未知"}

    adl = sum(daily_ad_lines)
    ma5 = sum(daily_ad_lines[-5:]) / 5 if len(daily_ad_lines) >= 5 else None
    ma20 = sum(daily_ad_lines[-20:]) / 20 if len(daily_ad_lines) >= 20 else None

    if ma5 and ma20:
        if ma5 > ma20:
            trend = "上升"
        else:
            trend = "下降"
    elif len(daily_ad_lines) >= 2:
        trend = "上升" if daily_ad_lines[-1] > daily_ad_lines[-2] else "下降"
    else:
        trend = "未知"

    return {
        "adl_current": adl,
        "adl_ma5": round(ma5, 1) if ma5 else None,
        "adl_ma20": round(ma20, 1) if ma20 else None,
        "trend": trend,
        "description": f"ADL={adl}，趋势{trend}",
    }


def calc_above_ma_ratio(stocks: list[dict], ma_period: int = 20) -> dict:
    """均线以上个股占比。

    Args:
        stocks: 股票列表，每项含 close, ma{period}（如ma20, ma60）
        ma_period: 均线周期（20或60）

    Returns:
        dict: {above, below, ratio, description}
    """
    ma_key = f"ma{ma_period}"
    above = 0
    below = 0
    for s in stocks:
        close = s.get("close", 0)
        ma = s.get(ma_key)
        if ma is None or ma == 0 or close == 0:
            continue
        if close > ma:
            above += 1
        else:
            below += 1

    total = above + below
    ratio = above / total * 100 if total > 0 else 0

    return {
        "above": above,
        "below": below,
        "total": total,
        "ratio": round(ratio, 1),
        "ma_period": ma_period,
        "description": f"MA{ma_period}以上占比{ratio:.1f}%（{above}/{total}）",
    }


def market_breadth_score(stocks: list[dict], daily_ad_lines: list[int] = None) -> dict:
    """综合市场宽度评分（0-100）。

    评分维度：
    - 涨跌家数比（25分）：ADR>1.5满分，<0.5零分
    - 新高新低（25分）：NH-NL>0且NH/NL>2满分
    - ADL趋势（20分）：上升满分，下降零分
    - MA20以上占比（15分）：>70%满分，<30%零分
    - MA60以上占比（15分）：>60%满分，<40%零分

    Args:
        stocks: 全市场股票列表
        daily_ad_lines: 历史每日AD Line（可选）

    Returns:
        dict: {score, level, components, description, position_suggestion}
    """
    if not stocks:
        return {"score": 0, "level": "未知", "components": {}}

    # 1. 涨跌家数比
    ad = calc_advance_decline_ratio(stocks)
    adr = ad.get("ratio", 1)
    if adr is None:
        ad_score = 25
    elif adr >= 1.5:
        ad_score = 25
    elif adr >= 1.0:
        ad_score = 18
    elif adr >= 0.7:
        ad_score = 10
    else:
        ad_score = 5

    # 2. 新高新低
    nhnl = calc_new_high_low_index(stocks)
    nhnl_idx = nhnl.get("nhnl_index", 0)
    nhnl_ratio = nhnl.get("nhnl_ratio", 1)
    if nhnl_idx > 0 and (nhnl_ratio is None or nhnl_ratio >= 2):
        nh_score = 25
    elif nhnl_idx > 0:
        nh_score = 18
    elif nhnl_idx == 0:
        nh_score = 12
    elif nhnl_idx > -len(stocks) * 0.05:
        nh_score = 8
    else:
        nh_score = 3

    # 3. ADL趋势
    if daily_ad_lines:
        adl = calc_adl_index(daily_ad_lines)
        adl_score = 20 if adl["trend"] == "上升" else 8
    else:
        # 无历史ADL，用当日AD Line近似
        adl = {"adl_current": ad["ad_line"], "trend": "未知"}
        adl_score = 15 if ad["ad_line"] > 0 else 8

    # 4. MA20以上占比
    ma20 = calc_above_ma_ratio(stocks, 20)
    ma20_ratio = ma20.get("ratio", 50)
    if ma20_ratio >= 70:
        ma20_score = 15
    elif ma20_ratio >= 50:
        ma20_score = 10
    elif ma20_ratio >= 30:
        ma20_score = 5
    else:
        ma20_score = 2

    # 5. MA60以上占比
    ma60 = calc_above_ma_ratio(stocks, 60)
    ma60_ratio = ma60.get("ratio", 50)
    if ma60_ratio >= 60:
        ma60_score = 15
    elif ma60_ratio >= 45:
        ma60_score = 10
    elif ma60_ratio >= 30:
        ma60_score = 5
    else:
        ma60_score = 2

    total_score = ad_score + nh_score + adl_score + ma20_score + ma60_score

    if total_score >= 70:
        level = "健康"
        position = "可正常仓位（70-90%），市场广度支持上涨"
    elif total_score >= 50:
        level = "中性"
        position = "中等仓位（40-60%），注意分化"
    elif total_score >= 30:
        level = "虚弱"
        position = "低仓位（20-40%），市场广度不足"
    else:
        level = "极度虚弱"
        position = "极低仓位（0-20%）或空仓，市场普遍下跌"

    return {
        "score": total_score,
        "level": level,
        "components": {
            "advance_decline": {"score": ad_score, "data": ad},
            "new_high_low": {"score": nh_score, "data": nhnl},
            "adl": {"score": adl_score, "data": adl},
            "ma20_above": {"score": ma20_score, "data": ma20},
            "ma60_above": {"score": ma60_score, "data": ma60},
        },
        "position_suggestion": position,
        "description": f"市场宽度{total_score}/100（{level}），{position}",
    }
