import argparse
import hashlib
import json
import math
import os
import re
import shutil
import sys
import tempfile
from pathlib import Path

try:
    from PIL import Image
except ImportError:
    print("缺少 Pillow，无法处理图像。请在当前 Python 环境安装 Pillow。", file=sys.stderr)
    raise SystemExit(2)


SCHEMA_VERSION = 1
IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp"}


class AssetToolError(Exception):
    pass


def natural_key(value):
    return [int(part) if part.isdigit() else part.lower() for part in re.split(r"(\d+)", value)]


def frame_number(path):
    matches = re.findall(r"\d+", path.stem)
    if not matches:
        raise AssetToolError(f"文件名缺少帧号：{path.name}")
    return int(matches[-1])


def discover_frames(directory):
    root = Path(directory)
    if not root.is_dir():
        raise AssetToolError(f"帧目录不存在：{root}")
    paths = sorted(
        [path for path in root.iterdir() if path.is_file() and path.suffix.lower() in IMAGE_SUFFIXES],
        key=lambda path: natural_key(path.name),
    )
    if not paths:
        raise AssetToolError("帧目录中没有可读图片")
    numbers = [frame_number(path) for path in paths]
    if len(numbers) != len(set(numbers)):
        raise AssetToolError("发现重复帧号")
    return paths


def image_hash(image):
    rgba = image.convert("RGBA")
    digest = hashlib.sha256()
    digest.update(f"{rgba.width}x{rgba.height}:RGBA".encode())
    digest.update(rgba.tobytes())
    return digest.hexdigest()


def alpha_bbox(image):
    rgba = image.convert("RGBA")
    return rgba.getchannel("A").getbbox()


def inspect_frames(paths):
    records = []
    hashes = {}
    for path in paths:
        try:
            with Image.open(path) as image:
                image.load()
                digest = image_hash(image)
                bbox = alpha_bbox(image)
                record = {
                    "file": path.name,
                    "size": [image.width, image.height],
                    "mode": image.mode,
                    "format": image.format,
                    "has_alpha": "A" in image.getbands() or "transparency" in image.info,
                    "content_bbox": list(bbox) if bbox else None,
                    "content_hash": digest,
                }
        except Exception as error:
            raise AssetToolError(f"图片无法读取：{path.name}：{error}") from error
        hashes.setdefault(digest, []).append(path.name)
        records.append(record)
    duplicate_groups = [files for files in hashes.values() if len(files) > 1]
    for record in records:
        record["duplicate"] = any(record["file"] in group for group in duplicate_groups)
    return records


def ensure_writable_output(path, overwrite):
    target = Path(path)
    if target.exists() and not overwrite:
        raise AssetToolError(f"输出已存在：{target}")
    target.parent.mkdir(parents=True, exist_ok=True)
    return target


def save_image_atomic(image, output, overwrite, **kwargs):
    target = ensure_writable_output(output, overwrite)
    handle, temporary = tempfile.mkstemp(prefix=f".{target.name}.", suffix=target.suffix, dir=target.parent)
    os.close(handle)
    temp_path = Path(temporary)
    try:
        image.save(temp_path, **kwargs)
        if target.exists():
            target.unlink()
        os.replace(temp_path, target)
    except Exception:
        temp_path.unlink(missing_ok=True)
        raise


def normalize_frames(paths, output_dir, canvas_size, anchor, overwrite=False, alignment="foot-center"):
    if alignment not in {"preserve", "foot-center"}:
        raise AssetToolError("不支持的对齐模式")
    width, height = canvas_size
    anchor_x, anchor_y = anchor
    if width <= 0 or height <= 0 or not 0 <= anchor_x < width or not 0 <= anchor_y < height:
        raise AssetToolError("画布或锚点超出有效范围")
    target = Path(output_dir)
    if target.exists() and not overwrite:
        raise AssetToolError(f"输出已存在：{target}")
    temporary = Path(tempfile.mkdtemp(prefix=f".{target.name}.", dir=target.parent))
    records = []
    try:
        for index, path in enumerate(paths):
            with Image.open(path) as source:
                frame = source.convert("RGBA")
                bbox = frame.getchannel("A").getbbox()
                if not bbox:
                    raise AssetToolError(f"帧没有可见内容：{path.name}")
                source_anchor_x = (bbox[0] + bbox[2]) // 2
                source_anchor_y = bbox[3] - 1
                offset = (0, 0) if alignment == "preserve" else (anchor_x - source_anchor_x, anchor_y - source_anchor_y)
                moved_bbox = (
                    bbox[0] + offset[0],
                    bbox[1] + offset[1],
                    bbox[2] + offset[0],
                    bbox[3] + offset[1],
                )
                if moved_bbox[0] < 0 or moved_bbox[1] < 0 or moved_bbox[2] > width or moved_bbox[3] > height:
                    raise AssetToolError(f"统一画布会裁切主体：{path.name}")
                canvas = Image.new("RGBA", (width, height), (0, 0, 0, 0))
                canvas.alpha_composite(frame, offset)
                filename = f"frame-{index:03d}.png"
                canvas.save(temporary / filename, format="PNG", optimize=False)
                records.append({"source": path.name, "file": filename, "offset": list(offset)})
        if target.exists():
            shutil.rmtree(target)
        os.replace(temporary, target)
        return records
    except Exception:
        shutil.rmtree(temporary, ignore_errors=True)
        raise


def grid_for(frame_count, columns=None):
    if frame_count <= 0:
        raise AssetToolError("图集至少需要一帧")
    cols = columns or math.ceil(math.sqrt(frame_count))
    if cols <= 0:
        raise AssetToolError("图集列数必须大于零")
    return cols, math.ceil(frame_count / cols)


def build_sheet(paths, output, columns=None, overwrite=False):
    sizes = []
    frames = []
    for path in paths:
        with Image.open(path) as source:
            frame = source.convert("RGBA")
            frame.load()
            frames.append(frame.copy())
            sizes.append(frame.size)
    if len(set(sizes)) != 1:
        raise AssetToolError("图集输入帧尺寸不一致")
    cell_width, cell_height = sizes[0]
    cols, rows = grid_for(len(frames), columns)
    sheet = Image.new("RGBA", (cell_width * cols, cell_height * rows), (0, 0, 0, 0))
    for index, frame in enumerate(frames):
        sheet.alpha_composite(frame, ((index % cols) * cell_width, (index // cols) * cell_height))
    save_image_atomic(sheet, output, overwrite, format="PNG", optimize=False)
    return {
        "size": [sheet.width, sheet.height],
        "grid": [cols, rows],
        "cell_size": [cell_width, cell_height],
        "frame_count": len(frames),
    }


def extract_sheet_cells(sheet_path, grid, cell_size, frame_count):
    cols, rows = grid
    cell_width, cell_height = cell_size
    with Image.open(sheet_path) as source:
        sheet = source.convert("RGBA")
        if sheet.size != (cols * cell_width, rows * cell_height):
            raise AssetToolError("图集尺寸与网格不一致")
        return [
            sheet.crop(
                (
                    (index % cols) * cell_width,
                    (index // cols) * cell_height,
                    (index % cols + 1) * cell_width,
                    (index // cols + 1) * cell_height,
                )
            )
            for index in range(frame_count)
        ]


def validate_durations(durations, frame_count):
    if len(durations) != frame_count or any(value <= 0 for value in durations):
        raise AssetToolError("帧时长必须与帧数一致且全部大于零")


def build_gif(paths, output, durations, mode="loop", overwrite=False):
    validate_durations(durations, len(paths))
    if mode not in {"loop", "once", "hold-last"}:
        raise AssetToolError("播放模式必须是 loop、once 或 hold-last")
    frames = []
    for path in paths:
        with Image.open(path) as source:
            frames.append(source.convert("RGBA"))
    target = ensure_writable_output(output, overwrite)
    handle, temporary = tempfile.mkstemp(prefix=f".{target.name}.", suffix=".gif", dir=target.parent)
    os.close(handle)
    temp_path = Path(temporary)
    try:
        options = {
            "save_all": True,
            "append_images": frames[1:],
            "duration": durations,
            "disposal": 2,
            "optimize": False,
        }
        if mode == "loop":
            options["loop"] = 0
        frames[0].save(temp_path, format="GIF", **options)
        if target.exists():
            target.unlink()
        os.replace(temp_path, target)
    except Exception:
        temp_path.unlink(missing_ok=True)
        raise
    return {"frame_count": len(frames), "durations": list(durations), "mode": mode}


def write_json(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n")


def animation_metadata(asset_id, sheet, anchor, durations, mode, source_dir, events=None, alignment="preserve"):
    return {
        "alignment": alignment,
        "anchor": {"name": "canvas-pivot" if alignment == "preserve" else "foot-center", "x": anchor[0], "y": anchor[1]},
        "asset_id": asset_id,
        "events": list(events or []),
        "playback": {
            "frames": [
                {
                    "cell": [index % sheet["grid"][0], index // sheet["grid"][0]],
                    "duration_ms": duration,
                    "index": index,
                }
                for index, duration in enumerate(durations)
            ],
            "mode": mode,
        },
        "schema_version": SCHEMA_VERSION,
        "sheet": {
            "cell_size": sheet["cell_size"],
            "file": "sheet.png",
            "grid": sheet["grid"],
            "size": sheet["size"],
        },
        "source": {"frames": "frames-normalized", "input": Path(source_dir).name},
        "status": "draft",
    }


def atomic_directory_commit(temporary, target, overwrite):
    target = Path(target)
    if target.exists() and not overwrite:
        raise AssetToolError(f"输出已存在：{target}")
    backup = None
    try:
        if target.exists():
            backup = target.with_name(f".{target.name}.backup")
            if backup.exists():
                shutil.rmtree(backup)
            os.replace(target, backup)
        os.replace(temporary, target)
        if backup:
            shutil.rmtree(backup)
    except Exception:
        if target.exists() and backup:
            shutil.rmtree(target, ignore_errors=True)
        if backup and backup.exists():
            os.replace(backup, target)
        raise


def build_animation(frames_dir, output_dir, asset_id, durations, mode, columns, anchor, overwrite=False, events=None, alignment="preserve"):
    paths = discover_frames(frames_dir)
    validate_durations(durations, len(paths))
    inspected = inspect_frames(paths)
    sizes = {tuple(record["size"]) for record in inspected}
    if len(sizes) != 1:
        raise AssetToolError("构建前的帧尺寸不一致")
    canvas_size = next(iter(sizes))
    target = Path(output_dir)
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(tempfile.mkdtemp(prefix=f".{target.name}.build.", dir=target.parent))
    try:
        normalized_dir = temporary / "frames-normalized"
        normalize_frames(paths, normalized_dir, canvas_size, anchor, False, alignment)
        normalized_paths = discover_frames(normalized_dir)
        sheet = build_sheet(normalized_paths, temporary / "sheet.png", columns, False)
        build_gif(normalized_paths, temporary / "preview.gif", durations, mode, False)
        metadata = animation_metadata(asset_id, sheet, anchor, durations, mode, frames_dir, events, alignment)
        write_json(temporary / "animation.json", metadata)
        write_json(temporary / "inspection.json", {"frames": inspect_frames(normalized_paths)})
        verification = verify_animation(temporary)
        if not verification["valid"]:
            raise AssetToolError("构建结果未通过交叉校验")
        write_json(temporary / "verification.json", verification)
        atomic_directory_commit(temporary, target, overwrite)
        return verification
    except Exception:
        shutil.rmtree(temporary, ignore_errors=True)
        raise


def verify_animation(directory):
    root = Path(directory)
    metadata_path = root / "animation.json"
    if not metadata_path.is_file():
        raise AssetToolError("缺少 animation.json")
    metadata = json.loads(metadata_path.read_text())
    if metadata.get("schema_version") != SCHEMA_VERSION:
        raise AssetToolError("不支持的动画 JSON schema")
    frames = metadata.get("playback", {}).get("frames", [])
    if not frames:
        raise AssetToolError("动画 JSON 没有帧")
    durations = [frame.get("duration_ms") for frame in frames]
    validate_durations(durations, len(frames))
    cell_size = metadata["sheet"]["cell_size"]
    anchor = metadata["anchor"]
    if not 0 <= anchor["x"] < cell_size[0] or not 0 <= anchor["y"] < cell_size[1]:
        raise AssetToolError("动画锚点超出单元格")
    normalized_paths = discover_frames(root / "frames-normalized")
    cells = extract_sheet_cells(
        root / metadata["sheet"]["file"],
        metadata["sheet"]["grid"],
        cell_size,
        len(frames),
    )
    sheet_matches = True
    for path, cell in zip(normalized_paths, cells):
        with Image.open(path) as source:
            if image_hash(source) != image_hash(cell):
                sheet_matches = False
                break
    with Image.open(root / "preview.gif") as gif:
        gif_count = gif.n_frames
        gif_durations = []
        for index in range(gif_count):
            gif.seek(index)
            gif_durations.append(gif.info.get("duration", 0))
    durations_match = len(gif_durations) == len(durations) and all(
        abs(actual - expected) < 10 for actual, expected in zip(gif_durations, durations)
    )
    valid = len(normalized_paths) == len(frames) == gif_count and durations_match and sheet_matches
    return {
        "frame_count": len(frames),
        "gif_durations": gif_durations,
        "gif_durations_match": durations_match,
        "sheet_round_trip": sheet_matches,
        "valid": valid,
    }


def parse_pair(value, name):
    try:
        left, right = value.split(",", 1)
        return int(left), int(right)
    except Exception as error:
        raise AssetToolError(f"{name} 必须使用 x,y 格式") from error


def parse_durations(value):
    try:
        return [int(part) for part in value.split(",")]
    except ValueError as error:
        raise AssetToolError("帧时长必须是逗号分隔的整数") from error


def emit(value):
    print(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True))


def create_parser():
    parser = argparse.ArgumentParser(prog="asset-tool")
    subparsers = parser.add_subparsers(dest="command", required=True)
    inspect_parser = subparsers.add_parser("inspect")
    inspect_parser.add_argument("frames_dir")
    normalize_parser = subparsers.add_parser("normalize")
    normalize_parser.add_argument("frames_dir")
    normalize_parser.add_argument("output_dir")
    normalize_parser.add_argument("--canvas", required=True)
    normalize_parser.add_argument("--anchor", required=True)
    normalize_parser.add_argument("--alignment", choices=["preserve", "foot-center"], default="preserve")
    normalize_parser.add_argument("--overwrite", action="store_true")
    gif_parser = subparsers.add_parser("build-gif")
    gif_parser.add_argument("frames_dir")
    gif_parser.add_argument("output")
    gif_parser.add_argument("--durations", required=True)
    gif_parser.add_argument("--mode", choices=["loop", "once", "hold-last"], default="loop")
    gif_parser.add_argument("--overwrite", action="store_true")
    sheet_parser = subparsers.add_parser("build-sheet")
    sheet_parser.add_argument("frames_dir")
    sheet_parser.add_argument("output")
    sheet_parser.add_argument("--columns", type=int)
    sheet_parser.add_argument("--overwrite", action="store_true")
    animation_parser = subparsers.add_parser("build-animation")
    animation_parser.add_argument("frames_dir")
    animation_parser.add_argument("output_dir")
    animation_parser.add_argument("--asset-id", required=True)
    animation_parser.add_argument("--durations", required=True)
    animation_parser.add_argument("--mode", choices=["loop", "once", "hold-last"], default="loop")
    animation_parser.add_argument("--columns", type=int)
    animation_parser.add_argument("--anchor", required=True)
    animation_parser.add_argument("--alignment", choices=["preserve", "foot-center"], default="preserve")
    animation_parser.add_argument("--overwrite", action="store_true")
    verify_parser = subparsers.add_parser("verify-animation")
    verify_parser.add_argument("animation_dir")
    return parser


def main(argv=None):
    args = create_parser().parse_args(argv)
    if args.command == "inspect":
        emit({"frames": inspect_frames(discover_frames(args.frames_dir))})
    elif args.command == "normalize":
        emit({"frames": normalize_frames(discover_frames(args.frames_dir), args.output_dir, parse_pair(args.canvas, "画布"), parse_pair(args.anchor, "锚点"), args.overwrite, args.alignment)})
    elif args.command == "build-gif":
        emit(build_gif(discover_frames(args.frames_dir), args.output, parse_durations(args.durations), args.mode, args.overwrite))
    elif args.command == "build-sheet":
        emit(build_sheet(discover_frames(args.frames_dir), args.output, args.columns, args.overwrite))
    elif args.command == "build-animation":
        emit(build_animation(args.frames_dir, args.output_dir, args.asset_id, parse_durations(args.durations), args.mode, args.columns, parse_pair(args.anchor, "锚点"), args.overwrite, alignment=args.alignment))
    elif args.command == "verify-animation":
        report = verify_animation(args.animation_dir)
        emit(report)
        if not report["valid"]:
            return 3
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssetToolError as error:
        print(json.dumps({"error": str(error)}, ensure_ascii=False), file=sys.stderr)
        raise SystemExit(3)
