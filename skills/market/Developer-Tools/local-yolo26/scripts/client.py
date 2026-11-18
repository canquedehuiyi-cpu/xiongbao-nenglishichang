# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: Intel OBL

"""Short-lived CLI controller for the local-yolo26 detection server.

Controls a long-running server.py over the Windows named pipe
``\\\\.\\pipe\\local-yolo26`` via the shared server-dog:

    (default)      ensure the detection server is up on the requested device
    --status       report server state + device
    --stop         shut the server down (releases camera + GPU/NPU memory)

Device switch: if a server is already running on a DIFFERENT device than
requested, it is shut down and a fresh one is started on the new device.
There is no resume flag (first-run downloads simply require re-running run.ps1).
"""

from __future__ import annotations

import argparse
import filecmp
import json
import os
import shutil
import subprocess
import sys
import time
from multiprocessing.connection import Client
from pathlib import Path

PIPE_ADDRESS = r"\\.\pipe\local-yolo26"
AUTHKEY = b"local-yolo26"
SKILL_NAME = "local-yolo26"
STATE_RUNNING_STR = "running"

DOG_PIPE_ADDRESS = r"\\.\pipe\skill-server-dog"
DOG_AUTHKEY = b"skill-server-dog"
DOG_BOOT_TIMEOUT = 30.0
DOG_BOOT_POLL_INTERVAL = 0.3
SERVER_BOOT_TIMEOUT = 60.0
SERVER_BOOT_POLL_INTERVAL = 0.3
DEFAULT_SHUTDOWN_TIMEOUT = 10.0

OPENVINO_ROOT = Path(os.environ.get("USERPROFILE", str(Path.home()))) / ".openvino"
# server-dog is a machine-wide singleton at the canonical shared temp root; the
# skill's own server tree lives under a per-skill subdir.
TEMP_ROOT = OPENVINO_ROOT / "temp"
TEMP_DOG = TEMP_ROOT / "server-dog.py"
TEMP_GET_GPU_MEM = TEMP_ROOT / "get_gpu_mem.py"
TEMP_DIR = TEMP_ROOT / "local-yolo26"
TEMP_SCRIPTS = TEMP_DIR / "scripts"
TEMP_SERVER = TEMP_SCRIPTS / "server.py"
LEGACY_TEMP_SERVER_DOG = TEMP_DIR / "server-dog.py"

# First run downloads + exports models; cap each invocation's wait generously.
DOWNLOAD_WAIT_TIMEOUT = 9 * 60.0
STATUS_POLL_INTERVAL = 2.0

_HERE = Path(__file__).resolve().parent
_SKILL_ROOT = _HERE.parent
SERVER_PATH = TEMP_SERVER
DOG_PATH = TEMP_DOG

CLAW_MAP = {
    ".workbuddy": "WorkBuddy.exe",
    ".openclaw": "openclaw.mjs",
    "Marvis": "Marvis.exe",
    ".trae-cn": "TRAE SOLO CN.exe",
    "Coze": "Coze.exe",
}


def _configure_stream_encoding(stream) -> None:
    reconfigure = getattr(stream, "reconfigure", None)
    if callable(reconfigure):
        reconfigure(encoding="utf-8")


_configure_stream_encoding(sys.stdout)
_configure_stream_encoding(sys.stderr)


def _normalize_log_path(log_path: str | None) -> Path | None:
    if not log_path:
        timestamp = time.strftime("%Y%m%d-%H%M%S")
        log_path = f"~/.openvino/log/yolo26-client-py-{timestamp}.log"
    path = Path(log_path).expanduser()
    return path if path.is_absolute() else Path.cwd() / path


def _log_message(log_path: Path | None, message: str) -> None:
    if log_path is None:
        return
    try:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with log_path.open("a", encoding="utf-8") as stream:
            timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
            stream.write(f"[{timestamp}] [client pid={os.getpid()}] {message}\n")
    except OSError:
        pass


def _try_connect():
    try:
        return Client(PIPE_ADDRESS, authkey=AUTHKEY)
    except (FileNotFoundError, OSError, EOFError):
        return None


def _try_dog_connect():
    try:
        return Client(DOG_PIPE_ADDRESS, authkey=DOG_AUTHKEY)
    except (FileNotFoundError, OSError, EOFError):
        return None


def _hidden_startupinfo():
    if os.name != "nt" or not hasattr(subprocess, "STARTUPINFO"):
        return None
    startupinfo = subprocess.STARTUPINFO()
    startupinfo.dwFlags |= getattr(subprocess, "STARTF_USESHOWWINDOW", 0)
    startupinfo.wShowWindow = getattr(subprocess, "SW_HIDE", 0)
    return startupinfo


def _pythonw_executable() -> str:
    python_exe = Path(sys.executable)
    pythonw_exe = python_exe.with_name("pythonw.exe")
    return str(pythonw_exe) if pythonw_exe.exists() else str(python_exe)


def _detect_claw_name() -> str | None:
    skill_root = str(_SKILL_ROOT)
    for key, exe in CLAW_MAP.items():
        if key in skill_root:
            return exe
    return None


def _needs_sync(src: Path, dst: Path) -> bool:
    if not dst.exists():
        return True
    return not filecmp.cmp(str(src), str(dst), shallow=False)


def _terminate_legacy_dog(log_path: Path | None) -> None:
    try:
        import psutil
    except ImportError:
        return
    target = str(LEGACY_TEMP_SERVER_DOG).casefold()
    for proc in psutil.process_iter(["pid", "cmdline"]):
        try:
            cmdline = proc.info.get("cmdline") or []
            if any(target in str(part).casefold() for part in cmdline):
                proc.terminate()
                _log_message(log_path, f"terminated legacy dog pid={proc.info.get('pid')}")
        except (psutil.AccessDenied, psutil.NoSuchProcess, psutil.ZombieProcess):
            continue


def _sync_runtime_scripts(log_path: Path | None) -> None:
    """Copy server.py and everything it imports into TEMP_DIR/scripts, plus the
    shared dog + gpu probe into TEMP_ROOT, so the server runs from a stable
    location across skill upgrades."""
    src_scripts = _HERE
    flat_files = [
        (src_scripts / "server.py", TEMP_SERVER),
        (src_scripts / "yolo_demo.py", TEMP_SCRIPTS / "yolo_demo.py"),
        (src_scripts / "demo_utils.py", TEMP_SCRIPTS / "demo_utils.py"),
        (src_scripts / "ensure_models.py", TEMP_SCRIPTS / "ensure_models.py"),
        (src_scripts / "server-dog.py", TEMP_DOG),
        (src_scripts / "get_gpu_mem.py", TEMP_GET_GPU_MEM),
    ]
    root_files = [
        (_SKILL_ROOT / "info.json", TEMP_DIR / "info.json"),
    ]
    files = flat_files + root_files
    if not any(_needs_sync(s, d) for s, d in files):
        return

    _log_message(log_path, "runtime scripts outdated; refreshing")
    if _try_connect() is not None:
        _log_message(log_path, "shutting down existing server before refresh")
        _cmd_shutdown(DEFAULT_SHUTDOWN_TIMEOUT, log_path)
        deadline = time.time() + DEFAULT_SHUTDOWN_TIMEOUT
        while time.time() < deadline and _try_connect() is not None:
            time.sleep(0.2)
    _terminate_legacy_dog(log_path)

    TEMP_SCRIPTS.mkdir(parents=True, exist_ok=True)
    TEMP_ROOT.mkdir(parents=True, exist_ok=True)
    for src, dst in files:
        last_err: Exception | None = None
        for _ in range(5):
            try:
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dst)
                last_err = None
                break
            except PermissionError as exc:
                last_err = exc
                time.sleep(0.3)
        if last_err is not None:
            raise RuntimeError(f"failed to update {dst} (still in use): {last_err}")
    _log_message(log_path, f"refreshed runtime tree under {TEMP_DIR}")


def _spawn_dog(log_path: Path | None) -> None:
    creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    env = {k: v for k, v in os.environ.items()
           if not (k.startswith("WORKBUDDY_") or k.startswith("CODEBUDDY_"))}
    OPENVINO_ROOT.mkdir(parents=True, exist_ok=True)
    subprocess.Popen(
        [_pythonw_executable(), str(DOG_PATH)],
        creationflags=creationflags,
        startupinfo=_hidden_startupinfo(),
        close_fds=True,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        cwd=str(OPENVINO_ROOT),
        env=env,
    )
    _log_message(log_path, f"spawned server-dog: {DOG_PATH}")


def _ensure_dog(log_path: Path | None):
    conn = _try_dog_connect()
    if conn is not None:
        return conn
    _spawn_dog(log_path)
    deadline = time.time() + DOG_BOOT_TIMEOUT
    while time.time() < deadline:
        conn = _try_dog_connect()
        if conn is not None:
            return conn
        time.sleep(DOG_BOOT_POLL_INTERVAL)
    raise RuntimeError("server-dog did not start")


def _read_info_json() -> dict:
    return json.loads((_SKILL_ROOT / "info.json").read_text(encoding="utf-8"))


def _request_server_start(dog_conn, device: str, log_path: Path | None) -> None:
    info = _read_info_json()
    venv_name = info.get("venv_name", "yolo26")
    mem_need_gb = float(info.get("mem_need_gb", 4.0))
    server_alive_timeout = info.get("server_alive_timeout", -1)
    venv_python = str(OPENVINO_ROOT / "venv" / venv_name / "Scripts" / "pythonw.exe")
    payload = {
        "op": "start_server",
        "skill_name": SKILL_NAME,
        "server_path": str(SERVER_PATH),
        "venv_python": venv_python,
        "pipe_address": PIPE_ADDRESS,
        "authkey": AUTHKEY.decode("latin-1"),
        "mem_need_gb": mem_need_gb,
        "server_alive_timeout": server_alive_timeout,
        "claw_name": _detect_claw_name(),
        "extra_env": {
            "YOLO_DEVICE": device.upper(),
            "OPENVINO_TELEMETRY_OPT_OUT": "1",
        },
    }
    _log_message(log_path, f"start_server -> dog (device={device}, mem_need_gb={mem_need_gb})")
    reply = None
    try:
        dog_conn.send(payload)
        reply = dog_conn.recv()
    finally:
        try:
            dog_conn.close()
        except Exception:
            pass
    if not isinstance(reply, dict) or not reply.get("ok"):
        err = (reply or {}).get("error", "<unknown>")
        if err == "not_enough_memory":
            print("系统资源不足, 无法启动该技能", file=sys.stderr)
        raise RuntimeError(f"start_server failed: {err}")
    _log_message(log_path, f"dog spawned server pid={reply.get('pid')}")


def _send(conn, msg: dict, log_path: Path | None = None) -> dict:
    try:
        conn.send(dict(msg))
        reply = conn.recv()
    finally:
        conn.close()
    return reply if isinstance(reply, dict) else {}


def _running_status(log_path: Path | None) -> dict | None:
    """Return the running server's status reply, or None if no server answers."""
    conn = _try_connect()
    if conn is None:
        return None
    return _send(conn, {"op": "status"}, log_path)


def _pid_alive(pid: int | None) -> bool:
    if not pid:
        return False
    try:
        import psutil
        return psutil.pid_exists(pid)
    except ImportError:
        return False


def _wait_for_server_gone(deadline: float, pid: int | None, log_path: Path | None) -> bool:
    """Wait until the old server is fully gone before a restart re-requests a start.

    The server closes its named-pipe listener BEFORE the process exits (OpenVINO /
    torch teardown takes several seconds), so a pipe-only check returns too early:
    the server-dog keys server reuse on pid liveness, so re-requesting while the
    old pid is still alive makes the dog hand back the dying server and spawn
    nothing. We therefore wait for BOTH the pipe to stop answering AND the pid to
    exit. When pid is unknown (None) we fall back to the pipe-only check."""
    while time.time() < deadline:
        conn = _try_connect()
        if conn is None:
            if not _pid_alive(pid):
                return True
        else:
            try:
                conn.close()
            except Exception:
                pass
        time.sleep(SERVER_BOOT_POLL_INTERVAL)
    return False


def _ensure_server(device: str, log_path: Path | None):
    _sync_runtime_scripts(log_path)

    # Device-switch restart: a running server on a different device must be
    # shut down and replaced, since the model is compiled for one device.
    status = _running_status(log_path)
    current = status.get("device") if status else None
    if current is not None and current.upper() != device.upper():
        old_pid = status.get("pid") if status else None
        _log_message(log_path, f"device switch {current} -> {device} (old pid={old_pid}); restarting server")
        print(f"切换设备 {current} -> {device.upper()}, 正在重启服务...")
        _cmd_shutdown(DEFAULT_SHUTDOWN_TIMEOUT, log_path)
        # Wait for the OLD PROCESS to exit (not just its pipe): the dog reuses a
        # server while its pid is alive, so re-requesting too early would hand
        # back the dying old-device server and never start the new one.
        if not _wait_for_server_gone(time.time() + DEFAULT_SHUTDOWN_TIMEOUT + 15.0, old_pid, log_path):
            raise RuntimeError("old server did not exit in time for device switch")
    elif current is not None:
        _log_message(log_path, f"server already running on {current}; reusing")
        return

    _log_message(log_path, "server not running; asking dog to start it")
    dog = _ensure_dog(log_path)
    _request_server_start(dog, device, log_path)
    deadline = time.time() + SERVER_BOOT_TIMEOUT
    while time.time() < deadline:
        conn = _try_connect()
        if conn is not None:
            conn.close()
            return
        time.sleep(SERVER_BOOT_POLL_INTERVAL)
    raise RuntimeError(f"server did not come up within {SERVER_BOOT_TIMEOUT:.0f}s")


def _wait_for_running(log_path: Path | None, deadline: float) -> tuple[str, dict]:
    last_reply: dict = {}
    while True:
        if time.time() >= deadline:
            return ("timeout", last_reply)
        conn = _try_connect()
        if conn is None:
            time.sleep(STATUS_POLL_INTERVAL)
            continue
        reply = _send(conn, {"op": "status"}, log_path)
        last_reply = reply
        state = reply.get("state")
        _log_message(log_path, f"wait_for_running: state={state}")
        if state == STATE_RUNNING_STR:
            return ("running", reply)
        if state == "error":
            return ("error", reply)
        remaining = deadline - time.time()
        if remaining <= 0:
            return ("timeout", last_reply)
        time.sleep(min(STATUS_POLL_INTERVAL, remaining))


def _print_running(reply: dict) -> None:
    device = reply.get("device", "?")
    print("\n=== 本地实时目标检测已就绪 / Local object detection ready ===")
    print(f"  运行设备 / device: {device}")
    print("  已弹出检测窗口, 在画面中实时显示检测框。")
    print("  A detection window is open showing live bounding boxes.")
    print("  关闭窗口 / close: 在窗口上按 q 或 ESC")
    print("  停止服务 / stop:  scripts\\run.ps1 --stop")


def _cmd_start(device: str, log_path: Path | None) -> int:
    deadline = time.time() + DOWNLOAD_WAIT_TIMEOUT
    try:
        _ensure_server(device, log_path)
    except RuntimeError as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 2

    outcome, reply = _wait_for_running(log_path, deadline)

    if outcome == "timeout":
        print("模型正在下载并转换 (首次运行较慢), 请稍候后重新运行 `scripts\\run.ps1` 继续。")
        return 3
    if outcome == "error":
        print("[ERROR] 服务初始化失败 / Server initialization failed:", file=sys.stderr)
        print(reply.get("error", "<unknown init error>"), file=sys.stderr)
        return 1

    _print_running(reply)
    return 0


def _cmd_status(log_path: Path | None) -> int:
    conn = _try_connect()
    if conn is None:
        print("server not running")
        return 0
    reply = _send(conn, {"op": "status"}, log_path)
    state = reply.get("state")
    print(
        f"state:   {state}\n"
        f"pid:     {reply.get('pid')}\n"
        f"uptime:  {reply.get('uptime_s', 0.0):.1f}s\n"
        f"device:  {reply.get('device')}"
    )
    if state == STATE_RUNNING_STR:
        _print_running(reply)
    return 0


def _cmd_shutdown(timeout: float, log_path: Path | None) -> int:
    conn = _try_connect()
    if conn is None:
        print("server not running")
        return 0
    reply = _send(conn, {"op": "shutdown", "timeout": timeout}, log_path)
    if not reply.get("ok", False):
        print(f"shutdown failed: {reply.get('error', '<unknown>')}", file=sys.stderr)
        return 1
    print(f"server shutting down (grace period: {timeout:.1f}s)")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="local-yolo26 CLI controller")
    parser.add_argument("--device", default="GPU")
    parser.add_argument("--log", type=str, default=None)
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--server-status", action="store_true")
    group.add_argument("--server-shutdown", action="store_true")
    parser.add_argument("--server-shutdown-timeout", type=float, default=DEFAULT_SHUTDOWN_TIMEOUT)
    args = parser.parse_args()
    log_path = _normalize_log_path(args.log)

    if args.server_status:
        return _cmd_status(log_path)
    if args.server_shutdown:
        return _cmd_shutdown(args.server_shutdown_timeout, log_path)
    return _cmd_start(args.device, log_path)


if __name__ == "__main__":
    sys.exit(main())
