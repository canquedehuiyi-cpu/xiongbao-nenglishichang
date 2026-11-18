---
name: local-yolo26
description: |
  Local Realtime Object Detection (本地实时目标检测). Use this skill whenever the user, in Chinese or English, wants to detect or recognize objects from the local camera in real time, draw live bounding boxes, or "see what's in front of the camera".

  Trigger on Chinese phrases like 目标检测 / 实时目标检测 / 物体检测 / 物体识别 / 实时识别 / 摄像头检测 / 打开摄像头识别物体 / 检测画面中的物体 / 实时画框, and English phrases like object detection / real-time detection / detect objects / recognize objects from camera / live bounding boxes / YOLO detection — whether or not the user says "本地" / "locally".

  This skill runs **fully locally** on the user's Intel AIPC using YOLO26 exported to OpenVINO INT8. It opens the camera and shows a live OpenCV window with detection boxes, an FPS/latency overlay, and a detection count. Inference runs on Intel CPU, GPU, or NPU, selectable with `-Device`.

  Prefer this skill over any cloud vision API whenever the user wants live, local, camera-based object detection on this box.
license: Intel OBL Distribution
---

# Local Realtime Object Detection (本地实时目标检测)

## What it is

A long-running interactive service. `run.ps1` starts a background server that
downloads/exports the YOLO26 OpenVINO INT8 model once, opens the camera, and
shows a live detection window. The command returns after the window is up; the
server keeps running (no timeout) until you stop it.

## Usage

### Start detection

The working directory is the skill's root directory.
```
.\scripts\run.ps1                 # start on GPU (default), open the live window
.\scripts\run.ps1 -Device gpu     # Intel iGPU (default)
.\scripts\run.ps1 -Device npu     # Intel NPU
.\scripts\run.ps1 -Device cpu     # CPU
```

Switching `-Device` while a server is already running automatically restarts it
on the new device.

### Control

The working directory is the skill's root directory.
```
.\scripts\run.ps1 --status        # show server state + current device
.\scripts\run.ps1 --stop          # stop the server, release camera + GPU/NPU
```


## Requirements & behavior

- A camera must be present. With no camera, `run.ps1` prints
  `无法启动服务, 未检测到摄像头设备.` and exits.
- First run downloads `yolo26s.pt` and the INT8 calibration data from a gitcode
  mirror, then exports an OpenVINO INT8 model. This is slow once; later runs are
  fast. If the first run is still downloading/exporting, re-run `scripts\run.ps1`.
- Models live under `%USERPROFILE%\.openvino\models\yolo26\`.
- Fixed configuration: model `yolo26s.pt`, precision INT8, camera source `0`,
  image size 640.
