"""使用 CrownCAD 返回的真实草图坐标系进行世界与局部坐标转换。

调用方提供正交单位轴及原点；本模块不根据平面法向推算局部轴。
"""

from __future__ import annotations

import math
from typing import Mapping, Sequence


class SketchPlaneError(ValueError):
    """坐标转换输入包含无效向量时抛出。"""


Vector = list[float]


def _vector(value: Sequence[float], name: str) -> Vector:
    # 在向量运算前拦截不规范 API 数据，避免后续只得到难以定位的索引或类型错误。
    if len(value) != 3:
        raise SketchPlaneError(f"{name} 必须包含三个坐标分量")
    result: Vector = []
    for component in value:
        if isinstance(component, bool) or not isinstance(component, (int, float)):
            raise SketchPlaneError(f"{name} 必须是数值向量")
        number = float(component)
        if not math.isfinite(number):
            raise SketchPlaneError(f"{name} 不能包含非有限数值")
        result.append(number)
    return result


def _dot(left: Sequence[float], right: Sequence[float]) -> float:
    return sum(a * b for a, b in zip(left, right))


def world_to_local(
    world_point: Sequence[float], system: Mapping[str, Sequence[float]]
) -> Vector:
    """将世界坐标点换算为该坐标系的局部 x/y/z 坐标。"""

    point = _vector(world_point, "worldPoint")
    origin = _vector(system["origin"], "origin")
    # 对世界坐标偏移量分别投影到正交的局部轴；z 是沿平面法向的有符号距离。
    offset = [point[index] - origin[index] for index in range(3)]
    return [
        _dot(offset, _vector(system["xAxis"], "xAxis")),
        _dot(offset, _vector(system["yAxis"], "yAxis")),
        _dot(offset, _vector(system["normal"], "normal")),
    ]


def local_to_world(
    local_point: Sequence[float], system: Mapping[str, Sequence[float]]
) -> Vector:
    """将局部 x/y/z 坐标换算为世界坐标点。"""

    local = _vector(local_point, "localPoint")
    origin = _vector(system["origin"], "origin")
    axes = [
        _vector(system["xAxis"], "xAxis"),
        _vector(system["yAxis"], "yAxis"),
        _vector(system["normal"], "normal"),
    ]
    # 这是逆基变换：origin + x*xAxis + y*yAxis + z*normal。
    return [
        origin[index] + sum(local[axis] * axes[axis][index] for axis in range(3))
        for index in range(3)
    ]
