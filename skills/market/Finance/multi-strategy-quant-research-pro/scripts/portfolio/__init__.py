# -*- coding: utf-8 -*-
"""组合优化模块。

从"选股"升级到"仓位配置"：
- 等权组合（基准）
- 最小方差组合
- 风险平价组合
- 最大夏普组合

约束：单票上限、行业上限、不做空、权重和为1。
"""

from .optimizer import (
    optimize_portfolio,
    optimize_equal_weight,
    optimize_min_variance,
    optimize_risk_parity,
    optimize_max_sharpe,
    calc_cov_matrix,
    portfolio_variance,
    portfolio_return,
    risk_contributions,
)
from .style_neutral import (
    calc_exposure,
    neutralize_weights,
    style_report,
)

__all__ = [
    "optimize_portfolio",
    "optimize_equal_weight",
    "optimize_min_variance",
    "optimize_risk_parity",
    "optimize_max_sharpe",
    "calc_cov_matrix",
    "portfolio_variance",
    "portfolio_return",
    "risk_contributions",
    "calc_exposure",
    "neutralize_weights",
    "style_report",
]
