"""策略参数遍历优化。

网格搜索策略参数区间，输出每组参数的回测绩效，
帮助找到历史最优参数区间，并分析参数敏感性。

注意：参数优化存在过拟合风险，最优参数不代表未来有效。
优化结果仅供研究参考，不构成投资建议。
"""

import itertools
from dataclasses import dataclass, field
from typing import Callable, Dict, Optional

from .engine import BacktestEngine, BacktestConfig

# 优化目标指标 -> 中文名（用于结果文案，随所选 metric 动态显示，不写死“夏普”）
_METRIC_LABEL = {
    "sharpe_ratio": "夏普比率",
    "annual_return": "年化收益率",
    "max_drawdown": "最大回撤",
    "calmar_ratio": "卡玛比率",
}


@dataclass
class OptimizationResult:
    """参数优化结果。"""
    strategy_name: str
    param_grid: dict
    results: list = field(default_factory=list)  # [{params, metrics, rank}]
    best_params: dict = field(default_factory=dict)
    best_metrics: dict = field(default_factory=dict)
    sensitivity: dict = field(default_factory=dict)  # 参数敏感性分析
    total_combinations: int = 0
    metric: str = "sharpe_ratio"  # 实际优化目标指标
    error: str = ""


def optimize_params(
    strategy_func: Callable,
    klines: list,
    param_grid: Dict[str, list],
    backtest_config: Optional[BacktestConfig] = None,
    metric: str = "sharpe_ratio",
    stock_code: str = "",
    stock_name: str = "",
) -> OptimizationResult:
    """网格搜索策略参数。

    Args:
        strategy_func: 策略判定函数
        klines: 历史K线数据
        param_grid: 参数网格，如 {"S18_ROE_MIN": [10, 12, 15, 18, 20]}
        backtest_config: 回测配置
        metric: 优化目标指标（sharpe_ratio / annual_return / max_drawdown / calmar_ratio）
        stock_code: 股票代码
        stock_name: 股票名称

    Returns:
        OptimizationResult: 优化结果
    """
    result = OptimizationResult(
        strategy_name=getattr(strategy_func, "__name__", "unknown"),
        param_grid=param_grid,
        metric=metric,
    )

    if not param_grid:
        result.error = "参数网格为空"
        return result

    # 生成所有参数组合
    keys = sorted(param_grid.keys())
    values = [param_grid[k] for k in keys]
    combinations = list(itertools.product(*values))
    result.total_combinations = len(combinations)

    if not combinations:
        result.error = "参数组合为空"
        return result

    # config 全局参数只导入一次（不在每个参数组合循环内重复 import / 改写 sys.path）
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    import config as global_config

    bt_config = backtest_config or BacktestConfig()
    all_results = []

    for combo in combinations:
        params = dict(zip(keys, combo))

        original_values = {}
        for key, val in params.items():
            if hasattr(global_config, key):
                original_values[key] = getattr(global_config, key)
                setattr(global_config, key, val)

        try:
            engine = BacktestEngine(strategy_func, bt_config)
            bt_result = engine.run(klines, stock_code=stock_code, stock_name=stock_name)
            m = bt_result.metrics
            all_results.append({
                "params": params,
                "metrics": m,
                "sharpe_ratio": m.get("sharpe_ratio", 0),
                "annual_return": m.get("annual_return", 0),
                "max_drawdown": m.get("max_drawdown", 0),
                "calmar_ratio": m.get("calmar_ratio", 0),
                "win_rate": m.get("win_rate", 0),
                "total_trades": m.get("total_trades", 0),
            })
        except Exception as e:
            all_results.append({
                "params": params,
                "metrics": {},
                "sharpe_ratio": -999,
                "annual_return": -999,
                "max_drawdown": 999,
                "calmar_ratio": -999,
                "win_rate": 0,
                "total_trades": 0,
                "error": str(e),
            })
        finally:
            # 恢复原始参数
            for key, val in original_values.items():
                setattr(global_config, key, val)

    # 按优化指标排序
    reverse = metric != "max_drawdown"  # max_drawdown越小越好，其他越大越好
    all_results.sort(key=lambda x: x.get(metric, 0), reverse=reverse)

    # 排名
    for i, r in enumerate(all_results):
        r["rank"] = i + 1

    result.results = all_results
    if all_results:
        best = all_results[0]
        result.best_params = best["params"]
        result.best_metrics = best["metrics"]

    # 参数敏感性分析：每个参数变化时指标的波动范围
    sensitivity = {}
    for key in keys:
        values_for_key = {}
        for r in all_results:
            v = r["params"].get(key)
            if v not in values_for_key:
                values_for_key[v] = []
            values_for_key[v].append(r.get(metric, 0))
        sensitivity[key] = {
            "values": {str(v): round(sum(ms) / len(ms), 4) if ms else 0 for v, ms in values_for_key.items()},
            "range": round(max(sum(ms) / len(ms) for ms in values_for_key.values()) -
                           min(sum(ms) / len(ms) for ms in values_for_key.values()), 4) if values_for_key else 0,
        }
    result.sensitivity = sensitivity

    return result


def format_optimization_result(opt_result: OptimizationResult, top_n: int = 10) -> str:
    """格式化参数优化结果。"""
    lines = []
    lines.append("=" * 60)
    lines.append(f"参数优化结果：{opt_result.strategy_name}")
    lines.append("=" * 60)
    lines.append(f"参数组合总数: {opt_result.total_combinations}")
    metric_label = _METRIC_LABEL.get(opt_result.metric, opt_result.metric)
    lines.append(f"优化目标: {metric_label}")
    lines.append("")

    if opt_result.error:
        lines.append(f"错误: {opt_result.error}")
        return "\n".join(lines)

    lines.append(f"最优参数: {opt_result.best_params}")
    bm = opt_result.best_metrics
    lines.append(f"  年化收益: {bm.get('annual_return', 0)*100:.2f}%")
    lines.append(f"  最大回撤: {bm.get('max_drawdown', 0)*100:.2f}%")
    lines.append(f"  夏普比率: {bm.get('sharpe_ratio', 0):.2f}")
    lines.append(f"  胜率: {bm.get('win_rate', 0)*100:.1f}%")
    lines.append("")

    lines.append(f"Top {min(top_n, len(opt_result.results))} 参数组合:")
    lines.append("-" * 60)
    for r in opt_result.results[:top_n]:
        lines.append(f"  #{r['rank']} {r['params']}")
        lines.append(f"     夏普={r.get('sharpe_ratio', 0):.2f}  年化={r.get('annual_return', 0)*100:.1f}%  "
                     f"回撤={r.get('max_drawdown', 0)*100:.1f}%  交易={r.get('total_trades', 0)}次")
    lines.append("")

    lines.append("参数敏感性分析:")
    for key, sens in opt_result.sensitivity.items():
        lines.append(f"  {key}: 波动范围={sens['range']:.4f}")
        for v, avg in sens["values"].items():
            lines.append(f"    {v} → 平均{metric_label}={avg:.4f}")

    lines.append("")
    lines.append("注：参数优化存在过拟合风险，历史最优参数不代表未来有效。")
    lines.append("   优化结果仅供研究参考，不构成投资建议。")
    lines.append("=" * 60)
    return "\n".join(lines)
