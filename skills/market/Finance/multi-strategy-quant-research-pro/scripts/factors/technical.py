# -*- coding: utf-8 -*-
"""技术因子库（18个）。

每个因子函数签名：factor_name(klines) -> float | None
返回因子值；数据不足时返回 None。
因子方向：正值表示看多，负值表示看空（已统一方向）。
"""

from indicators.technical import (
    calc_ma, calc_ema, calc_macd, calc_rsi,
    calc_bollinger, calc_adx, calc_atr, check_ma_alignment,
)


def _last(values, default=None):
    return values[-1] if values else default


def factor_ma_alignment(klines):
    """均线多头排列强度：MA5>MA10>MA20>MA60 满足的层级数（0-4）。"""
    r = check_ma_alignment(klines, (5, 10, 20, 60))
    return float(r.get("aligned_count", 0)) if r else None


def factor_ema_trend(klines):
    """EMA趋势：(EMA12 - EMA26) / EMA26 * 100，正值多头。"""
    e12 = _last(calc_ema(klines, 12))
    e26 = _last(calc_ema(klines, 26))
    if e12 is None or e26 is None or e26 == 0:
        return None
    return (e12 - e26) / e26 * 100


def factor_macd_hist(klines):
    """MACD柱：最新DIF-DEA，正值多头动能。"""
    macd = calc_macd(klines)
    if not macd:
        return None
    hist = macd.get("macd") or []
    return _last(hist)


def factor_rsi(klines):
    """RSI(14)：标准化到[-50,50]，50为中性，>0偏强。"""
    rsi = _last(calc_rsi(klines, 14))
    if rsi is None:
        return None
    return rsi - 50


def factor_boll_position(klines):
    """布林带位置：(收盘-下轨)/(上轨-下轨)，0-1区间，>0.5偏强。"""
    boll = calc_bollinger(klines, 20, 2)
    if not boll or not klines:
        return None
    upper = _last(boll.get("upper") or [])
    lower = _last(boll.get("lower") or [])
    close = klines[-1].get("close", 0)
    if upper is None or lower is None or upper == lower:
        return None
    return (close - lower) / (upper - lower)


def factor_adx(klines):
    """ADX(14)：趋势强度，>25为强趋势。"""
    return _last(calc_adx(klines, 14))


def factor_atr_ratio(klines):
    """ATR比率：ATR(14)/收盘*100，波动率指标。"""
    atr = _last(calc_atr(klines, 14))
    if atr is None or not klines:
        return None
    close = klines[-1].get("close", 0)
    if close == 0:
        return None
    return atr / close * 100


def factor_kdj_j(klines):
    """KDJ的J值：超买超卖，>100超买，<0超卖。"""
    if len(klines) < 9:
        return None
    closes = [k["close"] for k in klines]
    highs = [k["high"] for k in klines]
    lows = [k["low"] for k in klines]
    k_vals, d_vals = [], []
    for i in range(len(klines)):
        if i < 8:
            k_vals.append(50.0)
            d_vals.append(50.0)
            continue
        hh = max(highs[i-8:i+1])
        ll = min(lows[i-8:i+1])
        rsv = (closes[i] - ll) / (hh - ll) * 100 if hh != ll else 50
        k = 2/3 * k_vals[-1] + 1/3 * rsv
        d = 2/3 * d_vals[-1] + 1/3 * k
        k_vals.append(k)
        d_vals.append(d)
    j = 3 * k_vals[-1] - 2 * d_vals[-1]
    return j


def factor_cci(klines):
    """CCI(14)：顺势指标，>100超买，<-100超卖。"""
    n = 14
    if len(klines) < n:
        return None
    tps = [(k["high"] + k["low"] + k["close"]) / 3 for k in klines]
    tp = tps[-1]
    ma_tp = sum(tps[-n:]) / n
    md = sum(abs(t - ma_tp) for t in tps[-n:]) / n
    if md == 0:
        return 0.0
    return (tp - ma_tp) / (0.015 * md)


def factor_williams_r(klines):
    """威廉指标(14)：标准化到[0,100]，>80超卖（反向）。"""
    n = 14
    if len(klines) < n:
        return None
    hh = max(k["high"] for k in klines[-n:])
    ll = min(k["low"] for k in klines[-n:])
    close = klines[-1]["close"]
    if hh == ll:
        return 50.0
    wr = (hh - close) / (hh - ll) * 100
    return 100 - wr  # 反向：>50偏强


def factor_obv_trend(klines):
    """OBV趋势：OBV的20日变化率，正值资金流入。"""
    if len(klines) < 21:
        return None
    obv = 0.0
    obvs = []
    for i, k in enumerate(klines):
        if i == 0:
            obv = k.get("volume", 0)
        else:
            prev_close = klines[i-1]["close"]
            vol = k.get("volume", 0)
            if k["close"] > prev_close:
                obv += vol
            elif k["close"] < prev_close:
                obv -= vol
        obvs.append(obv)
    if obvs[-21] == 0:
        return None
    return (obvs[-1] - obvs[-21]) / abs(obvs[-21]) * 100


def factor_momentum_1m(klines):
    """1个月动量：近20日涨跌幅%。"""
    if len(klines) < 21:
        return None
    return (klines[-1]["close"] / klines[-21]["close"] - 1) * 100


def factor_momentum_3m(klines):
    """3个月动量：近60日涨跌幅%。"""
    if len(klines) < 61:
        return None
    return (klines[-1]["close"] / klines[-61]["close"] - 1) * 100


def factor_momentum_6m(klines):
    """6个月动量：近120日涨跌幅%。"""
    if len(klines) < 121:
        return None
    return (klines[-1]["close"] / klines[-121]["close"] - 1) * 100


def factor_reversal_5d(klines):
    """5日反转：近5日涨跌幅%，负值表示超跌（反转因子取负）。"""
    if len(klines) < 6:
        return None
    ret = (klines[-1]["close"] / klines[-6]["close"] - 1) * 100
    return -ret  # 反转：跌得多的得分高


def factor_volatility_20d(klines):
    """20日波动率：日收益率标准差*sqrt(252)*100，年化波动率%。"""
    import math
    if len(klines) < 21:
        return None
    rets = []
    for i in range(-20, 0):
        if klines[i-1]["close"] == 0:
            continue
        rets.append(klines[i]["close"] / klines[i-1]["close"] - 1)
    if len(rets) < 2:
        return None
    mean = sum(rets) / len(rets)
    var = sum((r - mean) ** 2 for r in rets) / (len(rets) - 1)
    return math.sqrt(var) * math.sqrt(252) * 100


def factor_volume_ratio(klines):
    """量比：当日成交量/5日均量，>1放量。"""
    if len(klines) < 6:
        return None
    today_vol = klines[-1].get("volume", 0)
    avg5 = sum(k.get("volume", 0) for k in klines[-6:-1]) / 5
    if avg5 == 0:
        return None
    return today_vol / avg5


def factor_bias_20(klines):
    """20日乖离率：(收盘-MA20)/MA20*100，正值偏离上方。"""
    ma20 = _last(calc_ma(klines, 20))
    if ma20 is None or ma20 == 0 or not klines:
        return None
    return (klines[-1]["close"] - ma20) / ma20 * 100


# 因子注册表：名称 -> (函数, 大类, 方向描述)
TECHNICAL_FACTORS = {
    "ma_alignment": (factor_ma_alignment, "技术", "均线多头排列强度"),
    "ema_trend": (factor_ema_trend, "技术", "EMA趋势"),
    "macd_hist": (factor_macd_hist, "技术", "MACD柱"),
    "rsi": (factor_rsi, "技术", "RSI相对强弱"),
    "boll_position": (factor_boll_position, "技术", "布林带位置"),
    "adx": (factor_adx, "技术", "ADX趋势强度"),
    "atr_ratio": (factor_atr_ratio, "技术", "ATR波动率"),
    "kdj_j": (factor_kdj_j, "技术", "KDJ-J值"),
    "cci": (factor_cci, "技术", "CCI顺势指标"),
    "williams_r": (factor_williams_r, "技术", "威廉指标"),
    "obv_trend": (factor_obv_trend, "技术", "OBV资金趋势"),
    "momentum_1m": (factor_momentum_1m, "技术", "1个月动量"),
    "momentum_3m": (factor_momentum_3m, "技术", "3个月动量"),
    "momentum_6m": (factor_momentum_6m, "技术", "6个月动量"),
    "reversal_5d": (factor_reversal_5d, "技术", "5日反转"),
    "volatility_20d": (factor_volatility_20d, "技术", "20日年化波动率"),
    "volume_ratio": (factor_volume_ratio, "技术", "量比"),
    "bias_20": (factor_bias_20, "技术", "20日乖离率"),
}
