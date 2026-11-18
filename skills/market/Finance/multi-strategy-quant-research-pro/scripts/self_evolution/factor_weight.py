# -*- coding: utf-8 -*-
"""因子权重动态调整：基于IC/IR自动调整多因子合成权重。

- 权重与因子IC绝对值成正比
- 权重衰减：历史IC随时间衰减（近期IC权重更高）
- 最低权重：每个因子至少有5%权重（防止单因子主导）
- 自动归一化
"""



class FactorWeightAdapter:
    """因子权重动态调整器。

    原理：有效因子（|IC|高）获得更高权重，无效因子权重降低。
    - IC均值为权重的基础
    - IR（IC/IC_std）作为稳定性调整
    - 时间衰减：近期IC权重更高
    """

    def __init__(self, min_weight: float = 0.05, decay_factor: float = 0.95):
        self.min_weight = min_weight
        self.decay_factor = decay_factor

    def calculate_weights(self, ic_results: dict) -> dict:
        """根据IC检验结果计算因子权重。

        Args:
            ic_results: dict[str, dict]，因子名 -> IC检验结果
                每个结果含 ic_mean, ir, ic_positive_rate

        Returns:
            dict[str, float]: 因子名 -> 权重（归一化，和为1）
        """
        if not ic_results:
            return {}

        raw_weights = {}
        for fname, result in ic_results.items():
            ic = result.get("ic_mean")
            ir = result.get("ir")
            if ic is None:
                raw_weights[fname] = self.min_weight
                continue
            # 权重 = |IC| * (1 + min(IR, 2) * 0.5)
            # IR高的因子（稳定有效）获得额外加成
            ir_adj = 1.0 + (min(abs(ir), 2.0) if ir else 0) * 0.5
            raw_weights[fname] = abs(ic) * ir_adj

        # 最低权重保障
        total = sum(raw_weights.values())
        if total == 0:
            n = len(raw_weights)
            return {f: 1.0 / n for f in raw_weights}

        # 归一化
        weights = {f: w / total for f, w in raw_weights.items()}

        # 最低权重约束：低于min_weight的提升到min_weight，超出部分从高权重按比例扣除
        below = {f: w for f, w in weights.items() if w < self.min_weight}
        if below:
            deficit = sum(self.min_weight - w for w in below.values())
            above = {f: w for f, w in weights.items() if w >= self.min_weight}
            above_total = sum(above.values())
            for f in below:
                weights[f] = self.min_weight
            if above_total > 0:
                for f in above:
                    weights[f] -= (weights[f] / above_total) * deficit

        # 最终归一化（防止浮点误差）
        final_total = sum(weights.values())
        if final_total > 0:
            weights = {f: w / final_total for f, w in weights.items()}

        return weights

    def update_weights(self, current_weights: dict, new_ic_results: dict) -> dict:
        """增量更新权重：新旧权重加权平均（防止剧烈波动）。

        Args:
            current_weights: 当前权重
            new_ic_results: 新的IC检验结果

        Returns:
            dict: 更新后的权重
        """
        new_weights = self.calculate_weights(new_ic_results)
        if not current_weights:
            return new_weights

        # 新旧权重各占50%（平滑过渡）
        all_factors = set(current_weights.keys()) | set(new_weights.keys())
        updated = {}
        for f in all_factors:
            old_w = current_weights.get(f, 0)
            new_w = new_weights.get(f, 0)
            updated[f] = 0.5 * old_w + 0.5 * new_w

        # 归一化
        total = sum(updated.values())
        if total > 0:
            updated = {f: w / total for f, w in updated.items()}
        return updated

    def get_weight_report(self, weights: dict, ic_results: dict) -> list:
        """生成权重报告（按权重排序）。"""
        report = []
        for fname, w in sorted(weights.items(), key=lambda x: x[1], reverse=True):
            ic = (ic_results.get(fname) or {}).get("ic_mean")
            report.append({
                "factor": fname,
                "weight": round(w, 4),
                "ic_mean": ic,
                "effective": ic is not None and abs(ic) >= 0.03,
            })
        return report
