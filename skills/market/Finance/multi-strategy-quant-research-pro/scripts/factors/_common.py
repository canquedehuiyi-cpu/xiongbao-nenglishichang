# -*- coding: utf-8 -*-
"""因子库内部共享工具（仅因子模块使用，不对外注册为因子）。"""


def numeric_series(history) -> list:
    """把多期历史序列统一提取为有序数值列表。

    兼容两种元素形态：
    - 裸数值（int/float）；
    - 字典（数据层年度序列形态），取值键 "value"，兼容 ROE 序列的 "roe" 键。

    布尔值与非数值一律忽略，返回 float 列表，供稳定性/加速/扩张类因子计算。
    """
    values = []
    for item in history or []:
        if isinstance(item, dict):
            value = item.get("value", item.get("roe"))
        else:
            value = item
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            continue
        values.append(float(value))
    return values


def chronological_series(history) -> list:
    """提取按时间从早到晚排列的数值序列（供"末期-初期"类变化量因子使用）。

    - 字典形态（数据层年度序列，带 "year"）按年份升序，确保 [-1] 为最新年度；
    - 裸数值形态无法判断时间，按调用方给出的先后顺序保留（契约为从早到晚）。
    """
    items = []
    for item in history or []:
        if isinstance(item, dict):
            year = item.get("year")
            value = item.get("value", item.get("roe"))
            if isinstance(year, int) and isinstance(value, (int, float)) and not isinstance(value, bool):
                items.append((year, float(value)))
        elif isinstance(item, (int, float)) and not isinstance(item, bool):
            items.append((len(items), float(item)))
    items.sort(key=lambda pair: pair[0])
    return [value for _, value in items]
