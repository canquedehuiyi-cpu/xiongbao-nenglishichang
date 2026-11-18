"""S19 MACD金叉择时策略（进阶策略）

算法核心（严格语义）：
基于公开日K线数据的 MACD 指标，检测**近 N 个交易日内 DIF 上穿 DEA（金叉）**，
并可选要求当前处于上升趋势，作为趋势启动/延续的择时信号。

1. 金叉检测（核心通过条件）：最近 S19_CROSS_DAYS 个交易日内，
   DIF 由下方上穿 DEA（dif[i] <= dea[i] 且 dif[i+1] > dea[i+1]），
   记录金叉触发日期与距今天数；窗口内无金叉则不通过。
2. 上升趋势确认（S19_REQUIRE_TREND=True 时计入通过判定，默认开启）：
   - 收盘价 > MA20（站上短期均线）
   - MA20 向上（今日 MA20 > 5 日前 MA20，均线斜率为正）
   - DIF > 0（快线在零轴上方，多头区域）
3. 金叉强度辅助（加分，不参与通过判定）：
   - 金叉距今天数越近信号越新鲜；DIF-DEA 差值越大动能越强。

与 S05（MACD底背离）的区别：
- S05 检测"价格新低但 DIF 未新低"的底背离抄底信号（反转预期）；
- S19 检测"DIF 上穿 DEA"的金叉趋势信号（顺势启动/延续），
  是案例"最近 N 天日线金叉且处于上升趋势"的直接实现。

数据源：日K线（calc_macd / calc_sma，纯技术面，三市场可用，零额外数据依赖）。
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from typing import Optional
from .base import make_result, clean_klines
from indicators import calc_macd, calc_sma
import config  # noqa: F401

S19_CROSS_DAYS = getattr(config, "S19_CROSS_DAYS", 20)            # 金叉检测窗口（近N个交易日）
S19_REQUIRE_TREND = getattr(config, "S19_REQUIRE_TREND", True)     # 是否要求上升趋势确认
S19_MA_PERIOD = getattr(config, "S19_MA_PERIOD", 20)               # 趋势确认均线周期
S19_TREND_LOOKBACK = getattr(config, "S19_TREND_LOOKBACK", 5)      # 均线斜率对比天数
S19_WEIGHT = getattr(config, "S19_WEIGHT", 0.06)                   # 默认权重


def check_s19_macd_golden_cross(
    klines: list[dict],
    fundamental: Optional[dict] = None,
    money_flow: Optional[dict] = None,
) -> dict:
    """S19 MACD金叉择时策略判定。

    Args:
        klines: 日K线列表
        fundamental: 基本面数据字典（本策略不使用，保留统一签名）
        money_flow: 资金流数据字典（本策略不使用，保留统一签名）

    Returns:
        {code, name, passed, score, signal_strength, reasons, details}
    """
    reasons = []
    details = {}
    score = 0.0

    klines = clean_klines(klines)

    if not klines or len(klines) < 60:
        return make_result(
            code="S19", name="MACD金叉择时",
            passed=False,
            score=0,
            reasons=[f"K线数据不足（{len(klines) if klines else 0}条，需≥60）"],
            details={},
        )

    closes = [k["close"] for k in klines]
    dates = [k["date"] for k in klines]

    # ── 计算 MACD ──
    macd_data = calc_macd(klines)
    dif = macd_data["dif"]
    dea = macd_data["dea"]
    n = len(dif)

    details["cross_days_window"] = S19_CROSS_DAYS
    details["ma_period"] = S19_MA_PERIOD
    details["require_trend"] = S19_REQUIRE_TREND

    # ── 条件一：近 S19_CROSS_DAYS 日内 DIF 上穿 DEA（金叉，核心通过条件）──
    cross_pass = False
    cross_date = None
    cross_days_ago = None
    start = max(n - S19_CROSS_DAYS - 1, 1)
    for i in range(n - 2, start - 1, -1):
        if dif[i] <= dea[i] and dif[i + 1] > dea[i + 1]:
            cross_date = dates[i + 1]
            cross_days_ago = n - 1 - (i + 1)
            cross_pass = True
            break

    details["golden_cross_date"] = cross_date
    details["cross_days_ago"] = cross_days_ago
    details["signal_date"] = cross_date  # 报告层通用信号时间字段

    if cross_pass:
        reasons.append(f"近{S19_CROSS_DAYS}日MACD金叉: {cross_date}（距今{cross_days_ago}个交易日）")
    else:
        reasons.append(f"近{S19_CROSS_DAYS}日无MACD金叉（DIF未上穿DEA）")

    # ── 条件二：上升趋势确认（S19_REQUIRE_TREND 时计入通过判定）──
    trend_pass = False
    ma = calc_sma(closes, S19_MA_PERIOD)
    cur_close = closes[-1]
    cur_dif = dif[-1]
    cur_dea = dea[-1]
    details["close"] = round(cur_close, 2)
    details["dif"] = round(cur_dif, 2)
    details["dea"] = round(cur_dea, 2)

    if ma and len(ma) >= S19_TREND_LOOKBACK + 1:
        ma_now = ma[-1]
        ma_prev = ma[-(S19_TREND_LOOKBACK + 1)]
        details["ma"] = round(ma_now, 2)
        details["ma_prev"] = round(ma_prev, 2)
        above_ma = cur_close > ma_now
        ma_rising = ma_now > ma_prev
        dif_above_zero = cur_dif > 0
        trend_pass = above_ma and ma_rising and dif_above_zero
        if trend_pass:
            reasons.append(
                f"上升趋势确认: 收盘{cur_close:.2f}>MA{S19_MA_PERIOD}({ma_now:.2f}) "
                f"且MA上行({ma_now:.2f}>{ma_prev:.2f}) 且DIF({cur_dif:.2f})>0"
            )
        else:
            parts = []
            if not above_ma:
                parts.append(f"收盘{cur_close:.2f}<=MA{S19_MA_PERIOD}({ma_now:.2f})")
            if not ma_rising:
                parts.append(f"MA未上行({ma_now:.2f}<={ma_prev:.2f})")
            if not dif_above_zero:
                parts.append(f"DIF({cur_dif:.2f})<=0")
            reasons.append("上升趋势未确认: " + "；".join(parts))
    else:
        details["ma"] = None
        reasons.append(f"均线数据不足（需≥{S19_MA_PERIOD + S19_TREND_LOOKBACK}根），无法确认趋势")

    details["trend_pass"] = trend_pass
    details["conditions"] = {
        "golden_cross": cross_pass,
        "trend_confirm": trend_pass,
    }

    # ── 评分：金叉（0.6）+ 趋势确认（0.4）──
    if cross_pass:
        score += 0.6
    if trend_pass:
        score += 0.4

    # 金叉新鲜度与动能强度（signal_strength 由 make_result 按 score 推导）
    if cross_pass and cross_days_ago is not None and cross_days_ago <= 3:
        reasons.append(f"信号新鲜（金叉距今仅{cross_days_ago}个交易日）")

    # 严格通过判定：金叉 且（按配置）上升趋势确认
    if S19_REQUIRE_TREND:
        passed = cross_pass and trend_pass
    else:
        passed = cross_pass

    return make_result(
        code="S19", name="MACD金叉择时",
        passed=passed,
        score=score,
        reasons=reasons,
        details=details,
    )


__all__ = ["check_s19_macd_golden_cross"]
