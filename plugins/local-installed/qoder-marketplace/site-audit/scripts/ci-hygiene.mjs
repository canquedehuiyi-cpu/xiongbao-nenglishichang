#!/usr/bin/env node
/**
 * CI 与测试覆盖：CI-1..4。
 *
 * 立场：CI 红不代表挡得住东西，CI 绿也不代表它跑过。
 * 这一组只看工作流文件的实际权限与触发条件，以及「测试到底覆盖了哪一层」。
 */

import { existsSync, readFileSync, readdirSync, statSync } from 'node:fs';
import { join, resolve, relative } from 'node:path';
import {parseArgs, makeFindingCtx, safeRun, guardPaths, usage, run, resolveBin, gitRo} from './lib/harness.mjs';
import { scanWorkflowYaml, writeScopes, runInterpolations } from './lib/rules.mjs';
import { walkLimited, walkCoverage } from './lib/fsx.mjs';

const SCRIPT = 'ci-hygiene.mjs';
const USAGE = 'audit ci-hygiene --out <dir> --repo <dir> [--tests <dir>] [--check-protection]';

const SHA_PIN = /uses:\s*[\w.-]+\/[\w./-]+@?[0-9a-f]{40}/;
const MUTABLE = /uses:\s*[\w.-]+\/[\w./-]+@(main|master|v?\d+(\.\d+)*)\b/;

function findWorkflows(repo) {
  const d = join(repo, '.github', 'workflows');
  if (!existsSync(d)) return [];
  return readdirSync(d).filter((f) => /\.(yml|yaml)$/.test(f)).map((f) => ({ name: f, path: join(d, f), text: readFileSync(join(d, f), 'utf8') }));
}

/** 源文件清单：带上限且自报覆盖度（见 lib/fsx.mjs 的注释）。 */
function srcFiles(dir, cap = 500) {
  return walkLimited(dir, { cap, match: (n) => /.(mjs|cjs|js|ts|astro|vue|svelte|jsx|tsx)$/.test(n) });
}
async function main(argv) {
  let opts;
  try {
    opts = parseArgs(argv, { value: ['out', 'repo', 'tests'], bool: ['check-protection'] }).opts;
  } catch (e) {
    return usage(SCRIPT, USAGE, e.message);
  }
  guardPaths(opts, SCRIPT);
  if (!opts.out) return usage(SCRIPT, USAGE, '需要 --out');
  const ctx = makeFindingCtx(SCRIPT, opts, undefined);
  const { record } = ctx;
  const repo = opts.repo ? resolve(opts.repo) : null;
  if (!repo || !existsSync(repo)) {
    for (const id of ['CI-1', 'CI-2', 'CI-3', 'CI-4']) record({ id, verdict: 'not-run', reason: '需要 --repo' });
    return ctx.finish();
  }
  const rel = (f) => relative(repo, f).split('\\').join('/');
  const wfs = findWorkflows(repo);

  /* ---------- CI-1 工作流加固 ---------- */
  if (!wfs.length) {
    record({
      id: 'CI-1',
      verdict: 'fail',
      severity: 'P1',
      title: '仓库里没有任何 CI 工作流：所有「已通过检查」的说法都只可能在本地发生',
      evidence: `已扫 ${rel(repo)}/.github/workflows`,
      nextAction: '加一条 push/PR 上依次跑 install→类型→测试→构建→内容校验的工作流，并配 concurrency 避免与定时推送并行',
    });
  } else {
    const issues = [];
    const add = (w, sev, why) => issues.push({ file: `.github/workflows/${w.name}`, sev, why });
    for (const w of wfs) {
      const t = w.text;
      const { permissions, runs } = scanWorkflowYaml(t);
      const writes = writeScopes(permissions);
      const { untrusted, other: others } = runInterpolations(runs);
      const forkTrig = /pull_request_target|issue_comment|pull_request_review_comment|discussion_comment|repository_dispatch/.test(t);
      if (!permissions.length) {
        add(w, 'P2', '未声明 permissions：GITHUB_TOKEN 沿用仓库默认，而默认值很可能是 write-all');
      } else if (writes.some((x) => x.level === 'write-all')) {
        add(w, 'P1', `permissions: write-all（job ${writes.find((x) => x.level === 'write-all').job || '顶层'}）：一次供应链投毒的 action 就能改写仓库`);
      } else if (writes.length) {
        add(w, forkTrig ? 'P2' : 'P3', `GITHUB_TOKEN 被给了写权限：${writes.map((x) => `${x.scope}=${x.level}${x.job ? '@' + x.job : ''}`).join(', ').slice(0, 90)}——对照实际用到的动作核一遍能否降为 read`);
      }
      const jobs = [...t.matchAll(/\n\s{2}(\w[\w-]*):\s*\n/g)].map((m) => m[1]);
      const mutable = (t.match(new RegExp(MUTABLE, 'g')) || []).filter((x) => !SHA_PIN.test(x));
      if (mutable.length) add(w, 'P2', `${mutable.length} 个第三方动作钉在可变标签：${mutable.slice(0, 2).join(' | ').slice(0, 60)}`);
      if (/\bpull_request_target\b/.test(t)) add(w, 'P1', 'pull_request_target：会用基仓库的写权限跑 fork 代码');
      if (!/timeout-minutes/.test(t)) add(w, 'P3', '无 timeout-minutes：一次挂住的作业会长期占并发');
      if (untrusted.length) {
        add(w, forkTrig ? 'P1' : 'P2', `${untrusted.length} 处在 run: 里插值不可信上下文（例：${untrusted[0].expr}）——${forkTrig ? '该工作流会被无写权限的外部提交者触发，等于让他在 runner 上执行脚本' : '即便当前只有内部触发源可触发，也应在改动作后重看这一条'}`);
      } else if (others.length) {
        add(w, 'P3', `${others.length} 处 run: 里插值上下文（例：${others[0].expr}）：改用 env: 传参，插值只留给非 run 字段`);
      }
      if (/npm ci|npm install/.test(t) && !/--ignore-scripts/.test(t)) add(w, 'P2', 'npm ci/install 未加 --ignore-scripts：PR 改 lockfile 即可在 runner 上跑安装脚本');
      if (/secrets\.|GITHUB_TOKEN/.test(t) && /\becho\b/.test(jobs.length ? t : t)) add(w, 'P2', '工作流里同时出现 secrets 与 echo，需人工确认没有把令牌打进日志');
    }
    const worst = issues.length ? issues.map((i) => i.sev).sort()[0] : '-';
    const p1 = issues.filter((i) => i.sev === 'P1');
    record({
      id: 'CI-1',
      verdict: issues.length ? 'fail' : 'pass',
      severity: issues.length ? worst : '-',
      title: issues.length
        ? `${wfs.length} 个工作流里 ${issues.length} 处加固缺口${p1.length ? `（含 ${p1.length} 处可直接导致仓库被改写：${p1[0].why.slice(0, 60)}）` : `（例：${issues[0].why.slice(0, 70)}）`}`
        : `${wfs.length} 个工作流：权限显式最小化、动作钉 SHA、有 timeout、run 里不插值上下文`,
      // 证据按严重度排序并走 evidenceMax：否则最危险的那条可能落在截断窗口之外，
      // 报告里只剩次要项。统一的上限由 makeFinding 负责，不在脚本里自截。
      evidence: JSON.stringify([...issues].sort((x, y) => x.sev.localeCompare(y.sev)).slice(0, 3).map((i) => `${i.sev} ${i.file}: ${i.why}`)),
      evidenceMax: 460,
      locator: issues.length ? { file: issues[0].file } : null,
      nextAction: p1.length
        ? '先收权限：顶层写 permissions 白名单，把不可信上下文改成 env 传值（run 里用 $NAME），再把动作钉到 SHA'
        : issues.length ? '按缺口逐条补：permissions 白名单 + 动作钉 SHA + timeout-minutes + --ignore-scripts' : '',
    });
  }

  /* ---------- CI-2 类型逃逸 ---------- */
  const srcWalk = srcFiles(repo);
  const all = srcWalk.files;
  const srcCov = walkCoverage(srcWalk);
  const escape = [];
  for (const f of all) {
    const src = readFileSync(f, 'utf8');
    const anyc = (src.match(/:\s*any\b|as any\b|<any>/g) || []).length;
    const bang = (src.match(/\w!\.\w|\)![\s.)]/g) || []).length;
    if (anyc + bang >= 3) escape.push({ file: rel(f), any: anyc, bang });
  }
  escape.sort((a, b) => b.any + b.bang - (a.any + a.bang));
  record({
    id: 'CI-2',
    verdict: escape.length ? 'fail' : all.length ? 'pass' : 'not-run',
    severity: 'P3',
    level: 'S',
    reason: all.length ? '' : '仓库里一个源文件都没扫到（不是「没有类型逃逸」，是没有可扫的东西）' + (srcCov ? '；' + srcCov : ''),
    title: escape.length
      ? `${escape.length} 个文件密集使用类型逃逸（最高 ${escape[0].file}：any ${escape[0].any}、非空断言 ${escape[0].bang}）——每一处都是「编译器看不见的真实类型错误」的藏身处`
      : `${all.length} 个源文件里没有成片的 any/非空断言${srcCov ? '（覆盖不全：' + srcCov + '）' : ''}`,
    evidence: JSON.stringify(escape.slice(0, 3)).slice(0, 220),
    nextAction: escape.length ? '把这些位置改成真实类型（如 CollectionEntry<"daily">），别用 any 盖住 string|undefined' : '',
  });

  /* ---------- CI-3 覆盖按层分布 ---------- */
  const testsDir = [opts.tests && join(repo, opts.tests), join(repo, 'tests'), join(repo, 'test'), join(repo, '__tests__')].filter(Boolean).find(existsSync);
  if (!testsDir) {
    record({ id: 'CI-3', verdict: 'not-run', reason: '找不到测试目录（试过 tests/ test/ __tests__/）' });
  } else {
    const testFiles = srcFiles(testsDir);
    const imported = new Set();
    for (const t of testFiles) {
      const src = readFileSync(t, 'utf8');
      for (const m of src.matchAll(/from\s+['"]([^'"]+)['"]/g)) {
        if (m[1].startsWith('.')) {
          const guess = resolve(join(t, '..'), m[1]);
          imported.add(relative(repo, guess).split('\\').join('/'));
          imported.add(relative(repo, guess).split('\\').join('/').replace(/\.(ts|js|mjs)$/, ''));
        }
      }
    }
    const never = all.filter((f) => {
      const r = rel(f).replace(/\.(ts|js|mjs)$/, '');
      return !(imported.has(r) || imported.has(rel(f)));
    });
    const byDir = new Map();
    for (const f of never) {
      const top = rel(f).split('/').slice(0, 2).join('/');
      byDir.set(top, (byDir.get(top) || 0) + 1);
    }
    const astroUntested = all.filter((f) => /\.astro$/.test(f)).length;
    record({
      id: 'CI-3',
      verdict: !all.length ? 'not-run' : never.length > all.length * 0.5 ? 'fail' : 'pass',
      severity: astroUntested && !testFiles.length ? 'P2' : 'P3',
      level: 'S',
      title: !all.length ? '没有源文件可判定覆盖分层（不是覆盖良好）' : never.length > all.length * 0.5
        ? `测试只覆盖到 ${all.length - never.length}/${all.length} 个源文件，未覆盖集中在 ${[...byDir.entries()].sort((a, b) => b[1] - a[1]).slice(0, 2).map(([d, n]) => `${d}(${n})`).join('、')}——历史发现若落在未覆盖层，测试再多也挡不住回归`
        : `${testFiles.length} 个测试文件覆盖 ${all.length - never.length}/${all.length} 个源文件`,
      evidence: JSON.stringify({ testFiles: testFiles.length, never: never.length, byDir: Object.fromEntries(byDir), astroFiles: astroUntested }).slice(0, 240),
      locator: { file: rel(testsDir) },
      nextAction: never.length > all.length * 0.5 ? '把页面层组件抽出成可被测试 import 的纯函数，否则那一层永远在测试之外' : '',
    });
  }

  /* ---------- CI-4 CI 是不是闸门 ---------- */
  const triggers = wfs.map((w) => (/on:[\s\S]{0,80}?\n\s+pull_request/.test(w.text) ? 'PR' : '') + (/push:/.test(w.text) ? ' push' : '') + (/schedule:/.test(w.text) ? ' schedule' : '')).filter(Boolean);
  const hasGh = !!resolveBin('gh');
  // 查分支保护要拿**使用者自己的 gh 登录态**去请求 GitHub，而 owner/repo 是从
  // 被审仓库的 origin 里读出来的：一个恶意仓库可以把 origin 写成攻击者的 slug，
  // 于是这台机器带着你的令牌去问它。所以这条默认不开（第 3 轮）。
  const remoteUrl = gitRo(repo, ['remote', 'get-url', 'origin'], { timeout: 30000 });
  let protection = null;
  if (hasGh && opts['check-protection'] && remoteUrl.ok) {
    const m = /github\.com[:/]([\w.-]+)\/([\w.-]+?)(\.git)?$/.exec(remoteUrl.stdout.trim());
    if (m) {
      // 不带使用者的登录态出网：GH_TOKEN/GITHUB_TOKEN 显式清空，只查公开可匿名读的接口
      const r = run('gh', ['api', `repos/${m[1]}/${m[2]}/branches/main/protection`], { timeout: 60000, env: { GH_TOKEN: '', GITHUB_TOKEN: '', GH_HOST: '' }, cleanEnv: true });
      protection = r.ok ? '已配置' : r.code === 403 ? '无法读取（令牌权限不足）' : '未配置（404）';
    }
  }
  record({
    id: 'CI-4',
    verdict: protection === '未配置（404）' ? 'fail' : protection === null ? 'not-run' : 'pass',
    severity: protection === '未配置（404）' ? 'P2' : '-',
    reason: protection === null ? `分支保护状态没查到（${hasGh ? (opts['check-protection'] ? 'gh 无法读取该仓库或令牌权限不足' : '默认不查：这一步要用使用者自己的 gh 登录态去访问由被审仓库 origin 决定的地址，需显式 --check-protection') : '本机没有 gh'}）：CI 到底是不是闸门，这一项没有结论` : '',
    level: 'J',
    title: protection === '未配置（404）'
      ? `main 无分支保护：CI 只在 push 之后触发，是事后信号而非闸门。格式错误的产物会先发布、事后才报错`
      : `触发方式 ${triggers.join('/') || '未知'}；分支保护未查（${hasGh ? 'gh 在读权限范围内没给结论' : '本机无 gh'}），需人工在托管方侧核对`,
    evidence: JSON.stringify({ triggers, protection, hasGh }).slice(0, 200),
    unblockCommand: hasGh ? '' : '装好 gh 并登录后重跑，或在仓库设置页人工确认分支保护',
    nextAction: protection === '未配置（404）' ? '要么给 main 加 required status check（会改变现有自动化流程，需权衡），要么在文档里如实写明「CI 是事后信号」' : '',
  });

  return ctx.finish();
}

process.exitCode = await safeRun(SCRIPT, USAGE, main, process.argv.slice(2));
