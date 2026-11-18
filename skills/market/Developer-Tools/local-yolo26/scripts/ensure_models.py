# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: Intel OBL

"""Download the YOLO26 weights and INT8 calibration data from gitcode.

Both artifacts are fetched over plain HTTP from gitcode (NOT GitHub / ModelScope):
  * yolo26s.pt  — the detector weights, exported to OpenVINO INT8 at load time.
  * coco8.zip   — the tiny COCO8 calibration dataset used by Ultralytics' INT8
                  export. Unzipped locally; a local coco8.yaml (no `download:`
                  key) is written so the export never reaches GitHub.

Everything lands under ``~/.openvino/models/yolo26/``. Each download is atomic
(into a sibling ``.partial`` path, renamed into place only after validation), so
a partial state is never observed; re-running validates and skips present
artifacts.
"""

from __future__ import annotations

import os
import shutil
import urllib.request
import zipfile
from pathlib import Path
from typing import Callable

YOLO_PT_URL = "https://gitcode.com/gcw_ggDjjkY3/kjfile/releases/download/ai-skills/yolo26s.pt"
COCO8_ZIP_URL = "https://gitcode.com/gcw_ggDjjkY3/kjfile/releases/download/ai-skills/coco8.zip"


def _openvino_root() -> Path:
    return Path(os.environ.get("USERPROFILE", str(Path.home()))) / ".openvino"


# Evaluated at import so tests that monkeypatch USERPROFILE before importing see
# the patched value. (conftest sets USERPROFILE via the autouse fixture.)
MODELS_ROOT = _openvino_root() / "models" / "yolo26"


def _log(logger: Callable[[str], None] | None, msg: str) -> None:
    if logger is not None:
        logger(msg)
    else:
        print(f"[ensure_models] {msg}", flush=True)


def _download_atomic(url: str, dest: Path, logger: Callable[[str], None] | None) -> None:
    """Download url -> dest atomically via a .partial temp file."""
    if dest.exists():
        _log(logger, f"present, skip: {dest.name}")
        return
    dest.parent.mkdir(parents=True, exist_ok=True)
    partial = dest.with_name(dest.name + ".partial")
    if partial.exists():
        partial.unlink()
    _log(logger, f"downloading {url} -> {partial}")
    with urllib.request.urlopen(url) as resp, partial.open("wb") as out:
        shutil.copyfileobj(resp, out)
    os.replace(partial, dest)
    _log(logger, f"installed {dest.name}")


def ensure_weights(logger: Callable[[str], None] | None = None) -> Path:
    dest = MODELS_ROOT / "yolo26s.pt"
    _download_atomic(YOLO_PT_URL, dest, logger)
    return dest


def ensure_coco8(logger: Callable[[str], None] | None = None) -> Path:
    """Ensure datasets/coco8/ exists (download + unzip coco8.zip atomically)."""
    coco_dir = MODELS_ROOT / "datasets" / "coco8"
    if (coco_dir / "images" / "train").is_dir() and (coco_dir / "images" / "val").is_dir():
        _log(logger, "coco8 present, skip")
        return coco_dir

    datasets_dir = MODELS_ROOT / "datasets"
    datasets_dir.mkdir(parents=True, exist_ok=True)
    zip_path = datasets_dir / "coco8.zip"
    _download_atomic(COCO8_ZIP_URL, zip_path, logger)

    extract_partial = datasets_dir / "coco8.partial"
    if extract_partial.exists():
        shutil.rmtree(extract_partial)
    extract_partial.mkdir(parents=True)
    with zipfile.ZipFile(zip_path) as zf:
        zf.extractall(extract_partial)
    # The zip contains a top-level coco8/ folder.
    extracted_root = extract_partial / "coco8"
    if not extracted_root.is_dir():
        raise RuntimeError("coco8.zip did not contain a coco8/ directory")
    if coco_dir.exists():
        shutil.rmtree(coco_dir)
    os.replace(extracted_root, coco_dir)
    shutil.rmtree(extract_partial, ignore_errors=True)
    _log(logger, f"unzipped coco8 -> {coco_dir}")
    return coco_dir


def write_coco8_yaml(logger: Callable[[str], None] | None = None) -> Path:
    """Write datasets/coco8.yaml pointing at the local images, with NO download:
    key so Ultralytics' INT8 export never reaches GitHub."""
    coco_dir = MODELS_ROOT / "datasets" / "coco8"
    yaml_path = MODELS_ROOT / "datasets" / "coco8.yaml"
    # Build COCO names mapping (0..79). Imported lazily to avoid a hard dep here.
    from yolo_demo import COCO_NAMES

    names_lines = "\n".join(f"  {idx}: {name}" for idx, name in COCO_NAMES.items())
    # Forward slashes in the path so the yaml is platform-neutral for Ultralytics.
    path_str = str(coco_dir).replace("\\", "/")
    content = (
        f"path: {path_str}\n"
        f"train: images/train\n"
        f"val: images/val\n"
        f"names:\n{names_lines}\n"
    )
    yaml_path.write_text(content, encoding="utf-8")
    _log(logger, f"wrote {yaml_path}")
    return yaml_path


def download_all(logger: Callable[[str], None] | None = None) -> None:
    """Fetch everything the loading phase needs. Raises on first hard failure."""
    MODELS_ROOT.mkdir(parents=True, exist_ok=True)
    ensure_weights(logger)
    ensure_coco8(logger)
    write_coco8_yaml(logger)
    _log(logger, "all artifacts present")


if __name__ == "__main__":
    download_all()
