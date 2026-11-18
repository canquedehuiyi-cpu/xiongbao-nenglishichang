#!/usr/bin/env python3
"""pptx-lite: build a 16:9 .pptx from a JSON spec. Fast, deterministic, no browser.

Usage: build_deck.py <spec.json> <out.pptx>
Spec schema (see SKILL.md). Prints one concise status line.
"""
import json, sys

from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE

SW, SH = 13.333, 7.5          # 16:9 inches
M = 0.6                      # side margin

DEFAULT_THEME = {
    "primary": "1E5128", "accent": "4E9F3D", "bg": "FFFFFF",
    "text": "333333", "muted": "666666", "light": "F0F7EE", "font": "Calibri",
}


def C(h):
    return RGBColor.from_string(h)


def new_prs():
    p = Presentation()
    p.slide_width = Inches(SW)
    p.slide_height = Inches(SH)
    return p


def blank(prs):
    return prs.slides.add_slide(prs.slide_layouts[6])


def rect(slide, x, y, w, h, fill=None, line=None):
    sh = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(x), Inches(y), Inches(w), Inches(h))
    if fill:
        sh.fill.solid(); sh.fill.fore_color.rgb = C(fill)
    else:
        sh.fill.background()
    if line:
        sh.line.color.rgb = C(line); sh.line.width = Pt(1)
    else:
        sh.line.fill.background()
    sh.shadow.inherit = False
    return sh


def textbox(slide, x, y, w, h, anchor=MSO_ANCHOR.TOP):
    tb = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = tb.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = anchor
    return tf


def para(tf, text, size, color, bold=False, first=False, align=None, space_after=6, level=0):
    p = tf.paragraphs[0] if first else tf.add_paragraph()
    p.text = text
    p.level = level
    p.font.size = Pt(size)
    p.font.bold = bold
    p.font.color.rgb = C(color)
    p.space_after = Pt(space_after)
    if align:
        p.alignment = align
    return p


def header(slide, t, title):
    """Top accent band + slide title + underline rule."""
    rect(slide, 0, 0, SW, 0.9, fill=t["primary"])
    tf = textbox(slide, M, 0.18, SW - 2 * M, 0.6, anchor=MSO_ANCHOR.MIDDLE)
    para(tf, t.get("kicker", ""), 12, "FFFFFF", bold=True, first=True)
    tf = textbox(slide, M, 1.15, SW - 2 * M, 0.8)
    para(tf, title, 30, t["primary"], bold=True, first=True)
    rect(slide, M, 2.0, SW - 2 * M, 0.045, fill=t["accent"])


def footer(slide, t, n, total):
    tf = textbox(slide, SW - M - 1.6, SH - 0.45, 1.6, 0.3)
    para(tf, f"{n} / {total}", 10, t["accent"], first=True, align=PP_ALIGN.RIGHT)


def s_title(prs, t, s):
    sl = blank(prs)
    rect(sl, 0, 0, SW, SH, fill=t["primary"])
    rect(sl, 0, SH - 0.35, SW, 0.35, fill=t["accent"])
    tf = textbox(sl, M, 2.2, SW - 2 * M, 1.4, anchor=MSO_ANCHOR.MIDDLE)
    para(tf, s["title"], 44, "FFFFFF", bold=True, first=True, align=PP_ALIGN.CENTER)
    if s.get("subtitle"):
        tf = textbox(sl, M, 3.7, SW - 2 * M, 1.0)
        para(tf, s["subtitle"], 20, t["light"], first=True, align=PP_ALIGN.CENTER)
    if s.get("footer"):
        tf = textbox(sl, M, 6.6, SW - 2 * M, 0.4)
        para(tf, s["footer"], 12, "BBBBBB", first=True, align=PP_ALIGN.CENTER)
    return sl


def s_section(prs, t, s):
    sl = blank(prs)
    rect(sl, 0, 0, SW, SH, fill=t["light"])
    rect(sl, 0, 0, 0.35, SH, fill=t["accent"])
    tf = textbox(sl, 1.2, 3.0, SW - 2.4, 1.2, anchor=MSO_ANCHOR.MIDDLE)
    para(tf, s["title"], 36, t["primary"], bold=True, first=True)
    return sl


def _bullets(tf, t, items, size):
    first = True
    for it in items:
        txt = it["text"] if isinstance(it, dict) else it
        lvl = it.get("level", 0) if isinstance(it, dict) else 0
        mark = "•  " if lvl == 0 else "–  "
        para(tf, mark + txt, size - (2 if lvl else 0), t["text"],
             first=first, level=lvl, space_after=8)
        first = False


def s_bullets(prs, t, s):
    sl = blank(prs)
    header(sl, t, s["title"])
    tf = textbox(sl, M, 2.35, SW - 2 * M, SH - 2.9)
    _bullets(tf, t, s["bullets"], s.get("size", 20))
    return sl


def s_two_col(prs, t, s):
    sl = blank(prs)
    header(sl, t, s["title"])
    cw = (SW - 2 * M - 0.5) / 2
    for i, key in enumerate(("left", "right")):
        col = s[key]
        x = M + i * (cw + 0.5)
        rect(sl, x, 2.35, cw, 0.5, fill=t["accent"])
        tf = textbox(sl, x + 0.15, 2.4, cw - 0.3, 0.4, anchor=MSO_ANCHOR.MIDDLE)
        para(tf, col["heading"], 16, "FFFFFF", bold=True, first=True)
        tf = textbox(sl, x, 3.05, cw, SH - 3.6)
        _bullets(tf, t, col["bullets"], s.get("size", 16))
    return sl


def s_table(prs, t, s):
    sl = blank(prs)
    header(sl, t, s["title"])
    rows, cols = len(s["rows"]) + 1, len(s["header"])
    gf = sl.shapes.add_table(rows, cols, Inches(M), Inches(2.35),
                             Inches(SW - 2 * M), Inches(0.5 * rows))
    tbl = gf.table
    for c, htxt in enumerate(s["header"]):
        cell = tbl.cell(0, c)
        cell.fill.solid(); cell.fill.fore_color.rgb = C(t["primary"])
        p = cell.text_frame.paragraphs[0]; p.text = htxt
        p.font.bold = True; p.font.size = Pt(14); p.font.color.rgb = C("FFFFFF")
    for r, row in enumerate(s["rows"], start=1):
        for c, val in enumerate(row):
            cell = tbl.cell(r, c)
            cell.fill.solid()
            cell.fill.fore_color.rgb = C(t["light"] if r % 2 == 0 else "FFFFFF")
            p = cell.text_frame.paragraphs[0]; p.text = str(val)
            p.font.size = Pt(13); p.font.color.rgb = C(t["text"])
    return sl


def s_stats(prs, t, s):
    sl = blank(prs)
    header(sl, t, s["title"])
    n = len(s["stats"])
    gap = 0.3
    cw = (SW - 2 * M - gap * (n - 1)) / n
    for i, st in enumerate(s["stats"]):
        x = M + i * (cw + gap)
        rect(sl, x, 2.6, cw, 2.2, fill=t["light"])
        rect(sl, x, 2.6, cw, 0.08, fill=t["accent"])
        tf = textbox(sl, x + 0.1, 2.95, cw - 0.2, 1.0, anchor=MSO_ANCHOR.MIDDLE)
        para(tf, st["value"], 34, t["primary"], bold=True, first=True, align=PP_ALIGN.CENTER)
        tf = textbox(sl, x + 0.15, 3.95, cw - 0.3, 0.8)
        para(tf, st["label"], 12, t["muted"], first=True, align=PP_ALIGN.CENTER)
    return sl


def s_closing(prs, t, s):
    sl = blank(prs)
    rect(sl, 0, 0, SW, SH, fill=t["primary"])
    tf = textbox(sl, M, 1.6, SW - 2 * M, 1.0, anchor=MSO_ANCHOR.MIDDLE)
    para(tf, s["title"], 40, "FFFFFF", bold=True, first=True, align=PP_ALIGN.CENTER)
    if s.get("subtitle"):
        tf = textbox(sl, M, 2.7, SW - 2 * M, 0.6)
        para(tf, s["subtitle"], 18, t["light"], first=True, align=PP_ALIGN.CENTER)
    if s.get("bullets"):
        tf = textbox(sl, 2.5, 3.7, SW - 5.0, 2.6)
        _bullets(tf, {**t, "text": "DDEEDD"}, s["bullets"], 16)
    return sl


BUILDERS = {
    "title": s_title, "section": s_section, "bullets": s_bullets,
    "two_col": s_two_col, "table": s_table, "stats": s_stats, "closing": s_closing,
}


def main():
    if len(sys.argv) != 3:
        print("ERROR: usage: build_deck.py <spec.json> <out.pptx>"); sys.exit(2)
    try:
        with open(sys.argv[1], encoding="utf-8") as f:
            spec = json.load(f)
    except Exception as e:
        print(f"ERROR: bad spec JSON: {e}"); sys.exit(2)

    t = {**DEFAULT_THEME, **spec.get("theme", {})}
    prs = new_prs()
    slides = spec.get("slides", [])
    total = len(slides)
    for i, s in enumerate(slides, start=1):
        b = BUILDERS.get(s.get("type"))
        if not b:
            print(f"ERROR: unknown slide type '{s.get('type')}' at index {i-1}"); sys.exit(2)
        sl = b(prs, t, s)
        if s.get("type") not in ("title", "section", "closing"):
            footer(sl, t, i, total)
    prs.save(sys.argv[2])
    print(f"OK: {total} slides -> {sys.argv[2]}")


if __name__ == "__main__":
    main()
