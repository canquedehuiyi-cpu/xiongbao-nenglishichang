"""已有 CrownCAD 拓扑的辅助预览；不是 CAD 实体渲染或尺寸验收。"""

from __future__ import annotations

import argparse
import json
import math
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import Any

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.geometry_measurements import dot, norm, number, sub, unit, vector

EPSILON = 1e-6  # 坐标一致性精度，与工程验收容差无关。


def cross(a, b):
    return [
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    ]


def sample_circle(info, adjacent_faces, *, chord_error, epsilon):
    curve, geom = info["Curve"], info["Geom"]
    center, radius = vector(curve["CP"]), number(curve["R"])
    if radius <= 0:
        raise ValueError("圆半径无效")
    start, end, middle = [vector(geom[k]) for k in ("SP", "EP", "MP")]
    radial = [sub(p, center) for p in (start, end, middle)]
    if any(abs(norm(q) - radius) > epsilon for q in radial):
        raise ValueError("圆参数与边界点不一致")
    u = unit(radial[0])
    normal = cross(radial[0], radial[2])
    if norm(normal) <= epsilon * radius:
        normal = None
        for face in adjacent_faces:
            try:
                surface = face["elementInfo"]["Surface"]
                candidate = (
                    surface.get("Norm")
                    if face.get("type") == "Plane"
                    else (
                        surface.get("Axis") if face.get("type") == "Cylinder" else None
                    )
                )
                if candidate is None:
                    continue
                candidate = unit(candidate)
                if all(abs(dot(q, candidate)) <= epsilon for q in radial):
                    normal = candidate
                    break
            except (KeyError, TypeError, ValueError, AttributeError):
                continue
        if normal is None:
            raise ValueError("无法确定圆平面")
    normal = unit(normal)
    if any(abs(dot(q, normal)) > epsilon for q in radial):
        raise ValueError("圆弧点不共面")
    v = unit(cross(normal, u))

    def angle(point):
        q = sub(point, center)
        return math.atan2(dot(q, v), dot(q, u)) % (2 * math.pi)

    sweep = 2 * math.pi if norm(sub(start, end)) <= epsilon else angle(end)
    if norm(sub(start, end)) > epsilon and angle(middle) > sweep + 1e-8:
        sweep -= 2 * math.pi
    if abs(number(geom["L"]) - radius * abs(sweep)) > epsilon:
        raise ValueError("弧长与采样走向不一致")
    # MP 是实际边中点；核对它没有仅仅落在圆上却不在该弧中点。
    midpoint = [
        center[j] + radius * (math.cos(sweep / 2) * u[j] + math.sin(sweep / 2) * v[j])
        for j in range(3)
    ]
    if norm(sub(midpoint, middle)) > epsilon:
        raise ValueError("圆弧中点与走向不一致")
    step = 2 * math.acos(max(-1.0, min(1.0, 1 - chord_error / radius)))
    if step <= 0:
        raise ValueError("绘图精度过小，无法稳定采样")
    count = max(8, math.ceil(abs(sweep) / step))
    if count > 4096:
        raise ValueError("当前精度需要过多采样点")
    return [
        [
            center[j]
            + radius
            * (math.cos(sweep * i / count) * u[j] + math.sin(sweep * i / count) * v[j])
            for j in range(3)
        ]
        for i in range(count + 1)
    ]


def sample_edge(
    edge: Mapping[str, Any],
    adjacent_faces: list[Mapping[str, Any]],
    *,
    chord_error: float,
    epsilon: float,
) -> dict[str, Any]:
    """不可靠的几何返回原因；未知 Curve 绝不退回直线。"""
    try:
        chord_error, epsilon = number(chord_error), number(epsilon)
        if chord_error <= 0 or epsilon <= 0:
            raise ValueError("绘图精度须为正")
        info = edge["elementInfo"]
        if "Curve" in info:
            curve = info["Curve"]
            if not isinstance(curve, Mapping) or not {"CP", "R"} <= curve.keys():
                shape = (
                    ", ".join(map(str, curve))
                    if isinstance(curve, Mapping)
                    else type(curve).__name__
                )
                raise ValueError(f"不支持的 Curve 结构：{shape}")
            points = sample_circle(
                info, adjacent_faces, chord_error=chord_error, epsilon=epsilon
            )
        else:
            geom = info["Geom"]
            a, b, middle = [vector(geom[k]) for k in ("SP", "EP", "MP")]
            length = norm(sub(a, b))
            if length <= epsilon:
                raise ValueError("退化直线边")
            if (
                abs(number(geom["L"]) - length) > epsilon
                or norm(sub(middle, [(x + y) / 2 for x, y in zip(a, b)])) > epsilon
            ):
                raise ValueError("直线参数不一致")
            points = [a, b]
        return {"points": points, "reason": ""}
    except (KeyError, TypeError, ValueError, AttributeError, OverflowError) as exc:
        return {"points": [], "reason": str(exc)}


def view_basis(name: str) -> tuple[list[float], list[float], list[float]]:
    cameras = {
        "overall": [-1, 0.7, -1.7],
        "front": [0, 0, -1],
        "top": [0, 1, 0],
        "right": [1, 0, 0],
    }
    camera = unit(cameras[name])
    reference_up = [0, 0, -1] if abs(dot(camera, [0, 1, 0])) > 0.99 else [0, 1, 0]
    right = unit(cross(reference_up, camera))
    return right, unit(cross(camera, right)), camera


def project_point(point, basis):
    point = vector(point)
    return tuple(dot(point, direction) for direction in basis)


def _intersects(a, b, c, d, epsilon):
    # 相交或接触都拒绝；平面孔口不能靠猜测修补。
    def orientation(p, q, r):
        return (q[0] - p[0]) * (r[1] - p[1]) - (q[1] - p[1]) * (r[0] - p[0])

    def on(p, q, r):
        return abs(orientation(p, q, r)) <= epsilon * max(math.dist(p, q), 1) and all(
            min(p[i], q[i]) - epsilon <= r[i] <= max(p[i], q[i]) + epsilon
            for i in (0, 1)
        )

    if any((on(a, b, c), on(a, b, d), on(c, d, a), on(c, d, b))):
        return True
    return (
        orientation(a, b, c) * orientation(a, b, d) < 0
        and orientation(c, d, a) * orientation(c, d, b) < 0
    )


def _inside(point, ring):
    # 调用前已排除环间接触和相交，因此射线法只需处理严格包含。
    x, y = point
    inside = False
    for a, b in zip(ring, ring[1:] + ring[:1]):
        if (a[1] > y) != (b[1] > y) and x < (b[0] - a[0]) * (y - a[1]) / (
            b[1] - a[1]
        ) + a[0]:
            inside = not inside
    return inside


def _validate_rings(loops, normal, epsilon):
    origin = loops[0][0]
    u = unit(sub(loops[0][1], origin))
    v = unit(cross(normal, u))
    rings = []
    for loop in loops:
        if any(abs(dot(sub(p, origin), normal)) > epsilon for p in loop):
            raise ValueError("边界不共面")
        ring = [(dot(sub(p, origin), u), dot(sub(p, origin), v)) for p in loop[:-1]]
        segments = list(zip(ring, ring[1:] + ring[:1]))
        if (
            len(ring) < 3
            or abs(sum(a[0] * b[1] - b[0] * a[1] for a, b in segments)) <= epsilon**2
        ):
            raise ValueError("边界面积退化")
        for i, (a, b) in enumerate(segments):
            for j, (c, d) in enumerate(segments[:i]):
                if j == i - 1 or (i == len(segments) - 1 and j == 0):
                    continue
                if _intersects(a, b, c, d, epsilon):
                    raise ValueError("边界自交或接触")
        rings.append(ring)
    for i, ring in enumerate(rings):
        for other in rings[:i]:
            if any(
                _intersects(a, b, c, d, epsilon)
                for a, b in zip(ring, ring[1:] + ring[:1])
                for c, d in zip(other, other[1:] + other[:1])
            ):
                raise ValueError("边界环相交或接触")
    return [
        sum(_inside(ring[0], other) for j, other in enumerate(rings) if i != j)
        for i, ring in enumerate(rings)
    ]


def build_face_loops(
    graph: Mapping[str, Any],
    face_id: str | int,
    *,
    epsilon: float,
    chord_error: float = 0.05,
) -> dict[str, Any]:
    """消费实际边各一次，拒绝分叉、开环及自交；返回嵌套深度供 mask 使用。"""
    try:
        epsilon = number(epsilon)
        if epsilon <= 0:
            raise ValueError("坐标精度须为正")
        face = graph["faces"][str(face_id)]
        if face.get("type") != "Plane":
            raise ValueError("非 Plane 面不填色")
        normal = unit(face["elementInfo"]["Surface"]["Norm"])
        edge_ids = [str(k) for k in face["edgeIds"]]
        if not edge_ids or len(set(edge_ids)) != len(edge_ids):
            raise ValueError("边界为空或边重复")
        pieces = []
        for key in edge_ids:
            sampled = sample_edge(
                graph["edges"][key], [face], chord_error=chord_error, epsilon=epsilon
            )
            if sampled["reason"]:
                raise ValueError("边 " + key + ": " + sampled["reason"])
            pieces.append(sampled["points"])
        # 每个端点必须只有一个伙伴；整圆可独立闭合，但不能与其他环接触。
        for i, piece in enumerate(pieces):
            for side in (0, -1):
                matches = [
                    (j, k)
                    for j, p in enumerate(pieces)
                    for k in (0, -1)
                    if (j, k) != (i, side) and norm(sub(piece[side], p[k])) <= epsilon
                ]
                if len(matches) != 1:
                    raise ValueError("边界未闭合或连接有歧义")
        remaining = list(pieces)
        loops = []
        while remaining:
            loop = list(remaining.pop(0))
            while norm(sub(loop[0], loop[-1])) > epsilon:
                found = [
                    (i, side)
                    for i, p in enumerate(remaining)
                    for side in (0, -1)
                    if norm(sub(loop[-1], p[side])) <= epsilon
                ]
                if len(found) != 1:
                    raise ValueError("边界未闭合或分叉")
                i, side = found[0]
                piece = remaining.pop(i)
                if side == -1:
                    piece = list(reversed(piece))
                loop.extend(piece[1:])
            loop[-1] = loop[0]
            loops.append(loop)
        depths = _validate_rings(loops, normal, epsilon)
        return {"loops": loops, "depths": depths, "reason": ""}
    except (KeyError, TypeError, ValueError, AttributeError, OverflowError) as exc:
        return {"loops": [], "depths": [], "reason": str(exc)}


def _font(ImageFont):
    # 候选是可选项；缺失时使用 Pillow 字体，并把提示写入说明。
    candidates = [
        Path("C:/Windows/Fonts/msyh.ttc"),
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
        Path("/System/Library/Fonts/PingFang.ttc"),
    ]
    for path in candidates:
        if path.is_file():
            try:
                return ImageFont.truetype(str(path), 18), str(path)
            except OSError:
                continue
    return ImageFont.load_default(), "default (中文可能缺字，请阅读 JSON 说明)"


def _pixel_mapper(basis, origin, center, scale):
    """每个视图独立绑定映射参数，避免引用循环中的后续视图。"""

    def pixel(point):
        px, py, _ = project_point(point, basis)
        return origin[0] + (px - center[0]) * scale, origin[1] - (
            py - center[1]
        ) * scale

    return pixel


def render_preview(
    graph: Mapping[str, Any],
    output: str | Path,
    *,
    views: list[str],
    mode: str,
    title: str,
    chord_error: float,
) -> dict[str, Any]:
    """只读拓扑，生成 PNG 和限制说明。退出码与模型验收没有关系。"""
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError as exc:
        raise ValueError(
            '绘图需要 Pillow；请在当前 Python 环境运行 python -m pip install -r "'
            f'{Path(__file__).resolve().parents[1] / "requirements.txt"}"'
        ) from exc
    chord_error = number(chord_error)
    if chord_error <= 0:
        raise ValueError("弦高误差须为正")
    if (
        mode not in ("wireframe", "planar")
        or not views
        or len(set(views)) != len(views)
    ):
        raise ValueError("绘图模式或视图无效")
    if not isinstance(graph, Mapping) or not all(
        isinstance(graph.get(k), Mapping) for k in ("edges", "faces")
    ):
        raise ValueError("需要公共采集器格式的 edges 和 faces")
    try:
        bases = [view_basis(name) for name in views]
    except (KeyError, TypeError) as exc:
        raise ValueError("未知视图") from exc
    adjacent = {}
    for face in graph["faces"].values():
        if isinstance(face, Mapping):
            for edge_id in face.get("edgeIds", []):
                adjacent.setdefault(str(edge_id), []).append(face)
    sampled, skipped_edges = {}, []
    for key, edge in graph["edges"].items():
        result = sample_edge(
            edge, adjacent.get(str(key), []), chord_error=chord_error, epsilon=EPSILON
        )
        if result["points"]:
            sampled[str(key)] = result["points"]
        else:
            skipped_edges.append({"id": str(key), "reason": result["reason"]})
    if not sampled:
        raise ValueError("没有可绘制的有效边")
    faces, skipped_faces = [], []
    if mode == "planar":
        for key in graph["faces"]:
            result = build_face_loops(
                graph, key, epsilon=EPSILON, chord_error=chord_error
            )
            if result["reason"]:
                face = graph["faces"][key]
                skipped_faces.append(
                    {
                        "id": str(key),
                        "type": face.get("type") if isinstance(face, Mapping) else None,
                        "reason": result["reason"],
                    }
                )
            else:
                faces.append(result)
    partial = bool(skipped_edges or skipped_faces)
    columns = min(2, len(views))
    rows = math.ceil(len(views) / columns)
    width, height = 640 * columns, 440 * rows + 80
    picture = Image.new("RGB", (width, height), "#f5f7fa")
    draw = ImageDraw.Draw(picture)
    font, font_path = _font(ImageFont)
    draw.text(
        (20, 12),
        "拓扑数据预览 / Topology preview " + str(title),
        fill="#253f58",
        font=font,
    )
    draw.text(
        (20, 40),
        "存在未绘制部分，详见说明 / Partial"
        if partial
        else "辅助示意；非消隐工程图 / Auxiliary view",
        fill="#526579",
        font=font,
    )
    for index, (name, basis) in enumerate(zip(views, bases)):
        x0, y0 = index % columns * 640, index // columns * 440 + 80
        draw.rounded_rectangle(
            (x0 + 12, y0 + 8, x0 + 628, y0 + 432), radius=14, fill="white"
        )
        draw.text((x0 + 30, y0 + 22), name, fill="#253f58", font=font)
        points = [project_point(p, basis) for piece in sampled.values() for p in piece]
        lo_x, hi_x = min(p[0] for p in points), max(p[0] for p in points)
        lo_y, hi_y = min(p[1] for p in points), max(p[1] for p in points)
        scale = min(550 / max(hi_x - lo_x, EPSILON), 340 / max(hi_y - lo_y, EPSILON))

        pixel = _pixel_mapper(
            basis, (x0 + 320, y0 + 240), ((lo_x + hi_x) / 2, (lo_y + hi_y) / 2), scale
        )

        if mode == "planar":
            # 画家排序是近似展示；mask 的孔透出原背景，不涂白盖住后面的面。
            ordered = sorted(
                faces,
                key=lambda f: (
                    sum(project_point(p, basis)[2] for loop in f["loops"] for p in loop)
                    / sum(len(loop) for loop in f["loops"])
                ),
            )
            for face in ordered:
                mask = Image.new("L", picture.size, 0)
                mask_draw = ImageDraw.Draw(mask)
                for depth, loop in sorted(
                    zip(face["depths"], face["loops"]), key=lambda pair: pair[0]
                ):
                    polygon = [pixel(p) for p in loop]
                    area = sum(
                        a[0] * b[1] - b[0] * a[1]
                        for a, b in zip(polygon, polygon[1:] + polygon[:1])
                    )
                    if abs(area) > 1e-6:
                        mask_draw.polygon(polygon, fill=255 if depth % 2 == 0 else 0)
                picture.paste("#98b4c7", (0, 0, width, height), mask)
        for piece in sampled.values():
            draw.line([pixel(p) for p in piece], fill="#2e536d", width=2)
    output = Path(output)
    if output.suffix.lower() != ".png":
        raise ValueError("输出路径必须是 .png")
    metadata = {
        "source_path": None,
        "views": list(views),
        "mode": mode,
        "chord_error_mm": chord_error,
        "coordinate_epsilon_mm": EPSILON,
        "drawn_edge_count": len(sampled),
        "skipped_edges": skipped_edges,
        "skipped_faces": skipped_faces,
        "font": font_path,
        "world_up": [0, 1, 0],
        "camera_directions": {
            name: list(basis[2]) for name, basis in zip(views, bases)
        },
        "limitations": [
            "包含遮挡边，不是消隐工程图",
            "平面填色采用近似深度排序，不还原非平面曲面",
            "不替代浏览器查看、尺寸测量或干涉检查",
        ],
        "exit_code": 2 if partial else 0,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    picture.save(output, format="PNG")
    output.with_suffix(".render.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    return metadata


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--topology", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument(
        "--views",
        nargs="+",
        default=["overall", "front", "top", "right"],
        choices=["overall", "front", "top", "right"],
    )
    parser.add_argument("--mode", choices=["wireframe", "planar"], default="wireframe")
    parser.add_argument("--title", default="")
    parser.add_argument("--chord-error", type=float, default=0.05)
    args = parser.parse_args(argv)
    try:
        graph = json.loads(args.topology.read_text(encoding="utf-8-sig"))
        metadata = render_preview(
            graph,
            args.output,
            views=args.views,
            mode=args.mode,
            title=args.title,
            chord_error=args.chord_error,
        )
        metadata["source_path"] = str(args.topology)
        args.output.with_suffix(".render.json").write_text(
            json.dumps(metadata, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
            encoding="utf-8",
        )
        print(
            f"预览已生成：{args.output}；绘制 {metadata['drawn_edge_count']} 条边；退出码 {metadata['exit_code']}"
        )
        return metadata["exit_code"]
    except (OSError, ValueError, TypeError) as exc:
        print(f"无法生成预览：{exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
