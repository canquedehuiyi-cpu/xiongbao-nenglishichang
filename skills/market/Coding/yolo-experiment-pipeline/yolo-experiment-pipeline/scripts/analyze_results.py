#!/usr/bin/env python3
"""Summarize and compare Ultralytics results.csv files.

The script reports both metric peaks separately, post-peak degradation, loss
trends, and a heuristic fitting assessment. It never assumes that the saved
best.pt corresponds to the mAP50 peak.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from pathlib import Path

MAP50 = "metrics/mAP50(B)"
MAP50_95 = "metrics/mAP50-95(B)"
TRAIN_BOX = "train/box_loss"
VAL_BOX = "val/box_loss"
TRAIN_CLS = "train/cls_loss"
VAL_CLS = "val/cls_loss"


def _read_csv(csv_path):
    with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        return [
            {(key.strip() if isinstance(key, str) else key): value for key, value in row.items()}
            for row in reader
        ]


def _number(row, key):
    value = row.get(key)
    if value is None or str(value).strip() == "":
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if math.isnan(number) or math.isinf(number):
        return None
    return number


def _epoch(row, index):
    epoch = _number(row, "epoch")
    return int(round(epoch)) if epoch is not None else index + 1


def _average(values):
    values = [value for value in values if value is not None]
    return sum(values) / len(values) if values else None


def _drop(best, last):
    if best is None or last is None or best == 0:
        return None
    return (best - last) / abs(best) * 100.0


def _rise(best, last):
    if best is None or last is None or best == 0:
        return None
    return (last - best) / abs(best) * 100.0


def _assess(best_epoch, total_epochs, drop50, drop95, val_box_rise):
    strong = []
    if best_epoch is not None and total_epochs:
        ratio = best_epoch / total_epochs
        if ratio < 0.4:
            strong.append(f"best epoch at {ratio:.1%} of training")
    if drop50 is not None and drop50 > 3.0:
        strong.append(f"mAP50 dropped {drop50:.2f}% after peak")
    if drop95 is not None and drop95 > 8.0:
        strong.append(f"mAP50-95 dropped {drop95:.2f}% after peak")
    if val_box_rise is not None and val_box_rise > 35.0:
        strong.append(f"val/box_loss rose {val_box_rise:.1f}% after peak")
    if strong:
        return "overfit_likely", strong

    mild = []
    if drop50 is not None and drop50 > 0.5:
        mild.append(f"mAP50 dropped {drop50:.2f}% after peak")
    if drop95 is not None and drop95 > 3.0:
        mild.append(f"mAP50-95 dropped {drop95:.2f}% after peak")
    if val_box_rise is not None and val_box_rise > 10.0:
        mild.append(f"val/box_loss rose {val_box_rise:.1f}% after peak")
    if mild:
        return "mild_overfit", mild

    if best_epoch is not None and total_epochs and best_epoch >= total_epochs - 1:
        return "still_improving", ["best epoch is at the end of training"]
    return "no_clear_overfit", ["no strong post-peak degradation signals"]


def summarize_run(run_path, window=10):
    run_path = Path(run_path)
    csv_path = run_path / "results.csv" if run_path.is_dir() else run_path
    if not csv_path.is_file():
        raise FileNotFoundError(f"results.csv not found: {csv_path}")

    rows = _read_csv(csv_path)
    if not rows:
        raise ValueError(f"empty results.csv: {csv_path}")

    records = []
    for index, row in enumerate(rows):
        records.append(
            {
                "epoch": _epoch(row, index),
                "mAP50": _number(row, MAP50),
                "mAP50_95": _number(row, MAP50_95),
                "train_box": _number(row, TRAIN_BOX),
                "val_box": _number(row, VAL_BOX),
                "train_cls": _number(row, TRAIN_CLS),
                "val_cls": _number(row, VAL_CLS),
            }
        )

    with_map50 = [record for record in records if record["mAP50"] is not None]
    with_map50_95 = [record for record in records if record["mAP50_95"] is not None]
    if not with_map50:
        raise ValueError(f"no {MAP50} values in {csv_path}")

    best50 = max(with_map50, key=lambda record: record["mAP50"])
    best95 = max(with_map50_95, key=lambda record: record["mAP50_95"]) if with_map50_95 else None
    last50 = with_map50[-1]
    last95 = with_map50_95[-1] if with_map50_95 else None
    final_epoch = records[-1]["epoch"]
    tail = records[-window:] if window > 0 else records

    drop50 = _drop(best50["mAP50"], last50["mAP50"])
    drop95 = _drop(best95["mAP50_95"], last95["mAP50_95"]) if best95 and last95 else None
    val_box_rise = _rise(best50["val_box"], last50["val_box"])
    train_box_change = _rise(best50["train_box"], last50["train_box"])
    val_cls_rise = _rise(best50["val_cls"], last50["val_cls"])

    assessment, reasons = _assess(
        best50["epoch"],
        final_epoch,
        drop50,
        drop95,
        val_box_rise,
    )

    weights_dir = csv_path.parent / "weights"
    best_pt = weights_dir / "best.pt"
    best_map50_pt = weights_dir / "best_mAP50.pt"

    return {
        "run": csv_path.parent.name if csv_path.name == "results.csv" else csv_path.stem,
        "csv": str(csv_path.resolve()),
        "epochs": final_epoch,
        "best_map50": best50["mAP50"],
        "best_map50_epoch": best50["epoch"],
        "best_map50_95": best95["mAP50_95"] if best95 else None,
        "best_map50_95_epoch": best95["epoch"] if best95 else None,
        "best_epoch_ratio": (best50["epoch"] / final_epoch) if final_epoch else None,
        "last_metric_epoch": last50["epoch"],
        "last_map50": last50["mAP50"],
        "last_map50_95": last95["mAP50_95"] if last95 else None,
        "map50_drop_pct": drop50,
        "map50_95_drop_pct": drop95,
        "tail_window": len(tail),
        "tail_map50_avg": _average([record["mAP50"] for record in tail]),
        "tail_map50_95_avg": _average([record["mAP50_95"] for record in tail]),
        "val_box_loss_rise_pct": val_box_rise,
        "train_box_loss_change_pct": train_box_change,
        "val_cls_loss_rise_pct": val_cls_rise,
        "metrics_disagree": bool(
            best95 and best95["epoch"] != best50["epoch"]
        ),
        "fit_assessment": assessment,
        "fit_reasons": reasons,
        "weights": {
            "best_pt": str(best_pt) if best_pt.exists() else None,
            "best_mAP50_pt": str(best_map50_pt) if best_map50_pt.exists() else None,
            "best_pt_selection": "mAP50-95 (default fitness)",
        },
    }


def _fmt(value, digits=4):
    return "-" if value is None else f"{value:.{digits}f}"


def _pct(value):
    return "-" if value is None else f"{value:.2f}%"


def _md(value):
    return str(value).replace("|", "\\|")


def _print_run(result):
    print(f"Run: {result['run']}")
    print(f"  csv: {result['csv']}")
    print(
        f"  epochs: {result['epochs']} | best mAP50: {_fmt(result['best_map50'])} "
        f"@ {result['best_map50_epoch']} | best mAP50-95: {_fmt(result['best_map50_95'])} "
        f"@ {result['best_map50_95_epoch']}"
    )
    print(
        f"  last metrics: mAP50={_fmt(result['last_map50'])} "
        f"mAP50-95={_fmt(result['last_map50_95'])}"
    )
    print(
        f"  post-peak: mAP50 {_pct(result['map50_drop_pct'])} | "
        f"mAP50-95 {_pct(result['map50_95_drop_pct'])} | "
        f"val/box_loss {_pct(result['val_box_loss_rise_pct'])} | "
        f"train/box_loss {_pct(result['train_box_loss_change_pct'])}"
    )
    print(
        f"  tail({result['tail_window']}): mAP50={_fmt(result['tail_map50_avg'])} "
        f"mAP50-95={_fmt(result['tail_map50_95_avg'])}"
    )
    print(
        f"  fit: {result['fit_assessment']} "
        f"({'; '.join(result['fit_reasons'])})"
    )
    if result["metrics_disagree"]:
        print(
            "  WARNING: mAP50 and mAP50-95 peaks are at different epochs; "
            "default best.pt follows mAP50-95."
        )
    print(
        f"  weights: best.pt={'yes' if result['weights']['best_pt'] else 'no'} | "
        f"best_mAP50.pt={'yes' if result['weights']['best_mAP50_pt'] else 'no'}"
    )
    if result["weights"]["best_mAP50_pt"]:
        print("  note: best_mAP50.pt exists; verify it loads before use.")
    print()


def _markdown(results):
    lines = [
        "# YOLO results comparison",
        "",
        "| Run | mAP50 | best ep | mAP50-95 | best ep | last mAP50 | mAP50 drop | val box rise | fit |",
        "|-----|-------|---------|----------|---------|------------|------------|--------------|-----|",
    ]
    for result in results:
        lines.append(
            "| {run} | {m50} | {e50} | {m95} | {e95} | {last} | {drop} | {box} | {fit} |".format(
                run=_md(result["run"]),
                m50=_fmt(result["best_map50"]),
                e50=result["best_map50_epoch"],
                m95=_fmt(result["best_map50_95"]),
                e95=result["best_map50_95_epoch"],
                last=_fmt(result["last_map50"]),
                drop=_pct(result["map50_drop_pct"]),
                box=_pct(result["val_box_loss_rise_pct"]),
                fit=result["fit_assessment"],
            )
        )
    lines.extend(
        [
            "",
            "Notes:",
            "- best.pt is selected by mAP50-95 (Ultralytics detection fitness).",
            "- Check for best_mAP50.pt when mAP50 is the business metric.",
            "- Fit assessment is heuristic; confirm with loss curves and validation trends.",
        ]
    )
    return lines


def main():
    parser = argparse.ArgumentParser(description="Summarize Ultralytics results.csv files")
    parser.add_argument("runs", nargs="+", help="Run directories or results.csv paths")
    parser.add_argument("--window", type=int, default=10, help="Tail window for moving averages")
    parser.add_argument("--json", type=Path, help="Write full results to JSON")
    parser.add_argument("--markdown", type=Path, help="Write comparison table to Markdown")
    args = parser.parse_args()

    results = []
    errors = []
    for run in args.runs:
        try:
            results.append(summarize_run(run, window=args.window))
        except Exception as exc:
            errors.append((str(run), f"{type(exc).__name__}: {exc}"))

    for run, error in errors:
        print(f"ERROR: {run}: {error}", file=sys.stderr)

    if not results:
        return 3

    for result in results:
        _print_run(result)

    if len(results) > 1:
        print("Comparison:")
        header = f"{'Run':<32} {'mAP50':>8} {'ep':>5} {'mAP50-95':>9} {'ep':>5} {'fit':>18}"
        print(header)
        print("-" * len(header))
        for result in results:
            print(
                f"{result['run'][:32]:<32} {_fmt(result['best_map50']):>8} "
                f"{result['best_map50_epoch']:>5} {_fmt(result['best_map50_95']):>9} "
                f"{str(result['best_map50_95_epoch']):>5} {result['fit_assessment']:>18}"
            )
        print()

    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(
            json.dumps({"runs": results, "errors": errors}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print(f"JSON written: {args.json}")

    if args.markdown:
        args.markdown.parent.mkdir(parents=True, exist_ok=True)
        args.markdown.write_text("\n".join(_markdown(results)) + "\n", encoding="utf-8")
        print(f"Markdown written: {args.markdown}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
