#!/usr/bin/env python3
"""Render a self-contained ecommerce delivery from public project data.

Python 3.9+ standard library; no network, design API or account operations.
All local image paths are relative to the input JSON directory. Existing output
directories are never overwritten. Private execution receipts must stay separate.
"""
import argparse
import copy
import hashlib
from html import escape
import json
from pathlib import Path
import re
import shutil
import sys
import tempfile
from urllib.parse import parse_qsl, urlsplit
import zipfile

STAGES = {'selection': '选品研究', 'product': '商品资料', 'content': '商品文案',
          'visual': '商品图片', 'campaign': '活动策划', 'review': '检查与复盘'}
STATUSES = {'planned': '待制作', 'pending': '制作中', 'delivered': '已交付',
            'failed': '未完成', 'outdated': '待更新', 'reference': '参考素材'}
MAX_IMAGE_BYTES = 64 * 1024 * 1024


def require(condition, message):
    if not condition:
        raise ValueError(message)


def fields(value, allowed, required, label):
    require(isinstance(value, dict), f'{label}: expected an object')
    require(set(value) <= set(allowed.split()), f'{label}: unknown fields')
    require(set(required.split()) <= set(value), f'{label}: missing required fields')


def string(value, label, limit=30000):
    require(isinstance(value, str) and bool(value.strip()) and len(value) <= limit, f'{label}: invalid text')
    return value


def identifier(value):
    require(isinstance(value, str) and bool(re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,63}', value)), 'Invalid record ID')
    return value


def unique_ids(records, label):
    require(isinstance(records, list), f'{label}: expected a list')
    ids = [identifier(r.get('id')) if isinstance(r, dict) else identifier(None) for r in records]
    require(len(set(ids)) == len(ids), f'{label}: duplicate IDs')
    return set(ids)


def public_url(url):
    string(url, 'source URL', 4096)
    require(not re.search(r'[\s\x00-\x1f\x7f\\]', url), 'Invalid public URL')
    try:
        parsed = urlsplit(url)
        _ = parsed.port
    except ValueError:
        raise ValueError('Invalid public URL') from None
    require(parsed.scheme in {'https', 'http'} and bool(parsed.hostname) and not parsed.username and not parsed.password, 'Invalid public URL')
    secret_keys = {'token', 'access_token', 'refresh_token', 'api_key', 'apikey', 'signature', 'x-amz-signature', 'security-token', 'authorization', 'credential'}
    require(not any(k.lower() in secret_keys for k, _ in parse_qsl(parsed.query)), 'Private ticket URLs do not belong in delivery data')
    require('/mcp-files/' not in parsed.path, 'Download receipts must remain private')
    return url


def local_image(base, relative):
    string(relative, 'image path', 1024)
    path = Path(relative)
    require(not path.is_absolute() and '..' not in path.parts and '\\' not in relative, 'Image must be inside the input folder')
    resolved = (base / path).resolve()
    require(resolved.is_relative_to(base) and resolved.is_file(), 'Missing image or image outside input folder')
    require(24 < resolved.stat().st_size <= MAX_IMAGE_BYTES, 'Invalid image size')
    with resolved.open('rb') as stream:
        header = stream.read(16)
    suffix = resolved.suffix.lower()
    valid = ((suffix == '.png' and header.startswith(b'\x89PNG\r\n\x1a\n'))
             or (suffix in {'.jpg', '.jpeg'} and header.startswith(b'\xff\xd8\xff'))
             or (suffix == '.webp' and header[:4] == b'RIFF' and header[8:12] == b'WEBP'))
    require(valid, 'Unsupported image or content/extension mismatch')
    return resolved


def validate(value, base):
    data = copy.deepcopy(value)
    fields(data, 'schema_version title summary updated_at markets sections assets sources open_items',
           'schema_version title summary updated_at markets sections assets sources open_items', 'project')
    require(data['schema_version'] == '1.0', 'Unsupported schema_version')
    for name in ('title', 'summary', 'updated_at'):
        string(data[name], name)
    market_ids = unique_ids(data['markets'], 'markets')
    require(market_ids and 'shared' not in market_ids, 'At least one market is required; shared is reserved')
    for market in data['markets']:
        fields(market, 'id label platform region language currency timezone', 'id label platform region language currency timezone', 'market')
        for key, value in market.items():
            string(value, f'market {key}', 200)
    section_ids = unique_ids(data['sections'], 'sections')
    sections = {section['id']: section for section in data['sections']}
    for section in data['sections']:
        fields(section, 'id market_id stage title revision body items table', 'id market_id stage title revision', 'section')
        require(section['market_id'] in market_ids | {'shared'}, 'Unknown section market')
        require(section['stage'] in STAGES, 'Unknown stage')
        string(section['title'], 'section title')
        require(type(section['revision']) is int and section['revision'] >= 1, 'Revision must be a positive integer')
        if 'body' in section:
            string(section['body'], 'section body')
        if 'items' in section:
            require(isinstance(section['items'], list), 'items must be a list')
            for item in section['items']:
                string(item, 'section item')
        if 'table' in section:
            table = section['table']
            fields(table, 'columns rows', 'columns rows', 'table')
            require(isinstance(table['columns'], list) and bool(table['columns']), 'Empty table columns')
            for column in table['columns']:
                string(column, 'table column')
            require(isinstance(table['rows'], list), 'Invalid table rows')
            for row in table['rows']:
                require(isinstance(row, list) and len(row) == len(table['columns']), 'Table row width mismatch')
                require(all(isinstance(cell, str) for cell in row), 'Table cells must be strings')
    unique_ids(data['assets'], 'assets')
    files = {}
    for asset in data['assets']:
        fields(asset, 'id market_id title placement status file copy notes specification depends_on', 'id market_id title placement status', 'asset')
        require(asset['market_id'] in market_ids, 'Unknown asset market')
        require(asset['status'] in STATUSES, 'Unknown asset status')
        for key in ('title', 'placement', 'copy', 'notes', 'specification'):
            if key in asset:
                string(asset[key], f'asset {key}')
        require(asset['status'] != 'delivered' or bool(asset.get('file')), 'Delivered assets need a real file')
        if 'file' in asset:
            files[asset['id']] = local_image(base, asset['file'])
        dependencies = asset.get('depends_on', {})
        require(isinstance(dependencies, dict), 'Invalid asset dependencies')
        changed = []
        for key, revision in dependencies.items():
            require(key in section_ids and type(revision) is int and revision >= 1, 'Missing or invalid asset dependency')
            require(sections[key]['market_id'] in {'shared', asset['market_id']}, 'Cross-market asset dependency')
            require(revision <= sections[key]['revision'], 'Dependency revision is newer than source')
            if revision != sections[key]['revision']:
                changed.append(sections[key]['title'])
        if changed and asset['status'] not in {'planned', 'failed'}:
            asset['status'] = 'outdated'
            asset['notes'] = (asset.get('notes', '') + '\n依据已更新：' + '、'.join(changed)).strip()
    require(isinstance(data['sources'], list), 'Invalid sources')
    for source in data['sources']:
        fields(source, 'title url accessed_at market_id note', 'title url accessed_at market_id', 'source')
        public_url(source['url'])
        require(source['market_id'] in market_ids | {'shared'}, 'Unknown source market')
        for key in ('title', 'accessed_at', 'note'):
            if key in source:
                string(source[key], f'source {key}')
    require(isinstance(data['open_items'], list), 'Invalid open_items')
    for item in data['open_items']:
        string(item, 'open item')
    return data, files


def e(value):
    return escape(str(value), quote=True)


def paragraph(text):
    return '<p>' + e(text).replace('\n', '<br>') + '</p>' if text else ''


def render_html(data):
    labels = {m['id']: m['label'] for m in data['markets']}
    labels['shared'] = '共用商品资料'
    filters = '<button class="active" data-filter="all" aria-pressed="true">全部市场</button>'
    filters += ''.join(f'<button data-filter="{e(m["id"])}" aria-pressed="false">{e(m["label"])}</button>' for m in data['markets'])
    market_cards = ''.join('<article class="market"><span>' + e(m['platform']) + '</span><h3>' + e(m['label']) + '</h3><p>' + e(' · '.join(m[k] for k in ('region', 'language', 'currency'))) + '</p><small>' + e(m['timezone']) + '</small></article>' for m in data['markets'])
    section_html = []
    copy_lines = ['# ' + data['title'], '', data['summary'], '']
    for section in data['sections']:
        title = e(section['title'])
        body = paragraph(section.get('body', ''))
        body += '<ul>' + ''.join('<li>' + e(i) + '</li>' for i in section.get('items', [])) + '</ul>' if section.get('items') else ''
        if section.get('table'):
            table = section['table']
            body += '<div class="table-scroll"><table><thead><tr>' + ''.join('<th>' + e(c) + '</th>' for c in table['columns']) + '</tr></thead><tbody>'
            body += ''.join('<tr>' + ''.join('<td>' + e(c) + '</td>' for c in row) + '</tr>' for row in table['rows']) + '</tbody></table></div>'
        section_html.append(f'<article class="section" data-market="{e(section["market_id"])}"><div class="eyebrow">{e(STAGES[section["stage"]])} / {e(labels[section["market_id"]])}</div><h2>{title}</h2>{body}<small>资料版本 {section["revision"]}</small></article>')
        copy_lines.extend(['## ' + section['title'] + ' · ' + labels[section['market_id']], '', section.get('body', ''), *('- ' + i for i in section.get('items', [])), ''])
        if section.get('table'):
            table = section['table']
            copy_lines.extend([' | '.join(table['columns']), *(' | '.join(row) for row in table['rows']), ''])
    asset_html = []
    for asset in data['assets']:
        status = STATUSES[asset['status']]
        media = f'<img src="{e(asset["file"])}" alt="{e(asset["title"])}" loading="lazy">' if asset.get('file') else f'<div class="placeholder">{e(status)}</div>'
        link = f'<a class="download" href="{e(asset["file"])}" download>下载图片</a>' if asset.get('file') else ''
        asset_html.append(f'<article class="asset" data-market="{e(asset["market_id"])}">{media}<div class="asset-body"><span class="badge {e(asset["status"])}">{e(status)}</span><div class="eyebrow">{e(labels[asset["market_id"]])} / {e(asset["placement"])}</div><h3>{e(asset["title"])}</h3>{paragraph(asset.get("copy", ""))}{paragraph(asset.get("specification", ""))}{paragraph(asset.get("notes", ""))}{link}</div></article>')
        copy_lines.extend(['## ' + asset['title'] + ' · ' + labels[asset['market_id']], '', '状态：' + status, '用途：' + asset['placement'], asset.get('copy', ''), asset.get('notes', ''), ''])
    sources = ''.join(f'<li data-market="{e(s["market_id"])}"><a href="{e(s["url"])}" target="_blank" rel="noopener noreferrer">{e(s["title"])}</a><small> · {e(s["accessed_at"])} · {e(labels[s["market_id"]])}</small>{paragraph(s.get("note", ""))}</li>' for s in data['sources'])
    counts = {status: sum(a['status'] == status for a in data['assets']) for status in STATUSES}
    values = {'TITLE': e(data['title']), 'SUMMARY': e(data['summary']), 'UPDATED': e(data['updated_at']),
              'MARKET_COUNT': str(len(data['markets'])), 'DELIVERED_COUNT': str(counts['delivered']),
              'OPEN_COUNT': str(len(data['assets']) - counts['delivered'] - counts['reference']),
              'FILTERS': filters, 'MARKETS': market_cards, 'SECTIONS': '\n'.join(section_html),
              'ASSETS': '\n'.join(asset_html) or '<p class="muted">本次交付没有图片制作任务。</p>',
              'SOURCES': sources or '<li>本次未附公开来源；请按正文标识区分用户资料与待核验判断。</li>',
              'OPEN_ITEMS': ''.join('<li>' + e(i) + '</li>' for i in data['open_items']) or '<li>本次记录没有待补项。</li>'}
    template = (Path(__file__).resolve().parent.parent / 'assets/delivery.html').read_text(encoding='utf-8')
    # Single-pass substitution: user text containing template-like strings is inert.
    html = re.sub(r'@@([A-Z_]+)@@', lambda m: values[m[1]], template)
    return html, '\n'.join(copy_lines), counts


def render(input_path, output_path):
    input_path = Path(input_path).expanduser().resolve()
    output_path = Path(output_path).expanduser().resolve()
    if output_path.exists():
        raise FileExistsError('Choose a new delivery directory; previous deliveries are preserved')
    require(input_path.stat().st_size <= 2 * 1024 * 1024, 'Project JSON is too large')
    data, files = validate(json.loads(input_path.read_text(encoding='utf-8')), input_path.parent)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.ecommerce-', dir=output_path.parent) as temporary:
        staging = Path(temporary) / 'delivery'
        staging.mkdir()
        for asset in data['assets']:
            if asset['id'] in files:
                original = files[asset['id']]
                asset['file'] = f'assets/{asset["id"]}{original.suffix.lower()}'
                target = staging / asset['file']
                target.parent.mkdir(exist_ok=True)
                shutil.copyfile(original, target)
        html, copy_text, counts = render_html(data)
        (staging / 'index.html').write_text(html, encoding='utf-8')
        (staging / 'copy.md').write_text(copy_text, encoding='utf-8')
        (staging / 'project.json').write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        hashes = {p.relative_to(staging).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(staging.rglob('*')) if p.is_file()}
        (staging / 'SHA256SUMS.txt').write_text(''.join(f'{digest}  {name}\n' for name, digest in hashes.items()), encoding='utf-8')
        with zipfile.ZipFile(staging / 'deliverables.zip', 'x', zipfile.ZIP_DEFLATED) as archive:
            for path in sorted(staging.rglob('*')):
                if path.is_file() and path.name != 'deliverables.zip':
                    archive.write(path, path.relative_to(staging).as_posix())
        # Exclusive creation prevents clobbering an output created during rendering.
        output_path.mkdir(exist_ok=False)
        for path in staging.iterdir():
            shutil.move(str(path), output_path / path.name)
    return {'html': str(output_path / 'index.html'), 'zip': str(output_path / 'deliverables.zip'),
            'copy': str(output_path / 'copy.md'), 'markets': len(data['markets']), 'assets': counts}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    try:
        print(json.dumps(render(args.input, args.output), ensure_ascii=False))
    except (ValueError, OSError, KeyError, TypeError) as error:
        print('Delivery not created: ' + (str(error) if isinstance(error, ValueError) else type(error).__name__), file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
