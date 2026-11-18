# -*- coding: utf-8 -*-
"""多因子合成：标准化 + 加权合成 + 因子筛选。

支持三种合成方式：
1. 等权合成：所有有效因子等权平均
2. IC加权合成：按因子IC绝对值加权
3. 自定义权重：用户指定各因子权重
"""

import math


def zscore(values):
    """z-score标准化：(x - mean) / std。"""
    valid = [v for v in values if v is not None]
    if len(valid) < 2:
        return [0.0 if v is not None else None for v in values]
    mean = sum(valid) / len(valid)
    var = sum((v - mean) ** 2 for v in valid) / (len(valid) - 1)
    std = math.sqrt(var)
    if std == 0:
        return [0.0 if v is not None else None for v in values]
    return [(v - mean) / std if v is not None else None for v in values]


def rank_normalize(values):
    """排名标准化：将因子值转为[0,1]区间的排名分。"""
    valid = [(i, v) for i, v in enumerate(values) if v is not None]
    if not valid:
        return [None] * len(values)
    sorted_idx = sorted(valid, key=lambda x: x[1])
    ranks = {}
    for rank, (idx, _) in enumerate(sorted_idx):
        ranks[idx] = rank / (len(sorted_idx) - 1) if len(sorted_idx) > 1 else 0.5
    return [ranks.get(i) for i in range(len(values))]


def composite_equal_weight(factor_matrix):
    """等权合成。

    Args:
        factor_matrix: dict[str, list[float|None]]，因子名 -> 各股票因子值

    Returns:
        list[float]: 合成后的综合得分
    """
    if not factor_matrix:
        return []
    n_stocks = len(next(iter(factor_matrix.values())))
    # 每个因子z-score标准化
    normalized = {}
    for fname, vals in factor_matrix.items():
        normalized[fname] = zscore(vals)
    # 等权平均
    result = []
    for i in range(n_stocks):
        vals = [normalized[f][i] for f in normalized if normalized[f][i] is not None]
        result.append(sum(vals) / len(vals) if vals else None)
    return result


def composite_ic_weight(factor_matrix, ic_weights):
    """IC加权合成：按因子IC绝对值加权。

    Args:
        factor_matrix: dict[str, list[float|None]]
        ic_weights: dict[str, float]，因子名 -> IC值（取绝对值作为权重）

    Returns:
        list[float]: 合成后的综合得分
    """
    if not factor_matrix:
        return []
    n_stocks = len(next(iter(factor_matrix.values())))
    normalized = {}
    weights = {}
    total_w = 0
    for fname, vals in factor_matrix.items():
        normalized[fname] = zscore(vals)
        w = abs(ic_weights.get(fname, 0))
        weights[fname] = w
        total_w += w
    if total_w == 0:
        return composite_equal_weight(factor_matrix)
    result = []
    for i in range(n_stocks):
        weighted_sum = 0
        weight_sum = 0
        for f in normalized:
            if normalized[f][i] is not None:
                weighted_sum += normalized[f][i] * weights[f]
                weight_sum += weights[f]
        result.append(weighted_sum / weight_sum if weight_sum > 0 else None)
    return result


def composite_custom_weight(factor_matrix, custom_weights):
    """自定义权重合成。

    Args:
        factor_matrix: dict[str, list[float|None]]
        custom_weights: dict[str, float]，因子名 -> 权重（自动归一化）

    Returns:
        list[float]: 合成后的综合得分
    """
    if not factor_matrix:
        return []
    total = sum(custom_weights.values())
    if total == 0:
        return composite_equal_weight(factor_matrix)
    normalized_weights = {k: v / total for k, v in custom_weights.items()}
    return composite_ic_weight(factor_matrix, normalized_weights)


def select_effective_factors(factor_matrix, ic_results, min_ic=0.03):
    """筛选有效因子：|IC| >= min_ic 的因子。

    Args:
        factor_matrix: dict[str, list]
        ic_results: dict[str, dict]，因子名 -> IC检验结果
        min_ic: 最小IC阈值（默认0.03）

    Returns:
        dict[str, list]: 仅含有效因子的矩阵
    """
    effective = {}
    for fname, vals in factor_matrix.items():
        ic = (ic_results.get(fname) or {}).get("ic_mean")
        if ic is not None and abs(ic) >= min_ic:
            effective[fname] = vals
    return effective


def format_composite_result(scores, codes=None, top_n=20):
    """格式化合成结果：排序输出Top N。"""
    paired = [(i, s) for i, s in enumerate(scores) if s is not None]
    paired.sort(key=lambda x: x[1], reverse=True)
    result = []
    for rank, (idx, score) in enumerate(paired[:top_n], 1):
        code = codes[idx] if codes and idx < len(codes) else f"#{idx}"
        result.append({"rank": rank, "code": code, "composite_score": round(score, 4)})
    return result
