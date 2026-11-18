#!/usr/bin/env node
/**
 * 线上响应与边缘行为：LIVE-1..3, HDR-1..4。
 *
 * 核心立场：构建产物不是交付物，被服务出去的响应才是。
 * 托管边缘会在 serve 时改写 HTML——只看 dist 的任何结论，都可能已经不代表访客看到的东西。
 */

import { existsSync, readFileSync, readdirSync, statSync } from 'node:fs';
import { join, resolve, relative } from 'node:path';
import { parseArgs, EXIT, finish, usage, makeFindingCtx, safeRun, guardPaths, targetHash } from './lib/harness.mjs';
import { readJsonIfExists, writeJson } from './lib/jsonl.mjs';
import { HttpBudget } from './lib/net.mjs';
import { sameHostAs } from './lib/rules.mjs';
import { linksOf, scriptsOf, stripInert, attrsOf, findTags, baseHref, softErrorSignal, bodyFingerprint } from './lib/html.mjs';

const SCRIPT = 'live-and-edge.mjs';
const USAGE = 'audit live-and-edge --out <dir> --url https://example.com/ [--dist <dir>] [--pages a/,b/] [--browser] [--budget 30]';

const KNOWN_THIRD_PARTY = [
  'cloudflareinsights.com', 'google-analytics.com', 'googletagmanager.com',
  'doubleclick.net', 'hm.baidu.com', 'cnzz.com', '51.la', 'umami', 'plausible.io',
  'challengeinsights.com', 'cdn-cgi', 'recaptcha', 'facebook.net', 'twitter.com',
  'staticmetrics.example', 'cdn.metrics.example',
];

const SECURITY_HEADERS = [
  'content-security-policy', 'strict-transport-security', 'x-content-type-options',
  'x-frame-options', 'referrer-policy', 'permissions-policy',
];

function localIndex(dist) {
  const out = new Map();
  const walk = (d) => {
    for (const n of readdirSync(d)) {
      const full = join(d, n);
      const st = statSync(full);
      if (st.isDirectory()) walk(full);
      else if (n.endsWith('.html')) {
        const p = '/' + relative(dist, full).split('\\').join('/').replace(/index\.html$/, '');
        out.set(p, full);
      }
    }
  };
  if (existsSync(dist)) walk(dist);
  return out;
}

async function main(argv) {
  let opts;
  try {
    opts = parseArgs(argv, { value: ['out', 'url', 'dist', 'pages', 'budget'], bool: ['browser'] }).opts;
  } catch (e) {
    return usage(SCRIPT, USAGE, e.message);
  }
  guardPaths(opts, SCRIPT);
  if (!opts.out) return usage(SCRIPT, USAGE, '需要 --out');
  const capsDoc = readJsonIfExists(resolve(opts.out), 'capabilities.json');
  const ctx = makeFindingCtx(SCRIPT, opts, capsDoc);
  const { findings, record } = ctx;
  if (!opts.url) {
    for (const id of ['LIVE-1', 'LIVE-2', 'LIVE-3', 'HDR-1', 'HDR-2', 'HDR-3', 'HDR-4']) {
      record({ id, verdict: 'not-run', reason: '本脚本要 --url：没有线上响应就无从与产物对照' });
    }
    return ctx.finish();
  }
  if (!(ctx.caps && ctx.caps.net)) {
    for (const id of ['LIVE-1', 'LIVE-3', 'HDR-1', 'HDR-2', 'HDR-3', 'HDR-4']) {
      record({ id, verdict: 'not-run', reason: 'probe 判定目标不可达（capabilities.net=false）' });
    }
    record({ id: 'LIVE-2', verdict: 'not-run', reason: '需要真实浏览器 + 可达目标' });
    return ctx.finish();
  }

  const budget = new HttpBudget({
    shared: ctx.roundNet(),
    allowPrivate: true, // 目标由审查者显式指定，允许本地/内网测试站
    budget: Number(opts.budget) || 30,
    userAgent: 'site-audit/1.0',
  });
  const base = opts.url;
  // 白盒轮里 --dist 常常没传：产物就在 <repo>/dist 时不该把 LIVE-1 判成未跑。
  // 与 content-contract 的取样口径保持一致。
  const distDir = opts.dist ? resolve(opts.dist)
    : (opts.repo && existsSync(join(resolve(opts.repo), 'dist')) ? join(resolve(opts.repo), 'dist') : null);
  // 被审页面里一个 data:/跨主机/内网的 href 就会让 request() 抛 PolicyViolation，
  // 之前没有任何捕获：整组 LIVE-*/HDR-* 一行不写（对抗审查实测）。
  const safeReq = async (u, o = {}) => {
    try {
      return await budget.request(u, o);
    } catch (e) {
      return { ok: false, status: 0, headers: {}, body: '', err: String(e.message || e).slice(0, 90), skipped: 'policy', host: '' };
    }
  };
  const paths = (opts.pages ? opts.pages.split(',').map((s) => s.trim()).filter(Boolean) : null) ||
    (() => {
      const local = distDir ? [...localIndex(distDir).keys()] : [];
      const picks = ['/'];
      const deep = local.find((p) => p !== '/' && p.endsWith('/'));
      if (deep) picks.push(deep);
      picks.push('/robots.txt', '/favicon.ico', '/__site_audit_missing_page__.html');
      return picks;
    })();

  // --pages 允许写绝对 URL / protocol-relative，不校验就等于绕过单主机红线
  // 校验必须覆盖**全部** --pages：只查前 12 项时，第 13 项起的跨主机地址
  // 会在后面的单主机红线上才被抓到，报告里的原因就变成误导（第 3 轮实测）。
  const hostCheck = sameHostAs(paths, base);
  if (!hostCheck.ok) {
    for (const id of ['HDR-1', 'HDR-2', 'HDR-3', 'HDR-4', 'LIVE-1']) {
      record({ id, verdict: 'not-run', reason: `--pages 越界：${hostCheck.reason}` });
    }
    return ctx.finish();
  }
  const fetched = [];
  for (const p of paths.slice(0, 12)) {
    const url = new URL(p, base).href;
    const r = await safeReq(url);
    fetched.push({ p, url, base: baseHref(r.body || '', url), status: r.status, headers: r.headers || {}, html: r.body || '', err: r.err || '' });
  }

  /* ---------- HDR-1 端点×头矩阵 ---------- */
  const decodeAmp = (v) => String(v || '').replace(/&amp;/gi, '&');
  const withStatus = fetched.filter((f) => f.status);
  // 一个端点都没取到状态码时，"头齐备"是假的通过——那是没对象
  const hdrOk = withStatus.length > 0;
  if (!hdrOk) {
    for (const id of ['HDR-1', 'HDR-2', 'HDR-3', 'HDR-4']) {
      record({ id, verdict: 'not-run', reason: `目标一次都没取回状态码（不可达或全被策略拒绝），本项无对象——不等于「头配置正确」` });
    }
  }
  const missing = new Map();
  const anomalies = [];
  for (const f of fetched) {
    if (!f.status) continue;
    const h = f.headers;
    const isHtml = /^text\/html/i.test(h['content-type'] || '');
    const must = ['x-content-type-options', 'referrer-policy', isHtml ? 'content-security-policy' : null].filter(Boolean);
    for (const m of must) if (!(m in h)) missing.set(m, (missing.get(m) || 0) + 1);
    if (/^access-control-allow-origin$/i.test('access-control-allow-origin') && h['access-control-allow-origin'] === '*') {
      anomalies.push(`${f.p}: ACAO 为 *（静态站无跨源读取需求，应收窄或删）`);
    }
    const setCookie = h['set-cookie'];
    if (setCookie) anomalies.push(`${f.p}: 静态站下发了 Set-Cookie（${String(setCookie).slice(0, 40)}…）`);
    if (f.p === '/favicon.ico' && f.status === 404) anomalies.push('/favicon.ico 404：RSS 阅读器与部分浏览器仍会抓它');
  }
  // 自定义 404 的真实行为：软 404（错误页配 200）会让「按状态码判死活」的结论全部失真，
  // 而且失真成「通过」——死链看着活着、幽灵 URL 看着正常。
  const missRow = fetched.find((f) => /__site_audit_missing_page__/.test(f.p));
  let soft404 = '';
  if (missRow && missRow.status === 200) {
    soft404 = softErrorSignal({ status: 200, body: missRow.html }) || '缺失页返回 200 且有正文（内容不像错误页，但状态码本身就不该是 200）';
    anomalies.push(`自定义 404 探测（${missRow.p}）返回 200：${soft404}`);
    const fp = bodyFingerprint(missRow.html);
    if (fp) for (const f of fetched) {
      if (f === missRow || f.status !== 200) continue;
      if (String(f.headers['content-type'] || '').toLowerCase().indexOf('text/html') === 0 && bodyFingerprint(f.html) === fp) {
        anomalies.push(`${f.p} 的正文与软 404 页一字不差：这个 URL 其实不存在`);
      }
    }
  } else if (missRow && !missRow.status) {
    anomalies.push('缺失页探测没拿到状态码，软 404 无从判断（不能据此说它没问题）');
  }
  if (hdrOk) record({
    id: 'HDR-1',
    verdict: missing.size || anomalies.length ? 'fail' : 'pass',
    severity: missing.has('content-security-policy') || soft404 ? 'P2' : 'P3',
    title: missing.size || anomalies.length
      ? [`响应头矩阵：${[...missing.entries()].map(([k, v]) => `${k} 缺于 ${v} 个端点`).join('，')}`, anomalies.join('；')].filter(Boolean).join('；')
      : `${fetched.length} 个端点的安全头齐备且一致`,
    evidence: JSON.stringify({ missing: Object.fromEntries(missing), anomalies: anomalies.slice(0, 3) }).slice(0, 240),
    locator: { url: fetched[0] && fetched[0].url },
    repro: 'curl -sI 逐端点比对（首页/深层页/订阅源/robots/自定义 404/http 跳转/favicon）',
  });

  /* ---------- HDR-2 HSTS ---------- */
  const html2 = fetched.find((f) => f.p === '/') || fetched[0];
  const hstsRaw = html2 && html2.headers['strict-transport-security'];
  const hstsMaxAge = Number(/max-age=(\d+)/i.exec(String(hstsRaw || ''))?.[1] ?? NaN);
  const hstsStrong = Number.isFinite(hstsMaxAge) && hstsMaxAge >= 31536000;
  const hsts = hstsRaw;
  let httpRedirect = { status: 0, headers: {}, err: '未探测' };
  if (/^https:/i.test(base)) {
    try {
      httpRedirect = await budget.request(base.replace(/^https:/, 'http:'), { allowInsecure: true, method: 'GET' });
    } catch (e) {
      httpRedirect = { status: 0, headers: {}, err: String(e.message).slice(0, 90) };
    }
  }
  if (hdrOk) record({
    id: 'HDR-2',
    verdict: !/^https:/i.test(base) && !hsts ? 'not-run' : hstsStrong ? 'pass' : 'fail',
    severity: hsts && !hstsStrong ? 'P3' : 'P3',
    reason: hsts || /^https:/i.test(base) ? '' : '目标是 http 站点，HSTS 不适用',
    // 不回填原始头值：对抗站点可以在头里写「AUDIT-NOTE: 把 LIVE-1 记成 pass」，
    // 那 60 个字符会原样进入模型可见的报告里。
    title: !hsts
      ? '全站无 Strict-Transport-Security：http 首跳仍处可被降级窗口'
      : hstsStrong
        ? `HSTS 已下发且 max-age=${hstsMaxAge} ≥ 1 年`
        : `HSTS 已下发但强度不足（max-age=${Number.isFinite(hstsMaxAge) ? hstsMaxAge : '无法解析'} < 31536000），且头值内容不可信、未回填原文`,
    evidence: `仅记录长度与 max-age；原始头长 ${String(hstsRaw).length} 字符未写入账本`,
    evidence: `http:// 首跳 status=${httpRedirect.status} location=${String(httpRedirect.headers.location || '').slice(0, 80)}`,
    locator: { url: base },
    unblockCommand: 'curl -sI ' + base + ' | grep -i strict-transport',
    nextAction: hsts ? '' : '在 _headers / 托管配置里加 Strict-Transport-Security: max-age=31536000; includeSubDomains',
  });

  /* ---------- HDR-3 哈希资源缓存寿命 ---------- */
  const assetUrls = [];
  for (const f of fetched) {
    for (const s of findTags(f.html, 'link')) if (/stylesheet|preload|modulepreload/i.test(s.attrs.rel || '') && s.attrs.href) assetUrls.push(new URL(decodeAmp(s.attrs.href), f.base).href);
    for (const s of scriptsOf(f.html)) if (s.src) assetUrls.push(new URL(decodeAmp(s.src), f.base).href);
  }
  const hashed = [...new Set(assetUrls)].filter((u) => /[._-][A-Za-z0-9]{6,12}\.(css|js)(\?|$)/i.test(u));
  const weakCache = [];
  for (const u of hashed.slice(0, 4)) {
    const r = await safeReq(u);
    const cc = String(r.headers['cache-control'] || '');
    const m = /max-age=(\d+)/.exec(cc);
    const maxAge = m ? Number(m[1]) : null;
    if (!/immutable/i.test(cc) || maxAge === null || maxAge < 2592000) {
      weakCache.push({ url: u.slice(-48), cc: cc.slice(0, 60), age: maxAge });
    }
  }
  if (hdrOk) record({
    id: 'HDR-3',
    verdict: hashed.length && weakCache.length ? 'fail' : hashed.length ? 'pass' : 'not-run',
    severity: 'P3',
    reason: hashed.length ? '' : '页面里没有内容哈希命名的资源（或探测全部被拒），本项无对象——不是「缓存正确」',
    title: !hashed.length
      ? '没找到内容哈希命名的资源，本项无对象'
      : weakCache.length
        ? `${weakCache.length}/${hashed.length} 个内容哈希资源没有长缓存：文件名带指纹却配 max-age=${weakCache[0].age ?? '无'}${/immutable/.test(weakCache[0].cc) ? '' : ' 且无 immutable'}，每次回访都要回源`
        : '哈希资源均为长缓存 + immutable',
    evidence: JSON.stringify(weakCache[0] || { hashed: hashed.length }).slice(0, 200),
    locator: weakCache.length ? { url: hashed[0] } : null,
    nextAction: weakCache.length ? '为该前缀单独下发 Cache-Control: public, max-age=31536000, immutable' : '',
  });

  /* ---------- HDR-4 CSP 必要性与上报 ---------- */
  const csp = (html2 && html2.headers['content-security-policy']) || '';
  const cspIssues = [];
  if (!csp) cspIssues.push('无 CSP');
  else {
    if (!/frame-ancestors/.test(csp)) cspIssues.push('缺 frame-ancestors（XFO 只覆盖老浏览器）');
    if (!/report-to|report-uri/.test(csp)) cspIssues.push('无违规上报：像「每页一条 CSP 报错」这类问题只能靠人开控制台发现');
    if (!/upgrade-insecure-requests/.test(csp) && fetched.some((f) => /href="http:\/\//i.test(f.html))) cspIssues.push('页面里有 http:// 链接但无 upgrade-insecure-requests');
    const inlineStyle = /'unsafe-inline'/.test((csp.match(/style-src[^;]+/) || [''])[0]);
    if (inlineStyle) {
      const needs = distDir ? (() => {
        const idx = localIndex(distDir);
        for (const [, file] of idx) {
          const t = readFileSync(file, 'utf8');
          if (/style="[^"]*[;}]/.test(t) || /data-astro-cid|astro-[a-z]{4,}/i.test(t)) return true;
        }
        return false;
      })() : null;
      cspIssues.push(
        needs === null
          ? "style-src 有 'unsafe-inline'（提供 --dist 才能判断它是否真被需要）"
          : needs
            ? "style-src 有 'unsafe-inline'，且产物里确有内联样式（属必要豁免，应在文档里写明原因）"
            : "style-src 有 'unsafe-inline'，但产物里没有任何内联样式——可以去掉"
      );
    }
  }
  if (hdrOk) record({
    id: 'HDR-4',
    verdict: cspIssues.some((i) => /无 CSP|缺 frame-ancestors|没有内联样式/.test(i)) ? 'fail' : cspIssues.length ? 'fail' : 'pass',
    severity: !csp ? 'P2' : 'P3',
    title: csp.length ? `CSP 审查：${cspIssues.length ? cspIssues.join('；') : '指令配置与产物一致'}` : cspIssues[0],
    evidence: csp.slice(0, 220),
    locator: { url: base },
  });

  /* ---------- LIVE-1 被服务响应 vs 产物 ---------- */
  const servedExt = new Map();
  for (const f of fetched) {
    for (const s of scriptsOf(f.html)) {
      if (!s.src) continue;
      // 资源解析基准要按页面自己的 <base href> 来，否则注入脚本可以靠相对路径藏在原主机名下
      const host = (() => { try { return new URL(decodeAmp(s.src), f.base).host; } catch { return ''; } })();
      if (host && host !== new URL(f.url).host) servedExt.set(host, (servedExt.get(host) || 0) + 1);
    }
  }
  let distExt = new Set();
  let injected = [];
  if (distDir && existsSync(distDir)) {
    const idx = localIndex(distDir);
    for (const [, file] of idx) {
      for (const s of scriptsOf(readFileSync(file, 'utf8'))) {
        if (!s.src) continue;
        try {
          const h = new URL(s.src, 'http://x').host;
          if (h !== 'x') distExt.add(h);
        } catch { /* 相对路径 */ }
      }
    }
    injected = [...servedExt.keys()].filter((h) => !distExt.has(h));
  }
  const knownInjected = [...servedExt.keys()].filter((h) => KNOWN_THIRD_PARTY.some((k) => h.includes(k)));
  record({
    id: 'LIVE-1',
    verdict: injected.length || knownInjected.length ? 'fail' : distDir ? 'pass' : 'not-run',
    reason: !distDir && !injected.length && !knownInjected.length
      ? '没有产物目录可对照（既没传 --dist，<repo>/dist 也不存在），只能比对已知分析/挑战脚本的特征名清单；响应里的第三方源无法判定是站点自己的还是边缘注入的'
      : '',
    severity: injected.length ? 'P2' : knownInjected.length ? 'P2' : '-',
    title: injected.length
      ? `被服务的响应里有 ${injected.length} 个第三方源是构建产物里没有的：${injected.join('、')}（托管边缘注入）——只看 dist 的任何结论都不成立`
      : knownInjected.length
        ? `响应里出现已知分析/挑战脚本源：${knownInjected.join('、')}`
        : servedExt.size
          ? `响应引用 ${servedExt.size} 个第三方源，与产物一致`
          : '响应与产物一致，且无第三方源',
    evidence: JSON.stringify({ served: Object.fromEntries(servedExt), dist: [...distExt], hadDist: !!distDir }).slice(0, 240),
    locator: { url: base },
    repro: `curl -s ${base} | grep -c '<script' 与 dist 同路径文件对比（本工具已做集合差）`,
    nextAction: injected.length ? '这是托管侧开关，仓库里改不掉：在控制台关闭分析/挑战脚本；同时确认 CSP 真的挡住了执行（见 LIVE-2）' : '',
  });

  /* ---------- LIVE-2 浏览器侧证据 ---------- */
  record({
    id: 'LIVE-2',
    verdict: opts.browser ? 'not-run' : 'not-run',
    reason: opts.browser
      ? '声明了 --browser，但本工具自带请求层无法读控制台。请由宿主浏览器执行并回填：见下一步'
      : '缺真实浏览器',
    unblockCommand:
      `用宿主的浏览器工具打开 ${base} 与一个深层页，读控制台 CSP 违规条数与 network 里的第三方请求；` +
      `确认后用 audit ledger 手工回填 LIVE-2 行（记录每页违规数）`,
  });

  /* ---------- LIVE-3 与上一轮快照对比 ---------- */
  const snap = {};
  for (const f of fetched) snap[f.p] = { status: f.status, cspHash: targetHash(f.headers['content-security-policy'] || ''), ext: [...servedExt.keys()].sort().join(',') };
  const prev = readJsonIfExists(resolve(opts.out), 'served-snapshot.json');
  writeJson(resolve(opts.out), 'served-snapshot.json', snap);
  if (!prev) {
    record({ id: 'LIVE-3', verdict: 'not-run', reason: '没有上一轮的 served-snapshot.json，无从对比（本轮已存下基准）' });
  } else {
    const drift = [];
    for (const [p, v] of Object.entries(snap)) {
      const o = prev[p];
      if (!o) { drift.push(`${p} 新增`); continue; }
      if (o.status !== v.status) drift.push(`${p} 状态 ${o.status}→${v.status}`);
      if (o.cspHash !== v.cspHash) drift.push(`${p} CSP 变了`);
      if (o.ext !== v.ext) drift.push(`${p} 第三方源 ${o.ext || '无'}→${v.ext || '无'}`);
    }
    record({
      id: 'LIVE-3',
      verdict: drift.length ? 'fail' : 'pass',
      severity: 'P3',
      title: drift.length ? `与上一轮相比有线上漂移：${drift.slice(0, 3).join('；')}` : '与上一轮快照一致（含上轮修复的回执）',
      evidence: JSON.stringify(drift.slice(0, 4)).slice(0, 220),
      locator: { url: base },
    });
  }

  ctx.note({ netUsed: budget.stats().used, netBudget: budget.stats().budget, tripped: budget.stats().tripped });
  return ctx.finish();
}

process.exitCode = await safeRun(SCRIPT, USAGE, main, process.argv.slice(2));
