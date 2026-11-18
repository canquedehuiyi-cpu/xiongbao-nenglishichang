#!/usr/bin/env node
/**
 * 构建产物取证：BLD-1..6。
 *
 * 立场：源码写了不等于产物里有。这一组只认 dist 里的字节，
 * 以及「把对抗性内容喂进真实构建后它还活不活得下来」。
 */

import { existsSync, readFileSync, readdirSync, statSync, rmSync, cpSync, mkdirSync, writeFileSync } from 'node:fs';
import { join, resolve, relative } from 'node:path';
import { parseArgs, EXIT, makeFindingCtx, safeRun, guardPaths, usage, npmScript, run, resolveBin, makeWorktree } from './lib/harness.mjs';
import { readJsonIfExists } from './lib/jsonl.mjs';
import { linksOf, scriptsOf, stripInert } from './lib/html.mjs';
import { walkLimited, walkCoverage } from './lib/fsx.mjs';
import { UNRUNNABLE_RE, missingProgram } from './lib/tools.mjs';

const SCRIPT = 'build-forensics.mjs';
const USAGE = 'audit build-forensics --out <dir> --repo <dir> [--dist <dir>] [--no-build]';

/**
 * 产物里的 HTML。带上限是必要的（仓库可能很大），但**触顶必须说出来**：
 * 原先这里只数「收够了几个」，450 页扫 400 页，报出来是一句口气完整的
 * 「400 页零内联事件」，同时 BLD-6 反过来编出「50 个 URL 在产物中不存在」的假缺陷。
 */
function htmlFiles(dir, cap = 400) {
  return walkLimited(dir, { cap, match: (n) => n.endsWith('.html'), skipDirs: new Set(['node_modules', '.git', '.astro', 'coverage']) });
}

async function main(argv) {
  let opts;
  try {
    opts = parseArgs(argv, { value: ['out', 'repo', 'dist'], bool: ['no-build'] }).opts;
  } catch (e) {
    return usage(SCRIPT, USAGE, e.message);
  }
  guardPaths(opts, SCRIPT);
  if (!opts.out) return usage(SCRIPT, USAGE, '需要 --out');
  const capsDoc = readJsonIfExists(resolve(opts.out), 'capabilities.json');
  const ctx = makeFindingCtx(SCRIPT, opts, capsDoc);
  const { record } = ctx;
  const repo = opts.repo ? resolve(opts.repo) : null;
  const dist = opts.dist ? resolve(opts.dist) : repo ? join(repo, 'dist') : null;

  if (!repo || !dist || !existsSync(dist)) {
    for (const id of ['BLD-1', 'BLD-2', 'BLD-3', 'BLD-4', 'BLD-5', 'BLD-6']) {
      record({ id, verdict: 'not-run', reason: '需要 --repo 与可存在的 --dist 产物目录（先跑构建）' });
    }
    return ctx.finish();
  }
  const rel = (f) => relative(repo, f).split('\\').join('/');
  const pageWalk = htmlFiles(dist);
  const pages = pageWalk.files;
  const pageCov = walkCoverage(pageWalk);
  // 0 页产物不是「全部通过」，是没有对象。旧版在这里能报出
  // 「0 页产物结构断言全通过 / 零 JS 零内联事件」这种漂亮的空结论（第 3 轮实测）。
  const noPages = !pages.length;
  const noPagesWhy = `产物目录里一个 HTML 都没有（${existsSync(dist) ? '目录存在但为空' : '目录不存在'}：${dist ? rel(dist) : '--dist 未指到有效目录'}）——「0 页全通过」不是结论`;

  /* ---------- BLD-1 重跑项目自己的门禁 ---------- */
  if (opts.noBuild || !(ctx.caps && ctx.caps.replay)) {
    record({ id: 'BLD-1', verdict: 'not-run', reason: opts.noBuild ? '显式 --no-build' : 'replay 能力缺失（无 package.json 或不可执行）' });
  } else {
    const pkg = JSON.parse(readFileSync(join(repo, 'package.json'), 'utf8'));
    const names = Object.keys(pkg.scripts || {});
    // 不写死 check/test/build/validate：真实项目常叫 lint/typecheck/verify/build:static，
    // 写死会让这一项在多数项目上「跑了 0 条命令」却报全绿。
    const gates = names.filter((s) => /^(check|typecheck|lint|test|tests|build|build:.+|validate|verify|ci)$/i.test(s)).slice(0, 6);
    if (!gates.length) {
      record({ id: 'BLD-1', verdict: 'not-run', reason: 'package.json 里没有可识别的门禁脚本（check/lint/test/build/validate/verify）' });
    }
    // 在 --out 的副本里跑：被审仓库必须保持只读，构建会写 dist、可能触发 postinstall
    const execTree = makeWorktree(opts.out, repo, 'bld-worktree');
    // 副本按规则不含 node_modules（依赖不属于被审项目的内容，也不该进任何产物）。
    // 于是「有依赖的项目在副本里必然构建失败」——把这种失败记成门禁红灯是编造缺陷。
    // 判据用 UNRUNNABLE_RE：除模块解析失败外，还要认「CLI 根本没装」这一类。
    const results = [];
    for (const g of gates) {
      const r = npmScript(execTree, g);
      const tail = String(r.stdout + r.stderr).replace(/\r?\n/g, ' ');
      results.push({
        gate: g,
        code: r.code,
        unrunnable: r.code !== 0 && (UNRUNNABLE_RE.test(tail) || missingProgram(pkg.scripts[g], [join(execTree, 'node_modules', '.bin')]).missing),
        tail: tail.slice(-90),
      });
    }
    rmSync(execTree, { recursive: true, force: true });
    const bad = results.filter((r) => r.code !== 0 && !r.unrunnable);
    const blocked = results.filter((r) => r.unrunnable);
    record({
      id: 'BLD-1',
      verdict: bad.length ? 'fail' : blocked.length ? 'not-run' : 'pass',
      severity: bad.some((b) => b.gate === 'build') ? 'P1' : bad.length ? 'P2' : '-',
      reason: !bad.length && blocked.length ? `${blocked.map((b) => b.gate).join('/')} 在这台机器上根本跑不起来（缺依赖或缺 CLI），不是门禁红灯：要在装好工具链的环境里重跑这一项` : '',
      title: bad.length ? `重跑门禁有红灯：${bad.map((b) => `${b.gate} exit ${b.code}`).join('，')}——此后每次部署都会失败` : blocked.length ? `${gates.length - blocked.length} 道门禁重放通过，${blocked.length} 道因工具链缺失未能重放` : `已重跑 ${results.map((r) => r.gate).join('/')}，全绿`,
      evidence: JSON.stringify(bad.length ? bad : results).slice(0, 240),
      nextAction: bad.length ? '先让构建恢复，再谈其它结论：构建是红的时候任何「产物安全」说法都不成立' : '',
    });

    /* ---------- BLD-3 对抗性内容喂进真实构建 ---------- */
    const work = makeWorktree(opts.out, repo, 'bld3');
    const contentDirs = ['src/posts', 'src/content/daily', 'content', 'posts'];
    const cdir = contentDirs.map((d) => join(work, d)).find((d) => existsSync(d));
    if (!cdir || !pkg.scripts || !pkg.scripts.build) {
      record({ id: 'BLD-3', verdict: 'not-run', reason: '副本里找不到内容目录或 build 脚本，无法注入对抗样本' });
    } else {
      const base = readdirSync(cdir).filter((f) => f.endsWith('.md'))[0];
      const probe = base ? readFileSync(join(cdir, base), 'utf8') : '';
      const samples = [
        { name: '空正文', body: '# 探针\n\n## 探针板块\n\n### 只有标题没有正文\n\n来源：[探针社](https://probe.example/1)（1 月 1 日）\n' },
        { name: '正文以分隔线开头', body: '# 探针\n\n---\n\n## 探针板块\n\n### 分隔线开头\n\n正文一行。\n\n来源：[探针社](https://probe.example/2)（1 月 1 日）\n' },
        { name: '免责声明在分隔线之后', body: probe + '\n---\n\n这是分隔线之后的声明文字，必须出现在产物里。\n' },
      ];
      // 零样本基线：先不加任何探针跑一次真实构建。它本身就失败时，后面三次失败说明不了样本的事
      // ——第 3 轮实测：一个构建本来就红的项目被报成「3 个对抗样本都会让构建崩溃（P1）」。
      const baseline = npmScript(work, 'build');
      const blTail = String(baseline.stdout + baseline.stderr).replace(/\s+/g, ' ');
      const baselineBad = baseline.code !== 0;
      const missing = missingProgram(pkg.scripts.build, [join(work, 'node_modules', '.bin')]);
      const toolchain = baselineBad && (UNRUNNABLE_RE.test(blTail) || missing.missing) ? (missing.program || '（脚本文本里的程序）') : '';
      const crashes = [];
      const lost = [];
      for (let i = 0; i < samples.length; i++) {
        const f = join(cdir, `zz-probe-${i}.md`);
        writeFileSync(f, samples[i].body, 'utf8');
        const r = npmScript(work, 'build');
        if (!r.ok) crashes.push({ sample: samples[i].name, code: r.code, tail: String(r.stderr).slice(-80) });
        if (samples[i].name.startsWith('免责声明')) {
          const hit = htmlFiles(join(work, 'dist')).files.find((p) => readFileSync(p, 'utf8').includes('必须出现在产物里'));
          if (!hit) lost.push('免责声明被静默丢弃');
        }
        rmSync(f);
      }
      rmSync(work, { recursive: true, force: true });
      record({
        id: 'BLD-3',
        verdict: baselineBad ? 'not-run' : crashes.length || lost.length ? 'fail' : 'pass',
        severity: baselineBad ? '-' : 'P1',
        reason: baselineBad
          ? `未注入任何样本时构建就已失败（exit ${baseline.code}），所以这三次失败说明不了对抗内容的事${toolchain ? '；且要跑的程序 ' + toolchain + ' 在这台机器上解析不到，属于工具链缺失而非项目缺陷' : ''}`
          : '',
        title: baselineBad
          ? '零样本基线未通过：本项无法判定（既不能说对抗内容安全，也不能说它会打崩构建）'
          : crashes.length
          ? `对抗性内容样本会让构建崩溃：${crashes.map((c) => `${c.sample}（exit ${c.code}）`).join('；')}——若该内容来自自动化，此后每次发布都失败`
          : lost.length
            ? `渲染器静默丢弃了内容：${lost.join('；')}`
            : `${samples.length} 个对抗样本经真实构建后均无崩溃、无内容丢失（零样本基线先通过）`,
        evidence: JSON.stringify({ baseline: baselineBad ? blTail.slice(-110) : 'ok', first: crashes[0] || lost[0] || null, samples: samples.length }).slice(0, 300),
        repro: '在临时副本里先跑一次干净构建作基线，通过后逐个追加探针内容文件再构建，比较退出码与产物文字',
      });
    }
  }

  /* ---------- BLD-2 产物结构断言 ---------- */
  const structural = [];
  let itemish = 0;
  for (const f of pages) {
    const html = readFileSync(f, 'utf8');
    const r = rel(f);
    if (!/lang=["'][^"']+["']/.test(html)) structural.push({ file: r, why: '缺 lang 属性' });
    if (!/<title>/.test(html)) structural.push({ file: r, why: '缺 title' });
    if (!/rel="canonical"/.test(html) && !/robots" content="noindex/.test(html)) structural.push({ file: r, why: '既无 canonical 也非 noindex 页' });
    for (const m of html.matchAll(/<a\b[^>]*href="#"[^>]*>/g)) structural.push({ file: r, why: 'href="#" 死链锚' });
    itemish += (html.match(/<article|<li class="|class="item"/g) || []).length;
  }
  record({
    id: 'BLD-2',
    verdict: noPages ? 'not-run' : structural.length ? 'fail' : 'pass',
    reason: noPages ? noPagesWhy : '',
    severity: structural.length > pages.length ? 'P2' : 'P3',
    title: structural.length ? `${pages.length} 页产物里有 ${structural.length} 处结构缺失（例：${structural[0].file} — ${structural[0].why}）` : `${pages.length} 页产物结构断言全通过${pageCov ? '（但' + pageCov + '）' : ''}`,
    evidence: JSON.stringify({ structural: structural.slice(0, 3), coverage: pageCov || '扫全' }).slice(0, 300),
    locator: structural.length ? { file: structural[0].file } : null,
  });

  /* ---------- BLD-4 产物安全普查 ---------- */
  const jsWalk = walkLimited(dist, { cap: 800, match: (n) => n.endsWith('.js'), skipDirs: new Set(['node_modules', '.git', '.astro', 'coverage']) });
  const js = jsWalk.files.map(rel);
  const jsCov = walkCoverage(jsWalk);
  let jsUrl = 0;
  let inlineHandler = 0;
  let insecureHref = 0;
  let controlChars = 0;
  for (const f of pages) {
    const html = readFileSync(f, 'utf8');
    jsUrl += (html.match(/href="javascript:/gi) || []).length;
    inlineHandler += (html.match(/\son[a-z]+\s*=\s*["'][^"']+/gi) || []).length;
    controlChars += (html.match(/[\u0000-\u0008\u000b\u000c\u000e-\u001f]/g) || []).length;
    for (const l of linksOf(stripInert(html))) if (/^http:\/\//i.test(l.href)) insecureHref++;
  }
  const n4 = js.length + jsUrl + inlineHandler + controlChars;
  record({
    id: 'BLD-4',
    verdict: noPages ? 'not-run' : n4 ? 'fail' : 'pass',
    reason: noPages ? noPagesWhy : '',
    severity: jsUrl + inlineHandler ? 'P1' : n4 ? 'P2' : '-',
    title: n4
      ? `产物安全普查有异常：JS ${js.length}、javascript: 链接 ${jsUrl}、内联事件 ${inlineHandler}、控制字符 ${controlChars}`
      : `产物零 JS、零内联事件、零 javascript: 链接、零控制字符（${pages.length} 页）`,
    evidence: js.length ? js.slice(0, 3).join(', ') : `http:// 降级链接 ${insecureHref} 处（计入 LNK-1，不在本项判红）`,
    nextAction: js.length ? '纯静态站不该带 JS：确认是否有构建插件注入，或据此把 CSP 的必要性重述一遍' : '',
  });

  /* ---------- BLD-5 体积预算 ---------- */
  const sizes = pages.map((f) => ({ file: rel(f), bytes: statSync(f).size })).sort((a, b) => b.bytes - a.bytes);
  const total = sizes.reduce((n, s) => n + s.bytes, 0);
  const worst = sizes[0];
  record({
    id: 'BLD-5',
    verdict: noPages ? 'not-run' : worst && worst.bytes > 200000 ? 'fail' : 'pass',
    reason: noPages ? noPagesWhy : '',
    severity: 'P3',
    title: worst && worst.bytes > 200000
      ? `单页体积失控：${worst.file} ${Math.round(worst.bytes / 1024)} KB（阈值 200 KB）`
      : `${pages.length} 页 / 共 ${(total / 1024).toFixed(0)} KB，最大单页 ${worst ? Math.round(worst.bytes / 1024) : 0} KB${pageCov ? '；' + pageCov : ''}`,
    evidence: JSON.stringify(sizes.slice(0, 2)),
  });

  /* ---------- BLD-6 站点地图 ↔ 产物 + 订阅源 ---------- */
  const sm = ['sitemap.xml', 'sitemap-0.xml', 'sitemap-index.xml'].map((f) => join(dist, f)).find(existsSync);
  const setDiff = [];
  if (sm) {
    const locs = [...readFileSync(sm, 'utf8').matchAll(/<loc>([^<]+)<\/loc>/g)].map((m) => {
      try { return new URL(m[1]).pathname; } catch { return m[1]; }
    });
    const have = new Set(pages.map((p) => '/' + relative(dist, p).split('\\').join('/').replace(/index\.html$/, '')));
    const notBuilt = pageWalk.truncated ? [] : locs.filter((l) => !have.has(l) && !have.has(l.replace(/\/$/, '') + '/index.html'));
    const notInSitemap = pageWalk.truncated ? [] : [...have].filter((h) => !locs.includes(h) && h !== '/');
    if (pageWalk.truncated) setDiff.push(`产物遍历触顶，差集无法计算（曾被误读成「URL 不存在」的假缺陷）`);
    if (notBuilt.length) setDiff.push(`站点地图里有 ${notBuilt.length} 个 URL 在产物中不存在：${notBuilt.slice(0, 2).join(', ')}`);
    if (notInSitemap.length) setDiff.push(`产物里有 ${notInSitemap.length} 个页面未进站点地图`);
  } else setDiff.push('产物里没有 sitemap');
  const feed = ['rss.xml', 'feed.xml', 'posts.xml', 'atom.xml'].map((f) => join(dist, f)).find(existsSync);
  let feedIssue = '';
  if (feed) {
    const xml = readFileSync(feed, 'utf8');
    if (/<\/?xml/.test(xml) && !/<\/rss>|<\/feed>/.test(xml)) feedIssue = '订阅源标签未闭合（XML 不合法）';
    if (/&amp;(lt|gt|quot|#)\w*;/i.test(xml)) feedIssue = '订阅源存在双重转义（&amp;lt; 之类），阅读器会显示字面量';
    if (/&lt;(p|div|span|ul|li|strong)\b/i.test(xml)) feedIssue = '订阅源里输出了被转义的 HTML 标签原文';
  } else feedIssue = '无订阅源文件';
  record({
    id: 'BLD-6',
    verdict: noPages ? 'not-run' : setDiff.length || feedIssue ? 'fail' : 'pass',
    reason: noPages ? noPagesWhy : '',
    severity: setDiff.some((s) => /不存在/.test(s)) ? 'P2' : 'P3',
    title: [...setDiff, feedIssue && `订阅源：${feedIssue}`].filter(Boolean).join('；') || `站点地图与产物逐条相等（${pages.length} 页），订阅源可解析`,
    evidence: JSON.stringify({ pages: pages.length, feed: feed ? rel(feed) : null, setDiff }).slice(0, 220),
  });

  return ctx.finish();
}

process.exitCode = await safeRun(SCRIPT, USAGE, main, process.argv.slice(2));
