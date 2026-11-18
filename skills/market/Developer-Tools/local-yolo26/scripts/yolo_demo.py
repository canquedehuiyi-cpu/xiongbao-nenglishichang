# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: Intel OBL

"""Live-only YOLO26 + OpenVINO inference, ported from the backup demo.

Trimmed to the live camera path: loads an exported OpenVINO INT8 model and runs
a real-time OpenCV detection window. Benchmark/export-CLI/downstream code from
the original demo is removed. The model and its exported OpenVINO directory live
under ``~/.openvino/models/yolo26/``. ``run_live`` is driven by server.py: it
takes the device and a ``stop_event`` so the server's shutdown can break the
render loop (in addition to the q/ESC keys).
"""

from __future__ import annotations

import os
import shutil
import threading
import time
from collections import deque
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent

# Keep Ultralytics' config + matplotlib cache inside the per-user openvino tree,
# never the (read-only, temp-copied) scripts dir.
_ULTRA_CFG = Path(os.environ.get("USERPROFILE", str(Path.home()))) / ".openvino" / "temp" / "local-yolo26" / "Ultralytics"

DEVICE_MAP = {
    "CPU": "intel:cpu",
    "GPU": "intel:gpu",
    "NPU": "intel:npu",
}

COCO_NAMES = {
    0: "person", 1: "bicycle", 2: "car", 3: "motorcycle", 4: "airplane",
    5: "bus", 6: "train", 7: "truck", 8: "boat", 9: "traffic light",
    10: "fire hydrant", 11: "stop sign", 12: "parking meter", 13: "bench",
    14: "bird", 15: "cat", 16: "dog", 17: "horse", 18: "sheep", 19: "cow",
    20: "elephant", 21: "bear", 22: "zebra", 23: "giraffe", 24: "backpack",
    25: "umbrella", 26: "handbag", 27: "tie", 28: "suitcase", 29: "frisbee",
    30: "skis", 31: "snowboard", 32: "sports ball", 33: "kite",
    34: "baseball bat", 35: "baseball glove", 36: "skateboard", 37: "surfboard",
    38: "tennis racket", 39: "bottle", 40: "wine glass", 41: "cup", 42: "fork",
    43: "knife", 44: "spoon", 45: "bowl", 46: "banana", 47: "apple",
    48: "sandwich", 49: "orange", 50: "broccoli", 51: "carrot", 52: "hot dog",
    53: "pizza", 54: "donut", 55: "cake", 56: "chair", 57: "couch",
    58: "potted plant", 59: "bed", 60: "dining table", 61: "toilet", 62: "tv",
    63: "laptop", 64: "mouse", 65: "remote", 66: "keyboard", 67: "cell phone",
    68: "microwave", 69: "oven", 70: "toaster", 71: "sink", 72: "refrigerator",
    73: "book", 74: "clock", 75: "vase", 76: "scissors", 77: "teddy bear",
    78: "hair drier", 79: "toothbrush",
}

MODEL_STEM = "yolo26s"


def models_root() -> Path:
    return Path(os.environ.get("USERPROFILE", str(Path.home()))) / ".openvino" / "models" / "yolo26"


def pt_path() -> Path:
    return models_root() / f"{MODEL_STEM}.pt"


def int8_model_dir() -> Path:
    return models_root() / f"{MODEL_STEM}_int8_openvino_model"


def coco8_yaml_path() -> Path:
    return models_root() / "datasets" / "coco8.yaml"


def _configure_ultralytics_env() -> None:
    mpl = _ULTRA_CFG / "mpl"
    _ULTRA_CFG.mkdir(parents=True, exist_ok=True)
    mpl.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("YOLO_CONFIG_DIR", str(_ULTRA_CFG))
    os.environ.setdefault("MPLCONFIGDIR", str(mpl))


def patch_ultralytics_openvino_backend(perf_hint: str = "throughput", num_requests: int = 0) -> None:
    """Force the Ultralytics OpenVINO backend to honor the perf hint / async path
    and to map intel:<device> onto an OpenVINO compiled model. Ported verbatim in
    behavior from the backup demo."""
    from ultralytics.nn.backends.openvino import OpenVINOBackend

    OpenVINOBackend._demo_perf_hint = "THROUGHPUT" if perf_hint == "throughput" else "LATENCY"
    OpenVINOBackend._demo_num_requests = max(0, int(num_requests))
    if getattr(OpenVINOBackend, "_demo_patched", False):
        return

    def load_model(self, weight) -> None:
        from ultralytics.utils import ARM64, LINUX, LOGGER
        from ultralytics.utils.checks import check_requirements
        import openvino as ov
        import torch

        LOGGER.info(f"Loading {weight} for OpenVINO inference...")
        check_requirements("openvino>=2024.0.0")

        core = ov.Core()
        fallback_device = "CPU" if core.available_devices == ["CPU"] else "AUTO"
        device_name = fallback_device

        if isinstance(self.device, str) and self.device.startswith("intel"):
            requested_device = self.device.split(":", 1)[1].upper()
            self.device = torch.device("cpu")
            device_name = requested_device
            if device_name not in core.available_devices:
                LOGGER.warning(f"OpenVINO device '{device_name}' not available. Using '{fallback_device}' instead.")
                device_name = fallback_device

        w = Path(weight)
        if not w.is_file():
            w = next(w.glob("*.xml"))

        ov_model = core.read_model(model=str(w), weights=w.with_suffix(".bin"))
        if ov_model.get_parameters()[0].get_layout().empty:
            ov_model.get_parameters()[0].set_layout(ov.Layout("NCHW"))

        metadata_file = w.parent / "metadata.yaml"
        if metadata_file.exists():
            from ultralytics.utils import YAML
            self.apply_metadata(YAML.load(metadata_file))

        self.inference_mode = self.__class__._demo_perf_hint
        config = {"PERFORMANCE_HINT": self.inference_mode}
        if self.__class__._demo_num_requests > 0:
            config["PERFORMANCE_HINT_NUM_REQUESTS"] = str(self.__class__._demo_num_requests)
        if LINUX and ARM64 and device_name == "CPU":
            config["EXECUTION_MODE_HINT"] = ov.properties.hint.ExecutionMode.ACCURACY
            config["INFERENCE_PRECISION_HINT"] = ov.Type.f32

        self.ov_compiled_model = core.compile_model(ov_model, device_name=device_name, config=config)
        self.input_name = self.ov_compiled_model.input().get_any_name()
        self.ov = ov

    OpenVINOBackend.load_model = load_model
    OpenVINOBackend._demo_patched = True


def _write_metadata_if_needed(target_dir: Path) -> None:
    """Ensure an Ultralytics-loadable metadata.yaml exists beside the exported
    OpenVINO model. Ported from the backup, generalized to the yolo26s stem."""
    import yaml

    yaml_path = target_dir / "metadata.yaml"
    if yaml_path.exists():
        return
    xml_files = sorted(target_dir.glob("*.xml"))
    bin_files = sorted(target_dir.glob("*.bin"))
    if not xml_files or not bin_files:
        return
    if xml_files[0].name != f"{MODEL_STEM}.xml":
        shutil.copy2(xml_files[0], target_dir / f"{MODEL_STEM}.xml")
    if bin_files[0].name != f"{MODEL_STEM}.bin":
        shutil.copy2(bin_files[0], target_dir / f"{MODEL_STEM}.bin")
    metadata_yaml = {
        "description": "YOLO26s OpenVINO model",
        "author": "Ultralytics",
        "license": "AGPL-3.0",
        "docs": "https://docs.ultralytics.com",
        "stride": 32,
        "task": "detect",
        "batch": 1,
        "imgsz": [640, 640],
        "names": COCO_NAMES,
        "args": {"batch": 1, "half": False, "int8": True, "dynamic": False, "nms": False},
        "channels": 3,
        "end2end": True,
    }
    with yaml_path.open("w", encoding="utf-8") as f:
        yaml.safe_dump(metadata_yaml, f, sort_keys=False, allow_unicode=True)


def ensure_openvino_model(imgsz: int = 640, force_export: bool = False) -> Path:
    """Export yolo26s.pt -> INT8 OpenVINO under models/yolo26/ if not present.

    Uses the locally-prepared coco8.yaml (written by ensure_models.py) for INT8
    calibration so the export never reaches GitHub. Idempotent."""
    from ultralytics import YOLO

    target_dir = int8_model_dir()
    if target_dir.exists() and not force_export and list(target_dir.glob("*.xml")):
        _write_metadata_if_needed(target_dir)
        return target_dir

    if target_dir.exists():
        shutil.rmtree(target_dir)

    model = YOLO(str(pt_path()))
    exported = Path(model.export(
        format="openvino",
        imgsz=imgsz,
        dynamic=False,
        half=False,
        int8=True,
        data=str(coco8_yaml_path()),
        fraction=1.0,
    )).resolve()

    target_dir.parent.mkdir(parents=True, exist_ok=True)
    if exported != target_dir:
        if target_dir.exists():
            shutil.rmtree(target_dir)
        shutil.move(str(exported), str(target_dir))
    _write_metadata_if_needed(target_dir)
    return target_dir


def load_model(device: str, imgsz: int = 640):
    """Build the OpenVINO model and return a ready-to-predict YOLO handle."""
    from ultralytics import YOLO

    _configure_ultralytics_env()
    patch_ultralytics_openvino_backend()
    ov_dir = ensure_openvino_model(imgsz=imgsz)
    return YOLO(str(ov_dir), task="detect")


def _configure_camera_source(source: str, width: int, height: int) -> None:
    import cv2

    if not source.isdigit():
        return
    cap = cv2.VideoCapture(int(source), cv2.CAP_DSHOW)
    if cap.isOpened():
        cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter.fourcc(*"MJPG"))
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
    cap.release()


def _source_for_ultralytics(source: str):
    return int(source) if source.isdigit() else source


def camera_available(source: str = "0") -> bool:
    """Authoritative camera probe: can OpenVINO/OpenCV actually open the source?"""
    import cv2

    if source.isdigit():
        cap = cv2.VideoCapture(int(source), cv2.CAP_DSHOW)
        if not cap.isOpened():
            cap.release()
            cap = cv2.VideoCapture(int(source))
    else:
        cap = cv2.VideoCapture(source)
    ok = cap.isOpened()
    cap.release()
    return ok


def run_live(
    model,
    device: str,
    *,
    stop_event: "threading.Event | None" = None,
    source: str = "0",
    imgsz: int = 640,
    conf: float = 0.25,
    perf_hint: str = "throughput",
    num_requests: int = 0,
    camera_width: int = 1280,
    camera_height: int = 720,
) -> int:
    """Run the live OpenCV detection window until stop_event is set or q/ESC.

    Raises RuntimeError if the camera cannot be opened, so the server can surface
    the Chinese 'no camera' message via its error state."""
    import cv2
    import numpy as np

    device = device.upper()
    if not camera_available(source):
        raise RuntimeError("无法启动服务, 未检测到摄像头设备.")

    _configure_camera_source(source, camera_width, camera_height)
    stream = model.predict(
        source=_source_for_ultralytics(source),
        show=False,
        device=DEVICE_MAP[device],
        imgsz=imgsz,
        conf=conf,
        vid_stride=1,
        stream=True,
        verbose=False,
    )

    from demo_utils import draw_panel

    title = "Ultralytics YOLO26 + OpenVINO"
    cv2.namedWindow(title, cv2.WINDOW_GUI_NORMAL)
    fps_window: deque[float] = deque(maxlen=60)
    infer_window: deque[float] = deque(maxlen=60)
    last_ts = time.perf_counter()
    skip_stats_frames = 8

    try:
        while True:
            if stop_event is not None and stop_event.is_set():
                break
            try:
                result = next(stream)
            except StopIteration:
                break
            now = time.perf_counter()
            frame_ms = (now - last_ts) * 1000.0
            last_ts = now
            if skip_stats_frames > 0:
                skip_stats_frames -= 1
            elif frame_ms > 0:
                fps_window.append(1000.0 / frame_ms)

            infer_ms = float(result.speed.get("inference", 0.0)) if hasattr(result, "speed") else 0.0
            if skip_stats_frames <= 0 and infer_ms > 0:
                infer_window.append(infer_ms)

            render = result.plot(img=result.orig_img, line_width=2, font_size=0.8, pil=False)
            avg_fps = float(np.mean(fps_window)) if fps_window else 0.0
            avg_infer_ms = float(np.mean(infer_window)) if infer_window else infer_ms
            infer_fps = 1000.0 / avg_infer_ms if avg_infer_ms > 0 else 0.0

            draw_panel(
                render,
                [
                    "Path: Ultralytics OpenVINO",
                    f"Device: {device} ({DEVICE_MAP[device]})",
                    "Precision: INT8",
                    f"OV Hint: {perf_hint.upper()} req={'AUTO' if num_requests <= 0 else num_requests}",
                    f"Live FPS: {avg_fps:.1f}",
                    f"Infer: {infer_fps:.1f} FPS / {avg_infer_ms:.1f} ms",
                    f"Detections: {len(result.boxes) if result.boxes is not None else 0}",
                ],
                anchor="top-right",
            )
            cv2.imshow(title, render)
            key = cv2.waitKey(1)
            if key in (ord("q"), ord("Q"), 27):
                break
    finally:
        close = getattr(stream, "close", None)
        if callable(close):
            close()
        try:
            cv2.destroyWindow(title)
        except Exception:
            pass
    return 0
