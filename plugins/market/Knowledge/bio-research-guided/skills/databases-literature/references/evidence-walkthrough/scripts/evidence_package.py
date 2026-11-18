"""Pack and verify an evidence package: a zip of artifacts plus a manifest
of their SHA-256 hashes.

  python evidence_package.py make <evidence_dir> <out.zip>
  python evidence_package.py verify <package.zip>

A passing verify means every listed file matches its recorded hash and the
package contents match the manifest exactly. It does NOT establish who
produced the package; that would need a signature, which this format does
not carry. Say "verified intact", not "verified authentic".
"""

import argparse
import hashlib
import json
import sys
import zipfile
from pathlib import Path


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def make(evidence_dir: Path, out_zip: Path) -> int:
    files = sorted(p for p in evidence_dir.rglob("*") if p.is_file())
    if not files:
        print(f"error: no files under {evidence_dir}", file=sys.stderr)
        return 1
    manifest = {
        "files": {
            str(p.relative_to(evidence_dir)): sha256(p.read_bytes()) for p in files
        }
    }
    manifest_bytes = json.dumps(manifest, indent=2, sort_keys=True).encode()
    with zipfile.ZipFile(out_zip, "w", zipfile.ZIP_DEFLATED) as zf:
        for p in files:
            zf.write(p, str(p.relative_to(evidence_dir)))
        zf.writestr("manifest.json", manifest_bytes)
    print(f"wrote {out_zip} ({len(files)} files)")
    print(f"manifest sha256: {sha256(manifest_bytes)}")
    return 0


def verify(pkg: Path) -> int:
    with zipfile.ZipFile(pkg) as zf:
        names = set(zf.namelist())
        if "manifest.json" not in names:
            print("error: manifest.json missing from package", file=sys.stderr)
            return 1
        manifest_bytes = zf.read("manifest.json")
        listed = json.loads(manifest_bytes).get("files", {})
        problems = []
        for name, expected in sorted(listed.items()):
            if name not in names:
                problems.append(f"{name}: listed in manifest but missing from package")
                continue
            actual = sha256(zf.read(name))
            if actual != expected:
                problems.append(f"{name}: hash mismatch (expected {expected[:12]}...)")
        for name in sorted(names - set(listed) - {"manifest.json"}):
            problems.append(f"{name}: present in package but not listed in manifest")
    print(f"manifest sha256: {sha256(manifest_bytes)}")
    if problems:
        for p in problems:
            print(f"FAIL {p}", file=sys.stderr)
        return 1
    print(f"verified intact: {len(listed)} files match their recorded hashes")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)
    m = sub.add_parser("make", help="zip an evidence directory with a hash manifest")
    m.add_argument("evidence_dir", type=Path)
    m.add_argument("out_zip", type=Path)
    v = sub.add_parser("verify", help="verify a package against its manifest")
    v.add_argument("package", type=Path)
    args = ap.parse_args()
    if args.cmd == "make":
        return make(args.evidence_dir, args.out_zip)
    return verify(args.package)


if __name__ == "__main__":
    sys.exit(main())
