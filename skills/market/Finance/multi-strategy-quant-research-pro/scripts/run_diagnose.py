"""单股诊断命令：分析单只股票的当前技术状态与趋势信号，供持有/离场决策参考。

用法：
    python run_diagnose.py --code 601869            # 长飞光纤
    python run_diagnose.py --code 600519 --days 250

输出内容（全部基于 skill 真实数据与策略判定，无伪造）：
    1. 当前技术状态：最新价、均线结构、RSI、近20/60日涨跌幅
    2. 全部策略当前信号：逐策略判定（通过的列出，未通过给出原因）
    3. 趋势策略历史回测绩效（真实K线信号回放）
    4. 综合技术判断：基于信号强度与回测的确定性规则结论（技术参考，非投资建议）

判断规则（确定性、如实）：
    - 趋势类策略（S02/S09/S17/S21/S23）通过数 ≥2 → 多头信号偏强
    - 趋势类策略通过数 =1 → 多头信号一般
    - 趋势类策略通过数 =0 → 无明显多头信号
    - 结合最近5笔回测交易的胜/亏分布给出持有/离场/观望的技术参考
"""

import sys
import os
import argparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from data import (
    fetch_daily_kline,
    fetch_financial_summary,
    fetch_valuation,
)
from strategies import STRATEGY_REGISTRY
from backtest import BacktestEngine, BacktestConfig
from backtest.signal import clean_klines
from indicators.technical import calc_rsi, calc_sma

# 趋势类策略（用于综合判断）
_TREND_STRATEGIES = ("S02", "S09", "S17", "S21", "S23")
# 回测默认使用的主要趋势策略
_BT_STRATEGY = "S09"


def _secid_of(code: str) -> str:
    """按代码前缀推断东财 secid 市场段（A股）。"""
    if code.startswith(("6", "9")):
        return "1"
    return "0"


def _backtest_strategy(strategy_id, klines, code, name, days):
    """用指定策略在真实K线上回测，返回绩效摘要。"""
    func = STRATEGY_REGISTRY[strategy_id]["func"]

    def strat(kl, fundamental=None, money_flow=None):
        r = func(kl, fundamental, money_flow)
        return {"passed": bool(r.get("passed")), "score": float(r.get("score") or 0)}

    try:
        eng = BacktestEngine(strat, BacktestConfig(min_trade_days=20, lot_size=100))
        result = eng.run(clean_klines(klines), stock_code=code, stock_name=name)
        metrics = getattr(result, "metrics", {}) or {}
        recent = getattr(result, "trades", None) or []
        recent_trades = recent[-5:]
        return {
            "strategy": strategy_id,
            "total_return": round(metrics.get("total_return") or 0, 4),
            "annual_return": round(metrics.get("annual_return") or 0, 4),
            "win_rate": round(metrics.get("win_rate") or 0, 4),
            "profit_loss_ratio": round(metrics.get("profit_loss_ratio") or 0, 4),
            "total_trades": metrics.get("total_trades") or getattr(result, "total_trades", 0),
            "recent_trades": [
                {
                    "date": getattr(t, "date", ""),
                    "action": getattr(t, "action", ""),
                    "price": round(float(getattr(t, "price", 0) or 0), 2),
                    "reason": getattr(t, "reason", ""),
                }
                for t in recent_trades
            ],
        }
    except Exception as e:  # 回测失败如实返回空摘要（不伪造）
        return {"strategy": strategy_id, "error": str(e)}


def run_diagnose(code: str, days: int = 250) -> dict:
    """执行单股诊断。

    Args:
        code: 股票代码（A股），如 601869
        days: 回测交易日数

    Returns:
        dict: {state, signals, backtest, verdict, disclaimer}
    """
    secid = _secid_of(code)
    klines = fetch_daily_kline(code, days=days, market_code=secid)
    if not klines:
        return {"error": "K线数据获取失败（代码可能无效或数据源不可达）"}

    fundamental = {}
    try:
        fundamental = fetch_financial_summary(code) or {}
    except Exception:
        fundamental = {}
    valuation = {}
    try:
        valuation = fetch_valuation(code) or {}
    except Exception:
        valuation = {}

    closes = [float(k["close"]) for k in klines]
    last = closes[-1]
    n = len(closes)

    # ── 当前技术状态 ──
    ma5 = calc_sma(closes, 5)[-1] if n >= 5 else None
    ma10 = calc_sma(closes, 10)[-1] if n >= 10 else None
    ma20 = calc_sma(closes, 20)[-1] if n >= 20 else None
    ma60 = calc_sma(closes, 60)[-1] if n >= 60 else None
    rsi = None
    rsi_vals = calc_rsi(klines, period=14)
    if rsi_vals:
        rsi = round(rsi_vals[-1], 2)
    ret20 = (last / closes[-21] - 1) * 100 if n >= 21 else None
    ret60 = (last / closes[-61] - 1) * 100 if n >= 61 else None

    state = {
        "code": code,
        "latest_date": klines[-1]["date"],
        "latest_close": round(last, 2),
        "ma5": round(ma5, 2) if ma5 else None,
        "ma10": round(ma10, 2) if ma10 else None,
        "ma20": round(ma20, 2) if ma20 else None,
        "ma60": round(ma60, 2) if ma60 else None,
        "rsi14": rsi,
        "ret_20d_pct": round(ret20, 2) if ret20 is not None else None,
        "ret_60d_pct": round(ret60, 2) if ret60 is not None else None,
        "close_vs_ma20": "上方" if ma20 and last > ma20 else "下方" if ma20 else None,
        "close_vs_ma60": "上方" if ma60 and last > ma60 else "下方" if ma60 else None,
        "ma_structure": "多头排列" if (ma5 and ma10 and ma20 and ma5 > ma10 > ma20) else "非多头排列",
    }

    # ── 全部策略当前信号 ──
    signals = []
    for sid, meta in STRATEGY_REGISTRY.items():
        try:
            r = meta["func"](klines, fundamental, None)
            signals.append({
                "strategy": sid,
                "name": meta["name"],
                "passed": bool(r.get("passed")),
                "score": float(r.get("score") or 0),
                "reasons": (r.get("reasons") or [])[:2],
            })
        except Exception as e:
            signals.append({"strategy": sid, "name": meta["name"], "passed": False,
                            "score": 0, "reasons": [f"判定异常: {e}"]})

    passed_signals = [s for s in signals if s["passed"]]
    trend_passed = [s for s in passed_signals if s["strategy"] in _TREND_STRATEGIES]

    # ── 趋势策略历史回测 ──
    backtest = _backtest_strategy(_BT_STRATEGY, klines, code, " ", days)

    # ── 综合技术判断（确定性规则，技术参考）──
    trend_count = len(trend_passed)
    if trend_count >= 2:
        trend_read = "多头信号偏强"
    elif trend_count == 1:
        trend_read = "多头信号一般"
    else:
        trend_read = "无明显多头信号"

    # 回测近期表现：最近5笔 买入→卖出 的盈亏方向
    recent_bias = None
    bt = backtest
    if not bt.get("error") and bt.get("recent_trades"):
        buys = [t for t in bt["recent_trades"] if t["action"] == "buy"]
        sells = [t for t in bt["recent_trades"] if t["action"] == "sell"]
        if buys and sells:
            buy_prices = {t["date"]: t["price"] for t in buys}
            wins = losses = 0
            for t in sells:
                # 找最近的买入价
                closest_buy = None
                for bd, bp in sorted(buy_prices.items()):
                    if bd <= t["date"]:
                        closest_buy = bp
                    else:
                        break
                if closest_buy:
                    if t["price"] >= closest_buy:
                        wins += 1
                    else:
                        losses += 1
            if wins + losses > 0:
                recent_bias = f"近{wins + losses}笔交易 {wins}胜{losses}亏"

    if trend_read == "多头信号偏强" and (recent_bias is None or "胜" in recent_bias):
        verdict = "偏多（持有）"
    elif trend_read == "无明显多头信号" or (recent_bias and "亏" in recent_bias and trend_count == 0):
        verdict = "偏空（离场/规避）"
    else:
        verdict = "观望（信号中性，需更多确认）"

    return {
        "state": state,
        "signals": signals,
        "passed_signals": passed_signals,
        "trend_count": trend_count,
        "trend_read": trend_read,
        "backtest": backtest,
        "recent_bias": recent_bias,
        "valuation": {k: v for k, v in valuation.items() if v not in (None, "", "-")},
        "verdict": verdict,
        "verdict_basis": [
            f"趋势类策略通过 {trend_count} 个（{trend_read}）",
            (f"回测近期：{recent_bias}") if recent_bias else "回测近期无完整买卖配对",
            f"最新收盘 {state['latest_close']:.2f}{'，位于MA20上方' if state['close_vs_ma20'] == '上方' else '，位于MA20下方'}",
        ],
        "disclaimer": "以上为历史与技术分析参考，不构成投资建议。股市有风险，投资需谨慎。",
    }


def _fmt(d: dict) -> str:
    lines = []
    s = d["state"]
    lines.append("=" * 60)
    lines.append(f"单股诊断：{s['code']} | 最新交易日 {s['latest_date']}")
    lines.append("=" * 60)
    lines.append("【当前技术状态】")
    ma60_txt = f"{s['ma60']:.2f}" if s["ma60"] else "N/A"
    lines.append(f"  最新收盘: {s['latest_close']:.2f} | MA5={s['ma5']:.2f} MA10={s['ma10']:.2f} MA20={s['ma20']:.2f} MA60={ma60_txt}")
    lines.append(f"  均线结构: {s['ma_structure']} | 相对MA20: {s['close_vs_ma20']} | 相对MA60: {s['close_vs_ma60']} | RSI14: {s['rsi14']}")
    lines.append(f"  近20日: {s['ret_20d_pct']}% | 近60日: {s['ret_60d_pct']}%")
    if d.get("valuation"):
        lines.append("  估值: " + " | ".join(f"{k}={v}" for k, v in list(d['valuation'].items())[:6]))
    lines.append("")
    lines.append("【全部策略当前信号】")
    passed = d.get("passed_signals") or []
    if passed:
        for p in passed:
            lines.append(f"  ✓ {p['strategy']} {p['name']} (score={p['score']:.2f})")
    else:
        lines.append("  当前无策略通过（市场环境/个股形态未触发）")
    lines.append("")
    lines.append(f"【趋势策略历史回测（{_BT_STRATEGY}）】")
    bt = d.get("backtest") or {}
    if bt.get("error"):
        lines.append(f"  回测失败: {bt['error']}")
    else:
        lines.append(f"  总收益: {(bt.get('total_return') or 0) * 100:.2f}% | 年化: {(bt.get('annual_return') or 0) * 100:.2f}% | 胜率: {(bt.get('win_rate') or 0) * 100:.1f}% | 盈亏比: {bt.get('profit_loss_ratio') or 0:.2f} | 交易: {bt.get('total_trades') or 0} 次")
        if bt.get("recent_trades"):
            lines.append("  最近交易:")
            for t in bt["recent_trades"][-6:]:
                lines.append(f"    {t['date']} {t['action']} @{t['price']:.2f} {t['reason']}")
    lines.append("")
    lines.append(f"【综合技术判断】{d.get('verdict')}")
    for b in d.get("verdict_basis") or []:
        lines.append(f"  依据: {b}")
    lines.append("")
    lines.append(d.get("disclaimer", ""))
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        prog="run_diagnose.py",
        description="multi-strategy-quant-research-pro 单股诊断（技术参考，非投资建议）")
    parser.add_argument("--code", required=True, help="股票代码，如 601869")
    parser.add_argument("--days", type=int, default=250, help="回测交易日数（默认250）")
    args = parser.parse_args()

    result = run_diagnose(args.code, days=args.days)
    if "error" in result:
        print(f"诊断失败: {result['error']}")
        return
    print(_fmt(result))


if __name__ == "__main__":
    main()
