#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Sync Qoder CLI (qodercli / qoderclicn) transcripts into the Qoder desktop app.

The Qoder desktop app keeps its session list in a local SQLite database
(main.sqlite) and lazily projects the full conversation from the CLI
transcript when a session is opened. Sessions created with the CLI never get a
row in that database, so they are invisible in the app.

This script registers missing CLI sessions in the app database and copies the
conversation into the app's own message table using the same payload format the
app's built-in CLI importer writes. The app only hydrates history lazily for
sessions it created itself, so imported sessions must carry their messages
up front or they open empty. Only rows created by this script are ever touched;
the script is idempotent and never deletes native app sessions.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sqlite3
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

IS_WINDOWS = os.name == "nt"
APP_ID_CN = "com.qodercn.app.stable"
APP_ID_INTL = "com.qoder.app.stable"

SKIP_TYPES = {
    "active-leaf",
    "runtime-config",
    "workspace-directories",
    "worktree-state",
    "attachment",
    "file-history-snapshot",
    "summary",
}

# Bump when the JSONL -> message conversion changes so old imports get rewritten.
MESSAGE_FORMAT_VERSION = 7

# Oldest backups beyond this count are removed, since sync now runs each turn.
BACKUP_KEEP = 20

COMMAND_NAME_RE = re.compile(r"<command-name>\s*(.*?)\s*</command-name>", re.S)
COMMAND_ARGS_RE = re.compile(r"<command-args>\s*(.*?)\s*</command-args>", re.S)
COMMAND_MESSAGE_RE = re.compile(r"<command-message>\s*(.*?)\s*</command-message>", re.S)
SKILL_LINK_RE = re.compile(r"\[@[^\]]*\]\(skill://([^)]+)\)")
COMMAND_LINK_RE = re.compile(r"\[@[^\]]*\]\(command://([^)]+)\)")


def log(msg: str, quiet: bool = False) -> None:
    if not quiet:
        print(msg)


def app_data_dirs() -> list[Path]:
    home = Path.home()
    if IS_WINDOWS:
        roaming = Path(os.environ.get("APPDATA", home / "AppData" / "Roaming"))
        return [roaming / APP_ID_CN, roaming / APP_ID_INTL]
    if sys.platform == "darwin":
        base = home / "Library" / "Application Support"
    else:
        base = Path(os.environ.get("XDG_CONFIG_HOME", home / ".config"))
    return [base / APP_ID_CN, base / APP_ID_INTL]


def find_app_db(explicit: str | None) -> Path:
    if explicit:
        p = Path(explicit).expanduser()
        if not p.is_file():
            raise SystemExit(f"App database not found: {p}")
        return p
    for d in app_data_dirs():
        candidate = d / "main.sqlite"
        if candidate.is_file():
            return candidate
    raise SystemExit(
        "Could not find the Qoder app database (main.sqlite). "
        "Open the Qoder app once, or pass --db <path>."
    )


def cli_project_roots(app_db: Path, existing_ids: set[str]) -> list[Path]:
    """Pick the CLI data folder that matches this app database.

    A standard app database only reads its own edition's CLI folder; mixing
    editions would import sessions into the wrong app. A custom database path
    falls back to whichever folder owns session ids the database already knows.
    """
    home = Path.home()
    cn = home / ".qoder-cn" / "projects"
    intl = home / ".qoder" / "projects"
    db_parent = str(app_db.parent).lower()
    if "qodercn" in db_parent:
        return [cn] if cn.is_dir() else []
    if "com.qoder.app" in db_parent:
        return [intl] if intl.is_dir() else []
    candidates = [cn, intl]

    def score(root: Path) -> int:
        if not root.is_dir():
            return -1
        return sum(1 for p in root.rglob("*.jsonl") if p.stem in existing_ids)

    ranked = sorted(candidates, key=score, reverse=True)
    best = ranked[0] if ranked else None
    if best is None or score(best) <= 0:
        best = next((p for p in candidates if p.is_dir()), None)
    return [best] if best else []


def read_jsonl(path: Path) -> list[dict]:
    entries = []
    try:
        with path.open("r", encoding="utf-8", errors="replace") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except Exception:
                    continue
                if isinstance(obj, dict):
                    entries.append(obj)
    except OSError:
        return []
    return entries


def content_text(message) -> str:
    if isinstance(message, str):
        return message
    if not isinstance(message, dict):
        return ""
    content = message.get("content")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                parts.append(str(block.get("text") or ""))
        return "\n".join(parts)
    return ""


def clean_title(text: str) -> str:
    text = re.sub(r"<[^>]+>.*?</[^>]+>", " ", text, flags=re.S)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def is_noise_text(text: str) -> bool:
    t = text.strip()
    if not t:
        return True
    if t.startswith(("<local-command", "<command-name>", "<command-message>", "<command-args>")):
        return True
    if t.startswith("[Request interrupted"):
        return True
    return False


def summarize(path: Path) -> dict | None:
    """Extract the facts needed to register a CLI session."""
    entries = read_jsonl(path)
    if not entries:
        return None

    session_id = path.stem
    cwd = None
    title = None
    model = None
    permission_mode = None
    git_branch = None
    created = None
    updated = None
    human_messages = 0

    for obj in entries:
        ts = obj.get("timestamp")
        if isinstance(ts, str):
            try:
                dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                ms = int(dt.timestamp() * 1000)
                created = ms if created is None else min(created, ms)
                updated = ms if updated is None else max(updated, ms)
            except Exception:
                pass
        elif isinstance(ts, (int, float)) and ts > 0:
            ms = int(ts if ts > 1e12 else ts * 1000)
            created = ms if created is None else min(created, ms)
            updated = ms if updated is None else max(updated, ms)

        if cwd is None and isinstance(obj.get("cwd"), str) and obj["cwd"].strip():
            cwd = obj["cwd"].strip()
        if git_branch is None and isinstance(obj.get("gitBranch"), str) and obj["gitBranch"].strip():
            git_branch = obj["gitBranch"].strip()
        if permission_mode is None and isinstance(obj.get("permissionMode"), str):
            permission_mode = obj["permissionMode"]
        if obj.get("type") == "runtime-config" and isinstance(obj.get("model"), str) and obj["model"].strip():
            model = obj["model"].strip()

        if obj.get("type") != "user" or obj.get("isSidechain") or is_hidden_entry(obj):
            continue
        human = obj.get("humanInput")
        # Slash-command invocations are tagged isMeta but still carry the real
        # human input; dropping them would hide sessions made only of commands.
        if obj.get("isMeta") and not (
            isinstance(human, dict) and str(human.get("text") or "").strip()
        ):
            continue
        text = ""
        if isinstance(human, dict) and str(human.get("text") or "").strip():
            text = str(human["text"])
        else:
            origin = obj.get("origin")
            if isinstance(origin, dict) and origin.get("kind") not in (None, "human"):
                continue
            raw = content_text(obj.get("message"))
            envelope = parse_command_envelope(raw)
            # clean_title would strip an envelope down to nothing, so keep the
            # command itself as the title for command-only sessions.
            text = ("/" + envelope[0] + (f" {envelope[1]}" if envelope[1] else "")
                    if envelope else raw)
        text = clean_title(text)
        if is_noise_text(text):
            continue
        human_messages += 1
        if title is None:
            title = text[:120]

    if not cwd:
        return None
    if title is None:
        return None
    if not updated:
        updated = int(path.stat().st_mtime * 1000)
    if not created:
        created = updated

    return {
        "session_id": session_id,
        "path": path,
        "cwd": cwd,
        "title": title,
        "model": model or "auto",
        "permission_mode": permission_mode or "default",
        "git_branch": git_branch,
        "created_at": created,
        "updated_at": updated,
        "human_messages": human_messages,
    }


def iso_to_ms(ts) -> int | None:
    if isinstance(ts, (int, float)) and ts > 0:
        return int(ts if ts > 1e12 else ts * 1000)
    if isinstance(ts, str) and ts.strip():
        try:
            dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return int(dt.timestamp() * 1000)
        except Exception:
            return None
    return None


def ms_to_iso(ms: int | None) -> str:
    if not ms:
        return ""
    dt = datetime.fromtimestamp(ms / 1000, tz=timezone.utc)
    return dt.isoformat(timespec="milliseconds").replace("+00:00", "Z")


def block_text(block) -> str:
    if isinstance(block, str):
        return block
    if not isinstance(block, dict):
        return ""
    if block.get("type") == "text":
        return str(block.get("text") or "")
    if block.get("type") == "image":
        return "[image]"
    return ""


def result_text(block) -> str:
    content = block.get("content")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "\n".join(t for t in (block_text(b) for b in content) if t)
    return ""


def command_display(command: str, args: str = "", is_skill: bool = False) -> str:
    """Render a slash command the way the app renders its own capability chips."""
    command = command.strip().lstrip("/")
    args = args.strip()
    scheme = "skill" if is_skill else "command"
    # Skill chips show the plugin prefix; command chips keep the full command.
    label = command.split(":", 1)[0] if is_skill else command
    text = f"[@{label}]({scheme}://{command})"
    return f"{text} {args}".strip()


def parse_command_envelope(text: str):
    """Return (command, args) when the text is only a slash-command envelope."""
    if "<command-name>" not in text and "<command-message>" not in text:
        return None
    rest = COMMAND_ARGS_RE.sub("", text)
    rest = COMMAND_NAME_RE.sub("", rest)
    rest = COMMAND_MESSAGE_RE.sub("", rest)
    if rest.strip():
        return None
    message = COMMAND_MESSAGE_RE.search(text)
    name = COMMAND_NAME_RE.search(text)
    command = (message.group(1) if message else name.group(1)).strip()
    args = COMMAND_ARGS_RE.search(text)
    return command.lstrip("/"), (args.group(1).strip() if args else "")


def normalize_user_text(text: str) -> str:
    """Render a slash-command envelope as the command chip the app knows."""
    envelope = parse_command_envelope(text)
    if envelope:
        return command_display(*envelope)
    # Plain "/name" prompts stay untouched so the skill-body check can still
    # turn real skill invocations into skill:// chips.
    return text


def human_turn_text(obj: dict) -> str | None:
    """Return the human prompt text, or None when the entry is not a prompt."""
    message = obj.get("message")
    content = message.get("content") if isinstance(message, dict) else None
    blocks = content if isinstance(content, list) else []
    has_result = any(isinstance(b, dict) and b.get("type") == "tool_result" for b in blocks)
    human = obj.get("humanInput")
    if isinstance(human, dict) and str(human.get("text") or "").strip():
        return normalize_user_text(str(human["text"]))
    if has_result and not any(isinstance(b, dict) and b.get("type") == "text" for b in blocks):
        return None
    if obj.get("isMeta"):
        return None
    origin = obj.get("origin")
    if isinstance(origin, dict) and origin.get("kind") not in (None, "human"):
        return None
    if isinstance(content, str):
        text = content
    else:
        text = "\n".join(t for t in (block_text(b) for b in blocks) if t)
    if text.startswith("[Request interrupted"):
        return None
    text = normalize_user_text(text)
    return text if text.strip() else None


def is_hidden_entry(obj: dict) -> bool:
    """Compaction summaries are transcript-only and must not become user turns."""
    return bool(obj.get("isCompactSummary") or obj.get("isVisibleInTranscriptOnly"))


def build_messages(path: Path) -> list[dict]:
    """Convert a CLI transcript into app message rows (legacy cli-import shape)."""
    entries = read_jsonl(path)
    turns: list[dict] = []
    tools: dict[str, dict] = {}
    current: dict | None = None

    # A slash command is recorded twice: once as a <command-name> envelope and
    # once as the real prompt (sometimes only the envelope exists). Drop the
    # envelope when the prompt carries the same input, so the turn is not doubled.
    human_prompts = []
    for index, obj in enumerate(entries):
        if obj.get("type") != "user" or obj.get("isSidechain") or is_hidden_entry(obj):
            continue
        human = obj.get("humanInput")
        if isinstance(human, dict) and str(human.get("text") or "").strip():
            human_prompts.append(
                (
                    index,
                    obj.get("promptId"),
                    str(human["text"]).strip(),
                    iso_to_ms(obj.get("timestamp")),
                )
            )
    skip_envelopes: set[int] = set()
    for index, obj in enumerate(entries):
        if obj.get("type") != "user" or obj.get("isSidechain") or is_hidden_entry(obj):
            continue
        envelope = parse_command_envelope(content_text(obj.get("message")))
        if not envelope:
            continue
        prompt_id = obj.get("promptId")
        if prompt_id and any(pid == prompt_id for _, pid, _, _ in human_prompts):
            skip_envelopes.add(index)
            continue
        command = envelope[0]
        for pos, _, prompt_text, _ in human_prompts:
            if pos <= index:
                continue
            prompt_command = prompt_text.lstrip("/").split(" ", 1)[0]
            if prompt_command == command:
                skip_envelopes.add(index)
            break

    def flush() -> None:
        nonlocal current
        if current is not None:
            turns.append(current)
            current = None

    for index, obj in enumerate(entries):
        if obj.get("isSidechain") or is_hidden_entry(obj) or index in skip_envelopes:
            continue
        etype = obj.get("type")
        if etype == "user":
            message = obj.get("message")
            content = message.get("content") if isinstance(message, dict) else None
            blocks = content if isinstance(content, list) else []
            has_result = False
            for block in blocks:
                if isinstance(block, dict) and block.get("type") == "tool_result":
                    has_result = True
                    tool = tools.get(str(block.get("tool_use_id") or ""))
                    if tool is not None:
                        tool["response"] = result_text(block)
                        if block.get("is_error"):
                            tool["status"] = "failed"
                        completed = obj.get("timestamp")
                        if isinstance(completed, str) and completed:
                            tool["completedAt"] = completed
                            start_ms = iso_to_ms(tool.get("startedAt"))
                            end_ms = iso_to_ms(completed)
                            if start_ms and end_ms and end_ms >= start_ms:
                                tool["durationMs"] = end_ms - start_ms
            text = human_turn_text(obj)
            if text is None:
                continue  # tool results and injected context do not start a turn
            if has_result and not text.strip():
                continue
            # Standalone skills arrive as a plain "/name args" prompt plus the
            # skill body; render them as the app's skill chip.
            if text.startswith("/") and content_text(message).startswith("Base directory for this skill:"):
                head, _, rest = text[1:].partition(" ")
                text = command_display(head, rest, is_skill=True)
            flush()
            uid = str(obj.get("uuid") or uuid.uuid4())
            current = {
                "uid": uid,
                "start_ms": iso_to_ms(obj.get("timestamp")),
                "user_text": text,
                "user_timestamp": obj.get("timestamp"),
                "parts": [],
                "tools": [],
                "texts": [],
            }
        elif etype == "assistant":
            if current is None:
                current = {
                    "uid": str(obj.get("uuid") or uuid.uuid4()),
                    "start_ms": iso_to_ms(obj.get("timestamp")),
                    "user_text": "",
                    "user_timestamp": obj.get("timestamp"),
                    "parts": [],
                    "tools": [],
                    "texts": [],
                }
            message = obj.get("message")
            blocks = message.get("content") if isinstance(message, dict) else None
            if not isinstance(blocks, list):
                continue
            entry_id = str(obj.get("uuid") or uuid.uuid4())
            counters = {"text": 0, "thinking": 0}
            for block in blocks:
                if not isinstance(block, dict):
                    continue
                btype = block.get("type")
                if btype == "text":
                    text = str(block.get("text") or "")
                    if not text.strip():
                        continue
                    counters["text"] += 1
                    current["parts"].append(
                        {
                            "id": f"{entry_id}:text:{counters['text'] - 1}",
                            "type": "text",
                            "text": text,
                            "parentToolUseId": None,
                        }
                    )
                    current["texts"].append(text)
                elif btype == "thinking":
                    text = str(block.get("thinking") or block.get("text") or "")
                    if not text.strip():
                        continue
                    counters["thinking"] += 1
                    current["parts"].append(
                        {
                            "id": f"{entry_id}:thinking:{counters['thinking'] - 1}",
                            "type": "thinking",
                            "text": text,
                            "status": "completed",
                            "parentToolUseId": None,
                        }
                    )
                elif btype == "tool_use":
                    tool_id = str(block.get("id") or uuid.uuid4())
                    tool = {
                        "id": tool_id,
                        "name": str(block.get("name") or "tool"),
                        "input": block.get("input") if isinstance(block.get("input"), dict) else {},
                        "status": "completed",
                        "parentToolUseId": None,
                        "startedAt": obj.get("timestamp") if isinstance(obj.get("timestamp"), str) else None,
                        "response": "",
                    }
                    tools[tool_id] = tool
                    current["tools"].append(tool)
                    current["parts"].append({"id": f"tool:{tool_id}", "type": "tool", "tool": tool})
    flush()

    rows = []
    sequence = 0
    for turn in turns:
        ts = turn["start_ms"]
        if turn["user_text"].strip():
            sequence += 1
            uid = turn["uid"]
            skills = SKILL_LINK_RE.findall(turn["user_text"])
            commands = COMMAND_LINK_RE.findall(turn["user_text"])
            rows.append(
                {
                    "message_id": uid,
                    "turn_id": uid,
                    "sequence": sequence,
                    "created_at": ts or 0,
                    "payload": {
                        "id": uid,
                        "role": "user",
                        "turnId": uid,
                        "issueId": None,
                        "text": turn["user_text"],
                        "timestamp": turn["user_timestamp"] or ms_to_iso(ts),
                        "tools": [],
                        "attachments": [],
                        "selectedSkillNames": skills,
                        "selectedPluginIds": [],
                        "selectedConnectorIds": [],
                        "selectedAgentNames": [],
                        "selectedCapabilityCommands": [
                            *(f"skill://{name}" for name in skills),
                            *(f"command://{name}" for name in commands),
                        ],
                        "referencedChatSessions": [],
                        "parts": [
                            {
                                "id": f"{uid}:text:0",
                                "type": "text",
                                "text": turn["user_text"],
                                "parentToolUseId": None,
                            }
                        ],
                    },
                }
            )
        if turn["parts"]:
            sequence += 1
            uid = turn["uid"]
            rows.append(
                {
                    "message_id": f"assistant:{uid}",
                    "turn_id": uid,
                    "sequence": sequence,
                    "created_at": ts or 0,
                    "payload": {
                        "id": f"assistant:{uid}",
                        "role": "assistant",
                        "forkBoundaryProviderId": "msg_" + uuid.uuid4().hex,
                        "turnId": uid,
                        "text": "\n".join(turn["texts"]),
                        "timestamp": turn["user_timestamp"] or ms_to_iso(ts),
                        "tools": turn["tools"],
                        "turnStartedAt": turn["user_timestamp"] or ms_to_iso(ts),
                        "parts": turn["parts"],
                    },
                }
            )
    return rows


def session_files(roots: list[Path]) -> list[Path]:
    files = []
    for root in roots:
        for p in root.rglob("*.jsonl"):
            parts = {part.lower() for part in p.parts}
            if "subagents" in parts or "transcript" in parts:
                continue
            # Only <project>/<session-id>.jsonl at the top level of a project.
            try:
                if p.parent.parent != root and p.parent != root:
                    continue
            except Exception:
                pass
            if re.fullmatch(r"[0-9a-fA-F-]{36}", p.stem) is None:
                continue
            files.append(p)
    return files


def norm_path(p: str) -> str:
    s = str(p).replace("\\", "/").rstrip("/")
    return s.lower() if IS_WINDOWS else s


def ensure_workspace(conn: sqlite3.Connection, cwd: str) -> str:
    rows = conn.execute("SELECT workspace_id, root_paths_json FROM workspaces WHERE deleted_at IS NULL").fetchall()
    target = norm_path(cwd)
    for workspace_id, roots_json in rows:
        try:
            roots = json.loads(roots_json or "[]")
        except Exception:
            roots = []
        if any(norm_path(r) == target for r in roots if isinstance(r, str)):
            return workspace_id

    workspace_id = str(uuid.uuid4())
    now = int(time.time() * 1000)
    name = Path(cwd).name or cwd
    conn.execute(
        """
        INSERT INTO workspaces
          (workspace_id, name, workspace_source, root_paths_json, extra_json,
           created_at, updated_at, archived, deleted_at, product_mode)
        VALUES (?, ?, 'local', ?, ?, ?, ?, 0, NULL, 'coding')
        """,
        (
            workspace_id,
            name,
            json.dumps([cwd], ensure_ascii=False),
            json.dumps({"workspaceIcon": "folder", "workspaceColor": "primary"}),
            now,
            now,
        ),
    )
    return workspace_id


def execution_target(cwd: str) -> dict:
    # The app keys local execution targets by ws_<sha256("local\0" + cwd)>;
    # a workspace row id here would not match what the app itself writes.
    digest = hashlib.sha256(("local\0" + cwd).encode("utf-8")).hexdigest()
    return {
        "mode": "local",
        "host": {"id": "local", "kind": "local", "label": "Local"},
        "workspace": {"id": f"ws_{digest}", "path": cwd},
    }


def is_own_import(extra_json) -> bool:
    try:
        extra = json.loads(extra_json or "{}")
    except Exception:
        return False
    if not isinstance(extra, dict) or extra.get("importedFrom") != "qodercli":
        return False
    sync = extra.get("cliSync")
    return isinstance(sync, dict) and sync.get("script") == "qodercli-session-sync"


def target_key(value) -> tuple | None:
    """Identity of an execution target, ignoring app-added or legacy keys."""
    if isinstance(value, str):
        try:
            value = json.loads(value or "{}")
        except Exception:
            return None
    if not isinstance(value, dict):
        return None
    workspace = value.get("workspace")
    host = value.get("host")
    if not isinstance(workspace, dict) or not isinstance(host, dict):
        return None
    return (host.get("id"), workspace.get("id"), workspace.get("path"))


def repair_needed(conn: sqlite3.Connection, info: dict) -> bool:
    row = conn.execute(
        "SELECT workspace_id, execution_target_json, extra_json FROM chat_sessions WHERE session_id = ?",
        (info["session_id"],),
    ).fetchone()
    if not row or not is_own_import(row[2]):
        return False
    if row[0] is None:
        return True
    return target_key(row[1]) != target_key(execution_target(info["cwd"]))


def repair_session(conn: sqlite3.Connection, info: dict, workspace_id: str) -> bool:
    """Fix rows written by older versions of this script (idempotent)."""
    if not repair_needed(conn, info):
        return False
    row = conn.execute(
        "SELECT workspace_id FROM chat_sessions WHERE session_id = ?",
        (info["session_id"],),
    ).fetchone()
    target_json = json.dumps(execution_target(info["cwd"]), ensure_ascii=False)
    target_workspace = row[0] or workspace_id
    conn.execute(
        "UPDATE chat_sessions SET execution_target_json = ?, workspace_id = ? WHERE session_id = ?",
        (target_json, target_workspace, info["session_id"]),
    )
    return True


def register_session(conn: sqlite3.Connection, info: dict, workspace_id: str) -> None:
    extra = {
        "importedFrom": "qodercli",
        "source": "workspace",
        "modelSelectionRevision": 1,
        "modelSource": {"kind": "system"},
        "cliSync": {
            "script": "qodercli-session-sync",
            "transcript": str(info["path"]),
        },
    }
    target = execution_target(info["cwd"])
    conn.execute(
        """
        INSERT INTO chat_sessions (
          session_id, origin_session_id, session_kind, conversation_mode, product_mode,
          title, cwd, execution_kind, workspace_id, git_branch, model, permission_mode,
          additional_direcotries, extra_json, created_at, updated_at,
          execution_target_json, archived, unread
        ) VALUES (?, NULL, 'standard', 'normal', 'coding',
          ?, ?, 'local', ?, ?, ?, ?,
          '{}', ?, ?, ?,
          ?, 0, 0)
        """,
        (
            info["session_id"],
            info["title"],
            info["cwd"],
            workspace_id,
            info["git_branch"],
            info["model"],
            info["permission_mode"],
            json.dumps(extra, ensure_ascii=False),
            info["created_at"],
            info["updated_at"],
            json.dumps(target, ensure_ascii=False),
        ),
    )


def cli_sync_stamp(extra_json) -> int:
    try:
        extra = json.loads(extra_json or "{}")
    except Exception:
        return 0
    sync = extra.get("cliSync") if isinstance(extra, dict) else None
    try:
        return int((sync or {}).get("messagesSyncedAt") or 0)
    except Exception:
        return 0


def cli_sync_format(extra_json) -> int:
    try:
        extra = json.loads(extra_json or "{}")
    except Exception:
        return 0
    sync = extra.get("cliSync") if isinstance(extra, dict) else None
    try:
        return int((sync or {}).get("messagesFormat") or 0)
    except Exception:
        return 0


def messages_status(conn: sqlite3.Connection, info: dict) -> str:
    """missing | stale | ok | foreign — foreign means do not touch it."""
    row = conn.execute(
        "SELECT extra_json FROM chat_sessions WHERE session_id = ?",
        (info["session_id"],),
    ).fetchone()
    if not row or not is_own_import(row[0]):
        return "foreign"
    sources = conn.execute(
        "SELECT source, COUNT(*) FROM chat_session_messages WHERE session_id = ? GROUP BY source",
        (info["session_id"],),
    ).fetchall()
    total = sum(count for _, count in sources)
    if total == 0:
        return "missing"
    if any(source != "cli-import" for source, _ in sources):
        return "foreign"
    try:
        mtime_ms = int(Path(info["path"]).stat().st_mtime * 1000)
    except OSError:
        mtime_ms = 0
    if cli_sync_format(row[0]) != MESSAGE_FORMAT_VERSION:
        return "stale"
    stamp = cli_sync_stamp(row[0])
    return "stale" if mtime_ms > stamp else "ok"


def sync_messages(conn: sqlite3.Connection, info: dict) -> int:
    """Write the transcript as app message rows; replaces only our own rows."""
    status = messages_status(conn, info)
    if status in ("ok", "foreign"):
        return 0
    rows = build_messages(Path(info["path"]))
    if not rows:
        return 0
    try:
        mtime_ms = int(Path(info["path"]).stat().st_mtime * 1000)
    except OSError:
        mtime_ms = info["updated_at"]
    # The international app uses a narrower message table; only fill columns
    # that actually exist so both editions can import the same transcript.
    available = {row[1] for row in conn.execute("PRAGMA table_info(chat_session_messages)")}
    columns = [
        "session_id",
        "message_id",
        "turn_id",
        "sequence",
        "payload_json",
        "status",
        "source",
        "created_at",
        "updated_at",
    ]
    placeholders = ["?", "?", "?", "?", "?", "'completed'", "'cli-import'", "?", "?"]
    has_role = "role" in available
    if has_role:
        columns.append("role")
        placeholders.append("?")
    if "feedback_revision" in available:
        columns.append("feedback_revision")
        placeholders.append("0")

    def insert_values(row: dict) -> list:
        values = [
            info["session_id"],
            row["message_id"],
            row["turn_id"],
            row["sequence"],
            json.dumps(row["payload"], ensure_ascii=False),
            row["created_at"],
            row["created_at"],
        ]
        if has_role:
            values.append(row["payload"].get("role"))
        return values

    conn.execute(
        "DELETE FROM chat_session_messages WHERE session_id = ? AND source = 'cli-import'",
        (info["session_id"],),
    )
    conn.executemany(
        f"INSERT INTO chat_session_messages ({', '.join(columns)}) "
        f"VALUES ({', '.join(placeholders)})",
        [insert_values(row) for row in rows],
    )
    conn.execute(
        "UPDATE chat_sessions SET updated_at = MAX(updated_at, ?) WHERE session_id = ?",
        (info["updated_at"], info["session_id"]),
    )
    extra_row = conn.execute(
        "SELECT extra_json FROM chat_sessions WHERE session_id = ?", (info["session_id"],)
    ).fetchone()
    try:
        extra = json.loads(extra_row[0] or "{}") if extra_row else {}
    except Exception:
        extra = {}
    if not isinstance(extra, dict):
        extra = {}
    sync = extra.get("cliSync") if isinstance(extra.get("cliSync"), dict) else {}
    sync["messagesSyncedAt"] = mtime_ms
    sync["messagesFormat"] = MESSAGE_FORMAT_VERSION
    extra["cliSync"] = sync
    conn.execute(
        "UPDATE chat_sessions SET extra_json = ? WHERE session_id = ?",
        (json.dumps(extra, ensure_ascii=False), info["session_id"]),
    )
    return len(rows)


def backup_db(db: Path) -> Path:
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    if IS_WINDOWS:
        base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
    else:
        base = Path.home() / ".local" / "share"
    out_dir = base / "QoderCLISessionSync" / "backups"
    out_dir.mkdir(parents=True, exist_ok=True)
    # Both editions use main.sqlite; keep their backup sets separate.
    prefix = re.sub(r"[^A-Za-z0-9._-]+", "-", db.parent.name) + "-" + db.stem
    out = out_dir / f"{prefix}-{stamp}.sqlite"
    src = sqlite3.connect(str(db), timeout=15)
    dst = sqlite3.connect(str(out))
    try:
        src.backup(dst)
    finally:
        dst.close()
        src.close()
    # Per-turn syncing would otherwise leave an unbounded pile of backups.
    for old in sorted(out_dir.glob(f"{prefix}-*.sqlite"), reverse=True)[BACKUP_KEEP:]:
        try:
            old.unlink()
        except OSError:
            pass
    return out


def hook_payload_cwd() -> str | None:
    """Hook stdin carries {"cwd": ...}; skip it on interactive runs to avoid blocking."""
    try:
        if sys.stdin is None or sys.stdin.isatty():
            return None
        payload = json.loads(sys.stdin.read() or "{}")
    except Exception:
        return None
    cwd = payload.get("cwd") if isinstance(payload, dict) else None
    return cwd if isinstance(cwd, str) and cwd.strip() else None


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    parser = argparse.ArgumentParser(description="Sync Qoder CLI sessions into the Qoder app session list.")
    parser.add_argument("--db", help="Path to the Qoder app main.sqlite (auto-detected by default)")
    parser.add_argument("--projects-root", help="Override the CLI projects folder (for testing or custom setups)")
    parser.add_argument("--cwd", help="Only sync sessions from this working directory (default: current directory)")
    parser.add_argument("--cwd-only", action="store_true", help="Only sync sessions from the current working directory")
    parser.add_argument("--hook", action="store_true", help="Read the hook payload from stdin to resolve the session cwd")
    parser.add_argument("--all", action="store_true", help="Sync every CLI session found")
    parser.add_argument("--limit", type=int, default=0, help="Only consider the N most recently updated sessions")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be added without writing")
    parser.add_argument("--quiet", action="store_true", help="Only print errors")
    args = parser.parse_args()

    db = find_app_db(args.db or os.environ.get("QODERCLI_SYNC_DB"))
    conn = sqlite3.connect(str(db), timeout=15)
    conn.execute("PRAGMA busy_timeout = 8000")
    try:
        existing = {row[0] for row in conn.execute("SELECT session_id FROM chat_sessions").fetchall()}

        projects_override = args.projects_root or os.environ.get("QODERCLI_SYNC_PROJECTS_ROOT")
        roots = ([Path(projects_override).expanduser()] if projects_override
                 else cli_project_roots(db, existing))
        if not roots:
            log("No Qoder CLI session folder found (~/.qoder-cn/projects or ~/.qoder/projects).", args.quiet)
            return 0

        wanted_cwd = None
        if args.cwd or args.cwd_only or args.hook or not args.all:
            cwd = args.cwd
            if not cwd and args.hook:
                cwd = hook_payload_cwd()
            wanted_cwd = norm_path(cwd or os.getcwd())

        files = session_files(roots)
        infos = []
        for f in files:
            info = summarize(f)
            if not info:
                continue
            if wanted_cwd and norm_path(info["cwd"]) != wanted_cwd:
                continue
            infos.append(info)

        infos.sort(key=lambda i: i["updated_at"], reverse=True)
        if args.limit and args.limit > 0:
            infos = infos[: args.limit]

        if not infos:
            log("No Qoder CLI sessions found for this project.", args.quiet)
            return 0

        missing = [i for i in infos if i["session_id"] not in existing]
        stale = [i for i in infos if i["session_id"] in existing and repair_needed(conn, i)]
        need_messages = [
            i for i in infos
            if i["session_id"] in existing
            and messages_status(conn, i) in ("missing", "stale")
        ]

        if not missing and not stale and not need_messages:
            log(f"All {len(infos)} CLI session(s) are already in the app.", args.quiet)
            return 0

        if args.dry_run:
            if missing:
                log(f"Would add {len(missing)} session(s) to {db}:", args.quiet)
                for i in missing:
                    log(f"  + {i['session_id']}  {i['title'][:60]}  [{i['cwd']}]", args.quiet)
            if stale:
                log(f"Would repair {len(stale)} previously imported session(s).", args.quiet)
            if missing or need_messages:
                log(
                    f"Would write messages for {len({i['session_id'] for i in missing + need_messages})} session(s).",
                    args.quiet,
                )
            return 0

        backup = backup_db(db)
        log(f"Backup: {backup}", args.quiet)

        to_sync = {i["session_id"]: i for i in missing + need_messages}
        added = 0
        repaired = 0
        messages_written = 0
        with conn:
            for info in missing:
                workspace_id = ensure_workspace(conn, info["cwd"])
                register_session(conn, info, workspace_id)
                added += 1
                log(f"  + {info['session_id']}  {info['title'][:60]}", args.quiet)
            for info in stale:
                workspace_id = ensure_workspace(conn, info["cwd"])
                if repair_session(conn, info, workspace_id):
                    repaired += 1
                    log(f"  ~ {info['session_id']}  {info['title'][:60]}", args.quiet)
            for info in to_sync.values():
                count = sync_messages(conn, info)
                messages_written += count
                if count:
                    log(f"  = {info['session_id']}  {count} message(s)", args.quiet)

        log(
            f"Added {added} session(s), repaired {repaired}, imported {messages_written} message(s). "
            "Restart or refocus the Qoder app to see them.",
            args.quiet,
        )
        return 0
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
