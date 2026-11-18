"""S20 资金流策略（进阶策略）

算法核心（严格语义）：
基于公开逐日资金流向数据，检测主力资金持续净流入与量价资金背离，
作为机构资金关注/抄底的信号。

1. 主力净流入率（核心通过条件）：近 S20_LOOKBACK 个交易日，
   主力净流入合计 / 同期成交额合计 >= S20_NET_INFLOW_RATIO_MIN（默认 3%），
   反映主力资金在统计期内的真实买入强度。
2. 连续净流入天数（核心通过条件，满足其一即可）：
   从最新交易日起连续主力净流入天数 >= S20_CONSECUTIVE_DAYS_MIN（默认 3 日）。
3. 量价资金背离（辅助加分，不参与通过判定）：
   近 S20_LOOKBACK 日股价下跌但主力净流入为正——价格被抛售但主力逆势吸筹，
   为潜在底部信号，加分但不单独决定通过。

数据可用性（如实）：
- A股/港股：push2his 历史节点可达时返回逐日多日资金流；延迟节点通常仅最近1日，
  数据不足时如实不通过（不伪造连续天数）。
- 美股：公开接口不返回该口径资金流数据，如实不通过。

数据源：东方财富公开资金流向API（逐日主力净流入/超大单/大单/中单/小单）。
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from typing import Optional
from .base import make_result, clean_klines
import config  # noqa: F401

S20_LOOKBACK = getattr(config, "S20_LOOKBACK", 10)                  # 统计窗口（近N个交易日）
S20_NET_INFLOW_RATIO_MIN = getattr(config, "S20_NET_INFLOW_RATIO_MIN", 0.03)  # 主力净流入率下限（3%）
S20_CONSECUTIVE_DAYS_MIN = getattr(config, "S20_CONSECUTIVE_DAYS_MIN", 3)     # 连续净流入天数下限
S20_WEIGHT = getattr(config, "S20_WEIGHT", 0.06)                    # 默认权重


def _extract_flow_list(money_flow) -> list[dict]:
    """兼容 money_flow 的两种真实形态，返回逐日资金流列表。"""
    if isinstance(money_flow, list):
        return money_flow
    if isinstance(money_flow, dict):
        # dict 形态可能含 daily 列表或 klines 列表
        for key in ("daily", "klines", "flows", "data"):
            v = money_flow.get(key)
            if isinstance(v, list):
                return v
    return []


def check_s20_money_flow(
    klines: list[dict],
    fundamental: Optional[dict] = None,
    money_flow: Optional[dict] = None,
) -> dict:
    """S20 资金流策略判定。

    Args:
        klines: 日K线列表（用于计算同期成交额）
        fundamental: 基本面数据（本策略不使用，保留统一签名）
        money_flow: 资金流数据（list[dict] 逐日，或 dict 含 daily 列表）

    Returns:
        {code, name, passed, score, signal_strength, reasons, details}
    """
    reasons = []
    details = {}
    score = 0.0

    klines = clean_klines(klines)
    flows = _extract_flow_list(money_flow)

    details["lookback"] = S20_LOOKBACK
    details["flow_data_days"] = len(flows)

    if not flows:
        return make_result(
            code="S20", name="资金流策略",
            passed=False,
            score=0,
            reasons=["无资金流数据（美股无公开口径，或当前通道仅最近1日且不足统计窗口），如实不通过"],
            details=details,
        )

    # 取最近 S20_LOOKBACK 日资金流（列表按日期升序，最旧在前）
    recent_flows = flows[-S20_LOOKBACK:] if len(flows) >= S20_LOOKBACK else flows
    n = len(recent_flows)

    if n < min(S20_LOOKBACK, S20_CONSECUTIVE_DAYS_MIN):
        return make_result(
            code="S20", name="资金流策略",
            passed=False,
            score=0,
            reasons=[f"资金流数据不足（仅{n}日，需≥{min(S20_LOOKBACK, S20_CONSECUTIVE_DAYS_MIN)}日），如实不通过"],
            details=details,
        )

    # ── 条件一：主力净流入率（核心通过条件）──
    total_net = sum(f.get("main_net_inflow", 0) or 0 for f in recent_flows)
    # 同期成交额：用K线 amount 字段（若有），否则用 close*volume 估算
    recent_klines = klines[-n:] if len(klines) >= n else klines
    total_amount = 0.0
    for k in recent_klines:
        amt = k.get("amount")
        if amt and amt > 0:
            total_amount += amt
        else:
            vol = k.get("volume", 0) or 0
            close = k.get("close", 0) or 0
            total_amount += close * vol

    net_ratio = (total_net / total_amount) if total_amount > 0 else 0.0
    inflow_pass = net_ratio >= S20_NET_INFLOW_RATIO_MIN

    details["total_net_inflow"] = round(total_net, 2)
    details["total_amount"] = round(total_amount, 2)
    details["net_inflow_ratio"] = round(net_ratio, 4)
    details["net_inflow_ratio_pct"] = f"{net_ratio * 100:.2f}%"

    if inflow_pass:
        reasons.append(f"近{n}日主力净流入率 {net_ratio*100:.2f}% >= {S20_NET_INFLOW_RATIO_MIN*100:.0f}%")
    else:
        reasons.append(f"近{n}日主力净流入率 {net_ratio*100:.2f}% < {S20_NET_INFLOW_RATIO_MIN*100:.0f}%")

    # ── 条件二：连续主力净流入天数（核心通过条件）──
    consecutive = 0
    for f in reversed(flows):
        if (f.get("main_net_inflow", 0) or 0) > 0:
            consecutive += 1
        else:
            break
    consecutive_pass = consecutive >= S20_CONSECUTIVE_DAYS_MIN

    details["consecutive_inflow_days"] = consecutive

    if consecutive_pass:
        reasons.append(f"连续{consecutive}日主力净流入 >= {S20_CONSECUTIVE_DAYS_MIN}日")
    else:
        reasons.append(f"连续净流入{consecutive}日 < {S20_CONSECUTIVE_DAYS_MIN}日")

    # ── 条件三：量价资金背离（辅助加分）──
    # 近 n 日股价涨跌幅
    price_change = 0.0
    if len(recent_klines) >= 2:
        price_change = (recent_klines[-1]["close"] / recent_klines[0]["close"] - 1) if recent_klines[0]["close"] > 0 else 0.0
    divergence_pass = price_change < 0 and total_net > 0
    details["price_change_pct"] = f"{price_change * 100:.2f}%"
    details["divergence"] = divergence_pass

    if divergence_pass:
        reasons.append(f"量价资金背离: 近{n}日股价{price_change*100:.2f}%但主力净流入{total_net/1e8:.2f}亿（逆势吸筹）")

    details["conditions"] = {
        "net_inflow_ratio_pass": inflow_pass,
        "consecutive_inflow_pass": consecutive_pass,
        "divergence_pass": divergence_pass,
    }

    # ── 评分：净流入率(0.4) + 连续天数(0.4) + 背离(0.2) ──
    if inflow_pass:
        score += 0.4
    if consecutive_pass:
        score += 0.4
    if divergence_pass:
        score += 0.2

    # 严格通过判定：净流入率 或 连续天数 满足其一（核心条件为"或"逻辑）
    passed = inflow_pass or consecutive_pass

    return make_result(
        code="S20", name="资金流策略",
        passed=passed,
        score=score,
        reasons=reasons,
        details=details,
    )


__all__ = ["check_s20_money_flow"]
