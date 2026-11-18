"""S22 相对强度策略（进阶策略）

算法核心（严格语义）：
检测个股自身的价格强度与动量加速，作为市场资金关注、股价走强的情绪信号。
相对强度不依赖外部大盘指数（纯技术面自洽），通过"中期涨幅 + 短期加速 + 放量确认"
三维度刻画个股在市场中的相对强势。

1. 中期强度（核心通过条件）：
   近 S22_MID_PERIOD（默认20）个交易日累计涨幅 >= S22_MID_RETURN_MIN（默认15%），
   且收盘价站上 MA20（趋势确认）。
2. 短期加速（核心通过条件）：
   近 S22_SHORT_PERIOD（默认5）个交易日累计涨幅 > 0（短期动能为正），
   即中期强势后短期仍在加速而非衰减。
3. 放量确认（辅助加分，不参与通过判定）：
   近 S22_MID_PERIOD 日均成交量 > 近60日日均成交量（资金关注度提升）。

与 S17 动量策略的区别：
- S17 聚焦"动量延续"（涨幅排名前 N% + 均线多头），偏趋势跟踪；
- S22 聚焦"相对强度 + 加速"（中期涨幅阈值 + 短期加速 + 放量），偏情绪/资金关注，
  两者互补而非重复。

数据：日K线（纯技术面，三市场可用，零额外数据依赖）。
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from typing import Optional
from .base import make_result, clean_klines
from indicators import calc_sma
import config  # noqa: F401

S22_MID_PERIOD = getattr(config, "S22_MID_PERIOD", 20)          # 中期统计窗口
S22_SHORT_PERIOD = getattr(config, "S22_SHORT_PERIOD", 5)       # 短期加速窗口
S22_MID_RETURN_MIN = getattr(config, "S22_MID_RETURN_MIN", 0.15)  # 中期涨幅下限（15%）
S22_VOLUME_LOOKBACK = getattr(config, "S22_VOLUME_LOOKBACK", 60)   # 成交量对比基准
S22_WEIGHT = getattr(config, "S22_WEIGHT", 0.05)                # 默认权重


def check_s22_relative_strength(
    klines: list[dict],
    fundamental: Optional[dict] = None,
    money_flow: Optional[dict] = None,
) -> dict:
    """S22 相对强度策略判定。

    Args:
        klines: 日K线列表
        fundamental: 基本面数据（本策略不使用，保留统一签名）
        money_flow: 资金流数据（本策略不使用，保留统一签名）

    Returns:
        {code, name, passed, score, signal_strength, reasons, details}
    """
    reasons = []
    details = {}
    score = 0.0

    klines = clean_klines(klines)

    min_required = max(S22_MID_PERIOD + 1, S22_VOLUME_LOOKBACK)
    if not klines or len(klines) < min_required:
        return make_result(
            code="S22", name="相对强度策略",
            passed=False,
            score=0,
            reasons=[f"K线数据不足（{len(klines) if klines else 0}条，需≥{min_required}）"],
            details=details,
        )

    closes = [k["close"] for k in klines]
    volumes = [k.get("volume", 0) or 0 for k in klines]

    # ── 条件一：中期强度（核心通过条件）──
    mid_start = closes[-(S22_MID_PERIOD + 1)]
    mid_end = closes[-1]
    mid_return = (mid_end / mid_start - 1) if mid_start > 0 else 0.0
    ma20 = calc_sma(closes, 20)
    above_ma20 = bool(ma20 and mid_end > ma20[-1])
    mid_pass = mid_return >= S22_MID_RETURN_MIN and above_ma20

    details["mid_return_pct"] = f"{mid_return * 100:.2f}%"
    details["mid_return"] = round(mid_return, 4)
    details["above_ma20"] = above_ma20

    if mid_pass:
        reasons.append(f"中期强度: 近{S22_MID_PERIOD}日涨幅{mid_return*100:.2f}% >= {S22_MID_RETURN_MIN*100:.0f}% 且收盘>MA20")
    else:
        parts = []
        if mid_return < S22_MID_RETURN_MIN:
            parts.append(f"涨幅{mid_return*100:.2f}% < {S22_MID_RETURN_MIN*100:.0f}%")
        if not above_ma20:
            parts.append("收盘<=MA20")
        reasons.append("中期强度不足: " + "；".join(parts))

    # ── 条件二：短期加速（核心通过条件）──
    short_start = closes[-(S22_SHORT_PERIOD + 1)]
    short_return = (mid_end / short_start - 1) if short_start > 0 else 0.0
    short_pass = short_return > 0

    details["short_return_pct"] = f"{short_return * 100:.2f}%"
    details["short_return"] = round(short_return, 4)

    if short_pass:
        reasons.append(f"短期加速: 近{S22_SHORT_PERIOD}日涨幅{short_return*100:.2f}% > 0（动能为正）")
    else:
        reasons.append(f"短期衰减: 近{S22_SHORT_PERIOD}日涨幅{short_return*100:.2f}% <= 0")

    # ── 条件三：放量确认（辅助加分）──
    vol_mid = sum(volumes[-S22_MID_PERIOD:]) / S22_MID_PERIOD if S22_MID_PERIOD > 0 else 0
    vol_base = sum(volumes[-S22_VOLUME_LOOKBACK:]) / S22_VOLUME_LOOKBACK if S22_VOLUME_LOOKBACK > 0 else 0
    volume_expand = vol_mid > vol_base * 1.1 if vol_base > 0 else False

    details["vol_mid_avg"] = round(vol_mid, 0)
    details["vol_base_avg"] = round(vol_base, 0)
    details["volume_expand"] = volume_expand

    if volume_expand:
        reasons.append(f"放量确认: 近{S22_MID_PERIOD}日均量{vol_mid:.0f} > 近{S22_VOLUME_LOOKBACK}日均量{vol_base:.0f}×1.1")

    details["conditions"] = {
        "mid_strength_pass": mid_pass,
        "short_acceleration_pass": short_pass,
        "volume_expand_pass": volume_expand,
    }

    # ── 评分：中期强度(0.5) + 短期加速(0.3) + 放量(0.2) ──
    if mid_pass:
        score += 0.5
    if short_pass:
        score += 0.3
    if volume_expand:
        score += 0.2

    # 严格通过判定：中期强度 + 短期加速 同时满足
    passed = mid_pass and short_pass

    return make_result(
        code="S22", name="相对强度策略",
        passed=passed,
        score=score,
        reasons=reasons,
        details=details,
    )


__all__ = ["check_s22_relative_strength"]
