# -*- coding: utf-8 -*-
"""多时间框架共振分析：月线定大趋势+周线定中期+日线定买点。

三级共振评分：
- 月线：大趋势方向（MA20月线排列+月线MACD方向+月线RSI位置）
- 周线：中期趋势（周线MA10排列+周线MACD方向+周线RSI位置）
- 日线：买入时机（日线信号+日线位置）

成熟度约定（子指标样本不足时不计分、不输出确定性多空结论）：
- MACD 的 DIF 自第26根起有效，需至少 MACD_MIN_BARS 根才可比较末两期；
- RSI(14) 需至少 RSI_MIN_BARS 根才有真实值（此前为50占位，不得据此判弱势）。
聚合后的月/周线样本通常偏少，因此综合得分按"实际成熟可评的子项满分"归一，
可评子项不足一半时如实返回"未知"，避免把占位值误判为空头/弱势。

共振等级：
- 强共振：三级都看多（评分>=80）
- 中共振：两级看多（评分50-79）
- 弱共振：一级看多（评分20-49）
- 无共振：零级看多（评分<20）
"""

from .technical import calc_ma, calc_macd, calc_rsi

# 子指标成熟度门槛（根数）
MACD_MIN_BARS = 28   # DIF 自第26根起有效，留2根用于末两期比较
RSI_MIN_BARS = 15    # RSI(14) 需 period+1 根
# 可评子项满分低于该值时，认为样本不足以判断趋势，如实返回未知
_MIN_EVALUABLE_SCORE = 50


def analyze_monthly_trend(daily_klines: list[dict]) -> dict:
    """月线趋势分析（从日线聚合月线）。

    Args:
        daily_klines: 日K线列表；建议不少于250根以聚合出足量月线（约10根以上），
            少于60根或聚合后月线不足6根返回数据不足。

    Returns:
        dict: {trend, score, indicators, description}
    """
    if len(daily_klines) < 60:
        return {"trend": "未知", "score": 0, "indicators": {}, "description": "数据不足"}

    monthly = _aggregate_monthly(daily_klines)
    if len(monthly) < 6:
        return {"trend": "未知", "score": 0, "indicators": {}, "description": "月线数据不足"}

    score = 0
    max_score = 0
    indicators = {}

    # 1. 月线MA排列（MA5月 vs MA10月）
    ma5 = calc_ma(monthly, 5)
    ma10 = calc_ma(monthly, 10)
    if ma5 and ma10 and ma5[-1] and ma10[-1]:
        max_score += 25
        if ma5[-1] > ma10[-1]:
            score += 25
            indicators["ma_alignment"] = "多头"
        else:
            indicators["ma_alignment"] = "空头"
        if len(ma5) >= 2 and ma5[-2]:
            max_score += 10
            if ma5[-1] > ma5[-2]:
                score += 10
                indicators["ma_direction"] = "上行"
            else:
                indicators["ma_direction"] = "下行"

    # 2. 月线MACD方向（月线样本不足28根时不具参考性，跳过且不输出多空标签）
    if len(monthly) >= MACD_MIN_BARS:
        macd = calc_macd(monthly)
        dif = macd.get("dif") or []
        dea = macd.get("dea") or []
        if len(dif) >= 2 and len(dea) >= 2:
            max_score += 25
            if dif[-1] > dea[-1]:
                score += 25
                indicators["macd"] = "多头"
            else:
                indicators["macd"] = "空头"
            max_score += 10
            if dif[-1] > dif[-2]:
                score += 10
                indicators["macd_direction"] = "上行"
            else:
                indicators["macd_direction"] = "下行"

    # 3. 月线RSI位置（不足15根时为50占位值，跳过）
    if len(monthly) >= RSI_MIN_BARS:
        rsi = calc_rsi(monthly, 14)
        if rsi and rsi[-1]:
            max_score += 20
            indicators["rsi"] = round(rsi[-1], 1)
            if 50 < rsi[-1] < 70:
                score += 20
                indicators["rsi_status"] = "强势区间"
            elif rsi[-1] >= 70:
                score += 10
                indicators["rsi_status"] = "超买"
            elif 30 < rsi[-1] <= 50:
                indicators["rsi_status"] = "弱势区间"
            else:
                indicators["rsi_status"] = "超卖"

    # 4. 价格位置（收盘 vs MA10月）
    if monthly and ma10 and ma10[-1]:
        max_score += 10
        if monthly[-1]["close"] > ma10[-1]:
            score += 10
            indicators["price_vs_ma10"] = "上方"
        else:
            indicators["price_vs_ma10"] = "下方"

    if max_score < _MIN_EVALUABLE_SCORE:
        return {"trend": "未知", "score": 0, "indicators": indicators, "n_months": len(monthly),
                "description": "月线样本不足，趋势未知"}

    final_score = round(score / max_score * 100)
    if final_score >= 60:
        trend = "多头"
    elif final_score >= 30:
        trend = "震荡"
    else:
        trend = "空头"

    return {
        "trend": trend,
        "score": final_score,
        "indicators": indicators,
        "n_months": len(monthly),
        "description": f"月线{trend}（评分{final_score}/100）",
    }


def analyze_weekly_trend(weekly_klines: list[dict]) -> dict:
    """周线趋势分析。

    Args:
        weekly_klines: 周K线列表；建议不少于30根，少于20根返回数据不足。

    Returns:
        dict: {trend, score, indicators, description}
    """
    if len(weekly_klines) < 20:
        return {"trend": "未知", "score": 0, "indicators": {}, "description": "周线数据不足"}

    score = 0
    max_score = 0
    indicators = {}

    # 1. 周线MA排列（MA5 vs MA10 vs MA20）
    ma5 = calc_ma(weekly_klines, 5)
    ma10 = calc_ma(weekly_klines, 10)
    ma20 = calc_ma(weekly_klines, 20)
    if ma5 and ma10 and ma20 and ma5[-1] and ma10[-1] and ma20[-1]:
        max_score += 30
        if ma5[-1] > ma10[-1] > ma20[-1]:
            score += 30
            indicators["ma_alignment"] = "完美多头"
        elif ma5[-1] > ma10[-1]:
            score += 15
            indicators["ma_alignment"] = "部分多头"
        else:
            indicators["ma_alignment"] = "空头"

    # 2. 周线MACD（不足28根时 DIF/DEA 尚未成熟，跳过且不输出多空标签）
    if len(weekly_klines) >= MACD_MIN_BARS:
        macd = calc_macd(weekly_klines)
        dif = macd.get("dif") or []
        dea = macd.get("dea") or []
        hist = macd.get("macd") or []
        if len(dif) >= 2 and len(dea) >= 2:
            max_score += 25
            if dif[-1] > dea[-1]:
                score += 25
                indicators["macd"] = "多头"
            else:
                indicators["macd"] = "空头"
        if len(hist) >= 2:
            max_score += 15
            if hist[-1] > hist[-2]:
                score += 15
                indicators["macd_momentum"] = "增强"
            else:
                indicators["macd_momentum"] = "减弱"

    # 3. 周线RSI（不足15根为50占位值，跳过）
    if len(weekly_klines) >= RSI_MIN_BARS:
        rsi = calc_rsi(weekly_klines, 14)
        if rsi and rsi[-1]:
            max_score += 20
            indicators["rsi"] = round(rsi[-1], 1)
            if 50 < rsi[-1] < 70:
                score += 20
                indicators["rsi_status"] = "强势"
            elif rsi[-1] >= 70:
                score += 10
                indicators["rsi_status"] = "超买"
            else:
                indicators["rsi_status"] = "弱势"

    # 4. 价格 vs MA20周
    if weekly_klines and ma20 and ma20[-1]:
        max_score += 10
        if weekly_klines[-1]["close"] > ma20[-1]:
            score += 10
            indicators["price_vs_ma20"] = "上方"
        else:
            indicators["price_vs_ma20"] = "下方"

    if max_score < _MIN_EVALUABLE_SCORE:
        return {"trend": "未知", "score": 0, "indicators": indicators, "n_weeks": len(weekly_klines),
                "description": "周线样本不足，趋势未知"}

    final_score = round(score / max_score * 100)
    if final_score >= 60:
        trend = "多头"
    elif final_score >= 30:
        trend = "震荡"
    else:
        trend = "空头"

    return {
        "trend": trend,
        "score": final_score,
        "indicators": indicators,
        "n_weeks": len(weekly_klines),
        "description": f"周线{trend}（评分{final_score}/100）",
    }


def analyze_daily_signal(daily_klines: list[dict]) -> dict:
    """日线买入时机分析。

    Args:
        daily_klines: 日K线列表（建议不少于35根以保证MACD成熟，少于30根返回未知）

    Returns:
        dict: {signal, score, indicators, description}
    """
    if len(daily_klines) < 30:
        return {"signal": "未知", "score": 0, "indicators": {}}

    score = 0
    indicators = {}

    # 1. 日线MA排列
    ma5 = calc_ma(daily_klines, 5)
    ma10 = calc_ma(daily_klines, 10)
    ma20 = calc_ma(daily_klines, 20)
    if ma5 and ma10 and ma20 and ma5[-1] and ma10[-1] and ma20[-1]:
        if ma5[-1] > ma10[-1] > ma20[-1]:
            score += 25
            indicators["ma_alignment"] = "完美多头"
        elif ma5[-1] > ma10[-1]:
            score += 12
            indicators["ma_alignment"] = "部分多头"
        else:
            indicators["ma_alignment"] = "空头"

    # 2. 日线MACD金叉（DIF/DEA成熟后才判定，避免全0占位误判金叉/空头）
    if len(daily_klines) >= MACD_MIN_BARS:
        macd = calc_macd(daily_klines)
        dif = macd.get("dif") or []
        dea = macd.get("dea") or []
        hist = macd.get("macd") or []
        if len(dif) >= 2 and len(dea) >= 2:
            if dif[-1] > dea[-1] and dif[-2] <= dea[-2]:
                score += 30
                indicators["macd"] = "金叉"
            elif dif[-1] > dea[-1]:
                score += 15
                indicators["macd"] = "多头"
            else:
                indicators["macd"] = "空头"
        if len(hist) >= 2 and hist[-1] > 0 and hist[-1] > hist[-2]:
            score += 10
            indicators["macd_momentum"] = "红柱放大"

    # 3. 日线RSI（成熟后才判定）
    if len(daily_klines) >= RSI_MIN_BARS:
        rsi = calc_rsi(daily_klines, 14)
        if rsi and rsi[-1]:
            indicators["rsi"] = round(rsi[-1], 1)
            if 40 < rsi[-1] < 60:
                score += 15
                indicators["rsi_status"] = "中性偏强"
            elif 60 <= rsi[-1] < 75:
                score += 20
                indicators["rsi_status"] = "强势"
            elif rsi[-1] >= 75:
                score += 5
                indicators["rsi_status"] = "超买"
            else:
                indicators["rsi_status"] = "弱势"

    # 4. 量能
    if len(daily_klines) >= 6:
        vol_today = daily_klines[-1].get("volume", 0)
        vol_avg5 = sum(k.get("volume", 0) for k in daily_klines[-6:-1]) / 5
        if vol_avg5 > 0 and vol_today > vol_avg5 * 1.2:
            score += 10
            indicators["volume"] = "放量"
        else:
            indicators["volume"] = "缩量/平量"

    if score >= 60:
        signal = "买入时机"
    elif score >= 30:
        signal = "观望"
    else:
        signal = "回避"

    return {
        "signal": signal,
        "score": score,
        "indicators": indicators,
        "description": f"日线{signal}（评分{score}/100）",
    }


def multi_timeframe_resonance(daily_klines: list[dict],
                              weekly_klines: list[dict] = None) -> dict:
    """多时间框架共振分析。

    Args:
        daily_klines: 日K线
        weekly_klines: 周K线（可选，没有则从日线聚合）

    Returns:
        dict: {resonance_score, resonance_level, monthly, weekly, daily, description}
    """
    # 月线分析（从日线聚合）
    monthly = analyze_monthly_trend(daily_klines)

    # 周线分析
    if weekly_klines is None:
        weekly_klines = _aggregate_weekly(daily_klines)
    weekly = analyze_weekly_trend(weekly_klines)

    # 日线分析
    daily = analyze_daily_signal(daily_klines)

    # 综合共振评分（月线40% + 周线35% + 日线25%）
    total_score = (monthly["score"] * 0.4 +
                   weekly["score"] * 0.35 +
                   daily["score"] * 0.25)

    # 共振等级（"未知"不计入看多周期数）
    bullish_count = sum(1 for x in [monthly, weekly, daily]
                        if x.get("trend", x.get("signal")) in ("多头", "买入时机"))

    if total_score >= 70 and bullish_count >= 2:
        level = "强共振"
    elif total_score >= 50 and bullish_count >= 1:
        level = "中共振"
    elif total_score >= 30:
        level = "弱共振"
    else:
        level = "无共振"

    description = (f"{level}（综合{total_score:.0f}分）："
                   f"月线{monthly['trend']}({monthly['score']}分) + "
                   f"周线{weekly['trend']}({weekly['score']}分) + "
                   f"日线{daily['signal']}({daily['score']}分)，"
                   f"看多周期{bullish_count}/3")

    return {
        "resonance_score": round(total_score, 1),
        "resonance_level": level,
        "bullish_timeframes": bullish_count,
        "monthly": monthly,
        "weekly": weekly,
        "daily": daily,
        "description": description,
    }


def _aggregate_monthly(daily_klines: list[dict]) -> list[dict]:
    """从日线聚合月线。"""
    if not daily_klines:
        return []
    monthly = []
    current_month = None
    month_data = None
    for k in daily_klines:
        date_str = k.get("date", "")
        month = date_str[:7] if len(date_str) >= 7 else None
        if month != current_month:
            if month_data:
                monthly.append(month_data)
            current_month = month
            month_data = {
                "date": date_str,
                "open": k["open"],
                "high": k["high"],
                "low": k["low"],
                "close": k["close"],
                "volume": k.get("volume", 0),
            }
        else:
            month_data["high"] = max(month_data["high"], k["high"])
            month_data["low"] = min(month_data["low"], k["low"])
            month_data["close"] = k["close"]
            month_data["volume"] += k.get("volume", 0)
    if month_data:
        monthly.append(month_data)
    return monthly


def _aggregate_weekly(daily_klines: list[dict]) -> list[dict]:
    """从日线聚合周线（按自然周，周一为一周开始）。"""
    if not daily_klines:
        return []
    import datetime
    weekly = []
    current_week = None
    week_data = None
    for k in daily_klines:
        date_str = k.get("date", "")
        try:
            dt = datetime.datetime.strptime(date_str[:10], "%Y-%m-%d")
            iso = dt.isocalendar()
            week_key = f"{iso[0]}-W{iso[1]}"
        except (ValueError, IndexError):
            week_key = date_str[:10]
        if week_key != current_week:
            if week_data:
                weekly.append(week_data)
            current_week = week_key
            week_data = {
                "date": date_str,
                "open": k["open"],
                "high": k["high"],
                "low": k["low"],
                "close": k["close"],
                "volume": k.get("volume", 0),
            }
        else:
            week_data["high"] = max(week_data["high"], k["high"])
            week_data["low"] = min(week_data["low"], k["low"])
            week_data["close"] = k["close"]
            week_data["volume"] += k.get("volume", 0)
    if week_data:
        weekly.append(week_data)
    return weekly
