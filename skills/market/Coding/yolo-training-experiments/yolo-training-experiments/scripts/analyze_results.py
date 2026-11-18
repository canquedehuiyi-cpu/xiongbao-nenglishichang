#!/usr/bin/env python3
"""Compare Ultralytics YOLO detection runs from results.csv files."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

KEYS = {
    "mAP50": "metrics/mAP50(B)",
    "mAP50_95": "metrics/mAP50-95(B)",
    "precision": "metrics/precision(B)",
    "recall": "metrics/recall(B)",
    "train_box": "train/box_loss",
    "train_cls": "train/cls_loss",
    "val_box": "val/box_loss",
    "val_cls": "val/cls_loss",
}


def as_float(value: Any) -> float | None:
    try:
        if value is None or value == "":
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def mean(values: list[float]) -> float | None:
    return sum(values) / len(values) if values else None


def pct_change(old: float | None, new: float | None) -> float | None:
    if old is None or new is None or old == 0:
        return None
    return (new - old) / old * 100


def mean_abs_step(values: list[float]) -> float | None:
    if len(values) < 2:
        return None
    steps = [abs(values[index] - values[index - 1]) for index in range(1, len(values))]
    return mean(steps)


def load_rows(csv_path: Path) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    with csv_path.open(newline="", encoding="utf-8-sig") as handle:
        for raw in csv.DictReader(handle):
            row = {str(key).strip(): value for key, value in raw.items() if key is not None}
            if as_float(row.get(KEYS["mAP50"])) is not None:
                rows.append(row)
    return rows


def discover_runs(paths: list[Path]) -> list[Path]:
    runs: list[Path] = []
    seen: set[Path] = set()
    for raw in paths:
        path = raw.expanduser().resolve()
        candidates: list[Path] = []
        if (path / "results.csv").is_file():
            candidates = [path]
        elif path.is_dir():
            candidates = [
                child
                for child in sorted(path.iterdir())
                if child.is_dir() and (child / "results.csv").is_file()
            ]
        for candidate in candidates:
            resolved = candidate.resolve()
            if resolved not in seen:
                seen.add(resolved)
                runs.append(resolved)
    return runs


def best_index(rows: list[dict[str, str]], key: str) -> int | None:
    best_i: int | None = None
    best_value: float | None = None
    for index, row in enumerate(rows):
        value = as_float(row.get(key))
        if value is None:
            continue
        if best_value is None or value > best_value:
            best_i, best_value = index, value
    return best_i


def metrics_at(rows: list[dict[str, str]], index: int | None) -> dict[str, Any] | None:
    if index is None or index < 0 or index >= len(rows):
        return None
    row = rows[index]
    return {
        "epoch": index + 1,
        "mAP50": as_float(row.get(KEYS["mAP50"])),
        "mAP50_95": as_float(row.get(KEYS["mAP50_95"])),
        "precision": as_float(row.get(KEYS["precision"])),
        "recall": as_float(row.get(KEYS["recall"])),
        "train_box_loss": as_float(row.get(KEYS["train_box"])),
        "train_cls_loss": as_float(row.get(KEYS["train_cls"])),
        "val_box_loss": as_float(row.get(KEYS["val_box"])),
        "val_cls_loss": as_float(row.get(KEYS["val_cls"])),
    }


def loss_series(rows: list[dict[str, str]], first: str, second: str) -> list[float | None]:
    values: list[float | None] = []
    for row in rows:
        a = as_float(row.get(first))
        b = as_float(row.get(second))
        if a is not None and b is not None:
            values.append(a + b)
        elif a is not None:
            values.append(a)
        elif b is not None:
            values.append(b)
        else:
            values.append(None)
    return values


def fit_assessment(rows: list[dict[str, str]], min_epochs: int) -> dict[str, Any]:
    n = len(rows)
    if n < min_epochs:
        return {
            "flags": ["INSUFFICIENT_DATA"],
            "evidence": [f"only {n} epochs; need at least {min_epochs} for a trend check"],
            "best_epoch_ratio": None,
            "mAP50_volatility": None,
            "peak_to_last_drop": None,
            "train_loss_change_pct": None,
            "val_loss_change_pct": None,
        }

    m50 = [as_float(row.get(KEYS["mAP50"])) for row in rows]
    m50_values = [value for value in m50 if value is not None]
    best_i = best_index(rows, KEYS["mAP50"])
    last_i = n - 1
    if best_i is None:
        return {
            "flags": ["INSUFFICIENT_DATA"],
            "evidence": ["mAP50 column is missing or empty"],
            "best_epoch_ratio": None,
            "mAP50_volatility": None,
            "peak_to_last_drop": None,
            "train_loss_change_pct": None,
            "val_loss_change_pct": None,
        }

    peak = m50_values[best_i] if best_i < len(m50_values) else None
    last = m50_values[-1]
    drop = None if peak is None else peak - (last or 0)
    best_ratio = (best_i + 1) / n

    warmup = max(1, n // 10)
    tail = [value for value in m50_values[warmup:] if value is not None]
    volatility = mean_abs_step(tail)

    train = loss_series(rows, KEYS["train_box"], KEYS["train_cls"])
    val = loss_series(rows, KEYS["val_box"], KEYS["val_cls"])
    early_n = max(1, n // 10)
    early_train = mean([value for value in train[:early_n] if value is not None])
    late_train = mean([value for value in train[-early_n:] if value is not None])
    train_change = pct_change(early_train, late_train)
    val_at_best = val[best_i] if 0 <= best_i < len(val) else None
    val_at_last = val[-1] if val else None
    val_change = pct_change(val_at_best, val_at_last)

    flags: list[str] = []
    evidence: list[str] = []

    if drop is not None and drop >= 0.05 and best_ratio <= 0.95:
        flags.append("OVERFIT_SIGNAL")
        evidence.append(
            f"mAP50 peaked at epoch {best_i + 1} ({peak:.4f}) then fell "
            f"{drop:.4f} to {last:.4f} by epoch {n}"
        )
        if train_change is not None and val_change is not None:
            evidence.append(
                f"train loss changed {train_change:+.1f}% (early→late) while val loss "
                f"changed {val_change:+.1f}% (best→last)"
            )

    if best_i >= n - max(2, n // 20):
        flags.append("STILL_IMPROVING")
        evidence.append(
            f"best mAP50 epoch is {best_i + 1}/{n}; the run had not clearly plateaued"
        )

    if volatility is not None and volatility >= 0.04:
        flags.append("HIGH_VAL_NOISE")
        evidence.append(
            f"mean absolute epoch-to-epoch mAP50 change after warmup is {volatility:.4f}; "
            "a small validation set can produce this"
        )

    if "OVERFIT_SIGNAL" not in flags and "STILL_IMPROVING" not in flags:
        flags.append("NO_STRONG_SIGNAL")
        evidence.append("no strong overfitting or still-improving pattern was detected")

    if "OVERFIT_SIGNAL" in flags and "HIGH_VAL_NOISE" in flags:
        evidence.append("overfitting signal is mixed with high validation noise; confirm with repeats")

    return {
        "flags": flags,
        "evidence": evidence,
        "best_epoch_ratio": best_ratio,
        "mAP50_volatility": volatility,
        "peak_to_last_drop": drop,
        "train_loss_change_pct": train_change,
        "val_loss_change_pct": val_change,
    }


def analyze_run(run_dir: Path, min_epochs: int) -> dict[str, Any]:
    rows = load_rows(run_dir / "results.csv")
    weights = run_dir / "weights"
    best50 = best_index(rows, KEYS["mAP50"])
    best95 = best_index(rows, KEYS["mAP50_95"])
    sidecar = weights / "best_mAP50.json"
    sidecar_data = None
    if sidecar.is_file():
        try:
            sidecar_data = json.loads(sidecar.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            sidecar_data = None
    return {
        "name": run_dir.name,
        "run_dir": str(run_dir),
        "results_csv": str(run_dir / "results.csv"),
        "epochs": len(rows),
        "best_by_mAP50": metrics_at(rows, best50),
        "best_by_mAP50_95": metrics_at(rows, best95),
        "last": metrics_at(rows, len(rows) - 1) if rows else None,
        "fit": fit_assessment(rows, min_epochs),
        "checkpoints": {
            "best_pt": str(weights / "best.pt") if (weights / "best.pt").is_file() else None,
            "best_mAP50_pt": str(weights / "best_mAP50.pt")
            if (weights / "best_mAP50.pt").is_file()
            else None,
            "best_mAP50_json": sidecar_data,
        },
    }


def metric_curve(rows: list[dict[str, str]], key: str) -> list[float]:
    return [
        value
        for row in rows
        if (value := as_float(row.get(key))) is not None
    ]


def identical_curves(
    runs: list[Path], reports: list[dict[str, Any]], tolerance: float
) -> list[dict[str, Any]]:
    curves: list[tuple[str, list[float]]] = []
    for run_dir, report in zip(runs, reports):
        rows = load_rows(run_dir / "results.csv")
        curve = metric_curve(rows, KEYS["mAP50"])
        if len(curve) >= 5 and len(set(round(value, 9) for value in curve)) > 1:
            curves.append((report["name"], curve))

    matches: list[dict[str, Any]] = []
    for i in range(len(curves)):
        for j in range(i + 1, len(curves)):
            name_a, curve_a = curves[i]
            name_b, curve_b = curves[j]
            n = min(len(curve_a), len(curve_b))
            if n < 5:
                continue
            if all(abs(curve_a[k] - curve_b[k]) <= tolerance for k in range(n)):
                matches.append(
                    {
                        "a": name_a,
                        "b": name_b,
                        "compared_epochs": n,
                        "tolerance": tolerance,
                        "hint": (
                            "check duplicate configs or detection-ignored augmentation "
                            "parameters such as erasing/auto_augment"
                        ),
                    }
                )
    return matches


def fmt(value: Any, digits: int = 4) -> str:
    return f"{value:.{digits}f}" if isinstance(value, (int, float)) else "-"


def pct(value: float | None) -> str:
    return f"{value:+.1f}%" if isinstance(value, (int, float)) else "-"


def render_console(reports: list[dict[str, Any]], matches: list[dict[str, Any]]) -> str:
    lines: list[str] = []
    lines.append("Best by mAP50")
    lines.append(
        f"{'run':<28} {'ep':>5} {'mAP50':>8} {'mAP50-95':>10} {'P':>7} {'R':>7} {'best_mAP50.pt':>14}"
    )
    lines.append("-" * 92)
    for item in reports:
        best = item["best_by_mAP50"] or {}
        lines.append(
            f"{item['name']:<28} {fmt(best.get('epoch'), 0):>5} {fmt(best.get('mAP50')):>8} "
            f"{fmt(best.get('mAP50_95')):>10} {fmt(best.get('precision')):>7} "
            f"{fmt(best.get('recall')):>7} "
            f"{'yes' if item['checkpoints']['best_mAP50_pt'] else 'no':>14}"
        )

    lines.append("\nBest by mAP50-95")
    lines.append(
        f"{'run':<28} {'ep':>5} {'mAP50-95':>10} {'mAP50':>8} {'P':>7} {'R':>7} {'best.pt':>10}"
    )
    lines.append("-" * 88)
    for item in reports:
        best = item["best_by_mAP50_95"] or {}
        lines.append(
            f"{item['name']:<28} {fmt(best.get('epoch'), 0):>5} {fmt(best.get('mAP50_95')):>10} "
            f"{fmt(best.get('mAP50')):>8} {fmt(best.get('precision')):>7} "
            f"{fmt(best.get('recall')):>7} "
            f"{'yes' if item['checkpoints']['best_pt'] else 'no':>10}"
        )

    lines.append("\nFitting")
    lines.append(
        f"{'run':<28} {'ep':>5} {'best ep':>8} {'drop':>8} {'train d%':>9} {'val d%':>8} flags"
    )
    lines.append("-" * 96)
    for item in reports:
        fit = item["fit"]
        best_ep = (item["best_by_mAP50"] or {}).get("epoch")
        lines.append(
            f"{item['name']:<28} {item['epochs']:>5} {fmt(best_ep, 0):>8} "
            f"{fmt(fit.get('peak_to_last_drop')):>8} {pct(fit.get('train_loss_change_pct')):>9} "
            f"{pct(fit.get('val_loss_change_pct')):>8} {','.join(fit['flags'])}"
        )
    lines.append("train d%: early->late; val d%: mAP50-best->last")

    if matches:
        lines.append("\nIdentical mAP50 curves")
        for match in matches:
            lines.append(
                f"- {match['a']} ~ {match['b']} over {match['compared_epochs']} epochs; "
                f"{match['hint']}"
            )
    return "\n".join(lines)


def render_markdown(
    reports: list[dict[str, Any]], matches: list[dict[str, Any]]
) -> str:
    lines = [
        "# YOLO 训练实验结果对比",
        "",
        f"生成时间：{datetime.now().isoformat(timespec='seconds')}",
        "",
        "## 按 mAP50 选择",
        "",
        "| Run | Best epoch | mAP50 | mAP50-95 @ same epoch | Precision | Recall | best_mAP50.pt |",
        "|---|---:|---:|---:|---:|---:|---|",
    ]
    for item in reports:
        best = item["best_by_mAP50"] or {}
        lines.append(
            f"| {item['name']} | {fmt(best.get('epoch'), 0)} | {fmt(best.get('mAP50'))} | "
            f"{fmt(best.get('mAP50_95'))} | {fmt(best.get('precision'))} | "
            f"{fmt(best.get('recall'))} | {'yes' if item['checkpoints']['best_mAP50_pt'] else 'no'} |"
        )

    lines += [
        "",
        "## 按 mAP50-95 选择",
        "",
        "| Run | Best epoch | mAP50-95 | mAP50 @ same epoch | Precision | Recall | best.pt |",
        "|---|---:|---:|---:|---:|---:|---|",
    ]
    for item in reports:
        best = item["best_by_mAP50_95"] or {}
        lines.append(
            f"| {item['name']} | {fmt(best.get('epoch'), 0)} | {fmt(best.get('mAP50_95'))} | "
            f"{fmt(best.get('mAP50'))} | {fmt(best.get('precision'))} | "
            f"{fmt(best.get('recall'))} | {'yes' if item['checkpoints']['best_pt'] else 'no'} |"
        )

    lines += [
        "",
        "## 拟合状态",
        "",
        "| Run | Epochs | Best mAP50 epoch | Peak→last drop | Train loss Δ (early→late) | Val loss Δ (mAP50-best→last) | Flags |",
        "|---|---:|---:|---:|---:|---:|---|",
    ]
    for item in reports:
        fit = item["fit"]
        best = item["best_by_mAP50"] or {}
        lines.append(
            f"| {item['name']} | {item['epochs']} | {fmt(best.get('epoch'), 0)} | "
            f"{fmt(fit.get('peak_to_last_drop'))} | {pct(fit.get('train_loss_change_pct'))} | "
            f"{pct(fit.get('val_loss_change_pct'))} | {', '.join(fit['flags'])} |"
        )

    lines += ["", "### 判断依据", ""]
    for item in reports:
        lines.append(f"**{item['name']}**")
        for evidence in item["fit"]["evidence"]:
            lines.append(f"- {evidence}")
        lines.append("")

    if matches:
        lines += ["## 相同训练曲线", ""]
        for match in matches:
            lines.append(
                f"- `{match['a']}` 与 `{match['b']}` 在前 {match['compared_epochs']} 个 epoch "
                f"mAP50 曲线完全相同。{match['hint']}。"
            )
        lines.append("")

    lines += [
        "## 解读限制",
        "",
        "- 表格中的 P/R/mAP50-95 是同一 epoch 的伴随指标，不是各自峰值。",
        "- 拟合标记是启发式；验证集很小时必须结合重复实验判断。",
        "- 只比较同一数据划分、同一 imgsz 和同一评估阈值下的结果。",
    ]
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Compare one or more Ultralytics YOLO runs using results.csv."
    )
    parser.add_argument("paths", nargs="+", type=Path, help="run directories or parent directories")
    parser.add_argument("--markdown", type=Path, help="write a Markdown report")
    parser.add_argument("--json", dest="json_path", type=Path, help="write a JSON report")
    parser.add_argument(
        "--tolerance", type=float, default=1e-6, help="tolerance for identical curve detection"
    )
    parser.add_argument(
        "--min-epochs", type=int, default=5, help="minimum epochs for fit trend checks"
    )
    args = parser.parse_args()

    runs = discover_runs(args.paths)
    if not runs:
        print("no results.csv found in the given paths", file=sys.stderr)
        return 2

    reports = [analyze_run(run_dir, args.min_epochs) for run_dir in runs]
    matches = identical_curves(runs, reports, args.tolerance)

    console = render_console(reports, matches)
    print(console)

    if args.markdown:
        args.markdown.parent.mkdir(parents=True, exist_ok=True)
        args.markdown.write_text(render_markdown(reports, matches), encoding="utf-8")
        print(f"\nmarkdown: {args.markdown}")

    if args.json_path:
        args.json_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "runs": reports,
            "identical_curves": matches,
            "notes": [
                "metrics marked 'at same epoch' are not per-metric peaks",
                "fit flags are heuristics; small validation sets require repeats",
            ],
        }
        args.json_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(f"json: {args.json_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
