# -*- coding: utf-8 -*-
"""自进化引擎。

四大模块：
- KnowledgeBase: 知识库（历史回测/参数优化/市场环境存储）
- ParamAdapter: 参数自适应（基于历史表现调整策略参数）
- FactorWeightAdapter: 因子权重动态调整（基于IC/IR）
- StrategySelector: 策略优胜劣汰（自动推荐/黑名单）

自进化原则：
1. 学习率控制，防止过拟合
2. 最小样本数要求，防止小样本噪声
3. 参数边界约束，不越界
4. 所有调整可追溯、可解释
5. 仅优化参数和权重，不改变策略逻辑
"""

from .knowledge_base import KnowledgeBase
from .param_adapter import ParamAdapter
from .factor_weight import FactorWeightAdapter
from .strategy_selector import StrategySelector


class SelfEvolutionEngine:
    """自进化引擎统一入口。"""

    def __init__(self, storage_dir=None, learning_rate=0.3, min_samples=3):
        self.kb = KnowledgeBase(storage_dir)
        self.param_adapter = ParamAdapter(self.kb, learning_rate, min_samples)
        self.factor_weight_adapter = FactorWeightAdapter()
        self.strategy_selector = StrategySelector(self.kb)

    def record_backtest(self, strategy, code, params, metrics, hold_days=10):
        """记录回测结果（学习的输入）。"""
        self.kb.add_backtest_result(strategy, code, params, metrics, hold_days)

    def adapt_params(self, strategy, current_params):
        """自适应调整参数。"""
        return self.param_adapter.adapt(strategy, current_params)

    def adapt_factor_weights(self, ic_results, current_weights=None):
        """动态调整因子权重。"""
        if current_weights:
            return self.factor_weight_adapter.update_weights(current_weights, ic_results)
        return self.factor_weight_adapter.calculate_weights(ic_results)

    def recommend_strategies(self, top_n=5, market_regime=None):
        """推荐策略组合。"""
        return self.strategy_selector.recommend(top_n, market_regime)

    def get_evolution_report(self) -> dict:
        """生成自进化报告。"""
        return {
            "knowledge_base": self.kb.get_stats_summary(),
            "strategy_evaluation": self.strategy_selector.evaluate_all(),
            "blacklist": self.strategy_selector.get_blacklist(),
        }


__all__ = [
    "KnowledgeBase", "ParamAdapter", "FactorWeightAdapter",
    "StrategySelector", "SelfEvolutionEngine",
]
