"""Pure-Python preflight checks for CrownCAD sketch slots.

CrownCAD draws slots from local 2D points and rejects degenerate input at
execution time.  These helpers mirror the confirmed slot semantics so the
agent can validate dimensions with the standard library before submitting
CrownScript: the straight slot needs a non-degenerate center line and a
positive half width, and both arc slots require the half width to stay
strictly below the centerline arc radius.
"""

from __future__ import annotations

import math
from typing import Any, Sequence


class SketchSlotError(ValueError):
    """Raised when slot parameters cannot form a valid sketch slot."""


Point = Sequence[float]

_REL_TOL = 1e-6
_ABS_EPS = 1e-9
_ZERO_EPS = 1e-12


def _point2d(value: Point, name: str) -> tuple[float, float]:
    # Keep malformed input from reaching arithmetic with a confusing error.
    if len(value) != 2:
        raise SketchSlotError(f"{name} 必须是二维坐标")
    result: list[float] = []
    for component in value:
        if isinstance(component, bool) or not isinstance(component, (int, float)):
            raise SketchSlotError(f"{name} 必须是数值坐标")
        number = float(component)
        if not math.isfinite(number):
            raise SketchSlotError(f"{name} 不能包含非有限数值")
        result.append(number)
    return (result[0], result[1])


def _distance(a: tuple[float, float], b: tuple[float, float]) -> float:
    return math.hypot(a[0] - b[0], a[1] - b[1])


def _circumcircle(
    a: tuple[float, float], b: tuple[float, float], c: tuple[float, float]
) -> tuple[tuple[float, float], float]:
    determinant = 2.0 * (
        a[0] * (b[1] - c[1]) + b[0] * (c[1] - a[1]) + c[0] * (a[1] - b[1])
    )
    span = max(1.0, abs(a[0]), abs(a[1]), abs(b[0]), abs(b[1]), abs(c[0]), abs(c[1]))
    if abs(determinant) <= _ABS_EPS * span * span:
        raise SketchSlotError("三点共线，无法确定中心圆弧")
    square_a = a[0] * a[0] + a[1] * a[1]
    square_b = b[0] * b[0] + b[1] * b[1]
    square_c = c[0] * c[0] + c[1] * c[1]
    center_x = (
        square_a * (b[1] - c[1]) + square_b * (c[1] - a[1]) + square_c * (a[1] - b[1])
    ) / determinant
    center_y = (
        square_a * (c[0] - b[0]) + square_b * (a[0] - c[0]) + square_c * (b[0] - a[0])
    ) / determinant
    return (center_x, center_y), _distance((center_x, center_y), a)


def circumcircle(first: Point, second: Point, third: Point) -> dict[str, Any]:
    """Compute the circle through three 2D points; collinear input errors."""

    center, radius = _circumcircle(
        _point2d(first, "first"), _point2d(second, "second"), _point2d(third, "third")
    )
    return {"center": [center[0], center[1]], "radius": radius}


def _arc_half_width(
    radius_pnt: tuple[float, float], center: tuple[float, float], arc_radius: float
) -> float:
    # Confirmed CrownCAD rule: the radius point supplies the slot half width
    # as its radial distance to the centerline arc, on either side.
    return abs(_distance(radius_pnt, center) - arc_radius)


def _validate_arc_half_width(half_width: float, arc_radius: float) -> None:
    if half_width <= _ZERO_EPS:
        raise SketchSlotError("radiusPnt 落在中心圆弧上，半宽必须大于 0")
    if half_width >= arc_radius:
        raise SketchSlotError("半宽必须小于中心圆弧半径，半宽大于等于半径会报错")


def validate_straight_slot(start: Point, end: Point, radius_pnt: Point) -> dict[str, float]:
    """Preflight a straight slot: non-degenerate center line and half width."""

    start_pnt = _point2d(start, "startPnt")
    end_pnt = _point2d(end, "endPnt")
    radius_point = _point2d(radius_pnt, "radiusPnt")
    length = _distance(start_pnt, end_pnt)
    if length <= _ZERO_EPS:
        raise SketchSlotError("startPnt 与 endPnt 重合，直口槽中心线长度为零")
    offset_x = end_pnt[0] - start_pnt[0]
    offset_y = end_pnt[1] - start_pnt[1]
    cross = offset_x * (radius_point[1] - start_pnt[1]) - offset_y * (
        radius_point[0] - start_pnt[0]
    )
    half_width = abs(cross) / length
    if half_width <= _ZERO_EPS:
        raise SketchSlotError("radiusPnt 到中心线的距离为零，半宽必须大于 0")
    return {"centerLineLength": length, "halfWidth": half_width}


def validate_center_arc_slot(
    center: Point, start: Point, end: Point, radius_pnt: Point
) -> dict[str, float]:
    """Preflight a center arc slot: equidistant ends and 0 < r < R."""

    center_pnt = _point2d(center, "centerPnt")
    start_pnt = _point2d(start, "startPnt")
    end_pnt = _point2d(end, "endPnt")
    arc_radius = _distance(center_pnt, start_pnt)
    if arc_radius <= _ZERO_EPS:
        raise SketchSlotError("startPnt 与 centerPnt 重合，无法确定中心圆弧半径")
    end_radius = _distance(center_pnt, end_pnt)
    if abs(end_radius - arc_radius) > _REL_TOL * max(1.0, arc_radius):
        raise SketchSlotError("startPnt 与 endPnt 到 centerPnt 的距离不一致，不能确定同一中心圆弧")
    half_width = _arc_half_width(_point2d(radius_pnt, "radiusPnt"), center_pnt, arc_radius)
    _validate_arc_half_width(half_width, arc_radius)
    return {"centerArcRadius": arc_radius, "halfWidth": half_width}


def validate_three_arc_slot(
    start: Point, third: Point, end: Point, radius_pnt: Point
) -> dict[str, Any]:
    """Preflight a three-point arc slot: non-collinear arc and 0 < r < R."""

    start_pnt = _point2d(start, "startPnt")
    third_pnt = _point2d(third, "thirdPnt")
    end_pnt = _point2d(end, "endPnt")
    center, arc_radius = _circumcircle(start_pnt, third_pnt, end_pnt)
    half_width = _arc_half_width(_point2d(radius_pnt, "radiusPnt"), center, arc_radius)
    _validate_arc_half_width(half_width, arc_radius)
    return {
        "center": [center[0], center[1]],
        "centerArcRadius": arc_radius,
        "halfWidth": half_width,
    }
