#!/usr/bin/env python3
"""fill.py — substitute {{TOKEN}} placeholders in an existing .docx.

    python3 fill.py template.docx out.docx --set CO_QUAN="UBND Quận 1" --set SO="12/NQ"
    python3 fill.py template.docx --list

Stdlib only. Never edits the input file in place. Reports tokens that stayed
unfilled (usually because Word split them across runs) without failing the run.
"""
import argparse
import re
import sys
import zipfile

TOKEN_RE = re.compile(r"\{\{([A-Z0-9_]+)\}\}")
WTEXT = re.compile(r"(<w:t(?:\s[^>]*)?>)(.*?)(</w:t>)", re.S)


def read_parts(path):
    with zipfile.ZipFile(path) as z:
        return z.namelist(), {n: z.read(n) for n in z.namelist()}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("template")
    ap.add_argument("output", nargs="?")
    ap.add_argument("--set", action="append", default=[], metavar="KEY=VALUE")
    ap.add_argument("--list", action="store_true", help="print tokens and exit")
    a = ap.parse_args()

    try:
        names, parts = read_parts(a.template)
    except (OSError, zipfile.BadZipFile):
        sys.exit("FAIL: not a readable .docx: %s" % a.template)

    xml = parts["word/document.xml"].decode("utf-8")
    found = []
    for m in TOKEN_RE.finditer(xml):
        if m.group(1) not in found:
            found.append(m.group(1))

    if a.list:
        print("\n".join(found) if found else "(no {{TOKEN}} placeholders)")
        return

    if not a.output:
        sys.exit("FAIL: need an output path (or --list)")

    values = {}
    for kv in a.set:
        if "=" not in kv:
            sys.exit("FAIL: --set expects KEY=VALUE, got %s" % kv)
        k, v = kv.split("=", 1)
        values[k.strip()] = v

    def sub(mo):
        head, text, tail = mo.group(1), mo.group(2), mo.group(3)
        def one(mo2):
            key = mo2.group(1)
            return values.get(key, mo2.group(0))
        return head + TOKEN_RE.sub(one, text) + tail

    new = WTEXT.sub(sub, xml)
    # A token is unfilled when its {{TOKEN}} form survives substitution — usually
    # because Word split it across runs, so WTEXT never saw it whole.
    missing = [t for t in found if ("{{%s}}" % t) in new]
    unused = sorted(set(values) - set(found))

    parts["word/document.xml"] = new.encode("utf-8")
    with zipfile.ZipFile(a.output, "w", zipfile.ZIP_DEFLATED) as z:
        for n in names:
            z.writestr(n, parts[n])

    print("ok: %s (filled %d/%d tokens)" % (a.output, len(found) - len(missing), len(found)))
    if missing:
        print("unfilled: %s" % ", ".join(missing))
    if unused:
        print("ignored (not in template): %s" % ", ".join(unused))


if __name__ == "__main__":
    main()
