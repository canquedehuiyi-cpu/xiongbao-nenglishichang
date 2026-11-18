# -*- coding: utf-8 -*-
"""ANNOTATED TEMPLATE — copy into a project script and adapt ranges/classes to the
audit census. Index system = python-docx d.paragraphs (TOC inside sdt is NOT listed).
Never reuse office-docx MCP blockIndexes here (different index system)."""
import copy
from docx import Document
from docx.shared import Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH as AL
from docx.oxml.ns import qn

PATH = r'report.docx'  # change to the target file's absolute path
EA, ASC = '宋体', 'Times New Roman'


def set_run(r, size=12, bold=False, ea=EA, asc=ASC):
    r.font.name = asc                      # ascii + hAnsi
    r._element.rPr.rFonts.set(qn('w:eastAsia'), ea)
    r.font.size = Pt(size)
    r.font.bold = bold


def pin_par(p, size=12, bold=False, indent=24, ls=1.5, align=None):
    pf = p.paragraph_format
    pf.first_line_indent = Pt(indent) if indent is not None else None
    pf.line_spacing = ls
    pf.alignment = align                   # None = inherit (justified from style)
    for r in p.runs:
        set_run(r, size, bold)


def rebuild(p, segments):
    """segments = [(text, bold[, subscript])]; clears runs, keeps paragraph pPr."""
    for r in list(p.runs):
        r._element.getparent().remove(r._element)
    for seg in segments:
        r = p.add_run(seg[0])
        set_run(r, bold=seg[1])
        if len(seg) > 2 and seg[2]:
            va = r._element.rPr.makeelement(qn('w:vertAlign'), {qn('w:val'): 'subscript'})
            r._element.rPr.append(va)


d = Document(PATH)
ps = d.paragraphs

# 1) classes from audit census: front/cover indices, HEAD set, body range.
# HEAD = {21, 22, 55, 57, 68}
# for i in HEAD: pin_par(ps[i], size=14 if i == 21 else 12, bold=True, indent=None)
# for i in range(23, 83):
#     if i not in HEAD: pin_par(ps[i])

# 2) bold lead-in to first colon (keep doc-wide convention):
# lead, rest = ps[i].text.split('：', 1); rebuild(ps[i], [(lead + '：', True), (rest, False)])

# 3) real subscripts for formulas:
# rebuild(ps[i], [('P=(B', False), ('0', False, True), ('-B', False), ('t', False, True),
#                 (')/B', False), ('0', False, True), ('×100%', False)])

# 4) tables: header bold+center, body left, single spacing, no indent:
# for t in d.tables:
#     for ri, row in enumerate(t.rows):
#         for cell in row.cells:
#             for p in cell.paragraphs:
#                 pin_par(p, bold=(ri == 0), indent=None, ls=1.0,
#                         align=AL.CENTER if ri == 0 else AL.LEFT)
# column widths (twips) via cell.width or MCP setTableCellFormat; narrow last column
# causes 1-2 chars/line; justified cells stretch -> COM alignment (render script -AlignTable1).

# 5) TOC styles font pinning:
# for nm in ('TOC 1', 'TOC 2', 'TOC 3'):
#     rPr = d.styles[nm].element.get_or_add_rPr()
#     rf = rPr.get_or_add_rFonts()
#     rf.set(qn('w:eastAsia'), EA); rf.set(qn('w:ascii'), ASC); rf.set(qn('w:hAnsi'), ASC)

# 6) auto-number vs manual-number mix: drop w:numPr and mirror a manual item's pPr:
# ref = ps[72]; p = ps[69]
# p._p.replace(p._p.find(qn('w:pPr')), copy.deepcopy(ref._p.find(qn('w:pPr'))))
# p.style = ref.style; rebuild(p, [('1、' + p.text, True)])  # capture text BEFORE clearing

d.save(PATH)