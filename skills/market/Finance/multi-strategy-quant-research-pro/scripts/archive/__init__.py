"""
multi-strategy-quant-research-pro v1.1.2 策略表现档案库 (archive) 子模块。

功能：
- schema:    SQLite 建表与初始化
- tracker:   筛选快照记录 + 收益回填
- analytics: 策略表现聚合统计 + 权重建议
- reporter:  档案报告生成
"""

from .schema import init_db
from .tracker import log_screening, refresh_performance
from .analytics import refresh_strategy_stats, get_strategy_ranking, suggest_weights
from .reporter import text_archive_report, json_archive_report

__all__ = [
    "init_db",
    "log_screening",
    "refresh_performance",
    "refresh_strategy_stats",
    "get_strategy_ranking",
    "suggest_weights",
    "text_archive_report",
    "json_archive_report",
]
