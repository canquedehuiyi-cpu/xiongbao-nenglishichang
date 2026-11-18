"""multi-strategy-quant-research-pro v1.1.2 回测引擎模块。

事件驱动回测框架，严格无前视偏差：
- 按交易日逐天推进，第t天的信号仅使用第t天及之前的数据
- 模拟真实交易成本（佣金+印花税+滑点）
- 涨跌停/停牌如实处理（涨停买不进、跌停卖不出、停牌跳过）
- 支持信号驱动/固定持有期/止损止盈三种退出模式
- 输出交易明细、每日净值、绩效指标
- 回测精度增强：行业中性+分层回测+因子衰减+过拟合检测

本模块为纯Python标准库实现，零外部依赖。
回测结果为历史数据统计，不代表未来收益，不构成投资建议。
"""

from .engine import BacktestEngine, BacktestResult, BacktestConfig
from .metrics import calculate_metrics, MetricsResult
from .optimizer import optimize_params, OptimizationResult
from .precision import (
    stratified_backtest,
    industry_neutral_backtest,
    factor_decay_curve,
    overfitting_detection,
    parameter_stability_test,
)
from .signal import collect_signal_returns

__all__ = [
    "BacktestEngine",
    "BacktestResult",
    "BacktestConfig",
    "calculate_metrics",
    "MetricsResult",
    "optimize_params",
    "OptimizationResult",
    "stratified_backtest",
    "industry_neutral_backtest",
    "factor_decay_curve",
    "overfitting_detection",
    "parameter_stability_test",
    "collect_signal_returns",
]
