#!/usr/bin/env node
/**
 * 开轮 + 能力探测。
 *
 * 为什么必须先跑它：后续每个脚本按 capabilities.json 决定「跑」还是「记一条 not-run + 原因」。
 * 没有这一份，「缺能力」和「有人没跑」就分不开——而后者正是本工具要消灭的东西。
 * probe 也是唯一递增轮次的人。
 */

import { existsSync, statSync } from 'node:fs';
import { join, resolve, basename } from 'node:path';
import { parseArgs, EXIT, resolveBin, resolveNpm, usage, nowIso, targetHash, run } from './lib/tools.mjs';
import { ensureOut, assertReadablePath, homePlaceholder } from './lib/scratch.mjs';
import { writeJson, readJsonIfExists } from './lib/jsonl.mjs';
import { HttpBudget, parseRobots, PolicyViolation, openRoundNetState } from './lib/net.mjs';
import { safeRun, sweepStaleWorktrees, guardPaths, gitRo } from './lib/harness.mjs';

const SCRIPT = 'probe.mjs';
const USAGE = 'audit probe --out <dir> [--url https://example.com/] [--repo <dir>] [--authorized "who"] [--browser] [--probe-links] [--budget 60]';

const PREAMBLE =
  '黑盒模式会对可能不属于你的主机发起真实网络请求（被动读取 + 轻量主动探测）。' +
  '未获授权的使用可能违反法律或对方服务条款，责任在使用者。' +
  '确认已获得授权后加 --authorized "<谁授权的>"。';

export async function main(argv) {
  let opts;
  try {
    opts = parseArgs(argv, {
      value: ['out', 'url', 'repo', 'authorized', 'budget', 'concurrency', 'user-agent', 'dist'],
      bool: ['browser', 'probe-links'],
    }).opts;
  } catch (e) {
    return usage('probe', USAGE, e.message);
  }
  if (!opts.out) return usage('probe', USAGE, '需要 --out');
  if (!opts.url && !opts.repo) return usage('probe', USAGE, '至少要有 --url 或 --repo 之一');
  // 带凭据的目标地址必须在入口就拒：请求层面 net.mjs 不会发出去，但 probe 会把原文
  // 写进 capabilities.json / state.json ——凭据于是躺在要给人看的目录里（第 3 轮实测）。
  if (opts.url) {
    try {
      const uu = new URL(opts.url);
      if (uu.username || uu.password) {
        return usage('probe', USAGE, '--url 里带 userinfo：本工具从不发送任何凭据，请改用凭据助手或去掉 user:pass@');
      }
    } catch {
      return usage('probe', USAGE, '--url 不是合法 URL：' + String(opts.url).slice(0, 60));
    }
  }

  // --out 位置必须校验：probe 是最常跑的入口，绕过守卫就等于把账本写进被审仓库或插件源码树
  guardPaths(opts, SCRIPT);
  let outDir;
  try {
    outDir = ensureOut(opts.out);
  } catch (e) {
    return usage('probe', USAGE, e.message);
  }

  const mode = opts.repo ? 'whitebox' : 'blackbox';
  if (mode === 'blackbox' && !opts.authorized) {
    console.error('probe: 黑盒模式拒绝启动。');
    console.error(PREAMBLE);
    return EXIT.USAGE;
  }

  /* ---- 仓库侧能力 ---- */
  let repo = null;
  let repoReal = '';
  if (opts.repo) {
    try {
      repoReal = assertReadablePath(resolve(opts.repo), { purpose: '被审项目' });
      if (statSync(repoReal).isDirectory()) repo = repoReal;
    } catch (e) {
      console.error(`probe: --repo 不可用：${e.message}`);
      return EXIT.USAGE;
    }
  }
  const caps = {
    repo: !!repo,
    dist: !!(opts.dist && existsSync(resolve(opts.dist))),
    replay: false,
    net: false,
    browser: opts.browser === true,
    links: opts.probeLinks === true,
    git: false,
    ci: false,
    ledger: false,
  };
  const notes = [];
  // 开轮先补收上次硬杀留下的副本（信号钩子救不了 kill -9 与断电）
  const swept = sweepStaleWorktrees();
  if (swept.removed.length) notes.push(`清掉 ${swept.removed.length} 份上次遗留的临时副本（${swept.root}）`);
  if (swept.failed) notes.push('临时目录读不了，历史副本未能回收');

  if (repo) {
    const pkg = join(repo, 'package.json');
    caps.replay = existsSync(pkg);
    caps.git = existsSync(join(repo, '.git'));
    caps.ci =
      existsSync(join(repo, '.github', 'workflows')) ||
      existsSync(join(repo, '.gitlab-ci.yml')) ||
      existsSync(join(repo, 'Jenkinsfile')) ||
      existsSync(join(repo, '.circleci', 'config.yml'));
    if (!caps.replay) notes.push('无 package.json：replay 类检查（BLD-1/3, SEC-6/7, CI-2）将记 not-run');
    if (!caps.git) notes.push('该树不是 git 仓库：PIPE-4/6、SEO-2、DOC-3 需要历史，将记 not-run');
  }

  /* ---- 轮次元数据：网络预算要按轮记账，所以先定轮次再发请求 ---- */
  const prev = readJsonIfExists(outDir, 'state.json');
  const round = prev && Number.isFinite(prev.round) ? prev.round + 1 : 1;

  /* ---- 网络侧能力 ---- */
  const budget = new HttpBudget({
    shared: openRoundNetState(outDir, round),
    allowPrivate: true, // 目标由审查者显式指定，允许本地/内网测试站
    budget: Number(opts.budget) || 60,
    concurrency: Number(opts.concurrency) || 2,
    userAgent: opts.userAgent || 'site-audit/1.0',
  });
  let reach = null;
  let robots = null;
  if (opts.url) {
    try {
      const home = await budget.request(opts.url, { method: 'GET' });
      caps.net = home.ok || home.status > 0;
      reach = {
        url: opts.url,
        status: home.status,
        err: home.err || '',
        server: home.headers?.server || '',
        csp: home.headers?.['content-security-policy'] || '',
        bytes: home.body ? home.body.length : 0,
      };
      if (!caps.net) notes.push(`目标不可达（${home.err || 'status ' + home.status}）：所有 net 类检查将记 not-run`);
      const rb = await budget.request(new URL('/robots.txt', opts.url).href, { method: 'GET' });
      robots = rb.ok ? parseRobots(rb.body) : { parses: false, disallow: [], allow: [], sitemaps: [] };
    } catch (e) {
      if (!(e instanceof PolicyViolation)) throw e;
      notes.push(`策略拒绝: ${e.message}`);
    }
  }

  /* ---- 账本侧能力 ---- */
  caps.ledger = !!prev;
  const runId = `r${round}-${nowIso().replace(/[-:TZ.]/g, '').slice(0, 12)}`;

  writeJson(outDir, 'capabilities.json', {
    round,
    runId,
    mode,
    ts: nowIso(),
    capabilities: caps,
    tooling: {
      node: process.version,
      platform: process.platform,
      // 「找得到 git」与「跑得动 git」不是一回事：精简 PATH 下 resolveBin 能命中，
      // 真跑却被系统拒绝。能力矩阵虚报 yes 会让后面的检查把失败算成项目缺陷。
      git: !!resolveBin('git') && gitRo(null, ['--version'], { timeout: 20000, cleanEnv: true }).ok,
      npm: resolveNpm()?.how || 'none',
    },
    target: {
      url: opts.url || '',
      host: opts.url ? new URL(opts.url).host : '',
      targetHash: opts.url ? targetHash(opts.url) : '',
      repo: repo ? homePlaceholder(repo) : '',
      repoBasename: repo ? basename(repo) : '',
      dist: opts.dist ? homePlaceholder(resolve(opts.dist)) : '',
    },
    authorization: opts.authorized || (mode === 'whitebox' ? 'implicit: 使用者自己的项目' : ''),
    preamble: mode === 'blackbox' ? PREAMBLE : '',
    robots: robots ? { disallow: robots.disallow, allow: robots.allow, parses: robots.parses, sitemaps: robots.sitemaps } : null,
    reach,
    budget: budget.stats(),
    notes,
  });
  writeJson(outDir, 'state.json', {
    round,
    lastRunId: runId,
    mode,
    ts: nowIso(),
    openedBy: 'probe',
    targetHash: opts.url ? targetHash(opts.url) : '',
    url: opts.url || '',
  });

  console.log(`probe: round ${round} · mode ${mode} · runId ${runId}`);
  console.log('能力矩阵: ' + Object.entries(caps).map(([k, v]) => `${k}=${v ? 'yes' : 'no'}`).join('  '));
  console.log(`输出: ${homePlaceholder(outDir)}`);
  console.log(`请求预算: ${budget.stats().used}/${budget.stats().budget} 已用于探测本身`);
  for (const n of notes) console.log(`note: ${n}`);
  if (mode === 'blackbox') console.log('授权记录: ' + (opts.authorized || ''));
  console.log('');
  console.log('下一步：按能力跑检测脚本（缺能力的会各自记 not-run），最后 audit ledger verify 收口。');
  return EXIT.CLEAN;
}

process.exitCode = await safeRun(SCRIPT, USAGE, main, process.argv.slice(2));
