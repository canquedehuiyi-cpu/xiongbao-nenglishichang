"""CSV 报告生成模块。

将筛选结果输出为 UTF-8 with BOM 编码的 CSV 文件（Excel / WPS 直接打开不乱码），
字段与文本报告保持同口径，便于用户导入表格工具做二次排序、筛选与分析。

字段说明：
- 排名/市场/代码/名称/评分/共识度：与筛选结果一致
- 命中策略：多策略以 "|" 分隔（避免与 CSV 逗号冲突）
- 信号时间窗：各命中策略的信号触发日期（如 S19 金叉日），多策略以 "|" 分隔
- 子条件命中：各策略内部子条件命中状态（✓/✗），多策略以 "|" 分隔
- 支撑/压力：近N日真实K线高低点（技术位，非预测承诺）
- 行业：标的所属行业（未知时留空）
"""

import os
import csv
from datetime import datetime


def _extract_signal_window(strategy_results: dict, hits: list) -> str:
    """从命中策略的 details 中提取信号触发日期（信号时间窗）。

    优先字段：signal_date / golden_cross_date / cross_date / signal_window。
    缺失的策略不展示；全部缺失时返回空字符串。
    """
    parts = []
    for sid in hits:
        res = strategy_results.get(sid) or {}
        details = res.get("details") or {}
        sig = (details.get("signal_date")
               or details.get("golden_cross_date")
               or details.get("cross_date")
               or details.get("signal_window"))
        if sig:
            parts.append(f"{sid}:{sig}")
    return "|".join(parts)


def _extract_sub_conditions(strategy_results: dict, hits: list) -> str:
    """从命中策略的 details.conditions 中提取子条件命中状态。

    格式：S08:放量✓,突破✓ | S11:换手✓,振幅✗
    无 conditions 字段的策略不展示；全部缺失时返回空字符串。
    """
    parts = []
    for sid in hits:
        res = strategy_results.get(sid) or {}
        details = res.get("details") or {}
        conds = details.get("conditions")
        if not isinstance(conds, dict) or not conds:
            continue
        sub = []
        for k, v in conds.items():
            mark = "✓" if v else "✗"
            sub.append(f"{k}{mark}")
        if sub:
            parts.append(f"{sid}:" + ",".join(sub))
    return "|".join(parts)


def generate_csv_report(results, output_dir, market_env, strategy_stats, total_passed):
    """生成选股结果 CSV 报告。

    Args:
        results: 已按评分排序的筛选结果列表
        output_dir: 输出目录
        market_env: 市场环境信息（用于文件名区分市场）
        strategy_stats: 策略统计（本模块不使用，保留参数以统一报告签名）
        total_passed: 实际通过筛选的标的总数

    Returns:
        str: CSV 文件绝对路径
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    market = market_env.get("market", "全部") if market_env else "全部"
    filename = f"选股结果_{market}_{timestamp}.csv"
    filepath = os.path.join(output_dir, filename)
    os.makedirs(output_dir, exist_ok=True)

    with open(filepath, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow([
            "排名", "市场", "代码", "名称", "评分", "共识度",
            "命中策略", "信号时间窗", "子条件命中", "支撑", "压力", "行业",
            "止损位(2ATR)", "止盈位(3ATR)", "波动率", "盈亏比",
        ])
        for i, s in enumerate(results, start=1):
            sr = s.get("support_resistance") or {}
            hits = s.get("strategy_hits") or []
            strategy_results = s.get("strategy_results") or {}
            signal_window = _extract_signal_window(strategy_results, hits)
            sub_conditions = _extract_sub_conditions(strategy_results, hits)
            writer.writerow([
                i,
                s.get("market", ""),
                s.get("code", ""),
                s.get("name", ""),
                f"{s.get('score', 0):.2f}",
                s.get("consensus_level", ""),
                "|".join(str(h) for h in hits),
                signal_window,
                sub_conditions,
                sr.get("support", ""),
                sr.get("resistance", ""),
                s.get("industry", ""),
                s.get("stop_loss", ""),
                s.get("take_profit", ""),
                s.get("volatility_pct", ""),
                s.get("risk_reward_ratio", ""),
            ])
    return filepath
