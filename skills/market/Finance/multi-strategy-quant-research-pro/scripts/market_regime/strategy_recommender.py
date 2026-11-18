# -*- coding: utf-8 -*-
"""市场环境适配的策略推荐：根据市场环境推荐适合的策略组合。

不同市场环境下策略表现差异显著：
- 牛市：趋势/动量/海龟策略表现好
- 熊市：高股息/低估值/ROE防御策略表现好
- 震荡市：量价/底背离/筹码/金叉波段策略表现好
"""


# 市场环境 -> 推荐策略映射（基于策略特性，非历史回测结果）
REGIME_STRATEGY_MAP = {
    "牛市": {
        "primary": ["S09", "S17", "S16", "S22", "S23"],  # 趋势/动量/海龟/相对强度/均线趋势风控
        "secondary": ["S08", "S20", "S21", "S02"],       # 放量突破/资金流/多周期共振/上涨波段
        "avoid": ["S06", "S07"],                         # 高股息/低估值（牛市中防御型相对跑输）
        "rationale": "牛市中趋势跟踪和动量策略胜率高，防御型策略相对跑输",
    },
    "熊市": {
        "primary": ["S06", "S07", "S13", "S18"],          # 高股息/低估值/ROE杜邦/多年度ROE
        "secondary": ["S12", "S14"],                      # 现金流质量/费雪成长
        "avoid": ["S17", "S16", "S08"],                   # 动量/海龟/放量突破（熊市趋势策略易反复止损）
        "rationale": "熊市中防御型价值策略抗跌，趋势和动量策略容易反复止损",
    },
    "震荡市": {
        "primary": ["S01", "S05", "S11", "S19"],          # 红肥绿瘦/MACD底背离/筹码集中/MACD金叉
        "secondary": ["S10", "S04", "S03", "S15"],        # 布林带下轨/横盘调整/回调缩量/长期蓄力
        "avoid": ["S16", "S17", "S23"],                   # 海龟/动量/均线趋势风控（震荡市反复假突破）
        "rationale": "震荡市中波段和反转策略有效，趋势跟踪策略容易被反复止损",
    },
    "未知": {
        "primary": ["S06", "S09", "S13", "S17"],          # 均衡组合
        "secondary": ["S01", "S07", "S18"],
        "avoid": [],
        "rationale": "方向不明时建议均衡配置价值+成长+技术策略",
    },
}


def recommend_strategies_by_regime(regime: str, top_n: int = 5) -> dict:
    """根据市场环境推荐策略。

    Args:
        regime: 市场环境（牛市/熊市/震荡市/未知）
        top_n: 推荐策略数量

    Returns:
        dict: {recommended, avoid, rationale, combination_mode}
    """
    mapping = REGIME_STRATEGY_MAP.get(regime, REGIME_STRATEGY_MAP["未知"])

    recommended = list(mapping["primary"][:top_n])
    if len(recommended) < top_n:
        recommended.extend(mapping["secondary"][: top_n - len(recommended)])
    # 次选剔除已进入重点推荐的策略，保证 recommended 与 secondary 互斥不重叠
    secondary = [s for s in mapping["secondary"] if s not in recommended]

    return {
        "market_regime": regime,
        "recommended": recommended,
        "secondary": secondary,
        "avoid": mapping["avoid"],
        "rationale": mapping["rationale"],
        "combination_mode": "交集" if regime == "牛市" else "并集" if regime == "熊市" else "加权",
        "position_hint": {
            "牛市": "70%-90%仓位，持有期可延长至20-30日",
            "熊市": "10%-30%仓位，严格止损，持有期5-10日",
            "震荡市": "30%-50%仓位，高抛低吸，持有期5-15日",
            "未知": "50%仓位，均衡配置",
        }.get(regime, "50%仓位"),
    }


def get_strategy_regime_compatibility(strategy: str) -> dict:
    """查询某策略在各市场环境下的适配度。"""
    compatibility = {}
    for regime, mapping in REGIME_STRATEGY_MAP.items():
        if strategy in mapping["primary"]:
            compatibility[regime] = "高适配"
        elif strategy in mapping["secondary"]:
            compatibility[regime] = "中适配"
        elif strategy in mapping["avoid"]:
            compatibility[regime] = "低适配/回避"
        else:
            compatibility[regime] = "中性"
    return compatibility
