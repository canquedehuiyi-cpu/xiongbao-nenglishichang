# -*- coding: utf-8 -*-
"""信号质量过滤：对技术信号做质量评估，0-100分。

六大过滤维度：
1. 假突破识别：突破后3日内回落超过50%视为假突破
2. 量能确认：突破时成交量>1.5倍20日均量
3. 多指标共振：至少2个独立指标（MACD/RSI/布林/均线）确认
4. 趋势过滤：价格在MA20上方，且MA20上行
5. 波动率过滤：ATR/价格在合理区间（过高降分）
6. 位置过滤：价格不在布林带上轨上方（超买区降分）
"""

from .technical import calc_ma, calc_macd, calc_rsi, calc_bollinger, calc_atr


def detect_false_breakout(klines: list[dict], lookback: int = 20) -> dict:
    """假突破识别。

    检测最近是否出现突破后快速回落的假突破形态。

    Args:
        klines: K线列表
        lookback: 回望周期

    Returns:
        dict: {is_false_breakout, breakout_date, pullback_pct, score_penalty}
    """
    if len(klines) < lookback + 3:
        return {"is_false_breakout": False, "score_penalty": 0}

    # 找最近的突破点（收盘价突破前20日高点）
    recent_highs = []
    for i in range(len(klines)):
        window = klines[max(0, i - lookback):i]
        recent_highs.append(max(k["high"] for k in window) if window else klines[i]["high"])

    breakout_idx = None
    for i in range(len(klines) - 4, len(klines) - 1):
        if i >= lookback and klines[i]["close"] > recent_highs[i] * 1.01:
            breakout_idx = i
            break

    if breakout_idx is None:
        return {"is_false_breakout": False, "score_penalty": 0}

    # 突破后3日内回落幅度
    breakout_price = klines[breakout_idx]["close"]
    post_prices = [k["low"] for k in klines[breakout_idx+1:breakout_idx+4]]
    if not post_prices:
        return {"is_false_breakout": False, "score_penalty": 0}

    min_post = min(post_prices)
    pullback = (breakout_price - min_post) / breakout_price * 100
    breakout_range = breakout_price - recent_highs[breakout_idx]
    pullback_ratio = (breakout_price - min_post) / breakout_range if breakout_range > 0 else 0

    is_false = pullback_ratio > 0.5  # 回落超过突破幅度的50%

    return {
        "is_false_breakout": is_false,
        "breakout_date": klines[breakout_idx].get("date", ""),
        "pullback_pct": round(pullback, 2),
        "pullback_ratio": round(pullback_ratio, 2),
        "score_penalty": 25 if is_false else 0,
    }


def volume_confirmation(klines: list[dict], ratio_threshold: float = 1.5) -> dict:
    """量能确认：最近一日成交量是否放大。

    Args:
        klines: K线列表
        ratio_threshold: 量比阈值（默认1.5倍）

    Returns:
        dict: {confirmed, volume_ratio, score_bonus}
    """
    if len(klines) < 21:
        return {"confirmed": False, "volume_ratio": 0, "score_bonus": 0}

    today_vol = klines[-1].get("volume", 0)
    avg20 = sum(k.get("volume", 0) for k in klines[-21:-1]) / 20
    ratio = today_vol / avg20 if avg20 > 0 else 0

    confirmed = ratio >= ratio_threshold
    bonus = 15 if confirmed else (5 if ratio >= 1.2 else 0)

    return {
        "confirmed": confirmed,
        "volume_ratio": round(ratio, 2),
        "avg20_volume": round(avg20, 0),
        "score_bonus": bonus,
    }


def multi_indicator_resonance(klines: list[dict]) -> dict:
    """多指标共振：MACD/RSI/布林/均线独立确认。

    Args:
        klines: K线列表

    Returns:
        dict: {confirmations, indicators, score_bonus}
    """
    confirmations = 0
    indicators = {}

    # 1. MACD确认：DIF > DEA 且 DIF > 0
    macd = calc_macd(klines)
    if macd:
        dif = macd.get("dif") or []
        dea = macd.get("dea") or []
        if dif and dea and dif[-1] > dea[-1] and dif[-1] > 0:
            confirmations += 1
            indicators["macd"] = "确认"
        else:
            indicators["macd"] = "未确认"

    # 2. RSI确认：50 < RSI < 70（强势但不超买）
    rsi = calc_rsi(klines, 14)
    if rsi and rsi[-1]:
        if 50 < rsi[-1] < 70:
            confirmations += 1
            indicators["rsi"] = f"确认({rsi[-1]:.1f})"
        else:
            indicators["rsi"] = f"未确认({rsi[-1]:.1f})"

    # 3. 布林带确认：价格在中轨上方，且不在上轨上方
    boll = calc_bollinger(klines, 20, 2)
    if boll and klines:
        upper = (boll.get("upper") or [None])[-1]
        mid = (boll.get("mid") or [None])[-1]
        close = klines[-1]["close"]
        if mid and upper and mid < close < upper:
            confirmations += 1
            indicators["boll"] = "确认"
        else:
            indicators["boll"] = "未确认"

    # 4. 均线确认：MA5 > MA10 > MA20
    ma5 = calc_ma(klines, 5)
    ma10 = calc_ma(klines, 10)
    ma20 = calc_ma(klines, 20)
    if ma5 and ma10 and ma20 and ma5[-1] and ma10[-1] and ma20[-1]:
        if ma5[-1] > ma10[-1] > ma20[-1]:
            confirmations += 1
            indicators["ma"] = "确认(完美多头)"
        elif ma5[-1] > ma10[-1]:
            indicators["ma"] = "部分确认"
        else:
            indicators["ma"] = "未确认"

    bonus = 20 if confirmations >= 3 else (12 if confirmations >= 2 else (5 if confirmations >= 1 else 0))

    return {
        "confirmations": confirmations,
        "total_indicators": 4,
        "indicators": indicators,
        "score_bonus": bonus,
    }


def trend_filter(klines: list[dict]) -> dict:
    """趋势过滤：价格在MA20上方，且MA20上行。

    Returns:
        dict: {passed, price_vs_ma20, ma20_direction, score_bonus}
    """
    if len(klines) < 21:
        return {"passed": False, "score_bonus": 0}

    ma20 = calc_ma(klines, 20)
    if not ma20 or len(ma20) < 2 or not ma20[-1]:
        return {"passed": False, "score_bonus": 0}

    close = klines[-1]["close"]
    above_ma20 = close > ma20[-1]
    ma20_up = ma20[-1] > ma20[-2]

    passed = above_ma20 and ma20_up
    bonus = 15 if passed else (8 if above_ma20 else 0)

    return {
        "passed": passed,
        "price_vs_ma20": "上方" if above_ma20 else "下方",
        "ma20_direction": "上行" if ma20_up else "下行",
        "score_bonus": bonus,
    }


def volatility_filter(klines: list[dict]) -> dict:
    """波动率过滤：ATR/价格在合理区间。

    过高波动率（>5%）降分，过低（<1%）也降分（流动性不足）。

    Returns:
        dict: {atr_ratio, level, score_adjustment}
    """
    if len(klines) < 15:
        return {"atr_ratio": 0, "level": "未知", "score_adjustment": 0}

    atr = calc_atr(klines, 14)
    if not atr or not atr[-1] or not klines:
        return {"atr_ratio": 0, "level": "未知", "score_adjustment": 0}

    atr_ratio = atr[-1] / klines[-1]["close"] * 100 if klines[-1]["close"] > 0 else 0

    if 1.5 <= atr_ratio <= 4.0:
        level = "合理"
        adj = 10
    elif 1.0 <= atr_ratio < 1.5 or 4.0 < atr_ratio <= 6.0:
        level = "偏高/偏低"
        adj = 3
    else:
        level = "异常"
        adj = -10

    return {
        "atr_ratio": round(atr_ratio, 2),
        "level": level,
        "score_adjustment": adj,
    }


def position_filter(klines: list[dict]) -> dict:
    """位置过滤：价格不在布林带上轨上方（超买区）。

    Returns:
        dict: {position, boll_position, score_adjustment}
    """
    if len(klines) < 20:
        return {"position": "未知", "score_adjustment": 0}

    boll = calc_bollinger(klines, 20, 2)
    if not boll or not klines:
        return {"position": "未知", "score_adjustment": 0}

    upper = (boll.get("upper") or [None])[-1]
    lower = (boll.get("lower") or [None])[-1]
    close = klines[-1]["close"]

    if upper and lower and upper > lower:
        boll_pos = (close - lower) / (upper - lower)
    else:
        boll_pos = 0.5

    if boll_pos > 0.95:
        position = "超买区"
        adj = -15
    elif boll_pos > 0.8:
        position = "偏高"
        adj = -5
    elif boll_pos < 0.2:
        position = "超卖区"
        adj = 5  # 超卖区可能是反弹机会
    else:
        position = "合理区间"
        adj = 5

    return {
        "position": position,
        "boll_position": round(boll_pos, 3),
        "score_adjustment": adj,
    }


def signal_quality_score(klines: list[dict]) -> dict:
    """综合信号质量评分（0-100）。

    基础分50，加上各维度的加分/减分。

    Args:
        klines: K线列表

    Returns:
        dict: {score, level, dimensions, description}
    """
    if len(klines) < 30:
        return {"score": 0, "level": "数据不足", "dimensions": {},
                "description": "K线不足30根，无法评估信号质量"}

    score = 50
    dimensions = {}

    # 1. 假突破识别（减分）
    fb = detect_false_breakout(klines)
    score -= fb["score_penalty"]
    dimensions["false_breakout"] = fb

    # 2. 量能确认（加分）
    vc = volume_confirmation(klines)
    score += vc["score_bonus"]
    dimensions["volume"] = vc

    # 3. 多指标共振（加分）
    mir = multi_indicator_resonance(klines)
    score += mir["score_bonus"]
    dimensions["resonance"] = mir

    # 4. 趋势过滤（加分）
    tf = trend_filter(klines)
    score += tf["score_bonus"]
    dimensions["trend"] = tf

    # 5. 波动率过滤（加减分）
    vf = volatility_filter(klines)
    score += vf["score_adjustment"]
    dimensions["volatility"] = vf

    # 6. 位置过滤（加减分）
    pf = position_filter(klines)
    score += pf["score_adjustment"]
    dimensions["position"] = pf

    score = max(0, min(100, score))

    if score >= 75:
        level = "优质信号"
    elif score >= 55:
        level = "良好信号"
    elif score >= 40:
        level = "一般信号"
    else:
        level = "弱信号/谨慎"

    description = (f"信号质量{score}/100（{level}）："
                   f"假突破={'是' if fb['is_false_breakout'] else '否'}，"
                   f"量比={vc['volume_ratio']}，"
                   f"指标共振{mir['confirmations']}/{mir['total_indicators']}，"
                   f"趋势={tf['price_vs_ma20']}({tf['ma20_direction']})，"
                   f"波动率={vf['level']}，位置={pf['position']}")

    return {
        "score": score,
        "level": level,
        "dimensions": dimensions,
        "description": description,
    }
