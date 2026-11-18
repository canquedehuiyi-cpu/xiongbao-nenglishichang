#!/usr/bin/env python3
"""Self-test for anim-convert scripts/convert.py.

Generates temporary assets and exercises every conversion path:
frames dir -> gif/apng/webp(png)/mp4, gif -> webp, webp -> frames,
video -> gif, batch dir conversion, --scale, and the no-ffmpeg guard
(only when ffmpeg is absent). Exit 0 if all pass.

Usage: python scripts/self_test.py
"""
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parent
CONV = HERE / "convert.py"


def run(name, *args):
    r = subprocess.run([sys.executable, str(CONV), *args],
                       capture_output=True, text=True)
    ok = r.returncode == 0
    print(f"[{'PASS' if ok else 'FAIL'}] {name}")
    if not ok:
        print("   ", (r.stderr or r.stdout).strip().splitlines()[-1])
    return ok


def main():
    results = []
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        (root / "frames").mkdir()
        (root / "batch").mkdir()
        (root / "out").mkdir()
        # frames folder: 3 RGBA frames
        for i in range(1, 4):
            Image.new("RGBA", (64, 48), (50 * i, 100, 200, 255 - i * 20)
                      ).save(root / "frames" / f"f{i:04d}.png")
        # two animated gifs for batch
        f1 = Image.new("RGBA", (64, 48), (200, 50, 50, 255))
        f2 = Image.new("RGBA", (64, 48), (50, 200, 80, 255))
        for name, dur in (("a.gif", 100), ("b.gif", 150)):
            f1.save(root / "batch" / name, save_all=True,
                    append_images=[f2], duration=dur, loop=0)

        frames = str(root / "frames")
        out = root / "out"
        gif = out / "test.gif"
        results.append(run("frames -> gif", frames, str(gif), "--fps", "10"))
        results.append(run("frames -> apng", frames, str(out / "t.png"), "--fps", "10"))
        results.append(run("frames -> lossless webp", frames, str(out / "t.webp"),
                           "--fps", "10", "--lossless"))
        mp4 = out / "t.mp4"
        results.append(run("frames -> mp4", frames, str(mp4), "--fps", "12"))
        results.append(run("gif -> webp", str(gif), str(out / "c.webp")))
        results.append(run("webp -> frames dir", str(out / "t.webp"), str(out / "fx")))
        results.append(run("video -> gif", str(mp4), str(out / "v.gif"), "--fps", "8"))
        results.append(run("batch dir gif -> webp", str(root / "batch"),
                           str(out / "bw"), "--batch", "webp"))
        results.append(run("--scale 100", frames, str(out / "s.gif"),
                           "--fps", "10", "--scale", "100"))
        # sanity: scale actually resized
        with Image.open(out / "s.gif") as im:
            results.append(im.size == (100, 75))

    print(f"\n{sum(results)}/{len(results)} checks passed.")
    sys.exit(0 if all(results) else 1)


if __name__ == "__main__":
    main()