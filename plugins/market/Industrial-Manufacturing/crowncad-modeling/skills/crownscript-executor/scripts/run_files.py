"""单文档任务的本地资料管理。没有网络、CAD 写入或自动重发能力。

正式路径按用途固定；每次持锁更新、单文件原子替换，最后提交状态。
多文件更新中断会留下可检测的不配套现场，不承诺跨文件事务恢复。
资料格式由本模块初始化并校验，调用方不选择格式编号或手写状态。
"""

from __future__ import annotations

import argparse
import base64
import errno
import hashlib
import io
import json
import math
import os
import re
import stat
import sys
import tempfile
import time
import warnings
import zipfile
from collections.abc import Mapping
from contextlib import contextmanager
from copy import deepcopy
from pathlib import Path, PurePosixPath
from uuid import UUID, uuid4


# 内部存储协议；初始化、读取和机器可读返回使用同一个值。
_LAYOUT_VERSION = 1

FIXED_PATHS = {
    "request": "runtime/request.json",
    "submitted_code": "runtime/submitted.crownscript.js",
    "response": "runtime/response.json",
    "state": "runtime/state.json",
    "document": "runtime/document.json",
    "topology": "evidence/topology.json",
    "geometry": "evidence/geometry.json",
    "verification_json": "reports/verification.json",
    "verification_md": "reports/verification.md",
}
PURPOSE = re.compile(r"[a-z0-9][a-z0-9_-]{0,63}\Z")
TASK_NAME = re.compile(r'[^.\s][^\x00-\x1f<>:"/\\|?*]*__[0-9a-fA-F]{8}\Z')
SHA256 = re.compile(r"[0-9a-f]{64}\Z")
IMAGE_TYPES = {"PNG": ".png", "JPEG": ".jpg", "WEBP": ".webp"}
DYNAMIC_DIRS = {
    "crop": "analysis/crops", "reference_view": "analysis/reference-views",
    "view": "evidence/views", "query": "evidence/queries", "bundle": "evidence/bundles",
}
SCOPES = {"input_analysis", "current_model", "required_process"}
EXECUTION_STATUSES = {None, "awaiting_result", "responded", "failed", "unknown"}
VERIFICATION_STATUSES = {"not_run", "stale", "passed", "failed", "unverified"}
MAX_DATA_BYTES = 64 * 1024 * 1024
MAX_STDIN_BYTES = 2 * MAX_DATA_BYTES
MAX_UNPACKED_BYTES = 128 * 1024 * 1024
MAX_ENTRY_BYTES = 32 * 1024 * 1024
MAX_IMAGE_PIXELS = 16_000_000
ARCHIVE_SUFFIXES = {".json", ".jsonl", ".txt", ".log", ".js", ".py", ".png", ".jpg", ".webp"}
CAD_TOOLS = {"collect_topology", "query_topology_geometry", "resolve_sketch_plane", "capture_viewport"}
RESERVED_NAMES = {"CON", "PRN", "AUX", "NUL", *(f"COM{i}" for i in range(1, 10)),
                  *(f"LPT{i}" for i in range(1, 10))}


class RunFilesError(ValueError):
    """本地路径、来源或资料状态不符合运行约定。"""


def _digest(data):
    return hashlib.sha256(data).hexdigest()


def _assert_plain(path):
    # resolve 前检查，包括不存在的叶子的现存祖先。
    for item in (path, *path.parents):
        if os.path.lexists(item):
            info = os.lstat(item)
            if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & 1024:
                raise RunFilesError(f"拒绝链接或重解析点：{item}")


def _relative(value):
    if (not isinstance(value, str) or not value or "\\" in value or ":" in value
            or value.startswith("/") or any(p in {"", ".", ".."} for p in value.split("/"))):
        raise RunFilesError("要求安全的任务内正斜杠相对路径")
    for part in value.split("/"):
        if (re.search(r'[\x00-\x1f<>"|?*]', part) or part.endswith((" ", "."))
                or part.split(".")[0].upper() in RESERVED_NAMES):
            raise RunFilesError("文件名包含不允许的字符或保留名称")
    return PurePosixPath(value)


def _validate_root(root):
    root = Path(root).absolute()
    _assert_plain(root)
    if (not root.is_dir() or not TASK_NAME.fullmatch(root.name)
            or root.name.split("__")[0].endswith((" ", "."))
            or root.parent.name.casefold() != "runs" or root.parent.parent.name.casefold() != "generated"):
        raise RunFilesError("只接受 generated/runs/<语义>__<8位UUID> 的直接任务目录")
    return root.resolve(strict=True)


def _checked_path(root, relative):
    root = Path(root)
    path = root.joinpath(*_relative(relative).parts)
    _assert_plain(path)
    if not path.resolve().is_relative_to(root.resolve()):
        raise RunFilesError("路径超出本任务目录")
    if path.exists() and not path.is_file():
        raise RunFilesError(f"文件槽不是普通文件：{relative}")
    return path


def _reject_constant(value):
    raise RunFilesError("JSON 不允许 NaN/Infinity")


def _json_load(data):
    try:
        if isinstance(data, bytes):
            data = data.decode("utf-8-sig")
        def finite_float(value):
            result = float(value)
            if not math.isfinite(result):
                raise RunFilesError("JSON 不允许超出有限范围的数值")
            return result
        return json.loads(data, parse_constant=_reject_constant, parse_float=finite_float)
    except (UnicodeError, json.JSONDecodeError, TypeError) as error:
        raise RunFilesError("无法读取有效 UTF-8 JSON") from error


def _json_bytes(value):
    try:
        return (json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n").encode("utf-8")
    except (TypeError, ValueError, UnicodeError) as error:
        raise RunFilesError("不能保存无效 JSON 数据") from error


def _document(value):
    if (not isinstance(value, dict) or value.get("doc_type") != "PartDocument"
            or any(not isinstance(value.get(k), str) or not value[k].strip()
                   for k in ("document_id", "version_id"))):
        raise RunFilesError("要求已确认的单一 PartDocument 文档上下文")
    return {key: value[key] for key in ("document_id", "version_id", "doc_type")}


def _valid_uuid(value):
    try:
        return isinstance(value, str) and str(UUID(value)) == value
    except (ValueError, AttributeError):
        return False


def _managed_path(kind, purpose, suffix=""):
    if not isinstance(purpose, str) or not PURPOSE.fullmatch(purpose):
        raise RunFilesError("用途只接受小写字母、数字、下划线和短横线，最长64字符")
    if kind in FIXED_PATHS and kind != "state":
        if purpose != "main":
            raise RunFilesError("固定主查询和运行文件的 purpose 必须为 main")
        return FIXED_PATHS[kind]
    if kind not in DYNAMIC_DIRS:
        raise RunFilesError("未知文件类别")
    allowed = {".json"} if kind == "query" else {".zip"} if kind == "bundle" else set(IMAGE_TYPES.values())
    if suffix not in allowed:
        raise RunFilesError("文件扩展名不属于该用途")
    return f"{DYNAMIC_DIRS[kind]}/{purpose}{suffix}"


def _temporary_path(relative):
    path = _relative(relative)
    return (str(path).startswith((".work/input/", ".work/extracted/"))
            and path.suffix in ARCHIVE_SUFFIXES)


def _read_state(root):
    path = _checked_path(root, FIXED_PATHS["state"])
    if not path.is_file():
        raise RunFilesError("任务缺少运行状态；请通过 init 新建任务，不自动接管已有目录")
    state = _json_load(path.read_bytes())
    if not isinstance(state, dict) or type(state.get("layout_version")) is not int:
        raise RunFilesError("运行状态损坏，不允许回退成新任务")
    if state["layout_version"] != _LAYOUT_VERSION:
        raise RunFilesError("运行资料格式不受当前程序支持；保留目录，不自动迁移或覆盖")
    if (type(state.get("awaiting_result")) is not bool
            or not isinstance(state.get("execution_status"), (str, type(None)))
            or state.get("execution_status") not in EXECUTION_STATUSES
            or not isinstance(state.get("verification_status"), str)
            or state.get("verification_status") not in VERIFICATION_STATUSES
            or not isinstance(state.get("managed_files"), dict)):
        raise RunFilesError("运行状态损坏，不允许回退成新任务")
    operation_id = state.get("operation_id")
    if operation_id is not None and not _valid_uuid(operation_id):
        raise RunFilesError("运行状态的本地操作编号无效")
    if state.get("document") is not None:
        _document(state["document"])
    if operation_id is not None and (state.get("document") is None
            or not isinstance(state.get("submitted_sha256"), str)
            or not SHA256.fullmatch(state["submitted_sha256"])):
        raise RunFilesError("执行状态缺少配套文档或提交指纹")
    if ((state["execution_status"] is None) != (operation_id is None)
            or state["awaiting_result"] != (state["execution_status"] == "awaiting_result")):
        raise RunFilesError("运行状态的等待标记不配套")
    fingerprints = state.get("input_fingerprint")
    if not isinstance(fingerprints, dict) or set(fingerprints) != {"source", "parameters", "requirements"}:
        raise RunFilesError("输入指纹结构无效")
    for key, digest in fingerprints.items():
        if digest is None and (operation_id is None or key == "parameters"):
            continue
        if not isinstance(digest, str) or not SHA256.fullmatch(digest):
            raise RunFilesError("输入指纹无效")
    for relative, entry in state["managed_files"].items():
        _checked_path(root, relative)
        if (not isinstance(entry, dict) or not isinstance(entry.get("sha256"), str)
                or not SHA256.fullmatch(entry["sha256"]) or not isinstance(entry.get("scope"), str)
                or entry.get("scope") not in SCOPES or not isinstance(entry.get("kind"), str)
                or not isinstance(entry.get("status"), str)
                or entry.get("status") not in {"valid", "stale", "superseded", "cleanup_failed"}
                or not isinstance(entry.get("source"), dict)):
            raise RunFilesError("受管文件登记损坏")
        if entry.get("kind") == "temporary":
            if not _temporary_path(relative):
                raise RunFilesError("临时文件登记越界")
        elif _managed_path(entry.get("kind"), entry.get("purpose"), Path(relative).suffix) != relative:
            raise RunFilesError("受管文件路径与用途不配套")
    return state


@contextmanager
def _task_lock(root, timeout=15, *, _initializing=False):
    root = _validate_root(root)
    if not _initializing:
        # 旧布局在失败前也不能新增 runtime/ 或锁文件。
        _read_state(root)
    path = _checked_path(root, "runtime/workspace.lock")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a+b") as handle:
        if os.fstat(handle.fileno()).st_size == 0:
            handle.write(b"\0")
            handle.flush()
        deadline = time.monotonic() + timeout
        while True:
            try:
                handle.seek(0)
                if os.name == "nt":
                    import msvcrt
                    msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
                else:
                    import fcntl
                    fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except OSError as error:
                if error.errno not in {errno.EACCES, errno.EAGAIN, errno.EDEADLK}:
                    raise
                if time.monotonic() >= deadline:
                    raise RunFilesError("等待任务文件锁超时") from error
                time.sleep(min(0.05, max(0, deadline - time.monotonic())))
        try:
            yield
        finally:
            handle.seek(0)
            if os.name == "nt":
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def _atomic_write(path, data: bytes):
    """失败时保留旧正式文件及唯一临时现场，不退回截断覆盖。"""
    path = Path(path)
    _assert_plain(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=path.parent, prefix="run-files-", suffix=".tmp",
                                     delete=False) as handle:
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())
        temporary = handle.name
    os.replace(temporary, path)


def _write_state(root, state):
    _atomic_write(_checked_path(root, FIXED_PATHS["state"]), _json_bytes(state))


def _verify_files(root, state, *, allow_modified_replaced=False):
    for relative, entry in state["managed_files"].items():
        # 只读兼容旧任务的中转登记；新入口不再产生这种登记。
        if entry["kind"] == "temporary":
            continue
        if (allow_modified_replaced and entry["status"] != "valid"
                and entry["kind"] not in FIXED_PATHS and entry["scope"] != "required_process"
                and relative not in _report_refs(state)):
            continue
        path = _checked_path(root, relative)
        if not path.is_file() or _digest(path.read_bytes()) != entry["sha256"]:
            raise RunFilesError(f"文件与状态指纹不配套：{relative}")
    for kind, relative in FIXED_PATHS.items():
        if kind != "state" and _checked_path(root, relative).exists() and relative not in state["managed_files"]:
            raise RunFilesError(f"正式文件未完成登记，资料不配套：{relative}")


def _fingerprint_inputs(root):
    source = _checked_path(root, "model.crownscript.js").read_bytes()
    try:
        if not source.decode("utf-8").strip():
            raise RunFilesError("完整源码不能为空")
    except UnicodeError as error:
        raise RunFilesError("完整源码必须是 UTF-8") from error
    graph_data = _checked_path(root, "operation_graph.json").read_bytes()
    graph = _json_load(graph_data)
    if (not isinstance(graph, dict) or not isinstance(graph.get("requirements"), list)
            or not all(isinstance(item, dict)
                       and all(isinstance(item.get(key), str) and item[key].strip()
                               for key in ("id", "title", "kind", "stage"))
                       and ("required" not in item or type(item["required"]) is bool)
                       for item in graph["requirements"])):
        raise RunFilesError("新任务操作图需要公共 verification 可读的 requirements 列表")
    if len({item["id"] for item in graph["requirements"]}) != len(graph["requirements"]):
        raise RunFilesError("检查项编号不能重复")
    parameters = _checked_path(root, "parameters.json")
    parameter_data = parameters.read_bytes() if parameters.exists() else None
    if parameter_data is not None:
        _json_load(parameter_data)
    return {"source": _digest(source), "parameters": _digest(parameter_data) if parameter_data is not None else None,
            "requirements": _digest(graph_data)}


def _redact(value):
    if isinstance(value, Mapping):
        result = {}
        for key, item in value.items():
            normal = re.sub(r"[^a-z0-9]", "", str(key).lower())
            if (normal in {"authorization", "cookie", "setcookie", "downloadurl", "apikey", "password",
                           "credential", "credentials"} or normal.endswith(("token", "secret", "apikey", "authorization", "cookie", "password", "credentials"))):
                result[str(key)] = "[redacted]"
            else:
                result[str(key)] = _redact(item)
        return result
    if isinstance(value, (list, tuple)):
        return [_redact(item) for item in value]
    if isinstance(value, str):
        if re.search(r"(?i)\b(?:bearer|basic)\s+\S+|(?:api[_-]?key|token|secret|password)\s*[:=]\s*\S+", value):
            return "[redacted sensitive detail]"
        return re.sub(r"https?://[^\s<>\"']+", "[redacted URL]", value)
    return value


def _register(state, relative, kind, purpose, data, source, scope, *, status="valid"):
    state["managed_files"][relative] = {
        "kind": kind, "purpose": purpose, "sha256": _digest(data), "source": _redact(source),
        "operation_id": state["operation_id"], "scope": scope, "status": status,
    }


def _invalidate_report(state):
    state["verification_status"] = "stale"
    for entry in state["managed_files"].values():
        if entry["kind"] in {"verification_json", "verification_md"}:
            entry["status"] = "stale"


def _inputs_match(root, state):
    try:
        matches = _fingerprint_inputs(root) == state["input_fingerprint"]
    except (RunFilesError, OSError) as error:
        _invalidate_report(state)
        _write_state(root, state)
        raise RunFilesError("无法核对当前输入，旧检查已过期") from error
    if not matches:
        _invalidate_report(state)
        _write_state(root, state)
        raise RunFilesError("源码、参数或要求已变化，旧证据不能作为当前设计检查")


def _init_task(workspace, name):
    workspace = Path(workspace).absolute()
    _assert_plain(workspace)
    if not workspace.is_dir():
        raise RunFilesError("工程根目录不存在")
    if (not isinstance(name, str) or not name or name.startswith(".") or name[0].isspace()
            or name.endswith((" ", ".")) or re.search(r'[\x00-\x1f<>:"/\\|?*]', name)):
        raise RunFilesError("任务语义名称无效")
    _relative(name)
    parent = workspace / "generated" / "runs"
    _assert_plain(parent)
    parent.mkdir(parents=True, exist_ok=True)
    root = parent / f"{name}__{uuid4().hex[:8]}"
    root.mkdir(exist_ok=False)
    with _task_lock(root, _initializing=True):
        _write_state(root, {
            "layout_version": _LAYOUT_VERSION, "document": None, "operation_id": None,
            "awaiting_result": False, "execution_status": None,
            "input_fingerprint": {"source": None, "parameters": None, "requirements": None},
            "submitted_sha256": None, "verification_status": "not_run",
            "verification_stage": None, "managed_files": {},
        })
    return root


def _reconciled(root, state):
    record = state.get("reconciliation")
    if not isinstance(record, dict) or record.get("operation_id") != state["operation_id"]:
        return False
    refs = record.get("evidence")
    return bool(refs) and all(
        relative in state["managed_files"]
        and state["managed_files"][relative]["sha256"] == digest
        and _digest(_checked_path(root, relative).read_bytes()) == digest
        for relative, digest in refs.items()
    )


def prepare_execution(
    root: str | Path, *, document: dict, overwrite: bool, code: str, purpose: str,
) -> dict:
    root = _validate_root(root)
    document = _document(document)
    if type(overwrite) is not bool or not isinstance(code, str) or not code.strip():
        raise RunFilesError("overwrite 必须是 bool，实际提交代码必须非空")
    if not isinstance(purpose, str) or not PURPOSE.fullmatch(purpose):
        raise RunFilesError("执行用途无效")
    code_data = code.encode("utf-8")
    if len(code_data) > MAX_DATA_BYTES:
        raise RunFilesError("提交代码超过大小限制")
    with _task_lock(root):
        state = _read_state(root)
        _verify_files(root, state)
        if state["awaiting_result"] or (state["execution_status"] in {"failed", "unknown"}
                                       and not _reconciled(root, state)):
            raise RunFilesError("上一轮仍在等待结果或有未解决写入，先真实回查")
        if state["document"] is not None and state["document"] != document:
            raise RunFilesError("同一任务不能切换文档")
        fingerprint = _fingerprint_inputs(root)
        operation_id = str(uuid4())
        for entry in state["managed_files"].values():
            if entry["scope"] == "current_model" or entry["kind"] == "response":
                entry["status"] = "stale"
        _invalidate_report(state)
        state.update(document=document, operation_id=operation_id, awaiting_result=True,
                     execution_status="awaiting_result", input_fingerprint=fingerprint,
                     submitted_sha256=_digest(code_data), verification_stage=None)
        state.pop("reconciliation", None)
        request = dict(operation_id=operation_id, document=document, overwrite=overwrite,
                       purpose=purpose, submitted_sha256=_digest(code_data), input_fingerprint=fingerprint)
        request_data = _json_bytes(request)
        for kind, data in (("submitted_code", code_data), ("request", request_data)):
            relative = FIXED_PATHS[kind]
            _atomic_write(_checked_path(root, relative), data)
            _register(state, relative, kind, "main", data, {"operation_id": operation_id}, "current_model")
        if _fingerprint_inputs(root) != fingerprint:
            raise RunFilesError("准备期间设计输入变化，请求未就绪；保留现场，不调用 CAD")
        _write_state(root, state)
    return dict(operation_id=operation_id, code=code, code_path=str(root / FIXED_PATHS["submitted_code"]),
                document=document, overwrite=overwrite, input_fingerprint=fingerprint)


def _business_result(result):
    if hasattr(result, "model_dump"):
        result = result.model_dump(mode="json")
    if isinstance(result, (str, bytes)):
        result = _json_load(result)
    # 不持久化未经脱敏的工具文本。只解析可识别的 JSON 业务数据。
    if not isinstance(result, dict):
        return None, False
    is_error = result.get("isError") is True
    if "code" in result or "errorInfo" in result:
        return result, is_error
    candidates = []
    if isinstance(result.get("structuredContent"), dict):
        candidates.append(result["structuredContent"])
    blocks = result.get("content")
    for block in blocks if isinstance(blocks, list) else []:
        if isinstance(block, dict) and block.get("type") == "text":
            try:
                candidate = _json_load(block.get("text"))
            except RunFilesError:
                continue
            if isinstance(candidate, dict):
                candidates.append(candidate)
    if not candidates or any(item != candidates[0] for item in candidates[1:]):
        return None, is_error
    return candidates[0], is_error


def save_execution_result(
    root: str | Path, *, operation_id: str, result: object, outcome: str,
) -> dict:
    if outcome not in {"responded", "failed", "unknown"}:
        raise RunFilesError("调用结果分类无效")
    root = _validate_root(root)
    payload, is_error = _business_result(result)
    explicit_error = payload is not None and (
        (payload.get("code") is not None and payload["code"] != 200)
        or bool(payload.get("errorInfo"))
        or any(isinstance(item, dict) and item.get("errorInfo")
               for item in (payload.get("data") if isinstance(payload.get("data"), list) else []))
    )
    status = ("failed" if explicit_error else "unknown" if outcome == "unknown" or payload is None
              or is_error or payload.get("code") != 200 else outcome)
    safe_result = _redact(payload) if payload is not None else {"errorType": "unknown_tool_result"}
    response = dict(operation_id=operation_id, execution_status=status, result=safe_result)
    data = _json_bytes(response)
    with _task_lock(root):
        state = _read_state(root)
        _verify_files(root, state)
        if state["operation_id"] != operation_id:
            raise RunFilesError("返回结果的本地操作编号不匹配")
        request = _json_load(_checked_path(root, FIXED_PATHS["request"]).read_bytes())
        submitted = _checked_path(root, FIXED_PATHS["submitted_code"]).read_bytes()
        if (request.get("operation_id") != operation_id
                or request.get("submitted_sha256") != _digest(submitted)
                or state["submitted_sha256"] != _digest(submitted)):
            raise RunFilesError("请求和实际提交代码不配套")
        existing = state["managed_files"].get(FIXED_PATHS["response"])
        if existing and existing["operation_id"] == operation_id:
            if existing["sha256"] != _digest(data):
                raise RunFilesError("同一次操作已有不同返回，不允许覆盖")
            try:
                unchanged = _fingerprint_inputs(root) == state["input_fingerprint"]
            except (RunFilesError, OSError):
                unchanged = False
            if not unchanged:
                _invalidate_report(state)
                _write_state(root, state)
            return {"operation_id": operation_id, "execution_status": state["execution_status"]}
        if not state["awaiting_result"]:
            raise RunFilesError("本次操作已经收尾，不能补写不同结果")
        _atomic_write(_checked_path(root, FIXED_PATHS["response"]), data)
        _register(state, FIXED_PATHS["response"], "response", "main", data,
                  {"operation_id": operation_id}, "current_model")
        state.update(awaiting_result=False, execution_status=status)
        _invalidate_report(state)
        _write_state(root, state)
    return {"operation_id": operation_id, "execution_status": status}


def _image_info(data):
    try:
        from PIL import Image
    except ImportError as error:
        raise RunFilesError("图片验证需要执行器现有的 Pillow 依赖") from error
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(data)) as image:
                width, height = image.size
                fmt = image.format
                if fmt not in IMAGE_TYPES or width * height > MAX_IMAGE_PIXELS or min(width, height) <= 0:
                    raise RunFilesError("图片格式或像素尺寸超出允许范围")
                image.verify()
            with Image.open(io.BytesIO(data)) as image:
                image.load()
        return IMAGE_TYPES[fmt], {"width": width, "height": height, "format": fmt}
    except (OSError, ValueError, Image.DecompressionBombError, Image.DecompressionBombWarning) as error:
        raise RunFilesError("图片无效；只接受真实 PNG/JPEG/WebP") from error


def _zip_entries(data):
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            infos = archive.infolist()
            if len(infos) > 256 or sum(info.file_size for info in infos) > MAX_UNPACKED_BYTES:
                raise RunFilesError("ZIP 条目数或展开大小超限")
            names, files = set(), {}
            for info in infos:
                # Windows ZipInfo.filename 会把反斜杠规范化，必须检查包内原始名称。
                name = info.orig_filename.rstrip("/") if info.is_dir() else info.orig_filename
                relative = _relative(name).as_posix()
                mode = info.external_attr >> 16
                if (relative.casefold() in names or stat.S_ISLNK(mode) or info.flag_bits & 1
                        or info.file_size > MAX_ENTRY_BYTES
                        or (not info.is_dir() and Path(relative).suffix.lower() not in ARCHIVE_SUFFIXES)):
                    raise RunFilesError("ZIP 包含重复、链接、加密、超限或未知类型条目")
                names.add(relative.casefold())
                if not info.is_dir():
                    files[relative] = archive.read(info)  # 校验 CRC，且已限制总展开大小。
            file_names = {name.casefold() for name in files}
            for name in files:
                if any(parent.as_posix().casefold() in file_names
                       for parent in PurePosixPath(name).parents):
                    raise RunFilesError("ZIP 文件与目录路径冲突")
            return files
    except (zipfile.BadZipFile, RuntimeError, NotImplementedError, OSError) as error:
        raise RunFilesError("ZIP 无效或不能安全读取") from error


def _evidence_source(state, kind, source, scope):
    if not isinstance(source, dict) or scope not in SCOPES:
        raise RunFilesError("要求明确的资料来源和 scope")
    if kind == "document":
        if source.get("tool") != "create_document":
            raise RunFilesError("文档角色只接受实际 create_document 返回")
        return
    if scope == "input_analysis":
        if kind not in {"crop", "reference_view", "bundle"} or not SHA256.fullmatch(str(source.get("source_sha256", ""))):
            raise RunFilesError("输入分析必须关联原始来源哈希")
        if kind == "crop":
            crop = source.get("crop")
            if (not isinstance(crop, list) or len(crop) != 4
                    or any(type(v) is not int or v < 0 for v in crop) or min(crop[2:]) == 0):
                raise RunFilesError("裁剪必须记录非负起点和正宽高")
        return
    if (kind in {"crop", "reference_view"} or source.get("tool") not in CAD_TOOLS
            or _document(source.get("document")) != state["document"]
            or source.get("operation_id") != state["operation_id"] or not state["operation_id"]
            or not source.get("coverage")):
        raise RunFilesError("CAD 证据来源、范围或查询前操作编号不匹配")
    reconciliation = source.get("reconciliation") is True
    if reconciliation:
        if scope != "required_process" or kind not in {"query", "topology", "geometry", "bundle"}:
            raise RunFilesError("回查必须是必要过程中的实际只读查询")
    elif state["awaiting_result"] or state["execution_status"] != "responded":
        raise RunFilesError("等待、失败或未知写入后的证据只能用于真实回查")
    if kind == "view" and source["tool"] != "capture_viewport":
        raise RunFilesError("当前模型图必须来自实际 capture_viewport")


def _created_document(payload):
    if not isinstance(payload, dict):
        raise RunFilesError("文档响应不是 JSON 对象")
    if "content" in payload or "structuredContent" in payload:
        payload, failed = _business_result(payload)
        if failed or payload is None:
            raise RunFilesError("创建响应不是可靠的实际业务结果")
    if ((payload.get("code") is not None and payload["code"] != 200) or payload.get("errorInfo")):
        raise RunFilesError("失败的创建响应不能绑定文档")
    # 支持已有创建器返回的蛇形字段及 CrownCAD 原生的驼峰字段。
    for candidate in (payload.get("executionContext"), payload, payload.get("document"),
                      payload.get("data")):
        if isinstance(candidate, dict):
            value = {
                "document_id": candidate.get("document_id", candidate.get("documentId", candidate.get("id"))),
                "version_id": candidate.get("version_id", candidate.get("versionId", candidate.get("activeVersionId"))),
                "doc_type": candidate.get("doc_type", candidate.get("docType", candidate.get("documentType"))),
            }
            if value["document_id"] and value["version_id"] and value["doc_type"]:
                return _document(value)
    raise RunFilesError("创建响应缺少实际文档上下文")


def save_evidence(
    root: str | Path, *, kind: str, purpose: str, data: bytes | bytearray | dict,
    source: dict, scope: str,
) -> Path:
    root = _validate_root(root)
    if kind not in {"crop", "reference_view", "view", "query", "bundle", "topology", "geometry", "document"}:
        raise RunFilesError("未知证据类别")
    if not isinstance(source, dict):
        raise RunFilesError("必须提供实际来源")
    data = bytes(data) if isinstance(data, (bytes, bytearray)) else _json_bytes(data)
    if len(data) > MAX_DATA_BYTES:
        raise RunFilesError("资料大小超限")
    source = deepcopy(source)
    artifact = source.get("artifact")
    if artifact is not None:
        if (not isinstance(artifact, dict) or type(artifact.get("byteSize")) is not int
                or artifact["byteSize"] != len(data) or artifact.get("sha256") != _digest(data)):
            raise RunFilesError("下载大小或 SHA-256 不匹配")
    elif scope != "input_analysis" and kind != "document":
        raise RunFilesError("CAD 下载资料必须带实际 byteSize 和 SHA-256")
    if kind in {"crop", "reference_view", "view"}:
        suffix, dimensions = _image_info(data)
        for key in ("width", "height"):
            expected = source.get(key, artifact.get(key) if isinstance(artifact, dict) else None)
            if expected is not None and (type(expected) is not int or expected != dimensions[key]):
                raise RunFilesError("图片实际尺寸与来源声明不一致")
        source.update(dimensions)
    elif kind == "bundle":
        suffix = ".zip"
        _zip_entries(data)  # 校验条目及内容；不解包写盘，也不执行包内代码。
    else:
        suffix = ".json"
        payload = _json_load(data)
        if not isinstance(payload, dict):
            raise RunFilesError("查询及文档资料必须是 JSON 对象")
        data = _json_bytes(_redact(payload))
    relative = _managed_path(kind, purpose, suffix)
    extract = source.pop("extract", [])
    if not isinstance(extract, list) or extract:
        raise RunFilesError("不支持 ZIP 解包写盘；提取清单只能省略或为空列表")
    with _task_lock(root):
        state = _read_state(root)
        _verify_files(root, state)
        _evidence_source(state, kind, source, scope)
        if scope == "current_model" and kind != "document":
            _inputs_match(root, state)
        if kind == "document":
            document = _created_document(payload)
            if state["document"] is not None and document != state["document"]:
                raise RunFilesError("创建响应属于另一个文档")
            state["document"] = document
        existing = state["managed_files"].get(relative)
        if (existing and existing["sha256"] == _digest(data) and existing["source"] == _redact(source)
                and existing["scope"] == scope and existing["status"] == "valid"
                and (scope == "input_analysis" or existing["operation_id"] == state["operation_id"])
                and not extract):
            return root / relative
        for old_relative, entry in state["managed_files"].items():
            if entry["kind"] == kind and entry["purpose"] == purpose and old_relative != relative:
                entry["status"] = "superseded"
        report_refs = _report_refs(state)
        if relative in report_refs:
            _invalidate_report(state)
        _atomic_write(_checked_path(root, relative), data)
        _register(state, relative, kind, purpose, data, source, scope)
        _write_state(root, state)
    _cleanup_after_publish(root)
    return root / relative


def _report_refs(state):
    entry = state["managed_files"].get(FIXED_PATHS["verification_json"], {})
    return entry.get("source", {}).get("evidence", {})


def _has_live_replacement(root, state, relative, entry):
    """仅删除确已交接的旧副本；stale 或同名覆盖都不能单独作为删除依据。"""
    protected = set(_report_refs(state)) | set(state.get("reconciliation", {}).get("evidence", {}))
    if (entry["status"] not in {"superseded", "cleanup_failed"} or relative in protected
            or entry["kind"] not in DYNAMIC_DIRS or entry["scope"] != "current_model"):
        return False
    old = _checked_path(root, relative)
    if not old.is_file() or _digest(old.read_bytes()) != entry["sha256"]:
        return False
    for replacement, current in state["managed_files"].items():
        if (replacement == relative or current["status"] != "valid"
                or current["operation_id"] != state["operation_id"]
                or any(current[key] != entry[key] for key in ("kind", "purpose", "scope"))):
            continue
        path = _checked_path(root, replacement)
        # 新文件可以已被报告采用；保护它不被删除，不阻止旧副本完成交接。
        if path.is_file() and _digest(path.read_bytes()) == current["sha256"]:
            return True
    return False


def _record_reconciliation(root, operation_id, evidence_refs, reason):
    root = _validate_root(root)
    if not isinstance(reason, str) or not reason.strip() or not isinstance(evidence_refs, dict) or not evidence_refs:
        raise RunFilesError("必须提供实际回查依据及判断原因")
    with _task_lock(root):
        state = _read_state(root)
        _verify_files(root, state)
        if state["operation_id"] != operation_id or state["execution_status"] not in {"awaiting_result", "failed", "unknown"}:
            raise RunFilesError("回查操作编号或待处理状态不匹配")
        for relative, digest in evidence_refs.items():
            entry = state["managed_files"].get(relative)
            if (not entry or entry["sha256"] != digest or entry["status"] != "valid"
                    or entry["operation_id"] != operation_id or entry["scope"] != "required_process"
                    or entry["kind"] not in {"query", "geometry", "topology"}
                    or entry["source"].get("reconciliation") is not True):
                raise RunFilesError("解除阻塞需要本次实际只读回查证据")
        if state["awaiting_result"]:
            state["execution_status"] = "unknown"
        state["awaiting_result"] = False
        state["reconciliation"] = {
            "operation_id": operation_id, "evidence": evidence_refs, "reason": _redact(reason),
        }
        _invalidate_report(state)
        _write_state(root, state)
    return {"operation_id": operation_id, "execution_status": state["execution_status"], "reconciled": True}


def _verification_module():
    # 同时支持技能包导入和直接 python run_files.py；不反向导入 MCP。
    if __package__:
        from . import verification
    else:
        import verification
    return verification


def save_report(root: str | Path, *, report: dict, source_fingerprint: dict) -> dict:
    root = _validate_root(root)
    if not isinstance(report, dict) or not isinstance(source_fingerprint, dict):
        raise RunFilesError("要求公共检查报告和取证时的指纹")
    verification = _verification_module()
    with _task_lock(root):
        state = _read_state(root)
        _verify_files(root, state)
        _inputs_match(root, state)
        if (state["awaiting_result"] or state["execution_status"] != "responded"
                or source_fingerprint.get("operation_id") != state["operation_id"]
                or source_fingerprint.get("input_fingerprint") != state["input_fingerprint"]):
            raise RunFilesError("当前执行与报告来源不配套")
        refs = source_fingerprint.get("evidence")
        if not isinstance(refs, dict):
            raise RunFilesError("报告必须携带所用证据路径及 SHA-256")
        for relative, digest in refs.items():
            entry = state["managed_files"].get(relative)
            allowed_scope = entry and (entry["scope"] == "current_model" or (
                report.get("stage") != "final" and entry["scope"] == "required_process"
                and entry["source"].get("reconciliation") is not True))
            if (not entry or entry["sha256"] != digest or entry["status"] != "valid"
                    or not allowed_scope or entry["operation_id"] != state["operation_id"]
                    or entry["kind"] not in {"query", "geometry", "topology", "view"}):
                raise RunFilesError("报告使用了未登记、过期或非当前模型证据")
        graph = _json_load(_checked_path(root, "operation_graph.json").read_bytes())
        stage = report.get("stage")
        rows = report.get("checks")
        if not isinstance(stage, str) or not stage or not isinstance(rows, list):
            raise RunFilesError("报告缺少阶段或检查结果")
        findings, additional_ids = [], []
        for row in rows:
            if not isinstance(row, dict) or not isinstance(row.get("requirement"), dict):
                raise RunFilesError("报告检查行格式无效")
            if stage != "final" and row["requirement"].get("stage") != stage:
                additional_ids.append(row["requirement"].get("id"))
            for key in ("findings", "rejected_findings"):
                values = row.get(key, [])
                if not isinstance(values, list) or not all(isinstance(item, dict) for item in values):
                    raise RunFilesError("报告 findings 必须是检查记录列表")
                for finding in values:
                    # 允许“孔壁面：42”等语义说明，但每项有效结论至少关联一个实际入库文件。
                    evidence = finding.get("evidence", [])
                    if not isinstance(evidence, (list, tuple)):
                        raise RunFilesError("检查项 evidence 必须是引用列表")
                    if finding.get("status") == "passed" and not any(ref in refs for ref in evidence if isinstance(ref, str)):
                        raise RunFilesError("通过项缺少已绑定的实际证据文件")
                    if finding.get("status") == "passed" and finding.get("kind") in {"visual", "number"}:
                        kinds = {"view"} if finding["kind"] == "visual" else {"geometry", "topology", "query"}
                        if not any(isinstance(ref, str) and ref in refs
                                   and state["managed_files"][ref]["kind"] in kinds for ref in evidence):
                            raise RunFilesError("视觉项需要实际图片，数值项需要实际几何查询")
                    for ref in evidence:
                        if isinstance(ref, str) and (ref.startswith(("evidence/", "analysis/", "runtime/", ".work/"))
                                                     and ref not in refs):
                            raise RunFilesError("报告文件引用未包含在取证指纹中")
                    findings.append(finding)
        rebuilt = verification.build_report(graph["requirements"], findings, stage=stage,
                                             additional_ids=additional_ids)
        def writer(path, text):
            relative = path.relative_to(root).as_posix()
            if relative not in {FIXED_PATHS["verification_json"], FIXED_PATHS["verification_md"]}:
                raise RunFilesError("报告目标不属于固定槽")
            _atomic_write(_checked_path(root, relative), text.encode("utf-8"))
        verification.write_report(rebuilt, root / "reports", write_text=writer)
        for kind in ("verification_json", "verification_md"):
            relative = FIXED_PATHS[kind]
            _register(state, relative, kind, "main", _checked_path(root, relative).read_bytes(),
                      source_fingerprint, "current_model")
        # 写报告期间，设计源文件也可能被外部编辑器改动；提交通过前再核对。
        _inputs_match(root, state)
        _verify_files(root, state)
        state.update(verification_status=rebuilt["status"], verification_stage=stage)
        _write_state(root, state)
    result = {"verification_status": rebuilt["status"], "verification_stage": stage,
              "json_path": str(root / FIXED_PATHS["verification_json"]),
              "markdown_path": str(root / FIXED_PATHS["verification_md"])}
    result["cleanup"] = _cleanup_after_publish(root)
    return result


def _unmanaged_files(root, state):
    known = set(state["managed_files"]) | set(FIXED_PATHS.values()) | {
        "runtime/workspace.lock", "README.md", "model.crownscript.js",
        "parameters.json", "operation_graph.json", "analysis/analysis_notes.md",
    }
    result = []
    for current, dirs, filenames in os.walk(root, followlinks=False):
        current = Path(current)
        # 不读取未知文件的内容，也不跟随目录联接。
        for name in list(dirs):
            path = current / name
            try:
                _assert_plain(path)
            except RunFilesError:
                dirs.remove(name)
                result.append(path.relative_to(root).as_posix())
        for name in filenames:
            relative = (current / name).relative_to(root).as_posix()
            if relative not in known:
                result.append(relative)
    return sorted(result)


def cleanup_replaced(root: str | Path, *, dry_run: bool = False) -> dict:
    if type(dry_run) is not bool:
        raise RunFilesError("dry_run 必须是 bool")
    root = _validate_root(root)
    result = {"candidates": [], "deleted": [], "skipped": [], "errors": [], "unmanaged": []}
    with _task_lock(root):
        state = _read_state(root)
        # 清理不因未知文件或人为改过的候选而停止；这些文件只报告，不删除。
        _verify_files(root, state, allow_modified_replaced=True)
        result["unmanaged"] = _unmanaged_files(root, state)
        if state["operation_id"] and _fingerprint_inputs(root) != state["input_fingerprint"]:
            _invalidate_report(state)
            if not dry_run:
                _write_state(root, state)
            result["skipped"].append({"reason": "设计输入已变化，保留现场"})
            return result
        if state["awaiting_result"] or state["execution_status"] != "responded":
            result["skipped"].append({"reason": "尚未可靠完成交接，保留现场"})
            return result
        protected = set(_report_refs(state)) | set(state.get("reconciliation", {}).get("evidence", {}))
        changed = False
        for relative, entry in list(state["managed_files"].items()):
            if entry["kind"] == "temporary":
                result["skipped"].append({"path": relative, "reason": "旧中转资料只读保留，不自动迁移或删除"})
                continue
            if (relative in protected or entry["kind"] in FIXED_PATHS
                    or entry["scope"] == "required_process" or entry["status"] == "valid"
                    or entry["scope"] == "input_analysis"):
                continue
            path = _checked_path(root, relative)
            if not path.is_file() or _digest(path.read_bytes()) != entry["sha256"]:
                result["skipped"].append({"path": relative, "reason": "文件缺失或哈希不符，不自动删除"})
                continue
            if not _has_live_replacement(root, state, relative, entry):
                result["skipped"].append({"path": relative, "reason": "没有可靠替代物，不自动删除"})
                continue
            result["candidates"].append(relative)
            if dry_run:
                continue
            try:
                path.unlink()
            except OSError:
                entry["status"] = "cleanup_failed"
                result["errors"].append({"path": relative, "reason": "删除失败，可稍后重试"})
            else:
                del state["managed_files"][relative]
                result["deleted"].append(relative)
            changed = True
        if changed:
            _write_state(root, state)
    return result


def _cleanup_after_publish(root):
    """正式资料已提交；清理受阻只提示，不把保存成功改成执行失败。"""
    try:
        result = cleanup_replaced(root)
    except (RunFilesError, OSError):
        result = {"candidates": [], "deleted": [], "skipped": [],
                  "errors": [{"reason": "清理暂缓，保留现场"}], "unmanaged": []}
    if result["errors"]:
        print("正式资料已保存，清理暂缓", file=sys.stderr)
    return result


def _read_stdin_payload(stream):
    data = stream.read(MAX_STDIN_BYTES + 1)
    if len(data) > MAX_STDIN_BYTES:
        raise RunFilesError("标准输入大小超限")
    payload = _json_load(data)
    if not isinstance(payload, dict):
        raise RunFilesError("标准输入必须是 UTF-8 JSON 对象")
    return payload


def _decode_stdin_data(payload):
    encoded = payload.get("data_base64")
    if not isinstance(encoded, str):
        raise RunFilesError("data_base64 必须是 Base64 字符串")
    try:
        data = base64.b64decode(encoded, validate=True)
    except ValueError as error:
        raise RunFilesError("data_base64 不是有效 Base64") from error
    if len(data) > MAX_DATA_BYTES:
        raise RunFilesError("资料大小超限")
    return data


def _cli_parser():
    parser = argparse.ArgumentParser(description="本地任务文件管理；不调用 CAD")
    commands = parser.add_subparsers(dest="command", required=True)
    init = commands.add_parser("init")
    init.add_argument("--workspace", required=True)
    init.add_argument("--name", required=True)
    for command in ("prepare", "save-result", "save-evidence", "save-report", "resolve", "clean"):
        sub = commands.add_parser(command)
        sub.add_argument("--root", required=True)
        if command != "clean":
            sub.add_argument("--stdin", action="store_true", required=True,
                             help="从标准输入读取一份 UTF-8 JSON 对象，不保存中转文件")
        if command == "prepare":
            sub.add_argument("--document-id", required=True)
            sub.add_argument("--version-id", required=True)
            sub.add_argument("--overwrite", choices=("true", "false"), required=True)
            sub.add_argument("--purpose", required=True)
        elif command == "save-result":
            sub.add_argument("--operation-id", required=True)
            sub.add_argument("--outcome", choices=("responded", "failed", "unknown"), required=True)
        elif command == "save-evidence":
            sub.add_argument("--kind", required=True)
            sub.add_argument("--purpose", required=True)
            sub.add_argument("--scope", choices=sorted(SCOPES), required=True)
        elif command == "resolve":
            sub.add_argument("--operation-id", required=True)
            sub.add_argument("--reason", required=True)
        elif command == "clean":
            sub.add_argument("--apply", action="store_true")
    return parser


def main(argv=None):
    args = _cli_parser().parse_args(argv)
    try:
        if args.command == "init":
            result = {"root": str(_init_task(args.workspace, args.name)),
                      "layout_version": _LAYOUT_VERSION}
        else:
            if args.command != "clean":
                payload = _read_stdin_payload(sys.stdin.buffer)
                required = {
                    "prepare": {"code": str}, "save-result": {"result": (dict, type(None))},
                    "save-evidence": {"data_base64": str, "source": dict},
                    "save-report": {"report": dict, "source_fingerprint": dict},
                    "resolve": {"evidence_refs": dict},
                }[args.command]
                if any(key not in payload or not isinstance(payload[key], expected)
                       for key, expected in required.items()):
                    raise RunFilesError("标准输入缺少必需字段或字段类型不正确")
                if args.command == "save-evidence":
                    data = _decode_stdin_data(payload)
            root = _validate_root(args.root)
            if args.command == "prepare":
                result = prepare_execution(
                    root, document=dict(document_id=args.document_id, version_id=args.version_id,
                                        doc_type="PartDocument"),
                    overwrite=args.overwrite == "true",
                    code=payload["code"], purpose=args.purpose,
                )
                result.pop("code")  # stdout 不输出完整脚本。
            elif args.command == "save-result":
                result = save_execution_result(
                    root, operation_id=args.operation_id, outcome=args.outcome,
                    result=payload["result"])
            elif args.command == "save-evidence":
                path = save_evidence(root, kind=args.kind, purpose=args.purpose, scope=args.scope,
                                     data=data, source=payload["source"])
                result = {"path": str(path)}
            elif args.command == "save-report":
                result = save_report(root, report=payload["report"],
                                     source_fingerprint=payload["source_fingerprint"])
            elif args.command == "resolve":
                result = _record_reconciliation(root, args.operation_id,
                                                payload["evidence_refs"], args.reason)
            else:
                result = cleanup_replaced(root, dry_run=not args.apply)
        print(json.dumps(result, ensure_ascii=False, allow_nan=False))
        return 0
    except (RunFilesError, OSError, ValueError, KeyError, TypeError, ImportError) as error:
        # 不回显原始工具异常或输入值；已准备请求不能因本地错误自动重发。
        message = str(error) if isinstance(error, RunFilesError) else "本地操作失败；保留现场，不自动重发 CAD"
        print(json.dumps({"status": "error", "errorType": type(error).__name__, "message": message},
                         ensure_ascii=False))
        return 1


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    raise SystemExit(main())
