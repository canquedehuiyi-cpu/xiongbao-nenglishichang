# -*- coding: utf-8 -*-
"""动态仓位管理模块。

四种仓位模型：
- 凯利公式：基于胜率和盈亏比的理论最优仓位
- ATR波动率：每只股票风险相同
- 风险平价：每只股票贡献相同组合风险
- 信号强度：信号越强仓位越大
"""

from .sizing import (
    kelly_position,
    atr_position,
    signal_strength_position,
    risk_parity_position,
    calculate_position,
)

__all__ = [
    "kelly_position",
    "atr_position",
    "signal_strength_position",
    "risk_parity_position",
    "calculate_position",
]
