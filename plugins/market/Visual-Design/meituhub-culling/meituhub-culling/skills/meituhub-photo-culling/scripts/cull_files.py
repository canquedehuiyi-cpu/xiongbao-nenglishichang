#!/usr/bin/env python3
"""Read-only inventory and non-destructive, manifest-driven photo copying."""
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import unicodedata

FORMATS = {'.jpg', '.jpeg', '.png', '.webp', '.heic', '.heif', '.tif', '.tiff',
           '.dng', '.cr2', '.cr3', '.nef', '.arw', '.raf', '.orf', '.rw2', '.pef', '.srw'}


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def inventory(source):
    root = source.resolve(strict=True)
    if not root.is_dir():
        raise ValueError('Source must be a directory')
    files, skipped = [], []
    for parent, dirs, names in os.walk(root, followlinks=False):
        for name in list(dirs):
            path = Path(parent) / name
            if path.is_symlink():
                dirs.remove(name)
                skipped.append({'path': path.relative_to(root).as_posix(), 'reason': 'symlink'})
        for name in sorted(names):
            path = Path(parent) / name
            rel = path.relative_to(root).as_posix()
            if path.is_symlink():
                skipped.append({'path': rel, 'reason': 'symlink'})
            elif path.suffix.lower() in FORMATS and path.is_file():
                files.append({'source_relpath': rel, 'bytes': path.stat().st_size,
                              'format': path.suffix.lower()[1:], 'decision': 'review'})
    return {'files': sorted(files, key=lambda x: x['source_relpath']), 'skipped': skipped,
            'count': len(files), 'visual_analysis': 'not_performed'}


def resolve_photo(root, rel):
    if not isinstance(rel, str) or not rel or '\\' in rel or ':' in rel:
        raise ValueError('Use a relative POSIX photo path')
    parts = PurePosixPath(rel)
    if parts.is_absolute() or '..' in parts.parts or any(ord(c) < 32 for c in rel):
        raise ValueError('Unsafe source path')
    path = root
    for part in parts.parts:
        path = path / part
        if path.is_symlink():
            raise ValueError('Symlink inputs are not copied')
    actual = path.resolve(strict=True)
    if not actual.is_relative_to(root) or not actual.is_file() or actual.suffix.lower() not in FORMATS:
        raise ValueError('Input is not a supported photo under the source directory')
    return actual, parts.as_posix()


def copy_selected(source, manifest_path, output):
    root = source.resolve(strict=True)
    if not root.is_dir():
        raise ValueError('Source must be a directory')
    if output.is_symlink() or output.exists():
        raise ValueError('Output must be a new directory; existing content is never overwritten')
    destination = output.resolve()
    if destination.is_relative_to(root) or root.is_relative_to(destination):
        raise ValueError('Output must be separate from the source tree')
    raw = json.loads(manifest_path.read_text(encoding='utf-8'))
    records = raw.get('selections')
    if not isinstance(records, list):
        raise ValueError('Manifest requires a selections array')
    plan, seen = [], set()
    for record in records:
        if not isinstance(record, dict) or record.get('decision') not in {'selected', 'rejected', 'review'}:
            raise ValueError('Every item needs a valid decision')
        actual, rel = resolve_photo(root, record.get('source_relpath'))
        key = unicodedata.normalize('NFC', rel).casefold()
        if key in seen:
            raise ValueError('Duplicate or case-colliding relative path')
        seen.add(key)
        if record['decision'] == 'selected':
            if not record.get('reason') or not record.get('evidence_id'):
                raise ValueError('Selected photos require a reason and evidence_id')
            plan.append((actual, rel, dict(record)))
    if not plan:
        raise ValueError('No selected photos; no output directory created')
    destination.mkdir(parents=True, exist_ok=False)
    copied = []
    try:
        for original, rel, record in plan:
            target = destination / '01_精选保留' / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            before = digest(original)
            with original.open('rb') as reader, target.open('xb') as writer:
                shutil.copyfileobj(reader, writer)
            after = digest(target)
            if after != before or digest(original) != before:
                raise RuntimeError('Source changed during copy or copy integrity check failed')
            record.update({'source_relpath': rel, 'output_relpath': target.relative_to(destination).as_posix(),
                           'sha256': after, 'bytes': target.stat().st_size})
            copied.append(record)
        (destination / 'selected_files.txt').write_text(''.join(x['source_relpath']+'\n' for x in copied), encoding='utf-8')
        result = {'status': 'copied', 'copied_count': len(copied), 'copied': copied,
                  'decisions': records, 'source_modified': False,
                  'note': 'Evidence IDs are supplied by the caller; this script does not perform visual analysis.'}
        (destination / 'manifest.json').write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
        return {'status': 'copied', 'count': len(copied), 'output': str(destination)}
    except Exception as exc:
        # Preserve partial files for inspection; never roll back by touching source files.
        (destination / 'copy-error.json').write_text(json.dumps({'status': 'partial', 'copied': copied,
            'error': str(exc)}, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    scan = sub.add_parser('inventory')
    scan.add_argument('source', type=Path)
    copy = sub.add_parser('copy')
    copy.add_argument('source', type=Path)
    copy.add_argument('manifest', type=Path)
    copy.add_argument('output', type=Path)
    args = parser.parse_args()
    result = inventory(args.source) if args.command == 'inventory' else copy_selected(args.source, args.manifest, args.output)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
