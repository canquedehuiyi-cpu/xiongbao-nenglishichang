#!/usr/bin/env python3
"""
Discover the TmAgent ZWCAD plugin API endpoint.

Reads the discovery file written by the plugin at:
    %APPDATA%/TmAgent/api_address.json

Usage:
    python discover.py           # Print discovery info as JSON
    python discover.py --url     # Print just the execute URL
    python discover.py --health  # Check if the API is reachable
"""
import json
import os
import sys
import urllib.request
import urllib.error

DISCOVERY_PATH = os.path.join(os.environ.get("APPDATA", ""), "TmAgent", "api_address.json")


def read_discovery():
    """Read and parse the discovery file. Returns dict or None."""
    if not os.path.exists(DISCOVERY_PATH):
        return None
    try:
        with open(DISCOVERY_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return None


def check_health(base_url):
    """Ping the health endpoint. Returns (ok, message)."""
    try:
        url = base_url.rstrip("/") + "/api/health"
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=3) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            has_doc = data.get("hasActiveDocument", False)
            if not has_doc:
                return True, "ok (no CAD document open)"
            return True, "ok"
    except urllib.error.URLError as e:
        return False, f"unreachable: {e.reason}"
    except Exception as e:
        return False, str(e)


def main():
    info = read_discovery()
    if info is None:
        print(json.dumps({
            "error": "Discovery file not found. Is TmAgent plugin loaded in ZWCAD?",
            "expected_path": DISCOVERY_PATH
        }, ensure_ascii=False, indent=2))
        sys.exit(1)

    if "--url" in sys.argv:
        print(info["endpoints"]["execute"])
        return

    if "--health" in sys.argv:
        base = info.get("baseUrl", info.get("base_url", ""))
        ok, msg = check_health(base)
        print(json.dumps({"healthy": ok, "message": msg}, ensure_ascii=False))
        sys.exit(0 if ok else 1)

    # Default: print full discovery info
    print(json.dumps(info, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
