#!/usr/bin/env python3
"""
Qwen-Image-3.0 image generation and editing via Alibaba Cloud Model Studio
(DashScope / Bailian).

Standard-library only -- no pip install required.

Models
------
qwen-image-3.0-pro   Pro tier, best quality (default).
qwen-image-3.0       Standard tier, balances quality and speed.
Both models support text-to-image (T2I) AND image-to-image / editing (I2I)
through the same endpoint and request shape.

Subcommands
-----------
status      Report whether credentials are already configured (never prints the
            full API key).
configure   One-time (or repeat, to rotate) credential setup. Writes
            ~/.qoder/qwen-image/config.json with permissions 600. MEANT TO BE RUN
            BY A HUMAN, DIRECTLY IN THEIR OWN TERMINAL -- see the security note
            below.
generate    Text-to-image: call the API with a prompt and download the
            resulting image(s) to disk.
edit        Image-to-image / editing: combine 1-3 input images (public URL or
            local file -- local files are Base64-encoded automatically) with an
            editing instruction and download the result(s).
Model Studio image URLs are only valid for 24 hours, so both commands download
immediately rather than just printing the URL.

Security note on `configure`
-----------------------------
Run with no arguments, `configure` prompts interactively: the API key is read
with getpass (input hidden, never echoed to the screen, never written to shell
history) and never needs to be passed as a command-line argument at all. This
is deliberate -- an AI coding agent invoking this script as a tool call would
otherwise see the raw key as part of the command it runs and potentially log
or echo it. `configure` refuses to run non-interactively unless every value is
supplied via flags, precisely so that "just run configure for me" from an
agent either fails safely or requires the agent to already possess the secret
some other way (which nothing in this skill provides). This script does not
attempt to detect who is invoking it -- that's not reliably possible -- so the
real control is the accompanying SKILL.md instructing the agent to never run
this subcommand or collect a key on the user's behalf.

Where these API details come from
----------------------------------
Endpoint shape, model names, request/response schema: Alibaba Cloud Model Studio
official docs, "Qwen-Image-3.0 text-to-image image editing API reference"
(https://help.aliyun.com/en/model-studio/qwen-image-generation-and-editing-api-reference,
English mirror of the China-region docs; the most complete and current page)
and https://www.alibabacloud.com/help/en/model-studio/qwen-image-generation-and-editing-api-reference
(international page, lags behind on model list and parameter details),
retrieved 2026-08-26.

Alibaba Cloud can change model IDs, parameters, or endpoint shapes without much
notice. If a call fails with a 404, "model not found", or a schema-validation
error from the API itself, that is a strong sign the documentation moved --
re-check the live docs (links above) rather than assuming this script is wrong.
The model name and API base URL are both stored in the config file and
overridable per-call (--model, --base-url) precisely so a doc change doesn't
require editing this script.
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
import urllib.error
import urllib.request

# Credentials live inside this skill folder so the skill is portable on its own.
# The upstream qwen-image location is still read as a fallback, so an existing
# install keeps working without migrating anything.
SKILL_DIR = pathlib.Path(__file__).resolve().parent.parent
CONFIG_DIR = SKILL_DIR
CONFIG_PATH = SKILL_DIR / "credentials.json"
LEGACY_CONFIG_PATH = pathlib.Path.home() / ".qoder" / "qwen-image" / "config.json"

DEFAULT_MODEL = "qwen-image-3.0"  # Standard, not Pro: cheaper and faster

# Shorthand accepted for --model / --configure --model, mapped to real model ids.
MODEL_ALIASES = {
    "pro": "qwen-image-3.0-pro",
    "standard": "qwen-image-3.0",
}

# region key -> Alibaba Cloud region id used in the MaaS gateway subdomain.
# Regions listed in the official reference page for this model family. If a new
# region appears later, add it here or just pass --base-url to bypass this table.
REGIONS = {
    "singapore": "ap-southeast-1",  # international / Model Studio (English console)
    "beijing": "cn-beijing",        # China mainland / Bailian (百炼)
    "frankfurt": "eu-central-1",    # Germany
    "tokyo": "ap-northeast-1",      # Japan
}

# I2I input constraints, validated client-side so failures are immediate and local.
MAX_INPUT_IMAGES = 3
MAX_INPUT_IMAGE_BYTES = 10 * 1024 * 1024  # documented limit: 10 MB per input image


def resolve_model(name: str) -> str:
    return MODEL_ALIASES.get((name or "").strip().lower(), name)


def endpoint_for(region_key: str, workspace_id: str) -> str:
    if region_key not in REGIONS:
        sys.exit(
            f"Unknown region '{region_key}'. Known regions: {', '.join(REGIONS)}. "
            "If Model Studio has added a new region for this model, pass --base-url "
            "directly instead of --region."
        )
    region = REGIONS[region_key]
    return (
        f"https://{workspace_id}.{region}.maas.aliyuncs.com"
        "/api/v1/services/aigc/multimodal-generation/generation"
    )


def load_config_from():
    """Return (config dict, path it came from); skill-local first, legacy second."""
    for path in (CONFIG_PATH, LEGACY_CONFIG_PATH):
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f), path
    return None, None


def load_config():
    return load_config_from()[0]


def save_config(cfg: dict):
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2)
    os.chmod(CONFIG_PATH, stat.S_IRUSR | stat.S_IWUSR)  # 600: owner read/write only


# --------------------------------------------------------------------------
# status
# --------------------------------------------------------------------------

def cmd_status(args):
    cfg, path = load_config_from()
    if not cfg:
        print(json.dumps({"configured": False, "config_path": str(CONFIG_PATH)}, indent=2))
        return
    key = cfg.get("api_key", "")
    source = ("make-image-lite credentials" if path == CONFIG_PATH
              else "legacy qwen-image config (fallback)")
    print(json.dumps({
        "configured": True,
        "config_path": str(path),
        "source": source,
        "region": cfg.get("region"),
        "workspace_id": cfg.get("workspace_id"),
        "model": cfg.get("model", DEFAULT_MODEL),
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
        "model": resolve_model(args.model) or DEFAULT_MODEL,
    }
    if args.base_url:
        cfg["base_url"] = args.base_url

    save_config(cfg)
    print(f"Saved Model Studio credentials to {CONFIG_PATH} (file permissions set to 600).")
    print("This is a one-time step -- future runs of 'generate' will reuse this config.")


# --------------------------------------------------------------------------
# generate / edit (shared request pipeline)
# --------------------------------------------------------------------------

def api_call(url: str, api_key: str, body: dict) -> dict:
    req = urllib.request.Request(
        url,
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=300) as resp:
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


def encode_local_image(path_str: str) -> str:
    """Read a local image file and return a data:{mime};base64,{data} URI."""
    path = pathlib.Path(path_str).expanduser()
    if not path.is_file():
        sys.exit(f"Input image not found: {path_str}")
    size = path.stat().st_size
    if size > MAX_INPUT_IMAGE_BYTES:
        sys.exit(
            f"Input image {path_str} is {size / 1024 / 1024:.1f} MB; the API limit is "
            "10 MB per input image. Downscale or recompress it first."
        )
    mime_type, _ = mimetypes.guess_type(str(path))
    if not mime_type or not mime_type.startswith("image/"):
        sys.exit(
            f"Cannot determine an image MIME type for {path_str}. Supported input "
            "formats: JPG, JPEG, PNG, BMP, TIFF, WEBP, GIF."
        )
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime_type};base64,{encoded}"


def resolve_image_input(value: str) -> str:
    """Accept a public URL, a data: URI, or a local file path for --image."""
    if value.startswith(("http://", "https://", "data:")):
        return value
    return encode_local_image(value)


def build_parameters(args, is_i2i: bool) -> dict:
    prompt_extend = not args.no_prompt_extend
    parameters = {
        "prompt_extend": prompt_extend,
        "watermark": args.watermark,
    }
    if args.size:
        parameters["size"] = args.size
    if args.n:
        parameters["n"] = args.n
    if args.negative_prompt:
        parameters["negative_prompt"] = args.negative_prompt
    if args.seed is not None:
        parameters["seed"] = args.seed

    if args.prompt_extend_mode:
        if is_i2i and args.prompt_extend_mode == "agent":
            sys.exit(
                "--prompt-extend-mode agent is only supported for text-to-image. "
                "The API rejects it for image editing with HTTP 400; use 'direct'."
            )
        parameters["prompt_extend_mode"] = args.prompt_extend_mode

    # enable_thinking requires prompt_extend=true. Only send it explicitly, and
    # keep the two flags mutually consistent instead of letting the API 400.
    if args.no_thinking:
        parameters["enable_thinking"] = False
    elif not prompt_extend:
        parameters["enable_thinking"] = False
        print(
            "Note: thinking mode requires prompt_extend=true, so enable_thinking was "
            "set to false along with --no-prompt-extend.",
            file=sys.stderr,
        )
    return parameters


def require_config() -> dict:
    cfg = load_config()
    if not cfg:
        sys.exit(
            "No Model Studio credentials configured yet. This is a one-time setup step "
            "that a human must run directly, in their own terminal -- not an AI agent, "
            "and not this command. Tell the user to run:\n"
            "  python3 scripts/qwen_image.py configure\n"
            "and follow the interactive prompts (see references/manual-setup.md for the "
            "console steps to obtain an API key and workspace ID). Do not attempt to run "
            "'configure' yourself or ask the user to paste their key into this chat."
        )
    return cfg


def run_image_call(args, content: list, default_stem: str):
    """Send one T2I or I2I request and download every returned image to disk."""
    cfg = require_config()

    api_key = cfg["api_key"]
    base_url = args.base_url or cfg.get("base_url") or endpoint_for(cfg["region"], cfg["workspace_id"])
    model = resolve_model(args.model or cfg.get("model", DEFAULT_MODEL))

    body = {
        "model": model,
        "input": {
            "messages": [
                {"role": "user", "content": content}
            ]
        },
        "parameters": build_parameters(args, is_i2i=any("image" in item for item in content)),
    }

    result = api_call(base_url, api_key, body)

    output = result.get("output")
    if not output:
        sys.exit(f"Unexpected response (no 'output' field):\n{json.dumps(result, indent=2)}")

    choices = output.get("choices", [])
    if not choices:
        sys.exit(f"No images in response:\n{json.dumps(result, indent=2)}")

    out_dir = pathlib.Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    stem = args.filename or default_stem

    saved = []
    for idx, choice in enumerate(choices):
        content = choice.get("message", {}).get("content", [])
        for item in content:
            image_url = item.get("image")
            if not image_url:
                continue
            suffix = f"-{idx + 1}" if len(choices) > 1 or len(content) > 1 else ""
            dest = out_dir / f"{stem}-{ts}{suffix}.png"
            try:
                urllib.request.urlretrieve(image_url, dest)
            except Exception as e:  # noqa: BLE001 -- surface any download failure clearly
                sys.exit(f"Generated image but failed to download it from {image_url}: {e}")
            saved.append(str(dest))

    if not saved:
        sys.exit(f"Response succeeded but contained no image URLs:\n{json.dumps(result, indent=2)}")

    print(json.dumps({
        "request_id": result.get("request_id"),
        "saved_files": saved,
        "usage": result.get("usage"),
    }, indent=2))


def cmd_generate(args):
    run_image_call(args, [{"text": args.prompt}], default_stem="qwen-image")


def cmd_edit(args):
    if len(args.image) > MAX_INPUT_IMAGES:
        sys.exit(f"The API accepts at most {MAX_INPUT_IMAGES} input images per edit request.")
    content = [{"image": resolve_image_input(img)} for img in args.image]
    content.append({"text": args.prompt})
    run_image_call(args, content, default_stem="qwen-edit")


# --------------------------------------------------------------------------
# CLI wiring
# --------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Generate and edit images with Qwen-Image-3.0 (Standard/Pro) "
                    "via Alibaba Cloud Model Studio."
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
    p_conf.add_argument("--model", default=None, help=f"Override the model id: qwen-image-3.0 (default), qwen-image-3.0-pro, or shorthand 'pro'/'standard'")
    p_conf.add_argument("--base-url", default=None, help="Advanced: override the full endpoint URL instead of deriving it from --region/--workspace-id")
    p_conf.set_defaults(func=cmd_configure)

    def add_generation_args(p, default_stem_note):
        p.add_argument("--prompt", required=True, help="Full description (T2I) or editing instruction (I2I) -- the more concrete and specific, the better the result")
        p.add_argument("--negative-prompt", default=None, help="Things to avoid in the image")
        p.add_argument("--size", default=None, help='"width*height", e.g. "1664*928" for 16:9. Pixel area between 512*512 and 2048*2048, aspect ratio 1:8 to 8:1. Omit to let the API choose.')
        p.add_argument("--n", type=int, default=None, help="Number of images to generate (documented range: 1-6)")
        p.add_argument("--seed", type=int, default=None, help="Fixed seed for reproducibility (0-2147483647)")
        p.add_argument("--watermark", action="store_true", help="Add an AI-generated-content watermark (off by default)")
        p.add_argument("--no-prompt-extend", action="store_true", help="Disable Model Studio's automatic prompt rewriting/expansion")
        p.add_argument("--prompt-extend-mode", choices=["direct", "agent"], default=None, help="Prompt rewriting method: direct (default) works everywhere; agent gives finer rewriting but is T2I-only")
        p.add_argument("--no-thinking", action="store_true", help="Disable thinking mode (on by default server-side; improves quality but is slower)")
        p.add_argument("--out", default="outputs", help="Directory to save downloaded images into (default: outputs/)")
        p.add_argument("--filename", default=None, help=f"Filename stem for saved images (default: {default_stem_note})")
        p.add_argument("--model", default=None, help="Override the model id for this call only (qwen-image-3.0 (default), qwen-image-3.0-pro, or 'pro'/'standard')")
        p.add_argument("--base-url", default=None, help="Advanced: override the full endpoint URL for this call only")

    p_gen = sub.add_parser("generate", help="Text-to-image: generate an image from a text prompt")
    add_generation_args(p_gen, "qwen-image")
    p_gen.set_defaults(func=cmd_generate)

    p_edit = sub.add_parser("edit", help="Image-to-image: edit/recompose 1-3 input images per a text instruction")
    p_edit.add_argument("--image", action="append", required=True, help="Input image: public http(s) URL, data: URI, or local file path (auto-Base64-encoded). Repeatable, 1-3 images; array order defines reference order. Example: --image ./photo.png --image ./style.jpg")
    add_generation_args(p_edit, "qwen-edit")
    p_edit.set_defaults(func=cmd_edit)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
