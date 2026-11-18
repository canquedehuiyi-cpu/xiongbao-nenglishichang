#!/usr/bin/env python3
"""Animation format converter.

Supports interconversion between:
  - frames folder (a directory of image files, sorted naturally)
  - .gif (animated)
  - .webp (animated)
  - .png (APNG, animated)

Usage:
  python convert.py <input> <output> [--fps N] [--duration MS] [--loop N]
                    [--pattern GLOB] [--quality 0-100] [--lossless]

If <input> is a directory, it is treated as a frames folder.
If <input> is a file, its extension decides the source format.

If <output> is a directory (existing or ending with / or \\), frames are
extracted into it as <name>_0001.png, <name>_0002.png, ...
Otherwise the output extension decides the target format.
"""
import argparse
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image, ImageSequence


SUPPORTED_READ = {".gif", ".webp", ".png", ".apng", ".mp4", ".webm", ".mov"}
VIDEO_EXTS = {".mp4", ".webm", ".mov"}
FRAME_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tga"}


def natural_key(s: str):
    return [int(t) if t.isdigit() else t.lower() for t in re.split(r"(\d+)", s)]


def err(msg: str):
    print(f"[ERROR] {msg}", file=sys.stderr)


def ok(msg: str):
    print(f"[OK] {msg}")


def run_ffmpeg(cmd):
    """Run ffmpeg once; exit with a clear message on missing binary or failure."""
    if shutil.which("ffmpeg") is None:
        err("ffmpeg not found in PATH. Install ffmpeg to use video input/output.")
        sys.exit(2)
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        tail = [l for l in r.stderr.splitlines() if l.strip()][-2:]
        err(f"ffmpeg failed: {' | '.join(tail)}")
        sys.exit(2)


def load_frames_from_video(path: Path, fps: float):
    """Decode a video into RGBA frames via ffmpeg -> PNG sequence."""
    if not fps or fps <= 0:
        fps = 24
    with tempfile.TemporaryDirectory() as td:
        pat = str(Path(td) / "f_%04d.png")
        run_ffmpeg(["ffmpeg", "-y", "-i", str(path), "-vf", f"fps={fps}", pat])
        files = sorted(Path(td).glob("f_*.png"), key=lambda p: natural_key(p.name))
        if not files:
            err(f"No frames decoded from '{path}'.")
            sys.exit(2)
        frames = [_load_rgba(f) for f in files]
    n = len(frames)
    ms = int(round(1000.0 / fps))
    print(f"[INFO] Decoded {n} frame(s) from {path.suffix.upper()}.")
    return frames, [ms] * n


def load_frames_from_folder(folder: Path, pattern: str):
    files = []
    for p in folder.iterdir():
        if p.is_file() and p.suffix.lower() in FRAME_EXTS:
            if pattern == "*" or p.match(pattern):
                files.append(p)
    if not files:
        err(f"No image files found in '{folder}' matching '{pattern}'.")
        sys.exit(2)
    files.sort(key=lambda p: natural_key(p.name))
    frames = [_load_rgba(f) for f in files]
    print(f"[INFO] Loaded {len(frames)} frame(s).")
    return frames, None


def _load_rgba(path: Path) -> Image.Image:
    with Image.open(path) as im:
        return im.convert("RGBA")


def load_frames_from_file(path: Path):
    im = Image.open(path)
    frames = []
    durations = []
    for frame in ImageSequence.Iterator(im):
        # copy to detach from the underlying lazy image
        f = frame.convert("RGBA").copy()
        frames.append(f)
        d = frame.info.get("duration", 0)
        durations.append(d if isinstance(d, (int, float)) else 0)
    im.close()
    n = len(frames)
    if n == 0:
        err(f"No frames decoded from '{path}'.")
        sys.exit(2)
    print(f"[INFO] Decoded {n} frame(s) from {path.suffix.upper()}.")
    return frames, durations


def deduce_duration_ms(durations, fps, total_frames):
    # Prefer source per-frame durations when available and non-zero.
    if durations and any(d and d > 0 for d in durations):
        # Pillow WebP/GIF expects per-frame duration in ms.
        return [int(round(d)) for d in durations]
    if not fps or fps <= 0:
        fps = 24
    ms = int(round(1000.0 / fps))
    return [ms] * total_frames


def to_p_mode(frame: Image.Image) -> Image.Image:
    """Quantize to palette mode for compact GIF output."""
    if frame.mode == "P":
        return frame
    rgba = frame.convert("RGBA")
    # RGBA requires Octree (method=2) in Pillow; mediancut (1) is RGB-only.
    return rgba.quantize(colors=256, method=Image.Quantize.FASTOCTREE).convert("P")


def write_gif(path: Path, frames, durations, loop):
    if len(frames) == 1:
        frames[0].save(path, format="GIF", save_all=True, loop=loop,
                       duration=durations[0])
        return
    # Build P-mode copies for consistent palette handling.
    p_frames = [to_p_mode(f) for f in frames]
    p_frames[0].save(
        path, format="GIF", save_all=True, append_images=p_frames[1:],
        loop=loop, duration=durations, disposal=2,
    )


def write_webp(path: Path, frames, durations, quality, lossless, loop):
    kwargs = dict(
        format="WEBP", save_all=True, append_images=frames[1:],
        loop=loop, duration=durations, quality=quality, method=6,
    )
    if lossless:
        kwargs["lossless"] = True
        kwargs.pop("quality", None)
    frames[0].save(path, **kwargs)


def write_apng(path: Path, frames, durations, loop):
    frames[0].save(
        path, format="PNG", save_all=True, append_images=frames[1:],
        loop=loop, duration=durations, disposal=2,
    )


def write_frames_folder(folder: Path, frames, stem):
    folder.mkdir(parents=True, exist_ok=True)
    width = max(4, len(str(len(frames))))
    for i, f in enumerate(frames, 1):
        out = folder / f"{stem}_{i:0{width}d}.png"
        f.convert("RGBA").save(out, format="PNG")
    print(f"[INFO] Wrote {len(frames)} frame(s) to {folder}.")


def write_video(path: Path, frames, fps, kind):
    """Encode frames into a video via ffmpeg from a temp PNG sequence."""
    if not fps or fps <= 0:
        fps = 24
    codec = {"mp4": "libx264", "webm": "libvpx-vp9", "mov": "libx264"}[kind]
    with tempfile.TemporaryDirectory() as td:
        pngs = Path(td) / "f_%04d.png"
        for i, f in enumerate(frames, 1):
            f.convert("RGB").save(Path(td) / f"f_{i:04d}.png", format="PNG")
        cmd = ["ffmpeg", "-y", "-framerate", str(fps), "-i", str(pngs),
               "-vf", "scale=trunc(iw/2)*2:trunc(ih/2)*2", "-pix_fmt", "yuv420p"]
        if kind == "webm":
            cmd += ["-c:v", "libvpx-vp9", "-crf", "30", "-b:v", "0"]
        else:
            cmd += ["-c:v", "libx264", "-crf", "23", "-preset", "medium"]
        cmd.append(str(path))
        run_ffmpeg(cmd)


def detect_output_kind(out_arg: str):
    p = Path(out_arg)
    # Treat as frames folder if: no suffix, or ends with separator, or exists as dir.
    if out_arg.endswith(("/", "\\")) or (p.exists() and p.is_dir()) or p.suffix == "":
        return "frames", p
    ext = p.suffix.lower()
    if ext in {".gif"}:
        return "gif", p
    if ext in {".webp"}:
        return "webp", p
    if ext in {".png", ".apng"}:
        return "apng", p
    if ext in {".mp4", ".webm", ".mov"}:
        return ext.lstrip("."), p
    err(f"Unsupported output extension '{ext}'. Use .gif/.webp/.png/.mp4/.webm/.mov or a folder.")
    sys.exit(2)


def write_any(out_path: Path, frames, durations, kind, loop, quality, lossless, fps):
    """Dispatch frames to any output kind (gif/webp/apng/mp4/webm/mov)."""
    if kind == "gif":
        write_gif(out_path, frames, durations, loop)
    elif kind == "webp":
        write_webp(out_path, frames, durations, quality, lossless, loop)
    elif kind == "apng":
        write_apng(out_path, frames, durations, loop)
    else:
        write_video(out_path, frames, fps, kind)


def batch_convert(in_dir: Path, out_dir: Path, ext: str, args):
    """Convert every convertible file in in_dir to target ext in out_dir."""
    out_dir.mkdir(parents=True, exist_ok=True)
    files = sorted(
        (p for p in in_dir.iterdir() if p.is_file()
         and (p.suffix.lower() in SUPPORTED_READ or p.suffix.lower() in FRAME_EXTS)),
        key=lambda p: natural_key(p.name))
    if not files:
        err(f"No convertible files found in '{in_dir}'.")
        sys.exit(2)
    ok_cnt = skip_cnt = 0
    for p in files:
        try:
            if p.suffix.lower() in VIDEO_EXTS:
                frames, _ = load_frames_from_video(p, args.fps)
                durations = [int(round(1000.0 / (args.fps or 24)))] * len(frames)
            else:
                frames, durations = load_frames_from_file(p)
            if args.duration and args.duration > 0:
                durations = [int(round(args.duration))] * len(frames)
            frames = apply_scale(frames, args.scale)
            write_any(out_dir / f"{p.stem}.{ext}", frames, durations, ext,
                      args.loop, args.quality, args.lossless, args.fps)
            ok_cnt += 1
            print(f"[OK] BATCH {p.name} -> {p.stem}.{ext}")
        except (SystemExit, Exception):
            skip_cnt += 1
            print(f"[SKIP] {p.name}")
    print(f"[INFO] Batch done: {ok_cnt} ok, {skip_cnt} skipped.")


def parse_scale(s):
    """'480' (width) / '480x360' / 'x360' (height) -> (w|None, h|None)."""
    if not s:
        return None
    parts = s.strip().lower().split("x")
    if len(parts) == 1 and parts[0].isdigit():
        return (int(parts[0]), None)
    if len(parts) == 2 and all(p == "" or p.isdigit() for p in parts) and any(parts):
        w = int(parts[0]) if parts[0] else None
        h = int(parts[1]) if parts[1] else None
        return (w, h)
    err(f"Invalid --scale '{s}'. Use e.g. 480, 480x360 or x360.")
    sys.exit(2)


def apply_scale(frames, scale):
    if not scale:
        return frames
    w, h = scale
    out = []
    for f in frames:
        if w and h:
            size = (w, h)
        elif w:
            size = (w, max(1, round(f.height * w / f.width)))
        else:
            size = (max(1, round(f.width * h / f.height)), h)
        out.append(f.resize(size, Image.LANCZOS))
    return out


def main():
    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument("input")
    ap.add_argument("output")
    ap.add_argument("--fps", type=float, default=24.0)
    ap.add_argument("--duration", type=float, default=None,
                    help="Override per-frame duration in ms (overrides --fps).")
    ap.add_argument("--loop", type=int, default=0,
                    help="Loop count (0 = infinite). Passed through to GIF/WebP/APNG encoder.")
    ap.add_argument("--pattern", default="*",
                    help="Glob for frames folder input, e.g. '*.png'.")
    ap.add_argument("--quality", type=int, default=80,
                    help="WebP quality 0-100 (ignored if --lossless).")
    ap.add_argument("--lossless", action="store_true", help="WebP lossless.")
    ap.add_argument("--batch", default=None, metavar="EXT",
                    help="Batch mode: input is a folder, output is a folder; "
                         "convert every file to EXT (gif/webp/apng/mp4/webm/mov).")
    ap.add_argument("--scale", default=None, metavar="WxH",
                    help="Scale output frames, e.g. 480 (width) / 480x360 / x360.")
    args = ap.parse_args()

    in_path = Path(args.input)
    if not in_path.exists():
        err(f"Input not found: {in_path}")
        sys.exit(2)

    args.scale = parse_scale(args.scale)

    if args.batch:
        if not in_path.is_dir():
            err("--batch requires a folder as input.")
            sys.exit(2)
        ext = args.batch.lower().lstrip(".")
        if ext not in {"gif", "webp", "apng", "mp4", "webm", "mov"}:
            err(f"Unsupported batch target '{ext}'.")
            sys.exit(2)
        batch_convert(in_path, Path(args.output), ext, args)
        return

    # Load source frames.
    if in_path.is_dir():
        frames, src_durations = load_frames_from_folder(in_path, args.pattern)
    else:
        ext = in_path.suffix.lower()
        if ext not in SUPPORTED_READ:
            err(f"Unsupported input extension '{ext}'. Supported: {sorted(SUPPORTED_READ)}")
            sys.exit(2)
        if ext in VIDEO_EXTS:
            frames, src_durations = load_frames_from_video(in_path, args.fps)
        else:
            frames, src_durations = load_frames_from_file(in_path)

    frames = apply_scale(frames, args.scale)

    # Decide durations.
    if args.duration is not None and args.duration > 0:
        durations = [int(round(args.duration))] * len(frames)
    else:
        durations = deduce_duration_ms(src_durations, args.fps, len(frames))

    # Write output.
    out_kind, out_path = detect_output_kind(args.output)
    if out_kind == "frames":
        stem = in_path.stem if in_path.is_file() else in_path.name
        write_frames_folder(out_path, frames, stem)
    else:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        write_any(out_path, frames, durations, out_kind,
                  args.loop, args.quality, args.lossless, args.fps)
        if out_kind in {"mp4", "webm", "mov"}:
            ok(f"Wrote {out_path}  ({len(frames)} frames @ {args.fps}fps, {out_kind})")
        elif out_kind == "gif":
            ok(f"Wrote GIF: {out_path}  ({len(frames)} frames, ~{durations[0]}ms/frm, loop={args.loop})")
        elif out_kind == "webp":
            tag = "lossless" if args.lossless else f"q{args.quality}"
            ok(f"Wrote WebP: {out_path}  ({len(frames)} frames, {tag}, loop={args.loop})")
        elif out_kind == "apng":
            ok(f"Wrote APNG: {out_path}  ({len(frames)} frames, ~{durations[0]}ms/frm, loop={args.loop})")


if __name__ == "__main__":
    main()
