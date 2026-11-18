#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""multi-strategy-quant-research-pro v1.1.2 策略回测独立入口。

支持三种回测模式：
1. 单策略回测：指定策略ID和股票代码，回测历史表现
2. 多策略对比：同一股票多策略净值对比
3. 参数优化：网格搜索策略参数区间

使用方式：
    python run_backtest.py --strategy S09 --code 600519 --days 500
    python run_backtest.py --strategy S01,S09,S17 --code 600519 --compare
    python run_backtest.py --strategy S18 --code 600519 --optimize "S18_ROE_MIN=10|12|15|18|20"
    （同一参数的多个候选值用竖线 | 分隔；多个不同参数用逗号分隔）

回测结果为历史数据统计，不代表未来收益，不构成投资建议。
"""

import argparse
import os
import sys
import json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from strategies import STRATEGY_REGISTRY
from backtest import BacktestEngine, BacktestConfig, optimize_params
from backtest.metrics import format_metrics
from backtest.optimizer import format_optimization_result
from data.a_share import fetch_daily_kline


def get_kline(code: str, days: int = 500) -> list:
    """获取股票历史日K线。"""
    try:
        klines = fetch_daily_kline(code, days=days)
        return klines or []
    except Exception as e:
        print(f"获取K线失败: {e}")
        return []


def run_single_backtest(strategy_id: str, code: str, days: int, bt_config: BacktestConfig):
    """单策略回测。"""
    if strategy_id not in STRATEGY_REGISTRY:
        print(f"错误：策略 {strategy_id} 不存在。可用策略：{', '.join(sorted(STRATEGY_REGISTRY.keys()))}")
        return

    strategy_info = STRATEGY_REGISTRY[strategy_id]
    strategy_func = strategy_info["func"]
    strategy_name = strategy_info["name"]

    print(f"正在回测：{strategy_id} {strategy_name} | 股票：{code} | 近{days}个交易日")
    print("-" * 60)

    klines = get_kline(code, days)
    if not klines:
        print("错误：无法获取K线数据")
        return

    print(f"获取K线：{len(klines)}根，{klines[0]['date']} ~ {klines[-1]['date']}")
    print()

    engine = BacktestEngine(strategy_func, bt_config)
    result = engine.run(klines, stock_code=code, stock_name=code)

    if result.error:
        print(f"回测错误：{result.error}")
        return

    print(f"回测区间：{result.start_date} ~ {result.end_date}（{result.total_days}个交易日）")
    print(f"交易次数：{result.total_trades}次完整买卖回合")
    print()

    if result.metrics:
        print(format_metrics(result.metrics))

    # 交易明细
    if result.trades:
        print()
        print("交易明细（最近10笔）：")
        print("-" * 60)
        for t in result.trades[-10:]:
            print(f"  {t.date} {t.action:4s} 价格={t.price:8.3f} 数量={t.shares:6d} "
                  f"金额={t.amount:12.2f} 原因={t.reason}")

    return result


def run_compare(strategy_ids: list, code: str, days: int, bt_config: BacktestConfig):
    """多策略对比回测。"""
    klines = get_kline(code, days)
    if not klines:
        print("错误：无法获取K线数据")
        return

    print(f"多策略对比：{code} | {len(klines)}根K线 | {klines[0]['date']} ~ {klines[-1]['date']}")
    print("-" * 70)

    results = []
    for sid in strategy_ids:
        if sid not in STRATEGY_REGISTRY:
            print(f"跳过不存在的策略：{sid}")
            continue
        strategy_func = STRATEGY_REGISTRY[sid]["func"]
        strategy_name = STRATEGY_REGISTRY[sid]["name"]
        engine = BacktestEngine(strategy_func, bt_config)
        result = engine.run(klines, stock_code=code, stock_name=code)
        m = result.metrics
        results.append({
            "strategy": sid,
            "name": strategy_name,
            "annual_return": m.get("annual_return", 0),
            "max_drawdown": m.get("max_drawdown", 0),
            "sharpe": m.get("sharpe_ratio", 0),
            "win_rate": m.get("win_rate", 0),
            "trades": m.get("total_trades", 0),
        })

    # 按夏普排序
    results.sort(key=lambda x: x["sharpe"], reverse=True)

    print(f"{'策略':<6} {'名称':<12} {'年化收益':>10} {'最大回撤':>10} {'夏普':>8} {'胜率':>8} {'交易次数':>8}")
    print("-" * 70)
    for r in results:
        print(f"{r['strategy']:<6} {r['name']:<12} {r['annual_return']*100:>9.2f}% "
              f"{r['max_drawdown']*100:>9.2f}% {r['sharpe']:>8.2f} "
              f"{r['win_rate']*100:>7.1f}% {r['trades']:>8d}")
    print()
    print("注：以上为历史回测数据，不代表未来收益，不构成投资建议。")


def run_optimize(strategy_id: str, code: str, days: int, param_grid_str: str, bt_config: BacktestConfig):
    """参数优化。"""
    if strategy_id not in STRATEGY_REGISTRY:
        print(f"错误：策略 {strategy_id} 不存在")
        return

    # 解析参数网格
    param_grid = {}
    for item in param_grid_str.split(","):
        if "=" in item:
            key, vals = item.split("=", 1)
            param_grid[key.strip()] = [float(v) if "." in v else int(v) for v in vals.split("|")]

    if not param_grid:
        print("错误：参数网格格式无效。示例：S18_ROE_MIN=10|12|15|18|20")
        return

    klines = get_kline(code, days)
    if not klines:
        print("错误：无法获取K线数据")
        return

    print(f"参数优化：{strategy_id} {STRATEGY_REGISTRY[strategy_id]['name']} | {code}")
    print(f"参数网格：{param_grid}")
    print(f"K线：{len(klines)}根")
    print("-" * 60)

    strategy_func = STRATEGY_REGISTRY[strategy_id]["func"]
    opt = optimize_params(
        strategy_func, klines, param_grid,
        backtest_config=bt_config, metric="sharpe_ratio",
        stock_code=code, stock_name=code,
    )

    print(format_optimization_result(opt, top_n=10))


def main():
    parser = argparse.ArgumentParser(description="multi-strategy-quant-research-pro 策略回测工具")
    parser.add_argument("--strategy", required=True, help="策略ID，如 S09；多策略用逗号分隔")
    parser.add_argument("--code", required=True, help="股票代码，如 600519")
    parser.add_argument("--days", type=int, default=500, help="回测交易日数（默认500）")
    parser.add_argument("--capital", type=float, default=100000, help="初始资金（默认100000）")
    parser.add_argument("--exit-mode", choices=["signal", "fixed", "stop"], default="signal",
                        help="退出模式：signal信号驱动/fixed固定持有/stop止损止盈")
    parser.add_argument("--hold-days", type=int, default=20, help="固定持有天数（exit-mode=fixed时）")
    parser.add_argument("--position", choices=["full", "half", "custom"], default="full", help="仓位模式")
    parser.add_argument("--compare", action="store_true", help="多策略对比模式")
    parser.add_argument("--optimize", type=str, default="", help="参数优化，格式：KEY=v1|v2|v3")
    parser.add_argument("--output", type=str, default="", help="输出JSON文件路径")
    args = parser.parse_args()

    bt_config = BacktestConfig(
        initial_capital=args.capital,
        exit_mode=args.exit_mode,
        fixed_hold_days=args.hold_days,
        position_mode=args.position,
    )

    strategy_ids = [s.strip() for s in args.strategy.split(",")]

    if args.optimize:
        if len(strategy_ids) != 1:
            print("参数优化仅支持单策略")
            return
        run_optimize(strategy_ids[0], args.code, args.days, args.optimize, bt_config)
    elif args.compare or len(strategy_ids) > 1:
        run_compare(strategy_ids, args.code, args.days, bt_config)
    else:
        result = run_single_backtest(strategy_ids[0], args.code, args.days, bt_config)
        if args.output and result:
            output_data = {
                "stock_code": result.stock_code,
                "strategy": strategy_ids[0],
                "start_date": result.start_date,
                "end_date": result.end_date,
                "total_days": result.total_days,
                "metrics": result.metrics,
                "trades": [t.__dict__ for t in result.trades],
                "daily_nav": [d.__dict__ for d in result.daily_nav],
            }
            with open(args.output, "w", encoding="utf-8") as f:
                json.dump(output_data, f, ensure_ascii=False, indent=2)
            print(f"\n回测结果已保存到：{args.output}")


if __name__ == "__main__":
    main()
