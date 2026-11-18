# -*- coding: utf-8 -*-
"""参数自适应：根据历史回测结果自动调整策略参数。

学习率控制（默认0.3），参数边界约束，防止过拟合。
仅调整连续型数值参数（如阈值、周期），不改变策略逻辑。
"""

import config


def _build_param_ranges(raw_ranges: dict) -> dict:
    """只保留在 config 中真实存在的标量参数，杜绝参数名错配导致的静默失效。

    文件名序号（s01..s20）与策略编号（S01..S23）存在偏移，极易写错参数名；
    此处以 config 实际属性为唯一权威，写错的键会被直接剔除，不会进入调整流程。
    """
    validated = {}
    for sid, params in raw_ranges.items():
        validated[sid] = {name: rng for name, rng in params.items() if hasattr(config, name)}
    return validated


class ParamAdapter:
    """策略参数自适应调整器。

    原理：根据历史回测表现，向最优参数方向逐步调整。
    - 学习率 alpha：调整步长占参数范围的比例（默认0.3，防止过拟合）
    - 参数边界：每个参数有合理范围，不越界
    - 最小样本数：历史回测次数>=3才调整（防止小样本噪声）
    """

    def __init__(self, knowledge_base, learning_rate: float = 0.3, min_samples: int = 3):
        self.kb = knowledge_base
        self.learning_rate = learning_rate
        self.min_samples = min_samples

    # 各策略可调参数的合理范围（键名必须与 config.py 中的真实常量一一对应）
    _RAW_PARAM_RANGES = {
        "S01": {"S01_YANG_RATIO_MIN": (0.5, 0.8), "S01_VOL_RATIO_MIN": (1.0, 3.0)},
        "S05": {"S05_LOOKBACK": (20, 60), "S05_DIVERGENCE_MIN_GAP": (0.01, 0.10)},
        "S06": {"S06_DIVIDEND_YIELD_MIN": (2.0, 8.0)},
        "S07": {"S07_PE_MAX": (10, 40), "S07_PB_MAX": (1.0, 5.0)},
        "S09": {"S09_ADX_MIN": (15, 40), "S09_CENTER_DAYS": (3, 10)},
        "S13": {"S13_ROE_MIN": (8.0, 25.0)},
        "S14": {"S14_REVENUE_GROWTH_MIN": (10.0, 40.0),
                "S14_PROFIT_GROWTH_MIN": (10.0, 40.0), "S14_PEG_MAX": (0.8, 3.0)},
        "S15": {"S15_DECLINE_60D_MIN": (10.0, 30.0), "S15_CONSO_20D_AMP_MAX": (5.0, 20.0),
                "S15_BOTTOM_VOL_VS_MA60": (1.0, 2.5), "S15_FLOW_DAYS_MIN": (2, 6)},
        "S17": {"S17_MOM_MID": (40, 120), "S17_MOM_MID_MIN": (0.03, 0.20),
                "S17_RSI_MAX": (60, 85), "S17_MA_BIAS_MAX": (0.10, 0.40)},
        "S18": {"S18_ROE_MIN": (10.0, 20.0), "S18_YEARS": (2, 5)},
        "S19": {"S19_CROSS_DAYS": (5, 30)},
        "S20": {"S20_NET_INFLOW_RATIO_MIN": (0.01, 0.10),
                "S20_CONSECUTIVE_DAYS_MIN": (2, 6), "S20_LOOKBACK": (5, 20)},
    }
    PARAM_RANGES = _build_param_ranges(_RAW_PARAM_RANGES)

    def adapt(self, strategy: str, current_params: dict) -> dict:
        """根据历史表现自适应调整参数。

        Args:
            strategy: 策略编号（如"S01"）
            current_params: 当前参数字典

        Returns:
            dict: 调整后的参数（无足够历史时返回原参数）
        """
        stats = self.kb.get_strategy_stats(strategy)
        if stats["count"] < self.min_samples:
            return current_params  # 样本不足，不调整

        best_params = self.kb.get_best_params(strategy)
        if not best_params:
            return current_params

        ranges = self.PARAM_RANGES.get(strategy, {})
        adjusted = dict(current_params)

        for param_name, best_val in best_params.items():
            if param_name not in ranges:
                continue
            current_val = current_params.get(param_name)
            if current_val is None or not isinstance(best_val, (int, float)):
                continue
            low, high = ranges[param_name]
            # 向最优参数方向调整，步长=学习率*差值
            diff = best_val - current_val
            new_val = current_val + self.learning_rate * diff
            # 边界约束
            new_val = max(low, min(high, new_val))
            # 整数参数取整
            if isinstance(current_val, int):
                new_val = int(round(new_val))
            adjusted[param_name] = round(new_val, 4)

        return adjusted

    def get_adjustment_report(self, strategy: str, current_params: dict) -> dict:
        """生成参数调整报告（说明调整了什么、为什么）。"""
        stats = self.kb.get_strategy_stats(strategy)
        best_params = self.kb.get_best_params(strategy)
        adjusted = self.adapt(strategy, current_params)

        changes = []
        for k, v in current_params.items():
            if k in adjusted and adjusted[k] != v:
                changes.append({
                    "param": k,
                    "current": v,
                    "adjusted": adjusted[k],
                    "best_historical": best_params.get(k) if best_params else None,
                })

        return {
            "strategy": strategy,
            "historical_samples": stats["count"],
            "historical_win_rate": stats["win_rate"],
            "historical_avg_return": stats["avg_return"],
            "adjusted": len(changes) > 0,
            "changes": changes,
            "note": f"学习率{self.learning_rate:.1f}，样本不足{self.min_samples}次不调整",
        }
