# -*- coding: utf-8 -*-
"""自进化知识库：存储历史回测结果、参数优化结果、市场环境记录。

轻量JSON文件存储，无外部依赖。支持读写、查询、统计、自动过期清理。
数据仅用于策略参数自适应，不涉及用户隐私。
"""

import json
import os
import time
from typing import Optional


class KnowledgeBase:
    """自进化知识库。

    存储三类数据：
    - backtest_results: 历史回测结果（策略/股票/参数/绩效）
    - param_optimizations: 参数优化结果
    - market_regimes: 历史市场环境记录
    """

    def __init__(self, storage_dir: Optional[str] = None):
        if storage_dir is None:
            storage_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "cache_data", "evolution")
        self.storage_dir = storage_dir
        os.makedirs(storage_dir, exist_ok=True)
        self._files = {
            "backtest": os.path.join(storage_dir, "backtest_results.json"),
            "params": os.path.join(storage_dir, "param_optimizations.json"),
            "regimes": os.path.join(storage_dir, "market_regimes.json"),
        }
        self._cache = {}

    def _load(self, key: str) -> list:
        if key in self._cache:
            return self._cache[key]
        path = self._files[key]
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self._cache[key] = data if isinstance(data, list) else []
            except (json.JSONDecodeError, OSError):
                self._cache[key] = []
        else:
            self._cache[key] = []
        return self._cache[key]

    def _save(self, key: str):
        path = self._files[key]
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(self._cache.get(key, []), f, ensure_ascii=False, indent=2)
        except OSError:
            pass

    def add_backtest_result(self, strategy: str, code: str, params: dict,
                            metrics: dict, hold_days: int = 10):
        """记录一次回测结果。"""
        records = self._load("backtest")
        records.append({
            "timestamp": int(time.time()),
            "strategy": strategy,
            "code": code,
            "params": params,
            "hold_days": hold_days,
            "metrics": metrics,
        })
        # 最多保留500条，防止文件过大
        if len(records) > 500:
            records = records[-500:]
        self._cache["backtest"] = records
        self._save("backtest")

    def get_strategy_stats(self, strategy: str) -> dict:
        """统计某策略的历史表现。"""
        records = [r for r in self._load("backtest") if r["strategy"] == strategy]
        if not records:
            return {"count": 0, "avg_return": None, "win_rate": None, "avg_max_drawdown": None}
        returns = [r["metrics"].get("total_return", 0) for r in records if r["metrics"].get("total_return") is not None]
        wins = [r for r in records if (r["metrics"].get("total_return") or 0) > 0]
        drawdowns = [r["metrics"].get("max_drawdown", 0) for r in records if r["metrics"].get("max_drawdown") is not None]
        return {
            "count": len(records),
            "avg_return": round(sum(returns) / len(returns), 4) if returns else None,
            "win_rate": round(len(wins) / len(records), 4) if records else None,
            "avg_max_drawdown": round(sum(drawdowns) / len(drawdowns), 4) if drawdowns else None,
        }

    def get_all_strategy_stats(self) -> dict:
        """统计所有策略的历史表现。"""
        records = self._load("backtest")
        strategies = set(r["strategy"] for r in records)
        return {s: self.get_strategy_stats(s) for s in sorted(strategies)}

    def add_param_optimization(self, strategy: str, best_params: dict,
                               best_metric: float, metric_name: str = "total_return"):
        """记录一次参数优化结果。"""
        records = self._load("params")
        records.append({
            "timestamp": int(time.time()),
            "strategy": strategy,
            "best_params": best_params,
            "best_metric": best_metric,
            "metric_name": metric_name,
        })
        if len(records) > 200:
            records = records[-200:]
        self._cache["params"] = records
        self._save("params")

    def get_best_params(self, strategy: str) -> Optional[dict]:
        """获取某策略历史最优参数。"""
        records = [r for r in self._load("params") if r["strategy"] == strategy]
        if not records:
            return None
        best = max(records, key=lambda r: r.get("best_metric", 0))
        return best.get("best_params")

    def add_market_regime(self, regime: str, indicators: dict):
        """记录市场环境。"""
        records = self._load("regimes")
        records.append({
            "timestamp": int(time.time()),
            "regime": regime,
            "indicators": indicators,
        })
        if len(records) > 365:
            records = records[-365:]
        self._cache["regimes"] = records
        self._save("regimes")

    def get_recent_regime(self, days: int = 30) -> Optional[str]:
        """获取最近N天最常见的市场环境。"""
        records = self._load("regimes")
        if not records:
            return None
        cutoff = int(time.time()) - days * 86400
        recent = [r for r in records if r["timestamp"] >= cutoff]
        if not recent:
            return records[-1].get("regime")
        from collections import Counter
        counter = Counter(r["regime"] for r in recent)
        return counter.most_common(1)[0][0]

    def get_stats_summary(self) -> dict:
        """获取知识库整体统计。"""
        return {
            "backtest_records": len(self._load("backtest")),
            "param_optimizations": len(self._load("params")),
            "market_regime_records": len(self._load("regimes")),
            "strategies_evaluated": len(self.get_all_strategy_stats()),
        }
