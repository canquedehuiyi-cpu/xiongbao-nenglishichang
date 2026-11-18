#!/usr/bin/env python3
"""Offline prototype delivery checks. Browser evidence must be supplied honestly."""
import argparse
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path, PurePosixPath
import re
import shutil
import sys
from urllib.parse import unquote, urlsplit
import zipfile


TEMPLATES = Path(__file__).resolve().parent.parent / "templates"
DOCS = {"requirements.md", "DESIGN.md", "README.md"}
CODE_EXT = {".html", ".css", ".js", ".mjs"}
IMAGE_EXT = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".svg"}
ASSET_EXT = IMAGE_EXT | {".woff", ".woff2", ".ttf", ".otf", ".ico", ".json", ".txt", ".md"}
TEXT_EXT = CODE_EXT | {".md", ".json", ".svg", ".txt"}
IDENTIFIER = re.compile(r"[a-zA-Z0-9][a-zA-Z0-9_-]{0,99}\Z")
SENSITIVE = re.compile(
    r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----|"
    r"Bearer\s+[A-Za-z0-9_.-]{16,}|"
    r"[?&](?:x-oss-signature|x-amz-signature|signature|access_token|refresh_token)=|"
    r'''["']?(?:api[_-]?key|access[_-]?token|refresh[_-]?token|password)["']?\s*[:=]\s*["'][^"'\n]{8,}["']''',
    re.I,
)


def need(condition, message):
    if not condition:
        raise ValueError(message)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def safe_file(root, relative):
    root = Path(root).resolve()
    need(isinstance(relative, str) and relative, "Expected a relative file path")
    p = PurePosixPath(relative)
    need(not p.is_absolute() and "\\" not in relative and ":" not in relative
         and not any(x in {"", ".", ".."} or x.startswith(".") for x in relative.split("/")),
         "Unsafe path: " + relative)
    target = root
    for part in p.parts:
        target /= part
        need(not target.is_symlink(), "Symlink not allowed: " + relative)
    need(target.resolve().is_relative_to(root), "Path escapes project: " + relative)
    need(target.is_file() and target.stat().st_size > 0, "Missing or empty file: " + relative)
    return target


def load_json(root, name):
    value = json.loads(safe_file(root, name).read_text(encoding="utf-8"))
    need(isinstance(value, dict) and value.get("schema_version") == 1,
         "Expected schema_version=1 object: " + name)
    return value


def viewport(value):
    return (isinstance(value, dict) and set(value) == {"width", "height"}
            and all(type(x) is int and 100 <= x <= 10000 for x in value.values()))


def image_file(root, relative):
    path = safe_file(root, relative)
    need(path.suffix.lower() in IMAGE_EXT, "Expected an image: " + relative)
    data = path.read_bytes()
    valid = ((path.suffix.lower() == ".png" and data.startswith(b"\x89PNG\r\n\x1a\n"))
             or (path.suffix.lower() in {".jpg", ".jpeg"} and data.startswith(b"\xff\xd8\xff"))
             or (path.suffix.lower() == ".webp" and data[:4] == b"RIFF" and data[8:12] == b"WEBP")
             or (path.suffix.lower() == ".gif" and data[:6] in {b"GIF87a", b"GIF89a"})
             or (path.suffix.lower() == ".svg" and b"<svg" in data[:2048]))
    need(valid, "Image header does not match extension: " + relative)
    return path


def local_target(root, owner, url, *, resource):
    root = Path(root).resolve()
    parts = urlsplit(url.strip())
    scheme = parts.scheme.lower()
    if scheme or parts.netloc:
        if scheme == "data" and resource and url.lower().startswith("data:image/"):
            return None
        need(not resource and scheme in {"https", "http", "mailto", "tel"},
             "External or unsafe runtime resource in " + owner + ": " + url[:160])
        return None
    if not parts.path:
        return None
    decoded = unquote(parts.path)
    need(not decoded.startswith("/") and "\\" not in decoded,
         "Use portable relative paths in " + owner)
    # Resolve ordinary ../ links inside the project, then apply file protections.
    target = (root / owner).parent / decoded
    need(not any(p.is_symlink() for p in [target, *target.parents] if p != root.parent),
         "Symlink resource in " + owner)
    resolved = target.resolve()
    need(resolved.is_relative_to(root), "Resource escapes project: " + owner)
    rel = resolved.relative_to(root).as_posix()
    safe_file(root, rel)
    return rel


class HTMLLinks(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []

    def handle_starttag(self, tag, attributes):
        attrs = dict(attributes)
        for field in ("src", "poster", "href", "action"):
            if attrs.get(field):
                self.links.append((attrs[field], not (tag == "a" and field == "href")))
        # Ordinary srcset URLs; embedded data-image srcsets need browser review.
        if attrs.get("srcset"):
            need("data:" not in attrs["srcset"], "Use a local file for srcset images")
            for candidate in attrs["srcset"].split(","):
                if candidate.strip():
                    self.links.append((candidate.strip().split()[0], True))


def source_files(root):
    manifest = load_json(root, "prototype.json")
    need(isinstance(manifest.get("title"), str) and manifest["title"].strip(), "Missing prototype title")
    files = set(DOCS) | {"prototype.json"}
    entry = manifest.get("entry")
    need(isinstance(entry, str) and entry.endswith(".html"), "Entry must be an HTML file")
    files.add(entry)
    declared = manifest.get("files")
    need(isinstance(declared, list) and all(isinstance(x, str) for x in declared), "files must be a path list")
    need(len(declared) == len(set(declared)), "Duplicate delivery file")
    for relative in declared:
        path = PurePosixPath(relative)
        allowed = ((len(path.parts) == 1 and path.suffix in CODE_EXT)
                   or (len(path.parts) > 1 and path.parts[0] in {"pages", "css", "js"} and path.suffix in CODE_EXT)
                   or (len(path.parts) > 1 and path.parts[0] == "assets" and path.suffix.lower() in ASSET_EXT))
        need(allowed, "File is outside the delivery allowlist: " + relative)
        files.add(relative)
    pages = manifest.get("pages")
    need(isinstance(pages, list) and pages, "At least one approved page is required")
    page_ids = set()
    for page in pages:
        need(isinstance(page, dict), "Invalid page")
        pid = page.get("id", "")
        need(isinstance(pid, str) and IDENTIFIER.fullmatch(pid) and pid not in page_ids, "Invalid or duplicate page ID")
        page_ids.add(pid)
        need(page.get("terminal") in {"mobile", "desktop"} and viewport(page.get("viewport")), "Invalid terminal/viewport: " + pid)
        approval = page.get("approval", {})
        need(approval.get("status") == "confirmed" and isinstance(approval.get("note"), str)
             and approval["note"].strip(), "Page has no user adoption record: " + pid)
        reference = page.get("reference", {})
        rel = reference.get("path", "")
        need(isinstance(rel, str) and rel.startswith("reference/"), "Reference must be in reference/: " + pid)
        reference_path = image_file(root, rel)
        need(reference.get("sha256") == digest(reference_path), "Reference hash changed: " + pid)
        need(reference.get("source") in {"shenhuo", "user"}, "Invalid reference source: " + pid)
        if reference["source"] == "shenhuo":
            need(isinstance(reference.get("variant_id"), str) and reference["variant_id"].strip(), "Missing real variant_id: " + pid)
        else:
            need(reference.get("variant_id") in {None, ""}, "User reference must not invent a variant_id: " + pid)
        files.add(rel)
        route = page.get("route")
        need(isinstance(route, str) and route, "Missing page route: " + pid)
        target = local_target(root, "prototype.json", route, resource=True)
        need(target and target.endswith(".html") and target in files, "Page route is not a declared HTML file: " + pid)
    transitions = manifest.get("transitions")
    need(isinstance(transitions, list), "transitions must be a list")
    transition_ids = set()
    for transition in transitions:
        need(isinstance(transition, dict), "Invalid transition")
        tid = transition.get("id", "")
        need(isinstance(tid, str) and IDENTIFIER.fullmatch(tid) and tid not in transition_ids, "Invalid or duplicate transition ID")
        transition_ids.add(tid)
        need(transition.get("from") in page_ids and transition.get("to") in page_ids, "Unknown transition endpoint: " + tid)
        need(all(isinstance(transition.get(k), str) and transition[k].strip() for k in ("trigger", "result")), "Missing trigger/result: " + tid)
    reachable = {pages[0]["id"]}
    for _ in pages:
        reachable.update(t["to"] for t in transitions if t["from"] in reachable)
    need(reachable == page_ids, "Pages are unreachable from the first page in the transition table")
    for relative in sorted(files):
        path = safe_file(root, relative)
        if path.suffix.lower() not in TEXT_EXT:
            continue
        content = path.read_text(encoding="utf-8")
        need(not SENSITIVE.search(content), "Potential credential or signed URL in " + relative)
        links = []
        if path.suffix == ".html":
            parser = HTMLLinks()
            parser.feed(content)
            links = parser.links
        elif path.suffix == ".css":
            links = [(u.strip().strip("\"'"), True) for u in re.findall(r"url\(([^)]+)\)", content)]
            links += [(u, True) for u in re.findall(r'''@import\s+["']([^"']+)["']''', content)]
        for url, resource in links:
            target = local_target(root, relative, url, resource=resource)
            need(target is None or target in files, "Referenced file missing from delivery list: " + str(target))
    return manifest, files


def fingerprint(root, files):
    return {f: digest(safe_file(root, f)) for f in sorted(files - {"README.md"})}


def inspect_project(root, *, require_preview=False):
    root = Path(root).expanduser().resolve()
    manifest, files = source_files(root)
    hashes = fingerprint(root, files)
    verification = load_json(root, "verification.json")
    status = verification.get("status")
    need(status in {"not_run", "partial", "passed"}, "Invalid preview status")
    need(isinstance(verification.get("limitations"), list), "Preview limitations must be a list")
    pages_by_id = {p["id"]: p for p in manifest["pages"]}
    transitions = {t["id"] for t in manifest["transitions"]}
    checked_pages, checked_flows = set(), set()
    for check in verification.get("pages", []):
        pid = check.get("page_id")
        need(pid in pages_by_id and pid not in checked_pages, "Unknown/duplicate preview page")
        checked_pages.add(pid)
        need(check.get("viewport") == pages_by_id[pid]["viewport"], "Preview viewport mismatch: " + pid)
        need(check.get("result") in {"passed", "failed"} and check.get("notes"), "Missing observed page result: " + pid)
        shot = check.get("screenshot", "")
        need(shot.startswith("preview/"), "Preview screenshot must be in preview/")
        image_file(root, shot)
        files.add(shot)
    for check in verification.get("flows", []):
        tid = check.get("transition_id")
        need(tid in transitions and tid not in checked_flows, "Unknown/duplicate preview transition")
        checked_flows.add(tid)
        need(check.get("result") in {"passed", "failed"} and check.get("notes"), "Missing observed flow result: " + tid)
    if status == "passed":
        need(bool(verification.get("checked_at")), "Missing preview time")
        need(checked_pages == set(pages_by_id) and checked_flows == transitions, "Preview does not cover every page and transition")
        need(all(c["result"] == "passed" for c in verification["pages"] + verification["flows"]), "Preview contains a failed check")
        need(verification.get("source_hashes") == hashes, "Preview evidence is stale; recheck changed source files")
    if require_preview:
        need(status == "passed", "Browser preview not verified; do not report it as passed")
    receipt_path = safe_file(root, "verification.json")
    need(not SENSITIVE.search(receipt_path.read_text()), "Potential credential in verification.json")
    files.add("verification.json")
    return {"ok": True, "root": str(root), "title": manifest["title"], "preview_status": status,
            "source_hashes": hashes, "files": sorted(files),
            "warnings": [] if status == "passed" else ["Browser preview has not fully passed; disclose this in README and delivery."]}


def initialize(root):
    root = Path(root).expanduser().absolute()
    need(not root.exists(), "Use a new prototype directory; existing files are never overwritten")
    root.mkdir(parents=True)
    for source in sorted(TEMPLATES.iterdir()):
        if source.is_file():
            shutil.copyfile(source, root / source.name)
    for name in ("assets", "css", "js", "reference", "preview"):
        (root / name).mkdir()
    return {"ok": True, "root": str(root), "status": "templates_only", "html_created": False}


def pack(root, output, *, allow_unverified_preview=False):
    report = inspect_project(root, require_preview=not allow_unverified_preview)
    root = Path(report["root"])
    output = Path(output).expanduser().absolute()
    need(not output.is_symlink() and not output.resolve().is_relative_to(root), "Write ZIP outside the prototype directory")
    need(output.suffix.lower() == ".zip", "Output must end with .zip")
    output.parent.mkdir(parents=True, exist_ok=True)
    # Buffer before writing: a conflicting existing release is never truncated.
    import io
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for relative in report["files"]:
            info = zipfile.ZipInfo("prototype/" + relative, (2000, 1, 1, 0, 0, 0))
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, safe_file(root, relative).read_bytes())
    payload = buffer.getvalue()
    if output.exists():
        need(output.read_bytes() == payload, "Different ZIP already exists; choose a new versioned filename")
    else:
        with output.open("xb") as handle:
            handle.write(payload)
    return {"ok": True, "zip": str(output), "sha256": hashlib.sha256(payload).hexdigest(),
            "file_count": len(report["files"]), "preview_status": report["preview_status"], "warnings": report["warnings"]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("init", "check", "fingerprint", "pack"))
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--require-preview", action="store_true")
    parser.add_argument("--allow-unverified-preview", action="store_true")
    args = parser.parse_args()
    try:
        if args.command == "init":
            report = initialize(args.root)
        elif args.command == "fingerprint":
            root = args.root.expanduser().resolve()
            _, files = source_files(root)
            report = {"ok": True, "source_hashes": fingerprint(root, files)}
        elif args.command == "pack":
            need(args.output is not None, "pack requires --output")
            report = pack(args.root, args.output, allow_unverified_preview=args.allow_unverified_preview)
        else:
            report = inspect_project(args.root, require_preview=args.require_preview)
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0
    except (ValueError, OSError, TypeError, KeyError, AttributeError) as error:
        print(json.dumps({"ok": False, "error": str(error)}, ensure_ascii=False), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
