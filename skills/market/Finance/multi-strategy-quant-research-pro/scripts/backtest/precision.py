# -*- coding: utf-8 -*-
"""回测精度提升模块。

四大功能：
1. 行业中性回测：按行业分组多空，消除行业暴露
2. 分层回测：按因子值分5层，检验收益单调性
3. 因子衰减曲线：IC随持有期变化，判断因子有效期
4. 过拟合检测：样本内外IC对比、参数稳定性检验

纯Python标准库实现，无外部依赖。
"""

import math


def stratified_backtest(factor_values: list[float], returns: list[float],
                        n_groups: int = 5) -> dict:
    """分层回测：按因子值分组，计算各组平均收益并检验单调性。

    分组核心与 factors.ic_test 共用同一实现（_stratified_core），本函数在其上
    额外输出单调性比例与 top_minus_bottom；有效因子的各组收益应近似单调。

    Args:
        factor_values: 因子值列表
        returns: 对应股票的未来收益
        n_groups: 分组数（默认5层）

    Returns:
        dict: {groups, long_short, monotonicity, monotonic_direction, top_minus_bottom}
    """
    from factors.ic_test import _stratified_core
    core = _stratified_core(factor_values, returns, n_groups, ret_digits=6, range_digits=4)
    if core is None:
        return {"groups": [], "long_short": None, "monotonicity": None,
                "note": f"样本不足（需>= {n_groups * 2}）"}
    groups, long_short = core

    # 单调性检验：相邻组收益差的符号一致性
    signs = []
    for i in range(len(groups) - 1):
        diff = groups[i + 1]["avg_return"] - groups[i]["avg_return"]
        signs.append(1 if diff > 0 else (-1 if diff < 0 else 0))
    positive = sum(1 for s in signs if s > 0)
    negative = sum(1 for s in signs if s < 0)
    monotonicity = positive / len(signs) if positive >= negative else negative / len(signs)
    direction = "递增" if positive >= negative else "递减"

    return {
        "groups": groups,
        "long_short": round(long_short, 6),
        "monotonicity": round(monotonicity, 4),
        "monotonic_direction": direction,
        "top_minus_bottom": round(long_short, 6),
        "note": f"第1层=因子最低，第{n_groups}层=因子最高",
    }




def industry_neutral_backtest(factor_values: list[float], returns: list[float],
                              industries: list[str]) -> dict:
    """行业中性回测：在每个行业内部做分层，然后汇总。

    消除行业暴露：不是全市场选高分股，而是每个行业内选高分股，
    这样多空组合的行业暴露为中性。

    Args:
        factor_values: 因子值
        returns: 未来收益
        industries: 行业标签

    Returns:
        dict: {industry_results, overall_long_short, avg_ic_by_industry}
    """
    if not factor_values or not industries:
        return {"industry_results": [], "overall_long_short": None}

    # 按行业分组
    industry_data = {}
    for i, ind in enumerate(industries):
        if ind not in industry_data:
            industry_data[ind] = {"factors": [], "returns": []}
        industry_data[ind]["factors"].append(factor_values[i])
        industry_data[ind]["returns"].append(returns[i])

    industry_results = []
    all_long = []
    all_short = []
    ics = []

    for ind, data in industry_data.items():
        if len(data["factors"]) < 4:
            continue
        # 行业内分层（3层：高/中/低）
        result = stratified_backtest(data["factors"], data["returns"], n_groups=3)
        if result["groups"]:
            industry_results.append({
                "industry": ind,
                "count": len(data["factors"]),
                "long_return": result["groups"][-1]["avg_return"],
                "short_return": result["groups"][0]["avg_return"],
                "long_short": result["long_short"],
            })
            all_long.append(result["groups"][-1]["avg_return"])
            all_short.append(result["groups"][0]["avg_return"])
            # 行业内IC
            from factors.ic_test import calculate_ic_series
            ic = calculate_ic_series(data["factors"], data["returns"])
            if ic.get("ic_mean") is not None:
                ics.append(ic["ic_mean"])

    overall_ls = (sum(all_long) / len(all_long) - sum(all_short) / len(all_short)) if all_long else None
    avg_ic = sum(ics) / len(ics) if ics else None

    return {
        "industry_results": industry_results,
        "n_industries": len(industry_results),
        "overall_long_short": round(overall_ls, 6) if overall_ls is not None else None,
        "avg_ic_by_industry": round(avg_ic, 4) if avg_ic is not None else None,
        "note": "每个行业内部分层，消除行业暴露",
    }


def factor_decay_curve(factor_values: list[float], price_series: list[list[float]],
                       horizons: list[int] = None) -> dict:
    """因子衰减曲线：IC随持有期变化。

    计算因子在不同持有期（1/5/10/20/30日）后的IC，
    判断因子的有效期和衰减速度。

    Args:
        factor_values: 因子值（截面）
        price_series: 各股票的价格序列（用于计算不同持有期收益）
        horizons: 持有期列表（默认[1,5,10,20,30]）

    Returns:
        dict: {decay_curve, half_life, peak_horizon}
    """
    if horizons is None:
        horizons = [1, 5, 10, 20, 30]

    from factors.ic_test import calculate_ic_series

    curve = []
    for h in horizons:
        # 计算持有h期的收益
        returns = []
        valid_factors = []
        for i, prices in enumerate(price_series):
            if len(prices) > h and prices[0] > 0:
                ret = prices[h] / prices[0] - 1
                returns.append(ret)
                valid_factors.append(factor_values[i])
        if len(valid_factors) >= 5:
            ic = calculate_ic_series(valid_factors, returns)
            curve.append({
                "horizon": h,
                "ic": ic.get("ic_mean"),
                "ir": ic.get("ir"),
                "n_samples": len(valid_factors),
            })

    # 半衰期：IC降到峰值一半的持有期
    peak_ic = max((c["ic"] or 0) for c in curve) if curve else 0
    half_life = None
    peak_horizon = None
    for c in curve:
        if c["ic"] == peak_ic:
            peak_horizon = c["horizon"]
            break
    if peak_ic > 0:
        for c in curve:
            if c["horizon"] > (peak_horizon or 0) and (c["ic"] or 0) <= peak_ic / 2:
                half_life = c["horizon"]
                break

    return {
        "decay_curve": curve,
        "peak_horizon": peak_horizon,
        "peak_ic": round(peak_ic, 4) if peak_ic else None,
        "half_life": half_life,
        "note": "半衰期=IC降到峰值一半的持有期",
    }


def overfitting_detection(in_sample_ic: dict, out_sample_ic: dict,
                          in_sample_return: float, out_sample_return: float) -> dict:
    """过拟合检测：样本内外表现对比。

    过拟合的典型特征：
    - 样本内IC远高于样本外IC
    - 样本内收益远高于样本外收益
    - IC衰减率>50%

    Args:
        in_sample_ic: 样本内IC结果 {ic_mean, ir}
        out_sample_ic: 样本外IC结果 {ic_mean, ir}
        in_sample_return: 样本内策略收益
        out_sample_return: 样本外策略收益

    Returns:
        dict: {ic_decay, return_decay, overfitting_score, verdict}
    """
    in_ic = in_sample_ic.get("ic_mean") or 0
    out_ic = out_sample_ic.get("ic_mean") or 0

    # IC衰减率
    ic_decay = (in_ic - out_ic) / abs(in_ic) if in_ic != 0 else 0
    # 收益衰减率
    return_decay = (in_sample_return - out_sample_return) / abs(in_sample_return) if in_sample_return != 0 else 0

    # 过拟合评分（0-100，越高越可能过拟合）
    score = 0
    if ic_decay > 0.3:
        score += 30
    if ic_decay > 0.5:
        score += 20
    if return_decay > 0.3:
        score += 25
    if return_decay > 0.5:
        score += 25
    if out_ic < 0.02 and in_ic > 0.05:
        score += 20
    score = min(score, 100)

    if score >= 70:
        verdict = "严重过拟合"
    elif score >= 40:
        verdict = "可能过拟合"
    elif score >= 20:
        verdict = "轻微过拟合"
    else:
        verdict = "无明显过拟合"

    return {
        "in_sample_ic": round(in_ic, 4),
        "out_sample_ic": round(out_ic, 4),
        "ic_decay": round(ic_decay, 4),
        "in_sample_return": round(in_sample_return, 6),
        "out_sample_return": round(out_sample_return, 6),
        "return_decay": round(return_decay, 4),
        "overfitting_score": score,
        "verdict": verdict,
        "recommendation": {
            "严重过拟合": "建议减少参数数量、增加正则化、扩大样本区间",
            "可能过拟合": "建议增加样本外验证、检查参数稳定性",
            "轻微过拟合": "可接受，建议持续监控样本外表现",
            "无明显过拟合": "模型稳健性良好",
        }.get(verdict, ""),
    }


def parameter_stability_test(param_results: list[dict]) -> dict:
    """参数稳定性检验：不同参数下的表现波动。

    过拟合的另一个特征：参数微小变化导致结果剧烈波动。

    Args:
        param_results: [{params, ic, return}, ...] 不同参数的结果

    Returns:
        dict: {ic_std, return_std, stability_score, verdict}
    """
    if len(param_results) < 3:
        return {"note": "参数组合不足（需>=3）"}

    ics = [r.get("ic", 0) for r in param_results]
    returns = [r.get("return", 0) for r in param_results]

    ic_mean = sum(ics) / len(ics)
    ic_std = math.sqrt(sum((ic - ic_mean) ** 2 for ic in ics) / len(ics))
    ic_cv = ic_std / abs(ic_mean) if ic_mean != 0 else float("inf")

    ret_mean = sum(returns) / len(returns)
    ret_std = math.sqrt(sum((r - ret_mean) ** 2 for r in returns) / len(returns))
    ret_cv = ret_std / abs(ret_mean) if ret_mean != 0 else float("inf")

    # 稳定性评分（0-100，越高越稳定）
    score = 100
    if ic_cv > 0.3:
        score -= 30
    if ic_cv > 0.5:
        score -= 20
    if ret_cv > 0.5:
        score -= 25
    if ret_cv > 1.0:
        score -= 25
    score = max(score, 0)

    if score >= 80:
        verdict = "参数稳定"
    elif score >= 50:
        verdict = "参数较稳定"
    else:
        verdict = "参数不稳定"

    return {
        "n_params": len(param_results),
        "ic_mean": round(ic_mean, 4),
        "ic_std": round(ic_std, 4),
        "ic_cv": round(ic_cv, 4),
        "return_mean": round(ret_mean, 6),
        "return_std": round(ret_std, 6),
        "return_cv": round(ret_cv, 4),
        "stability_score": score,
        "verdict": verdict,
    }
