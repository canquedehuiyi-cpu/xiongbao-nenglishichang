#!/usr/bin/env node
/**
 * 发布链路信任边界：PIPE-1..6。
 *
 * 立场：能被发布的东西就能被用来发布别的东西。每日自动化会「拉下远端快照 → 跑校验 → 推回远端」，
 * 于是「跑谁的校验」这一件事决定了仓库被攻破时会不会变成发布机上的任意代码执行。
 */

import { existsSync, readFileSync, readdirSync, statSync } from 'node:fs';
import { walkLimited, walkCoverage } from './lib/fsx.mjs';
import { join, resolve, relative, basename } from 'node:path';
import {parseArgs, makeFindingCtx, safeRun, guardPaths, usage, run, resolveBin, gitRo} from './lib/harness.mjs';

const SCRIPT = 'pipeline-trust.mjs';
const USAGE = 'audit pipeline-trust --out <dir> --repo <dir> [--ref origin/main]';

const PIPELINE_HINT = /^(push[-_]?[\w-]*|publish[\w-]*|deploy[\w-]*|release[\w-]*|fetch[-_]?repo[\w-]*|ship[\w-]*)\.(mjs|cjs|js|ts)$/i;

function sourceFiles(dir, cap = 1200) {
  // 统一走 fsx：手写版只数「收够几个」，不数「跳过几个」——
  // 那正是 420 页产物那类假结论的成因（见 lib/fsx.mjs）。
  return walkLimited(dir, { cap, match: (n) => /\.(mjs|cjs|js|ts)$/.test(n) });
}

function lineOf(src, idx) {
  return src.slice(0, idx).split('\n').length;
}

async function main(argv) {
  let opts;
  try {
    opts = parseArgs(argv, { value: ['out', 'repo', 'ref'] }).opts;
  } catch (e) {
    return usage(SCRIPT, USAGE, e.message);
  }
  guardPaths(opts, SCRIPT);
  if (!opts.out) return usage(SCRIPT, USAGE, '需要 --out');
  const ctx = makeFindingCtx(SCRIPT, opts, undefined);
  const { record } = ctx;
  const repo = opts.repo ? resolve(opts.repo) : null;
  if (!repo || !existsSync(repo)) {
    for (const id of ['PIPE-1', 'PIPE-2', 'PIPE-3', 'PIPE-4', 'PIPE-5', 'PIPE-6']) {
      record({ id, verdict: 'not-run', reason: '需要 --repo：这一组审的是发布脚本与被跟踪文件的内容' });
    }
    return ctx.finish();
  }
  const rel = (f) => relative(repo, f).split('\\').join('/');
  const srcWalk = sourceFiles(repo);
  const files = srcWalk.files;
  const srcCov = walkCoverage(srcWalk);
  const pipeline = files.filter((f) => PIPELINE_HINT.test(basename(f)) || /push|publish|deploy/.test(readFileSync(f, 'utf8').slice(0, 400)));

  if (!files.length) {
    // 「读了 0 个文件」与「读了 0 个文件都没发现问题」在报告里长得一样，含义相反
    for (const id of ['PIPE-1', 'PIPE-2', 'PIPE-3', 'PIPE-5']) {
      record({ id, verdict: 'not-run', reason: `仓库里一个 js/ts 源文件都没读到${srcCov ? '（' + srcCov + '）' : ''}：这不是「发布链路干净」，是没有对象` });
    }
    record({ id: 'PIPE-4', verdict: 'not-run', reason: '同上：没有源文件可判定提交范围' });
    record({ id: 'PIPE-6', verdict: 'not-run', reason: '同上：没有可对齐的导出树' });
    return ctx.finish();
  }

  /* ---------- PIPE-1 执行的是哪一份门禁代码 ---------- */
  const suspicions = [];
  for (const f of pipeline) {
    const src = readFileSync(f, 'utf8');
    // 特征：把「命令行传入的目录 / 刚从远端拉下的快照」里的脚本交给 node 执行
    const callsRemoteCopy =
      /execFile(?:Sync)?\(\s*(?:process\.execPath|'node'|"node")[\s\S]{0,220}?(argv\[\d\]|work|repoDir|target|snapshot|repoTarget)/.test(src);
    const importsFromArgv = /import\(|require\([\s\S]{0,120}(argv\[\d\]|process\.argv)/.test(src);
    if (callsRemoteCopy || importsFromArgv) {
      const idx = Math.max(src.search(/execFile/), src.search(/argv\[\d\]/));
      suspicions.push({ file: rel(f), line: lineOf(src, idx), kind: importsFromArgv ? '按参数路径 import' : '按参数路径 exec' });
    }
    // 可信副本若与待发布快照同树，快照可替换它（本轮就发现过一次）
    const trustsSelfCopy = /import\.meta\.url|selfDir/.test(src) && !/startsWith\(|resolve\([^)]*repo/.test(src);
    if (trustsSelfCopy) suspicions.push({ file: rel(f), line: 1, kind: '用 import.meta.url 定位可信副本，但没有断言「本脚本不在待发布目录内」' });
  }
  record({
    id: 'PIPE-1',
    verdict: suspicions.length ? 'fail' : pipeline.length ? 'pass' : 'not-run',
    severity: suspicions.some((s) => /exec|import/.test(s.kind)) ? 'P1' : 'P2',
    level: 'J',
    reason: pipeline.length ? '' : '没找到名字像发布/部署的脚本',
    title: suspicions.length
      ? `发布脚本有 ${suspicions.length} 处「执行来自待发布快照的代码/由参数决定的路径」：${suspicions.map((s) => `${s.file}:${s.line} ${s.kind}`).join('；')}——仓库一旦被攻破即在发布机上任执行`
      : `已读 ${pipeline.length} 个发布脚本：校验器/守卫都以脚本自身位置定位且不从参数路径执行代码`,
    evidence: JSON.stringify(suspicions.slice(0, 2)).slice(0, 220),
    nextAction: suspicions.length ? '只执行本脚本旁边的可信副本，并断言 selfDir 不在待发布目录内；快照里的内容目录只当数据传入' : '',
  });

  /* ---------- PIPE-2 破坏性操作与符号链接遍历 ---------- */
  const risky = [];
  for (const f of files) {
    const src = readFileSync(f, 'utf8');
    for (const m of src.matchAll(/rm(?:Sync)?\s*\(\s*([^,)]+),\s*\{[^}]*recursive:\s*true[^}]*force:\s*true/g)) {
      const arg = m[1].trim();
      const guarded = /basename|isDirectory|startsWith|assert|realpath/.test(src.slice(Math.max(0, m.index - 900), m.index));
      if (!guarded && /^(?:work|dir|target|dest|path|repoTarget|outDir)$|argv/.test(arg)) {
        risky.push({ file: rel(f), line: lineOf(src, m.index), op: '递归强删 ' + arg, why: '删除路径来自参数且同一函数体内没有目录名/类型校验' });
      }
    }
    if (/statSync\s*\(/.test(src) && /readdirSync\s*\(/.test(src) && /isDirectory\(\)/.test(src) && !/lstatSync|isSymbolicLink/.test(src)) {
      if (/push\(\s*\{[^}]*full|upload|addFile|stageFiles|files\.push/.test(src)) {
        risky.push({ file: rel(f), line: lineOf(src, src.search(/statSync\s*\(/)), op: '遍历用 statSync（跟随符号链接）', why: '仓库里一个符号链接目录即可把发布机上的任意文件纳入上传清单' });
      }
    }
  }
  record({
    id: 'PIPE-2',
    verdict: risky.length ? 'fail' : 'pass',
    severity: risky.some((r) => /递归强删/.test(r.op)) ? 'P1' : 'P2',
    level: 'J',
    title: risky.length ? `${risky.length} 处破坏性/遍历原语缺防护：${risky.map((r) => `${r.file}:${r.line} ${r.op}`).join('；')}` : `已读 ${files.length} 个脚本文件：递归删除都有路径校验，遍历不经符号链接`,
    evidence: JSON.stringify(risky.slice(0, 2)).slice(0, 220),
    nextAction: risky.length ? '删除前校验目录名与类型；遍历改 lstatSync 并跳过 isSymbolicLink()' : '',
  });

  /* ---------- PIPE-3 门禁顺序与只读预演 ---------- */
  const order = [];
  for (const f of pipeline) {
    const src = readFileSync(f, 'utf8');
    const gi = Math.min(...['validate', 'scanSecrets', 'check(', 'guard'].map((k) => { const i = src.indexOf(k); return i < 0 ? 1e9 : i; }));
    const wi = Math.min(...['push', 'execFileSync(\'git\'', 'octokit', 'createUpdateFile', 'gitBlobSha'].map((k) => { const i = src.indexOf(k); return i < 0 ? 1e9 : i; }));
    const dryRun = /--dry-run|dryRun/.test(src);
    if (gi > wi && gi < 1e9) order.push({ file: rel(f), why: '写远端的调用出现在门禁之前，格式错误的产物会先发布再报错' });
    if (!dryRun) order.push({ file: rel(f), why: '没有 --dry-run：一个成功路径会改写公开仓库的脚本，无法安全测试' });
  }
  record({
    id: 'PIPE-3',
    verdict: order.length ? 'fail' : pipeline.length ? 'pass' : 'not-run',
    severity: order.some((o) => /写远端/.test(o.why)) ? 'P1' : 'P3',
    level: 'S',
    reason: pipeline.length ? '' : '没找到发布脚本',
    title: order.length ? `门禁顺序/预演能力有缺口：${order.map((o) => `${o.file} — ${o.why}`).join('；')}` : `${pipeline.length} 个发布脚本均先过门禁再写远端，且提供只读预演`,
    evidence: JSON.stringify(order.slice(0, 2)).slice(0, 220),
  });

  /* ---------- PIPE-4 幂等性与每次提交范围 ---------- */
  if (!resolveBin('git')) {
    record({ id: 'PIPE-4', verdict: 'not-run', reason: '环境里没有 git' });
  } else {
    const log = gitRo(repo, ['log', '--format=%s', '-n', '60'], { timeout: 60000 });
    const dupes = [];
    if (log.ok) {
      const seen = new Map();
      log.stdout.split(/\r?\n/).filter(Boolean).forEach((s, i) => {
        seen.set(s, (seen.get(s) || []).concat(i));
      });
      for (const [s, idx] of seen) if (idx.length > 1) dupes.push({ subject: s.slice(0, 40), count: idx.length });
    }
    const wide = [];
    const stat = gitRo(repo, ['show', '--stat', '--format=', 'HEAD'], { timeout: 60000 });
    if (stat.ok) {
      const touched = stat.stdout.split(/\r?\n/).filter((l) => /\|/.test(l)).length;
      if (touched > 25) wide.push({ head: touched, note: '单次提交触及文件数偏多，难审阅' });
    }
    record({
      id: 'PIPE-4',
      verdict: dupes.length || wide.length ? 'fail' : log.ok ? 'pass' : 'not-run',
      severity: 'P3',
      reason: log.ok ? '' : '取不到提交历史（目录不是仓库 / 仓库还没有任何提交 / git 不可执行——三者本工具不分定论）',
      title: dupes.length
        ? `历史里有 ${dupes.length} 组同名提交（例：「${dupes[0].subject}」×${dupes[0].count}）：自动化重跑无法区分首发与修订`
        : wide.length
          ? `${wide[0].head} 个文件在一次提交里被改动`
          : '最近 60 次提交无同名，单次范围可审',
      evidence: JSON.stringify({ dupes: dupes.slice(0, 2), wide, isRepo: log.ok }).slice(0, 220),
      nextAction: dupes.length ? '重跑且修改已有产物时，自动在提交信息追加「（修订）」' : '',
    });
  }

  /* ---------- PIPE-5 被跟踪文件里的本机路径 ---------- */
  const leaks = [];
  let tracked = { ok: false, stdout: '' };
  if (resolveBin('git')) tracked = gitRo(repo, ['ls-files'], { timeout: 60000 });
  const list = tracked.ok ? tracked.stdout.split(/\r?\n/).filter(Boolean) : files.map(rel);
  for (const r of list) {
    if (!/\.(mjs|cjs|js|ts|json|yml|yaml|md|txt|env)$/.test(r)) continue;
    const f = join(repo, r);
    if (!existsSync(f) || statSync(f).size > 400000) continue;
    const src = readFileSync(f, 'utf8');
    for (const m of src.matchAll(/(?:^|[^\w/])([A-Za-z]:[\\/][^\s'"`,)]{2,}|\/Users\/[\w.-]{2,}|\/home\/[\w.-]{2,})/g)) {
      if (/example|placeholder|[A-Za-z]:[\\/]path|schemas|\bwww\b/i.test(m[1])) continue;
      leaks.push({ file: r, line: lineOf(src, m.index), shape: m[1].slice(0, 26).replace(/[A-Za-z0-9_.-]{4,}/g, '…') });
    }
  }
  record({
    id: 'PIPE-5',
    verdict: leaks.length ? 'fail' : list.length ? 'pass' : 'not-run',
    severity: 'P3',
    reason: leaks.length || list.length ? '' : '拿不到被跟踪文件清单（不是仓库、无提交，或 git 不可执行）：0 条清单不等于 0 处泄露',
    title: leaks.length ? `${leaks.length} 个被跟踪文件里写有本机绝对路径（例：${leaks[0].file}:${leaks[0].line}）——公开仓库里等于交代发布机的目录结构` : `${list.length} 个被跟踪文件里没有本机绝对路径`,
    evidence: JSON.stringify(leaks.slice(0, 2)).slice(0, 200),
    locator: leaks.length ? { file: leaks[0].file, line: leaks[0].line } : null,
    nextAction: leaks.length ? '改成环境变量或命令行参数，默认值别写进仓库' : '',
  });

  /* ---------- PIPE-6 手上这份 == 远端 ---------- */
  if (!resolveBin('git')) {
    record({ id: 'PIPE-6', verdict: 'not-run', reason: '无 git' });
  } else {
    const local = gitRo(repo, ['rev-parse', 'HEAD'], { timeout: 30000 });
    const dirty = gitRo(repo, ['status', '--porcelain'], { timeout: 30000 });
    const remote = gitRo(repo, ['ls-remote', 'origin', opts.ref || 'refs/heads/main'], { timeout: 60000 });
    if (!local.ok) {
      record({ id: 'PIPE-6', verdict: 'not-run', reason: '取不到本地 HEAD（不是仓库，或有 .git 但还没有提交）：导出树无法与远端对齐' });
    } else {
      const l = local.stdout.trim().slice(0, 40);
      const r = (remote.stdout || '').split(/\s/)[0] || '';
      const uncommitted = dirty.ok ? dirty.stdout.split(/\r?\n/).filter(Boolean).length : -1;
      const remoteRead = remote.ok && !!r;
      record({
        id: 'PIPE-6',
        verdict: (r && r !== l) || uncommitted > 0 ? 'fail' : remoteRead ? 'pass' : 'not-run',
        severity: 'P2',
        reason: !remoteRead && uncommitted <= 0
          ? '远端读不到（本工具不使用任何凭据，私有仓库必然失败）：没有远端 sha 就无法判断「审的是不是将要发布的那一份」，这属于未跑，不是通过'
          : '',
        title: r && r !== l
          ? `本地 HEAD ${l.slice(0, 8)} ≠ 远端 ${r.slice(0, 8)}：审的可能是一份过期副本，所有结论都要重做`
          : uncommitted > 0
            ? `工作树有 ${uncommitted} 处未提交改动：审查对象与将发布的对象不是同一份东西`
            : remoteRead ? `本地与远端一致（${l.slice(0, 8)}），工作树干净` : `工作树干净、本地 HEAD ${l.slice(0, 8)}；远端未核对（无凭据可用）`,
        evidence: JSON.stringify({ local: l.slice(0, 8), remote: r.slice(0, 8) || '不可达', uncommitted }),
      });
    }
  }

  return ctx.finish();
}

process.exitCode = await safeRun(SCRIPT, USAGE, main, process.argv.slice(2));
