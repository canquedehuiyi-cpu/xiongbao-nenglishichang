#!/usr/bin/env python3
"""Read-only PPTX text-box checks. Actual rendering is always a separate required check."""
import argparse
import json
from pathlib import Path
import re
import zipfile
import xml.etree.ElementTree as ET

NS = {'p': 'http://schemas.openxmlformats.org/presentationml/2006/main',
      'a': 'http://schemas.openxmlformats.org/drawingml/2006/main'}
EMU = 914400

def inspect_pptx(filename):
    result = {'file': str(filename), 'checks': [], 'pages': [],
              'render_review': 'pending', 'installed_fonts_and_glyph_coverage': 'unverified',
              'limitations': ['Box geometry cannot determine text wrapping, glyph rendering or actual overflow inside a box.',
                             'Grouped/rotated text is reported for manual review, not declared checked.',
                             'An overlap is a review candidate; intentional visual layering must be judged in the rendered page.']}
    with zipfile.ZipFile(filename) as archive:
        presentation = ET.fromstring(archive.read('ppt/presentation.xml'))
        canvas = presentation.find('p:sldSz', NS)
        cw, ch = int(canvas.get('cx')), int(canvas.get('cy'))
        # Use presentation order, rather than assuming slide file numbers are page numbers.
        rels = ET.fromstring(archive.read('ppt/_rels/presentation.xml.rels'))
        targets = {r.get('Id'): r.get('Target') for r in rels}
        slide_ids = presentation.find('p:sldIdLst', NS)
        order = []
        for node in slide_ids:
            rid = node.get('{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id')
            target = targets[rid]
            if target.startswith('/'):
                order.append(target.lstrip('/'))
            else:
                import posixpath
                order.append(posixpath.normpath('ppt/' + target))
        for page_number, name in enumerate(order, 1):
            root = ET.fromstring(archive.read(name))
            parents = {child: parent for parent in root.iter() for child in parent}
            boxes, fonts, issues = [], set(), []
            for shape in root.findall('.//p:sp', NS):
                body = shape.find('p:txBody', NS)
                if body is None:
                    continue
                text = ''.join(n.text or '' for n in body.findall('.//a:t', NS))
                if not text.strip():
                    continue
                props = shape.find('p:nvSpPr/p:cNvPr', NS)
                oid = props.get('id') if props is not None else 'unknown'
                label = props.get('name') if props is not None else 'text'
                for element in body.iter():
                    if element.tag.rsplit('}', 1)[-1] in {'latin', 'ea', 'cs'} and element.get('typeface'):
                        fonts.add(element.get('typeface'))
                def issue(kind, severity, detail, other=None):
                    value = {'kind': kind, 'severity': severity, 'object_id': oid,
                             'object_name': label, 'text_excerpt': text[:80], 'detail': detail}
                    if other is not None:
                        value['other_object_id'] = other
                    issues.append(value)
                grouped = False
                ancestor = parents.get(shape)
                while ancestor is not None:
                    if ancestor.tag == '{' + NS['p'] + '}grpSp':
                        grouped = True
                    ancestor = parents.get(ancestor)
                transform = shape.find('p:spPr/a:xfrm', NS)
                if grouped or transform is None or int(transform.get('rot', '0')) % 21600000:
                    issue('complex_transform', 'review', 'Grouped, rotated or missing geometry; inspect actual rendering.')
                    continue
                offset, extent = transform.find('a:off', NS), transform.find('a:ext', NS)
                if offset is None or extent is None:
                    issue('missing_geometry', 'review', 'Text-box position/size unavailable.')
                    continue
                x, y = int(offset.get('x')), int(offset.get('y'))
                w, h = int(extent.get('cx')), int(extent.get('cy'))
                if w <= 0 or h <= 0:
                    issue('invalid_text_box', 'error', 'Text-box width or height is not positive.')
                    continue
                # Allow only small rounding differences (~0.5pt).
                tolerance = 6350
                if x < -tolerance or y < -tolerance or x+w > cw+tolerance or y+h > ch+tolerance:
                    issue('text_box_outside_canvas', 'error', 'Text box extends beyond the slide canvas; verify clipping and repair.')
                if '\ufffd' in text:
                    issue('replacement_character', 'review', 'Literal Unicode replacement character found; compare with source.')
                autofit = body.find('a:bodyPr/a:normAutofit', NS)
                if autofit is not None and int(autofit.get('fontScale', '100000')) < 100000:
                    issue('font_shrunk', 'review', 'Saved text autofit reduced font size; inspect legibility.')
                boxes.append({'id': oid, 'name': label, 'rect': [x, y, w, h], 'text': text[:80]})
            for i, box in enumerate(boxes):
                x, y, w, h = box['rect']
                for other in boxes[i+1:]:
                    ox, oy, ow, oh = other['rect']
                    iw = max(0, min(x+w, ox+ow)-max(x, ox))
                    ih = max(0, min(y+h, oy+oh)-max(y, oy))
                    if iw > 6350 and ih > 6350 and iw*ih / min(w*h, ow*oh) > .03:
                        issues.append({'kind': 'text_box_overlap', 'severity': 'review',
                                       'object_id': box['id'], 'other_object_id': other['id'],
                                       'text_excerpt': box['text'],
                                       'detail': 'Text-box rectangles overlap; verify actual text collision or intentional layering.'})
            result['pages'].append({'page': page_number, 'slide_part': name,
                                    'measured_text_boxes': len(boxes), 'declared_fonts': sorted(fonts),
                                    'issues': issues})
    issues = [issue for page in result['pages'] for issue in page['issues']]
    result['summary'] = {'pages': len(result['pages']),
                         'geometry_errors': sum(i['severity'] == 'error' for i in issues),
                         'review_candidates': sum(i['severity'] == 'review' for i in issues),
                         'geometry': 'requires_repair' if any(i['severity'] == 'error' for i in issues) else 'no_detected_error',
                         'delivery_ready': False}
    return result

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('pptx', type=Path)
    parser.add_argument('--out', type=Path, help='Write a JSON report outside the input PPTX')
    args = parser.parse_args()
    result = inspect_pptx(args.pptx)
    data = json.dumps(result, ensure_ascii=False, indent=2)
    if args.out:
        if args.out.resolve() == args.pptx.resolve():
            parser.error('Report must not overwrite the PPTX')
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(data, encoding='utf-8')
    else:
        print(data)
    return 2 if result['summary']['geometry_errors'] else 0

if __name__ == '__main__':
    raise SystemExit(main())
