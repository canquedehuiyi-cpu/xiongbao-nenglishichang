# -*- coding: utf-8 -*-
"""因子库（47个因子，5大类）。

技术因子18个 / 价值因子9个 / 质量因子9个 / 成长因子6个 / 资金因子5个。

统一接口：
- 技术因子：factor_name(klines) -> float | None
- 价值/质量/成长/资金因子：factor_name(ctx) -> float | None
  ctx = {"klines": [...], "financial": {...}, "valuation": {...},
         "money_flow": [...], "extended": {...}}

因子方向统一：正值看多，负值看空。
"""

from .technical import TECHNICAL_FACTORS
from .value import VALUE_FACTORS
from .quality import QUALITY_FACTORS
from .growth import GROWTH_FACTORS
from .money_flow import MONEY_FLOW_FACTORS
from .orthogonal import (
    calc_correlation_matrix,
    gram_schmidt_orthogonalize,
    neutralize_factor,
    neutralize_all_factors,
    compare_ic_before_after,
)
from .composite import (
    composite_equal_weight,
    composite_ic_weight,
    composite_custom_weight,
    select_effective_factors,
    format_composite_result,
    rank_normalize,
)
from .ic_test import (
    calculate_ic_series,
    stratified_backtest,
    evaluate_factor,
)

# 全因子注册表：名称 -> (函数, 大类, 描述)
ALL_FACTORS = {}
ALL_FACTORS.update(TECHNICAL_FACTORS)
ALL_FACTORS.update(VALUE_FACTORS)
ALL_FACTORS.update(QUALITY_FACTORS)
ALL_FACTORS.update(GROWTH_FACTORS)
ALL_FACTORS.update(MONEY_FLOW_FACTORS)

# 按大类分组
FACTOR_GROUPS = {
    "技术": list(TECHNICAL_FACTORS.keys()),
    "价值": list(VALUE_FACTORS.keys()),
    "质量": list(QUALITY_FACTORS.keys()),
    "成长": list(GROWTH_FACTORS.keys()),
    "资金": list(MONEY_FLOW_FACTORS.keys()),
}


def calc_factor(factor_name, klines=None, ctx=None):
    """计算单个因子值。

    Args:
        factor_name: 因子名称（如 "rsi", "roe", "ep"）
        klines: K线数据（技术因子用）
        ctx: 上下文数据（价值/质量/成长/资金因子用）

    Returns:
        float | None: 因子值
    """
    entry = ALL_FACTORS.get(factor_name)
    if not entry:
        return None
    func = entry[0]
    category = entry[1]
    if category == "技术":
        return func(klines) if klines else None
    else:
        return func(ctx) if ctx else None


def calc_all_factors(klines=None, ctx=None):
    """计算全部因子值。

    Returns:
        dict[str, float|None]: 因子名 -> 因子值
    """
    result = {}
    for fname, (func, category, _) in ALL_FACTORS.items():
        try:
            if category == "技术":
                result[fname] = func(klines) if klines else None
            else:
                result[fname] = func(ctx) if ctx else None
        except Exception:
            result[fname] = None
    return result


def get_factor_count():
    """返回因子总数。"""
    return len(ALL_FACTORS)


def list_factors(category=None):
    """列出因子清单。

    Args:
        category: 大类筛选（技术/价值/质量/成长/资金），None表示全部

    Returns:
        list[dict]: [{name, category, description}]
    """
    result = []
    for fname, (_, cat, desc) in ALL_FACTORS.items():
        if category and cat != category:
            continue
        result.append({"name": fname, "category": cat, "description": desc})
    return result


__all__ = [
    "ALL_FACTORS", "FACTOR_GROUPS",
    "TECHNICAL_FACTORS", "VALUE_FACTORS", "QUALITY_FACTORS",
    "GROWTH_FACTORS", "MONEY_FLOW_FACTORS",
    "calc_factor", "calc_all_factors", "get_factor_count", "list_factors",
    "calc_correlation_matrix", "gram_schmidt_orthogonalize",
    "neutralize_factor", "neutralize_all_factors", "compare_ic_before_after",
    "composite_equal_weight", "composite_ic_weight", "composite_custom_weight",
    "select_effective_factors", "format_composite_result", "rank_normalize",
    "calculate_ic_series", "stratified_backtest", "evaluate_factor",
]
