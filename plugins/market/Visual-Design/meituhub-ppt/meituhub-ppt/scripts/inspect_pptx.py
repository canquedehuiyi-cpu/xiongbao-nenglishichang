#!/usr/bin/env python3
"""Extract a read-only PPTX content ledger using the Python standard library."""
import argparse
import hashlib
import json
from pathlib import Path
import posixpath
import zipfile
import xml.etree.ElementTree as ET

NS = {'p': 'http://schemas.openxmlformats.org/presentationml/2006/main',
      'a': 'http://schemas.openxmlformats.org/drawingml/2006/main',
      'r': 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'}


def inspect(path):
    with zipfile.ZipFile(path) as z:
        names = set(z.namelist())
        if len(names) > 100000 or sum(x.file_size for x in z.infolist()) > 1024**3:
            raise ValueError('PPTX exceeds inspection limits')

        def xml(name):
            data = z.read(name)
            if b'<!DOCTYPE' in data or b'<!ENTITY' in data:
                raise ValueError('DTD/entity declarations are not supported')
            return ET.fromstring(data)

        def relations(part):
            parent, base = posixpath.split(part)
            relname = posixpath.join(parent, '_rels', base+'.rels')
            if relname not in names:
                return {}
            result = {}
            for rel in xml(relname):
                external = rel.get('TargetMode') == 'External'
                target = rel.get('Target', '')
                resolved = target if external else posixpath.normpath(posixpath.join(parent, target))
                if not external and target.startswith('/'):
                    resolved = target.lstrip('/')
                result[rel.get('Id')] = {'type': rel.get('Type', '').split('/')[-1],
                                       'target': resolved, 'external': external}
            return result

        rels = relations('ppt/presentation.xml')
        presentation = xml('ppt/presentation.xml')
        slides = []
        for number, slideid in enumerate(presentation.findall('p:sldIdLst/p:sldId', NS), 1):
            rid = slideid.get('{'+NS['r']+'}id')
            part = rels[rid]['target']
            root = xml(part)
            srels = relations(part)
            notes, charts = [], []
            for rel in srels.values():
                if rel['external'] or rel['target'] not in names:
                    continue
                if rel['type'] == 'notesSlide':
                    notes = [node.text or '' for node in xml(rel['target']).findall('.//a:t', NS)]
                elif rel['type'] == 'chart':
                    chart = xml(rel['target'])
                    charts.append({'part': rel['target'], 'sha256': hashlib.sha256(z.read(rel['target'])).hexdigest(),
                                   'cached_values': [node.text or '' for node in chart.iter() if node.tag.endswith('}v')]})
            slides.append({'page': number, 'part': part,
                           'texts': [node.text or '' for node in root.findall('.//a:t', NS)],
                           'notes': notes, 'charts': charts, 'relationships': list(srels.values()),
                           'has_timing': root.find('p:timing', NS) is not None})
        media = [{'part': name, 'bytes': z.getinfo(name).file_size,
                  'sha256': hashlib.sha256(z.read(name)).hexdigest()}
                 for name in sorted(names) if name.startswith('ppt/media/') and not name.endswith('/')]
        return {'pages': len(slides), 'slides': slides, 'media': media,
                'render_verified': False, 'editability_verified': False,
                'limits': 'Structure and cached values only; not a complete parser for all Office objects.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    if args.input.resolve() == args.output.resolve():
        raise ValueError('Output cannot overwrite source')
    result = inspect(args.input)
    with args.output.open('x', encoding='utf-8') as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2)
        stream.write('\n')


if __name__ == '__main__':
    main()
