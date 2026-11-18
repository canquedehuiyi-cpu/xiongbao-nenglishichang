#!/usr/bin/env python3
"""Validate a YOLO detector on labeled data or on unlabeled images.

Labeled mode wraps Ultralytics model.val and reports overall/per-class metrics.
Images mode samples unlabeled images, handles corrupted files, and reports
detection statistics plus optional visualizations. Images mode is qualitative;
it does not compute mAP because there are no ground-truth labels.
"""

from __future__ import annotations

import argparse
import json
import random
import statistics
import sys
import time
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff", ".webp"}


def _collect_images(source, exclude=None):
    source = Path(source).resolve()
    exclude = Path(exclude).resolve() if exclude else None
    images = []
    for path in source.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in IMAGE_EXTENSIONS:
            continue
        if exclude and (path == exclude or exclude in path.parents):
            continue
        images.append(path)
    return sorted(images)


def _sample(images, sample_size, seed):
    if sample_size <= 0 or sample_size >= len(images):
        return list(images)
    return random.Random(seed).sample(images, sample_size)


def _class_name(names, index):
    if isinstance(names, dict):
        return str(names.get(index, index))
    try:
        return str(names[index])
    except (IndexError, KeyError, TypeError):
        return str(index)


def _jsonable(value):
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    try:
        return float(value)
    except (TypeError, ValueError):
        return str(value)


def _write_json(path, payload):
    if path:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        Path(path).write_text(json.dumps(_jsonable(payload), ensure_ascii=False, indent=2), encoding="utf-8")


def _write_markdown(path, lines):
    if path:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        Path(path).write_text("\n".join(lines) + "\n", encoding="utf-8")


def _fmt(value, digits=4):
    return "-" if value is None else f"{value:.{digits}f}"


def _pct(value):
    return "-" if value is None else f"{value:.1f}%"


def run_labeled(args):
    from ultralytics import YOLO

    model = YOLO(str(args.model))
    kwargs = {
        "data": str(args.data),
        "split": args.split,
        "imgsz": args.imgsz,
        "batch": args.batch,
        "device": args.device,
        "plots": args.plots,
        "verbose": args.verbose,
    }
    if args.conf is not None:
        kwargs["conf"] = args.conf
    if args.iou is not None:
        kwargs["iou"] = args.iou

    metrics = model.val(**kwargs)

    names = getattr(metrics, "names", {})
    if isinstance(names, (list, tuple)):
        names = {index: name for index, name in enumerate(names)}

    per_class = []
    for index, name in sorted(names.items()):
        try:
            precision, recall, ap50, ap = metrics.box.class_result(index)
        except Exception:
            continue
        per_class.append(
            {
                "class_id": index,
                "class": str(name),
                "precision": float(precision),
                "recall": float(recall),
                "mAP50": float(ap50),
                "mAP50_95": float(ap),
            }
        )

    payload = {
        "mode": "labeled",
        "model": str(Path(args.model).resolve()),
        "data": str(Path(args.data).resolve()),
        "split": args.split,
        "imgsz": args.imgsz,
        "batch": args.batch,
        "device": str(args.device),
        "conf_override": args.conf,
        "iou_override": args.iou,
        "overall": {
            "precision": float(metrics.box.mp),
            "recall": float(metrics.box.mr),
            "mAP50": float(metrics.box.map50),
            "mAP50_95": float(metrics.box.map),
        },
        "per_class": per_class,
        "speed_ms_per_image": _jsonable(getattr(metrics, "speed", {})),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    overall = payload["overall"]
    print("Labeled validation")
    print(f"  model: {payload['model']}")
    print(f"  data: {payload['data']} (split={args.split})")
    print(
        f"  mAP50={_fmt(overall['mAP50'])} mAP50-95={_fmt(overall['mAP50_95'])} "
        f"P={_fmt(overall['precision'])} R={_fmt(overall['recall'])}"
    )
    speed = payload["speed_ms_per_image"] or {}
    inference_ms = speed.get("inference") if isinstance(speed, dict) else None
    inference_text = (
        f"{inference_ms:.2f} ms/image ({1000.0 / inference_ms:.1f} FPS)"
        if inference_ms
        else "-"
    )
    print(f"  inference: {inference_text}")
    for row in per_class:
        print(
            f"  {row['class']}: mAP50={_fmt(row['mAP50'])} "
            f"mAP50-95={_fmt(row['mAP50_95'])} P={_fmt(row['precision'])} R={_fmt(row['recall'])}"
        )

    _write_json(args.output, payload)

    lines = [
        "# YOLO labeled validation",
        "",
        f"- model: `{payload['model']}`",
        f"- data: `{payload['data']}` (split `{args.split}`)",
        f"- imgsz: {args.imgsz}, batch: {args.batch}, device: {args.device}",
        "",
        "| Metric | Value |",
        "|--------|-------|",
        f"| mAP50 | {_fmt(overall['mAP50'])} |",
        f"| mAP50-95 | {_fmt(overall['mAP50_95'])} |",
        f"| Precision | {_fmt(overall['precision'])} |",
        f"| Recall | {_fmt(overall['recall'])} |",
        f"| Inference | {inference_text} |",
        "",
        "| Class | Precision | Recall | mAP50 | mAP50-95 |",
        "|-------|-----------|--------|-------|----------|",
    ]
    for row in per_class:
        lines.append(
            f"| {row['class']} | {_fmt(row['precision'])} | {_fmt(row['recall'])} | "
            f"{_fmt(row['mAP50'])} | {_fmt(row['mAP50_95'])} |"
        )
    _write_markdown(args.markdown, lines)
    return 0


def run_images(args):
    from ultralytics import YOLO
    import cv2

    source = Path(args.source).resolve()
    if not source.is_dir():
        raise NotADirectoryError(f"source is not a directory: {source}")

    output_dir = (
        Path(args.output_dir).resolve()
        if args.output_dir
        else source.parent / f"{source.name}_validation_results"
    )
    vis_dir = output_dir / "visualizations"
    if args.save_visuals:
        vis_dir.mkdir(parents=True, exist_ok=True)

    images = _collect_images(source, exclude=output_dir)
    if not images:
        raise ValueError(f"no images found under {source}")
    sampled = _sample(images, args.sample, args.seed)

    model = YOLO(str(args.model))
    counters = Counter()
    class_counts = Counter()
    confidence_scores = []
    skipped = []
    per_folder = defaultdict(
        lambda: {
            "sampled": 0,
            "processed": 0,
            "images_with_detections": 0,
            "boxes": 0,
            "classes": Counter(),
        }
    )

    started = time.time()
    for index, image_path in enumerate(sampled, 1):
        stats = per_folder[image_path.parent.name]
        stats["sampled"] += 1
        try:
            results = model.predict(
                source=str(image_path),
                conf=args.conf,
                iou=args.iou,
                imgsz=args.imgsz,
                device=args.device,
                save=False,
                verbose=False,
            )
            if not results:
                raise RuntimeError("no prediction result (unreadable image?)")
            result = results[0]
            boxes = result.boxes
            count = 0 if boxes is None else len(boxes)

            counters["processed_images"] += 1
            counters["total_boxes"] += count
            stats["processed"] += 1
            stats["boxes"] += count

            if count:
                counters["images_with_detections"] += 1
                stats["images_with_detections"] += 1
                for box in boxes:
                    class_id = int(box.cls[0])
                    class_name = _class_name(result.names, class_id)
                    confidence = float(box.conf[0])
                    class_counts[class_name] += 1
                    stats["classes"][class_name] += 1
                    confidence_scores.append(confidence)

            if args.save_visuals:
                plotted = result.plot()
                output_path = vis_dir / f"{image_path.stem}_pred.jpg"
                if not cv2.imwrite(str(output_path), plotted):
                    raise RuntimeError(f"failed to write visualization: {output_path}")
        except Exception as exc:
            skipped.append(
                {"image": str(image_path), "error": f"{type(exc).__name__}: {exc}"}
            )

        if args.progress_every and index % args.progress_every == 0:
            print(f"  processed {index}/{len(sampled)}")

    processed = counters["processed_images"]
    if processed == 0:
        raise RuntimeError("no image was processed successfully")

    scores = confidence_scores
    high = sum(value >= 0.7 for value in scores)
    mid = sum(0.5 <= value < 0.7 for value in scores)
    low = sum(value < 0.5 for value in scores)
    confidence = {
        "count": len(scores),
        "mean": statistics.mean(scores) if scores else None,
        "median": statistics.median(scores) if scores else None,
        "stdev": statistics.pstdev(scores) if len(scores) > 1 else (0.0 if scores else None),
        "min": min(scores) if scores else None,
        "max": max(scores) if scores else None,
        "high_ge_0.7": high,
        "mid_0.5_to_0.7": mid,
        "low_lt_0.5": low,
        "high_pct": high / len(scores) * 100 if scores else None,
        "mid_pct": mid / len(scores) * 100 if scores else None,
        "low_pct": low / len(scores) * 100 if scores else None,
    }

    def folder_payload(stats):
        return {
            "sampled": stats["sampled"],
            "processed": stats["processed"],
            "images_with_detections": stats["images_with_detections"],
            "boxes": stats["boxes"],
            "classes": dict(stats["classes"]),
        }

    elapsed = time.time() - started
    payload = {
        "mode": "images",
        "model": str(Path(args.model).resolve()),
        "source": str(source),
        "sample_requested": args.sample,
        "images_available": len(images),
        "sampled": len(sampled),
        "processed": processed,
        "skipped": len(skipped),
        "skipped_details": skipped[:200],
        "conf": args.conf,
        "iou": args.iou,
        "imgsz": args.imgsz,
        "seed": args.seed,
        "elapsed_sec": elapsed,
        "summary": {
            "total_boxes": counters["total_boxes"],
            "images_with_detections": counters["images_with_detections"],
            "detection_rate_pct": counters["images_with_detections"] / processed * 100,
            "avg_boxes_per_image": counters["total_boxes"] / processed,
            "avg_sec_per_image": elapsed / processed,
            "class_counts": dict(class_counts),
        },
        "confidence": confidence,
        "per_folder": {
            folder: folder_payload(stats)
            for folder, stats in sorted(per_folder.items())
        },
        "visualizations": str(vis_dir) if args.save_visuals else None,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "note": "Unlabeled image validation is qualitative; no mAP is computed.",
    }

    summary = payload["summary"]
    print("Unlabeled image validation")
    print(f"  model: {payload['model']}")
    print(f"  source: {payload['source']}")
    print(
        f"  sampled={len(sampled)} processed={processed} skipped={len(skipped)} "
        f"available={len(images)}"
    )
    print(
        f"  detection rate={_pct(summary['detection_rate_pct'])} "
        f"boxes={summary['total_boxes']} avg boxes/image={_fmt(summary['avg_boxes_per_image'], 2)}"
    )
    print(f"  avg time/image={summary['avg_sec_per_image']:.3f}s")
    print(f"  classes: {dict(class_counts)}")
    print(
        f"  confidence: mean={_fmt(confidence['mean'])} median={_fmt(confidence['median'])} "
        f"high>=0.7={_pct(confidence['high_pct'])}"
    )

    _write_json(args.output, payload)

    lines = [
        "# YOLO unlabeled image validation",
        "",
        f"- model: `{payload['model']}`",
        f"- source: `{payload['source']}`",
        f"- sampled: {len(sampled)}, processed: {processed}, skipped: {len(skipped)}",
        f"- conf: {args.conf}, iou: {args.iou}, seed: {args.seed}, imgsz: {args.imgsz}",
        "",
        "> Qualitative validation only; no ground-truth labels, so no mAP.",
        "",
        "| Metric | Value |",
        "|--------|-------|",
        f"| Detection rate | {_pct(summary['detection_rate_pct'])} |",
        f"| Total boxes | {summary['total_boxes']} |",
        f"| Images with detections | {summary['images_with_detections']} |",
        f"| Avg boxes/image | {_fmt(summary['avg_boxes_per_image'], 2)} |",
        f"| Avg time/image | {summary['avg_sec_per_image']:.3f} s |",
        f"| Mean confidence | {_fmt(confidence['mean'])} |",
        f"| High confidence (>=0.7) | {_pct(confidence['high_pct'])} |",
        "",
        "| Class | Count |",
        "|-------|-------|",
    ]
    for class_name, count in sorted(class_counts.items()):
        lines.append(f"| {class_name} | {count} |")
    lines.extend(
        [
            "",
            "| Folder | Sampled | Processed | With detections | Boxes |",
            "|--------|---------|-----------|-----------------|-------|",
        ]
    )
    for folder, stats in sorted(per_folder.items()):
        lines.append(
            f"| {folder} | {stats['sampled']} | {stats['processed']} | "
            f"{stats['images_with_detections']} | {stats['boxes']} |"
        )
    _write_markdown(args.markdown, lines)
    return 0


def build_parser():
    parser = argparse.ArgumentParser(description="Validate a YOLO detector on labeled or unlabeled data")
    parser.add_argument("--model", type=Path, required=True, help="Path to best.pt or best_mAP50.pt")
    parser.add_argument("--mode", choices=("labeled", "images"), required=True)

    labeled = parser.add_argument_group("labeled mode")
    labeled.add_argument("--data", type=Path, help="Dataset YAML")
    labeled.add_argument("--split", default="val", help="Dataset split to evaluate (val/test)")
    labeled.add_argument("--batch", type=int, default=32)
    labeled.add_argument("--plots", action="store_true", help="Let Ultralytics write validation plots")

    images = parser.add_argument_group("images mode")
    images.add_argument("--source", type=Path, help="Directory containing unlabeled images")
    images.add_argument("--sample", type=int, default=500, help="0 or >= available means all")
    images.add_argument("--seed", type=int, default=42)
    images.add_argument("--save-visuals", action="store_true")
    images.add_argument("--output-dir", type=Path)
    images.add_argument("--progress-every", type=int, default=50)

    common = parser.add_argument_group("common")
    common.add_argument("--imgsz", type=int, default=640)
    common.add_argument("--device", default="0")
    common.add_argument("--conf", type=float, default=None)
    common.add_argument("--iou", type=float, default=None)
    common.add_argument("--verbose", action="store_true")
    common.add_argument("--output", type=Path, help="Write JSON report")
    common.add_argument("--markdown", type=Path, help="Write Markdown report")
    common.add_argument("--debug", action="store_true", help="Re-raise exceptions")
    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()

    if not args.model.is_file():
        parser.error(f"--model does not exist: {args.model}")
    if args.mode == "labeled" and not args.data:
        parser.error("--data is required in labeled mode")
    if args.mode == "images" and not args.source:
        parser.error("--source is required in images mode")
    if args.mode == "images":
        if args.conf is None:
            args.conf = 0.25
        if args.iou is None:
            args.iou = 0.45

    try:
        if args.mode == "labeled":
            return run_labeled(args)
        return run_images(args)
    except Exception as exc:
        if args.debug:
            raise
        print(f"ERROR: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 3


if __name__ == "__main__":
    sys.exit(main())
