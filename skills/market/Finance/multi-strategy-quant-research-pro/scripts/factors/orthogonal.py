# -*- coding: utf-8 -*-
"""因子正交化：消除因子共线性，提升IC纯度。

三大功能：
1. 因子相关性矩阵：Pearson相关系数，识别高度相关因子对
2. Gram-Schmidt正交化：将相关因子转为正交因子
3. 风格中性化：对市值/行业/波动率做回归取残差，消除风格暴露

纯Python标准库实现，无外部依赖。
"""

import math
from typing import Optional


def pearson_corr(x: list[float], y: list[float]) -> Optional[float]:
    """计算Pearson相关系数（成对剔除None，样本不足返回None）。"""
    if len(x) != len(y):
        return None
    pairs = [(xi, yi) for xi, yi in zip(x, y) if xi is not None and yi is not None]
    if len(pairs) < 3:
        return None
    xs = [p[0] for p in pairs]
    ys = [p[1] for p in pairs]
    n = len(xs)
    mx = sum(xs) / n
    my = sum(ys) / n
    num = sum((xs[i] - mx) * (ys[i] - my) for i in range(n))
    dx = math.sqrt(sum((xs[i] - mx) ** 2 for i in range(n)))
    dy = math.sqrt(sum((ys[i] - my) ** 2 for i in range(n)))
    if dx == 0 or dy == 0:
        return None
    return num / (dx * dy)


def _mean_std(values: list[float]):
    """返回（均值，标准差），自动剔除None；有效样本<2时标准差为0。"""
    valid = [v for v in values if v is not None]
    if not valid:
        return 0.0, 0.0
    mean = sum(valid) / len(valid)
    if len(valid) < 2:
        return mean, 0.0
    var = sum((v - mean) ** 2 for v in valid) / len(valid)
    return mean, math.sqrt(var)


def calc_correlation_matrix(factor_matrix: dict[str, list[float]]) -> dict:
    """计算因子相关性矩阵。

    Args:
        factor_matrix: {factor_name: [factor_values]}，各因子值列表等长

    Returns:
        dict: {names, matrix, pairs, highly_correlated, avg_abs_correlation}
    """
    names = list(factor_matrix.keys())
    n = len(names)
    matrix = [[0.0] * n for _ in range(n)]
    pairs = []

    for i in range(n):
        matrix[i][i] = 1.0
        for j in range(i + 1, n):
            corr = pearson_corr(factor_matrix[names[i]], factor_matrix[names[j]])
            if corr is not None:
                matrix[i][j] = round(corr, 4)
                matrix[j][i] = round(corr, 4)
                pairs.append({
                    "factor_a": names[i],
                    "factor_b": names[j],
                    "correlation": round(corr, 4),
                    "abs_correlation": round(abs(corr), 4),
                })

    # 高度相关因子对（|r| > 0.7）
    highly_correlated = [p for p in pairs if p["abs_correlation"] > 0.7]
    pairs.sort(key=lambda x: x["abs_correlation"], reverse=True)

    return {
        "names": names,
        "matrix": matrix,
        "pairs": pairs,
        "highly_correlated": highly_correlated,
        "avg_abs_correlation": round(sum(p["abs_correlation"] for p in pairs) / len(pairs), 4) if pairs else 0,
    }


def _factor_variance(factor_matrix: dict[str, list[float]], name: str) -> float:
    """单个因子的方差（剔除None，样本不足返回0）。"""
    vals = [v for v in factor_matrix[name] if v is not None]
    if len(vals) < 2:
        return 0.0
    mean = sum(vals) / len(vals)
    return sum((v - mean) ** 2 for v in vals) / len(vals)


def gram_schmidt_orthogonalize(factor_matrix: dict[str, list[float]]) -> dict:
    """Gram-Schmidt正交化。

    将相关因子转为正交因子，正交后因子间相关性为0。
    按因子方差从高到低排序，优先保留高方差（信息量更大）因子。

    Args:
        factor_matrix: {factor_name: [factor_values]}

    Returns:
        dict: {orthogonal_matrix, explained_variance, n_original, n_orthogonal}
        explained_variance 中 orthogonal_variance 为标准化前的残差方差，
        retention=残差方差/原始方差，表示去除前置因子后保留的自身信息比例。
    """
    names = list(factor_matrix.keys())
    if not names:
        return {"orthogonal_matrix": {}, "explained_variance": [], "n_original": 0, "n_orthogonal": 0}

    n_stocks = len(factor_matrix[names[0]])
    sorted_names = sorted(names, key=lambda nm: _factor_variance(factor_matrix, nm), reverse=True)

    orthogonal = {}
    explained = []

    for idx, name in enumerate(sorted_names):
        vals = list(factor_matrix[name])
        # 对已正交化的因子逐一线性投影取残差
        for prev_name in sorted_names[:idx]:
            prev_vals = orthogonal[prev_name]
            corr = pearson_corr(vals, prev_vals)
            if corr is None or abs(corr) <= 1e-10:
                continue
            mean_v, std_v = _mean_std(vals)
            mean_p, std_p = _mean_std(prev_vals)
            if std_p <= 0 or std_v <= 0:
                continue
            beta = corr * std_v / std_p
            # 显式中心化：残差 = 均值 + (自身偏离) - 斜率*(前置因子偏离)，保持原尺度
            resid = []
            for i in range(n_stocks):
                if vals[i] is None or prev_vals[i] is None:
                    resid.append(vals[i])
                else:
                    resid.append(mean_v + (vals[i] - mean_v) - beta * (prev_vals[i] - mean_p))
            vals = resid

        # 标准化前先统计残差方差，得到真实信息保留比例
        orig_var = _factor_variance(factor_matrix, name)
        _, orth_std = _mean_std(vals)
        orth_var = orth_std ** 2

        # 标准化为零均值、单位方差，作为后续正交基
        valid = [v for v in vals if v is not None]
        if len(valid) >= 2:
            m = sum(valid) / len(valid)
            std = math.sqrt(sum((v - m) ** 2 for v in valid) / len(valid))
            if std > 0:
                vals = [(v - m) / std if v is not None else None for v in vals]
        orthogonal[name] = vals

        explained.append({
            "factor": name,
            "original_variance": round(orig_var, 6),
            "orthogonal_variance": round(orth_var, 6),
            "retention": round(orth_var / orig_var, 4) if orig_var > 0 else 0,
        })

    return {
        "orthogonal_matrix": orthogonal,
        "explained_variance": explained,
        "n_original": len(names),
        "n_orthogonal": len(orthogonal),
    }


def _design_row(i: int, use_mc: bool, use_vol: bool, n_ind: int,
                market_cap, industry_dummies, volatility) -> list[float]:
    """构建第 i 个样本的设计矩阵行（固定列数；启用列缺失时以0填充，等价于该风格无暴露）。"""
    row = [1.0]  # 截距项
    if use_mc:
        mc = market_cap[i] if i < len(market_cap) else None
        row.append(math.log(mc) if (mc is not None and mc > 0) else 0.0)
    if use_vol:
        vol = volatility[i] if i < len(volatility) else None
        row.append(float(vol) if vol is not None else 0.0)
    if n_ind > 0 and i < len(industry_dummies):
        row.extend(float(x) for x in industry_dummies[i][1:1 + n_ind])
    elif n_ind > 0:
        row.extend([0.0] * n_ind)
    return row


def neutralize_factor(factor_values: list[float],
                      market_cap: list[float] = None,
                      industry_dummies: list[list[int]] = None,
                      volatility: list[float] = None) -> list[float]:
    """因子风格中性化：对市值/行业/波动率做线性回归取残差。

    用最小二乘法解析解：β = (X'X)^(-1) X'y，残差 = y - Xβ。

    Args:
        factor_values: 因子值列表（None 位置原样保留）
        market_cap: 市值列表（取对数后作为自变量）
        industry_dummies: 行业虚拟变量矩阵，每行一个股票的one-hot
        volatility: 波动率列表

    Returns:
        list[float]: 中性化后的因子残差；有效样本不足时原样返回。
    """
    n = len(factor_values)
    if n < 3:
        return factor_values

    use_mc = bool(market_cap)
    use_vol = bool(volatility)
    n_ind = (len(industry_dummies[0]) - 1) if industry_dummies else 0

    # 构建自变量矩阵 X 与因变量 y（跳过因子值缺失样本）
    X = []
    y = []
    valid_rows = []
    for i in range(n):
        if factor_values[i] is None:
            continue
        X.append(_design_row(i, use_mc, use_vol, n_ind, market_cap, industry_dummies, volatility))
        y.append(factor_values[i])
        valid_rows.append(i)

    if not X:  # 全部为 None，无样本可回归
        return factor_values

    n_vars = len(X[0])
    if len(X) < n_vars + 1:  # 样本量不足以估计全部系数
        return factor_values

    # 最小二乘解析解，高斯消元解 (X'X)β = X'y
    XtX = [[0.0] * n_vars for _ in range(n_vars)]
    Xty = [0.0] * n_vars
    for i in range(len(X)):
        for j in range(n_vars):
            Xty[j] += X[i][j] * y[i]
            for k in range(n_vars):
                XtX[j][k] += X[i][j] * X[i][k]

    aug = [XtX[j] + [Xty[j]] for j in range(n_vars)]

    for col in range(n_vars):
        pivot = max(range(col, n_vars), key=lambda r: abs(aug[r][col]))
        aug[col], aug[pivot] = aug[pivot], aug[col]
        if abs(aug[col][col]) < 1e-12:
            continue
        for row in range(n_vars):
            if row != col:
                factor = aug[row][col] / aug[col][col]
                for k in range(col, n_vars + 1):
                    aug[row][k] -= factor * aug[col][k]

    beta = [0.0] * n_vars
    for i in range(n_vars):
        if abs(aug[i][i]) > 1e-12:
            beta[i] = aug[i][n_vars] / aug[i][i]

    # 计算残差（缺失位置保留 None；其余样本用同一设计行函数保证列对齐）
    residuals = []
    valid_set = set(valid_rows)
    for i in range(n):
        if factor_values[i] is None:
            residuals.append(None)
            continue
        if i not in valid_set:
            residuals.append(factor_values[i])
            continue
        row = _design_row(i, use_mc, use_vol, n_ind, market_cap, industry_dummies, volatility)
        predicted = sum(row[j] * beta[j] for j in range(n_vars))
        residuals.append(round(factor_values[i] - predicted, 6))

    return residuals


def neutralize_all_factors(factor_matrix: dict[str, list[float]],
                           market_cap: list[float] = None,
                           industry_dummies: list[list[int]] = None,
                           volatility: list[float] = None) -> dict:
    """对所有因子做风格中性化。"""
    result = {}
    for name, vals in factor_matrix.items():
        result[name] = neutralize_factor(vals, market_cap, industry_dummies, volatility)
    return result


def compare_ic_before_after(factor_matrix: dict[str, list[float]],
                            orthogonal_matrix: dict[str, list[float]],
                            future_returns: list[float]) -> dict:
    """比较正交化前后的IC。"""
    from .ic_test import calculate_ic_series

    before = {}
    after = {}
    for name in factor_matrix:
        ic_before = calculate_ic_series(factor_matrix[name], future_returns)
        before[name] = ic_before.get("ic_mean")
        if name in orthogonal_matrix:
            ic_after = calculate_ic_series(orthogonal_matrix[name], future_returns)
            after[name] = ic_after.get("ic_mean")
        else:
            after[name] = None

    comparison = []
    for name in factor_matrix:
        b = before.get(name)
        a = after.get(name)
        comparison.append({
            "factor": name,
            "ic_before": b,
            "ic_after": a,
            "ic_change": round(a - b, 4) if (a is not None and b is not None) else None,
            "improved": (a is not None and b is not None and abs(a) > abs(b)),
        })

    def _avg_abs(values: dict) -> float:
        valid = [v for v in values.values() if v is not None]
        return round(sum(abs(v) for v in valid) / len(valid), 4) if valid else 0

    return {
        "comparison": comparison,
        "avg_ic_before": _avg_abs(before),
        "avg_ic_after": _avg_abs(after),
    }
