# -*- coding: utf-8 -*-
"""策略优胜劣汰：根据历史表现自动启用/禁用策略。

- 最低胜率阈值（默认40%）：低于此胜率的策略自动标记为"弱表现"
- 最低收益阈值（默认0%）：平均收益为负的策略标记为"风险"
- 策略排名：按综合得分（胜率*0.4 + 收益*0.3 - 回撤*0.3）排序
- 推荐组合：自动推荐Top N策略
"""



class StrategySelector:
    """策略优胜劣汰选择器。

    根据知识库中的历史回测统计，自动评估各策略表现并推荐。
    """

    def __init__(self, knowledge_base,
                 min_win_rate: float = 0.40,
                 min_avg_return: float = 0.0,
                 max_drawdown_limit: float = 0.30):
        self.kb = knowledge_base
        self.min_win_rate = min_win_rate
        self.min_avg_return = min_avg_return
        self.max_drawdown_limit = max_drawdown_limit

    def evaluate_strategy(self, strategy: str) -> dict:
        """评估单个策略的表现。"""
        stats = self.kb.get_strategy_stats(strategy)
        if stats["count"] == 0:
            return {
                "strategy": strategy,
                "status": "未评估",
                "score": None,
                "reason": "无历史回测数据",
            }

        win_rate = stats.get("win_rate") or 0
        avg_return = stats.get("avg_return") or 0
        max_dd = stats.get("avg_max_drawdown") or 0

        # 综合得分：胜率40% + 收益30% - 回撤30%
        # 收益和回撤归一化到[0,1]
        score = (win_rate * 0.4 +
                 min(max(avg_return / 0.5, 0), 1) * 0.3 -
                 min(max(max_dd / 0.5, 0), 1) * 0.3)

        if win_rate < self.min_win_rate:
            status = "弱表现"
            reason = f"胜率{win_rate:.1%}低于阈值{self.min_win_rate:.0%}"
        elif avg_return < self.min_avg_return:
            status = "风险"
            reason = f"平均收益{avg_return:.2%}为负"
        elif max_dd > self.max_drawdown_limit:
            status = "高波动"
            reason = f"平均回撤{max_dd:.1%}超过{self.max_drawdown_limit:.0%}"
        else:
            status = "推荐"
            reason = "胜率、收益、回撤均达标"

        return {
            "strategy": strategy,
            "status": status,
            "score": round(score, 4),
            "win_rate": win_rate,
            "avg_return": avg_return,
            "avg_max_drawdown": max_dd,
            "sample_count": stats["count"],
            "reason": reason,
        }

    def evaluate_all(self, strategies: list = None) -> list:
        """评估所有策略，按得分排序。"""
        if strategies is None:
            # 默认评估知识库中有数据的策略 + 常用策略
            all_stats = self.kb.get_all_strategy_stats()
            strategies = sorted(all_stats.keys()) if all_stats else [
                "S01", "S05", "S06", "S07", "S09", "S13", "S14", "S17", "S18", "S19"
            ]

        results = [self.evaluate_strategy(s) for s in strategies]
        # 有得分的按得分排序，无得分的放后面
        scored = [r for r in results if r["score"] is not None]
        unscored = [r for r in results if r["score"] is None]
        scored.sort(key=lambda x: x["score"], reverse=True)
        return scored + unscored

    def recommend(self, top_n: int = 5, market_regime: str = None) -> list:
        """推荐Top N策略。

        Args:
            top_n: 推荐数量
            market_regime: 市场环境（可选，用于环境适配推荐）

        Returns:
            list[dict]: 推荐策略列表
        """
        all_evaluated = self.evaluate_all()

        # 市场环境适配（简单规则）
        regime_preference = {
            "牛市": ["S09", "S17", "S16", "S22", "S23"],  # 趋势/动量/海龟/相对强度/均线趋势风控
            "熊市": ["S06", "S07", "S13", "S18"],  # 高股息/低估值/ROE杜邦/多年ROE
            "震荡市": ["S01", "S05", "S11", "S19"],  # 红肥绿瘦/MACD底背离/筹码集中/MACD金叉
        }
        preferred = regime_preference.get(market_regime, []) if market_regime else []

        # 优先推荐"推荐"状态的策略，其次"高波动"，排除"弱表现"和"风险"
        recommended = [r for r in all_evaluated if r["status"] == "推荐"]
        if len(recommended) < top_n:
            high_vol = [r for r in all_evaluated if r["status"] == "高波动"]
            recommended.extend(high_vol[:top_n - len(recommended)])
        if len(recommended) < top_n:
            unevaluated = [r for r in all_evaluated if r["status"] == "未评估"]
            recommended.extend(unevaluated[:top_n - len(recommended)])

        # 市场环境偏好的策略优先
        if preferred:
            preferred_set = set(preferred)
            recommended.sort(key=lambda r: (r["strategy"] not in preferred_set,
                                            -(r["score"] or 0)))

        return recommended[:top_n]

    def get_blacklist(self) -> list:
        """获取黑名单（弱表现/风险策略）。"""
        all_evaluated = self.evaluate_all()
        return [r for r in all_evaluated if r["status"] in ("弱表现", "风险")]
