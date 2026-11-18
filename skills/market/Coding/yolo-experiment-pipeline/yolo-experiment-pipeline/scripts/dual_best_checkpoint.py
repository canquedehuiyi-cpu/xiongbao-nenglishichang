#!/usr/bin/env python3
"""Save an extra Ultralytics best checkpoint selected by mAP50.

The default Ultralytics best.pt is selected by fitness, which for detection is
mAP50-95. This callback copies the official last.pt written for the current
epoch whenever mAP50 reaches a new maximum. Copying preserves the official
checkpoint format, so the result loads with YOLO(path).

Do not build a custom torch.save dict with trainer/EMA objects; those files are
not guaranteed to load with Ultralytics.

When resuming, back up or move the existing best_mAP50.pt/json first; a new
process starts its tracker at -inf and can overwrite a better checkpoint.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path


def _metric(trainer, keys, box_attr):
    metrics = getattr(trainer, "metrics", None)
    if isinstance(metrics, dict):
        for key in keys:
            try:
                value = float(metrics[key])
            except (KeyError, TypeError, ValueError):
                continue
            if value == value:  # reject NaN
                return value

    validator = getattr(trainer, "validator", None)
    box = getattr(getattr(validator, "metrics", None), "box", None)
    try:
        value = float(getattr(box, box_attr))
    except (AttributeError, TypeError, ValueError):
        return None
    return value if value == value else None


def _map50(trainer):
    return _metric(trainer, ("metrics/mAP50(B)", "mAP50", "map50"), "map50")


def _map50_95(trainer):
    return _metric(trainer, ("metrics/mAP50-95(B)", "mAP50-95", "map5095"), "map")


class DualBestCheckpointSaver:
    """Copy Ultralytics last.pt to best_mAP50.pt on a new best mAP50."""

    def __init__(self, filename="best_mAP50.pt", metadata_filename="best_mAP50.json", verbose=True):
        self.filename = filename
        self.metadata_filename = metadata_filename
        self.verbose = verbose
        self.best_map50 = float("-inf")
        self.best_map50_95 = None
        self.best_epoch = None
        self.best_path = None

    def __call__(self, trainer):
        current = _map50(trainer)
        if current is None or current <= self.best_map50:
            return

        save_dir = Path(getattr(trainer, "save_dir", ""))
        weights_dir = save_dir / "weights"
        last = Path(getattr(trainer, "last", weights_dir / "last.pt"))
        if not last.is_file():
            fallback = weights_dir / "last.pt"
            if not fallback.is_file():
                raise FileNotFoundError(f"last.pt not found after save_model: {last} / {fallback}")
            last = fallback

        weights_dir.mkdir(parents=True, exist_ok=True)
        target = weights_dir / self.filename
        shutil.copy2(last, target)
        if target.stat().st_size == 0:
            raise RuntimeError(f"copied checkpoint is empty: {target}")

        self.best_map50 = current
        self.best_map50_95 = _map50_95(trainer)
        self.best_epoch = int(getattr(trainer, "epoch", -1)) + 1
        self.best_path = target

        metadata = {
            "selection_metric": "mAP50",
            "best_map50": current,
            "map50_95_at_best_map50": self.best_map50_95,
            "best_epoch": self.best_epoch,
            "source_checkpoint": str(last),
            "saved_checkpoint": str(target),
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        metadata_path = weights_dir / self.metadata_filename
        metadata_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")

        if self.verbose:
            print(
                f"[dual-best] epoch {self.best_epoch}: mAP50={current:.6f} -> {target} "
                f"(mAP50-95={self.best_map50_95})"
            )

    def attach(self, model):
        model.add_callback("on_model_save", self)
        return self


def attach_dual_best_checkpoint(model, filename="best_mAP50.pt", verbose=True):
    """Attach the dual-best callback and return the saver instance."""
    return DualBestCheckpointSaver(filename=filename, verbose=verbose).attach(model)


def verify_checkpoint(path):
    """Load a checkpoint with Ultralytics and print its metadata."""
    from ultralytics import YOLO

    model = YOLO(str(path))
    ckpt = getattr(model, "ckpt", None) or {}
    payload = {
        "path": str(Path(path).resolve()),
        "epoch": ckpt.get("epoch"),
        "best_fitness": ckpt.get("best_fitness"),
        "keys": sorted(ckpt.keys()),
        "note": (
            "epoch=-1 and best_fitness=null are normal for stripped final checkpoints; "
            "validate metrics with model.val and do not resume from a stripped best.pt."
        ),
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return payload


def _selftest():
    with tempfile.TemporaryDirectory() as tmp:
        run_dir = Path(tmp) / "run"
        weights_dir = run_dir / "weights"
        weights_dir.mkdir(parents=True)
        last = weights_dir / "last.pt"
        payload = b"official-checkpoint-bytes"
        last.write_bytes(payload)

        class FakeTrainer:
            pass

        saver = DualBestCheckpointSaver(verbose=False)

        trainer = FakeTrainer()
        trainer.save_dir = run_dir
        trainer.last = last
        trainer.epoch = 41
        trainer.metrics = {"metrics/mAP50(B)": 0.50, "metrics/mAP50-95(B)": 0.30}
        saver(trainer)

        copied = weights_dir / "best_mAP50.pt"
        assert copied.read_bytes() == payload, "checkpoint was not copied verbatim"
        assert saver.best_epoch == 42, saver.best_epoch
        meta = json.loads((weights_dir / "best_mAP50.json").read_text(encoding="utf-8"))
        assert meta["best_map50"] == 0.5

        # A worse mAP50 must not overwrite the saved checkpoint.
        trainer.epoch = 42
        trainer.metrics = {"metrics/mAP50(B)": 0.49, "metrics/mAP50-95(B)": 0.99}
        saver(trainer)
        assert copied.read_bytes() == payload
        assert saver.best_epoch == 42

        # A new best must refresh it with the current official last.pt.
        last.write_bytes(b"new-checkpoint-bytes")
        trainer.epoch = 43
        trainer.metrics = {"metrics/mAP50(B)": 0.60, "metrics/mAP50-95(B)": 0.40}
        saver(trainer)
        assert copied.read_bytes() == b"new-checkpoint-bytes"
        assert saver.best_epoch == 44

    print("selftest OK")


def main():
    parser = argparse.ArgumentParser(description="Dual best checkpoint helper for Ultralytics YOLO")
    parser.add_argument("--verify", type=Path, help="Load a checkpoint with YOLO() and print metadata")
    parser.add_argument("--selftest", action="store_true", help="Test the copy logic against a fake trainer")
    args = parser.parse_args()

    if args.verify:
        verify_checkpoint(args.verify)
        return 0
    if args.selftest:
        _selftest()
        return 0
    parser.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
