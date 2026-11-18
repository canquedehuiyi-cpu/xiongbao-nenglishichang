/**
 * 无依赖的 HTML 轻解析。
 *
 * 刻意不引入选择器引擎——审查工具自己变复杂，就是在给「跑不起来」创造条件。
 * 但对抗性审查暴露了三个必须修的解析缺陷，都改成结构化的栈式扫描：
 *  1. `<!--…-->` 用惰性正则删，4 万个未闭合注释就把一次取样的 60s 吃掉了（实测二次方放大）；
 *  2. `<template>` 里的内容浏览器不渲染，却被当成可见的来源块来计数；
 *  3. 惰性 `[\s\S]*?</p>` 会让一个未闭合的 `<p>` 吞掉后面整页，两个兄弟块塌成一个。
 */

const VOID_TAGS = new Set(['area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input', 'link', 'meta', 'param', 'source', 'track', 'wbr']);
/** 遇到这些块级标签时，未闭合的 <p> 自动结束（HTML 解析器的真实行为）。 */
const P_CLOSERS = new Set(['p', 'div', 'ul', 'ol', 'li', 'dl', 'dd', 'dt', 'table', 'tr', 'section', 'article', 'header', 'footer', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'blockquote', 'pre', 'form', 'main']);

const COMMENT_CAP = 20000;

/** 单遍删除注释（不用 [\s\S]*? 的正则，避免病态输入下的二次方开销）。 */
function dropComments(html) {
  let out = '';
  let i = 0;
  let guards = 0;
  while (i < html.length) {
    if (html.startsWith('<!--', i)) {
      const end = html.indexOf('-->', i + 4);
      if (end < 0) {
        // 未闭合注释：浏览器会把它一路吞到文档结尾，这里同样处理
        if (++guards > COMMENT_CAP) break;
        i = html.length;
        break;
      }
      i = end + 3;
      continue;
    }
    out += html[i++];
  }
  return out;
}

/** 去掉不可见/惰性内容与注释。 */
export function stripInert(html) {
  let s = dropComments(String(html == null ? '' : html));
  for (const tag of ['script', 'style', 'noscript', 'template']) {
    s = s.replace(new RegExp('<' + tag + '\\b[^>]*>[\\s\\S]*?</' + tag + '>', 'gi'), ' ');
  }
  return s;
}

export function attrsOf(tag) {
  const out = {};
  // 必须支持未加引号的属性值：压缩后的 HTML 里 `<script src=https://x/b.js>` 很常见，
  // 只认引号形态会让边缘注入的脚本对 LIVE-1/BLD-4 完全隐形。
  const re = /([a-zA-Z_:][-a-zA-Z0-9_:.]*)\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s"'=<>`]+))/g;
  for (const m of tag.matchAll(re)) {
    const k = m[1].toLowerCase();
    out[k] = m[2] !== undefined ? m[2] : m[3] !== undefined ? m[3] : m[4];
  }
  return out;
}

/** href/src 里的 HTML 实体要先解码，否则 `&amp;utm_source=` 一律漏检。 */
export function decodeAttr(v) {
  return String(v == null ? '' : v)
    .replace(/&amp;/gi, '&')
    .replace(/&#0*38;?/g, '&')
    .replace(/&#x26;/gi, '&')
    .replace(/&lt;/gi, '<')
    .replace(/&gt;/gi, '>')
    .replace(/&quot;/gi, '"')
    .replace(/&#0*39;?/g, "'");
}

export function textOf(fragment) {
  return String(fragment)
    .replace(/<[^>]*>/g, ' ')
    .replace(/&nbsp;/g, ' ')
    .replace(/&amp;/g, '&')
    .replace(/&lt;/g, '<')
    .replace(/&gt;/g, '>')
    .replace(/&quot;/g, '"')
    .replace(/&#39;/g, "'")
    .replace(/\s+/g, ' ')
    .trim();
}

const TAG_RE = /<(\/?)([a-zA-Z][a-zA-Z0-9:-]*)((?:"[^"]*"|'[^']*'|[^>"'])*)>/g;

/** 一次线性扫描，产出带属性的结构化标签序列。 */
export function iterTags(html) {
  const out = [];
  const re = new RegExp(TAG_RE.source, 'g');
  const s = String(html);
  let m;
  while ((m = re.exec(s))) {
    const closing = m[1] === '/';
    const name = m[2].toLowerCase();
    out.push({ closing, name, attrs: attrsOf('<' + name + (m[3] || '') + '>'), start: m.index, end: m.index + m[0].length });
    if (re.lastIndex === m.index) re.lastIndex++;
  }
  return out;
}

/**
 * 用栈还原「容器 → 其内部 HTML」的映射。未闭合标签按浏览器的隐式结束规则处理，
 * 不再靠惰性正则——那会让一个漏写的 </p> 把后面整页吞成一个块。
 */
export function containers(html, maxBlocks = 4000) {
  const clean = stripInert(html);
  const tags = iterTags(clean);
  const out = [];
  const stack = [];
  for (const t of tags) {
    if (t.closing) {
      for (let i = stack.length - 1; i >= 0; i--) {
        if (stack[i].name === t.name) {
          const opened = stack.splice(i, 1)[0];
          out.push({ name: t.name, attrs: opened.attrs, inner: clean.slice(opened.contentStart, t.start) });
          break;
        }
      }
      continue;
    }
    if (t.name === 'p') {
      for (let i = stack.length - 1; i >= 0; i--) if (stack[i].name === 'p') { const o = stack.splice(i, 1)[0]; out.push({ name: 'p', attrs: o.attrs, inner: clean.slice(o.contentStart, t.start) }); }
    } else if (P_CLOSERS.has(t.name)) {
      // 块级标签会隐式关闭仍开着的 <p>
      for (let i = stack.length - 1; i >= 0; i--) if (stack[i].name === 'p') { const o = stack.splice(i, 1)[0]; out.push({ name: 'p', attrs: o.attrs, inner: clean.slice(o.contentStart, t.start) }); }
    }
    if (!VOID_TAGS.has(t.name)) stack.push({ name: t.name, attrs: t.attrs, contentStart: t.end });
    if (out.length >= maxBlocks) break;
  }
  return out;
}

export function findTags(html, name) {
  const out = [];
  for (const t of iterTags(html)) {
    if (t.name === name && !t.closing) out.push({ tag: '<' + name + '>', attrs: t.attrs, index: t.start });
  }
  return out;
}

export function linksOf(html) {
  const out = [];
  const clean = String(html);
  const re = /<a\b((?:"[^"]*"|'[^']*'|[^>"'])*)>([\s\S]*?)<\/a>/gi;
  for (const m of clean.matchAll(re)) {
    const a = attrsOf('<a' + m[1] + '>');
    if (!a.href) continue;
    out.push({ href: decodeAttr(a.href), label: textOf(m[2]), rel: a.rel || '', target: a.target || '' });
  }
  return out;
}

export function scriptsOf(html) {
  return findTags(html, 'script')
    .map((s) => ({ src: s.attrs.src || '', inline: !s.attrs.src, integrity: s.attrs.integrity || '', crossorigin: s.attrs.crossorigin || '', attrs: s.attrs }));
}

/** `<base href>` 会改写所有相对资源的解析基准——不读它就会漏看注入脚本。 */
export function baseHref(html, docUrl) {
  for (const t of iterTags(html)) {
    if (t.name === 'base' && !t.closing) {
      const h = decodeAttr(t.attrs.href || '');
      if (!h) continue;
      try {
        return new URL(h, docUrl).href;
      } catch {
        return docUrl;
      }
    }
  }
  return docUrl;
}

/** 危险协议：不加载也可能被读者点到，必须计入而非过滤掉。 */
export const DANGEROUS_HREF = /^\s*(?:javascript|data|vbscript|file|blob):/i;
export function dangerousHref(href) {
  return DANGEROUS_HREF.test(decodeAttr(href).replace(/&#0*106;?/gi, 'j'));
}

const BLOCK_TAGS = new Set(['p', 'div', 'li', 'dd', 'dt', 'footer', 'section', 'span', 'tr', 'td']);

/**
 * 提取「成对的来源块」：容器里同时有若干链接与若干日期徽章。
 * 这是 CTX-1 的判据基础——不依赖具体框架，只依赖「一条来源行 = 一个块」。
 */
export function sourceBlocks(html, opt = {}) {
  const labelRe = opt.labelRe || /来源|来源:|source[:：]?|permalink/i;
  const classRe = opt.classRe || /class\s*=\s*(?:"[^"]*(?:src|source)[^"]*"|'[^']*(?:src|source)[^']*'|[^>\s"']*(?:src|source)[^\s>]*)/i;
  const badgeRe = opt.badgeRe || /class\s*=\s*(?:"[^"]*(?:src|source)-date[^"]*"|'[^"]*(?:src|source)-date[^']*'|[^\s>"']*(?:src|source)-date[^\s>]*)/gi;
  const blocks = [];
  for (const c of containers(html)) {
    if (!BLOCK_TAGS.has(c.name)) continue;
    const attrText = Object.entries(c.attrs).map(([k, v]) => k + '="' + v + '"').join(' ');
    const isSource = classRe.test(attrText) || labelRe.test(textOf(c.inner).slice(0, 80));
    if (!isSource) continue;
    const links = linksOf(c.inner);
    if (!links.length) continue;
    const badges = [...c.inner.matchAll(new RegExp(badgeRe.source, 'gi'))].length;
    blocks.push({ links, badges, raw: textOf(c.inner), tag: c.name });
  }
  return blocks;
}

/** 把 href 归一化到可比较形态，并给出可注册主机。 */
export function hostOf(href, baseUrl) {
  try {
    const u = new URL(decodeAttr(href), baseUrl);
    if (!/^https?:$/.test(u.protocol)) return { proto: u.protocol.replace(':', ''), host: '', registrable: '' };
    const parts = u.hostname.split('.');
    return { proto: u.protocol.replace(':', ''), host: u.hostname, registrable: parts.slice(-2).join('.') };
  } catch {
    return { proto: 'unparseable', host: '', registrable: '' };
  }
}

export const TRACKING_PARAMS = /(^|[?&])(utm_[a-z]+|smid|st|scene|refer|referrer|ref|gclid|gbraid|wbraid|fbclid|igsh|igshid|twclid|msclkid|yclid|mkt_tok|epik|aff|affiliate|s|pk_campaign|pk_kwd|mtm_[a-z]+|mc_cid|mc_eid|_bta|_pdya|commTag|trk|share_token|share_medium|unlocked_article_code|spm|from_source|td_refid|tduserid|npa|irclickid|vero_id|oly_enc_id|__s|__j)(=|$)/i;

/**
 * 「状态码 200，内容却是错误页」的指纹。
 *
 * 为什么需要：软 404（自定义错误页配 200）会让所有「按状态码判死活」的结论失真——
 * 死链看起来活着、sitemap 里的幽灵 URL 看起来正常、被删除的内容仍被索引。
 * 只看状态码的检查遇到它就哑火，而且哑火成「通过」。
 *
 * 判据收紧在两处，避免把「一篇讲 HTTP 状态码的文章」误判成错误页：
 *  1. 命中短语必须在 <title> 里（错误页的标题就是它的身份），或在**很短**的正文开头；
 *  2. 正文很短（错误页不会有几千字）。
 * 命中只说明「疑似」：跨主机探测时拿不到该站真 404 页做对照，因此调用方不得据此定 P1。
 * @param {{status:number, body:string}} res
 * @returns {string} 空串表示没有软错误页迹象
 */
export function softErrorSignal(res) {
  const status = Number(res && res.status) || 0;
  if (!status || status >= 400) return ''; // 真错误码不需要这个判据
  const body = String((res && res.body) || '');
  if (!body.trim()) return '';
  const title = ((/<title[^>]*>([\s\S]{0,200}?)<\/title>/i.exec(body) || [])[1] || '').trim();
  const text = body.replace(/<script[\s\S]*?<\/script>/gi, ' ').replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ');
  const SHAPE = /(?:\b(?:404|410|500|502|503)\b|not\s*found|page\s+not\s*found|doesn['’]t\s*exist|does\s*not\s*exist|no\s+such\s+page|页面(?:不存在|未找到|找不到|已删除|被移动)|找不到(?:该|此|该)页面|出错了|错误页)/i;
  if (title && SHAPE.test(title)) return `标题「${title.slice(0, 60)}」是错误页形态，但状态码 ${status}`;
  if (text.length < 1200 && SHAPE.test(text.slice(0, 400))) return `正文仅 ${text.length} 字符且开头是错误页形态，但状态码 ${status}`;
  return '';
}

/** 两页正文的粗指纹：用来把「本站真 404 页」与「被判定页」对照。 */
export function bodyFingerprint(body) {
  const text = String(body || '').replace(/<script[\s\S]*?<\/script>/gi, ' ').replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ').trim().toLowerCase();
  return text.slice(0, 600);
}
