#!/usr/bin/env python3
"""Run a controlled batch of Ultralytics YOLO detection experiments."""

from __future__ import annotations

import argparse
import csv
import json
import shutil
import sys
import time
import traceback
from datetime import datetime
from pathlib import Path
from typing import Any

CLASSIFICATION_ONLY = {"erasing", "auto_augment"}
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


def load_config(path: Path) -> dict[str, Any]:
    config = json.loads(path.read_text(encoding="utf-8-sig"))
    if not config.get("data"):
        raise ValueError("config.data is required")
    experiments = config.get("experiments") or []
    if not experiments:
        raise ValueError("config.experiments must contain at least one experiment")
    names: set[str] = set()
    for exp in experiments:
        name = str(exp.get("name", "")).strip()
        if not name:
            raise ValueError("every experiment needs a non-empty name")
        if any(char in name for char in ("/", "\\")):
            raise ValueError(f"experiment name must not contain path separators: {name}")
        if name in names:
            raise ValueError(f"duplicate experiment name: {name}")
        names.add(name)
        if not exp.get("model"):
            raise ValueError(f"experiment {name} is missing model")
    config["experiments"] = experiments
    return config


def build_params(config: dict[str, Any], exp: dict[str, Any], project_root: Path) -> dict[str, Any]:
    params = dict(config.get("common") or {})
    params.update(exp.get("params") or {})
    for key in ("name", "project", "exist_ok", "model", "resume"):
        params.pop(key, None)
    params["data"] = exp.get("data", config["data"])
    params["project"] = str(project_root)
    params["name"] = str(exp["name"])
    params["exist_ok"] = False
    if params.get("save") is False:
        print(f"[WARN] {exp['name']}: save=false ignored; dual-best saving needs save=true")
    if params.get("val") is False:
        print(f"[WARN] {exp['name']}: val=false ignored; per-epoch metrics need val=true")
    params["save"] = True
    params["val"] = True
    return params


def warn_invalid_detection_aug(name: str, params: dict[str, Any]) -> None:
    for key in sorted(CLASSIFICATION_ONLY.intersection(params)):
        value = params[key]
        if value in (None, False, 0, 0.0, "", "none", "None"):
            continue
        print(
            f"[WARN] {name}: {key}={value!r} is classification-only in Ultralytics "
            "and will be silently ignored for detection"
        )


def canonical_experiment(exp: dict[str, Any], params: dict[str, Any]) -> str:
    normalized = dict(params)
    for key in ("project", "name", "exist_ok"):
        normalized.pop(key, None)
    return json.dumps(
        {"model": exp.get("model"), "params": normalized},
        sort_keys=True,
        default=str,
    )


def prepare_run_dir(project_root: Path, name: str, overwrite: bool) -> Path:
    project_root.mkdir(parents=True, exist_ok=True)
    run_dir = project_root / name
    if not run_dir.exists():
        return run_dir
    if not overwrite:
        raise FileExistsError(
            f"{run_dir} already exists; choose a new experiment name or pass --overwrite "
            "to move the old directory to a timestamped backup"
        )
    backup = run_dir.with_name(f"{run_dir.name}.bak-{datetime.now():%Y%m%d-%H%M%S}")
    counter = 1
    while backup.exists():
        backup = run_dir.with_name(
            f"{run_dir.name}.bak-{datetime.now():%Y%m%d-%H%M%S}-{counter}"
        )
        counter += 1
    run_dir.rename(backup)
    print(f"[backup] {run_dir.name} -> {backup.name}")
    return run_dir


def attach_best_map50(model: Any, run_dir: Path, version: str) -> dict[str, Any]:
    state: dict[str, Any] = {
        "best_mAP50": None,
        "best_epoch": None,
        "checkpoint": None,
        "metrics_at_best": None,
    }

    def on_model_save(trainer: Any) -> None:
        metrics = getattr(trainer, "metrics", None) or {}
        m50 = as_float(metrics.get(KEYS["mAP50"]))
        if m50 is None:
            validator = getattr(trainer, "validator", None)
            try:
                m50 = float(validator.metrics.box.map50)
            except Exception:
                return
        if state["best_mAP50"] is not None and m50 <= state["best_mAP50"]:
            return

        source = Path(str(getattr(trainer, "last", "")))
        if not source.is_file():
            print(f"[WARN] {run_dir.name}: trainer.last is missing; best_mAP50.pt not saved")
            return
        destination = Path(getattr(trainer, "wdir", run_dir / "weights")) / "best_mAP50.pt"
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, destination)

        metrics_at_best = {}
        for key, value in metrics.items():
            number = as_float(value)
            if number is not None:
                metrics_at_best[key] = number
        state.update(
            best_mAP50=m50,
            best_epoch=int(trainer.epoch) + 1,
            checkpoint=str(destination),
            metrics_at_best=metrics_at_best,
        )
        sidecar = destination.with_name("best_mAP50.json")
        sidecar.write_text(
            json.dumps(
                {
                    "run": run_dir.name,
                    "mAP50": m50,
                    "epoch": state["best_epoch"],
                    "metrics_at_best": metrics_at_best,
                    "source_checkpoint": str(source),
                    "ultralytics_version": version,
                    "created_at": datetime.now().isoformat(timespec="seconds"),
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        print(
            f"[dual-best] {run_dir.name}: best_mAP50.pt at epoch "
            f"{state['best_epoch']} (mAP50={m50:.4f})"
        )

    model.add_callback("on_model_save", on_model_save)
    return state


def read_results(csv_path: Path) -> list[dict[str, str]]:
    if not csv_path.is_file():
        return []
    rows: list[dict[str, str]] = []
    with csv_path.open(newline="", encoding="utf-8-sig") as handle:
        for raw in csv.DictReader(handle):
            row = {str(key).strip(): value for key, value in raw.items() if key is not None}
            if as_float(row.get(KEYS["mAP50"])) is not None:
                rows.append(row)
    return rows


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


def verify_checkpoint(path: str | None) -> dict[str, Any]:
    if not path:
        return {"status": "missing"}
    try:
        from ultralytics import YOLO

        YOLO(path, verbose=False)
        return {"status": "ok", "path": path}
    except Exception as exc:  # noqa: BLE001 - report loader errors verbatim
        return {"status": "failed", "path": path, "error": str(exc)}


def summarize(
    exp: dict[str, Any],
    run_dir: Path,
    rows: list[dict[str, str]],
    state: dict[str, Any],
    elapsed: float,
    version: str,
) -> dict[str, Any]:
    best50 = best_index(rows, KEYS["mAP50"])
    best95 = best_index(rows, KEYS["mAP50_95"])
    summary = {
        "name": exp["name"],
        "desc": exp.get("desc", ""),
        "run_dir": str(run_dir),
        "epochs_completed": len(rows),
        "time_min": round(elapsed / 60, 2),
        "status": "ok" if rows else "no_results",
        "best_by_mAP50": metrics_at(rows, best50),
        "best_by_mAP50_95": metrics_at(rows, best95),
        "last": metrics_at(rows, len(rows) - 1) if rows else None,
        "best_mAP50_checkpoint": state,
        "checkpoint_load": verify_checkpoint(state.get("checkpoint")),
        "ultralytics_version": version,
    }
    (run_dir / "experiment_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return summary


def run_one(
    config: dict[str, Any], exp: dict[str, Any], project_root: Path, overwrite: bool
) -> dict[str, Any]:
    from ultralytics import YOLO
    import ultralytics

    params = build_params(config, exp, project_root)
    warn_invalid_detection_aug(exp["name"], params)
    run_dir = prepare_run_dir(project_root, exp["name"], overwrite)

    print("\n" + "=" * 72)
    print(f"[{datetime.now():%H:%M:%S}] {exp['name']}: {exp.get('desc', '')}")
    print(f"  model : {exp['model']}")
    print(f"  data  : {params['data']}")
    print(f"  output: {run_dir}")
    print("=" * 72)

    model = YOLO(str(exp["model"]))
    state = attach_best_map50(model, run_dir, ultralytics.__version__)
    started = time.time()
    model.train(**params)
    elapsed = time.time() - started
    rows = read_results(run_dir / "results.csv")
    summary = summarize(exp, run_dir, rows, state, elapsed, ultralytics.__version__)
    if not rows:
        print(f"[WARN] {exp['name']}: results.csv missing or empty")
    if summary["checkpoint_load"]["status"] == "failed":
        print(f"[WARN] {exp['name']}: best_mAP50.pt failed to load; use best.pt")
    return summary


def write_batch_summary(
    project_root: Path,
    config_path: Path,
    summaries: list[dict[str, Any]],
    failures: list[dict[str, Any]],
) -> None:
    project_root.mkdir(parents=True, exist_ok=True)
    payload = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "config": str(config_path),
        "experiments": summaries,
        "failures": failures,
    }
    (project_root / "batch_summary.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    columns = [
        "name",
        "status",
        "epochs_completed",
        "time_min",
        "mAP50",
        "best_mAP50_epoch",
        "mAP50_95_at_mAP50_best",
        "mAP50_95",
        "best_mAP50_95_epoch",
        "mAP50_at_mAP50_95_best",
        "last_mAP50",
        "checkpoint_load",
    ]
    with (project_root / "batch_summary.csv").open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        for item in summaries:
            best50 = item.get("best_by_mAP50") or {}
            best95 = item.get("best_by_mAP50_95") or {}
            last = item.get("last") or {}
            writer.writerow(
                {
                    "name": item["name"],
                    "status": item["status"],
                    "epochs_completed": item["epochs_completed"],
                    "time_min": item["time_min"],
                    "mAP50": best50.get("mAP50"),
                    "best_mAP50_epoch": best50.get("epoch"),
                    "mAP50_95_at_mAP50_best": best50.get("mAP50_95"),
                    "mAP50_95": best95.get("mAP50_95"),
                    "best_mAP50_95_epoch": best95.get("epoch"),
                    "mAP50_at_mAP50_95_best": best95.get("mAP50"),
                    "last_mAP50": last.get("mAP50"),
                    "checkpoint_load": item["checkpoint_load"]["status"],
                }
            )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run controlled Ultralytics YOLO detection experiments from a JSON config."
    )
    parser.add_argument("--config", required=True, type=Path, help="experiment config JSON")
    parser.add_argument("--dry-run", action="store_true", help="print effective params and exit")
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="move an existing run directory to a timestamped backup instead of refusing",
    )
    parser.add_argument("--only", help="comma-separated experiment names to run")
    args = parser.parse_args()

    config_path = args.config.expanduser().resolve()
    config = load_config(config_path)
    project_root = Path(config.get("project", "results")).expanduser()
    experiments = config["experiments"]

    if args.only:
        wanted = {name.strip() for name in args.only.split(",") if name.strip()}
        known = {exp["name"] for exp in experiments}
        missing = wanted - known
        if missing:
            parser.error(f"unknown experiment name(s): {', '.join(sorted(missing))}")
        experiments = [exp for exp in experiments if exp["name"] in wanted]

    if args.dry_run:
        print(f"project: {project_root.resolve()}")
        seen: dict[str, str] = {}
        for exp in experiments:
            params = build_params(config, exp, project_root)
            print("\n" + "-" * 72)
            print(f"{exp['name']}: {exp.get('desc', '')}")
            print(json.dumps(params, ensure_ascii=False, indent=2, default=str))
            warn_invalid_detection_aug(exp["name"], params)
            data_path = Path(str(params["data"])).expanduser()
            if not data_path.exists() and "://" not in str(data_path):
                print(f"[WARN] {exp['name']}: data path not found: {data_path}")
            key = canonical_experiment(exp, params)
            if key in seen:
                print(
                    f"[WARN] {exp['name']} has the same effective config as {seen[key]}; "
                    "the comparison would be redundant"
                )
            else:
                seen[key] = exp["name"]
        return 0

    summaries: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    for exp in experiments:
        try:
            summaries.append(run_one(config, exp, project_root, args.overwrite))
        except Exception as exc:  # noqa: BLE001 - keep the batch running
            print(f"\n[FAILED] {exp['name']}: {exc}")
            failures.append(
                {
                    "name": exp["name"],
                    "error": str(exc),
                    "traceback": traceback.format_exc()[-4000:],
                }
            )

    write_batch_summary(project_root, config_path, summaries, failures)

    print("\n" + "=" * 88)
    print(f"{'experiment':<28} {'mAP50':>8} {'mAP50-95':>10} {'load':>8} {'status':>12}")
    print("-" * 88)
    for item in summaries:
        best50 = item.get("best_by_mAP50") or {}
        best95 = item.get("best_by_mAP50_95") or {}
        m50 = best50.get("mAP50")
        m95 = best95.get("mAP50_95")
        m50_text = f"{m50:.4f}" if isinstance(m50, (int, float)) else "-"
        m95_text = f"{m95:.4f}" if isinstance(m95, (int, float)) else "-"
        print(
            f"{item['name']:<28} {m50_text:>8} {m95_text:>10} "
            f"{item['checkpoint_load']['status']:>8} {item['status']:>12}"
        )
    if failures:
        print(f"\n{len(failures)} experiment(s) failed; see {project_root / 'batch_summary.json'}")
    print(f"\nsummary: {project_root / 'batch_summary.json'}")
    return 0 if not failures else 1


if __name__ == "__main__":
    sys.exit(main())
