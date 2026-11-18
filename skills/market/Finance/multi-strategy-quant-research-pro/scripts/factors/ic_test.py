# -*- coding: utf-8 -*-
"""因子有效性检验：IC/IR计算 + 分层回测。

纯Python标准库实现，无外部依赖。
IC = 因子值与未来N日收益的Spearman秩相关系数。
IR = IC均值 / IC标准差（信息比率，>0.5为有效因子）。
"""

import math


def _valid_pairs(x, y):
    """成对剔除 None/非数值/布尔样本，保持两序列下标对应。"""
    px, py = [], []
    for a, b in zip(x, y):
        if isinstance(a, bool) or isinstance(b, bool):
            continue
        if isinstance(a, (int, float)) and isinstance(b, (int, float)):
            px.append(a)
            py.append(b)
    return px, py


def _rank(values):
    """计算秩（相同值取平均秩）。"""
    indexed = sorted(range(len(values)), key=lambda i: values[i])
    ranks = [0.0] * len(values)
    i = 0
    while i < len(indexed):
        j = i
        while j + 1 < len(indexed) and values[indexed[j+1]] == values[indexed[i]]:
            j += 1
        avg_rank = (i + j) / 2.0 + 1
        for k in range(i, j + 1):
            ranks[indexed[k]] = avg_rank
        i = j + 1
    return ranks


def _spearman_corr(x, y):
    """Spearman秩相关系数（内部成对剔除 None/非数值）。"""
    x, y = _valid_pairs(x, y)
    if len(x) != len(y) or len(x) < 3:
        return None
    rx = _rank(x)
    ry = _rank(y)
    n = len(x)
    mx = sum(rx) / n
    my = sum(ry) / n
    num = sum((rx[i] - mx) * (ry[i] - my) for i in range(n))
    dx = math.sqrt(sum((rx[i] - mx) ** 2 for i in range(n)))
    dy = math.sqrt(sum((ry[i] - my) ** 2 for i in range(n)))
    if dx == 0 or dy == 0:
        return None
    return num / (dx * dy)


def calculate_ic_series(factor_values, future_returns):
    """计算IC（因子值与未来收益的Spearman秩相关）。

    Args:
        factor_values: list[float]，截面因子值（单期）
        future_returns: list[float]，对应标的的未来N日收益

    Returns:
        dict: {ic_mean, ic_std, ir, ic_positive_rate, ic_series}
        说明：IR 需多期IC序列（每期一个截面IC）计算均值/标准差，单期截面输入
        无法计算，ic_std 与 ir 如实返回 None。
    """
    fv, fr = _valid_pairs(factor_values, future_returns)
    if len(fv) < 5:
        return {"ic_mean": None, "ic_std": None, "ir": None,
                "ic_positive_rate": None, "ic_series": [], "note": "有效样本不足（<5期）"}

    ic = _spearman_corr(fv, fr)
    if ic is None:
        return {"ic_mean": None, "ic_std": None, "ir": None,
                "ic_positive_rate": None, "ic_series": [], "note": "无法计算IC"}

    return {
        "ic_mean": round(ic, 4),
        "ic_std": None,
        "ir": None,
        "ic_positive_rate": round(1.0 if ic > 0 else 0.0, 4),
        "ic_series": [round(ic, 4)],
        "note": "单期截面IC（IR需多期IC序列，单期输入如实返回None）",
    }


def _stratified_core(factor_values, returns, n_groups, ret_digits=4, range_digits=2):
    """分层回测公共核心：成对清洗→按因子值排序→等频分组→组均收益与多空差。

    供 factors.ic_test 与 backtest.precision 复用，保证两处分层口径一致。
    有效样本不足（少于 n_groups*2）时返回 None，由调用方按各自结构返回“不足”。

    Returns:
        (groups, long_short)：groups 每项含 group/factor_range/avg_return/count；
        long_short = 最高层平均收益 - 最底层平均收益。
    """
    fv, rt = _valid_pairs(factor_values, returns)
    if len(fv) < n_groups * 2:
        return None
    paired = sorted(zip(fv, rt), key=lambda x: x[0])
    group_size = len(paired) // n_groups
    groups = []
    for g in range(n_groups):
        start = g * group_size
        end = start + group_size if g < n_groups - 1 else len(paired)
        subgroup = paired[start:end]
        avg_ret = sum(r for _, r in subgroup) / len(subgroup) if subgroup else 0.0
        groups.append({
            "group": g + 1,
            "factor_range": (f"{subgroup[0][0]:.{range_digits}f}~{subgroup[-1][0]:.{range_digits}f}"
                             if subgroup else "N/A"),
            "avg_return": round(avg_ret, ret_digits),
            "count": len(subgroup),
        })
    long_short = groups[-1]["avg_return"] - groups[0]["avg_return"]
    return groups, long_short


def stratified_backtest(factor_values, returns, n_groups=5):
    """分层回测：按因子值分组，计算各组平均收益。

    Args:
        factor_values: list[float]，股票因子值
        returns: list[float]，对应股票的未来收益
        n_groups: 分组数（默认5层）

    Returns:
        dict: {groups: [{group, factor_range, avg_return, count}], long_short: 多空收益}
    """
    core = _stratified_core(factor_values, returns, n_groups, ret_digits=4, range_digits=2)
    if core is None:
        return {"groups": [], "long_short": None, "note": "有效样本不足"}
    groups, long_short = core
    return {
        "groups": groups,
        "long_short": round(long_short, 4),
        "note": f"第1层=因子最低，第{n_groups}层=因子最高",
    }




def evaluate_factor(factor_name, factor_values, returns, n_groups=5):
    """综合评估单个因子：IC + 分层回测。"""
    ic_result = calculate_ic_series(factor_values, returns)
    strat_result = stratified_backtest(factor_values, returns, n_groups)
    return {
        "factor": factor_name,
        "ic": ic_result,
        "stratified": strat_result,
        "verdict": _verdict(ic_result, strat_result),
    }


def _verdict(ic_result, strat_result):
    """因子有效性判断。"""
    ic = ic_result.get("ic_mean")
    ls = strat_result.get("long_short")
    if ic is None:
        return "数据不足，无法判断"
    if abs(ic) >= 0.05 and (ls is None or abs(ls) > 0):
        direction = "正向" if ic > 0 else "反向"
        return f"有效因子（IC={ic:.3f}，{direction}）"
    return f"弱有效/无效因子（IC={ic:.3f}，建议结合分层结果判断）"
