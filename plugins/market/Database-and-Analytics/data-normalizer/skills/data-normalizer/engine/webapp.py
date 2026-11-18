"""
webapp.py —— 本地工作台服务（内置 http.server，零外部依赖）

被 main.py 的 serve 子命令调用（用户双击 open_workbench.bat 之后
实际在跑的东西）。只服务本机（127.0.0.1），不对外监听。

用 Python 内置 http.server 替代 FastAPI/uvicorn——工作台只服务本机单人，
不需要真正的异步高并发，但要 ThreadingHTTPServer：单线程版会被浏览器的
keep-alive 连接占死，第二个请求（哪怕只是拉一个静态资源）全部饿死。
长任务的非阻塞另经 /api/async-run + /api/queue 提供（宿主 Agent 用）。
"""

from __future__ import annotations

import base64
import sys
import itertools
import json
import re
import socket
import threading
import time
import webbrowser
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlparse, parse_qs
from typing import Any

from file_browser import list_directory_tree, open_in_explorer
from io_utils import write_result_json
from main import _input_fingerprints, _persist_execution_log, _write_run_evidence, check_access
from scenario_api import Issue, IssueLevel, ScenarioDefinition
from state_store import StateStore
from workflow import crash_result, execute_task_guarded, human_summary, resume_task_guarded
from engine_runtime import EngineRuntimeImpl

# 浏览器上传的文件落在这里（不是白名单可浏览目录，避免和"产物"混在一起）
_UPLOAD_SUBDIR = "storage/uploads"
_MAX_UPLOAD_BYTES = 30 * 1024 * 1024  # 30MB：本地单人工具的合理上限
_UPLOAD_MAX_AGE_SECONDS = 7 * 24 * 3600  # 上传文件只是任务输入的临时落脚点，7 天够用


def _issue_dicts(issues) -> list[dict[str, Any]]:
    return [{"level": i.level.value, "message": i.message, "detail": i.detail} for i in issues]


def _prune_old_uploads(upload_dir: Path) -> None:
    """机会性清理：每次有新上传落地前，顺手删掉超过 7 天的旧上传文件。

    不追踪"是否还在被某次运行引用"——上传文件只是给 execute_task 用的
    临时输入副本，执行完就该功成身退；留 7 天是给"任务失败、用户还没
    来得及看就想重跑"这类场景留余量，不是长期存档。清理失败（权限、
    文件被占用）不影响本次上传，静默跳过即可。
    """
    if not upload_dir.is_dir():
        return
    cutoff = time.time() - _UPLOAD_MAX_AGE_SECONDS
    try:
        for item in upload_dir.iterdir():
            if item.is_file() and item.stat().st_mtime < cutoff:
                item.unlink(missing_ok=True)
    except OSError as exc:
        print(f"[degraded] 临时产物清理失败: {exc!r}", file=sys.stderr)


def _materialize_uploaded_files(dist_root: Path, inputs: dict) -> dict:
    """把前端上传的文件字节落成本地临时文件，替换成路径字符串。

    FILE 字段有两种给法：手动粘贴的路径（字符串，原样透传，兼容旧行为/
    CLI 场景不受影响）；或前端拖拽/选择上传的文件（{"name":..., "data":
    base64}）。落盘后场景包代码完全无感知——走的还是原来
    resolve_input_file 那条老路，不需要为"文件是不是上传的"改一行场景包
    代码。

    一个任务可能有多个 FILE 字段（比如 compliance 的要求清单+应答清单）：
    前面的字段已经写盘、后面的字段校验失败时，必须把前面已经落盘的文件
    一并撤销——不然请求整体被 400 拒绝，那个孤儿文件却永远留在磁盘上，
    没有任何运行记录会引用它。
    """
    out = dict(inputs)
    if not any(isinstance(v, dict) and "data" in v for v in inputs.values()):
        return out  # 没有真正的上传字段，不用碰 uploads 目录

    upload_dir = dist_root / _UPLOAD_SUBDIR
    _prune_old_uploads(upload_dir)

    written: list[Path] = []
    try:
        for field_id, value in inputs.items():
            if not (isinstance(value, dict) and "data" in value):
                continue
            name = str(value.get("name") or "upload")
            safe_name = re.sub(r"[^\w.\-一-鿿]+", "_", name) or "upload"
            try:
                raw = base64.b64decode(value["data"], validate=True)
            except Exception as exc:
                raise ValueError(f"字段 {field_id} 的上传内容不是合法的 base64：{exc}") from exc
            if len(raw) > _MAX_UPLOAD_BYTES:
                raise ValueError(
                    f"字段 {field_id} 的上传文件超过 {_MAX_UPLOAD_BYTES // (1024 * 1024)}MB，"
                    "请改用「手动输入路径」"
                )
            upload_dir.mkdir(parents=True, exist_ok=True)
            stamp = time.strftime("%Y%m%d-%H%M%S")
            dest = upload_dir / f"{stamp}-{safe_name}"
            n = 1
            while dest.exists():
                dest = upload_dir / f"{stamp}-{n}-{safe_name}"
                n += 1
            dest.write_bytes(raw)
            written.append(dest)
            out[field_id] = str(dest)
    except Exception:
        for path in written:
            path.unlink(missing_ok=True)
        raise
    return out


def _write_last_result(
    scenario: ScenarioDefinition, dist_root: Path, result, fingerprints: dict[str, Any],
    extra: dict[str, Any] | None = None,
    run_id: int | None = None,
) -> None:
    """写 storage/last_result.json（工作台与 CLI 的兜底信源，核验页读它）。

    run / resume / 异步三条路径共用这一份写法——分叉的代价是某条入口悄悄
    少写审计字段（resume 比 run 多一个 resumed，走 extra 传进来）。
    run_id 常量写入顶层：/api/last-result 历史下钻时要沿着它把后续的人审
    复核绑回具体这次运行（运行粒度审计），不能丢。
    落盘失败压一条 ERROR 进 result.issues，不让它拖垮收尾。
    """
    try:
        write_result_json(
            dist_root / "storage" / "last_result.json",
            {
                "scenario": scenario.name,
                "task": result.task_id,
                "run_id": run_id,
                "status": result.status.value,
                "outputs": result.outputs,
                "issues": _issue_dicts(result.issues),
                "input_fingerprints": fingerprints,
                # P1: 完整审计链
                "output_fingerprints": result.output_fingerprints,
                "data_flow": [
                    {
                        "step_index": df.step_index,
                        "step_name": df.step_name,
                        "keys_written": list(df.keys_written),
                        "keys_count": df.keys_count,
                    }
                    for df in result.data_flow
                ],
                "environment": {
                    "engine_version": result.environment.engine_version,
                    "scenario_name": result.environment.scenario_name,
                    "scenario_version": result.environment.scenario_version,
                    "template_fingerprints": result.environment.template_fingerprints,
                    "python_version": result.environment.python_version,
                },
                **(extra or {}),
            },
        )
    except Exception as exc:  # noqa: BLE001 —— 落盘失败不能拖垮整次运行的收尾
        result.issues.append(Issue(IssueLevel.ERROR, f"结果落盘失败：{exc}"))


def _perform_run(
    scenario: ScenarioDefinition, dist_root: Path, task_id: str, inputs: dict[str, Any]
):
    """跑一次任务的完整管道，返回 (access, result, evidence_path, run_id)。

    授权 → 建 run 记录 → execute_task_guarded → 更新终态 + 执行日志 →
    last_result.json → 证据包。同步（/api/run-task）与异步（/api/async-run）
    两条入口共用这一个执行体：两条路各自写一遍的代价，就是异步那次运行
    悄悄没有审计链。

    run_id 随返回值吐出——工作台人审复核要绑定到具体这次运行（运行粒度
    审计），前端需要拿到它。record_run 失败时为 None。

    access.allowed 为 False 时不执行、不消耗，返回 (access, None, None, None)。
    result 永不为 None（除被拒绝那条路径）——引擎自身的意外异常已经被
    execute_task_guarded / crash_result 兜成 FAILED RunResult。
    """
    store = StateStore(dist_root / "storage" / "state.db")
    access = check_access()
    if not access.allowed:
        store.close()
        return access, None, None, None

    # V2.2: runtime 构造 + 创建 run 记录（checkpoint 需要）都可能失败——
    # 失败就没有可用的执行环境，直接落到崩溃兜底。先记 run 再构造 runtime，
    # 这样 run_id 一定拿得到，终态也一定收得回去（不会留下卡死在 RUNNING
    # 的孤儿记录）。
    try:
        run_id = store.record_run("RUNNING", task_id=task_id)
    except Exception as exc:  # noqa: BLE001 —— 连 run_log 都写不进去
        run_id = None
        result = crash_result(task_id, "record_run", exc)
    else:
        try:
            runtime = EngineRuntimeImpl(scenario.name, dist_root, store)
            # 顶层崩溃边界：兜住引擎自身的意外异常，与 CLI（main.py）共用
            # 同一层，防止 HTTP 请求无响应、run_log 卡死。
            result = execute_task_guarded(
                scenario, task_id, runtime, inputs, store=store, run_id=run_id,
            )
        except Exception as exc:  # noqa: BLE001 —— EngineRuntimeImpl 构造等罕见失败
            result = crash_result(task_id, "runtime_setup", exc)

    # V2.2: 更新终态（记账失败不影响已经拿到手的 result，最坏只是没留痕）
    if run_id is not None:
        try:
            store.update_run_state(
                run_id, result.status.value, human_summary(scenario, result),
            )
            _persist_execution_log(store, run_id, result)
        except Exception as exc:  # noqa: BLE001 —— 记账失败不影响已到手的结果,但留痕
            print(f"[degraded] web 终态记账失败: {exc!r}", file=sys.stderr)
    store.close()

    fingerprints = _input_fingerprints(scenario, task_id, result.inputs)
    _write_last_result(scenario, dist_root, result, fingerprints, run_id=run_id)

    # 档位特性 evidence_pack：与 CLI 同口径的自动审计证据包
    # （工作台跑的也有审计链；低档位返回 None）
    try:
        evidence_path = _write_run_evidence(dist_root, scenario, result, fingerprints)
    except Exception:  # noqa: BLE001
        evidence_path = None

    return access, result, evidence_path, run_id


# ---------------------------------------------------------------- 异步运行队列
# /api/async-run 秒回 run_id，进度与结果经 /api/queue 查询——给宿主 Agent
# 用（工作台前端仍走同步的 /api/run-task，任务秒级完成时不必轮询）。
# 这里只是调度外壳，执行体与同步路径是同一个 _perform_run。

_queue_lock = threading.Lock()
_queue_seq = itertools.count(1)
_queue_runs: dict[int, dict[str, Any]] = {}   # run_id -> {id, task, state, started_at, result?}


def _queue_put(task_id: str) -> int:
    with _queue_lock:
        rid = next(_queue_seq)
        _queue_runs[rid] = {
            "id": rid, "task": task_id, "state": "running",
            "started_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        }
        return rid


def _queue_finish(rid: int, state: str, payload: dict[str, Any]) -> None:
    with _queue_lock:
        entry = _queue_runs.get(rid)
        if entry is None:
            return
        entry["state"] = state
        entry["finished_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
        entry["result"] = payload


def _run_async(scenario: ScenarioDefinition, dist_root: Path, task_id: str,
               inputs: dict[str, Any], rid: int) -> None:
    """后台线程跑一次任务：授权/执行/记账/审计链与同步路径同一套逻辑。"""
    try:
        access, result, evidence_path, _run_id = _perform_run(
            scenario, dist_root, task_id, inputs)
    except Exception as exc:  # noqa: BLE001 —— 线程内必须兜住，否则队列条目永远停在 running
        _queue_finish(rid, "FAILED", {
            "state": "FAILED",
            "issues": [{"level": "error",
                        "message": f"引擎内部错误（async_run）：{type(exc).__name__}: {exc}"}],
        })
        return
    if result is None:
        _queue_finish(rid, "DENIED", {
            "state": "DENIED",
            "issues": [{"level": "error", "message": access.message}],
        })
        return
    _queue_finish(rid, result.status.value, {
        "state": result.status.value,
        "outputs": result.outputs,
        "issues": _issue_dicts(result.issues),
        "access_message": access.message,
        "evidence_pack": str(evidence_path) if evidence_path else "",
    })


def _task_schema(scenario: ScenarioDefinition) -> list[dict[str, Any]]:
    """把任务契约序列化成前端可直接渲染的结构。"""
    return [
        {
            "task_id": t.task_id,
            "label": t.label,
            "description": t.description,
            "input_fields": [
                {
                    "field_id": f.field_id,
                    "label": f.label,
                    "kind": f.kind.value,
                    "required": f.required,
                    "default": f.default,
                    "choices": list(f.choices),
                    "help_text": f.help_text,
                }
                for f in t.input_fields
            ],
        }
        for t in scenario.tasks
    ]


_REVIEW_VERDICTS = ("adopt", "edit", "reject")
_REVIEW_MAX_REASON = 500


def _parse_run_id_qs(qs: dict[str, list[str]]) -> int | None:
    """从 query string 里解析 run_id（可选）。非空但非法时返回 None（与"未给"
    等价，路径级已保证至少给了 task）；它能容忍前端拼坏的数字。"""
    raw = qs.get("run_id", [""])[0].strip()
    if not raw:
        return None
    try:
        return int(raw)
    except ValueError:
        return None


# MIME 类型映射（静态文件服务用）
_MIME_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "application/javascript; charset=utf-8",
    ".json": "application/json; charset=utf-8",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".svg": "image/svg+xml",
    ".ico": "image/x-icon",
}


class _WorkbenchHandler(BaseHTTPRequestHandler):
    """工作台 HTTP 请求处理器。所有端点都在这一个类里。"""

    # 由 run_server 注入
    dist_root: Path = None  # type: ignore
    scenario: ScenarioDefinition = None  # type: ignore

    # 连接空闲超时（秒）：一个连接过来了却一直不发完整请求（探活探测、
    # 客户端异常挂起等）会卡住 rfile.readline()。ThreadingHTTPServer 下它
    # 不再饿死别的请求，但这条线程和 socket 会一直挂着不放——单人本机工具
    # 也要有这层保护。BaseHTTPRequestHandler 对 socket.timeout 有现成的兜底
    # （记日志、标记 close_connection、继续），只差设置这个值。
    timeout = 30

    def log_message(self, format, *args):
        # 静默普通请求日志，只保留错误
        pass

    # ---- 响应工具 ----

    def _send_json(self, data: Any, status: int = 200) -> None:
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_file(self, path: Path) -> None:
        if not path.is_file():
            self.send_error(404, "Not Found")
            return
        suffix = path.suffix.lower()
        mime = _MIME_TYPES.get(suffix, "application/octet-stream")
        data = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", mime)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _read_body(self) -> dict:
        length = int(self.headers.get("Content-Length", 0))
        if length == 0:
            return {}
        raw = self.rfile.read(length)
        return json.loads(raw)

    # ---- GET 路由 ----

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/") or "/"

        if path == "/":
            self._send_file(self.dist_root / "web" / "index.html")
        elif path == "/api/status":
            self._handle_status()
        elif path == "/api/history":
            self._handle_history()
        elif path == "/api/last-result":
            self._handle_last_result()
        elif path == "/api/files":
            self._handle_files()
        elif path == "/api/review":
            self._handle_review_list()
        elif path == "/api/resumable":
            self._handle_resumable()
        elif path == "/api/queue":
            self._handle_queue()
        elif path.startswith("/web/"):
            # 静态文件：/web/app.js → dist_root/web/app.js
            rel = path[len("/web/"):]
            web_dir = self.dist_root / "web"
            target = (web_dir / rel).resolve()
            # 安全检查：不能跳出 web 目录
            if str(target).startswith(str(web_dir.resolve())):
                self._send_file(target)
            else:
                self.send_error(403, "Forbidden")
        else:
            self.send_error(404, "Not Found")

    # ---- POST 路由 ----

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/") or "/"

        if path == "/api/run-task":
            self._handle_run_task()
        elif path == "/api/async-run":
            self._handle_async_run()
        elif path == "/api/review":
            self._handle_review_submit()
        elif path == "/api/resume":
            self._handle_resume()
        elif path == "/api/files/open":
            self._handle_files_open()
        else:
            self.send_error(404, "Not Found")

    # ---- 端点实现 ----

    def _handle_status(self) -> None:
        store = StateStore(self.dist_root / "storage" / "state.db")
        access = check_access()
        last = store.last_run()
        store.close()
        self._send_json({
            "scenario": {
                "name": self.scenario.name,
                "display_name": self.scenario.display_name,
                "version": self.scenario.version,
                "description": self.scenario.description,
            },
            "tasks": _task_schema(self.scenario),
            "allowed": access.allowed,
            "message": access.message,
            "last_run": (
                {"ran_at": last[0], "task_id": last[1], "state": last[2]}
                if last else None
            ),
        })

    def _handle_run_task(self) -> None:
        payload = self._read_body()
        task_id = str(payload.get("task", ""))
        inputs = payload.get("inputs") or {}
        # 未知任务 404 前置拦截（与 /api/async-run 一致）——不能落进执行链路
        # 留下 task="" 的垃圾 FAILED run 记录污染 state.db 与 last_result.json
        if self.scenario.task(task_id) is None:
            self._send_json({"ok": False, "message": f"未知任务：{task_id}"}, status=404)
            return

        # 上传的文件字节先落盘、换成路径再校验格式——损坏的 base64、
        # 超出大小上限的文件不该流进执行链路。
        try:
            inputs = _materialize_uploaded_files(self.dist_root, inputs)
        except ValueError as exc:
            self._send_json({"ok": False, "message": str(exc)}, status=400)
            return

        access, result, evidence_path, run_id = _perform_run(
            self.scenario, self.dist_root, task_id, inputs)
        if result is None:
            self._send_json({"ok": False, "message": access.message}, status=403)
            return

        self._send_json({
            "ok": result.status.value != "FAILED",
            "state": result.status.value,
            "task_id": result.task_id,
            "run_id": run_id,
            "outputs": result.outputs,
            "issues": _issue_dicts(result.issues),
            "access_message": access.message,
            "evidence_pack": str(evidence_path) if evidence_path else "",
        })

    def _handle_queue(self) -> None:
        """GET /api/queue —— 异步运行队列（新在前）。"""
        with _queue_lock:
            runs = list(_queue_runs.values())
        runs.reverse()
        self._send_json({"runs": runs})

    def _handle_async_run(self) -> None:
        """POST /api/async-run —— 异步跑一次：秒回 run_id，进度查 /api/queue。

        上传字段的落盘同样在起线程前做完——400 要在这个请求里返回，
        不能等后台线程去拒。
        """
        payload = self._read_body()
        task_id = str(payload.get("task", ""))
        inputs = payload.get("inputs") or {}
        if self.scenario.task(task_id) is None:
            self._send_json({"ok": False, "message": f"未知任务：{task_id}"}, status=404)
            return
        try:
            inputs = _materialize_uploaded_files(self.dist_root, inputs)
        except ValueError as exc:
            self._send_json({"ok": False, "message": str(exc)}, status=400)
            return
        rid = _queue_put(task_id)
        threading.Thread(
            target=_run_async,
            args=(self.scenario, self.dist_root, task_id, inputs, rid),
            daemon=True,
        ).start()
        self._send_json({"ok": True, "run_id": rid, "state": "running"})

    def _handle_history(self) -> None:
        store = StateStore(self.dist_root / "storage" / "state.db")
        runs = store.list_runs(limit=20)
        store.close()
        self._send_json({
            "runs": [
                {"ran_at": r[0], "task_id": r[1], "state": r[2], "summary": r[3]}
                for r in runs
            ]
        })

    def _handle_last_result(self) -> None:
        path = self.dist_root / "storage" / "last_result.json"
        if not path.exists():
            self._send_json({"ok": False, "message": "还没有运行记录"})
            return
        self._send_json({"ok": True, "result": json.loads(path.read_text(encoding="utf-8"))})

    def _handle_files(self) -> None:
        self._send_json(list_directory_tree(self.dist_root))

    def _handle_files_open(self) -> None:
        payload = self._read_body()
        target = str(payload.get("path") or payload.get("rel_path") or "")
        ok = open_in_explorer(self.dist_root, target)
        self._send_json({"ok": ok})

    def _handle_review_list(self) -> None:
        """GET /api/review?task=<task_id>&run_id=<run_id> —— 回读本地复核记录。

        可只按 task、只按 run_id、或两者组合过滤，最新在前。辅助工作台本地
        面板即可做到运行粒度回溯。
        """
        qs = parse_qs(urlparse(self.path).query)
        task = qs.get("task", [""])[0].strip()
        run_id = _parse_run_id_qs(qs)
        if not task and run_id is None:
            self._send_json({"ok": False, "message": "缺少 task 或 run_id"}, status=400)
            return
        store = StateStore(self.dist_root / "storage" / "state.db")
        try:
            reviews = store.list_reviews(task_id=task or None, run_id=run_id)
        finally:
            store.close()
        self._send_json({"ok": True, "task": task, "run_id": run_id, "reviews": reviews})

    def _handle_review_submit(self) -> None:
        """POST /api/review —— 把工作台人审三键的 verdict 落库到 review_log。

        优先绑定前端回传的 run_id（本次运行粒度）；run_id 缺失时回退到最近
        一次运行的 task_id（向后兼容 last-result / resume 等无 run 上下文的
        渲染路径），此时该条复核 run_id 为空。verdict 白名单校验、理由限长，
        防止把垃圾数据写进复核台账。
        """
        payload = self._read_body()
        verdict = str(payload.get("verdict", ""))
        if verdict not in _REVIEW_VERDICTS:
            self._send_json({"ok": False, "message": f"非法 verdict：{verdict}"}, status=400)
            return
        reason = str(payload.get("reason", "")).strip() or "（未填写）"
        if len(reason) > _REVIEW_MAX_REASON:
            reason = reason[:_REVIEW_MAX_REASON]

        store = StateStore(self.dist_root / "storage" / "state.db")
        try:
            run_id_raw = payload.get("run_id")
            run_id = None
            if run_id_raw not in (None, ""):
                try:
                    run_id = int(run_id_raw)
                except (TypeError, ValueError):
                    self._send_json({"ok": False, "message": f"非法 run_id：{run_id_raw}"}, status=400)
                    return
                if store.run_task_id(run_id) is None:
                    self._send_json(
                        {"ok": False, "message": f"run_id={run_id} 不存在"}, status=400)
                    return

            task = str(payload.get("task", "")).strip()
            if not task:
                task = store.run_task_id(run_id) if run_id else None
            if not task:
                last = store.last_run()
                task = last[1] if last else ""
            if not task:
                self._send_json({"ok": False, "message": "缺少 task"}, status=400)
                return

            store.record_review(run_id, task, verdict, reason)
            reviews = store.list_reviews(task_id=task)
        finally:
            store.close()
        self._send_json({"ok": True, "run_id": run_id, "task": task, "reviews": reviews})

    def _handle_resumable(self) -> None:
        """V2.2: GET /api/resumable —— 列出可恢复的运行。"""
        store = StateStore(self.dist_root / "storage" / "state.db")
        resumable = store.list_resumable(limit=20)
        store.close()
        self._send_json({
            "ok": True,
            "resumable": [
                {
                    "run_id": r[0],
                    "ran_at": r[1],
                    "task_id": r[2],
                    "state": r[3],
                    "summary": r[4],
                    "next_step": r[5],
                    "checkpoint_at": r[6],
                }
                for r in resumable
            ],
        })

    def _handle_resume(self) -> None:
        """V2.2: POST /api/resume —— 从检查点恢复执行。"""
        payload = self._read_body()
        run_id = payload.get("run_id")

        store = StateStore(self.dist_root / "storage" / "state.db")

        # 确定 run_id
        if run_id is None:
            resumable = store.list_resumable(limit=1)
            if not resumable:
                store.close()
                self._send_json({"ok": False, "message": "没有可恢复的运行"}, status=404)
                return
            run_id = resumable[0][0]

        # 授权检查
        access = check_access()
        if not access.allowed:
            store.close()
            self._send_json({"ok": False, "message": access.message}, status=403)
            return

        # 加载 checkpoint 获取 task_id
        checkpoint = store.load_latest_checkpoint(run_id)
        if checkpoint is None:
            store.close()
            self._send_json({"ok": False, "message": f"run_id={run_id} 无可用检查点"}, status=404)
            return

        task_id = store.run_task_id(run_id) or ""
        if not task_id:
            store.close()
            self._send_json({"ok": False, "message": f"run_id={run_id} 无关联任务"}, status=400)
            return

        # 更新 run_log 状态为 RUNNING——只是状态展示，失败不影响真正的恢复执行
        try:
            store.update_run_state(run_id, "RUNNING", "恢复中...")
        except Exception as exc:  # noqa: BLE001
            print(f"[degraded] web resume 状态置 RUNNING 失败: {exc!r}", file=sys.stderr)

        # runtime 构造失败（目录权限等）同样要落到崩溃兜底，不能让 HTTP
        # 请求无响应；resume_task_guarded 已经兜住引擎自身的意外异常。
        try:
            runtime = EngineRuntimeImpl(self.scenario.name, self.dist_root, store)
            result = resume_task_guarded(self.scenario, task_id, runtime, store, run_id)
        except Exception as exc:  # noqa: BLE001
            result = crash_result(task_id, "resume_runtime_setup", exc)

        try:
            store.update_run_state(
                run_id, result.status.value,
                human_summary(self.scenario, result),
            )
            _persist_execution_log(store, run_id, result)
        except Exception as exc:  # noqa: BLE001 —— 顶层崩溃边界,留痕不阻断
            print(f"[degraded] web resume 终态记账失败: {exc!r}", file=sys.stderr)
        finally:
            store.close()

        _fingerprints = _input_fingerprints(self.scenario, task_id, result.inputs)

        # last_result.json 必须在 resume 后也刷新——否则"查看最近一次运行
        # 核验"会一直停在恢复前的 FAILED 快照，明明这次已经恢复成功。
        _write_last_result(self.scenario, self.dist_root, result, _fingerprints,
                           extra={"resumed": result.resumed}, run_id=run_id)

        # 档位特性 evidence_pack：恢复的运行同样落审计证据包（跑完即落）
        try:
            evidence_path = _write_run_evidence(self.dist_root, self.scenario, result, _fingerprints)
        except Exception:  # noqa: BLE001
            evidence_path = None

        self._send_json({
            "ok": result.status.value != "FAILED",
            "state": result.status.value,
            "task_id": task_id,  # 前端渲染结果后如果又失败，还能再提供一次"继续恢复"入口
            "run_id": run_id,
            "resumed": result.resumed,
            "resumed_from_step": result.resumed_from_step,
            "outputs": result.outputs,
            "issues": _issue_dicts(result.issues),
            "access_message": access.message,
            "evidence_pack": str(evidence_path) if evidence_path else "",
        })


def _open_browser_later(url: str, delay_seconds: float = 1.0) -> None:
    def _open():
        time.sleep(delay_seconds)
        webbrowser.open(url)
    threading.Thread(target=_open, daemon=True).start()


def _pick_port(preferred: int, attempts: int = 10) -> int:
    """找一个当前能绑定的端口。三个产品的工作台默认都是 8765，客户
    同时开两个时第二个会撞端口——占住就顺延，别崩。"""
    for candidate in range(preferred, preferred + attempts):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
            try:
                probe.bind(("127.0.0.1", candidate))
            except OSError:
                continue
            return candidate
    return preferred


def run_server(dist_root: Path, port: int, scenario: ScenarioDefinition) -> None:
    """启动本地工作台。接口与 FastAPI 版完全一致（dist_root, port, scenario）。"""
    actual = _pick_port(port)
    if actual != port:
        print(f"端口 {port} 已被占用（可能开着另一个工作台），本产品改用 {actual}。")
    url = f"http://127.0.0.1:{actual}/"

    # 注入配置到 Handler 类
    _WorkbenchHandler.dist_root = dist_root
    _WorkbenchHandler.scenario = scenario

    # ThreadingHTTPServer：单线程版会被浏览器的 keep-alive 连接占死，
    # 第二个请求（哪怕只是拉一个静态资源）全部饿死——实测抓到。
    # 一次长任务占住的是它自己那条连接，其余请求照常响应。
    server = ThreadingHTTPServer(("127.0.0.1", actual), _WorkbenchHandler)
    print(f"正在启动本地工作台：{scenario.display_name} ...")
    _open_browser_later(url)
    print(f"[OK] 服务已启动，浏览器即将打开：{url}")
    print("关闭这个窗口即可停止服务。")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("[degraded] 工作台服务被手动中断(Ctrl+C),正常收尾", file=sys.stderr)
    finally:
        server.server_close()
