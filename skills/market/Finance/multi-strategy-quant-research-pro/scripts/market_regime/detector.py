# -*- coding: utf-8 -*-
"""市场环境检测：判断当前市场处于牛市/熊市/震荡市。

基于大盘指数（上证指数000001）的真实K线数据：
- 趋势判断：MA20与MA60的排列关系
- 动量判断：近20日涨跌幅
- 波动率判断：20日年化波动率
- 成交量判断：近5日均量/20日均量
- 综合输出：市场环境 + 置信度 + 各指标值
"""

from indicators.technical import calc_ma
import math


def detect_market_regime(index_klines: list[dict]) -> dict:
    """检测市场环境。

    Args:
        index_klines: 大盘指数日K线列表（至少60根）

    Returns:
        dict: {regime, confidence, indicators, description}
            regime: 牛市 / 熊市 / 震荡市
            confidence: 0-1置信度
    """
    if len(index_klines) < 60:
        return {
            "regime": "未知",
            "confidence": 0,
            "indicators": {},
            "description": "K线数据不足60根，无法判断",
        }

    closes = [k["close"] for k in index_klines]
    latest = closes[-1]

    # 1. 趋势判断：MA20 vs MA60
    ma20 = calc_ma(index_klines, 20)
    ma60 = calc_ma(index_klines, 60)
    ma20_val = ma20[-1] if ma20 else None
    ma60_val = ma60[-1] if ma60 else None
    trend_score = 0
    if ma20_val and ma60_val:
        if ma20_val > ma60_val:
            trend_score = 1  # 多头排列
        else:
            trend_score = -1  # 空头排列

    # 2. 价格位置：收盘价 vs MA20
    price_vs_ma20 = 0
    if ma20_val:
        if latest > ma20_val:
            price_vs_ma20 = 1
        else:
            price_vs_ma20 = -1

    # 3. 动量：近20日涨跌幅
    momentum_20d = (latest / closes[-21] - 1) * 100 if closes[-21] != 0 else 0
    momentum_score = 0
    if momentum_20d > 3:
        momentum_score = 1
    elif momentum_20d < -3:
        momentum_score = -1

    # 4. 波动率：20日年化波动率
    rets = []
    for i in range(-20, 0):
        if closes[i-1] != 0:
            rets.append(closes[i] / closes[i-1] - 1)
    if len(rets) >= 2:
        mean_ret = sum(rets) / len(rets)
        var = sum((r - mean_ret) ** 2 for r in rets) / (len(rets) - 1)
        volatility = math.sqrt(var) * math.sqrt(252) * 100
    else:
        volatility = 0

    # 5. 成交量：近5日均量 vs 20日均量
    volumes = [k.get("volume", 0) for k in index_klines]
    vol_5 = sum(volumes[-5:]) / 5 if len(volumes) >= 5 else 0
    vol_20 = sum(volumes[-20:]) / 20 if len(volumes) >= 20 else 0
    volume_ratio = vol_5 / vol_20 if vol_20 > 0 else 1.0

    # 综合判断
    bull_signals = sum(1 for s in [trend_score, price_vs_ma20, momentum_score] if s > 0)
    bear_signals = sum(1 for s in [trend_score, price_vs_ma20, momentum_score] if s < 0)

    # 波动率高 + 方向不明确 = 震荡
    is_volatile = volatility > 25  # 年化波动率>25%为高波动
    direction_clear = abs(bull_signals - bear_signals) >= 2

    if bull_signals >= 2 and direction_clear:
        regime = "牛市"
        confidence = bull_signals / 3 * (0.8 if is_volatile else 1.0)
    elif bear_signals >= 2 and direction_clear:
        regime = "熊市"
        confidence = bear_signals / 3 * (0.8 if is_volatile else 1.0)
    else:
        regime = "震荡市"
        confidence = 0.5 + (0.2 if is_volatile else 0)

    # 成交量确认
    if regime == "牛市" and volume_ratio > 1.2:
        confidence = min(confidence + 0.1, 1.0)
    elif regime == "熊市" and volume_ratio > 1.2:
        confidence = min(confidence + 0.1, 1.0)

    description = (
        f"{regime}（置信度{confidence:.0%}）："
        f"MA20={ma20_val:.0f}, MA60={ma60_val:.0f}, "
        f"20日涨跌={momentum_20d:.1f}%, 年化波动={volatility:.1f}%, "
        f"量比={volume_ratio:.2f}"
    )

    return {
        "regime": regime,
        "confidence": round(confidence, 2),
        "indicators": {
            "ma20": round(ma20_val, 2) if ma20_val else None,
            "ma60": round(ma60_val, 2) if ma60_val else None,
            "ma_alignment": "多头" if trend_score > 0 else "空头" if trend_score < 0 else "纠缠",
            "price_vs_ma20": "上方" if price_vs_ma20 > 0 else "下方",
            "momentum_20d": round(momentum_20d, 2),
            "volatility_20d": round(volatility, 2),
            "volume_ratio": round(volume_ratio, 2),
            "bull_signals": bull_signals,
            "bear_signals": bear_signals,
        },
        "description": description,
    }


def get_position_suggestion(regime: str, confidence: float) -> dict:
    """根据市场环境给出仓位建议。"""
    suggestions = {
        "牛市": {"position": "70%-90%", "stop_loss": "宽松（-10%）", "style": "趋势/动量"},
        "熊市": {"position": "10%-30%", "stop_loss": "严格（-5%）", "style": "防御/价值"},
        "震荡市": {"position": "30%-50%", "stop_loss": "中等（-7%）", "style": "波段/高抛低吸"},
        "未知": {"position": "50%", "stop_loss": "中等（-7%）", "style": "均衡"},
    }
    base = suggestions.get(regime, suggestions["未知"])
    # 置信度调整
    if confidence < 0.5:
        base["position"] = "50%（方向不明，建议均衡）"
    return base
