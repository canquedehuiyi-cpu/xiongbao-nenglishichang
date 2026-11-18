import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from PIL import Image, ImageDraw


SCRIPT = Path(__file__).parents[1] / "asset_tool.py"


def load_module():
    spec = importlib.util.spec_from_file_location("asset_tool", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def make_frame(path, size=(24, 20), box=(4, 3, 14, 17), color=(220, 40, 80, 255)):
    image = Image.new("RGBA", size, (0, 0, 0, 0))
    ImageDraw.Draw(image).rectangle(box, fill=color)
    image.save(path)


class AssetToolTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.frames = self.root / "frames"
        self.frames.mkdir()
        make_frame(self.frames / "frame-1.png", box=(1, 2, 8, 18))
        make_frame(self.frames / "frame-2.png", box=(4, 2, 12, 18))
        make_frame(self.frames / "frame-10.png", box=(8, 2, 18, 18))

    def tearDown(self):
        self.temp.cleanup()

    def test_discovers_frames_in_natural_order_and_inspects_alpha(self):
        tool = load_module()
        paths = tool.discover_frames(self.frames)
        self.assertEqual([path.name for path in paths], ["frame-1.png", "frame-2.png", "frame-10.png"])
        result = tool.inspect_frames(paths)
        self.assertEqual(result[0]["size"], [24, 20])
        self.assertTrue(result[0]["has_alpha"])
        self.assertEqual(result[0]["content_bbox"], [1, 2, 9, 19])

    def test_rejects_duplicate_frame_numbers(self):
        make_frame(self.frames / "other-2.png")
        tool = load_module()
        with self.assertRaisesRegex(tool.AssetToolError, "重复帧号"):
            tool.discover_frames(self.frames)

    def test_normalize_uses_shared_canvas_without_stretching(self):
        tool = load_module()
        output = self.root / "normalized"
        records = tool.normalize_frames(
            tool.discover_frames(self.frames), output, (32, 28), (16, 24), overwrite=False
        )
        self.assertEqual(len(records), 3)
        with Image.open(output / "frame-000.png") as image:
            self.assertEqual(image.size, (32, 28))
            self.assertEqual(image.getbbox(), (12, 8, 20, 25))

    def test_sheet_round_trip_matches_source_pixels(self):
        tool = load_module()
        output = self.root / "sheet.png"
        paths = tool.discover_frames(self.frames)
        layout = tool.build_sheet(paths, output, columns=2, overwrite=False)
        self.assertEqual(layout["grid"], [2, 2])
        cells = tool.extract_sheet_cells(output, layout["grid"], layout["cell_size"], len(paths))
        for path, cell in zip(paths, cells):
            with Image.open(path) as source:
                self.assertEqual(source.convert("RGBA").tobytes(), cell.tobytes())

    def test_build_gif_preserves_variable_durations(self):
        tool = load_module()
        output = self.root / "preview.gif"
        tool.build_gif(tool.discover_frames(self.frames), output, [80, 120, 200], "loop", False)
        with Image.open(output) as image:
            durations = []
            for index in range(image.n_frames):
                image.seek(index)
                durations.append(image.info["duration"])
        self.assertEqual(durations, [80, 120, 200])

    def test_build_gif_rejects_invalid_duration(self):
        tool = load_module()
        with self.assertRaisesRegex(tool.AssetToolError, "帧时长"):
            tool.build_gif(tool.discover_frames(self.frames), self.root / "bad.gif", [80, 0, 100], "loop", False)

    def test_verification_accepts_gif_centisecond_quantization(self):
        tool = load_module()
        output = self.root / "quantized-animation"
        tool.build_animation(
            self.frames, output, "hero-run", [84, 84, 84], "loop", 2, (12, 18), False
        )
        report = tool.verify_animation(output)
        self.assertTrue(report["valid"])
        self.assertEqual(report["gif_durations"], [80, 80, 80])

    def test_build_animation_is_reproducible_and_verifiable(self):
        tool = load_module()
        first = self.root / "animation-a"
        second = self.root / "animation-b"
        kwargs = {
            "frames_dir": self.frames,
            "asset_id": "hero-run",
            "durations": [80, 120, 200],
            "mode": "loop",
            "columns": 2,
            "anchor": (12, 18),
            "overwrite": False,
        }
        tool.build_animation(output_dir=first, **kwargs)
        tool.build_animation(output_dir=second, **kwargs)
        self.assertEqual((first / "animation.json").read_bytes(), (second / "animation.json").read_bytes())
        self.assertEqual((first / "sheet.png").read_bytes(), (second / "sheet.png").read_bytes())
        report = tool.verify_animation(first)
        self.assertTrue(report["valid"])
        metadata = json.loads((first / "animation.json").read_text())
        self.assertEqual(metadata["status"], "draft")
        self.assertEqual(metadata["playback"]["frames"][1]["duration_ms"], 120)

    def test_failed_build_does_not_replace_existing_output(self):
        tool = load_module()
        output = self.root / "animation"
        output.mkdir()
        marker = output / "existing.txt"
        marker.write_text("keep")
        with self.assertRaises(tool.AssetToolError):
            tool.build_animation(
                self.frames, output, "hero-run", [100], "loop", 2, (12, 18), True
            )
        self.assertEqual(marker.read_text(), "keep")
        self.assertEqual(sorted(path.name for path in output.iterdir()), ["existing.txt"])

    def test_default_build_preserves_jump_and_horizontal_trajectory(self):
        tool = load_module()
        boxes = [(2, 10, 7, 18), (7, 2, 12, 10), (12, 9, 17, 17)]
        paths = tool.discover_frames(self.frames)
        for path, box in zip(paths, boxes):
            make_frame(path, box=box)
        output = self.root / "jump"
        tool.build_animation(self.frames, output, "jump", [100]*3, "once", 3, (12, 18))
        for index, path in enumerate(paths):
            with Image.open(path) as source, Image.open(output / "frames-normalized" / f"frame-{index:03d}.png") as actual:
                self.assertEqual(source.tobytes(), actual.tobytes())
                self.assertEqual(source.getbbox(), actual.getbbox())
        metadata = json.loads((output / "animation.json").read_text())
        self.assertEqual(metadata["alignment"], "preserve")
        self.assertEqual(metadata["anchor"]["name"], "canvas-pivot")

    def test_explicit_foot_alignment_remains_available(self):
        tool = load_module()
        output = self.root / "aligned"
        tool.build_animation(self.frames, output, "idle", [80, 120, 200], "loop", 2, (12, 18), alignment="foot-center")
        for path in tool.discover_frames(output / "frames-normalized"):
            with Image.open(path) as frame:
                bbox = frame.getbbox()
                self.assertEqual((bbox[0] + bbox[2]) // 2, 12)
                self.assertEqual(bbox[3] - 1, 18)
        metadata = json.loads((output / "animation.json").read_text())
        self.assertEqual(metadata["alignment"], "foot-center")

    def test_invalid_alignment_does_not_write_delivery(self):
        tool = load_module()
        output = self.root / "invalid-alignment"
        with self.assertRaisesRegex(tool.AssetToolError, "对齐模式"):
            tool.build_animation(self.frames, output, "idle", [100]*3, "loop", 2, (12, 18), alignment="unknown")
        self.assertFalse(output.exists())

    def test_cli_build_and_verify(self):
        output = self.root / "cli-animation"
        build = subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "build-animation",
                str(self.frames),
                str(output),
                "--asset-id",
                "hero-run",
                "--durations",
                "80,120,200",
                "--columns",
                "2",
                "--anchor",
                "12,18",
            ],
            capture_output=True,
            text=True,
        )
        self.assertEqual(build.returncode, 0, build.stderr)
        self.assertEqual(json.loads((output / "animation.json").read_text())["alignment"], "preserve")
        with Image.open(self.frames / "frame-1.png") as source, Image.open(output / "frames-normalized/frame-000.png") as actual:
            self.assertEqual(source.tobytes(), actual.tobytes())
        verify = subprocess.run(
            [sys.executable, str(SCRIPT), "verify-animation", str(output)],
            capture_output=True,
            text=True,
        )
        self.assertEqual(verify.returncode, 0, verify.stderr)
        self.assertTrue(json.loads(verify.stdout)["valid"])


if __name__ == "__main__":
    unittest.main()
