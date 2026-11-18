"""事件驱动回测引擎。

严格无前视偏差：第t天的交易信号仅使用第t天及之前的K线数据计算。
模拟真实交易摩擦：佣金+印花税+滑点，涨跌停/停牌如实处理。

使用方式：
    config = BacktestConfig(initial_capital=100000)
    engine = BacktestEngine(strategy_func, config)
    result = engine.run(klines, fundamental=None, money_flow=None)
    # result.trades, result.daily_nav, result.metrics
"""

from dataclasses import dataclass, field
from typing import Callable, Optional


@dataclass
class BacktestConfig:
    """回测参数配置。"""
    initial_capital: float = 100000.0          # 初始资金
    commission_rate: float = 0.00025            # 佣金率（万2.5）
    stamp_tax_rate: float = 0.001               # 印花税率（千1，仅卖出）
    slippage_rate: float = 0.001                # 滑点率（0.1%）
    position_mode: str = "full"                 # 仓位模式：full全仓 / half半仓 / custom自定义
    custom_position_pct: float = 1.0            # 自定义仓位比例（position_mode=custom时生效）
    exit_mode: str = "signal"                   # 退出模式：signal信号驱动 / fixed固定持有期 / stop止损止盈
    fixed_hold_days: int = 20                   # 固定持有天数（exit_mode=fixed时生效）
    stop_loss_atr_mult: float = 2.0             # 止损ATR倍数（exit_mode=stop时生效）
    take_profit_atr_mult: float = 3.0           # 止盈ATR倍数（exit_mode=stop时生效）
    atr_period: int = 14                         # ATR计算周期
    price_limit_pct: float = 9.8                 # 涨跌停阈值（%，A股9.8，港股/美股设为999禁用）
    min_trade_days: int = 60                     # 最少K线天数（不足则不回测）
    lot_size: int = 100                          # 每手股数（A股100，港股/美股设为1）


@dataclass
class Trade:
    """单笔交易记录。"""
    date: str
    action: str          # buy / sell
    price: float
    shares: int
    amount: float
    commission: float
    stamp_tax: float
    slippage: float
    total_cost: float    # 买入时总支出，卖出时净收入
    reason: str          # 交易原因


@dataclass
class DailyNav:
    """每日净值记录。"""
    date: str
    close: float
    position: int        # 持仓股数
    market_value: float  # 持仓市值
    cash: float          # 现金
    total_nav: float     # 总净值
    daily_return: float  # 日收益率


@dataclass
class BacktestResult:
    """回测结果。"""
    stock_code: str
    stock_name: str
    config: BacktestConfig
    trades: list = field(default_factory=list)
    daily_nav: list = field(default_factory=list)
    metrics: dict = field(default_factory=dict)
    start_date: str = ""
    end_date: str = ""
    total_days: int = 0
    win_trades: int = 0
    loss_trades: int = 0
    error: str = ""

    @property
    def total_trades(self) -> int:
        return len([t for t in self.trades if t.action == "buy"])

    @property
    def win_rate(self) -> float:
        total = self.total_trades
        return self.win_trades / total if total > 0 else 0.0


class BacktestEngine:
    """事件驱动回测引擎。"""

    def __init__(self, strategy_func: Callable, config: Optional[BacktestConfig] = None):
        """
        Args:
            strategy_func: 策略判定函数，签名(klines, fundamental=None, money_flow=None) -> dict
            config: 回测参数配置
        """
        self.strategy_func = strategy_func
        self.config = config or BacktestConfig()

    def _calc_atr(self, klines: list, period: int) -> float:
        """计算ATR（平均真实波幅）。K线不足period时用全部可用数据计算，确保止损止盈早期生效。"""
        if len(klines) < 2:
            return 0.0
        trs = []
        for i in range(1, len(klines)):
            high = klines[i].get("high", 0)
            low = klines[i].get("low", 0)
            prev_close = klines[i - 1].get("close", 0)
            tr = max(high - low, abs(high - prev_close), abs(low - prev_close))
            trs.append(tr)
        if not trs:
            return 0.0
        use_period = min(period, len(trs))
        return sum(trs[-use_period:]) / use_period

    def _is_limit_up(self, kline: dict) -> bool:
        """判断是否涨停（无法买入）。"""
        pct = kline.get("pct_chg", 0)
        if pct is None:
            return False
        return pct >= self.config.price_limit_pct

    def _is_limit_down(self, kline: dict) -> bool:
        """判断是否跌停（无法卖出）。"""
        pct = kline.get("pct_chg", 0)
        if pct is None:
            return False
        return pct <= -self.config.price_limit_pct

    def _is_suspended(self, kline: dict) -> bool:
        """判断是否停牌（成交量为0）。"""
        vol = kline.get("volume", 0)
        return vol is None or vol <= 0

    def _calc_buy_cost(self, price: float, shares: int) -> dict:
        """计算买入成本明细。"""
        amount = price * shares
        commission = max(amount * self.config.commission_rate, 5.0)  # 最低5元
        stamp_tax = 0.0  # 买入无印花税
        slippage = amount * self.config.slippage_rate
        total_cost = amount + commission + slippage
        return {
            "amount": amount,
            "commission": commission,
            "stamp_tax": stamp_tax,
            "slippage": slippage,
            "total_cost": total_cost,
        }

    def _calc_sell_cost(self, price: float, shares: int) -> dict:
        """计算卖出成本明细。"""
        amount = price * shares
        commission = max(amount * self.config.commission_rate, 5.0)
        stamp_tax = amount * self.config.stamp_tax_rate
        slippage = amount * self.config.slippage_rate
        net_income = amount - commission - stamp_tax - slippage
        return {
            "amount": amount,
            "commission": commission,
            "stamp_tax": stamp_tax,
            "slippage": slippage,
            "total_cost": net_income,  # 卖出时为净收入
        }

    def _position_pct(self) -> float:
        """获取仓位比例。"""
        if self.config.position_mode == "full":
            return 1.0
        elif self.config.position_mode == "half":
            return 0.5
        elif self.config.position_mode == "custom":
            return self.config.custom_position_pct
        return 1.0

    def run(self, klines: list, stock_code: str = "", stock_name: str = "",
            fundamental: Optional[dict] = None, money_flow: Optional[list] = None) -> BacktestResult:
        """执行回测。

        Args:
            klines: 历史日K线列表（按日期升序），每根含 date/open/high/low/close/volume/pct_chg
            stock_code: 股票代码
            stock_name: 股票名称
            fundamental: 基本面数据（如策略需要）
            money_flow: 资金流数据（如策略需要）

        Returns:
            BacktestResult: 回测结果
        """
        result = BacktestResult(stock_code=stock_code, stock_name=stock_name, config=self.config)

        if not klines or len(klines) < self.config.min_trade_days:
            result.error = f"K线数据不足（需要≥{self.config.min_trade_days}天，实际{len(klines) if klines else 0}天）"
            return result

        cash = self.config.initial_capital
        position = 0          # 持仓股数
        avg_cost = 0.0        # 持仓均价
        atr_at_buy = 0.0
        buy_date_idx = None
        trades = []
        daily_navs = []
        prev_nav = self.config.initial_capital

        pos_pct = self._position_pct()

        for i in range(self.config.min_trade_days - 1, len(klines)):
            current_k = klines[i]
            date = current_k.get("date", "")
            close = current_k.get("close", 0)
            if close <= 0:
                continue

            # 用截至当天的历史数据计算策略信号（无前视偏差）
            historical = klines[:i + 1]
            try:
                signal = self.strategy_func(historical, fundamental=fundamental, money_flow=money_flow)
                passed = signal.get("passed", False)
                score = signal.get("score", 0)
            except Exception:
                passed = False
                score = 0

            # 停牌检查
            suspended = self._is_suspended(current_k)

            # === 卖出逻辑 ===
            if position > 0:
                should_sell = False
                sell_reason = ""

                if self.config.exit_mode == "signal":
                    if not passed:
                        should_sell = True
                        sell_reason = "策略信号消失"

                # 止损止盈（stop模式或叠加）
                if self.config.exit_mode == "stop" or (position > 0 and atr_at_buy > 0):
                    atr = atr_at_buy
                    if atr > 0:
                        stop_price = avg_cost - self.config.stop_loss_atr_mult * atr
                        target_price = avg_cost + self.config.take_profit_atr_mult * atr
                        if close <= stop_price:
                            should_sell = True
                            sell_reason = f"触发止损（{close:.2f}≤{stop_price:.2f}）"
                        elif close >= target_price:
                            should_sell = True
                            sell_reason = f"触发止盈（{close:.2f}≥{target_price:.2f}）"

                # fixed模式：用索引计算持有天数
                if self.config.exit_mode == "fixed" and not should_sell:
                    if buy_date_idx is not None and (i - buy_date_idx) >= self.config.fixed_hold_days:
                        should_sell = True
                        sell_reason = f"持有{self.config.fixed_hold_days}天到期"

                if should_sell and not suspended and not self._is_limit_down(current_k):
                    sell_price = close * (1 - self.config.slippage_rate)
                    cost = self._calc_sell_cost(sell_price, position)
                    pnl = cost["total_cost"] - avg_cost * position
                    trades.append(Trade(
                        date=date, action="sell", price=round(sell_price, 3),
                        shares=position, amount=round(cost["amount"], 2),
                        commission=round(cost["commission"], 2),
                        stamp_tax=round(cost["stamp_tax"], 2),
                        slippage=round(cost["slippage"], 2),
                        total_cost=round(cost["total_cost"], 2),
                        reason=sell_reason,
                    ))
                    cash += cost["total_cost"]
                    if pnl > 0:
                        result.win_trades += 1
                    else:
                        result.loss_trades += 1
                    position = 0
                    avg_cost = 0.0
                    buy_date_idx = None
                    atr_at_buy = 0.0

            # === 买入逻辑 ===
            if position == 0 and passed and score > 0 and not suspended and not self._is_limit_up(current_k):
                buy_price = close * (1 + self.config.slippage_rate)
                target_value = cash * pos_pct
                shares = int(target_value / buy_price / self.config.lot_size) * self.config.lot_size
                if shares >= self.config.lot_size:
                    cost = self._calc_buy_cost(buy_price, shares)
                    if cost["total_cost"] <= cash:
                        trades.append(Trade(
                            date=date, action="buy", price=round(buy_price, 3),
                            shares=shares, amount=round(cost["amount"], 2),
                            commission=round(cost["commission"], 2),
                            stamp_tax=round(cost["stamp_tax"], 2),
                            slippage=round(cost["slippage"], 2),
                            total_cost=round(cost["total_cost"], 2),
                            reason=f"策略信号通过（score={score:.2f}）",
                        ))
                        cash -= cost["total_cost"]
                        position = shares
                        avg_cost = buy_price
                        buy_date_idx = i
                        atr_at_buy = self._calc_atr(historical, self.config.atr_period)

            # === 记录每日净值 ===
            market_value = position * close
            total_nav = cash + market_value
            daily_return = (total_nav - prev_nav) / prev_nav if prev_nav > 0 else 0.0
            daily_navs.append(DailyNav(
                date=date, close=close, position=position,
                market_value=round(market_value, 2), cash=round(cash, 2),
                total_nav=round(total_nav, 2), daily_return=round(daily_return, 6),
            ))
            prev_nav = total_nav

        # 期末净值已包含持仓市值，无需额外平仓操作

        result.trades = trades
        result.daily_nav = daily_navs
        result.total_days = len(daily_navs)
        if daily_navs:
            result.start_date = daily_navs[0].date
            result.end_date = daily_navs[-1].date

        # 计算绩效指标
        from .metrics import calculate_metrics
        result.metrics = calculate_metrics(daily_navs, trades, self.config.initial_capital)

        return result
