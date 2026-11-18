# -*- coding: utf-8 -*-
"""市场环境引擎。

四大模块：
- MarketRegimeDetector: 市场环境检测（牛市/熊市/震荡市 + 置信度 + 仓位建议）
- SectorRotationAnalyzer: 行业轮动分析（强势/弱势行业 + 轮动方向 + 热点概念）
- StrategyRecommender: 市场环境适配的策略推荐
- MarketBreadth: 市场宽度指标（涨跌比/新高新低/ADL/均线占比 + 仓位建议）

所有判断基于真实大盘指数和行业板块数据，确定性计算，不构成投资建议。
"""

from .detector import detect_market_regime, get_position_suggestion
from .sector_rotation import analyze_sector_rotation, get_concept_hotspots
from .strategy_recommender import recommend_strategies_by_regime, get_strategy_regime_compatibility
from .breadth import (
    calc_advance_decline_ratio,
    calc_new_high_low_index,
    calc_adl_index,
    calc_above_ma_ratio,
    market_breadth_score,
)


class MarketRegimeEngine:
    """市场环境引擎统一入口（无状态，直接调用底层函数）。"""

    def detect(self, index_klines):
        """检测市场环境。"""
        return detect_market_regime(index_klines)

    def analyze_sectors(self, industry_ranking, top_n=5):
        """分析行业轮动。"""
        return analyze_sector_rotation(industry_ranking, top_n)

    def recommend(self, regime, top_n=5):
        """根据市场环境推荐策略。"""
        return recommend_strategies_by_regime(regime, top_n)

    def full_analysis(self, index_klines, industry_ranking=None, top_n=5):
        """完整市场环境分析。"""
        regime = self.detect(index_klines)
        result = {"regime": regime}
        if industry_ranking:
            result["sector_rotation"] = self.analyze_sectors(industry_ranking, top_n)
        result["strategy_recommendation"] = self.recommend(regime["regime"], top_n)
        result["position_suggestion"] = get_position_suggestion(
            regime["regime"], regime["confidence"]
        )
        return result


__all__ = [
    "detect_market_regime", "get_position_suggestion",
    "analyze_sector_rotation", "get_concept_hotspots",
    "recommend_strategies_by_regime", "get_strategy_regime_compatibility",
    "calc_advance_decline_ratio", "calc_new_high_low_index",
    "calc_adl_index", "calc_above_ma_ratio", "market_breadth_score",
    "MarketRegimeEngine",
]
