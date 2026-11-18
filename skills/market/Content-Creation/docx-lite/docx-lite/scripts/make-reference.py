#!/usr/bin/env python3
"""Regenerate assets/reference-vn.docx: pandoc's default reference doc restyled to
Vietnamese administrative typography ( Nghi dinh 30/2020/NĐ-CP conventions ).

Run from anywhere; paths resolve from this file. Requires pandoc on PATH.
    python3 scripts/make-reference.py
"""
import os
import re
import subprocess
import sys
import tempfile
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "assets", "reference-vn.docx")

FONT = "Times New Roman"
BODY_SZ = "26"  # half-points -> 13pt, the NĐ30 body size
RFONTS = (
    '<w:rFonts w:ascii="%s" w:eastAsia="%s" w:hAnsi="%s" w:cs="%s" />' % ((FONT,) * 4)
)

# A4, and NĐ30 margins: top/bottom 20mm, left 30mm, right 15mm (1mm = 56.6929 twips)
SECTPR = (
    '<w:sectPr>'
    '<w:footnotePr><w:numRestart w:val="eachSect" /></w:footnotePr>'
    '<w:pgSz w:w="11906" w:h="16838" />'
    '<w:pgMar w:top="1134" w:right="851" w:bottom="1134" w:left="1701" '
    'w:header="567" w:footer="567" w:gutter="0" />'
    '<w:cols w:space="708" />'
    '<w:docGrid w:linePitch="360" />'
    '</w:sectPr>'
)

# styleId -> (size, bold, italic, alignment, space-before, space-after)
PARA_STYLES = {
    "Normal":       (BODY_SZ, True,  False, "both",   "0",   "0"),
    "BodyText":     (BODY_SZ, True,  False, "both",   "0",   "0"),
    "FirstParagraph": (BODY_SZ, True, False, "both",  "0",   "0"),
    "Compact":      (BODY_SZ, True,  False, "both",   "0",   "0"),
    "BlockText":    (BODY_SZ, False, True,  "both",   "120", "120"),
    "Title":        ("28",    True,  False, "center", "0",   "120"),
    "Subtitle":     ("26",    True,  False, "center", "0",   "240"),
    "Author":       (BODY_SZ, False, False, "center", "0",   "60"),
    "Date":         (BODY_SZ, False, False, "center", "0",   "240"),
    "Heading1":     ("26",    True,  False, "both",   "240", "60"),
    "Heading2":     ("26",    True,  False, "both",   "180", "60"),
    "Heading3":     ("26",    True,  True,  "both",   "120", "60"),
    "Heading4":     (BODY_SZ, True,  True,  "both",   "120", "60"),
    "TOCHeading":   ("28",    True,  False, "center", "0",   "120"),
}

# line spacing 1.3 -> 240 * 1.3 = 312
LINE = "312"


def pandoc_default_reference() -> bytes:
    try:
        return subprocess.run(
            ["pandoc", "--print-default-data-file", "reference.docx"],
            check=True, capture_output=True,
        ).stdout
    except FileNotFoundError:
        sys.exit("FAIL: pandoc not found on PATH")
    except subprocess.CalledProcessError as e:
        sys.exit("FAIL: pandoc could not emit reference.docx: %s" % e.stderr.decode()[:200])


def restyle(inner: str, size: str, bold: bool, italic: bool,
            align: str, before: str, after: str) -> str:
    """Rewrite a style's pPr/rPr, appended last, matching the w:style child order."""
    orig_ppr = re.search(r"<w:pPr>(.*?)</w:pPr>", inner, re.S)
    keep_next = "<w:keepNext />" if (orig_ppr and "<w:keepNext" in orig_ppr.group(1)) else ""
    outline = ""
    if orig_ppr:
        om = re.search(r'<w:outlineLvl w:val="\d+" />', orig_ppr.group(1))
        outline = om.group(0) if om else ""

    body = re.sub(r"<w:pPr>.*?</w:pPr>", "", inner, flags=re.S)
    body = re.sub(r"<w:rPr>.*?</w:rPr>", "", body, flags=re.S)

    ppr = ('<w:pPr>%s<w:spacing w:before="%s" w:after="%s" w:line="%s" w:lineRule="auto" />'
           '<w:jc w:val="%s" />%s</w:pPr>' % (keep_next, before, after, LINE, align, outline))
    rpr = ['<w:rPr>', RFONTS]
    if bold:
        rpr.append("<w:b /><w:bCs />")
    if italic:
        rpr.append("<w:i /><w:iCs />")
    rpr += ['<w:color w:val="000000" />',
            '<w:sz w:val="%s" /><w:szCs w:val="%s" />' % (size, size), "</w:rPr>"]
    return body.rstrip() + ppr + "".join(rpr)


def patch_styles(xml: str) -> str:
    for sid, (size, bold, italic, align, before, after) in PARA_STYLES.items():
        pat = re.compile(r'(<w:style [^>]*w:styleId="%s">)(.*?)(</w:style>)' % re.escape(sid), re.S)
        m = pat.search(xml)
        if not m:
            print("  warn: style %s not found, skipped" % sid)
            continue
        inner = restyle(m.group(2), size, bold, italic, align, before, after)
        xml = xml[: m.start()] + m.group(1) + inner + m.group(3) + xml[m.end():]

    # any style we did not enumerate (Heading5-9, Abstract...) must not stay blue
    xml = xml.replace('w:val="0F4761"', 'w:val="000000"')

    # linked character styles inherit the theme font; pin them to the real font
    xml = re.sub(r'<w:rFonts [^/>]*Theme="[^"]*"[^/]*/>', RFONTS, xml)
    # docDefaults: explicit font, 13pt, Vietnamese language tag
    xml = re.sub(
        r"<w:rPrDefault>\s*<w:rPr>.*?</w:rPr>",
        "<w:rPrDefault>\n      <w:rPr>%s<w:sz w:val=\"%s\" /><w:szCs w:val=\"%s\" />"
        "<w:lang w:val=\"vi-VN\" w:eastAsia=\"vi-VN\" w:bidi=\"ar-SA\" /></w:rPr>" % (RFONTS, BODY_SZ, BODY_SZ),
        xml, flags=re.S, count=1)
    # default paragraph spacing: single, no gap
    xml = re.sub(r"<w:pPrDefault>\s*<w:pPr>.*?</w:pPr>",
                 '<w:pPrDefault>\n      <w:pPr><w:spacing w:before="0" w:after="0" w:line="%s" w:lineRule="auto" /></w:pPr>' % LINE,
                 xml, flags=re.S, count=1)
    return xml


def main() -> None:
    src = pandoc_default_reference()
    tmp = tempfile.mkdtemp(prefix="refvn-")
    raw = os.path.join(tmp, "reference.docx")
    with open(raw, "wb") as fh:
        fh.write(src)

    with zipfile.ZipFile(raw) as zin:
        names = zin.namelist()
        parts = {n: zin.read(n) for n in names}

    styles = patch_styles(parts["word/styles.xml"].decode("utf-8"))
    parts["word/styles.xml"] = styles.encode("utf-8")

    doc = parts["word/document.xml"].decode("utf-8")
    doc = re.sub(r"<w:sectPr>.*?</w:sectPr>", SECTPR, doc, flags=re.S, count=1)
    if "w:pgSz" not in doc:
        sys.exit("FAIL: could not inject page size into document.xml")
    parts["word/document.xml"] = doc.encode("utf-8")

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED) as zout:
        for n in names:
            zout.writestr(n, parts[n])

    print("ok: %s" % os.path.relpath(OUT, os.path.join(HERE, "..")))
    print("    font=%s  body=%spt  A4  margins L17.0/R8.5/T11.3/B11.3mm  line=1.3" % (
        FONT, int(BODY_SZ) / 2))


if __name__ == "__main__":
    main()
