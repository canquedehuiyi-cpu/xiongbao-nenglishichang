"""CrownCAD 实际几何测量；候选不等于目标孔。"""

from __future__ import annotations

# scripts/geometry_measurements.py
import math
from collections.abc import Mapping
from typing import Any


def number(value: Any) -> float:
    # bool、NaN、无穷大不能进入几何计算。
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("不是有效数字")  # noqa: TRY004 -- 公共测量统一报告数据无效。
    try:
        value = float(value)
    except OverflowError as exc:
        raise ValueError("数字超出有限范围") from exc
    if not math.isfinite(value):
        raise ValueError("数字不是有限值")
    return value


def vector(value: Any) -> list[float]:
    if not isinstance(value, (list, tuple)) or len(value) != 3:
        raise ValueError("需要三个坐标分量")
    return [number(item) for item in value]


def sub(a, b):
    return [x - y for x, y in zip(a, b)]


def dot(a, b):
    return sum(x * y for x, y in zip(a, b))


def norm(v):
    return math.hypot(*v)


def unit(v: Any) -> list[float]:
    v = vector(v)
    length = norm(v)
    if not math.isfinite(length) or length <= 1e-12:
        raise ValueError("方向向量为零或超出有效范围")
    return [item / length for item in v]


def axis_distance(point: Any, origin: Any, axis: Any) -> float:
    # Origin 可沿轴移动，不可直接用它到目标点的距离代替轴线距离。
    delta = sub(vector(point), vector(origin))
    direction = unit(axis)
    projection = dot(delta, direction)
    return norm(sub(delta, [projection * item for item in direction]))


def axis_angle(actual: Any, expected: Any, directed: bool = False) -> float:
    cosine = dot(unit(actual), unit(expected))
    # 圆孔轴线一般不区分正反；明确要求朝向时 directed=True。
    if not directed:
        cosine = abs(cosine)
    return math.degrees(math.acos(max(-1.0, min(1.0, cosine))))


def measurement(values=None, refs=(), reason="", evidence=""):
    # measured 表示取得实际数字，是否符合要求由比较函数决定。
    return {
        "status": "unverified" if reason else "measured",
        "values": {} if values is None else values,
        "objects": list(refs),
        "evidence": evidence,
        "reason": reason,
    }


def collect_cylinders(graph: Mapping[str, Any], evidence: str = "") -> dict[str, Any]:
    """从正式 Cylinder 类型读取候选；坏图抛错，不伪造零候选。"""
    # 整理圆柱面候选，不把圆柱面直接叫作孔。
    if not isinstance(graph, Mapping) or not all(
        isinstance(graph.get(key), Mapping) for key in ("entities", "faces")
    ):
        raise ValueError("缺少有效的 entities 或 faces 集合")
    candidates, unreadable = [], []
    owners = {}
    for entity_id, entity in graph["entities"].items():
        if not isinstance(entity, Mapping) or not isinstance(
            entity.get("faceIds", []), list
        ):
            raise TypeError("实体节点或面引用无效")
        for face_id in entity.get("faceIds", []):
            owners.setdefault(str(face_id), []).append(str(entity_id))
    for face_id, face in graph["faces"].items():
        if not isinstance(face, Mapping):
            raise TypeError("面节点无效")
        if face.get("type") != "Cylinder":
            continue
        try:
            surface = face["elementInfo"]["Surface"]
            origin, axis = vector(surface["Origin"]), unit(surface["Axis"])
            radius = number(surface["Radius"])
            if radius <= 0:
                raise ValueError("半径不为正")
            candidates.append(
                {
                    "face_id": str(face_id),
                    "entity_ids": owners.get(str(face_id), []),
                    "origin": origin,
                    "axis": axis,
                    "diameter_mm": number(2 * radius),
                    "evidence": evidence,
                }
            )
        except (KeyError, TypeError, ValueError, AttributeError):
            unreadable.append(str(face_id))
    return {"candidates": candidates, "unreadable_faces": unreadable}


def find_cylinder_candidates(
    candidates, *, point, axis, search_mm, search_deg, entity_id=None
):
    # 根据区域和方向整理候选，不输入期望孔径，不硬选第一名。
    search_mm, search_deg = number(search_mm), number(search_deg)
    if search_mm <= 0 or not 0 < search_deg <= 90:
        raise ValueError("查找距离须为正，轴线查找角须在 0 到 90 度之间")
    point, axis = vector(point), unit(axis)  # 空候选时也检查参数。
    found = []
    for candidate in candidates:
        if entity_id is not None and str(entity_id) not in candidate["entity_ids"]:
            continue
        distance = axis_distance(point, candidate["origin"], candidate["axis"])
        angle = axis_angle(candidate["axis"], axis)
        if distance <= search_mm and angle <= search_deg:
            found.append(
                {**candidate, "axis_distance_mm": distance, "axis_angle_deg": angle}
            )
    return sorted(
        found, key=lambda item: (item["axis_distance_mm"], item["axis_angle_deg"])
    )


def measure_cylinder(candidate: Mapping[str, Any]) -> dict[str, Any]:
    # 返回指定圆柱面的数据；调用方确认它属于目标孔壁。
    try:
        diameter = number(candidate["diameter_mm"])
        if diameter <= 0:
            raise ValueError("直径无效")
        return measurement(
            {"diameter_mm": diameter},
            [candidate["face_id"]],
            evidence=candidate.get("evidence", ""),
        )
    except (KeyError, TypeError, ValueError, AttributeError):
        return measurement(reason="圆柱面数据不足或无效")


def plane_parameters(graph, face_id):
    # 读取法向和边界实际点，不取包围盒中心代替。
    face = graph["faces"][str(face_id)]
    if face.get("type") != "Plane":
        raise ValueError("所选面不是正式 Plane 类型")
    normal = unit(face["elementInfo"]["Surface"]["Norm"])
    for edge_id in face.get("edgeIds", []):
        info = graph["edges"].get(str(edge_id), {}).get("elementInfo", {})
        geom = info.get("Geom", {}) if isinstance(info, Mapping) else {}
        if "SP" in geom:
            return vector(geom["SP"]), normal
    raise ValueError("未取得平面上的实际点")


def measure_plane_gap(
    graph: Mapping[str, Any],
    first_face: str | int,
    second_face: str | int,
    epsilon: float,
    evidence: str = "",
) -> dict[str, Any]:
    try:
        epsilon = number(epsilon)
        if epsilon <= 0:
            raise ValueError("数值判断精度应为正")
        if str(first_face) == str(second_face):
            raise ValueError("不能用同一张面测两面距离")
        p1, n1 = plane_parameters(graph, first_face)
        p2, n2 = plane_parameters(graph, second_face)
        # epsilon 用于法向一致性判断，不是板厚工程公差。
        if (
            norm(sub(n1, n2)) > epsilon
            and norm([a + b for a, b in zip(n1, n2)]) > epsilon
        ):
            raise ValueError("两张面不平行")
        gap = abs(dot(sub(p2, p1), n1))
        return measurement(
            {"gap_mm": gap}, [str(first_face), str(second_face)], evidence=evidence
        )
    except (KeyError, TypeError, ValueError, AttributeError) as error:
        return measurement(reason=str(error), evidence=evidence)


def read_slot_edge(graph, edge_id, epsilon):
    info = graph["edges"][str(edge_id)]["elementInfo"]
    geom = info["Geom"]
    start, end, middle = vector(geom["SP"]), vector(geom["EP"]), vector(geom["MP"])
    length = number(geom["L"])
    if length <= epsilon:
        raise ValueError("槽边退化")
    curve = info.get("Curve")
    if "Curve" in info:
        # 有曲线字段但不支持时，不能退回当直线。
        if not isinstance(curve, Mapping):
            raise ValueError("无法读取槽端曲线")
        radius, center = number(curve["R"]), vector(curve["CP"])
        sweep = abs(number(curve["EA"]) - number(curve["SA"]))
        if radius <= 0 or not math.isclose(sweep, 180.0, abs_tol=1e-6, rel_tol=0):
            raise ValueError("槽端不是已支持的半圆弧")
        if abs(length - math.pi * radius) > epsilon:
            raise ValueError("弧长与半圆参数不一致")
        if any(
            abs(norm(sub(p, center)) - radius) > epsilon for p in (start, end, middle)
        ):
            raise ValueError("圆弧点和半径不一致")
        if norm([a + b - 2 * c for a, b, c in zip(start, end, center)]) > epsilon:
            raise ValueError("半圆端点不对称")
        return {
            "kind": "arc",
            "start": start,
            "end": end,
            "middle": middle,
            "radius": radius,
            "center": center,
        }
    # 无曲线字段也核对长度和中点，避免误认未知曲线。
    if abs(length - norm(sub(end, start))) > epsilon:
        raise ValueError("不是可确认的直线边")
    if norm(sub(middle, [(a + b) / 2 for a, b in zip(start, end)])) > epsilon:
        raise ValueError("直线中点不一致")
    return {"kind": "line", "start": start, "end": end, "middle": middle}


def measure_simple_slot(
    graph: Mapping[str, Any],
    edge_ids: list[str | int],
    epsilon: float,
    evidence: str = "",
) -> dict[str, Any]:
    try:
        epsilon = number(epsilon)
        if epsilon <= 0 or len(edge_ids) != 4 or len({str(i) for i in edge_ids}) != 4:
            raise ValueError("需要四条不同的边和正的数值精度")
        edges = [read_slot_edge(graph, edge_id, epsilon) for edge_id in edge_ids]
        arcs = [edge for edge in edges if edge["kind"] == "arc"]
        lines = [edge for edge in edges if edge["kind"] == "line"]
        if len(arcs) != 2 or len(lines) != 2:
            raise ValueError("仅支持两半圆加两直线的槽口")
        first, second = arcs
        radius = first["radius"]
        if abs(radius - second["radius"]) > epsilon:
            raise ValueError("两端半径不一致")
        delta = sub(second["center"], first["center"])
        distance = norm(delta)
        if distance <= epsilon:
            raise ValueError("两端圆心重合")
        direction = unit(delta)
        # 半圆直径方向必须垂直槽中心线。
        radial = sub(first["start"], first["center"])
        if abs(dot(radial, direction)) > epsilon:
            raise ValueError("半圆边与槽中心线不垂直")
        offset = [radius * item for item in unit(radial)]
        ends = [
            [[c + s * d for c, d in zip(arc["center"], offset)] for s in (1, -1)]
            for arc in arcs
        ]
        # 两端端点都必须落在同一槽平面、相同宽度位置。
        for arc, expected_ends in zip(arcs, ends):
            for point in (arc["start"], arc["end"]):
                if min(norm(sub(point, target)) for target in expected_ends) > epsilon:
                    raise ValueError("槽端边界不共面或不对齐")
        # 半圆中点必须朝外；朝内形成另一种轮廓。
        expected_mids = [
            [c - radius * d for c, d in zip(first["center"], direction)],
            [c + radius * d for c, d in zip(second["center"], direction)],
        ]
        for arc, expected_mid in zip(arcs, expected_mids):
            if norm(sub(arc["middle"], expected_mid)) > epsilon:
                raise ValueError("半圆方向不符合直腰形槽")
        remaining = list(lines)
        for side in (0, 1):
            a, b = ends[0][side], ends[1][side]
            matches = [
                line
                for line in remaining
                if (
                    norm(sub(line["start"], a)) <= epsilon
                    and norm(sub(line["end"], b)) <= epsilon
                )
                or (
                    norm(sub(line["start"], b)) <= epsilon
                    and norm(sub(line["end"], a)) <= epsilon
                )
            ]
            if len(matches) != 1:
                raise ValueError("槽侧边连接不完整或有歧义")
            remaining.remove(matches[0])
        return measurement(
            {
                "width_mm": 2 * radius,
                "center_distance_mm": distance,
                "total_length_mm": distance + 2 * radius,
            },
            [str(i) for i in edge_ids],
            evidence=evidence,
        )
    except (KeyError, TypeError, ValueError, AttributeError) as error:
        return measurement(reason="无法测量简单槽：" + str(error), evidence=evidence)


def measure_arc_radius(
    graph: Mapping[str, Any], edge_id: str | int, epsilon: float, evidence: str = ""
) -> dict[str, Any]:
    # 这里只测已确认圆弧边的半径，不把它当作完整圆角验收。
    try:
        epsilon = number(epsilon)
        if epsilon <= 0:
            raise ValueError("数值判断精度须为正")
        info = graph["edges"][str(edge_id)]["elementInfo"]
        curve, geom = info["Curve"], info["Geom"]
        radius, center = number(curve["R"]), vector(curve["CP"])
        if radius <= 0:
            raise ValueError("半径不为正")
        for key in ("SP", "EP", "MP"):
            if abs(norm(sub(vector(geom[key]), center)) - radius) > epsilon:
                raise ValueError("边界点与圆弧半径不一致")
        return measurement({"radius_mm": radius}, [str(edge_id)], evidence=evidence)
    except (KeyError, TypeError, ValueError, AttributeError) as error:
        return measurement(reason="圆弧半径未验证：" + str(error), evidence=evidence)


def measure_entity_count(
    graph: Mapping[str, Any], evidence: str = ""
) -> dict[str, Any]:
    # 是否为本轮全量采集由调用方确认；缺少集合不能默认为零实体。
    entities = graph.get("entities") if isinstance(graph, Mapping) else None
    if not isinstance(entities, Mapping) or not evidence:
        return measurement(reason="缺少完整实体集合或采集依据")
    return measurement({"count": len(entities)}, list(entities), evidence=evidence)
