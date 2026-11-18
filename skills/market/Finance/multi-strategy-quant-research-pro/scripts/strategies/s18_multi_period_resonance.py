"""S21 多周期共振策略（进阶策略）

算法核心（严格语义）：
日线趋势信号与周线趋势信号同时向上，形成多周期共振——
大周期（周线）定方向，小周期（日线）定时机，两者共振时趋势可靠性最高。

1. 日线趋势（核心通过条件）：
   - 收盘价 > MA20（站上短期均线）
   - MA20 向上（今日 MA20 > 5 日前 MA20，均线斜率为正）
2. 周线趋势（核心通过条件）：
   - 周收盘价 > 周 MA10（站上周线中期均线）
   - 周 MA10 向上（本周 MA10 > 3 周前 MA10）
3. 共振强度（辅助加分）：
   - 日线与周线同时满足为"强共振"；
   - 仅日线满足为"日线信号"（不通过，需周线确认）。

与 composer 层周线确认的区别：
- composer 的 _weekly_confirm 仅对综合得分打 0.85 折扣（不改变通过语义）；
- S21 是策略级双周期判定，周线趋势是通过判定的必要条件，
  真正实现"日线择时 + 周线择势"的多周期共振选股。

数据：日K线 + 周K线（fetch_weekly_kline，A股/港股可用，美股无周线接口如实不通过）。
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from typing import Optional
from .base import make_result, clean_klines
from indicators import calc_sma
import config  # noqa: F401

S21_DAILY_MA = getattr(config, "S21_DAILY_MA", 20)             # 日线均线周期
S21_WEEKLY_MA = getattr(config, "S21_WEEKLY_MA", 10)           # 周线均线周期
S21_DAILY_LOOKBACK = getattr(config, "S21_DAILY_LOOKBACK", 5)  # 日线均线斜率对比天数
S21_WEEKLY_LOOKBACK = getattr(config, "S21_WEEKLY_LOOKBACK", 3)  # 周线均线斜率对比周数
S21_WEIGHT = getattr(config, "S21_WEIGHT", 0.06)               # 默认权重


def check_s21_multi_period_resonance(
    klines: list[dict],
    fundamental: Optional[dict] = None,
    money_flow: Optional[dict] = None,
    weekly_klines: Optional[list[dict]] = None,
) -> dict:
    """S21 多周期共振策略判定。

    Args:
        klines: 日K线列表
        fundamental: 基本面数据（本策略不使用，保留统一签名）
        money_flow: 资金流数据（本策略不使用，保留统一签名）
        weekly_klines: 周K线列表（多周期共振必需；为 None 或不足时如实不通过）

    Returns:
        {code, name, passed, score, signal_strength, reasons, details}
    """
    reasons = []
    details = {}
    score = 0.0

    klines = clean_klines(klines)
    weekly_klines = clean_klines(weekly_klines or [])

    details["daily_ma"] = S21_DAILY_MA
    details["weekly_ma"] = S21_WEEKLY_MA

    # ── 日线趋势 ──
    daily_pass = False
    if klines and len(klines) >= S21_DAILY_MA + S21_DAILY_LOOKBACK:
        closes = [k["close"] for k in klines]
        ma = calc_sma(closes, S21_DAILY_MA)
        if ma and len(ma) >= S21_DAILY_LOOKBACK + 1:
            cur_close = closes[-1]
            ma_now = ma[-1]
            ma_prev = ma[-(S21_DAILY_LOOKBACK + 1)]
            above_ma = cur_close > ma_now
            ma_rising = ma_now > ma_prev
            daily_pass = above_ma and ma_rising
            details["daily_close"] = round(cur_close, 2)
            details["daily_ma_now"] = round(ma_now, 2)
            details["daily_ma_prev"] = round(ma_prev, 2)
            if daily_pass:
                reasons.append(f"日线趋势: 收盘{cur_close:.2f}>MA{S21_DAILY_MA}({ma_now:.2f}) 且MA上行({ma_now:.2f}>{ma_prev:.2f})")
            else:
                parts = []
                if not above_ma:
                    parts.append(f"收盘{cur_close:.2f}<=MA{S21_DAILY_MA}({ma_now:.2f})")
                if not ma_rising:
                    parts.append(f"MA未上行({ma_now:.2f}<={ma_prev:.2f})")
                reasons.append("日线趋势未确认: " + "；".join(parts))
        else:
            reasons.append(f"日线均线数据不足（需≥{S21_DAILY_MA + S21_DAILY_LOOKBACK}根）")
    else:
        reasons.append(f"日K线不足（需≥{S21_DAILY_MA + S21_DAILY_LOOKBACK}根，实际{len(klines)}根）")

    # ── 周线趋势 ──
    weekly_pass = False
    if weekly_klines and len(weekly_klines) >= S21_WEEKLY_MA + S21_WEEKLY_LOOKBACK:
        w_closes = [k["close"] for k in weekly_klines]
        w_ma = calc_sma(w_closes, S21_WEEKLY_MA)
        if w_ma and len(w_ma) >= S21_WEEKLY_LOOKBACK + 1:
            w_cur = w_closes[-1]
            w_ma_now = w_ma[-1]
            w_ma_prev = w_ma[-(S21_WEEKLY_LOOKBACK + 1)]
            w_above = w_cur > w_ma_now
            w_rising = w_ma_now > w_ma_prev
            weekly_pass = w_above and w_rising
            details["weekly_close"] = round(w_cur, 2)
            details["weekly_ma_now"] = round(w_ma_now, 2)
            details["weekly_ma_prev"] = round(w_ma_prev, 2)
            if weekly_pass:
                reasons.append(f"周线趋势: 周收{w_cur:.2f}>周MA{S21_WEEKLY_MA}({w_ma_now:.2f}) 且周MA上行({w_ma_now:.2f}>{w_ma_prev:.2f})")
            else:
                parts = []
                if not w_above:
                    parts.append(f"周收{w_cur:.2f}<=周MA{S21_WEEKLY_MA}({w_ma_now:.2f})")
                if not w_rising:
                    parts.append(f"周MA未上行({w_ma_now:.2f}<={w_ma_prev:.2f})")
                reasons.append("周线趋势未确认: " + "；".join(parts))
        else:
            reasons.append(f"周线均线数据不足（需≥{S21_WEEKLY_MA + S21_WEEKLY_LOOKBACK}根）")
    else:
        reasons.append(f"周K线不足或无周线数据（需≥{S21_WEEKLY_MA + S21_WEEKLY_LOOKBACK}根，实际{len(weekly_klines)}根；美股无公开周线接口）")

    details["conditions"] = {
        "daily_trend_pass": daily_pass,
        "weekly_trend_pass": weekly_pass,
    }

    # ── 评分：日线(0.4) + 周线(0.6)（周线定方向权重更高）──
    if daily_pass:
        score += 0.4
    if weekly_pass:
        score += 0.6

    # 严格通过判定：日线 + 周线 同时满足（共振）
    passed = daily_pass and weekly_pass
    if passed:
        reasons.append("多周期共振: 日线与周线趋势同时向上")

    return make_result(
        code="S21", name="多周期共振",
        passed=passed,
        score=score,
        reasons=reasons,
        details=details,
    )


__all__ = ["check_s21_multi_period_resonance"]
