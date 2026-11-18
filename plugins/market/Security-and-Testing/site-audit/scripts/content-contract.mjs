#!/usr/bin/env node
/**
 * 内容契约与漂移：CTX-1..5, DOC-1, DOC-3。
 *
 * 这一组检查的共同前提：内容是不可信输入（由自动化从任意网页搜集），
 * 而「文档写的契约」「校验器实际断言的」「渲染器真正产出的」是三个不同的东西。
 * 本脚本的职责就是让它们当面对质。
 */

import { existsSync, readFileSync, readdirSync, statSync, rmSync, mkdirSync, writeFileSync } from 'node:fs';
import { join, resolve, dirname, basename, relative } from 'node:path';
import { fileURLToPath } from 'node:url';
import { parseArgs, EXIT, finish, usage, makeFindingCtx, safeRun, guardPaths, makeWorktree, npmScript, nodeScript } from './lib/harness.mjs';
import { walkLimited, walkCoverage } from './lib/fsx.mjs';
import { sourceBlocks, linksOf, stripInert, textOf, hostOf, dangerousHref, TRACKING_PARAMS } from './lib/html.mjs';
import { readJsonIfExists } from './lib/jsonl.mjs';
import { applicable } from './lib/registry.mjs';

const SCRIPT = 'content-contract.mjs';
const USAGE = 'audit content-contract --out <dir> [--url https://example.com/] [--repo <dir>] [--dist <dir>] [--validator <npm-script|path>] [--pages a/,b/] [--js]';

/**
 * 由产物路径反推渲染前的内容源文件：dist/posts/X/index.html → src|content|data/posts/X.{md,mdx}。
 * 找不到就返回 null——调用方必须把「这一层没跑」说出来，而不是拿剩下两层当完整结论。
 */
function srcFileFor(relFile, repo) {
  if (!repo) return null;
  const SL = String.fromCharCode(47);
  const BS = String.fromCharCode(92);
  const DOT = String.fromCharCode(46);
  const r = String(relFile).split(BS).join(SL);
  const tail = r.replace(new RegExp('^.*?' + SL + 'dist' + SL), '').replace(new RegExp('^dist' + SL), '').replace(/^\.[\/\\]/, '');
  const stem = tail.replace(/\/index\.html$/, '').replace(/\.html$/, '');
  if (!stem || stem === SL || stem.includes(DOT + DOT)) return null;
  for (const dir of ['src', 'content', 'data']) {
    for (const ext of ['md', 'mdx', 'markdown', 'txt']) {
      const p = join(resolve(repo), dir, stem.replace(/^\//, '') + DOT + ext);
      if (existsSync(p)) return p;
    }
  }
  return null;
}

/** 采样用的 HTML 清单：带上限且自报触顶（见 lib/fsx.mjs）。 */
function listHtml(dir, cap = 40) {
  return walkLimited(dir, { cap, match: (n) => n.endsWith('.html') });
}
async function main(argv) {
  let opts;
  try {
    opts = parseArgs(argv, {
      value: ['out', 'url', 'repo', 'dist', 'validator', 'pages'],
      bool: ['js'],
    }).opts;
  } catch (e) {
    return usage(SCRIPT, USAGE, e.message);
  }
  guardPaths(opts, SCRIPT);
  if (!opts.out) return usage(SCRIPT, USAGE, '需要 --out');
  const caps = readJsonIfExists(resolve(opts.out), 'capabilities.json');
  const ctx = makeFindingCtx(SCRIPT, opts, caps);

  const { findings, record } = ctx;

  /* ---------- 页面语料：产物优先，其次线上 ---------- */
  const pages = [];
  let fetchLoss = null;
  const distDir = opts.dist ? resolve(opts.dist) : (opts.repo ? join(resolve(opts.repo), 'dist') : null);
  const distWalk = distDir && existsSync(distDir) ? listHtml(distDir) : null;
  const distCov = walkCoverage(distWalk);
  if (distDir && existsSync(distDir)) {
    for (const f of listHtml(distDir).files) pages.push({ from: 'dist', path: '/' + relative(distDir, f).split('\\').join('/').replace(/\/index\.html$/, '/'), html: readFileSync(f, 'utf8'), file: relative(resolve(opts.repo || '.'), f).split('\\').join('/') });
  }
  if (opts.url && caps && caps.capabilities && caps.capabilities.net) {
    const { HttpBudget } = await import('./lib/net.mjs');
    const budget = new HttpBudget({ shared: ctx.roundNet(), allowPrivate: true, budget: 24, userAgent: (caps.tooling && caps.tooling.ua) || 'site-audit/1.0' });
    let paths = (opts.pages || '').split(',').map((s) => s.trim()).filter(Boolean);
    if (!paths.length && distDir && existsSync(distDir)) {
      paths = pages.filter((p) => p.from === 'dist').map((p) => p.path);
    }
    if (!paths.length) {
      // 黑盒：先从首页发现同主机链接再采样。只看首页会让 CTX-1 的样本量退化成 1。
      const home = await budget.request(opts.url);
      paths = ['/'];
      const host = new URL(opts.url).host;
      for (const l of linksOf(stripInert(home.body || ''))) {
        if (paths.length >= 8) break;
        try {
          const u = new URL(l.href, opts.url);
          if (u.host === host && u.pathname !== '/' && !/\.(css|js|png|jpg|svg|xml|ico)$/i.test(u.pathname)) {
            paths.push(u.pathname + (u.pathname.endsWith('/') ? '' : '/'));
          }
        } catch { /* 跳过无法解析的 href */ }
      }
      paths = [...new Set(paths)];
    }
    const lost = [];
    const want = paths.slice(0, 20);
    for (const p of want) {
      const r = await budget.request(new URL(p, opts.url).href);
      // 只把 ok 的页塞进语料，却按「取样 N 页」的口径下结论 = 把丢掉的页当成查过了
      if (r.ok && r.body) pages.push({ from: 'served', path: p, html: r.body, file: null });
      else lost.push({ p, status: r.status || 0, why: r.skipped || r.err || '空响应体' });
    }
    fetchLoss = { want: want.length, got: want.length - lost.length, lost: lost.slice(0, 4) };
    ctx.note({ netUsed: budget.stats().used, netBudget: budget.stats().budget, tripped: budget.stats().tripped, pagesWanted: want.length, pagesLost: lost.length });
  }

  const corpusCov = fetchLoss && fetchLoss.lost.length
    ? `线上取样只取回 ${fetchLoss.got}/${fetchLoss.want} 页（丢弃：${fetchLoss.lost.map((l) => l.p + '=' + (l.status || l.why)).join(', ').slice(0, 120)}）`
    : (distCov ? '本地产物取样' + distCov : '');
  const locOf = (p) =>
    p.file ? { file: p.file } : opts.url ? { url: new URL(p.path, opts.url).href } : { file: p.path };

  if (!pages.length) {
    for (const id of ['CTX-1', 'CTX-2', 'CTX-4', 'CTX-5', 'LNK-1']) {
      record({ id, verdict: 'not-run', reason: '既无 --dist 产物也无可达 --url，没有可比对的页面语料' });
    }
    record({ id: 'CTX-3', verdict: 'not-run', reason: '缺 --repo 或未指定 --validator' });
    return ctx.finish();
  }

  /* ---------- CTX-1 成对结构完备性 ---------- */
  let undatedTotal = 0;
  let segTotal = 0;
  const offenders = [];
  for (const p of pages) {
    for (const b of sourceBlocks(p.html)) {
      segTotal += b.links.length;
      const undated = Math.max(0, b.links.length - b.badges);
      undatedTotal += undated;
      if (undated) offenders.push({ page: p.path, where: p.file, links: b.links.length, badges: b.badges, sample: b.raw.slice(0, 120) });
    }
  }
  record({
    id: 'CTX-1',
    verdict: undatedTotal ? 'fail' : 'pass',
    severity: undatedTotal ? (undatedTotal > segTotal / 4 ? 'P1' : 'P2') : '-',
    title: undatedTotal
      ? `来源段的日期标注未逐段兑现：${segTotal} 段中 ${undatedTotal} 段在页面上没有对应标注`
      : `来源段与标注逐段对齐（${segTotal} 段 / ${segTotal} 标注${corpusCov ? '，但' + corpusCov : ''}）`,
    evidence: (offenders.length ? `${offenders[0].page} 例：${offenders[0].sample}` : `取样 ${pages.length} 页`) + (corpusCov ? ' | ' + corpusCov : ''),
    locator: offenders.length ? { file: offenders[0].where || offenders[0].page } : null,
    repro: `遍历 <span class="src-html"> 数 <a> 与 .src-date：见本报告证据计数`,
    nextAction: offenders.length ? '内容侧逐段补标注；同时让校验器按分段而非行尾断言（见 CTX-3）' : '',
  });

  /* ---------- CTX-2 公示派生指标复算 ---------- */
  // 页面内三口径（URL / 剥注记后的媒体名 / 可注册主机）都由**同一份 HTML** 算出来，
  // 它们互相不一致，说明「来源数」这个数字本身没有唯一口径。
  // 只有再加一层**渲染之前**的源文件复算（--js），才能回答另一个问题：
  // 访客看到的数字，和内容作者写下的来源，还是同一件事吗？
  const statHits = [];
  const srcDiff = [];
  let jsOk = 0;
  let jsMiss = 0;
  for (const p of pages) {
    const m = /<b>\s*(\d+)\s*<\/b>\s*(?:家|个)?\s*来源/.exec(p.html) || /(\d+)\s*(?:家|个)\s*来源/.exec(stripInert(p.html));
    if (!m) continue;
    const shown = Number(m[1]);
    const all = [];
    for (const b of sourceBlocks(p.html)) all.push(...b.links);
    const byUrl = new Set(all.map((l) => l.href)).size;
    const byLabel = new Set(all.map((l) => l.label.replace(/[（(][^）)]*[）)]/g, '').trim())).size;
    const byHost = new Set(all.map((l) => hostOf(l.href, opts.url || 'http://x').registrable || l.href)).size;
    if (shown !== byLabel || shown !== byHost) {
      statHits.push({ page: p.path, where: p.file, shown, byUrl, byLabel, byHost, items: all.length });
    }
    if (!opts.js || !p.file) continue;
    const srcFile = srcFileFor(p.file, opts.repo);
    if (!srcFile) { jsMiss++; continue; }
    jsOk++;
    const srcUrls = new Set();
    for (const line of readFileSync(srcFile, 'utf8').split(/\r?\n/)) {
      if (!/^\s*(来源|来源：|Sources?|Source)\s*[:：]/i.test(line)) continue;
      for (const mm of line.matchAll(/\[([^\]]+)\]\((https?:\/\/[^)\s]+)(?:\s+["'][^"']*["'])?\)/g)) srcUrls.add(mm[2]);
    }
    // 同一口径、两个阶段：不等就是渲染环节吞掉或并掉了来源
    if (srcUrls.size !== byUrl) srcDiff.push({ page: p.path, srcFile: relative(resolve(opts.repo), srcFile).split('\\').join('/'), src: srcUrls.size, byUrl, shown });
  }
  const cross = opts.js
    ? `跨阶段：${jsOk} 页取到渲染前源文件${jsMiss ? `、${jsMiss} 页没找到（目录结构不常见，未据此下结论）` : ''}`
    : '跨阶段未启用（加 --js 才用渲染前的内容源文件复算同一数字）';
  const disagree = statHits.length + srcDiff.length;
  record({
    id: 'CTX-2',
    verdict: disagree ? 'fail' : 'pass',
    severity: 'P2',
    title: srcDiff.length
      ? `渲染前的内容源文件与页面给出的来源数不是同一件事（${srcDiff.length} 页）：源文件 ${srcDiff[0].src} 条 URL，页面渲染后按 URL 只剩 ${srcDiff[0].byUrl} 条，页面却公示 ${srcDiff[0].shown}（${srcDiff[0].srcFile}）`
      : statHits.length
        ? `页面公示的来源数与三种口径复算不一致（${statHits.length} 页）：公示 ${statHits[0].shown}，按 URL ${statHits[0].byUrl}，按媒体名 ${statHits[0].byLabel}，按主机 ${statHits[0].byHost}`
        : `公示来源数与复算一致（页面三口径${opts.js ? ' + 渲染前源文件' : ''}）`,
    evidence: JSON.stringify({ statHits: statHits.slice(0, 2), srcDiff: srcDiff.slice(0, 2), cross, corpus: corpusCov || '完整' }).slice(0, 300),
    locator: srcDiff.length
      ? { file: srcDiff[0].srcFile }
      : statHits.length
        ? locOf({ file: statHits[0].where, path: statHits[0].page })
        : null,
    repro: opts.js
      ? '对同一页：HTML 里按完整 URL 去重 = A；到 src/content 里数该行内 Markdown 的 URL 数 = B；页面公示数字 = C。比较 A/B/C'
      : '对同一页分别按完整 URL / 剥注记后的链接文字 / 可注册主机去重，与页面数字对比',
    nextAction: srcDiff.length
      ? '渲染器与内容契约对不上：先确定哪一层是对的（多半是渲染时按主机合并了来源），再把口径写进校验器'
      : statHits.length ? '确定唯一口径（建议：可注册主机 + 剥离转载注记），并在页面上写清它统计的是什么' : '',
  });

  /* ---------- CTX-3 声明的契约 vs 校验器实际断言 ---------- */
  await ctx3(record, opts, distDir, findings);

  /* ---------- CTX-4 语料级形态计数 ---------- */
  const corpus = pages.map((p) => textOf(stripInert(p.html))).join('\n');
  const shapes = {
    紧贴式日期: (corpus.match(/(?<![\d\s])\d{1,2}月\d{1,2}日/g) || []).length,
    空格式日期: (corpus.match(/\d{1,2}\s月\s?\d{1,2}\s日/g) || []).length,
    直角引号: (corpus.match(/「[^」]*」/g) || []).length,
    全角弯引号: (corpus.match(/[“”]/g) || []).length,
    ASCII直引号: (corpus.match(/"/g) || []).length,
    相对日期词: (corpus.match(/(明日|下周一|下周二|下周三|本周三|上周|昨天|今天)/g) || []).length,
  };
  const dominant = (a, b) => (a > 0 && b > 0 && Math.min(a, b) / Math.max(a, b) > 0.08);
  const drift = [];
  if (dominant(shapes['紧贴式日期'], shapes['空格式日期'])) drift.push(`日期形态混用 ${shapes['紧贴式日期']}/${shapes['空格式日期']}`);
  if (dominant(shapes['直角引号'], shapes['全角弯引号'])) drift.push(`引号形态混用 ${shapes['直角引号']}/${shapes['全角弯引号']}`);
  if (shapes['相对日期词']) drift.push(`永久归档里出现相对日期 ${shapes['相对日期词']} 处`);
  record({
    id: 'CTX-4',
    verdict: drift.length ? 'fail' : 'pass',
    severity: drift.length ? 'P3' : '-',
    title: drift.length ? `语料排版形态漂移：${drift.join('；')}` : '排版形态一致',
    evidence: JSON.stringify(corpusCov ? { ...shapes, corpus: corpusCov } : shapes).slice(0, 300),
    repro: '对页面可见文本按形态计数（见证据里的六个计数器）',
    nextAction: drift.length ? '把形态写进契约并让校验器强制（当前校验器只禁 ASCII 直引号）' : '',
  });

  /* ---------- CTX-5 需人判断的候选清单 ---------- */
  const candidates = [];
  for (const p of pages) {
    const t = textOf(stripInert(p.html));
    for (const m of t.matchAll(/[^。]*?(若属实|据报道|未经证实|知情人士)[^。]*?。/g)) {
      const sent = m[0];
      if (/\d{4}\s*年\s*(出生|生)|出生於|出生于/.test(sent)) candidates.push({ page: p.path, kind: '未经证实的叙述里含自然人生年', sample: sent.slice(0, 90) });
    }
    for (const m of t.matchAll(/[^。]*?(据|援引)\s*([A-Z][\w&.’' -]{2,24})(报道|消息|援引)[^。]*?。/g)) {
      const named = m[2].trim();
      const links = linksOf(p.html).map((l) => l.label + ' ' + l.href).join(' ');
      if (!links.toLowerCase().includes(named.toLowerCase().replace(/\s+/g, ''))) {
        candidates.push({ page: p.path, where: p.file, kind: `正文点名媒体「${named}」未出现在来源链接里`, sample: m[0].slice(0, 90) });
      }
    }
  }
  record({
    id: 'CTX-5',
    verdict: candidates.length ? 'fail' : 'pass',
    severity: candidates.length ? 'P2' : '-',
    level: 'J',
    title: candidates.length
      ? `${candidates.length} 处需人工判断的编辑问题（隐私暴露 / 归属缺口），逐条过一遍`
      : '未发现需人工判断的编辑问题候选',
    evidence: candidates.length ? `${candidates[0].kind} — ${candidates[0].page} — ${candidates[0].sample}` : '',
    locator: candidates.length ? locOf(candidates[0]) : null,
    nextAction: '判据：传闻句式里不得出现自然人的生年/家庭/健康/履历细节；正文点名的第一手媒体必须出现在来源里',
  });

  /* ---------- DOC-1 对外声明 vs 实际 ---------- */
  if (opts.repo) {
    const readmePath = ['README.md', 'readme.md', 'docs/README.md'].map((f) => join(resolve(opts.repo), f)).find(existsSync);
    if (readmePath) {
      const readme = readFileSync(readmePath, 'utf8');
      const claims = [];
      if (/不加载任何第三方脚本|所有资源自托管|no third-party/.test(readme)) {
        const servedHasThirdParty = pages.some((p) => linksOf(stripInert(p.html)).length && /src="https?:\/\/(?!synthetic|localhost|127\.)/.test(p.html));
        claims.push({ claim: '不加载任何第三方脚本', held: !servedHasThirdParty });
      }
      if (/凭据扫描|漏洞基线|门禁/.test(readme)) {
        claims.push({ claim: '存在有效的凭据扫描与漏洞基线门禁', held: null, note: '由 SEC-1/SEC-4 判定，本项不重复结论' });
      }
      const broken = claims.filter((c) => c.held === false);
      record({
        id: 'DOC-1',
        verdict: broken.length ? 'fail' : 'pass',
        severity: broken.length ? 'P2' : '-',
        title: broken.length ? `文档声明与实际不符：${broken.map((b) => b.claim).join('、')}` : claims.length ? '对外声明与实际一致' : '文档未作可核验声明',
        evidence: JSON.stringify(claims),
        locator: { file: relative(resolve(opts.repo), readmePath).split('\\').join('/') },
        repro: '把 README 里的可核验断言逐条对到产物/线上响应上',
      });
    } else {
      record({ id: 'DOC-1', verdict: 'not-run', reason: '仓库里找不到 README' });
    }
  } else {
    record({ id: 'DOC-1', verdict: 'not-run', reason: '黑盒模式没有仓库文档可比对' });
  }

  /* ---------- DOC-3 过期注释 / 死代码 ---------- */
  if (opts.repo && caps && caps.capabilities.git) {
    const srcFiles = [];
    const walk = (d) => {
      for (const n of readdirSync(d)) {
        if (['node_modules', '.git', 'dist'].includes(n)) continue;
        const full = join(d, n);
        statSync(full).isDirectory() ? walk(full) : /\.(m|c)?js|ts|astro$/.test(n) && srcFiles.push(full);
      }
    };
    walk(resolve(opts.repo));
    const allText = srcFiles.map((f) => readFileSync(f, 'utf8')).join('\n');
    const dead = [];
    for (const f of srcFiles) {
      for (const m of readFileSync(f, 'utf8').matchAll(/(?:指向|参见|see also)\s+([A-Za-z_$][\w$]{2,})/g)) {
        const sym = m[1];
        const uses = (allText.match(new RegExp(`\\b${sym}\\b`, 'g')) || []).length;
        if (uses <= 1) dead.push({ file: relative(resolve(opts.repo), f).split('\\').join('/'), sym });
      }
    }
    record({
      id: 'DOC-3',
      verdict: dead.length ? 'fail' : 'pass',
      severity: dead.length ? 'P3' : '-',
      level: 'J',
      title: dead.length ? `${dead.length} 处注释指向代码里已不存在的符号（最近一次：${dead[0].sym}）` : '未发现指向不存在符号的注释',
      evidence: dead.length ? `${dead[0].file} — ${dead[0].sym}` : `${srcFiles.length} 个源文件`,
      locator: dead.length ? { file: dead[0].file } : null,
    });
  } else {
    record({ id: 'DOC-3', verdict: 'not-run', reason: '需要 --repo 与 git 历史' });
  }

  /* ---------- LNK-1 追踪参数 / 协议降级 / 域名形态 ---------- */
  const allLinks = [];
  const dangerLinks = [];
  for (const p of pages) {
    for (const l of linksOf(stripInert(p.html))) {
      // 危险协议的链接不能因为「不是 http」就被悄悄过滤掉——那正是要报的东西
      if (dangerousHref(l.href)) {
        dangerLinks.push({ ...l, page: p.path, where: p.file });
        continue;
      }
      if (/^https?:/i.test(l.href)) allLinks.push({ ...l, page: p.path, where: p.file });
    }
  }
  const tracking = allLinks.filter((l) => TRACKING_PARAMS.test(l.href));
  const insecure = allLinks.filter((l) => l.href.startsWith('http://'));
  const redirects = allLinks.filter((l) => /(search_news|\/redirect|\/link\?|out\.php|l\.[a-z]\.|t\.co\/)/i.test(l.href));
  // 原先只看 pages[0] 却报成「条目内重复 N 处」——语料有 20 页时那是 1/20 的覆盖面
  const dupPerItem = pages.flatMap((p) => sourceBlocks(p.html).filter((b) => new Set(b.links.map((l) => l.href)).size !== b.links.length).map((b) => ({ page: p.path, links: b.links.length })));
  const hostVariants = new Map();
  for (const l of allLinks) {
    const h = hostOf(l.href, opts.url).host;
    if (!h) continue;
    const bare = h.replace(/^www\./, '');
    if (!hostVariants.has(bare)) hostVariants.set(bare, new Set());
    hostVariants.get(bare).add(h);
  }
  const inconsistent = [...hostVariants.entries()].filter(([, set]) => set.size > 1);
  const linkProblems = tracking.length + insecure.length + redirects.length + dupPerItem.length + inconsistent.length + dangerLinks.length;
  record({
    id: 'LNK-1',
    verdict: linkProblems ? 'fail' : 'pass',
    severity: dangerLinks.length ? 'P1' : tracking.some((t) => /unlocked_article_code|share_token|st=|smid/i.test(t.href)) ? 'P2' : linkProblems ? 'P3' : '-',
    title: linkProblems
      ? `链接卫生问题：危险协议 ${dangerLinks.length}、追踪参数 ${tracking.length}、http 降级 ${insecure.length}、点击中转 ${redirects.length}、条目内重复 ${dupPerItem.length}、同域多形态 ${inconsistent.length}`
      : '链接形态干净',
    evidence: ((dangerLinks[0] || tracking[0] || insecure[0] || { href: '' }).href.slice(0, 120)) + (corpusCov ? ' | ' + corpusCov : ''),
    locator: (() => {
      const first = dangerLinks[0] || tracking[0] || insecure[0] || redirects[0];
      // 链接对象带的是 page/where；locOf 要的是 file/path。
      // 直接丢进去会得到 `http://host/undefined` 这种指不回任何地方的证据位置。
      return first ? locOf({ file: first.where, path: first.page }) : null;
    })(),
    repro: `grep -oE '\\]\\((https?)://[^) ]*(utm_|smid|st=|scene=|refer=|agt=|commTag)[^) ]*\\)' 于源文件`,
    nextAction: 'javascript:/data: 之类的链接要删掉（会被渲染成可点但走危险协议）；其余清参数与协议降级',
  });

  /* ---------- 本脚本未覆盖的适用项 ---------- */
  const mine = applicable(opts.mode || (caps && caps.mode) || 'whitebox').filter((id) =>
    ['CTX-1', 'CTX-2', 'CTX-3', 'CTX-4', 'CTX-5', 'DOC-1', 'DOC-3', 'LNK-1'].includes(id)
  );
  for (const id of mine) if (!findings.some((f) => f.id === id)) record({ id, verdict: 'not-run', reason: '本脚本前置条件不满足' });

  return ctx.finish();
}

/**
 * CTX-3：把「文档声明的契约」拿到校验器面前对质——
 * 造一条确定违反契约的样本，喂进该校验器的副本，看它是红还是绿。
 * 这一步必须在仓库副本里做，绝不改使用者的树。
 */
async function ctx3(record, opts, distDir, findings) {
  const repo = opts.repo ? resolve(opts.repo) : null;
  const outDir = resolve(opts.out);
  if (!repo || !existsSync(repo)) {
    return record({ id: 'CTX-3', verdict: 'not-run', reason: '需要 --repo：该项要执行被审项目自己的校验器' });
  }
  let cmd = null;
  const pkgPath = join(repo, 'package.json');
  const pkg = existsSync(pkgPath) ? JSON.parse(readFileSync(pkgPath, 'utf8')) : null;
  const v = opts.validator;
  if (v && existsSync(join(repo, v))) cmd = { script: null, file: v };
  else if (v && pkg && pkg.scripts && pkg.scripts[v]) cmd = { script: v, file: null };
  else if (v && /^\w[\w:.-]*$/.test(v) && pkg && pkg.scripts && pkg.scripts[v]) cmd = { script: v, file: null };
  else if (!v && pkg && pkg.scripts) {
    const guess = ['validate', 'validate:content', 'check:content', 'lint:content'].find((s) => pkg.scripts[s]);
    if (guess) cmd = { script: guess, file: null };
  }
  if (!cmd) {
    return record({ id: 'CTX-3', verdict: 'not-run', reason: '找不到内容校验器：用 --validator 指明 npm script 名或脚本路径' });
  }

  // 统一走 makeWorktree：旧实现用 cpSync 的 basename 过滤器，
  // 既会跟随仓库里的符号链接（可能指向 ~/.ssh），也会把 .env 复制进账本目录。
  const work = makeWorktree(outDir, repo, 'ctx3-worktree');
  const runBaseline = () => {
    const r = cmd.script ? npmScript(work, cmd.script) : nodeScript(work, cmd.file);
    return { code: r.code, out: String(r.stdout + r.stderr).replace(/\r?\n/g, ' ').slice(0, 240) };
  };

  const base = runBaseline();
  const probeFile = findProbeTarget(work);
  if (!probeFile) {
    record({ id: 'CTX-3', verdict: 'not-run', reason: '副本里找不到可注入违规样本的内容文件（--repo 指向的树形态未知）' });
    return;
  }

  // 违规样本：多来源但只有行尾一个日期 —— 契约要求逐段，而典型实现只看行尾。
  const violating =
    '\n\n## 探针\n\n### 契约探针条目（自动化注入，可整段删除）\n\n' +
    '这条用于验证内容校验器是否真的按分段断言日期。若校验器仍报通过，说明它只看行尾。\n' +
    '来源：[探针甲社](https://probe-a.example/1)、[探针乙社](https://probe-b.example/2)（1 月 1 日）\n';
  writeFileSync(probeFile, readFileSync(probeFile, 'utf8') + violating, 'utf8');
  const after = runBaseline();
  rmSync(work, { recursive: true, force: true });

  const blind = base.code !== 0 ? null : after.code === 0;
  record({
    id: 'CTX-3',
    verdict: blind === null ? 'not-run' : blind ? 'fail' : 'pass',
    severity: blind ? 'P1' : '-',
    title:
      blind === null
        ? `校验器在正常状态下就不通过（exit ${base.code}），无法判定它对违规样本的反应`
        : blind
          ? `校验器对确定违反 README 契约的样本仍报通过（npm run ${cmd.script || cmd.file} → exit 0）：门禁与契约不等价`
          : `校验器正确拒绝了违反契约的样本（exit ${after.code}）`,
    evidence: `基线 exit ${base.code} → 注入违规样本后 exit ${after.code}；样本：多来源仅行尾一个日期`,
    locator: { file: relative(work, probeFile).split('\\').join('/') + '（门禁副本内，非你的树）' },
    repro: `复制仓库副本 → 追加多来源单日期条目 → 再跑 ${cmd.script || cmd.file}`,
    nextAction: blind ? '校验器改为按分段断言（与渲染器两套独立实现互相制衡），否则同类回归会每轮自动化重演' : '',
  });
}

function findProbeTarget(work) {
  const dirs = ['src/posts', 'src/content/daily', 'content', 'src/content', 'posts'];
  for (const d of dirs) {
    const abs = join(work, d);
    if (!existsSync(abs)) continue;
    const f = readdirSync(abs).filter((n) => n.endsWith('.md')).sort();
    if (f.length) return join(abs, f[0]);
  }
  return null;
}

process.exitCode = await safeRun(SCRIPT, USAGE, main, process.argv.slice(2));
