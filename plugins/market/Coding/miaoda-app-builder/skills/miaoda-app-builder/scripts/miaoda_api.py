#!/usr/bin/env python3
"""
Miaoda Platform API CLI Client

Usage:
    python miaoda_api.py [--api-key <token>] <command> [options]

Environment variables:
    MIAODA_API_KEY    - Bearer token (alternative to --api-key)

Network policy (fixed in code, not configurable):
    * Every request that carries the API key goes only to https://api.miaoda.cn,
      and redirects from the API are never followed.
    * File downloads (download-source / download-task-file) are sent without the
      API key, only over HTTPS, only to the allowlisted hosts below, with every
      redirect hop re-validated, and are written only into ./miaoda-downloads/.
"""

import argparse
import errno
import json
import os
import re
import sys
import time
import uuid
from urllib.parse import unquote, urljoin, urlparse
from typing import Optional

if __name__ == "__main__":
    from miaoda_runtime import use_plugin_runtime

    use_plugin_runtime()

try:
    import requests
except ImportError:
    print(
        "Error: 'requests' package not installed. Run: python3 -m pip install --require-hashes -r requirements.txt",
        file=sys.stderr,
    )
    sys.exit(1)

API_BASE_URL = "https://api.miaoda.cn"
_API_HOST = "api.miaoda.cn"
VERSION = "1.1.5"
CLIENT = "qoder"

# Download policy
DOWNLOAD_HOST_SUFFIXES = (".bcebos.com", ".miaoda.cn", ".appmiaoda.com")
DOWNLOAD_DIR_NAME = "miaoda-downloads"
DOWNLOAD_MAX_BYTES = 1024 * 1024 * 1024  # 1 GiB actually written to disk
DOWNLOAD_MAX_SECONDS = 600               # total time budget per download
DOWNLOAD_MAX_REDIRECTS = 3

# Polling policy
MIN_POLL_INTERVAL = 1.0
MAX_POLL_INTERVAL = 60.0
TRAJECTORY_DEFAULT_MAX_WAIT = 1800
TRAJECTORY_MAX_WAIT_LIMIT = 7200
PUBLISH_DEFAULT_MAX_WAIT = 300
PUBLISH_MAX_WAIT_LIMIT = 1800
MIN_FETCH_TIMEOUT = 1
MAX_FETCH_TIMEOUT = 120


class _PinnedApiSession(requests.Session):
    """HTTP session for authenticated calls.

    Only ``https://api.miaoda.cn`` (port 443) is accepted and redirects are
    never followed, so the API key and user input cannot be sent to any other
    host, whatever URL a caller builds.
    """

    def request(self, method, url, **kwargs):
        parsed = urlparse(url)
        host = (parsed.hostname or "").lower()
        if parsed.scheme != "https" or host != _API_HOST or parsed.port not in (None, 443):
            raise RuntimeError(
                f"Blocked request: authenticated calls may only go to {API_BASE_URL} (got host {host or '?'})"
            )
        kwargs["allow_redirects"] = False
        resp = super().request(method, url, **kwargs)
        if 300 <= resp.status_code < 400:
            resp.close()
            raise RuntimeError(
                f"Blocked redirect from {API_BASE_URL} (HTTP {resp.status_code}); redirects are not followed"
            )
        return resp


_API = _PinnedApiSession()


def _api_url(path: str) -> str:
    """Build an absolute URL on the fixed official API host."""
    return f"{API_BASE_URL}/{path.lstrip('/')}"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def auth_headers(api_key: str) -> dict:
    """Return HTTP headers with Bearer token authentication, JSON content type, and custom User-Agent."""
    return {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "User-Agent": f"miaoda-app-builder/{CLIENT}-{VERSION}",
    }


def raise_for_api_error(resp: "requests.Response"):
    """Raise RuntimeError if the HTTP response or the API-level status indicates an error.

    Checks both the HTTP status code (via raise_for_status) and the JSON body's
    ``status`` field.  Returns the parsed body on success.
    """
    resp.raise_for_status()
    body = resp.json()
    if body.get("status") != 0:
        msg = body.get("msg") or body.get("message") or json.dumps(body)
        raise RuntimeError(f"API error (status={body.get('status')}): {msg}")
    return body


def _raise_if_insufficient_credits(message: str) -> None:
    """Print a balance notice to stderr if credits are insufficient."""
    if not message:
        return
    if any(kw in message for kw in ("秒点不足", "秒点余额不足", "Insufficient Credits", "out of credits")):
        print("秒点余额不足", file=sys.stderr)


def _safe_filename(name: str, default: str) -> str:
    """Return a local filename without directory traversal or unsafe characters."""
    name = unquote((name or "").strip()).replace("\\", "/")
    name = os.path.basename(name.rstrip("/"))
    name = re.sub(r"[^A-Za-z0-9._ -]", "_", name).strip(" .")
    return name or default


def _filename_from_content_disposition(value: str) -> Optional[str]:
    """Extract filename from a Content-Disposition header when present."""
    if not value:
        return None
    match = re.search(r"filename\*=UTF-8''([^;]+)", value, flags=re.IGNORECASE)
    if match:
        return unquote(match.group(1).strip().strip('"'))
    match = re.search(r'filename="?([^";]+)"?', value, flags=re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return None


def _download_dir() -> str:
    """Return (and create) the only directory downloads may be written to.

    The directory is ``./miaoda-downloads`` under the current working directory
    (the session workspace). A symlinked download directory is rejected.
    """
    base = os.path.realpath(os.getcwd())
    target = os.path.join(base, DOWNLOAD_DIR_NAME)
    if os.path.islink(target):
        raise RuntimeError(f"Refusing to use symlinked download directory: {target}")
    os.makedirs(target, exist_ok=True)
    real = os.path.realpath(target)
    if os.path.dirname(real) != base:
        raise RuntimeError(f"Download directory escapes the workspace: {real}")
    return real


def _validate_output_name(name: str) -> str:
    """Accept a bare file name only: no absolute paths, separators, '.', '..' or hidden traversal."""
    if name is None:
        raise RuntimeError("--output must be a file name")
    raw = name.strip()
    if not raw or raw in (".", ".."):
        raise RuntimeError("--output must be a non-empty file name")
    if os.path.isabs(raw) or "/" in raw or "\\" in raw or raw.startswith("~") or "\x00" in raw:
        raise RuntimeError(
            f"--output only accepts a file name (got {name!r}); files are always saved under ./{DOWNLOAD_DIR_NAME}/"
        )
    if raw.startswith("."):
        raise RuntimeError(f"--output must not start with '.' (got {name!r})")
    return raw


def _resolve_target_path(file_name: str) -> str:
    """Return the final path inside the download directory, refusing overwrite and escape."""
    directory = _download_dir()
    path = os.path.join(directory, file_name)
    if os.path.dirname(os.path.realpath(path)) != directory:
        raise RuntimeError(f"Refusing to write outside ./{DOWNLOAD_DIR_NAME}/: {file_name}")
    if os.path.lexists(path):
        raise RuntimeError(
            f"File already exists: ./{DOWNLOAD_DIR_NAME}/{file_name}. Choose another --output name; existing files are never overwritten."
        )
    return path


def _validate_download_url(url: str) -> None:
    """Allow only HTTPS URLs on the allowlisted download hosts (default port)."""
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()
    if parsed.scheme != "https":
        raise RuntimeError(f"Blocked download: only HTTPS is allowed (got {parsed.scheme or '?'}://)")
    if parsed.username or parsed.password:
        raise RuntimeError("Blocked download: credentials in URL are not allowed")
    if parsed.port not in (None, 443):
        raise RuntimeError(f"Blocked download: non-standard port {parsed.port}")
    if not host or not any(host.endswith(sfx) for sfx in DOWNLOAD_HOST_SUFFIXES):
        raise RuntimeError(
            f"Blocked download: host {host or '?'} is not in the allowlist ({', '.join('*' + s for s in DOWNLOAD_HOST_SUFFIXES)})"
        )


def _infer_file_name(url: str, response: "requests.Response", output: Optional[str], default: str) -> str:
    """Choose the final file name from explicit output, response headers, or URL."""
    if output:
        return _validate_output_name(output)
    filename = _filename_from_content_disposition(response.headers.get("Content-Disposition", ""))
    if not filename:
        filename = os.path.basename(urlparse(url).path)
    return _safe_filename(filename, default)


def _download_url_to_file(url: str, output: Optional[str] = None, default_name: str = "download.bin") -> str:
    """Download an allowlisted HTTPS URL into ./miaoda-downloads/ and return the final path.

    * No API key or other credential is attached to the download request.
    * Redirects are followed manually (max DOWNLOAD_MAX_REDIRECTS) and every hop is re-validated.
    * Total time is capped at DOWNLOAD_MAX_SECONDS and bytes written at DOWNLOAD_MAX_BYTES.
    * The temp file is created exclusively in the same directory and removed on any failure.
    * Existing files are never overwritten.
    """
    if output is not None:
        _validate_output_name(output)
    deadline = time.monotonic() + DOWNLOAD_MAX_SECONDS
    current = url
    session = requests.Session()
    session.trust_env = False  # ignore .netrc credentials and proxy env for downloads
    try:
        for _hop in range(DOWNLOAD_MAX_REDIRECTS + 1):
            _validate_download_url(current)
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError(f"Download exceeded {DOWNLOAD_MAX_SECONDS}s")
            resp = session.get(
                current, stream=True, allow_redirects=False,
                timeout=(min(30, remaining), min(60, remaining)),
                headers={"User-Agent": f"miaoda-app-builder/{CLIENT}-{VERSION}"},
            )
            if resp.is_redirect or resp.status_code in (301, 302, 303, 307, 308):
                location = resp.headers.get("Location")
                resp.close()
                if not location:
                    raise RuntimeError("Redirect without Location header")
                current = urljoin(current, location)
                continue
            break
        else:
            raise RuntimeError(f"Too many redirects (>{DOWNLOAD_MAX_REDIRECTS})")

        with resp:
            resp.raise_for_status()
            declared = resp.headers.get("Content-Length")
            if declared and declared.isdigit() and int(declared) > DOWNLOAD_MAX_BYTES:
                raise RuntimeError(f"Download too large: {declared} bytes > limit {DOWNLOAD_MAX_BYTES}")
            file_name = _infer_file_name(current, resp, output, default_name)
            local_path = _resolve_target_path(file_name)
            directory = os.path.dirname(local_path)
            tmp_path = os.path.join(directory, f".{file_name}.{uuid.uuid4().hex}.part")
            flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_BINARY", 0)
            fd = os.open(tmp_path, flags, 0o600)
            written = 0
            try:
                with os.fdopen(fd, "wb") as fh:
                    for chunk in resp.iter_content(chunk_size=1024 * 1024):
                        if not chunk:
                            continue
                        written += len(chunk)
                        if written > DOWNLOAD_MAX_BYTES:
                            raise RuntimeError(f"Download exceeded size limit {DOWNLOAD_MAX_BYTES} bytes")
                        if time.monotonic() > deadline:
                            raise TimeoutError(f"Download exceeded {DOWNLOAD_MAX_SECONDS}s")
                        fh.write(chunk)
                    fh.flush()
                    os.fsync(fh.fileno())
                # Atomic, no-overwrite publish of the finished file.
                try:
                    os.link(tmp_path, local_path)
                except FileExistsError:
                    raise RuntimeError(f"File already exists: ./{DOWNLOAD_DIR_NAME}/{file_name}")
                except OSError as exc:
                    if exc.errno not in (errno.EPERM, errno.EXDEV, errno.ENOTSUP, getattr(errno, "EOPNOTSUPP", -1)):
                        raise
                    if os.path.lexists(local_path):
                        raise RuntimeError(f"File already exists: ./{DOWNLOAD_DIR_NAME}/{file_name}")
                    os.rename(tmp_path, local_path)
            finally:
                if os.path.lexists(tmp_path):
                    try:
                        os.remove(tmp_path)
                    except OSError:
                        pass
    finally:
        session.close()
    return local_path


# ---------------------------------------------------------------------------
# 1. List Apps (应用基本信息)
# ---------------------------------------------------------------------------

_LIST_APPS_STRIP = {"avatar", "mobileCover", "hasAppHost", "hasBackend"}
_LIST_APPS_BRIEF_KEEP = {"appId", "name", "type", "appFocus", "host", "updatedAt"}

def list_apps(
    api_key: str,
    name: str = "",
    page: int = 1,
    size: int = 12,
    brief: bool = False,
) -> dict:
    """POST /api/v1/app/list — paginated app list."""
    url = _api_url("/api/v1/app/list")
    payload = {
        "name": name,
        "page": page,
        "size": size,
        "sort": {"direction": "desc", "property": "updatedAt"},
    }
    resp = _API.post(url, json=payload, headers=auth_headers(api_key), timeout=30)
    result = raise_for_api_error(resp)
    data = result.get("data", {})
    # Accommodate both "items" and "list" response keys (API may vary)
    items = data.get("items", data.get("list", []))
    if brief:
        items = [
            {k: v for k, v in item.items() if k in _LIST_APPS_BRIEF_KEEP}
            for item in items
        ]
    else:
        for item in items:
            for key in _LIST_APPS_STRIP:
                item.pop(key, None)
    if "items" in data:
        data["items"] = items
    elif "list" in data:
        data["list"] = items
    return result


# ---------------------------------------------------------------------------
# 2. App Detail (应用详情)
# ---------------------------------------------------------------------------

def get_app_detail(
    api_key: str,
    app_id: str,
) -> dict:
    """GET /api/v1/app/bootstrap/{app_id} — app detail."""
    url = _api_url(f"/api/v1/app/bootstrap/{app_id}")
    resp = _API.get(url, headers=auth_headers(api_key), timeout=30)
    result = raise_for_api_error(resp)
    data = result.get("data", {})
    for key in ("hasBackend", "hasAppHost", "sandboxUrl"):
        data.pop(key, None)
    return result


# ---------------------------------------------------------------------------
# 3. Chat (two-step: POST chat → SSE trajectory)
# ---------------------------------------------------------------------------

def _build_chat_payload(
    text: str,
    context_id: str = "",
    app_id: Optional[str] = None,
    query_mode: str = "deep_mode",
    input_field_type: str = "web",
    lang: str = "zh",
    user_confirmation: Optional[dict] = None,
    node: Optional[dict] = None,
) -> dict:
    """Build a JSON-RPC 2.0 ``message/send`` payload for the chat endpoint.

    When ``user_confirmation`` is provided it replaces ``inputFieldType`` in the
    request metadata, which is used to send confirmation actions such as
    ``{"type": "generateApp"}``.  Leave ``context_id`` empty to create a new app;
    pass the existing ``conversationId`` to continue an existing conversation.

    When ``node`` is provided, an additional ``kind: "data"`` part is appended to
    ``message.parts``, carrying structured UI-node context (file path, line
    range, tag, current styles, etc.).  This is the LGUI (Live-GUI) mode: the
    Agent can pinpoint the exact DOM/JSX node the user has selected in the
    editor and skip searching the codebase to locate it.

    ``node`` may be either:
      * the inner node object directly — the function will wrap it as
        ``{"type": "node", "node": <node>}``, or
      * a pre-wrapped ``{"type": "node", "node": {...}}`` dict — passed through
        unchanged.
    """
    params_metadata: dict = {
        "defaultAgent": "AdaPro",
        "agentConfig": {},
        "runtime": "miaoda",
        "queryMode": query_mode,
    }
    if user_confirmation is not None:
        params_metadata["userConfirmation"] = user_confirmation
    else:
        params_metadata["inputFieldType"] = input_field_type

    parts: list = [{"kind": "text", "text": text}]
    if node is not None:
        # Accept either the raw node object or a pre-wrapped {type, node} dict.
        if isinstance(node, dict) and node.get("type") == "node" and "node" in node:
            node_data = node
        else:
            node_data = {"type": "node", "node": node}
        parts.append({"kind": "data", "data": node_data})

    payload = {
        "jsonrpc": "2.0",
        "method": "message/send",
        "id": str(uuid.uuid4()),
        "params": {
            "message": {
                "parts": parts,
                "kind": "message",
                "messageId": str(uuid.uuid4()),
                "role": "user",
                "contextId": context_id,
                "metadata": {},
                "taskId": "",
                "lang": lang,
            },
            "metadata": params_metadata,
        },
    }
    if app_id:
        payload["params"]["metadata"]["appId"] = app_id
    return payload


def _check_chat_response_for_error(chat_result: dict) -> None:
    """Raise RuntimeError if the chat POST response already indicates a terminal failure.

    When the platform rejects the request immediately (e.g. insufficient balance),
    it returns either a top-level JSON-RPC ``error`` field or a ``state=failed`` /
    ``final=true`` response.  Detecting this early avoids a pointless trajectory
    poll and surfaces the error message clearly.
    """
    # Path 1: top-level JSON-RPC error field (e.g., balance pre-check rejection)
    if "error" in chat_result:
        error = chat_result.get("error", {})
        error_msg = error.get("message", "")
        data = error.get("data", {})
        bce_code = data.get("bce_error_code", "") if isinstance(data, dict) else ""
        if bce_code == "MethodNotAllowed" or "秒点" in error_msg:
            _raise_if_insufficient_credits(error_msg or "秒点不足")
        raise RuntimeError(
            f"Chat request failed: {error_msg or json.dumps(error, ensure_ascii=False)}"
        )

    # Path 2: result field with failed/final state
    result = chat_result.get("result", {})
    state = result.get("status", {}).get("state", "")
    is_final = result.get("final", False)
    if state == "failed" or is_final:
        # Extract the human-readable error text from message parts if available
        parts = result.get("status", {}).get("message", {}).get("parts", [])
        text_parts = [p.get("text", "") for p in parts if p.get("kind") == "text"]
        error_text = " ".join(text_parts).strip() or json.dumps(chat_result, ensure_ascii=False)
        print(json.dumps(chat_result, ensure_ascii=False), flush=True)
        _raise_if_insufficient_credits(error_text)
        raise RuntimeError(f"Chat request failed: {error_text}")


def _extract_ids_from_chat_response(
    chat_result: dict, fallback_app_id: Optional[str]
) -> tuple[Optional[str], Optional[str]]:
    """
    Extract (appId, conversationId) from the chat POST response.

    Response path: result.status.message.metadata.{appId, conversationId}
    For a new app (contextId=""), both values are freshly assigned by the server.
    """
    try:
        metadata = (
            chat_result
            .get("result", {})
            .get("status", {})
            .get("message", {})
            .get("metadata", {})
        )
        app_id = metadata.get("appId") or fallback_app_id
        conversation_id = metadata.get("conversationId")
        return app_id, conversation_id
    except (AttributeError, TypeError):
        return fallback_app_id, None


def chat_no_stream(
    api_key: str,
    text: str,
    context_id: str = "",
    app_id: Optional[str] = None,
    query_mode: str = "deep_mode",
    input_field_type: str = "web",
    user_confirmation: Optional[dict] = None,
    node: Optional[dict] = None,
) -> dict:
    """POST /api/v1/conversation/chat — returns raw JSON-RPC response without streaming."""
    url = _api_url("/api/v1/conversation/chat")
    payload = _build_chat_payload(
        text, context_id, app_id, query_mode, input_field_type,
        user_confirmation=user_confirmation,
        node=node,
    )
    resp = _API.post(url, json=payload, headers=auth_headers(api_key), timeout=60)
    resp.raise_for_status()
    chat_result = resp.json()
    _check_chat_response_for_error(chat_result)
    return chat_result


def chat_stream(
    api_key: str,
    text: str,
    context_id: str = "",
    app_id: Optional[str] = None,
    query_mode: str = "deep_mode",
    input_field_type: str = "web",
    prompt_generate: bool = False,
    poll_interval: float = 2.0,
    fetch_timeout: int = 10,
    node: Optional[dict] = None,
    max_wait: Optional[float] = None,
):
    """
    Two-step chat flow:
      1. POST /api/v1/conversation/chat
      2. Poll GET /api/v1/conversation/trajectory?stream=false until terminal state

    When context_id="" a new app is created. Prints a header line:
      {"appId": "...", "conversationId": "..."}
    then polls trajectory events and prints each as a JSON line.

    If prompt_generate=True and the trajectory returns immediately generated text,
    prompts the user interactively whether to submit the app (generate-app confirmation).
    """
    # Guard: --app-id without a valid --context-id silently creates a NEW app every time.
    # Also catches bash jq -r returning the literal string "null" for a missing field.
    _INVALID_CONTEXT = {"", "null", "undefined", "none"}
    if app_id and context_id.strip().lower() in _INVALID_CONTEXT:
        raise RuntimeError(
            f"--app-id ({app_id}) was provided but --context-id is missing or invalid "
            f"(got: {context_id!r}).\n"
            "The platform will NOT modify the existing app — it will create a brand-new one.\n"
            "To continue/modify an existing app:  --app-id <appId> --context-id <conversationId>\n"
            "To create a new app from scratch:    omit both --app-id and --context-id\n"
            "To recover a lost conversationId:    python scripts/miaoda_api.py get-context-id --app-id <appId>"
        )

    # Step 1: submit chat
    chat_url = _api_url("/api/v1/conversation/chat")
    payload = _build_chat_payload(text, context_id, app_id, query_mode, input_field_type, node=node)

    resp = _API.post(chat_url, json=payload, headers=auth_headers(api_key), timeout=60)
    resp.raise_for_status()
    chat_result = resp.json()
    _check_chat_response_for_error(chat_result)

    # Step 2: resolve appId and conversationId
    resolved_app_id, resolved_conversation_id = _extract_ids_from_chat_response(chat_result, app_id)
    if not resolved_app_id:
        raise RuntimeError(
            "Could not extract appId from chat response. "
            "Check that context-id / app-id is correct, or leave context-id empty to create a new app."
        )

    # Print resolved IDs so the caller can store them for follow-up requests
    print(
        json.dumps(
            {"appId": resolved_app_id, "conversationId": resolved_conversation_id},
            ensure_ascii=False,
        ),
        flush=True,
    )

    text_output, prd_action = poll_trajectory(
        api_key, resolved_app_id,
        poll_interval=poll_interval,
        fetch_timeout=fetch_timeout,
        max_wait=max_wait,
    )

    # Determine whether the Agent needs to call generate-app next.
    # For general tasks (reports, PPT, analysis), prd_action is None and
    # generate-app must NOT be called.
    need_generate = False
    requirement_type = None
    if prd_action is not None:
        requirement_type = (prd_action.get("appInfo") or {}).get("requirementType")
        need_generate = (
            not prd_action.get("is_generated", False)
            and _has_generate_app_button(prd_action)
        )

    print(
        json.dumps({
            "needGenerateApp": need_generate,
            "requirementType": requirement_type,
            "appType": requirement_type if requirement_type else "TASK",
        }, ensure_ascii=False),
        flush=True,
    )

    # If prompt_generate is set and app creation PRD is ready, interactively ask
    if prompt_generate and need_generate:
        print(
            "\n[提示] PRD 已就绪，是否立即生成应用？(y/n): ",
            end="",
            flush=True,
        )
        answer = input().strip().lower()
        if answer in ("y", "yes", "是"):
            print("\n[提交应用]", flush=True)
            generate_app_confirmation(
                api_key,
                context_id=resolved_conversation_id or context_id,
                app_id=resolved_app_id,
                query_mode=query_mode,
                watch=True,
                poll_interval=poll_interval,
                fetch_timeout=fetch_timeout,
                max_wait=max_wait,
            )


def generate_app_confirmation(
    api_key: str,
    context_id: str = "",
    app_id: Optional[str] = None,
    query_mode: str = "deep_mode",
    watch: bool = False,
    poll_interval: float = 2.0,
    fetch_timeout: int = 10,
    max_wait: Optional[float] = None,
) -> dict:
    """POST /api/v1/conversation/chat with userConfirmation: {type: "generateApp"}.

    Submits the app-generation confirmation and returns immediately with the
    server's ``state=submitted`` response.  The resolved ``appId`` and
    ``conversationId`` are printed as a JSON line so callers can capture them.

    When ``watch=True`` the function additionally calls ``poll_trajectory`` to
    block until the generation reaches a terminal state.  For long-running
    generations prefer leaving ``watch=False`` and checking status separately
    with ``fetch_trajectory_once`` (or the ``fetch-trajectory`` CLI command).
    """
    _INVALID_CONTEXT = {"", "null", "undefined", "none"}
    if app_id and context_id.strip().lower() in _INVALID_CONTEXT:
        raise RuntimeError(
            f"--app-id ({app_id}) was provided but --context-id is missing or invalid "
            f"(got: {context_id!r}).\n"
            "The platform will NOT modify the existing app — it will create a brand-new one.\n"
            "Provide --context-id <conversationId> to confirm generation for the correct app."
        )

    chat_url = _api_url("/api/v1/conversation/chat")
    payload = _build_chat_payload(
        text="生成应用",
        context_id=context_id,
        app_id=app_id,
        query_mode=query_mode,
        user_confirmation={"type": "generateApp"},
    )
    resp = _API.post(chat_url, json=payload, headers=auth_headers(api_key), timeout=60)
    resp.raise_for_status()
    result = resp.json()
    _check_chat_response_for_error(result)

    resolved_app_id, resolved_conversation_id = _extract_ids_from_chat_response(result, app_id)
    print(
        json.dumps(
            {"appId": resolved_app_id, "conversationId": resolved_conversation_id},
            ensure_ascii=False,
        ),
        flush=True,
    )

    if watch and resolved_app_id:
        poll_trajectory(
            api_key, resolved_app_id,
            poll_interval=poll_interval,
            fetch_timeout=fetch_timeout,
            max_wait=max_wait,
        )

    return result


# ---------------------------------------------------------------------------
# 4. Conversation Trajectory
# ---------------------------------------------------------------------------

def _extract_text_from_event(event: dict) -> str:
    """Return concatenated text from a trajectory event's message parts (empty if none)."""
    result = event.get("result", {})
    status = result.get("status", {})
    message = status.get("message")
    if not message:
        return ""
    parts = message.get("parts", [])
    return "".join(p.get("text", "") for p in parts if p.get("kind") == "text")


def _extract_event_id(event: dict) -> Optional[int]:
    """Return result.metadata.eventId from a trajectory event, or None if absent."""
    try:
        return event.get("result", {}).get("metadata", {}).get("eventId")
    except (AttributeError, TypeError):
        return None


def _is_terminal_event(event: dict) -> bool:
    """Return True if the event represents a terminal state (completed / failed / final)."""
    result_obj = event.get("result", {})
    state = result_obj.get("status", {}).get("state", "")
    return state in ("completed", "input-required", "failed") or bool(result_obj.get("final"))


def _extract_prd_action_from_events(events: list) -> Optional[dict]:
    """Scan a batch of trajectory events and return the prdAgentAction data dict.

    prdAgentAction is only emitted during the app-creation PRD stage.
    Its presence (with a generateApp button) means the Agent must call
    generate-app next.  Absence means the chat was a general task that
    completed directly — no generate-app step is needed.

    Returns the first prdAgentAction found, or None if not present.
    """
    for event in events:
        result = event.get("result", {})
        artifact = result.get("artifact", {})
        if not isinstance(artifact, dict):
            continue
        for part in artifact.get("parts", []):
            data = part.get("data", {}) if isinstance(part, dict) else {}
            if isinstance(data, dict) and data.get("type") == "prdAgentAction":
                return data
    return None


def _has_generate_app_button(prd_action: dict) -> bool:
    """Return True if a prdAgentAction contains a generateApp confirmation button."""
    for action in prd_action.get("actions", []):
        if isinstance(action, dict):
            event = action.get("event", {})
            if isinstance(event, dict) and event.get("name") == "generateApp":
                return True
    return False


def fetch_trajectory_once(
    api_key: str,
    app_id: str,
    last_event_id: int = -1,
    timeout: int = 10,
) -> tuple[list, int, bool]:
    """GET /api/v1/conversation/trajectory?stream=false — single non-SSE fetch.

    Fetches a batch of trajectory events starting after ``last_event_id``.
    Pass ``last_event_id=-1`` to retrieve all events from the beginning.

    Returns:
        events       - list of event dicts (JSON-RPC 2.0 objects)
        max_event_id - highest ``result.metadata.eventId`` seen in this batch,
                       or the original ``last_event_id`` if no events were returned
        is_terminal  - True if any event in the batch is a terminal state
    """
    url = _api_url("/api/v1/conversation/trajectory")
    params = {"appId": app_id, "lastEventId": last_event_id, "stream": "false"}

    resp = _API.get(url, params=params, headers=auth_headers(api_key), timeout=timeout)
    resp.raise_for_status()
    body = resp.json()

    # Normalise the response: the endpoint may return a list directly,
    # or wrap events in {"status": 0, "data": [...]} / {"status": 0, "data": {"events": [...]}}
    if isinstance(body, list):
        events = body
    elif isinstance(body, dict):
        data = body.get("data", body)
        if isinstance(data, list):
            events = data
        elif isinstance(data, dict):
            events = data.get("events", [data])
        else:
            events = [body]
    else:
        events = []

    max_event_id = last_event_id
    is_terminal = False
    for event in events:
        eid = _extract_event_id(event)
        if eid is not None and eid > max_event_id:
            max_event_id = eid
        if _is_terminal_event(event):
            is_terminal = True

    return events, max_event_id, is_terminal


def _clamp_poll_settings(poll_interval: float, fetch_timeout: int, max_wait: Optional[float],
                         default_wait: float, wait_limit: float) -> tuple[float, int, float]:
    """Clamp polling parameters to safe bounds."""
    interval = min(max(float(poll_interval), MIN_POLL_INTERVAL), MAX_POLL_INTERVAL)
    timeout = int(min(max(int(fetch_timeout), MIN_FETCH_TIMEOUT), MAX_FETCH_TIMEOUT))
    wait = default_wait if max_wait is None else float(max_wait)
    wait = min(max(wait, interval), wait_limit)
    return interval, timeout, wait


def poll_trajectory(
    api_key: str,
    app_id: str,
    last_event_id: int = -1,
    poll_interval: float = 2.0,
    fetch_timeout: int = 10,
    max_wait: Optional[float] = None,
) -> tuple[str, Optional[dict]]:
    """Poll GET /api/v1/conversation/trajectory?stream=false until a terminal state.

    Calls ``fetch_trajectory_once`` repeatedly, printing each event as a JSON
    line and advancing ``lastEventId`` with each batch.  Stops when the server
    returns a completed / failed / final event, or when ``max_wait`` seconds
    (default TRAJECTORY_DEFAULT_MAX_WAIT, hard limit TRAJECTORY_MAX_WAIT_LIMIT)
    have elapsed. The poll interval is clamped to [MIN_POLL_INTERVAL,
    MAX_POLL_INTERVAL].

    On timeout a ``{"status": "TIMEOUT", "appId", "lastEventId", ...}`` JSON
    line is printed and TimeoutError is raised; the task keeps running on the
    platform and can be resumed with ``fetch-trajectory`` / ``trajectory``
    using the printed ``lastEventId``.

    Returns (text_output, prd_action) where prd_action is the prdAgentAction
    data dict if app-creation PRD was completed, or None for general tasks.
    """
    interval, timeout, wait = _clamp_poll_settings(
        poll_interval, fetch_timeout, max_wait, TRAJECTORY_DEFAULT_MAX_WAIT, TRAJECTORY_MAX_WAIT_LIMIT,
    )
    text_output = ""
    prd_action: Optional[dict] = None
    current_last_id = last_event_id
    deadline = time.monotonic() + wait

    while True:
        events, max_event_id, is_terminal = fetch_trajectory_once(
            api_key, app_id, current_last_id, timeout=timeout,
        )
        for event in events:
            print(json.dumps(event, ensure_ascii=False), flush=True)
            text_output += _extract_text_from_event(event)

        action = _extract_prd_action_from_events(events)
        if action is not None:
            prd_action = action

        current_last_id = max_event_id

        if is_terminal:
            break

        if time.monotonic() + interval > deadline:
            print(
                json.dumps({
                    "status": "TIMEOUT",
                    "appId": app_id,
                    "lastEventId": current_last_id,
                    "maxWaitSeconds": wait,
                    "resume": f"python3 scripts/miaoda_api.py fetch-trajectory --app-id {app_id} --last-event-id {current_last_id}",
                }, ensure_ascii=False),
                flush=True,
            )
            raise TimeoutError(
                f"Trajectory polling stopped after {int(wait)}s without a terminal state "
                f"(appId={app_id}, lastEventId={current_last_id}); the task may still be running"
            )

        time.sleep(interval)

    return text_output, prd_action


def stream_trajectory(
    api_key: str,
    app_id: str,
    last_event_id: int = 0,
    max_wait: Optional[float] = None,
) -> str:
    """GET /api/v1/conversation/trajectory — SSE stream (legacy).

    Prints each event as a JSON line. Stops at [DONE], state==completed/failed,
    or final==true, or after ``max_wait`` seconds (same bounds as polling).
    Returns concatenated text from all text-part events.
    Prefer ``poll_trajectory`` for more reliable long-running tasks.
    """
    _, _, wait = _clamp_poll_settings(
        MIN_POLL_INTERVAL, 10, max_wait, TRAJECTORY_DEFAULT_MAX_WAIT, TRAJECTORY_MAX_WAIT_LIMIT,
    )
    deadline = time.monotonic() + wait
    url = _api_url("/api/v1/conversation/trajectory")
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Accept": "text/event-stream",
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        "User-Agent": f"miaoda-app-builder/{CLIENT}-{VERSION}",
    }
    params = {"appId": app_id, "lastEventId": last_event_id}

    resp = _API.get(url, params=params, headers=headers, stream=True, timeout=(30, 300))
    resp.raise_for_status()
    resp.encoding = "utf-8"

    text_output = ""
    last_seen = last_event_id
    try:
        for line in resp.iter_lines(decode_unicode=True):
            if time.monotonic() > deadline:
                print(json.dumps({"status": "TIMEOUT", "appId": app_id, "lastEventId": last_seen,
                                  "maxWaitSeconds": wait}, ensure_ascii=False), flush=True)
                raise TimeoutError(
                    f"SSE trajectory stopped after {int(wait)}s (appId={app_id}, lastEventId={last_seen})"
                )
            if not line:
                continue
            if line.startswith("data:"):
                data_str = line[5:].strip()
                # Handle double-prefix edge case
                if data_str.startswith("data:"):
                    data_str = data_str[5:].strip()
                if data_str in ("[DONE]", "[done]"):
                    break
                try:
                    event = json.loads(data_str)
                    print(json.dumps(event, ensure_ascii=False), flush=True)
                    text_output += _extract_text_from_event(event)
                    eid = _extract_event_id(event)
                    if eid is not None and eid > last_seen:
                        last_seen = eid
                    if _is_terminal_event(event):
                        break
                except json.JSONDecodeError:
                    continue
    finally:
        resp.close()
    return text_output


# ---------------------------------------------------------------------------
# 4b. Get Context ID / Conversation History
# ---------------------------------------------------------------------------

def get_context_id(
    api_key: str,
    app_id: str,
    fetch_timeout: int = 10,
) -> Optional[str]:
    """Extract the conversationId (contextId) for an existing app by reading its trajectory.

    Scans ALL trajectory events and returns the MOST RECENT (last) non-empty contextId
    found, checking two paths per event:
      1. result.contextId           — direct field present in some event types
      2. result.status.message.metadata.conversationId  — same path as chat POST response

    Returning the most recent value ensures multi-round modification gets the
    up-to-date contextId in case the platform rotates it across interactions.
    Returns ``None`` if no events exist or neither field is found in any event.
    """
    events, _, _ = fetch_trajectory_once(
        api_key, app_id, last_event_id=-1, timeout=fetch_timeout,
    )
    found: Optional[str] = None
    for event in events:
        result = event.get("result", {})
        # Path 1: result.contextId
        ctx = result.get("contextId")
        if ctx:
            found = ctx
            continue
        # Path 2: result.status.message.metadata.conversationId (same as chat response)
        ctx = (
            result.get("status", {})
            .get("message", {})
            .get("metadata", {})
            .get("conversationId")
        )
        if ctx:
            found = ctx
    return found


def get_conversation_history(
    api_key: str,
    app_id: str,
    full: bool = False,
    limit: Optional[int] = None,
    fetch_timeout: int = 10,
) -> list[dict]:
    """Parse trajectory events into a human-readable conversation history.

    Returns a list of dicts, each representing one meaningful conversation turn:
      {"eventId": int, "role": str, "type": str, "content": str}

    Roles: "user", "agent", "system"
    Types: "message", "file", "status", "action"
    """
    events, _, _ = fetch_trajectory_once(
        api_key, app_id, last_event_id=-1, timeout=fetch_timeout,
    )

    history: list[dict] = []
    max_content = 200 if not full else 100_000

    for event in events:
        result = event.get("result", {})
        role = result.get("role", "")
        metadata = result.get("metadata", {})
        event_id = metadata.get("eventId")
        state = result.get("status", {}).get("state", "") if isinstance(result.get("status"), dict) else ""

        parts = result.get("parts", [])
        content_pieces: list[str] = []
        entry_type = "message"

        for p in parts:
            kind = p.get("kind", "")
            if kind == "text":
                text = p.get("text", "").strip()
                if text:
                    content_pieces.append(text[:max_content])
            elif kind == "data":
                data = p.get("data", {})
                dtype = data.get("type", "")
                if dtype == "filePart":
                    fname = data.get("filename", "")
                    ftext = data.get("text", "").strip()
                    entry_type = "file"
                    if full and ftext:
                        content_pieces.append(f"[file: {fname}] {ftext[:max_content]}")
                    else:
                        content_pieces.append(f"[file: {fname}]")
                elif dtype == "extension":
                    ext = data.get("extension", {})
                    content_pieces.append(f"[style: {ext.get('name', '')}]")
                elif dtype == "userConfirmation":
                    entry_type = "action"
                    content_pieces.append(f"[confirm: {data.get('type', '')}]")
                elif dtype == "file_edit_action":
                    entry_type = "action"
                    action = data.get("action_name", data.get("action", ""))
                    path = data.get("path", "")
                    content_pieces.append(f"[{action}: {path}]")
                elif dtype == "cmd_run_observation":
                    entry_type = "action"
                    content_pieces.append(f"[cmd: {data.get('observation', '')}]")

        content = " ".join(content_pieces).strip()

        if role in ("user", "agent"):
            if content:
                history.append({
                    "eventId": event_id,
                    "role": role,
                    "type": entry_type,
                    "content": content,
                })
        elif state and state != "working":
            history.append({
                "eventId": event_id,
                "role": "system",
                "type": "status",
                "content": f"state={state}",
            })

    if limit is not None and limit > 0:
        history = history[-limit:]

    return history


# ---------------------------------------------------------------------------
# 5. Publish App
# ---------------------------------------------------------------------------

def publish_app(
    api_key: str,
    app_id: str,
    app_env: str = "PRODUCE",
    enable_weapp_mini_program: bool = False,
    is_release_app_square: bool = False,
) -> dict:
    """POST /api/v1/app/release — triggers a release, returns releaseId.

    The Weixin mini program channel is OFF by default (web channel only).
    It is enabled only when the caller passes ``enable_weapp_mini_program=True``
    (CLI: ``publish --enable-weapp-mini-program``) after the user has explicitly
    confirmed that channel.
    """
    url = _api_url("/api/v1/app/release")
    payload = {
        "appId": app_id,
        "appEnv": app_env,
        "enableWeappMiniProgram": bool(enable_weapp_mini_program),
        "isReleaseAppSquare": is_release_app_square,
    }
    resp = _API.post(url, json=payload, headers=auth_headers(api_key), timeout=120)
    resp.raise_for_status()
    body = resp.json()
    if body.get("status") != 0:
        msg = body.get("msg") or body.get("message") or ""
        _raise_if_insufficient_credits(msg)
        raise RuntimeError(f"Publish failed (status={body.get('status')}): {msg}")
    return body


def get_publish_status(
    api_key: str,
    release_id: str,
) -> dict:
    """GET /api/v1/app/release/status/{release_id}"""
    url = _api_url(f"/api/v1/app/release/status/{release_id}")
    resp = _API.get(url, headers=auth_headers(api_key), timeout=120)
    resp.raise_for_status()
    return resp.json()


def publish_and_wait(
    api_key: str,
    app_id: str,
    app_env: str = "PRODUCE",
    poll_interval: float = 3,
    max_wait: Optional[float] = None,
    enable_weapp_mini_program: bool = False,
) -> dict:
    """Publish an app and poll until SUCCESS or FAILED (bounded by max_wait).

    Uses the same channel setting as ``publish_app`` (Weixin mini program off
    unless explicitly enabled).
    """
    interval, _, wait = _clamp_poll_settings(
        poll_interval, 10, max_wait, PUBLISH_DEFAULT_MAX_WAIT, PUBLISH_MAX_WAIT_LIMIT,
    )
    result = publish_app(api_key, app_id, app_env, enable_weapp_mini_program=enable_weapp_mini_program)

    release_id = result.get("data", {}).get("releaseId")
    if not release_id:
        raise RuntimeError("No releaseId in publish response")

    print(json.dumps({"releaseId": release_id, "status": "PROCESSING"}, ensure_ascii=False), flush=True)

    deadline = time.monotonic() + wait
    while True:
        status_result = get_publish_status(api_key, release_id)
        data = status_result.get("data", {})
        status = data.get("status", "UNKNOWN")

        print(json.dumps({"releaseId": release_id, "status": status}, ensure_ascii=False), flush=True)

        if status == "SUCCESS":
            return status_result
        if status == "FAILED":
            raise RuntimeError(f"Publish FAILED (releaseId={release_id})")

        if time.monotonic() + interval > deadline:
            print(json.dumps({"status": "TIMEOUT", "releaseId": release_id, "maxWaitSeconds": wait,
                              "resume": f"python3 scripts/miaoda_api.py publish-status --release-id {release_id}"},
                             ensure_ascii=False), flush=True)
            raise TimeoutError(f"Publish timed out after {int(wait)}s (releaseId={release_id}); check publish-status")

        time.sleep(interval)


def _find_public_url(value: object) -> Optional[str]:
    """Find a public app URL from the response's explicit data fields.

    Do not recurse through arbitrary business objects: fields such as API or
    editor URLs can otherwise be mistaken for the app delivery URL.
    """
    preferred_keys = ("appHost", "publicUrl", "publishUrl", "appUrl", "webUrl", "url")
    ignored_hosts = {"api.miaoda.cn", "www.miaoda.cn", "miaoda.cn"}

    def valid(candidate: object, allow_host: bool = False) -> Optional[str]:
        if not isinstance(candidate, str) or not candidate.strip():
            return None
        candidate = candidate.strip()
        if allow_host and "://" not in candidate:
            candidate = f"https://{candidate.lstrip('/')}"
        if not candidate.startswith(("http://", "https://")):
            return None
        parsed = urlparse(candidate)
        if not parsed.hostname or parsed.hostname.lower() in ignored_hosts or "/projects/" in parsed.path:
            return None
        return candidate

    if not isinstance(value, dict):
        return None
    data = value.get("data")
    if not isinstance(data, dict):
        data = value
    for key in preferred_keys:
        found = valid(data.get(key), allow_host=key == "appHost")
        if found:
            return found
    return None


def _editor_home_url(public_url: str) -> str:
    """Return the Miaoda editor host."""
    return "https://www.miaoda.cn"


def emit_mcp_app_marker(
    api_key: str,
    app_id: str,
    publish_result: dict,
    fetch_detail: bool = True,
) -> None:
    """Print an mcp-app marker only after a real public URL is confirmed."""
    detail = None
    public_url = _find_public_url(publish_result)
    if fetch_detail:
        try:
            detail = get_app_detail(api_key, app_id)
            public_url = public_url or _find_public_url(detail)
        except Exception as exc:
            print(f"[mcp-app] app-detail lookup failed: {exc}", file=sys.stderr)
    if not public_url:
        print("[mcp-app] no public URL returned; marker omitted", file=sys.stderr)
        return

    name = ""
    for source in (publish_result, detail or {}):
        data = source.get("data", source) if isinstance(source, dict) else {}
        if isinstance(data, dict) and isinstance(data.get("name"), str) and data["name"]:
            name = data["name"]
            break
    marker = {
        "name": name or app_id,
        "url": public_url,
        "source": "miaoda",
        "editUrl": f"{_editor_home_url(public_url)}/projects/{app_id}",
    }
    # Keep the marker protocol platform-independent: Windows stdout otherwise
    # translates each newline to CRLF, while consumers expect LF-delimited fences.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(newline="\n")
    print("```mcp-app", flush=True)
    print(json.dumps(marker, ensure_ascii=False, separators=(",", ":")), flush=True)
    print("```", flush=True)


# ---------------------------------------------------------------------------
# 6. Download Generated Artifacts
# ---------------------------------------------------------------------------

def _app_context_headers(api_key: str, app_id: str, app_env: str = "DEV") -> dict:
    """Build auth headers with app context for endpoints using ResourceContext."""
    headers = auth_headers(api_key)
    headers["x-app-id"] = app_id
    headers["x-app-env"] = app_env
    return headers


def download_source(api_key: str, app_id: str, app_env: str = "DEV") -> dict:
    """POST /api/v1/app/operation/download — return full source ZIP download info."""
    url = _api_url("/api/v1/app/operation/download")
    payload = {"appId": app_id, "env": app_env}
    resp = _API.post(url, json=payload, headers=_app_context_headers(api_key, app_id, app_env), timeout=60)
    return raise_for_api_error(resp)


def list_task_files(
    api_key: str,
    app_id: str,
    include_docs_dir: bool = False,
) -> dict:
    """GET /api/v1/app/agent_workspace/task_directory — list Agent task files."""
    url = _api_url("/api/v1/app/agent_workspace/task_directory")
    params = {"appId": app_id, "includeDocsDir": str(include_docs_dir).lower()}
    resp = _API.get(url, params=params, headers=auth_headers(api_key), timeout=30)
    return raise_for_api_error(resp)


def reveal_task_file(api_key: str, app_id: str, filename: str) -> dict:
    """GET /api/v1/app/agent_workspace/task_directory/reveal — return original and thumbnail URLs."""
    url = _api_url("/api/v1/app/agent_workspace/task_directory/reveal")
    params = {"appId": app_id, "filename": filename}
    resp = _API.get(url, params=params, headers=auth_headers(api_key), timeout=30)
    return raise_for_api_error(resp)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    """Construct and return the top-level argument parser with all subcommands."""
    parser = argparse.ArgumentParser(
        description=(
            "Miaoda Platform API CLI. Authenticated requests always go to "
            f"{API_BASE_URL} (not configurable)."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--api-key",
        default=os.environ.get("MIAODA_API_KEY"),
        help="Bearer token (or set MIAODA_API_KEY env var)",
    )

    sub = parser.add_subparsers(dest="command", required=True)

    # list-apps
    p = sub.add_parser("list-apps", help="List apps with basic info (paginated)")
    p.add_argument("--name", default="", help="Filter by app name (substring)")
    p.add_argument("--page", type=int, default=1)
    p.add_argument("--size", type=int, default=12)
    p.add_argument(
        "--brief",
        action="store_true",
        help="Output only key fields: appId, name, type, appFocus, host, updatedAt (reduces token usage)",
    )

    # app-detail
    p = sub.add_parser("app-detail", help="Get app detail by ID (auto-injects conversationId by default)")
    p.add_argument("--app-id", required=True, help="Application ID")
    p.add_argument(
        "--no-context",
        action="store_true",
        help="Skip auto-fetching conversationId from trajectory (faster but no contextId in response)",
    )

    # chat
    p = sub.add_parser("chat", help="Send a chat message and stream the response")
    p.add_argument("--text", required=True, help="Message text (user query)")
    p.add_argument(
        "--context-id",
        default="",
        help="conversationId of an existing app. Leave empty to create a new app (default: '')",
    )
    p.add_argument("--app-id", default=None, help="App ID (optional, improves routing for existing apps)")
    p.add_argument(
        "--query-mode",
        default="deep_mode",
        help="Query mode (default: deep_mode)",
    )
    p.add_argument(
        "--input-field-type",
        default="web",
        help="Input field type (default: web)",
    )
    p.add_argument(
        "--no-stream",
        action="store_true",
        help="Return raw chat POST response without trajectory polling",
    )
    p.add_argument(
        "--prompt-generate",
        action="store_true",
        help="After polling, interactively ask whether to submit app generation if text was returned",
    )
    p.add_argument(
        "--poll-interval",
        type=float,
        default=2.0,
        help="Seconds between trajectory polls (default: 2.0)",
    )
    p.add_argument(
        "--fetch-timeout",
        type=int,
        default=10,
        help="Per-request timeout in seconds for each trajectory fetch (default: 10)",
    )
    p.add_argument(
        "--max-wait",
        type=float,
        default=None,
        help="Stop polling after this many seconds (default: 1800, max: 7200); the task keeps running on the platform",
    )
    p.add_argument(
        "--node-json",
        default=None,
        help=(
            "LGUI mode: JSON string describing the currently-selected UI node "
            "(file path, line range, tag, styles, etc.). When set, an extra "
            "kind:'data' part is appended to message.parts so the Agent can "
            "pinpoint the exact node instead of searching the codebase. "
            "Accepts either the raw node object or a pre-wrapped "
            "'{\"type\":\"node\",\"node\":{...}}'."
        ),
    )

    # generate-app
    p = sub.add_parser(
        "generate-app",
        help="Submit app generation confirmation and return immediately with appId/conversationId",
    )
    p.add_argument("--context-id", default="", help="conversationId of the app to generate")
    p.add_argument("--app-id", default=None, help="App ID (optional)")
    p.add_argument("--query-mode", default="deep_mode", help="Query mode (default: deep_mode)")
    p.add_argument(
        "--watch",
        action="store_true",
        help="Block and poll trajectory until generation completes (default: return immediately)",
    )
    p.add_argument(
        "--poll-interval",
        type=float,
        default=2.0,
        help="Seconds between polls when --watch is set (default: 2.0)",
    )
    p.add_argument(
        "--fetch-timeout",
        type=int,
        default=10,
        help="Per-request timeout in seconds when --watch is set (default: 10)",
    )
    p.add_argument(
        "--max-wait",
        type=float,
        default=None,
        help="Stop polling after this many seconds (default: 1800, max: 7200); the task keeps running on the platform",
    )

    # trajectory  (polling, default)
    p = sub.add_parser(
        "trajectory",
        help="Poll trajectory until terminal state (non-SSE, default)",
    )
    p.add_argument("--app-id", required=True, help="Application ID")
    p.add_argument(
        "--last-event-id",
        type=int,
        default=-1,
        help="Start eventId: -1 = all events from beginning (default: -1)",
    )
    p.add_argument(
        "--poll-interval",
        type=float,
        default=2.0,
        help="Seconds between polls (default: 2.0)",
    )
    p.add_argument(
        "--fetch-timeout",
        type=int,
        default=10,
        help="Per-request timeout in seconds for each trajectory fetch (default: 10)",
    )
    p.add_argument(
        "--sse",
        action="store_true",
        help="Use legacy SSE streaming instead of polling",
    )
    p.add_argument(
        "--max-wait",
        type=float,
        default=None,
        help="Stop polling after this many seconds (default: 1800, max: 7200); the task keeps running on the platform",
    )

    # get-context-id
    p = sub.add_parser(
        "get-context-id",
        help="Retrieve the conversationId (contextId) for an existing app from its trajectory",
    )
    p.add_argument("--app-id", required=True, help="Application ID")
    p.add_argument(
        "--fetch-timeout",
        type=int,
        default=10,
        help="Request timeout in seconds (default: 10)",
    )

    # conversation-history
    p = sub.add_parser(
        "conversation-history",
        help="Show human-readable conversation history for an app",
    )
    p.add_argument("--app-id", required=True, help="Application ID")
    p.add_argument(
        "--full",
        action="store_true",
        help="Show full content instead of truncated summaries (default: truncate at 200 chars)",
    )
    p.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Only show the last N conversation turns",
    )
    p.add_argument(
        "--fetch-timeout",
        type=int,
        default=10,
        help="Request timeout in seconds (default: 10)",
    )

    # fetch-trajectory  (single non-SSE fetch, no polling loop)
    p = sub.add_parser(
        "fetch-trajectory",
        help="Fetch one batch of trajectory events without polling (stream=false)",
    )
    p.add_argument("--app-id", required=True, help="Application ID")
    p.add_argument(
        "--last-event-id",
        type=int,
        default=-1,
        help="Fetch events after this eventId; -1 = all (default: -1)",
    )
    p.add_argument(
        "--fetch-timeout",
        type=int,
        default=10,
        help="Request timeout in seconds (default: 10)",
    )

    # publish
    p = sub.add_parser("publish", help="Publish an app")
    p.add_argument("--app-id", required=True, help="Application ID to publish")
    p.add_argument("--env", default="PRODUCE", help="Target environment (default: PRODUCE)")
    p.add_argument(
        "--wait",
        action="store_true",
        help="Poll publish status until SUCCESS, FAILED or --max-wait",
    )
    p.add_argument(
        "--max-wait",
        type=float,
        default=None,
        help="With --wait: stop polling after this many seconds (default: 300, max: 1800)",
    )
    p.add_argument(
        "--poll-interval",
        type=float,
        default=3.0,
        help="With --wait: seconds between status checks (default: 3, range 1-60)",
    )
    p.add_argument(
        "--enable-weapp-mini-program",
        action="store_true",
        help="Also publish to the Weixin mini program channel (default: off). Use only after the user explicitly confirms this channel",
    )

    # publish-status
    p = sub.add_parser("publish-status", help="Get publish status by release ID")
    p.add_argument("--release-id", required=True, help="Release record ID from publish command")

    # download-source
    p = sub.add_parser("download-source", help="Download the full generated app source ZIP")
    p.add_argument("--app-id", required=True, help="Application ID")
    p.add_argument("--env", default="DEV", help="Source environment (default: DEV)")
    p.add_argument(
        "--output",
        default=None,
        help="File NAME only (no path). Saved under ./miaoda-downloads/; existing files are never overwritten",
    )
    p.add_argument("--print-url", action="store_true", help="Print download URL without saving file")

    # list-task-files
    p = sub.add_parser("list-task-files", help="List Agent workspace task files")
    p.add_argument("--app-id", required=True, help="Application ID")
    p.add_argument("--include-docs-dir", action="store_true", help="Include docs directory files")

    # download-task-file
    p = sub.add_parser("download-task-file", help="Download one Agent workspace task file")
    p.add_argument("--app-id", required=True, help="Application ID")
    p.add_argument("--filename", required=True, help="Task filename or /workspace/{appId}/tasks/... path")
    p.add_argument(
        "--output",
        default=None,
        help="File NAME only (no path). Saved under ./miaoda-downloads/; existing files are never overwritten",
    )
    p.add_argument("--print-url", action="store_true", help="Print download URL without saving file")

    return parser


def main():
    """Parse CLI arguments and dispatch to the appropriate API function."""
    parser = build_parser()
    args = parser.parse_args()

    if not args.api_key:
        print(
            "Error: API key required. Open https://www.miaoda.cn/ and sign in, then choose "
            "avatar → 秒哒 Skill → 复制密钥. Set MIAODA_API_KEY in the environment that "
            "runs the Qoder task and retry. Keep the key out of chat and command arguments.",
            file=sys.stderr,
        )
        sys.exit(1)

    try:
        if args.command == "list-apps":
            result = list_apps(
                args.api_key, args.name, args.page, args.size,
                brief=args.brief,
            )
            print(json.dumps(result, ensure_ascii=False, indent=2))

        elif args.command == "app-detail":
            result = get_app_detail(args.api_key, args.app_id)
            if not args.no_context:
                try:
                    context_id = get_context_id(args.api_key, args.app_id)
                    if context_id:
                        result.setdefault("data", {})["conversationId"] = context_id
                except Exception:
                    pass  # non-fatal: app may have no conversation history yet
            print(json.dumps(result, ensure_ascii=False, indent=2))
            emit_mcp_app_marker(
                args.api_key, args.app_id, result, fetch_detail=False,
            )

        elif args.command == "chat":
            node = None
            if args.node_json:
                try:
                    node = json.loads(args.node_json)
                except json.JSONDecodeError as exc:
                    print(
                        f"Error: --node-json is not valid JSON: {exc}",
                        file=sys.stderr,
                    )
                    sys.exit(1)
                if not isinstance(node, dict):
                    print(
                        "Error: --node-json must be a JSON object, "
                        f"got {type(node).__name__}.",
                        file=sys.stderr,
                    )
                    sys.exit(1)
            if args.no_stream:
                result = chat_no_stream(
                    args.api_key, args.text,
                    args.context_id, args.app_id,
                    args.query_mode, args.input_field_type,
                    node=node,
                )
                print(json.dumps(result, ensure_ascii=False, indent=2))
            else:
                chat_stream(
                    args.api_key, args.text,
                    args.context_id, args.app_id,
                    args.query_mode, args.input_field_type,
                    prompt_generate=args.prompt_generate,
                    poll_interval=args.poll_interval,
                    fetch_timeout=args.fetch_timeout,
                    node=node,
                    max_wait=args.max_wait,
                )

        elif args.command == "generate-app":
            generate_app_confirmation(
                args.api_key,
                context_id=args.context_id,
                app_id=args.app_id,
                query_mode=args.query_mode,
                watch=args.watch,
                poll_interval=args.poll_interval,
                fetch_timeout=args.fetch_timeout,
                max_wait=args.max_wait,
            )

        elif args.command == "trajectory":
            if args.sse:
                stream_trajectory(
                    args.api_key, args.app_id, args.last_event_id,
                    max_wait=args.max_wait,
                )
            else:
                poll_trajectory(
                    args.api_key, args.app_id,
                    last_event_id=args.last_event_id,
                    poll_interval=args.poll_interval,
                    fetch_timeout=args.fetch_timeout,
                    max_wait=args.max_wait,
                )

        elif args.command == "get-context-id":
            context_id = get_context_id(
                args.api_key, args.app_id,
                fetch_timeout=args.fetch_timeout,
            )
            if context_id:
                print(json.dumps({"appId": args.app_id, "conversationId": context_id}, ensure_ascii=False))
            else:
                print(
                    f"Error: Could not find conversationId for app {args.app_id}. "
                    "The app may have no conversation history.",
                    file=sys.stderr,
                )
                sys.exit(1)

        elif args.command == "conversation-history":
            history = get_conversation_history(
                args.api_key, args.app_id,
                full=args.full,
                limit=args.limit,
                fetch_timeout=args.fetch_timeout,
            )
            for entry in history:
                print(json.dumps(entry, ensure_ascii=False))

        elif args.command == "fetch-trajectory":
            events, max_event_id, is_terminal = fetch_trajectory_once(
                args.api_key, args.app_id, args.last_event_id,
                timeout=args.fetch_timeout,
            )
            for event in events:
                print(json.dumps(event, ensure_ascii=False))
            print(
                json.dumps({"maxEventId": max_event_id, "isTerminal": is_terminal}, ensure_ascii=False),
                file=sys.stderr,
            )

        elif args.command == "publish":
            if args.wait:
                result = publish_and_wait(
                    args.api_key, args.app_id, args.env,
                    poll_interval=args.poll_interval,
                    max_wait=args.max_wait,
                    enable_weapp_mini_program=args.enable_weapp_mini_program,
                )
                print(json.dumps(result, ensure_ascii=False, indent=2))
                emit_mcp_app_marker(args.api_key, args.app_id, result)
            else:
                result = publish_app(
                    args.api_key, args.app_id, args.env,
                    enable_weapp_mini_program=args.enable_weapp_mini_program,
                )
                print(json.dumps(result, ensure_ascii=False, indent=2))
                emit_mcp_app_marker(
                    args.api_key, args.app_id, result, fetch_detail=False,
                )

        elif args.command == "publish-status":
            result = get_publish_status(
                args.api_key, args.release_id,
            )
            print(json.dumps(result, ensure_ascii=False, indent=2))

        elif args.command == "download-source":
            result = download_source(args.api_key, args.app_id, args.env)
            data = result.get("data") or {}
            download_url = data.get("downloadUrl")
            if not download_url:
                raise RuntimeError("downloadUrl missing in response")
            if args.print_url:
                print(json.dumps(result, ensure_ascii=False, indent=2))
            else:
                local_path = _download_url_to_file(
                    download_url,
                    args.output,
                    default_name=f"{args.app_id}-source.zip",
                )
                data["localPath"] = local_path
                print(json.dumps(data, ensure_ascii=False, indent=2))

        elif args.command == "list-task-files":
            result = list_task_files(
                args.api_key, args.app_id, args.include_docs_dir,
            )
            print(json.dumps(result, ensure_ascii=False, indent=2))

        elif args.command == "download-task-file":
            result = reveal_task_file(args.api_key, args.app_id, args.filename)
            data = result.get("data") or {}
            download_url = data.get("url") or data.get("downloadUrl")
            if not download_url:
                raise RuntimeError("download url missing in response")
            if args.print_url:
                print(json.dumps(result, ensure_ascii=False, indent=2))
            else:
                default_name = _safe_filename(args.filename, f"{args.app_id}-task-file")
                local_path = _download_url_to_file(download_url, args.output, default_name=default_name)
                data["appId"] = args.app_id
                data["filename"] = args.filename
                data["downloadUrl"] = download_url
                data["localPath"] = local_path
                print(json.dumps(data, ensure_ascii=False, indent=2))

    except KeyboardInterrupt:
        sys.exit(0)
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
