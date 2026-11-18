/**
 * 合成夹具的微型渲染器。零依赖，手写。
 *
 * 里面刻意留着四类缺陷形状（见 README）。不要「顺手修好」——那会让验收失效。
 */

import { SECTION_KEYS } from './sections.mjs';

const SECTION_CLASS = {
  产品: 'sec-product',
  模型: 'sec-model',
  政策: 'sec-policy',
  基础设施: 'sec-infra',
};

const ESCAPES = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' };
export const escapeHtml = (s) => String(s).replace(/[&<>"']/g, (c) => ESCAPES[c]);

/**
 * 缺陷 A：先替换链接、再处理粗体，于是粗体扫描看到的是已经生成的 HTML。
 * 缺陷 B：URL 正则遇到第一个右括号就停，含平衡括号的 URL 被截断。
 */
const LINK_RE = /\[([^\]]+)\]\((https?:\/\/[^)\s]+)\)/g;
const BOLD_RE = /\*\*([^*]+)\*\*/g;

export function renderInline(text) {
  let out = escapeHtml(text);
  out = out.replace(LINK_RE, (_m, label, href) => `<a href="${href}" target="_blank" rel="noopener noreferrer">${label}</a>`);
  out = out.replace(BOLD_RE, '<strong>$1</strong>');
  return out;
}

/** 查表不经原型链防护：`constructor` / `__proto__` 会取到真值的非配色对象。 */
export function sectionClass(name) {
  return SECTION_CLASS[name] || 'sec-general';
}

/**
 * 来源行解析。按顿号分段（深度为 0 时才分），
 * 但只识别整行末尾的一个日期——这是缺陷 C（渲染字段完备性回归）的根源。
 */
const TRAILING_DATE = /[（(]([^（）()]{2,12})[）)]\s*$/;
const MD_LINK = /\[([^\]]+)\]\((https?:\/\/[^)\s]+)\)/;

export function parseSources(raw) {
  const parts = [];
  let depth = 0;
  let cur = '';
  for (const ch of raw) {
    if (ch === '[' || ch === '(' || ch === '（') depth++;
    else if (ch === ']' || ch === ')' || ch === '）') depth = Math.max(0, depth - 1);
    if (ch === '、' && depth === 0) {
      parts.push(cur);
      cur = '';
    } else cur += ch;
  }
  parts.push(cur);

  const segs = parts.map((s) => s.trim()).filter(Boolean);
  const m = raw.match(TRAILING_DATE);
  const lineDate = m && /\d/.test(m[1]) ? m[1] : '';
  return segs.map((text, i) => {
    const lm = text.match(MD_LINK);
    return {
      label: lm ? lm[1] : text,
      href: lm ? lm[2] : '',
      // 只有最后一段拿到日期，前面的段一律空 —— 缺陷 C
      date: i === segs.length - 1 ? lineDate : '',
    };
  });
}

/** 缺陷 D：把「家数」算成条数（每段都自带不同 URL，去重后必然等于段数）。 */
export function distinctMediaCount(items) {
  const names = new Set();
  for (const it of items) for (const p of it.sources) names.add(p.href || p.label);
  return names.size;
}

export function parsePost(md) {
  const lines = md.replace(/\r\n/g, '\n').split('\n');
  const post = { sections: [], disclaimer: '' };
  let sec = null;
  let item = null;
  const flushItem = () => {
    if (item && sec) sec.items.push(item);
    item = null;
  };
  const flushSec = () => {
    flushItem();
    if (sec && sec.items.length) post.sections.push(sec);
    sec = null;
  };
  for (const line of lines) {
    const t = line.trim();
    if (!t) continue;
    if (t.startsWith('## ')) {
      flushSec();
      sec = { name: t.slice(3).trim(), items: [] };
    } else if (t.startsWith('### ')) {
      flushItem();
      if (!sec) sec = { name: SECTION_KEYS[0], items: [] };
      item = { title: t.slice(4).trim(), body: '', sourceRaw: '' };
    } else if (t.startsWith('来源：') || t.startsWith('来源:')) {
      if (item) item.sourceRaw = t.replace(/^来源[：:]/, '').trim();
    } else if (t.startsWith('---')) {
      flushSec();
      item = null;
      sec = { name: '__disclaimer__', items: [] };
    } else if (sec && sec.name === '__disclaimer__') {
      post.disclaimer += (post.disclaimer ? ' ' : '') + t;
    } else if (item) {
      item.body += (item.body ? ' ' : '') + t;
    }
  }
  flushSec();
  if (!post.sections.length) {
    const d = post.disclaimer;
    post.sections = [{ name: SECTION_KEYS[0], items: [] }];
    post.disclaimer = d;
  }
  for (const s of post.sections) for (const i of s.items) i.sources = parseSources(i.sourceRaw);
  post.items = post.sections.flatMap((s) => s.items.map((i) => ({ ...i, section: s.name })));
  return post;
}

export function renderPost(post, meta) {
  const all = post.items;
  let html = `<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8">
<title>${escapeHtml(meta.title)}</title>
<link rel="canonical" href="${meta.canonical}">
<meta name="description" content="${escapeHtml(meta.title)}">
<meta property="og:title" content="${escapeHtml(meta.title)}">
<meta property="og:type" content="article">
<link rel="stylesheet" href="${meta.css}">
</head><body>
<main>
<h1>${escapeHtml(meta.title)}</h1>
<div class="stats"><span><b>${all.length}</b> 条</span> <span><b>${post.sections.length}</b> 个板块</span> <span><b>${distinctMediaCount(all)}</b> 家来源</span></div>`;
  for (const s of post.sections) {
    if (s.name === '__disclaimer__' || !s.items.length) continue;
    html += `\n<section class="sec ${sectionClass(s.name)}"><h2>${escapeHtml(s.name)}</h2>`;
    for (const it of s.items) {
      html += `\n<article class="item"><h3>${renderInline(it.title)}</h3>
<div class="body">${renderInline(it.body)}</div>
<p class="src"><span class="src-label">来源：</span><span class="src-html">${it.sources
        .map((p) => `${p.href ? `<a href="${escapeHtml(p.href)}" target="_blank" rel="noopener noreferrer">${escapeHtml(p.label)}</a>` : escapeHtml(p.label)}${p.date ? `<span class="src-date">${escapeHtml(p.date)}</span>` : ''}`)
        .join('、')}</span></p></article>`;
    }
    html += '\n</section>';
  }
  if (post.disclaimer) html += `\n<footer class="disclaimer">${escapeHtml(post.disclaimer)}</footer>`;
  html += '\n</main></body></html>\n';
  return html;
}

export { SECTION_KEYS };
