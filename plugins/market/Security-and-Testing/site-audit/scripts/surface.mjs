#!/usr/bin/env node
/**
 * 站面：SEO-1/2、A11Y-1/2、LNK-1/2。
 * 这些不影响能不能被入侵，但决定这个站在搜索引擎、读屏用户和读者眼里是不是可信。
 */

import { existsSync, readFileSync, readdirSync, statSync } from 'node:fs';
import { join, resolve, relative } from 'node:path';
import { parseArgs, makeFindingCtx, safeRun, guardPaths, usage, netPrecondition } from './lib/harness.mjs';
import { contrastRatio } from './lib/rules.mjs';
import { readJsonIfExists } from './lib/jsonl.mjs';
import { HttpBudget } from './lib/net.mjs';
import { linksOf, stripInert, textOf, findTags, hostOf, TRACKING_PARAMS, softErrorSignal } from './lib/html.mjs';

const SCRIPT = 'surface.mjs';
const USAGE = 'audit surface --out <dir> [--url https://example.com/] [--dist <dir>] [--repo <dir>] [--browser] [--probe-links]';

/* ---- WCAG 2.1 相对亮度与对比度 ---- */
/**
 * 颜色与对比度的解析统一走 lib/rules.mjs——那份实现可被 selftest 直接单测，
 * 而检测脚本自己带一份就永远测不到（文件末尾有 await main()，import 就会真跑一轮）。
 */
const COLOR_VAL = /(--[\w-]+)\s*:\s*(#[0-9a-fA-F]{3,8}\b|rgba?\([^)]*\)|hsla?\([^)]*\))/g;

/**
 * 抽自定义属性并按明暗分桶。
 * 旧实现有两个真 bug：暗色作用域那条正则**没有捕获组**（永远取到空串 → 暗色从不被检查），
 * 而 `:root{}` 的匹配不区分它是否落在 @media(dark) 里（暗色值会污染明色桶）。
 * 另外只认十六进制，于是 `--fg: rgb(190,190,190)` 这种真实不达标的值完全隐形。
 */
function cssVars(css) {
  const scopes = { light: {}, dark: {} };
  const parse = (body, into) => {
    for (const m of body.matchAll(COLOR_VAL)) into[m[1]] = m[2].trim();
  };
  let rest = css;
  const blocks = [];
  const head = /@media[^{]{0,300}\{/g;
  let m;
  while ((m = head.exec(css))) {
    let i = m.index + m[0].length;
    let depth = 1;
    while (i < css.length && depth > 0) {
      if (css[i] === '{') depth++;
      else if (css[i] === '}') depth--;
      i++;
    }
    blocks.push({ start: m.index, end: i, head: m[0], body: css.slice(m.index + m[0].length, i) });
  }
  for (const b of blocks) {
    // media 块从"其余"里挖掉，避免其内的 :root 被当成明色
    rest = rest.slice(0, b.start) + ' '.repeat(b.end - b.start) + rest.slice(b.end);
    const dark = /prefers-color-scheme\s*:\s*dark/i.test(b.head) || /\[data-theme=["']?dark/i.test(b.head + b.body);
    parse(b.body, dark ? scopes.dark : scopes.light);
  }
  parse(rest, scopes.light);
  for (const s of ['light', 'dark']) {
    for (let round = 0; round < 2; round++) {
      for (const [k, v] of Object.entries(scopes[s])) {
        const ind = /^var\(\s*(--[\w-]+)/.exec(v);
        if (ind && scopes[s][ind[1]]) scopes[s][k] = scopes[s][ind[1]];
      }
    }
  }
  return scopes;
}


function collect(dist, repo) {
  const files = [];
  const walk = (d) => {
    for (const n of readdirSync(d)) {
      const full = join(d, n);
      const st = statSync(full);
      if (st.isDirectory()) walk(full);
      else files.push(full);
    }
  };
  if (dist && existsSync(dist)) walk(dist);
  const html = files.filter((f) => f.endsWith('.html'));
  const css = files.filter((f) => f.endsWith('.css'));
  return { html, css, all: files, root: dist || repo };
}

async function main(argv) {
  let opts;
  try {
    opts = parseArgs(argv, { value: ['out', 'url', 'dist', 'repo'], bool: ['browser', 'probe-links'] }).opts;
  } catch (e) {
    return usage(SCRIPT, USAGE, e.message);
  }
  guardPaths(opts, SCRIPT);
  if (!opts.out) return usage(SCRIPT, USAGE, '需要 --out');
  const capsDoc = readJsonIfExists(resolve(opts.out), 'capabilities.json');
  const ctx = makeFindingCtx(SCRIPT, opts, capsDoc);
  const { record } = ctx;
  const dist = opts.dist ? resolve(opts.dist) : opts.repo ? join(resolve(opts.repo), 'dist') : null;
  const repo = opts.repo ? resolve(opts.repo) : null;
  if (!dist || !existsSync(dist)) {
    for (const id of ['SEO-1', 'SEO-2', 'A11Y-1', 'A11Y-2', 'LNK-2']) {
      record({ id, verdict: 'not-run', reason: '需要 --dist 产物目录（有 --url 但无产物时，样式与逐页 head 无法完整取证）' });
    }
    return ctx.finish();
  }
  const set = collect(dist, repo);
  const rel = (f) => relative(set.root, f).split('\\').join('/');
  const pages = set.html;

  /* ---------- SEO-1 head 完整性与索引策略 ---------- */
  const seo = [];
  const canonicals = new Map();
  for (const f of pages) {
    const html = readFileSync(f, 'utf8');
    const r = rel(f);
    const is404 = /404|not[- ]found/i.test(r) || /noindex/.test(html);
    const canon = (/<link rel="canonical" href="([^"]+)"/.exec(html) || [])[1];
    const isErrorPage = /404|not[- ]?found/i.test(r);
    if (!canon && !isErrorPage) seo.push({ file: r, why: '缺 canonical' });
    else if (canon) {
      canonicals.set(canon, (canonicals.get(canon) || 0) + 1);
      if (isErrorPage) seo.push({ file: r, why: '404 页仍发出 canonical，会把权重汇聚到坏页' });
    }
    if (/404/.test(r) && !/noindex/.test(html)) seo.push({ file: r, why: '错误页无 noindex' });
    if (!/404/.test(r) && /noindex/.test(html) && r !== '/') seo.push({ file: r, why: '常规页带 noindex' });
    if (!/404/.test(r) && r === '/' && /noindex/.test(html)) seo.push({ file: r, why: '首页带 noindex：整站会被搜索引擎降级' });
    if (!/property="og:title"/.test(html)) seo.push({ file: r, why: '缺 og:title' });
    if (!/name="description"/.test(html) && !/404/.test(r)) seo.push({ file: r, why: '缺 description' });
    if (!/name="theme-color"/.test(html)) seo.push({ file: r, why: '缺 theme-color（明暗两套）' });
    if (/<link rel="icon"[^>]*svg/.test(html) && r === '/') {
      if (!/rel="icon"[^>]*png|apple-touch-icon/i.test(html)) seo.push({ file: r, why: '只有 SVG 图标：部分阅读器/浏览器仍会抓 /favicon.ico 与 apple-touch-icon' });
    }
  }
  const dupCanon = [...canonicals.entries()].filter(([, n]) => n > 1);
  if (dupCanon.length) seo.push({ file: '(全站)', why: `${dupCanon.length} 个 canonical 被多页共用（应为逐页唯一）` });
  record({
    id: 'SEO-1',
    verdict: seo.length ? 'fail' : 'pass',
    severity: seo.some((s) => /首页带 noindex|404 页仍发出 canonical/.test(s.why)) ? 'P2' : 'P3',
    title: seo.length ? `${pages.length} 页里 ${seo.length} 处元数据/索引问题（例：${seo[0].file} — ${seo[0].why}）` : `${pages.length} 页 head 与索引策略一致`,
    evidence: JSON.stringify(seo.slice(0, 4)).slice(0, 240),
    locator: seo.length ? { file: seo[0].file } : null,
  });

  /* ---------- SEO-2 结构化数据是否说真话 ---------- */
  const jsonld = pages.map((f) => ({ f: rel(f), html: readFileSync(f, 'utf8') })).filter((p) => /application\/ld\+json/.test(p.html));
  if (!jsonld.length) {
    record({ id: 'SEO-2', verdict: 'not-run', reason: '产物里没有 JSON-LD，本项无对象（若文档声称有结构化数据，那是 DOC-1 的问题）' });
  } else {
    const lies = [];
    for (const p of jsonld) {
      const m = /<script type="application\/ld\+json">([\s\S]*?)<\/script>/.exec(p.html);
      if (!m) continue;
      let data = null;
      try { data = JSON.parse(m[1]); } catch { lies.push({ file: p.f, why: 'JSON-LD 不是合法 JSON' }); continue; }
      const pub = data.datePublished;
      const mod = data.dateModified;
      if (pub && mod && pub === mod && !/updated/.test(p.html)) {
        lies.push({ file: p.f, why: 'dateModified 恒等于 datePublished：文档声称支持修订标记，但构建路径里没有第二来源' });
      }
    }
    record({
      id: 'SEO-2',
      verdict: lies.length ? 'fail' : 'pass',
      severity: 'P3',
      title: lies.length ? `结构化数据有不实字段：${lies[0].why}（${lies.length} 页）` : `${jsonld.length} 页 JSON-LD 字段自洽`,
      evidence: JSON.stringify(lies[0] || { jsonldPages: jsonld.length }).slice(0, 200),
      locator: lies.length ? { file: lies[0].file } : null,
    });
  }

  /* ---------- A11Y-1 对比度 ---------- */
  // 先判定每个令牌是不是被用作「文字颜色」。只出现在 border/background/outline/fill 里的
  // 是装饰用途，拿 4.5:1 去要求它是误报（这一条在真实站点上第一次跑就误报了）。
  const cssJoined = set.css.map((f) => readFileSync(f, 'utf8')).join(String.fromCharCode(10));
  const textVars = new Set();
  for (const m of cssJoined.matchAll(/(^|[{;\s])(?:-webkit-text-fill-)?color\s*:\s*var\((--[\w-]+)\)/g)) textVars.add(m[2]);
  const decoVars = new Set();
  for (const m of cssJoined.matchAll(/(?:border(?:-\w+)?-color|background(?:-color)?|outline-color|fill|stroke|box-shadow|text-decoration-color)\s*:[^;]*var\((--[\w-]+)\)/g)) decoVars.add(m[1]);
  const contrastBad = [];
  const decorative = [];
  let checked = 0;
  for (const c of set.css) {
    const css = readFileSync(c, 'utf8');
    const scopes = cssVars(css);
    for (const theme of ['light', 'dark']) {
      const v = scopes[theme];
      const bg = v['--bg'] || (theme === 'light' ? '#ffffff' : '#000000');
      for (const [name, hex] of Object.entries(v)) {
        if (!/fg|text|color/i.test(name) || /bg/i.test(name)) continue;
        const ratio = contrastRatio(hex, bg);
        if (ratio === null) continue;
        checked++;
        const usages = pages.reduce((n, p) => n + (readFileSync(p, 'utf8').match(new RegExp('var\\(' + name.replace(/[-]/g, '\\-') + '\\)', 'g')) || []).length, 0)
          + (css.match(new RegExp('var\\(' + name.replace(/-/g, '\\-') + '\\)', 'g')) || []).length;
        if (ratio >= 4.5) continue;
        const entry = { theme, name, hex, bg, ratio: Number(ratio.toFixed(2)), usages };
        if (textVars.has(name)) contrastBad.push(entry);
        else decorative.push(entry);
      }
    }
  }
  const usedBad = contrastBad.filter((c) => c.usages > 0);
  record({
    id: 'A11Y-1',
    verdict: !checked ? 'not-run' : usedBad.length ? 'fail' : 'pass',
    severity: usedBad.length ? 'P1' : '-',
    reason: checked ? '' : '没解析出任何颜色型自定义属性（可能写法在本工具支持范围外）——这是「无对象」，不是「都达标」',
    level: 'S',
    title: usedBad.length
      ? `${usedBad.length} 个被用作文字颜色的令牌不达 WCAG AA：${usedBad.slice(0, 2).map((c) => `${c.name}(${c.theme}) ${c.ratio}:1，用于 ${c.usages} 处`).join('；')}（阈值 4.5:1）`
      : `已算 ${checked} 个令牌×主题组合：用作文字颜色的都 ≥4.5:1${decorative.length ? `；另有 ${decorative.length} 个低对比令牌只用于装饰（${decorative.slice(0, 2).map((d) => d.name + ' ' + d.ratio + ':1').join('、')}），不计入判红` : ''}`,
    evidence: JSON.stringify({ text: contrastBad.slice(0, 2), decorative: decorative.slice(0, 2) }).slice(0, 220),
    locator: usedBad.length ? { file: rel(set.css[0]) } : null,
    nextAction: usedBad.length ? '把承担信息文字的令牌提到 ≥4.5:1；确认那些装饰令牌确实没被用在文字上（本工具按 CSS 声明判定，内联样式需人工复核）' : '',
  });

  /* ---------- A11Y-2 状态与可访问名称 ---------- */
  const cssAll = set.css.map((f) => readFileSync(f, 'utf8')).join('\n');
  const a11y = [];
  if (!/:focus-visible|:focus\b/.test(cssAll)) a11y.push('无任何 :focus 样式：键盘用户看不见焦点');
  if (!/prefers-reduced-motion/.test(cssAll)) a11y.push('无 prefers-reduced-motion：动效无法关闭');
  if (!/@media print/.test(cssAll)) a11y.push('无打印样式');
  const hoverOnStatic = /\.(?:card|item|article)[^{}]*:hover/.test(cssAll);
  if (hoverOnStatic) {
    const links = new Set(pages.flatMap((p) => linksOf(stripInert(readFileSync(p, 'utf8'))).map((l) => l.href)));
    if (links.size === 0) a11y.push('非交互卡片带 hover 抬升阴影：暗示可点而点击无反应');
  }
  let missingLang = 0;
  let dupName = 0;
  for (const p of pages) {
    const html = readFileSync(p, 'utf8');
    if (!/<html[^>]*lang=/i.test(html)) missingLang++;
    const arts = [...html.matchAll(/<article\b([^>]*)>([\s\S]*?)<\/article>/gi)];
    for (const a of arts) {
      const hasName = /aria-label=|aria-labelledby=/.test(a[1]);
      const heading = /<h[23][^>]*>([\s\S]*?)<\/h[23]>/.test(a[2]);
      if (!hasName && !heading) dupName++;
    }
  }
  if (missingLang) a11y.push(`${missingLang} 页缺 <html lang>：读屏会用错语音包`);
  if (dupName) a11y.push(`${dupName} 个内容块既无小标题也无 aria-label：读屏里整块无名`);
  record({
    id: 'A11Y-2',
    verdict: a11y.length ? 'fail' : 'pass',
    severity: 'P3',
    level: 'S',
    title: a11y.length ? `可访问性状态缺口：${a11y.join('；')}` : '焦点/减弱动效/打印/语言/区块名齐备',
    evidence: JSON.stringify({ cssBytes: cssAll.length, pages: pages.length, browserTier: !!opts.browser }).slice(0, 200),
    locator: { file: rel(set.css[0] || pages[0]) },
    unblockCommand: opts.browser ? '' : '可访问性树里的实际名称需宿主浏览器复核（A11Y-2 的浏览器部分未跑）',
  });

  /* ---------- LNK-2 外链存活（需显式开启） ---------- */
  if (!opts.probeLinks) {
    record({ id: 'LNK-2', verdict: 'not-run', reason: '未开启 --probe-links：这项会向第三方站点发请求，必须显式同意' });
    return ctx.finish();
  }
  // 向一批第三方主机发请求前，必须已经 probe 开轮且（黑盒时）有授权记录
  const pre = netPrecondition(opts, capsDoc);
  if (!pre.ok) {
    record({ id: 'LNK-2', verdict: 'not-run', reason: `外链存活探测被前置条件挡住：${pre.reason}` });
    return ctx.finish();
  }
  const links = new Map();
  for (const p of pages) {
    for (const l of linksOf(stripInert(readFileSync(p, 'utf8')))) {
      if (!/^https?:/i.test(l.href)) continue;
      if (!links.has(l.href)) links.set(l.href, []);
      links.get(l.href).push(rel(p));
    }
  }
  const dead = [];
  const blocked = [];
  const errors = [];
  const softish = [];
  let budgetTotal = 0;
  const denied = [];
  let skipped = 0;
  // 共享一个预算实例：否则每条链接各建 budget:1，熔断计数永不累积、250ms 同站间隔也永不生效
  const linkBudget = new HttpBudget({
    shared: ctx.roundNet(),
    pool: 'external',
    budget: Math.min(30, [...links.keys()].length),
    multiHost: true,
    timeoutMs: 8000,
    userAgent: 'site-audit/1.0',
  });
  for (const [href, where] of [...links.entries()].slice(0, 30)) {
    const per = linkBudget;
    let r;
    try {
      r = await per.request(href);
    } catch (e) {
      denied.push({ href: href.slice(0, 80), why: String(e.message).slice(0, 70) });
      continue;
    }
    if (r.skipped) { skipped++; continue; }
    budgetTotal++;
    if (r.status >= 200 && r.status < 400) {
      // 软 200：状态码活着、内容已是错误页。跨主机拿不到该站真 404 页做对照，
      // 所以这只算线索（P3），不算确认死亡。
      const soft = softErrorSignal(r);
      if (soft) softish.push({ href: href.slice(0, 70), where: where[0], soft });
      continue;
    }
    if (r.status === 404 || r.status === 410) dead.push({ href, where: where[0], status: r.status });
    else if (r.status === 403 || r.status === 429 || r.status === 451) blocked.push({ href, where: where[0], status: r.status });
    else if (r.status >= 500) errors.push({ href, where: where[0], status: r.status, kind: 'server' });
    else if (!r.status) errors.push({ href, where: where[0], kind: 'connect/timeout', err: (r.err || '').slice(0, 50) });
  }
  record({
    id: 'LNK-2',
    verdict: dead.length || denied.length || softish.length ? 'fail' : budgetTotal === 0 || skipped ? 'not-run' : 'pass',
    severity: dead.length ? 'P2' : denied.length || softish.length ? 'P3' : '-',
    reason: dead.length || denied.length ? '' : budgetTotal === 0 ? '一条外链都没真正探测（全被拒绝或跳过），这是「无对象」，不是「无死链」' : skipped ? `仅探到 ${budgetTotal} 条，另有 ${skipped} 条被熔断/预算跳过，不足以支撑「无死链」的结论` : '',
    title: dead.length
      ? `${dead.length} 条外链确认死亡（404/410）：${dead[0].href.slice(0, 70)}（于 ${dead[0].where}）`
      : denied.length
          ? `站点外链里有 ${denied.length} 条按红线拒绝探测（内网/元数据地址或 URL 里带凭据，例：${denied[0].href}）——不探测，但这种链接本身就是可疑信号`
        : softish.length
          ? `${softish.length} 条外链状态码活着但内容像错误页（例：${softish[0].href} —— ${softish[0].soft}）：跨主机取不到该站真 404 页做对照，只作线索`
          : `已探 ${budgetTotal} 条外链，无 404/410、无软 200 迹象`,
    evidence: `实探 ${budgetTotal}；确认死 ${dead.length}；被 WAF/限流 ${blocked.length}（不能据此判死）；连接失败/超时 ${errors.length}；被跳过 ${skipped}；按策略拒绝 ${denied.length}（内网/元数据/带凭据）；软 200 线索 ${softish.length}`,
    locator: dead.length ? { file: dead[0].where } : null,
    nextAction: dead.length ? '替换为可核实的原始来源；并给发布链路加一个只报告、不阻断的周度链接体检' : '',
  });

  return ctx.finish();
}

process.exitCode = await safeRun(SCRIPT, USAGE, main, process.argv.slice(2));
