# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: Intel OBL

"""Persistent local-yolo26 detection server.

Holds the loaded OpenVINO model and runs a live OpenCV detection window on a
background thread. Long-running: no alive-timeout (server-dog is told -1). The
client only controls it (status / shutdown); there is no per-call request op.

Listens on the Windows named pipe ``\\\\.\\pipe\\local-yolo26``.

State machine:  starting -> downloading -> loading -> running
                                                    |-> error
"""

from __future__ import annotations

import argparse
import os
import sys
import threading
import time
import traceback
from multiprocessing.connection import Listener
from pathlib import Path

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

PIPE_ADDRESS = r"\\.\pipe\local-yolo26"
AUTHKEY = b"local-yolo26"
DEFAULT_SHUTDOWN_TIMEOUT = 10.0

STATE_STARTING = "starting"
STATE_DOWNLOADING = "downloading"
STATE_LOADING = "loading"
STATE_RUNNING = "running"
STATE_ERROR = "error"

for _stream_name in ("stdout", "stderr"):
    _stream = getattr(sys, _stream_name, None)
    if _stream is not None and hasattr(_stream, "reconfigure"):
        try:
            _stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

LOG_LOCK = threading.Lock()


def _normalize_log_path(log_path: str | None) -> Path | None:
    if not log_path:
        timestamp = time.strftime("%Y%m%d-%H%M%S")
        log_path = f"~/.openvino/log/yolo26-server-py-{timestamp}.log"
    path = Path(log_path).expanduser()
    return path if path.is_absolute() else Path.cwd() / path


def _log_message(log_path: Path | None, message: str) -> None:
    if log_path is None:
        return
    try:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        with LOG_LOCK:
            with log_path.open("a", encoding="utf-8") as stream:
                stream.write(f"[{timestamp}] [server pid={os.getpid()}] {message}\n")
    except OSError:
        pass


class Server:
    def __init__(self, device: str, log_path: Path | None = None) -> None:
        self.device = device.upper()
        self.start_time = time.time()
        self.shutdown_event = threading.Event()
        self.stop_event = threading.Event()
        self.shutdown_timeout = DEFAULT_SHUTDOWN_TIMEOUT
        self.listener: Listener | None = None
        self.runtime_lock = threading.Lock()
        self.model = None
        self.log_path = log_path
        self.state = STATE_STARTING
        self.init_error = ""
        self.init_thread: threading.Thread | None = None
        self.live_thread: threading.Thread | None = None

    def log(self, message: str) -> None:
        _log_message(self.log_path, message)

    def _init_runtime_worker(self) -> None:
        try:
            with self.runtime_lock:
                self.state = STATE_DOWNLOADING
            self.log("init: downloading models")

            import ensure_models

            def _dl_log(msg: str) -> None:
                print(f"[server] {msg}", flush=True)
                self.log(msg)

            ensure_models.download_all(_dl_log)

            with self.runtime_lock:
                self.state = STATE_LOADING
            self.log("init: exporting/loading OpenVINO model")

            import yolo_demo

            model = yolo_demo.load_model(self.device)

            def _run_live() -> None:
                try:
                    yolo_demo.run_live(model, self.device, stop_event=self.stop_event)
                except Exception:
                    err = traceback.format_exc()
                    self.log(f"live loop crashed:\n{err}")
                    with self.runtime_lock:
                        self.init_error = err
                        self.state = STATE_ERROR
                finally:
                    # When the window closes on its own (q/ESC), bring the server
                    # down so the camera/GPU are released.
                    self.shutdown_event.set()

            self.live_thread = threading.Thread(target=_run_live, name="live-loop", daemon=True)
            self.live_thread.start()

            with self.runtime_lock:
                self.model = model
                self.state = STATE_RUNNING
            self.log(f"init: running on {self.device}")
        except Exception:
            error_text = traceback.format_exc()
            with self.runtime_lock:
                self.init_error = error_text
                self.state = STATE_ERROR
            self.log(f"init failed:\n{error_text}")

    def _start_init_thread(self) -> None:
        if self.init_thread is not None and self.init_thread.is_alive():
            return
        self.init_thread = threading.Thread(target=self._init_runtime_worker, name="runtime-init", daemon=True)
        self.init_thread.start()
        self.log("init thread started")

    def dispatch(self, msg: dict) -> dict:
        op = msg.get("op")
        self.log(f"dispatching op={op!r}")

        if op == "status":
            with self.runtime_lock:
                state = self.state
                init_error = self.init_error
            reply = {
                "ok": True,
                "state": state,
                "pid": os.getpid(),
                "uptime_s": time.time() - self.start_time,
                "device": self.device,
            }
            if state == STATE_ERROR and init_error:
                reply["error"] = init_error
            return reply

        if op == "shutdown":
            timeout = msg.get("timeout", DEFAULT_SHUTDOWN_TIMEOUT)
            try:
                self.shutdown_timeout = float(timeout)
            except (TypeError, ValueError):
                self.shutdown_timeout = DEFAULT_SHUTDOWN_TIMEOUT
            self.log(f"shutdown requested (timeout={self.shutdown_timeout:.1f}s)")
            self.stop_event.set()
            self.shutdown_event.set()
            return {"ok": True, "state": "shutting_down"}

        self.log(f"unknown operation: {op!r}")
        return {"ok": False, "error": f"unknown op: {op!r}"}

    def serve_forever(self) -> None:
        assert self.listener is not None
        while not self.shutdown_event.is_set():
            try:
                conn = self.listener.accept()
            except OSError:
                if self.shutdown_event.is_set():
                    return
                raise
            try:
                msg = conn.recv()
                reply = self.dispatch(msg if isinstance(msg, dict) else {})
                conn.send(reply)
            except EOFError:
                self.log("client closed before full request")
            except Exception:
                error_text = traceback.format_exc()
                try:
                    conn.send({"ok": False, "error": error_text})
                except Exception:
                    pass
                self.log(f"accept-loop error:\n{error_text}")
            finally:
                try:
                    conn.close()
                except Exception:
                    pass


def main() -> int:
    parser = argparse.ArgumentParser(description="persistent local-yolo26 detection server")
    parser.add_argument("--device", default=os.environ.get("YOLO_DEVICE", "GPU"))
    parser.add_argument("--log", type=str, default=None)
    args = parser.parse_args()

    server = Server(device=args.device, log_path=_normalize_log_path(args.log))
    server.log(f"server starting with argv={sys.argv[1:]} device={server.device}")
    try:
        server.listener = Listener(PIPE_ADDRESS, family="AF_PIPE", authkey=AUTHKEY)
    except OSError as e:
        server.log(f"bind failed: {e}")
        print(f"[server] bind failed: {e}", flush=True)
        return 2

    server.log(f"listener ready on {PIPE_ADDRESS}")
    server._start_init_thread()
    print(f"local-yolo26 server listening on {PIPE_ADDRESS} (pid={os.getpid()})", flush=True)

    worker = threading.Thread(target=server.serve_forever, name="accept-loop", daemon=True)
    worker.start()

    try:
        while not server.shutdown_event.wait(timeout=0.5):
            if not worker.is_alive():
                server.log("accept-loop exited unexpectedly")
                return 1
    finally:
        try:
            if server.listener is not None:
                server.listener.close()
        except Exception:
            pass

    worker.join(timeout=server.shutdown_timeout)
    server.log("server exited")
    return 0


if __name__ == "__main__":
    sys.exit(main())
