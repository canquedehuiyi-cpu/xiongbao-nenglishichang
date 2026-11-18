# -*- coding: utf-8 -*-
"""Generic docx layout census audit (no per-doc spec needed).
Usage: python audit_docx.py <file.docx>
Prints per-class font/paragraph property census (minority combos = suspects),
runs without rPr (template-inheritance trap), half-width punctuation in CJK
context, auto-numbered paragraphs, vertAlign usage, table sizes/widths."""
import sys
import re
from collections import Counter
from docx import Document
from docx.oxml.ns import qn

HALF = re.compile(r'[一-鿿][,;:!?()]|[,;:!?()][一-鿿]')


def el(rPr, tag):
    return None if rPr is None else rPr.find(qn('w:' + tag))


def fonts_of(rPr):
    f = el(rPr, 'rFonts')
    if f is None:
        return (None, None)
    return (f.get(qn('w:eastAsia')), f.get(qn('w:ascii')))


def sz_of(rPr):
    e = el(rPr, 'sz')
    return None if e is None else int(e.get(qn('w:val'))) / 2.0


def bold_of(rPr):
    e = el(rPr, 'b')
    if e is None:
        return None
    return e.get(qn('w:val')) not in ('0', 'false', 'none')


def is_head(p):
    if (p.style.name or '').startswith('Heading'):
        return True
    pPr = p._p.find(qn('w:pPr'))
    return pPr is not None and pPr.find(qn('w:outlineLvl')) is not None


def main(path):
    d = Document(path)
    dd = d.styles.element.find(qn('w:docDefaults'))
    d_rpr = None
    if dd is not None:
        rprd = dd.find(qn('w:rPrDefault'))
        if rprd is not None:
            d_rpr = rprd.find(qn('w:rPr'))

    def chain(st):
        out, seen = [], set()
        while st is not None and st.style_id not in seen:
            seen.add(st.style_id)
            e = st.element.find(qn('w:rPr'))
            if e is not None:
                out.append(e)
            st = st.base_style
        return out

    def resolve(r_rpr, st):
        ea = asc = sz = None
        b = None
        srcs = ([r_rpr] if r_rpr is not None else []) + chain(st)
        if d_rpr is not None:
            srcs.append(d_rpr)
        for rPr in srcs:
            fe, fa = fonts_of(rPr)
            ea = ea or fe
            asc = asc or fa
            if sz is None:
                sz = sz_of(rPr)
            if b is None:
                b = bold_of(rPr)
        return (ea, asc, sz, bool(b))

    ps = d.paragraphs
    first_head = next((i for i, p in enumerate(ps) if is_head(p)), len(ps))

    def cls(i, p):
        if i < first_head:
            return 'front'
        n = p.style.name or ''
        if is_head(p):
            return 'head'
        if n.startswith('TOC'):
            return 'toc'
        if n.lower().startswith('caption'):
            return 'cap'
        return 'body'

    fc, pc, npar = {}, {}, Counter()
    no_rpr, half, numpr, vert = [], [], [], Counter()
    for i, p in enumerate(ps):
        c = cls(i, p)
        npar[c] += 1
        fc.setdefault(c, Counter())
        pc.setdefault(c, Counter())
        pf = p.paragraph_format
        ind = None if pf.first_line_indent is None else round(pf.first_line_indent.pt, 1)
        ls = pf.line_spacing
        ls = round(ls, 2) if isinstance(ls, float) else (None if ls is None else round(ls.pt, 1))
        pc[c][(ind, ls, str(pf.alignment))] += 1
        pPr = p._p.find(qn('w:pPr'))
        if pPr is not None and pPr.find(qn('w:numPr')) is not None:
            numpr.append((i, p.text[:24]))
        for m in HALF.finditer(p.text):
            half.append((i, p.text[max(0, m.start() - 6):m.end() + 6]))
        for r in p.runs:
            rPr = r._element.find(qn('w:rPr'))
            if rPr is None:
                no_rpr.append(i)
            fc[c][resolve(rPr, p.style)] += 1
            va = el(rPr, 'vertAlign')
            if va is not None:
                vert[va.get(qn('w:val'))] += 1

    print('FILE', path)
    for c in ('front', 'head', 'body', 'toc', 'cap'):
        if not npar[c]:
            continue
        print(f'CLASS {c} paras={npar[c]}')
        for combo, n in fc[c].most_common(8):
            print('   font', combo, 'x', n)
        for combo, n in pc[c].most_common(6):
            print('   para(ind_pt,ls,align)', combo, 'x', n)
    print('RUNS_WITHOUT_RPR', len(no_rpr), sorted(set(no_rpr))[:25],
          '...+%d' % (len(set(no_rpr)) - 25) if len(set(no_rpr)) > 25 else '')
    print('HALFWIDTH_PUNCT', len(half))
    for h in half[:15]:
        print('   ', h)
    print('NUMPR', numpr[:15])
    print('VERTALIGN', dict(vert))
    spacer = []
    for i, p in enumerate(ps):
        if p.text == '' and len(p.runs) == 1:
            brs = p._p.findall('.//' + qn('w:br'))
            if len(brs) == 1 and brs[0].get(qn('w:type')) == 'page':
                nxt = ps[i + 1].style.name if i + 1 < len(ps) else '(end)'
                spacer.append((i, nxt))
    print('SPACER_BREAK', len(spacer), spacer[:20],
          '(empty para holding only a page break: orphans into a blank page when preceding content fills the page; prefer pageBreakBefore on the next heading)')
    nohdr = [ti for ti, t in enumerate(d.tables)
             if t.rows[0]._tr.find(qn('w:trPr')) is None
             or t.rows[0]._tr.find(qn('w:trPr')).find(qn('w:tblHeader')) is None]
    print('TABLES_WITHOUT_REPEAT_HEADER', nohdr)
    tc = Counter()
    print('TABLES', len(d.tables))
    for ti, t in enumerate(d.tables):
        widths = [None if c.width is None else c.width.twips for c in t.columns]
        print(f' table {ti} rows={len(t.rows)} cols={len(t.columns)} widths={widths}')
        for row in t.rows:
            for cell in row.cells:
                for p in cell.paragraphs:
                    for r in p.runs:
                        tc[resolve(r._element.find(qn('w:rPr')), p.style)] += 1
    for combo, n in tc.most_common(8):
        print('   tfont', combo, 'x', n)


if __name__ == '__main__':
    try:
        main(sys.argv[1])
    except Exception as e:
        print('ERROR', type(e).__name__, e)
        sys.exit(1)