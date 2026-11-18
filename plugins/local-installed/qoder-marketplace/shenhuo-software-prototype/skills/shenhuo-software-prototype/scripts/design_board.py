#!/usr/bin/env python3
"""Local image review board. Approval notes must come from the user's real response."""
import argparse
import base64
import copy
from datetime import datetime, timezone
import hashlib
from html import escape
import json
import os
from pathlib import Path, PurePosixPath
import re
import sys
import tempfile


ID = re.compile(r'[a-zA-Z0-9][a-zA-Z0-9_-]{0,99}\Z')
MIME = {'.png': 'image/png', '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.webp': 'image/webp'}


def need(value, message):
    if not value:
        raise ValueError(message)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def now():
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


def text(value):
    return isinstance(value, str) and bool(value.strip())


def identifier(value):
    return isinstance(value, str) and ID.fullmatch(value)


def raster(path):
    path = Path(path).expanduser()
    need(not path.is_symlink() and path.is_file(), '图片不存在或是符号链接: ' + str(path))
    data = path.read_bytes()
    suffix = path.suffix.lower()
    valid = ((suffix == '.png' and data.startswith(b'\x89PNG\r\n\x1a\n'))
             or (suffix in {'.jpg', '.jpeg'} and data.startswith(b'\xff\xd8\xff'))
             or (suffix == '.webp' and data[:4] == b'RIFF' and data[8:12] == b'WEBP'))
    need(valid, '仅接受真实 PNG/JPEG/WebP 图片: ' + str(path))
    return data, MIME[suffix]


def local_file(root, relative):
    need(isinstance(relative, str) and not PurePosixPath(relative).is_absolute()
         and ':' not in relative and '\\' not in relative
         and all(p and not p.startswith('.') for p in relative.split('/')), '不安全的本地路径')
    path = root
    for part in relative.split('/'):
        path /= part
        need(not path.is_symlink(), '路径不能是符号链接')
    need(path.resolve().is_relative_to(root.resolve()), '路径越界')
    return path


def atomic_write(path, data):
    need(not path.is_symlink(), '拒绝覆盖符号链接: ' + str(path))
    handle = tempfile.NamedTemporaryFile(dir=path.parent, prefix='.board-', delete=False)
    temporary = Path(handle.name)
    try:
        with handle:
            handle.write(data)
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def read_state(root):
    root = Path(root).expanduser().resolve()
    state = json.loads(local_file(root, 'board.json').read_text(encoding='utf-8'))
    validate(root, state)
    return root, state


def current(page):
    return next((v for v in page['versions'] if v['version'] == page['current_version']), None)


def snapshot(state):
    pages = []
    for page in state['pages']:
        v = current(page)
        pages.append({k: page[k] for k in ('id', 'name', 'terminal', 'baseline')}
                     | {'current': {k: v[k] for k in ('version', 'sha256', 'source', 'variant_id')} if v else None})
    return sha(json.dumps(pages, ensure_ascii=False, sort_keys=True).encode())


def confirmed(state):
    approval = state.get('confirmation') or {}
    return (all(current(p) for p in state['pages']) and approval.get('snapshot') == snapshot(state)
            and text(approval.get('note')) and text(approval.get('at')))


def render_revision(state):
    return sha(json.dumps(state, ensure_ascii=False, sort_keys=True).encode())


def validate(root, state):
    need(isinstance(state, dict) and state.get('schema_version') == 1, '无效的总览清单版本')
    need(text(state.get('title')), '缺少项目名称')
    pages = state.get('pages')
    need(isinstance(pages, list) and pages, '缺少页面计划')
    ids = set()
    for p in pages:
        need(isinstance(p, dict) and identifier(p.get('id')) and p['id'] not in ids, '页面 ID 无效或重复')
        ids.add(p['id'])
        need(text(p.get('name')) and p.get('terminal') in {'mobile', 'desktop'}
             and type(p.get('baseline')) is bool, '页面名称、终端或基准标记无效')
        need(isinstance(p.get('versions'), list), '缺少版本记录')
        versions = set()
        for v in p['versions']:
            need(identifier(v.get('version')) and v['version'] not in versions, '版本号无效或重复')
            versions.add(v['version'])
            need(v.get('source') in {'user', 'shenhuo'}, '图片来源无效')
            need((v['source'] == 'shenhuo' and text(v.get('variant_id')))
                 or (v['source'] == 'user' and v.get('variant_id') is None), '神火图须有真实 variant_id，用户图不得伪造')
            need(v.get('path', '').startswith('images/'), '图片路径必须位于 images/')
            data, _ = raster(local_file(root, v['path']))
            need(sha(data) == v.get('sha256'), '图片哈希已变化: ' + p['id'])
        need(p.get('current_version') is None or p['current_version'] in versions, '当前版本不存在')
        need(p.get('adopted_version') is None or p['adopted_version'] in versions, '采用版本不存在')
    need(any(p['baseline'] for p in pages), '至少标记一张基准页')


STYLE = '''
:root{color-scheme:light;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","PingFang SC",sans-serif;color:#272627;background:#f5f5f3}
*{box-sizing:border-box}body{margin:0}header{padding:32px 28px 22px;background:#fff;border-bottom:1px solid #e4e3df}
.eyebrow{margin:0 0 10px;color:#77746f;font-size:11px;letter-spacing:.12em}h1{font-size:26px;line-height:1.35;margin:0 0 14px;letter-spacing:-.03em}
.intro{color:#68655f;font-size:13px;line-height:1.8;margin:12px 0 0}.summary{display:flex;gap:8px;align-items:center;flex-wrap:wrap;font-size:12px}
.pill{padding:5px 9px;border-radius:6px;background:#f1f0ed;color:#625e58}.pending{background:#fff2df;color:#916019}.approved{background:#eaf3ee;color:#336b4e}
main{padding:24px 28px 40px}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,220px),1fr));gap:22px;align-items:start}
.page-card{min-width:0;border:1px solid #deddd8;background:#fff;border-radius:12px;overflow:hidden}.page-card.desktop{grid-column:span 2}
.card-head{padding:15px 14px 13px;border-bottom:1px solid #e8e7e3}.card-head h2{font-size:15px;line-height:1.5;margin:0 0 8px;font-weight:650;overflow-wrap:anywhere}
.meta{display:flex;gap:6px;flex-wrap:wrap;align-items:center;font-size:11px;color:#77716a}.baseline{background:#eee8de;color:#6f5335}
.art{display:block;padding:0;border:0;width:100%;background:#fafaf8;cursor:zoom-in;text-align:left}.art img{display:block;width:100%;height:auto;object-fit:contain}
.empty{padding:90px 15px;text-align:center;color:#999;font-size:13px}.footer{font-size:11px;color:#89847b;line-height:1.6;margin:22px 0 0}
button:focus-visible{outline:3px solid #9a643b;outline-offset:-3px}dialog{width:min(95vw,1200px);height:92vh;border:1px solid #ddd;border-radius:12px;padding:0;box-shadow:0 14px 70px #0003}
dialog::backdrop{background:#17141299}.zoom-head{position:sticky;top:0;display:flex;align-items:center;justify-content:space-between;padding:13px 18px;background:#fff;border-bottom:1px solid #ddd;z-index:1;gap:16px}
.zoom-head strong{font-size:14px}.close{background:#f2f1ef;color:#333;border:0;padding:8px 13px;border-radius:6px;cursor:pointer}.zoom-body{padding:20px;background:#f4f3f0;text-align:center}
.zoom-body img{display:block;width:100%;max-width:1100px;height:auto;margin:auto}.zoom-body.mobile img{max-width:430px}
@media(min-width:1600px){.grid{grid-template-columns:repeat(auto-fit,minmax(240px,1fr))}}@media(max-width:600px){header{padding:24px 18px}main{padding:20px 18px}h1{font-size:23px}.page-card.desktop{grid-column:1/-1}.grid{gap:16px}}
'''


def html(root, state):
    adopted = sum(p['adopted_version'] == p['current_version'] and current(p) is not None for p in state['pages'])
    filled = sum(current(p) is not None for p in state['pages'])
    is_confirmed = confirmed(state)
    status = '整组已确认 · 可以进入交互实现' if is_confirmed else '整组待确认 · 尚未进入交互实现'
    cards = []
    for p in state['pages']:
        v = current(p)
        baseline = '<span class="pill baseline">基准页</span>' if p['baseline'] else ''
        approved = v is not None and p['adopted_version'] == v['version']
        label = '已采用' if approved else ('修改待确认' if p['adopted_version'] else '待确认')
        badge = f'<span class="pill {"approved" if approved else "pending"}">{label}</span>'
        terminal = '手机' if p['terminal'] == 'mobile' else 'PC'
        version = escape(v['version']) if v else '尚未生成'
        if v:
            data, mime = raster(local_file(root, v['path']))
            image = 'data:' + mime + ';base64,' + base64.b64encode(data).decode('ascii')
            art = f'<button type="button" class="art" aria-label="放大：{escape(p["name"], quote=True)}"><img src="{image}" alt="{escape(p["name"], quote=True)} · {version}" loading="lazy"></button>'
        else:
            art = '<div class="empty">此页效果图尚未生成</div>'
        cards.append(f'<article class="page-card {p["terminal"]}" data-page="{p["id"]}"><div class="card-head"><h2>{escape(p["name"])}</h2><div class="meta">{baseline}<span>{terminal} · {version}</span>{badge}</div></div>{art}</article>')
    markup = '''<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="color-scheme" content="light"><meta name="design-board-revision" content="[BOARD:REVISION]"><title>[BOARD:TITLE] · 设计稿总览</title><style>[BOARD:STYLE]</style></head><body>
<header><p class="eyebrow">DESIGN REVIEW / 设计稿总览</p><h1>[BOARD:TITLE]</h1><div class="summary"><span class="pill">[BOARD:COUNT]</span><span class="pill [BOARD:STATE_CLASS]">[BOARD:STATUS]</span></div>
<p class="intro">每页展示当前最新效果图，点击图片可放大。可按页面名称提出一页或多页的修改意见；整组确认后，再从这些图提取 DESIGN.md 并制作可交互 HTML。</p></header>
<main><div class="grid">[BOARD:CARDS]</div><p class="footer">这是图片审阅页。修改后会更新同一个总览入口；旧版本保留在本地记录中。更新时间：[BOARD:TIME]</p></main>
<dialog id="zoom"><div class="zoom-head"><strong id="zoom-title"></strong><button type="button" class="close">关闭</button></div><div class="zoom-body"><img alt=""></div></dialog>
<script>
const dialog=document.querySelector('#zoom');
document.querySelectorAll('.art').forEach(button=>button.addEventListener('click',()=>{
 const card=button.closest('.page-card'), source=button.querySelector('img');
 document.querySelector('#zoom-title').textContent=card.querySelector('h2').textContent;
 const target=dialog.querySelector('img');target.src=source.src;target.alt=source.alt;
 dialog.querySelector('.zoom-body').className='zoom-body '+(card.classList.contains('mobile')?'mobile':'desktop');
 dialog.showModal();
}));
dialog.querySelector('.close').addEventListener('click',()=>dialog.close());
dialog.addEventListener('click',e=>{if(e.target===dialog){const r=dialog.getBoundingClientRect();if(e.clientX<r.left||e.clientX>r.right||e.clientY<r.top||e.clientY>r.bottom)dialog.close();}});
// File previews stay self-contained. HTTP previews follow the same board as it changes.
if(location.protocol==='http:'||location.protocol==='https:'){
 const revision=document.querySelector('meta[name="design-board-revision"]').content;
 const scrollKey='design-board-scroll:'+location.pathname;
 try{const y=sessionStorage.getItem(scrollKey);if(y!==null){sessionStorage.removeItem(scrollKey);window.addEventListener('load',()=>window.scrollTo(0,Number(y)),{once:true});}}catch{}
 let checking=false;
 const checkForUpdate=async()=>{
  if(checking||document.hidden||dialog.open)return;
  checking=true;
  try{
   const response=await fetch(new URL('preview-state.json',location.href),{cache:'no-store',credentials:'omit'});
   if(!response.ok)return;
   const latest=await response.json();
   if(typeof latest.revision==='string'&&latest.revision!==revision){
    try{sessionStorage.setItem(scrollKey,String(window.scrollY));}catch{}
    location.reload();
   }
  }catch{}finally{checking=false;}
 };
 setInterval(checkForUpdate,2000);
 document.addEventListener('visibilitychange',checkForUpdate);
}
</script></body></html>'''
    values = {'TITLE': escape(state['title']), 'STYLE': STYLE, 'COUNT': f'{filled}/{len(state["pages"])} 页 · {adopted} 页已采用',
              'STATE_CLASS': 'approved' if is_confirmed else 'pending', 'STATUS': status, 'CARDS': ''.join(cards),
              'TIME': escape(state.get('updated_at', '')), 'REVISION': render_revision(state)}
    # One pass prevents user titles from becoming template substitutions.
    return re.sub(r'\[BOARD:([A-Z_]+)\]', lambda m: values[m.group(1)], markup).encode('utf-8')


def save(root, state):
    state['updated_at'] = now()
    validate(root, state)
    markup = html(root, state)
    atomic_write(root / 'board.json', (json.dumps(state, ensure_ascii=False, indent=2) + '\n').encode())
    atomic_write(root / 'index.html', markup)
    # Publish this last: an open browser only reloads once the new HTML is ready.
    atomic_write(root / 'preview-state.json', (json.dumps({'revision': render_revision(state)}) + '\n').encode())
    return inspect(root)


def initialize(root, plan):
    root = Path(root).expanduser().absolute()
    need(not root.exists(), '总览目录已存在；请使用 update 或 render，不能覆盖初始化')
    state = {'schema_version': 1, 'title': plan.get('title'), 'pages': [], 'confirmation': None, 'approval_history': []}
    for p in plan.get('pages', []):
        state['pages'].append({k: p.get(k) for k in ('id', 'name', 'terminal', 'baseline')}
                              | {'versions': [], 'current_version': None, 'adopted_version': None})
    validate(root, state)
    root.mkdir(parents=True)
    (root / 'images').mkdir()
    return save(root, state)


def update(root, changes):
    root, state = read_state(root)
    state = copy.deepcopy(state)
    pages = {p['id']: p for p in state['pages']}
    need(isinstance(changes, dict) and isinstance(changes.get('pages'), list) and changes['pages'], '修改清单须含页面')
    seen, writes = set(), []
    for change in changes['pages']:
        pid, version = change.get('id'), change.get('version')
        need(pid in pages and pid not in seen, '未知或重复页面: ' + str(pid))
        seen.add(pid)
        page = pages[pid]
        need(identifier(version) and all(v['version'] != version for v in page['versions']), '版本已存在或无效；使用新版本号')
        source, variant = change.get('source'), change.get('variant_id')
        need((source == 'shenhuo' and text(variant)) or (source == 'user' and variant is None), '来源或 variant_id 无效')
        need(text(change.get('image')), '缺少本地图片路径')
        image = Path(change['image']).expanduser()
        need(image.is_absolute(), '输入图片须为绝对路径')
        data, _ = raster(image)
        digest = sha(data)
        relative = f'images/{pid}-{version}-{digest[:12]}{image.suffix.lower()}'
        destination = local_file(root, relative)
        need(not destination.exists() or destination.read_bytes() == data, '同名图片内容冲突')
        record = {'version': version, 'path': relative, 'sha256': digest, 'source': source,
                  'variant_id': variant, 'created_at': now()}
        note = change.get('adoption_note')
        if note is not None:
            need(text(note), '采用依据不能为空')
            record['adoption_note'] = note
            page['adopted_version'] = version
        page['versions'].append(record)
        page['current_version'] = version
        writes.append((destination, data))
    if state.get('confirmation'):
        state['approval_history'].append(state['confirmation'])
    state['confirmation'] = None
    # All requested changes have been checked before touching the existing board.
    for path, data in writes:
        if not path.exists():
            atomic_write(path, data)
    return save(root, state)


def confirm(root, note):
    root, state = read_state(root)
    need(all(current(p) for p in state['pages']), '页面未齐，不能确认整组')
    need(text(note), '须记录用户明确整组确认的原话或上下文；脚本不能代替用户批准')
    if state.get('confirmation'):
        state['approval_history'].append(state['confirmation'])
    for page in state['pages']:
        page['adopted_version'] = page['current_version']
    state['confirmation'] = {'snapshot': snapshot(state), 'note': note, 'at': now()}
    return save(root, state)


def inspect(root, *, require_confirmed=False, expected=None):
    root, state = read_state(root)
    if expected is not None:
        need(isinstance(expected, dict) and isinstance(expected.get('pages'), list) and expected['pages'], '缺少本轮真实下载清单')
        pages = {p['id']: p for p in state['pages']}
        seen = set()
        for result in expected['pages']:
            pid = result.get('id')
            need(pid in pages and pid not in seen, '本轮下载含未知或重复页面')
            seen.add(pid)
            v = current(pages[pid])
            data, _ = raster(Path(result['image']).expanduser())
            need(v and v['version'] == result.get('version') and v['sha256'] == sha(data)
                 and v['source'] == result.get('source') and v['variant_id'] == result.get('variant_id'),
                 '新版图片尚未同步到总览: ' + pid)
    html_path = local_file(root, 'index.html')
    need(html_path.is_file() and html_path.read_bytes() == html(root, state), '总览 HTML 未同步；运行 render 后再检查')
    marker = local_file(root, 'preview-state.json')
    need(marker.is_file() and json.loads(marker.read_text()).get('revision') == render_revision(state),
         '总览刷新标记未同步；运行 render 后再检查')
    ready = bool(confirmed(state))
    if require_confirmed:
        need(ready, '当前整组效果图尚未确认；不能进入 DESIGN.md 和交互 HTML 实现')
    return {'ok': True, 'html': str(root / 'index.html'), 'page_count': len(state['pages']),
            'ready_pages': sum(current(p) is not None for p in state['pages']), 'confirmed': ready,
            'snapshot': snapshot(state), 'pages': [dict(id=p['id'], name=p['name'], terminal=p['terminal'],
                baseline=p['baseline'], current=current(p), adopted_version=p['adopted_version']) for p in state['pages']]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('init', 'update', 'render', 'check', 'confirm'))
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--input', type=Path, help='JSON plan for init, or changed pages for update')
    parser.add_argument('--note', help='Actual user confirmation; never fabricate')
    parser.add_argument('--require-confirmed', action='store_true')
    parser.add_argument('--expected', type=Path, help='Check against the actual downloaded result list (same format as update input)')
    args = parser.parse_args()
    try:
        if args.command in {'init', 'update'}:
            need(args.input is not None, 'init/update 需要 --input JSON 文件')
            value = json.loads(args.input.read_text(encoding='utf-8'))
            result = (initialize if args.command == 'init' else update)(args.root, value)
        elif args.command == 'confirm':
            result = confirm(args.root, args.note)
        elif args.command == 'render':
            root, state = read_state(args.root)
            result = save(root, state)
        else:
            expected = json.loads(args.expected.read_text(encoding='utf-8')) if args.expected else None
            result = inspect(args.root, require_confirmed=args.require_confirmed, expected=expected)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (ValueError, OSError, KeyError, TypeError, AttributeError) as error:
        print(json.dumps({'ok': False, 'error': str(error)}, ensure_ascii=False), file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
