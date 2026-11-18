"""回测绩效指标计算。

基于每日净值序列和交易记录计算：
- 绝对收益：总收益率、年化收益率
- 风险指标：最大回撤、年化波动率、下行波动率
- 风险调整收益：夏普比率、索提诺比率、卡玛比率
- 交易统计：胜率、盈亏比、平均持仓天数
- 月度收益表

所有指标基于历史数据计算，不代表未来收益。
"""

import datetime
import math
from dataclasses import dataclass


def _calendar_hold_days(buy_date, sell_date):
    """按自然日计算单笔买入到卖出的持仓天数，日期缺失/无法解析时返回None。"""
    try:
        d_buy = datetime.datetime.strptime(str(buy_date)[:10], "%Y-%m-%d")
        d_sell = datetime.datetime.strptime(str(sell_date)[:10], "%Y-%m-%d")
        return max((d_sell - d_buy).days, 0)
    except (ValueError, TypeError):
        return None


@dataclass
class MetricsResult:
    """绩效指标结果。"""
    total_return: float = 0.0           # 总收益率
    annual_return: float = 0.0          # 年化收益率
    max_drawdown: float = 0.0           # 最大回撤
    annual_volatility: float = 0.0      # 年化波动率
    downside_volatility: float = 0.0    # 下行波动率
    sharpe_ratio: float = 0.0           # 夏普比率（无风险利率2%）
    sortino_ratio: float = 0.0          # 索提诺比率
    calmar_ratio: float = 0.0           # 卡玛比率
    win_rate: float = 0.0               # 胜率
    profit_loss_ratio: float = 0.0      # 盈亏比
    avg_hold_days: float = 0.0          # 平均持仓天数
    total_trades: int = 0               # 总交易次数（完整买卖回合）
    monthly_returns: dict = None        # 月度收益率 {YYYY-MM: return%}
    final_nav: float = 0.0              # 期末净值
    initial_capital: float = 0.0        # 初始资金


def calculate_metrics(daily_navs: list, trades: list, initial_capital: float) -> dict:
    """计算回测绩效指标。

    Args:
        daily_navs: 每日净值记录列表（DailyNav对象）
        trades: 交易记录列表（Trade对象）
        initial_capital: 初始资金

    Returns:
        dict: 绩效指标字典
    """
    result = MetricsResult(initial_capital=initial_capital)
    if not daily_navs:
        return result.__dict__

    navs = [d.total_nav for d in daily_navs]
    returns = [d.daily_return for d in daily_navs]
    result.final_nav = navs[-1]

    # 总收益率
    result.total_return = (navs[-1] - initial_capital) / initial_capital if initial_capital > 0 else 0.0

    # 年化收益率（按252个交易日）
    total_days = len(navs)
    if total_days > 1 and navs[0] > 0:
        result.annual_return = (navs[-1] / navs[0]) ** (252.0 / total_days) - 1.0

    # 最大回撤
    peak = navs[0]
    max_dd = 0.0
    for nav in navs:
        if nav > peak:
            peak = nav
        dd = (peak - nav) / peak if peak > 0 else 0.0
        if dd > max_dd:
            max_dd = dd
    result.max_drawdown = max_dd

    # 年化波动率
    if len(returns) > 1:
        mean_ret = sum(returns) / len(returns)
        variance = sum((r - mean_ret) ** 2 for r in returns) / (len(returns) - 1)
        result.annual_volatility = math.sqrt(variance) * math.sqrt(252)

        # 下行波动率
        downside = [r for r in returns if r < 0]
        if downside:
            down_var = sum(r ** 2 for r in downside) / len(downside)
            result.downside_volatility = math.sqrt(down_var) * math.sqrt(252)

    # 夏普比率（无风险利率2%）
    risk_free = 0.02
    if result.annual_volatility > 0:
        result.sharpe_ratio = (result.annual_return - risk_free) / result.annual_volatility

    # 索提诺比率
    if result.downside_volatility > 0:
        result.sortino_ratio = (result.annual_return - risk_free) / result.downside_volatility

    # 卡玛比率
    if result.max_drawdown > 0:
        result.calmar_ratio = result.annual_return / result.max_drawdown

    # 交易统计
    buy_trades = [t for t in trades if t.action == "buy"]
    sell_trades = [t for t in trades if t.action == "sell"]
    result.total_trades = len(sell_trades)  # 完整回合数

    if sell_trades:
        # 计算每笔交易盈亏（简化：用卖出净收入 - 买入总成本）
        # 按顺序配对
        profits = []
        hold_days_list = []
        buy_idx = 0
        for sell in sell_trades:
            if buy_idx < len(buy_trades):
                buy = buy_trades[buy_idx]
                pnl = sell.total_cost - buy.total_cost
                profits.append(pnl)
                # 持仓天数：按买入/卖出日期真实配对计算自然日
                held = _calendar_hold_days(buy.date, sell.date)
                if held is not None:
                    hold_days_list.append(held)
                buy_idx += 1

        wins = [p for p in profits if p > 0]
        losses = [p for p in profits if p <= 0]
        result.win_rate = len(wins) / len(profits) if profits else 0.0

        avg_win = sum(wins) / len(wins) if wins else 0.0
        avg_loss = abs(sum(losses) / len(losses)) if losses else 0.0
        result.profit_loss_ratio = avg_win / avg_loss if avg_loss > 0 else float("inf") if avg_win > 0 else 0.0
        result.avg_hold_days = round(sum(hold_days_list) / len(hold_days_list), 1) if hold_days_list else 0.0

    # 月度收益
    monthly = {}
    for d in daily_navs:
        month = d.date[:7] if len(d.date) >= 7 else "unknown"
        if month not in monthly:
            monthly[month] = {"start": d.total_nav, "end": d.total_nav}
        monthly[month]["end"] = d.total_nav

    monthly_returns = {}
    prev_end = initial_capital
    for month in sorted(monthly.keys()):
        m = monthly[month]
        # 用月初值（上月末）计算本月收益
        month_ret = (m["end"] - prev_end) / prev_end if prev_end > 0 else 0.0
        monthly_returns[month] = round(month_ret * 100, 2)
        prev_end = m["end"]
    result.monthly_returns = monthly_returns

    return result.__dict__


def format_metrics(metrics: dict) -> str:
    """格式化绩效指标为可读文本。"""
    lines = []
    lines.append("=" * 50)
    lines.append("回测绩效指标")
    lines.append("=" * 50)
    lines.append(f"初始资金:     {metrics.get('initial_capital', 0):,.2f}")
    lines.append(f"期末净值:     {metrics.get('final_nav', 0):,.2f}")
    lines.append(f"总收益率:     {metrics.get('total_return', 0)*100:.2f}%")
    lines.append(f"年化收益率:   {metrics.get('annual_return', 0)*100:.2f}%")
    lines.append(f"最大回撤:     {metrics.get('max_drawdown', 0)*100:.2f}%")
    lines.append(f"年化波动率:   {metrics.get('annual_volatility', 0)*100:.2f}%")
    lines.append(f"夏普比率:     {metrics.get('sharpe_ratio', 0):.2f}")
    lines.append(f"索提诺比率:   {metrics.get('sortino_ratio', 0):.2f}")
    lines.append(f"卡玛比率:     {metrics.get('calmar_ratio', 0):.2f}")
    lines.append(f"交易次数:     {metrics.get('total_trades', 0)}")
    lines.append(f"平均持仓天数: {metrics.get('avg_hold_days', 0):.1f} 天")
    lines.append(f"胜率:         {metrics.get('win_rate', 0)*100:.1f}%")
    plr = metrics.get('profit_loss_ratio', 0)
    lines.append(f"盈亏比:       {plr:.2f}" if plr != float('inf') else "盈亏比:       ∞（无亏损交易）")
    lines.append("=" * 50)
    lines.append("注：以上为历史回测数据，不代表未来收益，不构成投资建议。")
    return "\n".join(lines)
