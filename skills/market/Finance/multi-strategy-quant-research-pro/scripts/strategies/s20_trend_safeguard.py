"""S23 均线趋势风控策略

判定逻辑（全部为确定性规则，真实可审计）：
- 条件一：MA20 向上（当前 MA20 > 5 日前 MA20，趋势向上）
- 条件二：股价站稳 MA20（连续≥3日收盘价 > MA20）
- 条件三：依托 MA60 震荡上行（收盘价 > MA60，且 MA60 走平或向上）
- 条件四：非无量反弹（最新成交量 ≥ 均量×系数，排除无量假反弹）
- 条件五：无高位见顶信号（RSI 未严重超买，且近 N 日无放量滞涨）

通过条件：以上五条全部满足（风控全通过才入选）。
数据源：日K线数据。
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from typing import Optional
from .base import make_result, clean_klines
from indicators.technical import calc_rsi, calc_sma
import config  # noqa: F401

S23_MA20 = getattr(config, "S23_MA20", 20)                       # MA20 周期
S23_MA20_SLOPE_DAYS = getattr(config, "S23_MA20_SLOPE_DAYS", 5)  # MA20 斜率对比天数
S23_STAND_DAYS = getattr(config, "S23_STAND_DAYS", 3)            # 站稳 MA20 的连续天数
S23_MA60 = getattr(config, "S23_MA60", 60)                       # MA60 周期
S23_MA60_SLOPE_DAYS = getattr(config, "S23_MA60_SLOPE_DAYS", 10) # MA60 斜率对比天数
S23_VOL_AVG_DAYS = getattr(config, "S23_VOL_AVG_DAYS", 5)        # 均量对比天数
S23_VOL_MIN_RATIO = getattr(config, "S23_VOL_MIN_RATIO", 0.5)    # 非无量：量 ≥ 均量×该系数
S23_RSI_PERIOD = getattr(config, "S23_RSI_PERIOD", 14)           # RSI 周期
S23_RSI_MAX = getattr(config, "S23_RSI_MAX", 75.0)               # RSI 未超买上限
S23_TOPPING_DAYS = getattr(config, "S23_TOPPING_DAYS", 5)        # 高位见顶检查窗口
S23_STAGNANT_PCT = getattr(config, "S23_STAGNANT_PCT", 1.0)      # 放量滞涨：涨幅 < 该值(%) 视为滞涨
S23_STAGNANT_VOL_RATIO = getattr(config, "S23_STAGNANT_VOL_RATIO", 1.5)  # 放量滞涨：量 > 均量×该系数


def check_s23_trend_safeguard(
    klines: list[dict],
    fundamental: Optional[dict] = None,
    money_flow: Optional[dict] = None,
) -> dict:
    """S23 均线趋势风控策略判定。

    Args:
        klines: 日K线列表（需不少于 S23_MA60 + max(S23_MA20_SLOPE_DAYS, S23_MA60_SLOPE_DAYS) + 5 条，默认75条）
        fundamental: 基本面数据字典（本策略不使用）
        money_flow: 资金流数据字典（本策略不使用）

    Returns:
        {code, name, passed, score, signal_strength, reasons, details}
    """
    klines = clean_klines(klines)
    reasons = []
    details = {}
    score = 0.0

    min_len = S23_MA60 + max(S23_MA20_SLOPE_DAYS, S23_MA60_SLOPE_DAYS) + 5
    if not klines or len(klines) < min_len:
        return make_result(
            code="S23", name="均线趋势风控",
            passed=False, score=0,
            reasons=[f"K线数据不足（{len(klines) if klines else 0}条，需≥{min_len}）"],
            details={},
        )

    closes = [float(k["close"]) for k in klines]
    volumes = [float(k["volume"]) for k in klines]
    last_idx = len(closes) - 1

    # 均线序列统一由指标层计算（唯一真源），此处仅按位置取值，窗口不足返回 None
    ma20_seq = calc_sma(closes, S23_MA20)
    ma60_seq = calc_sma(closes, S23_MA60)

    def _ma_at(seq: list[float], period: int, idx: int) -> Optional[float]:
        return seq[idx] if idx >= 0 and idx + 1 >= period else None

    # ── 条件一：MA20 向上 ──
    ma20_now = _ma_at(ma20_seq, S23_MA20, last_idx)
    ma20_prev = _ma_at(ma20_seq, S23_MA20, last_idx - S23_MA20_SLOPE_DAYS)
    details["ma20_now"] = round(ma20_now, 3) if ma20_now is not None else None
    details["ma20_prev"] = round(ma20_prev, 3) if ma20_prev is not None else None
    ma20_up = ma20_now is not None and ma20_prev is not None and ma20_now > ma20_prev
    if ma20_up:
        reasons.append(f"MA20 向上（{ma20_now:.2f} > {ma20_prev:.2f}）")
    else:
        reasons.append("MA20 未向上")
    if ma20_up:
        score += 0.2

    # ── 条件二：股价站稳 MA20（连续≥N日收盘 > MA20）──
    stand_pass = False
    if ma20_now is not None:
        stand_days = 0
        for i in range(last_idx, -1, -1):
            ma_i = _ma_at(ma20_seq, S23_MA20, i)
            if ma_i is not None and closes[i] > ma_i:
                stand_days += 1
            else:
                break
            if stand_days >= S23_STAND_DAYS:
                break
        details["stand_days"] = stand_days
        stand_pass = stand_days >= S23_STAND_DAYS
        if stand_pass:
            reasons.append(f"股价连续{stand_days}日站稳 MA20")
        else:
            reasons.append(f"股价未连续{S23_STAND_DAYS}日站稳 MA20（实际{stand_days}日）")
    else:
        details["stand_days"] = None
        reasons.append("MA20 数据不足")
    if stand_pass:
        score += 0.2

    # ── 条件三：依托 MA60 震荡上行（收盘 > MA60 且 MA60 走平/向上）──
    ma60_pass = False
    ma60_now = _ma_at(ma60_seq, S23_MA60, last_idx)
    ma60_prev = _ma_at(ma60_seq, S23_MA60, last_idx - S23_MA60_SLOPE_DAYS)
    details["ma60_now"] = round(ma60_now, 3) if ma60_now is not None else None
    details["ma60_prev"] = round(ma60_prev, 3) if ma60_prev is not None else None
    if ma60_now is not None and ma60_prev is not None:
        above = closes[-1] > ma60_now
        ma60_flat_up = ma60_now >= ma60_prev * 0.995  # 走平或向上（容差0.5%）
        ma60_pass = above and ma60_flat_up
        if ma60_pass:
            reasons.append(f"收盘 {closes[-1]:.2f} > MA60 {ma60_now:.2f} 且 MA60 走平/向上")
        else:
            reasons.append("未满足依托 MA60 震荡上行")
    else:
        reasons.append("MA60 数据不足")
    if ma60_pass:
        score += 0.2

    # ── 条件四：非无量反弹 ──
    vol_pass = False
    if len(volumes) >= S23_VOL_AVG_DAYS + 1:
        avg_vol = sum(volumes[-(S23_VOL_AVG_DAYS + 1):-1]) / S23_VOL_AVG_DAYS
        details["avg_vol"] = int(avg_vol)
        details["current_vol"] = int(volumes[-1])
        vol_pass = volumes[-1] >= avg_vol * S23_VOL_MIN_RATIO
        if vol_pass:
            reasons.append(f"量能正常（{volumes[-1]:.0f} ≥ 均量{avg_vol:.0f}×{S23_VOL_MIN_RATIO:.2f}，非无量反弹）")
        else:
            reasons.append(f"量能过低（{volumes[-1]:.0f} < 均量{avg_vol:.0f}×{S23_VOL_MIN_RATIO:.2f}，疑无量反弹）")
    else:
        details["avg_vol"] = None
        reasons.append("量能数据不足")
    if vol_pass:
        score += 0.2

    # ── 条件五：无高位见顶信号（RSI 未超买 + 近N日无放量滞涨）──
    topping_pass = False
    rsi_ok = True
    rsi_vals = calc_rsi(klines, period=S23_RSI_PERIOD)
    if rsi_vals and len(rsi_vals) > 0:
        latest_rsi = rsi_vals[-1]
        details["rsi"] = round(latest_rsi, 2)
        rsi_ok = latest_rsi < S23_RSI_MAX
        if not rsi_ok:
            reasons.append(f"RSI {latest_rsi:.1f} ≥ {S23_RSI_MAX:.0f} 超买（高位见顶风险）")
    else:
        details["rsi"] = None

    # 放量滞涨：窗口内某日涨幅 < S23_STAGNANT_PCT% 且量 > 均量×S23_STAGNANT_VOL_RATIO
    stagnant = False
    if len(klines) >= S23_TOPPING_DAYS + S23_VOL_AVG_DAYS + 1:
        for i in range(last_idx - S23_TOPPING_DAYS + 1, last_idx + 1):
            if i < 1:
                continue
            prev_close = closes[i - 1]
            if prev_close <= 0:
                continue
            chg_pct = (closes[i] / prev_close - 1) * 100
            avg_before = sum(volumes[i - S23_VOL_AVG_DAYS:i]) / S23_VOL_AVG_DAYS
            if chg_pct < S23_STAGNANT_PCT and volumes[i] > avg_before * S23_STAGNANT_VOL_RATIO:
                stagnant = True
                reasons.append(f"近{S23_TOPPING_DAYS}日存在放量滞涨（高位见顶风险）")
                break
    else:
        stagnant = True  # 数据不足视为无法确认无见顶，从严
        reasons.append("数据不足，无法确认无高位见顶信号（从严不通过）")

    topping_pass = rsi_ok and not stagnant
    if topping_pass:
        reasons.append("无高位见顶信号")
    if topping_pass:
        score += 0.2

    details["conditions"] = {
        "ma20_up": ma20_up,
        "stand_pass": stand_pass,
        "ma60_pass": ma60_pass,
        "vol_pass": vol_pass,
        "topping_pass": topping_pass,
    }

    return make_result(
        code="S23", name="均线趋势风控",
        passed=ma20_up and stand_pass and ma60_pass and vol_pass and topping_pass,
        score=score,
        reasons=reasons,
        details=details,
    )


__all__ = ["check_s23_trend_safeguard"]
