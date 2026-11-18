#!/usr/bin/env python3
"""
Wan3.0 video generation via Alibaba Cloud Model Studio (DashScope / Bailian).

Standard-library only -- no pip install required.

Model
-----
wan3.0-video   All-in-One reference-based video generation. Supports:
               - Text-to-video (prompt only)
               - Image-to-video: first frame, or first + last frame
               - Reference-based: up to 10 reference images, 5 reference
                 video clips, 5 reference audio clips (referred to in the
                 prompt as "Image 1", "Video 1", "Audio 1", ...)
               - File input (pdf/pptx/docx/... the model reads the document)
               - Web link input (public web page parsed into content)
               Output: up to 30 seconds, 480P/720P/1080P, with audio by
               default. First/last-frame mode is mutually exclusive with
               reference/file/link inputs.
wan3.0-video-prime
               Accelerated variant: significantly faster generation with the
               same feature surface (same inputs, resolutions, durations,
               audio). Selected with the --prime flag on 'generate'.

Subcommands
-----------
status      Report whether credentials are already configured (never prints
            the full API key).
configure   One-time (or repeat, to rotate) credential setup. Writes
            ~/.qoder/wan-video/config.json with permissions 600. MEANT TO BE
            RUN BY A HUMAN, DIRECTLY IN THEIR OWN TERMINAL -- see the
            security note below.
generate    Create an async video task, poll until it finishes (typically
            1-5 minutes), and download the resulting video to disk.
task        Query (and, if finished, download the result of) a task that was
            created earlier, e.g. one left running with `generate --no-wait`.

Model Studio video URLs are only valid for 24 hours, so this script always
downloads the video immediately when a task succeeds rather than just
printing the URL.

Credential reuse
----------------
If ~/.qoder/wan-video/config.json does not exist, this script falls back to
~/.qoder/qwen-image/config.json (same Model Studio account/key/workspace
shape). This lets users who already set up the qwen-image skill reuse those
credentials without re-entering anything. A wan-video config, once created,
always wins.

Security note on `configure`
-----------------------------
Run with no arguments, `configure` prompts interactively: the API key is read
with getpass (input hidden, never echoed to the screen, never written to
shell history) and never needs to be passed as a command-line argument at
all. This is deliberate -- an AI coding agent invoking this script as a tool
call would otherwise see the raw key as part of the command it runs and
potentially log or echo it. `configure` refuses to run non-interactively
unless every value is supplied via flags, precisely so that "just run
configure for me" from an agent either fails safely or requires the agent to
already possess the secret some other way (which nothing in this skill
provides). This script does not attempt to detect who is invoking it --
that's not reliably possible -- so the real control is the accompanying
SKILL.md instructing the agent to never run this subcommand or collect a key
on the user's behalf.

Where these API details come from
----------------------------------
Endpoint shape, model name, media types, request/response schema: Alibaba
Cloud Model Studio official docs, "Wan3.0 Video Generation API Reference"
(https://www.alibabacloud.com/help/en/model-studio/wan3-video-generation-api-reference,
international page; sample code applies to the Singapore region), retrieved
2026-08-26.

Alibaba Cloud can change model IDs, parameters, or endpoint shapes without
much notice. If a call fails with a 404, "model not found", or a
schema-validation error from the API itself, that is a strong sign the
documentation moved -- re-check the live docs (link above) rather than
assuming this script is wrong. The model name and API base URL are both
stored in the config file and overridable per-call (--model, --base-url)
precisely so a doc change doesn't require editing this script.
"""

import argparse
import base64
import datetime
import getpass
import json
import mimetypes
import os
import pathlib
import stat
import sys
import time
import urllib.error
import urllib.request

# Credentials live inside this skill folder so the skill is portable on its own.
# Two fallbacks follow: this skill's upstream location, then the qwen-image
# config, since both use the same Model Studio account.
SKILL_DIR = pathlib.Path(__file__).resolve().parent.parent
CONFIG_DIR = SKILL_DIR
CONFIG_PATH = SKILL_DIR / "credentials.json"
LEGACY_CONFIG_PATH = pathlib.Path.home() / ".qoder" / "wan-video" / "config.json"
QWEN_IMAGE_CONFIG_PATH = pathlib.Path.home() / ".qoder" / "qwen-image" / "config.json"

DEFAULT_MODEL = "wan3.0-video"
# Accelerated variant: faster generation, same feature surface.
PRIME_MODEL = "wan3.0-video-prime"

# region key -> Alibaba Cloud region id used in the MaaS gateway subdomain.
# Regions listed on the Wan3.0 reference page. If a new region appears later,
# add it here or just pass --base-url to bypass this table.
REGIONS = {
    "singapore": "ap-southeast-1",  # international / Model Studio (English console)
    "beijing": "cn-beijing",        # China mainland / Bailian (百炼)
}

SYNTHESIS_PATH = "/api/v1/services/aigc/video-generation/video-synthesis"

# Documented media limits, validated client-side so failures are immediate and local.
MAX_REFERENCE_IMAGES = 10
MAX_REFERENCE_VIDEOS = 5
MAX_REFERENCE_AUDIOS = 5
MAX_IMAGE_BYTES = 20 * 1024 * 1024       # 20 MB per input image
IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
VIDEO_SUFFIXES = {".mp4", ".mov"}
AUDIO_SUFFIXES = {".wav", ".mp3"}
FILE_SUFFIXES = {
    ".docx", ".doc", ".xlsx", ".xls", ".pptx", ".ppt",
    ".pdf", ".txt", ".key", ".pages", ".numbers", ".md",
}


def endpoint_for(region_key: str, workspace_id: str) -> str:
    if region_key not in REGIONS:
        sys.exit(
            f"Unknown region '{region_key}'. Known regions for Wan3.0: "
            f"{', '.join(REGIONS)}. If Model Studio has added a new region for "
            "this model, pass --base-url directly instead of --region."
        )
    region = REGIONS[region_key]
    return f"https://{workspace_id}.{region}.maas.aliyuncs.com{SYNTHESIS_PATH}"


def tasks_url_for(synthesis_url: str, task_id: str) -> str:
    """Derive the task-query URL from the synthesis endpoint URL."""
    base = synthesis_url.split("/api/v1/")[0]
    return f"{base}/api/v1/tasks/{task_id}"


def load_config():
    """Return (config dict, path it came from, whether it's the qwen-image fallback)."""
    for path in (CONFIG_PATH, LEGACY_CONFIG_PATH):
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f), path, False
    if QWEN_IMAGE_CONFIG_PATH.exists():
        with open(QWEN_IMAGE_CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f), QWEN_IMAGE_CONFIG_PATH, True
    return None, None, False


def save_config(cfg: dict):
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2)
    os.chmod(CONFIG_PATH, stat.S_IRUSR | stat.S_IWUSR)  # 600: owner read/write only


def not_configured_exit():
    sys.exit(
        "No Model Studio credentials configured yet. This is a one-time setup step "
        "that a human must run directly, in their own terminal -- not an AI agent, "
        "and not this generate command. Tell the user to run:\n"
        "  python3 scripts/wan_video.py configure\n"
        "and follow the interactive prompts (see references/manual-setup.md for the "
        "console steps to obtain an API key and workspace ID). Do not attempt to run "
        "'configure' yourself or ask the user to paste their key into this chat."
    )


# --------------------------------------------------------------------------
# status
# --------------------------------------------------------------------------

def cmd_status(args):
    cfg, path, from_qwen = load_config()
    if not cfg:
        print(json.dumps({
            "configured": False,
            "config_path": str(CONFIG_PATH),
            "note": "No config here and no qwen-image config to fall back on either.",
        }, indent=2))
        return
    key = cfg.get("api_key", "")
    # The qwen-image fallback config stores its own image model id, which is
    # meaningless here -- report this skill's default instead.
    model = DEFAULT_MODEL if from_qwen else cfg.get("model", DEFAULT_MODEL)
    if from_qwen:
        source = "qwen-image config (fallback)"
    elif path == CONFIG_PATH:
        source = "make-video-lite credentials"
    else:
        source = "legacy wan-video config (fallback)"
    print(json.dumps({
        "configured": True,
        "config_path": str(path),
        "source": source,
        "region": cfg.get("region"),
        "workspace_id": cfg.get("workspace_id"),
        "model": model,
        "api_key_preview": ("..." + key[-4:]) if len(key) >= 4 else "(unreadable)",
    }, indent=2))


# --------------------------------------------------------------------------
# configure
# --------------------------------------------------------------------------

def cmd_configure(args):
    interactive = sys.stdin.isatty()

    api_key = args.api_key
    if api_key is None:
        if not interactive:
            sys.exit(
                "No --api-key given, and stdin isn't an interactive terminal so there's "
                "nothing to prompt on. This command is meant to be run directly by you, "
                "in your own terminal, with no arguments -- it will then prompt for the "
                "key with hidden input. Refusing to guess or accept a key from anywhere "
                "else."
            )
        api_key = getpass.getpass(
            "Model Studio API key (input hidden, starts with sk- or sk-ws-): "
        ).strip()
        if not api_key:
            sys.exit("No API key entered -- aborting without saving anything.")
    if not api_key.startswith("sk-"):
        print(
            "Warning: Model Studio API keys normally start with 'sk-' (workspace-scoped "
            "keys start with 'sk-ws-'). Saving it anyway -- double check you copied it "
            "correctly from the console.",
            file=sys.stderr,
        )

    workspace_id = args.workspace_id
    if workspace_id is None:
        if not interactive:
            sys.exit("No --workspace-id given and stdin isn't interactive.")
        workspace_id = input(
            "Workspace ID (Model Studio console -> Workspace Details page): "
        ).strip()
        if not workspace_id:
            sys.exit("No workspace ID entered -- aborting without saving anything.")

    region = args.region
    if region is None:
        if not interactive:
            region = "singapore"
        else:
            raw = input(
                f"Region [{'/'.join(REGIONS)}] (default: singapore): "
            ).strip().lower()
            region = raw or "singapore"

    if not args.base_url and region not in REGIONS:
        sys.exit(f"--region must be one of: {', '.join(REGIONS)} (or pass --base-url instead)")

    cfg = {
        "api_key": api_key,
        "workspace_id": workspace_id,
        "region": region,
        "model": DEFAULT_MODEL,
    }
    if args.base_url:
        cfg["base_url"] = args.base_url

    save_config(cfg)
    print(f"Saved Model Studio credentials to {CONFIG_PATH} (file permissions set to 600).")
    print("This is a one-time step -- future runs of 'generate' will reuse this config.")


# --------------------------------------------------------------------------
# HTTP helpers
# --------------------------------------------------------------------------

def api_post(url: str, api_key: str, body: dict) -> dict:
    req = urllib.request.Request(
        url,
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
            "X-DashScope-Async": "enable",  # required: HTTP supports async only
        },
        method="POST",
    )
    return _do_request(req, url)


def api_get(url: str, api_key: str) -> dict:
    req = urllib.request.Request(
        url,
        headers={"Authorization": f"Bearer {api_key}"},
        method="GET",
    )
    return _do_request(req, url)


def _do_request(req, url: str) -> dict:
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", errors="replace")
        hint = ""
        if e.code == 401:
            hint = " (check that the API key and region/workspace match -- keys are region-scoped)"
        elif e.code == 404:
            hint = " (the model name or endpoint path may have changed -- re-check the docs)"
        sys.exit(f"Model Studio API returned HTTP {e.code}{hint}:\n{detail}")
    except urllib.error.URLError as e:
        sys.exit(f"Could not reach Model Studio endpoint ({url}): {e.reason}")


def image_to_data_uri(path: pathlib.Path) -> str:
    if path.stat().st_size > MAX_IMAGE_BYTES:
        sys.exit(f"Input image {path} exceeds the documented 20 MB limit.")
    mime = mimetypes.guess_type(str(path))[0]
    if mime not in ("image/jpeg", "image/png", "image/bmp", "image/webp"):
        sys.exit(
            f"Input image {path} has unsupported type '{mime}'. Documented formats: "
            "JPEG, JPG, PNG (no transparency), BMP, WEBP."
        )
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime};base64,{encoded}"


def resolve_media_url(value: str, kind: str, allowed_suffixes: set, local_ok: bool) -> str:
    """Accept a public URL, or a local path where the API allows Base64 inline data."""
    if value.startswith(("http://", "https://", "oss://", "data:")):
        return value
    path = pathlib.Path(value)
    if path.is_file():
        if not local_ok:
            sys.exit(
                f"Local {kind} files can't be sent inline: the API only accepts public "
                f"URLs for {kind} inputs. Upload '{path}' somewhere public (or to Model "
                "Studio's file upload API for an oss:// temporary URL) and pass that URL."
            )
        if path.suffix.lower() not in allowed_suffixes:
            sys.exit(
                f"Local {kind} '{path}' has extension '{path.suffix.lower()}', expected "
                f"one of: {', '.join(sorted(allowed_suffixes))}."
            )
        return image_to_data_uri(path)
    sys.exit(f"{kind} input '{value}' is neither a URL nor an existing local file.")


# --------------------------------------------------------------------------
# generate
# --------------------------------------------------------------------------

def build_media(args) -> list:
    media = []
    frames = []
    if args.first_frame:
        frames.append(("first_frame", resolve_media_url(args.first_frame, "first-frame image", IMAGE_SUFFIXES, local_ok=True)))
    if args.last_frame:
        frames.append(("last_frame", resolve_media_url(args.last_frame, "last-frame image", IMAGE_SUFFIXES, local_ok=True)))

    ref_images = [resolve_media_url(v, "reference image", IMAGE_SUFFIXES, local_ok=True) for v in (args.ref_image or [])]
    ref_videos = [resolve_media_url(v, "reference video", VIDEO_SUFFIXES, local_ok=False) for v in (args.ref_video or [])]
    ref_audios = [resolve_media_url(v, "reference audio", AUDIO_SUFFIXES, local_ok=False) for v in (args.ref_audio or [])]
    refs = ref_images + ref_videos + ref_audios

    if frames and refs:
        sys.exit(
            "Invalid media mix: first_frame/last_frame is mutually exclusive with "
            "reference_image/reference_video/reference_audio (per the API docs). "
            "Pick frame mode OR reference mode."
        )
    if args.file and args.link:
        sys.exit("Invalid media mix: 'file' and 'link' cannot be used together.")
    if frames and (args.file or args.link):
        sys.exit(
            "Invalid media mix: first_frame/last_frame is mutually exclusive with "
            "file/link inputs."
        )

    if len(ref_images) > MAX_REFERENCE_IMAGES:
        sys.exit(f"Too many reference images ({len(ref_images)}); the documented maximum is {MAX_REFERENCE_IMAGES}.")
    if len(ref_videos) > MAX_REFERENCE_VIDEOS:
        sys.exit(f"Too many reference videos ({len(ref_videos)}); the documented maximum is {MAX_REFERENCE_VIDEOS}.")
    if len(ref_audios) > MAX_REFERENCE_AUDIOS:
        sys.exit(f"Too many reference audios ({len(ref_audios)}); the documented maximum is {MAX_REFERENCE_AUDIOS}.")

    # Frame mode first, then references, then file/link. Within each type the
    # order here defines "Image 1"/"Video 1"/... numbering in the prompt.
    for t, url in frames:
        media.append({"type": t, "url": url})
    for url in ref_images:
        media.append({"type": "reference_image", "url": url})
    for url in ref_videos:
        media.append({"type": "reference_video", "url": url})
    for url in ref_audios:
        media.append({"type": "reference_audio", "url": url})
    if args.file:
        if pathlib.Path(args.file).is_file() and not args.file.startswith(("http", "oss")):
            suffix = pathlib.Path(args.file).suffix.lower()
            if suffix not in FILE_SUFFIXES:
                sys.exit(
                    f"File '{args.file}' has extension '{suffix}', expected one of: "
                    f"{', '.join(sorted(FILE_SUFFIXES))}."
                )
            sys.exit(
                f"Local document '{args.file}' can't be sent inline: the API only "
                "accepts public URLs for file inputs. Upload it somewhere public (or "
                "use Model Studio's file upload API for an oss:// temporary URL) and "
                "pass that URL."
            )
        media.append({"type": "file", "url": args.file})
    if args.link:
        media.append({"type": "link", "url": args.link})
    return media


def download_video(video_url: str, out_dir_arg: str, filename_stem: str) -> str:
    out_dir = pathlib.Path(out_dir_arg)
    out_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    dest = out_dir / f"{filename_stem}-{ts}.mp4"
    try:
        urllib.request.urlretrieve(video_url, dest)
    except Exception as e:  # noqa: BLE001 -- surface any download failure clearly
        sys.exit(
            f"Video generated but failed to download from {video_url}: {e}\n"
            "The URL stays valid for 24 hours -- retry with the 'task' subcommand."
        )
    return str(dest)


def poll_task(base_url: str, api_key: str, task_id: str, poll_interval: int, max_wait: int) -> dict:
    deadline = time.time() + max_wait
    waited = 0
    while True:
        result = api_get(tasks_url_for(base_url, task_id), api_key)
        output = result.get("output", {})
        status = output.get("task_status")
        if status in ("SUCCEEDED", "FAILED", "CANCELED", "UNKNOWN"):
            return result
        print(f"[{waited}s] task {task_id}: {status or 'PENDING'} -- next check in {poll_interval}s", file=sys.stderr)
        if time.time() + poll_interval > deadline:
            sys.exit(
                f"Timed out after ~{max_wait}s waiting for task {task_id} (last status: "
                f"{status or 'PENDING'}). The task is probably still running server-side -- "
                f"check it later with:\n  python3 scripts/wan_video.py task {task_id}\n"
                "(task ids stay queryable for 24 hours; do NOT create a duplicate task.)"
            )
        time.sleep(poll_interval)
        waited += poll_interval


def cmd_generate(args):
    cfg, _, from_qwen = load_config()
    if not cfg:
        not_configured_exit()

    api_key = cfg["api_key"]
    base_url = args.base_url or cfg.get("base_url") or endpoint_for(cfg["region"], cfg["workspace_id"])
    # A qwen-image fallback config stores an image model id -- ignore it here.
    # Priority: explicit --model > --prime > configured model > default.
    model = (args.model
             or (PRIME_MODEL if args.prime else None)
             or (None if from_qwen else cfg.get("model"))
             or DEFAULT_MODEL)

    if not args.prompt and not (args.first_frame or args.ref_image or args.ref_video
                                or args.ref_audio or args.file or args.link):
        sys.exit("Give at least --prompt, or one of the media flags (frame/reference/file/link mode).")

    media = build_media(args)

    input_obj = {"prompt": args.prompt} if args.prompt else {}
    if media:
        input_obj["media"] = media

    parameters = {
        "prompt_extend": not args.no_prompt_extend,
        "watermark": args.watermark,
        "audio": not args.no_audio,
    }
    if args.resolution:
        parameters["resolution"] = args.resolution
    if args.ratio:
        parameters["ratio"] = args.ratio
    if args.duration is not None:
        parameters["duration"] = args.duration
    if args.seed is not None:
        parameters["seed"] = args.seed

    body = {"model": model, "input": input_obj, "parameters": parameters}

    result = api_post(base_url, api_key, body)
    output = result.get("output", {})
    task_id = output.get("task_id")
    if not task_id:
        sys.exit(f"No task_id in response:\n{json.dumps(result, indent=2)}")

    print(f"Task created: {task_id} ({output.get('task_status', 'PENDING')})", file=sys.stderr)

    if args.no_wait:
        print(json.dumps({
            "task_id": task_id,
            "request_id": result.get("request_id"),
            "note": "Not waiting. Poll later with: python3 scripts/wan_video.py task "
                    + task_id,
        }, indent=2))
        return

    final = poll_task(base_url, api_key, task_id, args.poll_interval, args.max_wait)
    finish_and_report(final, args.out, args.filename or "wan-video")


def cmd_task(args):
    cfg, _, _ = load_config()
    if not cfg:
        not_configured_exit()

    api_key = cfg["api_key"]
    base_url = args.base_url or cfg.get("base_url") or endpoint_for(cfg["region"], cfg["workspace_id"])

    result = api_get(tasks_url_for(base_url, args.task_id), api_key)
    status = result.get("output", {}).get("task_status")
    if status in ("PENDING", "RUNNING"):
        print(json.dumps({
            "task_id": args.task_id,
            "task_status": status,
            "note": "Still running -- re-run this command later.",
        }, indent=2))
        return
    finish_and_report(result, args.out, args.filename or "wan-video")


def finish_and_report(result: dict, out_dir: str, filename_stem: str):
    output = result.get("output", {})
    status = output.get("task_status")
    if status == "FAILED":
        sys.exit(
            "Task failed. Relay these fields verbatim to the user:\n"
            + json.dumps({
                "task_id": output.get("task_id"),
                "code": output.get("code"),
                "message": output.get("message"),
                "request_id": result.get("request_id"),
            }, indent=2)
        )
    if status != "SUCCEEDED":
        sys.exit(f"Task ended in unexpected status '{status}':\n{json.dumps(result, indent=2)}")

    video_url = output.get("video_url")
    if not video_url:
        sys.exit(f"Task succeeded but no video_url in response:\n{json.dumps(result, indent=2)}")

    saved = download_video(video_url, out_dir, filename_stem)
    print(json.dumps({
        "task_id": output.get("task_id"),
        "request_id": result.get("request_id"),
        "saved_file": saved,
        "usage": result.get("usage"),
    }, indent=2))


# --------------------------------------------------------------------------
# CLI wiring
# --------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Generate videos with Wan3.0 (wan3.0-video) via Alibaba Cloud Model Studio."
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_status = sub.add_parser("status", help="Check whether credentials are configured")
    p_status.set_defaults(func=cmd_status)

    p_conf = sub.add_parser(
        "configure",
        help="Save Model Studio credentials (one-time setup, or rotate a key). "
             "Run with no flags for a safe interactive prompt -- recommended.",
    )
    p_conf.add_argument("--api-key", default=None, help="Model Studio API key (starts with sk- or sk-ws-). Omit to be prompted with hidden input instead (recommended).")
    p_conf.add_argument("--workspace-id", default=None, help="Found on the Workspace Details page of the Model Studio console. Omit to be prompted.")
    p_conf.add_argument("--region", default=None, choices=list(REGIONS), help="singapore (international, default) or beijing (China mainland). Omit to be prompted.")
    p_conf.add_argument("--base-url", default=None, help="Advanced: override the full synthesis endpoint URL instead of deriving it from --region/--workspace-id")
    p_conf.set_defaults(func=cmd_configure)

    p_gen = sub.add_parser("generate", help="Generate a video from a prompt and/or media inputs")
    p_gen.add_argument("--prompt", default=None, help="Video description. In reference mode, refer to media as 'Image 1', 'Video 1', 'Audio 1' etc. matching flag order. Up to 20,000 chars.")
    # Frame mode (mutually exclusive with reference/file/link)
    p_gen.add_argument("--first-frame", default=None, help="First-frame image: public URL or local image file (JPEG/PNG/BMP/WEBP, auto Base64-encoded)")
    p_gen.add_argument("--last-frame", default=None, help="Last-frame image: public URL or local image file")
    # Reference mode
    p_gen.add_argument("--ref-image", action="append", default=None, help="Reference image (repeatable, max 10). Public URL or local image file. Order defines Image 1, Image 2, ...")
    p_gen.add_argument("--ref-video", action="append", default=None, help="Reference video (repeatable, max 5; 1-15s each, <=15s total). Public URL only (mp4/mov). Order defines Video 1, Video 2, ...")
    p_gen.add_argument("--ref-audio", action="append", default=None, help="Reference audio (repeatable, max 5; 1-15s each, <=15s total). Public URL only (wav/mp3). Order defines Audio 1, Audio 2, ...")
    # File / link mode
    p_gen.add_argument("--file", default=None, help="Document for the model to read (pdf/pptx/docx/xlsx/txt/md/..., <=100MB, <=50 pages). Public URL only; mutually exclusive with --link.")
    p_gen.add_argument("--link", default=None, help="Public web page URL for the model to parse. Mutually exclusive with --file.")
    # Parameters
    p_gen.add_argument("--resolution", default="480P", choices=["480P", "720P", "1080P"], help="Resolution tier. Default 480P (cheap drafts); use 1080P for finals. Higher costs more.")
    p_gen.add_argument("--ratio", default="9:16", choices=["adaptive", "16:9", "9:16", "1:1", "4:3", "3:4"], help="Aspect ratio. Default 9:16 (vertical/mobile); 'adaptive' follows input media.")
    p_gen.add_argument("--duration", type=int, default=None, help="Seconds, 2-30 (default 5); -1 = smart duration. With reference-video input, input+output must total <=30s.")
    p_gen.add_argument("--no-audio", action="store_true", help="Generate a silent video (audio is on by default and free)")
    p_gen.add_argument("--seed", type=int, default=None, help="Fixed seed for reproducibility (0-2147483647)")
    p_gen.add_argument("--watermark", action="store_true", help="Add an AI-generated-content watermark (off by default)")
    p_gen.add_argument("--no-prompt-extend", action="store_true", help="Disable Model Studio's automatic prompt rewriting/expansion")
    # Behavior
    p_gen.add_argument("--poll-interval", type=int, default=15, help="Seconds between status polls (default 15, per docs recommendation)")
    p_gen.add_argument("--max-wait", type=int, default=1800, help="Give up polling after this many seconds (default 1800; the task keeps running server-side)")
    p_gen.add_argument("--no-wait", action="store_true", help="Create the task and exit immediately; retrieve it later with the 'task' subcommand")
    p_gen.add_argument("--out", default="outputs", help="Directory to save the downloaded video into (default: outputs/)")
    p_gen.add_argument("--filename", default=None, help="Filename stem for the saved video (default: wan-video)")
    p_gen.add_argument("--prime", action="store_true", help="Use wan3.0-video-prime, the accelerated model: significantly faster generation, same feature surface. Ignored if --model is given.")
    p_gen.add_argument("--model", default=None, help="Override the model id for this call only")
    p_gen.add_argument("--base-url", default=None, help="Advanced: override the full synthesis endpoint URL for this call only")
    p_gen.set_defaults(func=cmd_generate)

    p_task = sub.add_parser("task", help="Query an existing task by id (and download its video if done)")
    p_task.add_argument("task_id", help="The task_id printed by a previous generate call")
    p_task.add_argument("--out", default="outputs", help="Directory to save the downloaded video into (default: outputs/)")
    p_task.add_argument("--filename", default=None, help="Filename stem for the saved video (default: wan-video)")
    p_task.add_argument("--base-url", default=None, help="Advanced: override the full synthesis endpoint URL for this call only")
    p_task.set_defaults(func=cmd_task)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
