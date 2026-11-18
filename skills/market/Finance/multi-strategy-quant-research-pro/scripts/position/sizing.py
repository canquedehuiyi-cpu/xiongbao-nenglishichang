# -*- coding: utf-8 -*-
"""动态仓位管理：四种仓位模型。

1. 凯利公式仓位：基于胜率和盈亏比，理论最优仓位
2. ATR波动率仓位：基于ATR，每只股票风险相同
3. 风险平价仓位：每只股票贡献相同组合风险
4. 信号强度仓位：信号越强仓位越大

所有模型都有最大仓位约束和最小仓位过滤。
"""



def kelly_position(win_rate: float, win_loss_ratio: float,
                   max_position: float = 0.25, kelly_fraction: float = 0.5) -> dict:
    """凯利公式仓位。

    f* = (bp - q) / b
    其中：b=赔率（盈利/亏损），p=胜率，q=1-p

    实际使用中通常用"半凯利"（kelly_fraction=0.5）来降低波动。

    Args:
        win_rate: 胜率（0-1）
        win_loss_ratio: 盈亏比（平均盈利/平均亏损）
        max_position: 单票最大仓位
        kelly_fraction: 凯利比例（0.5=半凯利，更保守）

    Returns:
        dict: {position, kelly_full, kelly_fractional, method}
    """
    if win_rate <= 0 or win_rate >= 1 or win_loss_ratio <= 0:
        return {"position": 0, "method": "kelly", "note": "参数无效"}

    p = win_rate
    q = 1 - p
    b = win_loss_ratio
    kelly_full = (b * p - q) / b if b > 0 else 0
    kelly_full = max(0, kelly_full)  # 不做空
    kelly_fractional = kelly_full * kelly_fraction
    position = min(kelly_fractional, max_position)

    return {
        "position": round(position, 4),
        "kelly_full": round(kelly_full, 4),
        "kelly_fractional": round(kelly_fractional, 4),
        "win_rate": win_rate,
        "win_loss_ratio": win_loss_ratio,
        "method": "kelly",
        "note": f"凯利比例{kelly_fraction:.0%}，单票上限{max_position:.0%}",
    }


def atr_position(price: float, atr: float, risk_per_trade: float = 0.02,
                 total_capital: float = 100000, max_position: float = 0.25) -> dict:
    """ATR波动率仓位。

    仓位 = 风险预算 / (ATR × 价格)
    每只股票的最大亏损 = risk_per_trade × total_capital（当价格波动2×ATR时）

    Args:
        price: 当前价格
        atr: ATR(14)值
        risk_per_trade: 每笔交易风险比例（默认2%）
        total_capital: 总资金
        max_position: 单票最大仓位

    Returns:
        dict: {position, shares, risk_amount, atr_ratio, method}
    """
    if price <= 0 or atr <= 0:
        return {"position": 0, "method": "atr", "note": "价格或ATR无效"}

    risk_amount = total_capital * risk_per_trade
    # 止损距离 = 2 × ATR
    stop_distance = 2 * atr
    # 可买股数 = 风险金额 / 止损距离
    shares = risk_amount / stop_distance if stop_distance > 0 else 0
    position_value = shares * price
    position = position_value / total_capital if total_capital > 0 else 0
    position = min(position, max_position)

    atr_ratio = atr / price if price > 0 else 0

    return {
        "position": round(position, 4),
        "shares": int(shares),
        "risk_amount": round(risk_amount, 2),
        "stop_distance": round(stop_distance, 4),
        "atr_ratio": round(atr_ratio, 4),
        "method": "atr",
        "note": f"每笔风险{risk_per_trade:.0%}，止损距离2×ATR",
    }


def signal_strength_position(signal_score: float, max_position: float = 0.25,
                             min_position: float = 0.05) -> dict:
    """信号强度仓位。

    信号越强，仓位越大。信号强度0-100映射到min_position-max_position。

    Args:
        signal_score: 信号强度评分（0-100）
        max_position: 最大仓位
        min_position: 最小仓位（低于此不建仓）

    Returns:
        dict: {position, signal_level, method}
    """
    if signal_score <= 0:
        return {"position": 0, "signal_level": "无信号", "method": "signal_strength"}

    # 线性映射：0分→0，100分→max_position
    raw_position = (signal_score / 100.0) * max_position

    if raw_position < min_position:
        position = 0
        signal_level = "信号过弱"
    elif raw_position < max_position * 0.4:
        position = raw_position
        signal_level = "弱信号"
    elif raw_position < max_position * 0.7:
        position = raw_position
        signal_level = "中等信号"
    else:
        position = raw_position
        signal_level = "强信号"

    return {
        "position": round(position, 4),
        "signal_score": signal_score,
        "signal_level": signal_level,
        "method": "signal_strength",
        "note": f"信号强度{signal_score}/100",
    }


def risk_parity_position(volatilities: list[float], max_position: float = 0.25,
                         codes: list = None) -> dict:
    """风险平价仓位：每只股票贡献相同组合风险。

    仓位与波动率成反比：w_i ∝ 1/σ_i

    Args:
        volatilities: 各股票年化波动率列表
        max_position: 单票最大仓位
        codes: 股票代码列表

    Returns:
        dict: {positions, holdings, method}
    """
    n = len(volatilities)
    if n == 0:
        return {"positions": [], "holdings": [], "method": "risk_parity"}

    # 持仓数不足以满足单票上限时（n*max<1），放宽到 1/n 保证权重和恰为1且不超过生效上限
    max_position = max(max_position, 1.0 / n)

    # 倒数加权
    inv_vol = []
    for v in volatilities:
        if v and v > 0:
            inv_vol.append(1.0 / v)
        else:
            inv_vol.append(0)

    total = sum(inv_vol)
    if total == 0:
        positions = [1.0 / n] * n
    else:
        positions = [w / total for w in inv_vol]

    # 单票上限约束（水填充）
    for _ in range(50):
        over = [i for i in range(n) if positions[i] > max_position + 1e-10]
        if not over:
            break
        excess = sum(positions[i] - max_position for i in over)
        for i in over:
            positions[i] = max_position
        under = [i for i in range(n) if positions[i] < max_position - 1e-10]
        if not under:
            break
        under_total = sum(positions[i] for i in under)
        if under_total > 0:
            for i in under:
                positions[i] += excess * (positions[i] / under_total)
        else:
            # 未封顶仓位全为0时平均均摊，迭代收敛，保证总仓位为1
            add = excess / len(under)
            for i in under:
                positions[i] += add

    holdings = []
    for i, w in enumerate(positions):
        if w > 0.001:
            code = codes[i] if codes and i < len(codes) else f"#{i}"
            holdings.append({"code": code, "weight": round(w * 100, 2),
                             "volatility": round(volatilities[i], 4) if volatilities[i] else None})
    holdings.sort(key=lambda x: x["weight"], reverse=True)

    return {
        "positions": [round(w, 6) for w in positions],
        "holdings": holdings,
        "method": "risk_parity",
        "note": "仓位与波动率成反比，每只股票贡献相同风险",
    }


def calculate_position(stock_info: dict, method: str = "signal_strength",
                       max_position: float = 0.25, total_capital: float = 100000) -> dict:
    """统一仓位计算入口。

    Args:
        stock_info: 股票信息字典，含price/atr/win_rate/win_loss_ratio/signal_score等
        method: 仓位方法（kelly/atr/signal_strength/risk_parity）
        max_position: 单票最大仓位
        total_capital: 总资金

    Returns:
        dict: 仓位计算结果
    """
    if method == "kelly":
        return kelly_position(
            stock_info.get("win_rate", 0.5),
            stock_info.get("win_loss_ratio", 1.0),
            max_position
        )
    elif method == "atr":
        return atr_position(
            stock_info.get("price", 0),
            stock_info.get("atr", 0),
            stock_info.get("risk_per_trade", 0.02),
            total_capital,
            max_position
        )
    elif method == "signal_strength":
        return signal_strength_position(
            stock_info.get("signal_score", 50),
            max_position
        )
    else:
        return signal_strength_position(50, max_position)
