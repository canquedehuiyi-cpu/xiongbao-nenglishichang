# -*- coding: utf-8 -*-
"""风格中性化：选股结果的市值/行业/波动率/Beta四维中性。

在选股后做后处理，通过权重调整使组合的风格暴露接近市场基准，
避免"选出来全是小盘股"或"全是一个行业"的集中度风险。
"""

import math


def calc_exposure(stocks: list[dict], weights: list[float] = None) -> dict:
    """计算组合的风格暴露。

    Args:
        stocks: 股票列表，每项含 {code, market_cap, industry, volatility, beta, ...}
        weights: 权重列表（默认等权）

    Returns:
        dict: {market_cap_avg, industry_dist, volatility_avg, beta_avg, n_stocks}
    """
    n = len(stocks)
    if n == 0:
        return {}

    if weights is None:
        weights = [1.0 / n] * n

    # 加权平均市值
    total_w = sum(weights)
    if total_w > 0:
        weights = [w / total_w for w in weights]

    # 市值（对数加权平均）
    mc_vals = []
    mc_weights = []
    for i, s in enumerate(stocks):
        mc = s.get("market_cap")
        if mc and mc > 0:
            mc_vals.append(math.log(mc))
            mc_weights.append(weights[i])
    avg_log_mc = sum(mc_vals[i] * mc_weights[i] for i in range(len(mc_vals))) / sum(mc_weights) if mc_weights else 0
    avg_mc = math.exp(avg_log_mc)

    # 行业分布
    industry_dist = {}
    for i, s in enumerate(stocks):
        ind = s.get("industry", "未知")
        industry_dist[ind] = industry_dist.get(ind, 0) + weights[i]

    # 加权平均波动率
    vol_vals = [s.get("volatility", 0) for s in stocks if s.get("volatility") is not None]
    vol_weights = [weights[i] for i, s in enumerate(stocks) if s.get("volatility") is not None]
    avg_vol = sum(vol_vals[i] * vol_weights[i] for i in range(len(vol_vals))) / sum(vol_weights) if vol_vals else 0

    # 加权平均Beta
    beta_vals = [s.get("beta", 1.0) for s in stocks if s.get("beta") is not None]
    beta_weights = [weights[i] for i, s in enumerate(stocks) if s.get("beta") is not None]
    avg_beta = sum(beta_vals[i] * beta_weights[i] for i in range(len(beta_vals))) / sum(beta_weights) if beta_vals else 1.0

    return {
        "market_cap_avg": round(avg_mc, 0),
        "market_cap_log": round(avg_log_mc, 4),
        "industry_dist": {k: round(v, 4) for k, v in industry_dist.items()},
        "volatility_avg": round(avg_vol, 4),
        "beta_avg": round(avg_beta, 4),
        "n_stocks": n,
    }


def neutralize_weights(stocks: list[dict], benchmark: dict,
                       target_market_cap: float = None,
                       target_volatility: float = None,
                       target_beta: float = 1.0,
                       max_industry_weight: float = 0.3,
                       max_single_weight: float = 0.25,
                       iterations: int = 100) -> dict:
    """风格中性化权重调整。

    通过迭代调整权重，使组合的风格暴露接近基准。

    Args:
        stocks: 股票列表
        benchmark: 基准暴露 {market_cap_avg, volatility_avg, beta_avg, industry_dist}
        target_market_cap: 目标市值（默认用基准）
        target_volatility: 目标波动率（默认用基准）
        target_beta: 目标Beta（默认1.0）
        max_industry_weight: 行业权重上限
        max_single_weight: 单票权重上限
        iterations: 迭代次数

    Returns:
        dict: {weights, exposure_before, exposure_after, adjustments, neutralized}
    """
    n = len(stocks)
    if n == 0:
        return {"neutralized": False, "reason": "无股票"}

    # 初始等权
    weights = [1.0 / n] * n
    exposure_before = calc_exposure(stocks, weights)

    # 目标值
    target_mc = target_market_cap or benchmark.get("market_cap_avg", 0)
    target_vol = target_volatility or benchmark.get("volatility_avg", 0)
    target_beta_val = target_beta
    target_industry = benchmark.get("industry_dist", {})

    for iteration in range(iterations):
        current = calc_exposure(stocks, weights)
        adjusted = False

        # 1. 行业中性：超配行业降权，低配行业升权
        for ind, target_w in target_industry.items():
            current_w = current["industry_dist"].get(ind, 0)
            if current_w > max_industry_weight:
                # 超配行业降权
                diff = current_w - max_industry_weight
                ind_indices = [i for i, s in enumerate(stocks) if s.get("industry") == ind]
                if ind_indices:
                    total_ind_w = sum(weights[i] for i in ind_indices)
                    if total_ind_w > 0:
                        scale = (total_ind_w - diff) / total_ind_w
                        for i in ind_indices:
                            weights[i] *= scale
                        adjusted = True

        # 2. 市值中性：小盘股降权，大盘股升权（如果组合偏小盘）
        if target_mc > 0 and current["market_cap_avg"] > 0:
            mc_ratio = current["market_cap_avg"] / target_mc
            if mc_ratio < 0.8:  # 组合偏小盘
                # 给大盘股加权
                for i, s in enumerate(stocks):
                    mc = s.get("market_cap", 0)
                    if mc and mc > target_mc:
                        weights[i] *= 1.05
                        adjusted = True
                    elif mc and mc < target_mc * 0.5:
                        weights[i] *= 0.95
                        adjusted = True

        # 3. 波动率中性
        if target_vol > 0 and current["volatility_avg"] > 0:
            vol_ratio = current["volatility_avg"] / target_vol
            if vol_ratio > 1.2:  # 组合波动偏高
                for i, s in enumerate(stocks):
                    vol = s.get("volatility", 0)
                    if vol and vol > target_vol * 1.2:
                        weights[i] *= 0.95
                        adjusted = True

        # 4. Beta中性
        if current["beta_avg"] > 0:
            beta_diff = current["beta_avg"] - target_beta_val
            if abs(beta_diff) > 0.1:
                for i, s in enumerate(stocks):
                    beta = s.get("beta", 1.0)
                    if beta_diff > 0 and beta > target_beta_val:
                        weights[i] *= 0.97  # 高Beta降权
                        adjusted = True
                    elif beta_diff < 0 and beta < target_beta_val:
                        weights[i] *= 1.03  # 低Beta升权
                        adjusted = True

        # 5. 单票上限
        for i in range(n):
            if weights[i] > max_single_weight:
                weights[i] = max_single_weight
                adjusted = True

        # 归一化
        total = sum(weights)
        if total > 0:
            weights = [w / total for w in weights]

        if not adjusted:
            break

    exposure_after = calc_exposure(stocks, weights)

    # 计算调整幅度
    adjustments = {
        "market_cap_change": round((exposure_after["market_cap_avg"] - exposure_before["market_cap_avg"]) / max(1, exposure_before["market_cap_avg"]) * 100, 2),
        "volatility_change": round(exposure_after["volatility_avg"] - exposure_before["volatility_avg"], 4),
        "beta_change": round(exposure_after["beta_avg"] - exposure_before["beta_avg"], 4),
        "max_industry_before": round(max(exposure_before["industry_dist"].values()) if exposure_before["industry_dist"] else 0, 4),
        "max_industry_after": round(max(exposure_after["industry_dist"].values()) if exposure_after["industry_dist"] else 0, 4),
    }

    return {
        "weights": [round(w, 6) for w in weights],
        "exposure_before": exposure_before,
        "exposure_after": exposure_after,
        "adjustments": adjustments,
        "iterations": iteration + 1,
        "neutralized": True,
        "targets": {
            "market_cap": target_mc,
            "volatility": target_vol,
            "beta": target_beta_val,
            "max_industry_weight": max_industry_weight,
        },
    }


def style_report(exposure: dict, benchmark: dict = None) -> dict:
    """生成风格暴露报告。"""
    report = {
        "n_stocks": exposure.get("n_stocks", 0),
        "market_cap_avg": exposure.get("market_cap_avg", 0),
        "volatility_avg": exposure.get("volatility_avg", 0),
        "beta_avg": exposure.get("beta_avg", 0),
        "industry_dist": exposure.get("industry_dist", {}),
        "max_industry_weight": max(exposure.get("industry_dist", {}).values()) if exposure.get("industry_dist") else 0,
    }
    if benchmark:
        report["market_cap_vs_benchmark"] = round(
            (exposure.get("market_cap_avg", 0) - benchmark.get("market_cap_avg", 0)) / max(1, benchmark.get("market_cap_avg", 1)) * 100, 2
        )
        report["volatility_vs_benchmark"] = round(
            exposure.get("volatility_avg", 0) - benchmark.get("volatility_avg", 0), 4
        )
        report["beta_vs_benchmark"] = round(
            exposure.get("beta_avg", 0) - benchmark.get("beta_avg", 1.0), 4
        )
    return report
