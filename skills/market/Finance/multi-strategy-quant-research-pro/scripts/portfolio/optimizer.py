# -*- coding: utf-8 -*-
"""组合优化器：从选股升级到仓位配置。

四种优化模型：
1. 等权组合（基准）
2. 最小方差组合（Min Variance）
3. 风险平价组合（Risk Parity）
4. 最大夏普组合（Max Sharpe）

约束：权重>=0，权重和=1，单票上限，行业上限。
纯Python标准库实现，无外部依赖。用坐标下降法求解。
"""

import math


def calc_cov_matrix(returns: list[list[float]]) -> list[list[float]]:
    """计算协方差矩阵。

    Args:
        returns: list[list[float]]，每只股票的收益率序列（等长）

    Returns:
        list[list[float]]: n×n协方差矩阵
    """
    n = len(returns)
    if n == 0:
        return []
    t = len(returns[0])
    if t < 2:
        return [[0.0] * n for _ in range(n)]

    means = [sum(r) / t for r in returns]
    cov = [[0.0] * n for _ in range(n)]
    for i in range(n):
        for j in range(i, n):
            s = sum((returns[i][k] - means[i]) * (returns[j][k] - means[j]) for k in range(t))
            cov[i][j] = s / (t - 1)
            cov[j][i] = cov[i][j]
    return cov


def portfolio_variance(weights: list[float], cov: list[list[float]]) -> float:
    """计算组合方差 w'Σw。"""
    n = len(weights)
    var = 0.0
    for i in range(n):
        for j in range(n):
            var += weights[i] * weights[j] * cov[i][j]
    return var


def portfolio_return(weights: list[float], expected_returns: list[float]) -> float:
    """计算组合预期收益 w'μ。"""
    return sum(w * r for w, r in zip(weights, expected_returns))


def risk_contributions(weights: list[float], cov: list[list[float]]) -> list[float]:
    """计算各资产的风险贡献（边际风险贡献×权重）。"""
    n = len(weights)
    port_var = portfolio_variance(weights, cov)
    if port_var == 0:
        return [0.0] * n
    port_vol = math.sqrt(port_var)
    # 边际风险贡献 = (Σw)_i / σ_p
    mrc = []
    for i in range(n):
        mrc_i = sum(cov[i][j] * weights[j] for j in range(n)) / port_vol
        mrc.append(mrc_i)
    # 风险贡献 = w_i × MRC_i
    rc = [weights[i] * mrc[i] for i in range(n)]
    return rc


def _feasible_max_weight(n: int, max_weight: float) -> float:
    """规整单票上限使约束可行。

    n 只股票要满足“权重和=1 且每只<=max_weight”，必要条件是 n*max_weight>=1。
    当持仓数不足（如3只却设20%上限）时约束不可行，此时自动把上限放宽到恰好
    可行的 1/n（即等权），保证权重和为1且不超过生效上限，避免归一后变相超限
    或权重和小于1。n<=0 时原样返回。
    """
    if n <= 0:
        return max_weight
    return max(max_weight, 1.0 / n)


def _project_upper_bounds(weights: list[float], max_weight: float) -> list[float]:
    """严格投影到权重上限约束（水填充法）。

    算法：超过上限的股票设为上限，剩余权重在未达上限的股票中按比例分配，
    反复迭代直到所有股票<=上限且总和=1。
    """
    n = len(weights)
    w = [max(0.0, x) for x in weights]
    total = sum(w)
    if total == 0:
        return [1.0 / n] * n
    w = [x / total for x in w]

    for _ in range(100):
        over = [i for i in range(n) if w[i] > max_weight + 1e-12]
        if not over:
            break
        # 超过上限的设为上限
        excess = 0.0
        for i in over:
            excess += w[i] - max_weight
            w[i] = max_weight
        # 剩余权重分配给未达上限的股票
        under = [i for i in range(n) if w[i] < max_weight - 1e-12]
        if not under:
            break
        under_total = sum(w[i] for i in under)
        if under_total > 0:
            # 有正权重的未封顶股票：按现有比例分摊
            for i in under:
                w[i] += excess * (w[i] / under_total)
        else:
            # 未封顶股票当前全为0：平均均摊（下一轮继续把新超限的压回上限，迭代收敛）
            add = excess / len(under)
            for i in under:
                w[i] += add
    return w


def _project_constraints(weights: list[float], max_weight: float,
                         industry_map: dict = None, industry_max: float = 1.0) -> list[float]:
    """投影到约束集：权重>=0，和=1，单票上限，行业上限。

    先投影单票上限，再投影行业上限，反复迭代直到收敛。
    """
    w = list(weights)

    for _ in range(50):
        # 1. 单票上限
        w = _project_upper_bounds(w, max_weight)

        # 2. 行业上限
        if industry_map and industry_max < 1.0:
            industry_indices = {}
            for i, ind in industry_map.items():
                industry_indices.setdefault(ind, []).append(i)
            for ind, indices in industry_indices.items():
                ind_total = sum(w[i] for i in indices)
                if ind_total > industry_max + 1e-12:
                    scale = industry_max / ind_total
                    for i in indices:
                        w[i] *= scale
                    # 缩放后重新归一化并投影单票上限
                    w = _project_upper_bounds(w, max_weight)

        # 3. 检查收敛
        max_w = max(w) if w else 0
        industry_ok = True
        if industry_map and industry_max < 1.0:
            for ind, indices in industry_indices.items():
                if sum(w[i] for i in indices) > industry_max + 1e-10:
                    industry_ok = False
                    break
        if max_w <= max_weight + 1e-10 and industry_ok:
            break

    return w


def optimize_min_variance(cov: list[list[float]], max_weight: float = 0.2,
                          industry_map: dict = None, industry_max: float = 0.3,
                          max_iter: int = 500, tol: float = 1e-8) -> dict:
    """最小方差组合优化（坐标下降法）。

    Args:
        cov: 协方差矩阵
        max_weight: 单票权重上限
        industry_map: {index: industry} 行业映射
        industry_max: 行业权重上限
        max_iter: 最大迭代次数
        tol: 收敛阈值

    Returns:
        dict: {weights, expected_return, volatility, sharpe, method}
    """
    n = len(cov)
    if n == 0:
        return {"weights": [], "expected_return": 0, "volatility": 0, "sharpe": 0, "method": "min_variance"}

    max_weight = _feasible_max_weight(n, max_weight)  # 持仓数不足时放宽到可行上限
    # 初始化等权
    weights = [1.0 / n] * n
    weights = _project_constraints(weights, max_weight, industry_map, industry_max)

    prev_var = portfolio_variance(weights, cov)

    for iteration in range(max_iter):
        improved = False
        for i in range(n):
            # 固定其他权重，优化w_i
            # 目标：min w'Σw，对w_i求导
            # d/dw_i = 2*(Σw)_i，在约束下调整
            numerator = 0.0
            denominator = 2 * cov[i][i]
            for j in range(n):
                if j != i:
                    numerator -= cov[i][j] * weights[j]
            if denominator > 0:
                new_wi = numerator / denominator
            else:
                new_wi = weights[i]

            old_wi = weights[i]
            weights[i] = new_wi
            weights = _project_constraints(weights, max_weight, industry_map, industry_max)

            if abs(weights[i] - old_wi) > tol:
                improved = True

        cur_var = portfolio_variance(weights, cov)
        if abs(prev_var - cur_var) < tol and not improved:
            break
        prev_var = cur_var

    vol = math.sqrt(max(0, portfolio_variance(weights, cov)))
    return {
        "weights": [round(w, 6) for w in weights],
        "expected_return": 0.0,  # 最小方差不考虑收益
        "volatility": round(vol * math.sqrt(252), 4),  # 年化
        "sharpe": 0.0,
        "method": "min_variance",
        "effective_max_weight": round(max_weight, 6),
        "iterations": iteration + 1,
    }


def optimize_risk_parity(cov: list[list[float]], max_weight: float = 0.2,
                         industry_map: dict = None, industry_max: float = 0.3,
                         max_iter: int = 500, tol: float = 1e-8) -> dict:
    """风险平价组合优化（每只股票贡献相同风险）。

    用迭代法：每次调整权重使风险贡献趋于均等。
    """
    n = len(cov)
    if n == 0:
        return {"weights": [], "expected_return": 0, "volatility": 0, "sharpe": 0, "method": "risk_parity"}

    max_weight = _feasible_max_weight(n, max_weight)  # 持仓数不足时放宽到可行上限
    weights = [1.0 / n] * n
    weights = _project_constraints(weights, max_weight, industry_map, industry_max)

    for iteration in range(max_iter):
        rc = risk_contributions(weights, cov)
        total_rc = sum(rc)
        if total_rc == 0:
            break
        target_rc = total_rc / n

        # 调整权重：风险贡献高于目标的降低，低于目标的提高
        new_weights = []
        for i in range(n):
            if rc[i] > 0:
                adj = target_rc / rc[i]
                new_w = weights[i] * math.sqrt(adj)  # 平方根调整，更稳定
            else:
                new_w = weights[i] * 1.1
            new_weights.append(new_w)

        new_weights = _project_constraints(new_weights, max_weight, industry_map, industry_max)

        # 收敛判断
        max_change = max(abs(new_weights[i] - weights[i]) for i in range(n))
        weights = new_weights
        if max_change < tol:
            break

    vol = math.sqrt(max(0, portfolio_variance(weights, cov)))
    rc = risk_contributions(weights, cov)
    rc_std = 0.0
    if rc:
        rc_mean = sum(rc) / len(rc)
        rc_std = math.sqrt(sum((r - rc_mean) ** 2 for r in rc) / len(rc))

    return {
        "weights": [round(w, 6) for w in weights],
        "expected_return": 0.0,
        "volatility": round(vol * math.sqrt(252), 4),
        "sharpe": 0.0,
        "method": "risk_parity",
        "effective_max_weight": round(max_weight, 6),
        "risk_contribution_std": round(rc_std, 6),
        "iterations": iteration + 1,
    }


def optimize_max_sharpe(cov: list[list[float]], expected_returns: list[float],
                        risk_free_rate: float = 0.02, max_weight: float = 0.2,
                        industry_map: dict = None, industry_max: float = 0.3,
                        max_iter: int = 500, tol: float = 1e-8) -> dict:
    """最大夏普组合优化（最大化 (w'μ - rf) / sqrt(w'Σw)）。

    用坐标下降法，每次调整一个权重。
    """
    n = len(cov)
    if n == 0 or not expected_returns:
        return {"weights": [], "expected_return": 0, "volatility": 0, "sharpe": 0, "method": "max_sharpe"}

    max_weight = _feasible_max_weight(n, max_weight)  # 持仓数不足时放宽到可行上限
    weights = [1.0 / n] * n
    weights = _project_constraints(weights, max_weight, industry_map, industry_max)

    def sharpe(w):
        ret = portfolio_return(w, expected_returns)
        vol = math.sqrt(max(1e-10, portfolio_variance(w, cov)))
        return (ret - risk_free_rate / 252) / vol

    prev_sharpe = sharpe(weights)

    for iteration in range(max_iter):
        improved = False
        for i in range(n):
            best_wi = weights[i]
            best_sharpe = prev_sharpe
            # 在[0, max_weight]范围内搜索最优w_i
            for test_w in [0.0, max_weight * 0.25, max_weight * 0.5, max_weight * 0.75, max_weight]:
                test_weights = list(weights)
                test_weights[i] = test_w
                test_weights = _project_constraints(test_weights, max_weight, industry_map, industry_max)
                s = sharpe(test_weights)
                if s > best_sharpe:
                    best_sharpe = s
                    best_wi = test_weights[i]
            if abs(best_wi - weights[i]) > tol:
                weights[i] = best_wi
                weights = _project_constraints(weights, max_weight, industry_map, industry_max)
                improved = True

        cur_sharpe = sharpe(weights)
        if abs(cur_sharpe - prev_sharpe) < tol and not improved:
            break
        prev_sharpe = cur_sharpe

    ret = portfolio_return(weights, expected_returns)
    vol = math.sqrt(max(0, portfolio_variance(weights, cov)))
    annual_ret = ret * 252
    annual_vol = vol * math.sqrt(252)
    sharpe_ratio = (annual_ret - risk_free_rate) / annual_vol if annual_vol > 0 else 0

    return {
        "weights": [round(w, 6) for w in weights],
        "expected_return": round(annual_ret, 4),
        "volatility": round(annual_vol, 4),
        "sharpe": round(sharpe_ratio, 4),
        "method": "max_sharpe",
        "effective_max_weight": round(max_weight, 6),
        "iterations": iteration + 1,
    }


def optimize_equal_weight(n: int, max_weight: float = 0.2) -> dict:
    """等权组合（基准）；持仓数不足以满足单票上限时自动放宽到 1/n。"""
    if n == 0:
        return {"weights": [], "method": "equal_weight"}
    max_weight = _feasible_max_weight(n, max_weight)
    w = min(1.0 / n, max_weight)
    weights = [w] * n
    total = sum(weights)
    if total > 0:
        weights = [x / total for x in weights]
    return {
        "weights": [round(x, 6) for x in weights],
        "method": "equal_weight",
        "effective_max_weight": round(max_weight, 6),
    }


def optimize_portfolio(returns: list[list[float]], expected_returns: list[float] = None,
                       method: str = "max_sharpe", risk_free_rate: float = 0.02,
                       max_weight: float = 0.2, industry_map: dict = None,
                       industry_max: float = 0.3, codes: list = None) -> dict:
    """组合优化统一入口。

    Args:
        returns: 各股票历史收益率序列
        expected_returns: 预期收益率（默认用历史平均）
        method: 优化方法（equal_weight/min_variance/risk_parity/max_sharpe）
        risk_free_rate: 无风险利率（年化）
        max_weight: 单票权重上限
        industry_map: {index: industry}
        industry_max: 行业权重上限
        codes: 股票代码列表（用于输出）

    Returns:
        dict: 优化结果，含weights、各指标、按权重排序的持仓列表
    """
    n = len(returns)
    if n == 0:
        return {"error": "无输入数据"}

    cov = calc_cov_matrix(returns)
    if expected_returns is None:
        expected_returns = [sum(r) / len(r) if r else 0 for r in returns]

    if method == "equal_weight":
        result = optimize_equal_weight(n, max_weight)
    elif method == "min_variance":
        result = optimize_min_variance(cov, max_weight, industry_map, industry_max)
    elif method == "risk_parity":
        result = optimize_risk_parity(cov, max_weight, industry_map, industry_max)
    elif method == "max_sharpe":
        result = optimize_max_sharpe(cov, expected_returns, risk_free_rate,
                                     max_weight, industry_map, industry_max)
    else:
        result = optimize_equal_weight(n, max_weight)

    # 构建持仓列表（按权重排序）
    weights = result.get("weights", [])
    holdings = []
    for i, w in enumerate(weights):
        if w > 0.001:  # 忽略小于0.1%的仓位
            code = codes[i] if codes and i < len(codes) else f"#{i}"
            holdings.append({"code": code, "weight": round(w * 100, 2), "index": i})
    holdings.sort(key=lambda x: x["weight"], reverse=True)

    result["holdings"] = holdings
    result["n_positions"] = len(holdings)
    result["max_single_weight"] = holdings[0]["weight"] if holdings else 0
    result["constraints"] = {
        "requested_max_weight": max_weight,
        "effective_max_weight": result.get("effective_max_weight", round(max_weight, 6)),
        "industry_max": industry_max,
        "risk_free_rate": risk_free_rate,
    }
    return result
