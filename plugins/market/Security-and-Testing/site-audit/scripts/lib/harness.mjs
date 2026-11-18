/**
 * 检测脚本的公共骨架：finding 记录（自动补 round/mode/注册表元数据）、
 * npm/子进程调用（带 ok 标志，出错绝不静默）。
 */

import { resolve, join, dirname, sep } from 'node:path';
import { fileURLToPath } from 'node:url';
import { tmpdir } from 'node:os';
import { rmSync, mkdirSync, readdirSync, lstatSync, copyFileSync, mkdtempSync } from 'node:fs';
import { parseArgs, EXIT, finish, usage, run, resolveNpm, resolveBin, targetHash, nowIso } from './tools.mjs';
import { readJsonIfExists, appendFindings, makeFinding } from './jsonl.mjs';
import { byId, applicable } from './registry.mjs';
import { assertReadablePath, PathDenied } from './scratch.mjs';
import { outDirProblems } from './outdir.mjs';
import { openRoundNetState } from './net.mjs';

export { parseArgs, EXIT, finish, usage, run, resolveNpm, resolveBin, targetHash, nowIso, readJsonIfExists };

/**
 * 所有脚本共用的入口守卫：--out / --repo / --dist 三个路径都必须过私有区黑名单。
 * 直接在库里 process.exit(4)——因为「每个脚本自己记得调用」正是会失效的那种约定，
 * 而失效的后果是把使用者的 ~/.ssh 或模型记忆目录读进账本。
 */
export function guardPaths(opts, scriptName) {
  for (const problem of outDirProblems(opts, import.meta.url)) {
    console.error(`${scriptName}: --out 位置不安全——${problem}。请把 --out 指向被审项目与插件之外的独立目录。`);
    process.exit(EXIT.USAGE);
  }
  for (const key of ['out', 'repo', 'dist', 'scanner', 'tests', 'validator', 'renderer', 'from']) {
    if (!opts[key]) continue;
    try {
      // 相对值按被审仓库解析（--tests/--renderer 这些本来就是仓库内相对路径），
      // 否则会拿审查者的 cwd 去判一个项目内的路径，误拒或漏判。
      assertReadablePath(resolve(opts.repo || process.cwd(), opts[key]), { purpose: `--${key}` });
    } catch (e) {
      if (e instanceof PathDenied) {
        console.error(`${scriptName}: ${e.message}`);
        process.exit(EXIT.USAGE);
      }
      throw e;
    }
  }
}

/**
 * 网络前置条件：必须已经 probe 开轮，且黑盒模式下必须有授权记录。
 * 返回 { ok, reason }；调用方据此把相关检查记成 not-run 而不是硬跑。
 */
/**
 * 检测脚本的统一外壳。没有它时，脚本一崩 = 一行都不写 = 与「有发现」(exit 1) 无法区分，
 * 而崩溃时的栈回溯还会把绝对路径打进日志。实测过两次：SEC-3 的病态 gitignore 规则、
 * 以及一个漏掉的 import 造成 ReferenceError——两者都是「静默地什么都没查」。
 */
export async function safeRun(script, usageLine, mainFn, argv) {
  // Ctrl-C / 被 kill 也要收副本：审计过程会在临时目录留下被审项目的拷贝，
  // 只挂在正常路径上等于「使用者中断一次就漏一份」。
  bindWorktreeCleanup();
  try {
    const code = await mainFn(argv);
    cleanWorktrees();
    return code;
  } catch (e) {
    cleanWorktrees();
    console.error(`${script}: 崩溃，本轮结果不完整（${String((e && e.message) || e).slice(0, 160)}）`);
    let flushed = 0;
    for (const ctx of LIVE_CTX) {
      try {
        if (ctx.outDir && ctx.findings.length) {
          appendFindings(ctx.outDir, ctx.findings);
          flushed += ctx.findings.length;
        }
      } catch { /* 落盘失败也不能再抛 */ }
    }
    console.error(`${script}: 已尽力落盘 ${flushed} 行；请以 exit 3 视之（未跑成 ≠ 通过），修复后重跑`);
    void usageLine;
    return EXIT.UNUSABLE;
  }
}

export function netPrecondition(opts, capsDoc) {
  if (!capsDoc) return { ok: false, reason: '没有 capabilities.json：先跑 probe 开轮，否则授权与预算都无从校验' };
  if (!(capsDoc.capabilities && capsDoc.capabilities.net)) return { ok: false, reason: 'probe 判定目标不可达' };
  if (capsDoc.mode === 'blackbox' && !capsDoc.authorization) {
    return { ok: false, reason: '黑盒模式缺少授权记录：probe 必须带 --authorized' };
  }
  return { ok: true, reason: '' };
}

/**
 * 反「空样本假通过」：没有可分析的对象时必须记 not-run，绝不能记 pass。
 * 这是本工具最容易犯、也最危险的错——「0 页产物，结构断言全通过」读起来像通过。
 * @param {object} ctx makeFindingCtx 的返回值
 * @param {number} count 实际取到的样本数
 * @param {string[]} ids 受影响的检查 id
 * @param {string} reason 样本为 0 时的原因
 * @returns {boolean} 是否有样本可继续
 */
export function requireSample(ctx, count, ids, reason) {
  if (count > 0) return true;
  for (const id of ids) ctx.record({ id, verdict: 'not-run', reason });
  return false;
}

/**
 * @param {string} script 脚本名，写进 finding 便于溯源
 * @param {object} opts 已解析 argv
 * @param {object|null} caps capabilities.json 内容
 */
const LIVE_CTX = new Set();

export function makeFindingCtx(script, opts, caps) {
  const findings = [];
  const seen = new Set();
  const meta = (caps && caps.capabilities) || {};
  const st = caps || (opts.out ? readJsonIfExists(resolve(opts.out), 'state.json') : null);
  const base = {
    round: (st && Number(st.round)) || Number(opts.round) || 1,
    runId: (st && st.lastRunId) || 'unopened',
    mode: (st && st.mode) || opts.mode || (opts.repo || meta.repo ? 'whitebox' : 'blackbox'),
    targetHash: (st && st.targetHash) || (opts.url ? targetHash(opts.url) : ''),
    authorizedBy: (caps && caps.authorization) || (st && st.authorization) || '',
    script,
  };
  const stateRows = [];
  const outOfScope = [];
  const inScope = new Set(applicable(base.mode));
  const api = {
    findings,
    script,
    outDir: opts.out ? resolve(opts.out) : null,
    base,
    caps: meta,
    /**
     * 本轮共享的网络计数器。4 个脚本各自 new 一个 HttpBudget 时，
     * 「本轮 60 次预算」「250ms 间隔」「连续 403 熔断」全都只在单个进程内成立——
     * 对被审站点等于没有约束，对恶意站点等于白送一次假通过。
     */
    roundNet() {
      if (api._net === undefined) api._net = openRoundNetState(api.outDir, base.round);
      return api._net;
    },
    /** 记一行。pass/fail/not-run 都要有；not-run 必须带 reason。同 id 后写覆盖前写。 */
    record(row) {
      // 模式不适用的检查不许进账本：黑盒轮里混进白盒 id 会让「入账数 > 适用数」，
      // 完备性闸门的分母就失真了。但也不能静默丢——记进 outOfScope 并在收尾打印。
      if (!inScope.has(row.id)) {
        outOfScope.push(row.id);
        return null;
      }
      const reg = byId(row.id);
      const merged = makeFinding({
        ...base,
        ts: nowIso(),
        level: reg ? reg.lvl : 'M',
        title: (reg ? reg.t : row.id) + (row.titleSuffix || ''),
        severity: '-',
        verdict: 'pass',
        evidence: '',
        locator: null,
        repro: '',
        reason: '',
        unblockCommand: reg ? reg.unblock : '',
        nextAction: '',
        lastVerified: null,
        supersedes: null,
        ...row,
      });
      if (seen.has(merged.id)) {
        const i = findings.findIndex((f) => f.id === merged.id);
        findings.splice(i, 1, merged);
      } else {
        seen.add(merged.id);
        findings.push(merged);
      }
      return merged;
    },
    /** 只读检查：不记 finding，但把一次调用失败暴露出来（fail-open 的对称面）。 */
    note(text) {
      stateRows.push(text);
    },
    states: stateRows,
    outOfScope,
    /** 落盘后收尾。任何脚本的结束都必须走这里——否则结论只存在于 stdout，
     *  账本看不见，下一轮就无法结转，「无声放弃」又回来了。 */
    finish() {
      cleanWorktrees();
      // 不再跑第二遍 makeFinding：record() 里已经规范化并脱敏过了。
      // 重复调用会让作者声明的 evidenceMax 被重新按默认 200 截掉（本轮实测），
      // 并对已经打过 [REDACTED] 的文本二次脱敏——两次加工同一份数据，一定会出错。
      if (this.outDir && findings.length) appendFindings(this.outDir, findings);
      // 红线用掉了多少必须看得见：预算与熔断只在 net-round.json 里，不打印就等于
      // 「约束存在但没人知道它有没有生效」。
      const net = netRoundSummary(this.outDir, base.round);
      if (net) console.log(net);
      if (stateRows.length) console.log(`脚本自报的观测：${stateRows.map((r) => (typeof r === 'string' ? r : JSON.stringify(r))).join(' ')}`);
      if (outOfScope.length) {
        const uniq = [...new Set(outOfScope)];
        console.log('');
        console.log(`（本轮为 ${base.mode} 模式，以下 ${uniq.length} 项不适用、未入账：${uniq.join(', ')}）`);
      }
      return finish(script, findings);
    },
  };
  LIVE_CTX.add(api);
  return api;
}

/**
 * 本轮网络账本的一行摘要（读 <OUT>/net-round.json）。
 * 红线若从不被打印，就等于没人知道它有没有生效。
 * @param {string|null} outDir
 * @param {number} round
 */
function netRoundSummary(outDir, round) {
  if (!outDir) return '';
  const doc = readJsonIfExists(resolve(outDir), 'net-round.json');
  if (!doc || Number(doc.round) !== Number(round)) return '';
  const p = doc.pools || {};
  const t = p.target || {};
  const e = p.external || {};
  const tripped = Object.entries(doc.hosts || {}).filter(([, c]) => (c.n429 || 0) >= 2 || (c.n403 || 0) >= 3).map(([h]) => h);
  return `网络账本 本轮 ${round}：目标站 ${t.used || 0}/${t.cap || 40} · 外链 ${e.used || 0}/${e.cap || 20} · 内网/元数据拒绝 ${doc.deniedPrivate || 0} · 带凭据链接拒绝 ${doc.credUrls || 0}${tripped.length ? ` · 已熔断主机 ${tripped.length}` : ''}`;
}

/**
 * 造一份被审项目的副本，供「需要执行项目代码」的检查使用。
 * 落在系统临时目录（不是 --out）且随机命名，副本里的代码猜不到账本位置；
 * 排除依赖/版本库/构建产物，跳过符号链接与 .env、.pem、id_rsa、.local 这类凭据形态文件。
 * 正常清理由 safeRun/ctx.finish/信号钩子负责；被硬杀留下的由 probe 开局补收。
 */
/**
 * 副本必须落在系统临时目录，**不能**落在 --out 里。
 * 落在 --out 时，被审项目的脚本（cwd = 副本）只要写 `../findings.jsonl`
 * 就能伪造整本账本、把 ledger verify 骗成 exit 0（对抗性审查实测成功）。
 * 临时目录名随机，副本内的代码无从猜出账本位置。
 */
const OPEN_TREES = new Set();

export function makeWorktree(outDir, repo, name) {
  const dst = mkdtempSync(join(tmpdir(), 'site-audit-' + name.replace(/[^\w.-]+/g, '_') + '-'));
  rmSync(dst, { recursive: true, force: true });
  mkdirSync(dst, { recursive: true });
  const SKIP_DIRS = new Set(['node_modules', '.git', 'dist', '.site-audit', '.next', '.astro', 'coverage', 'build']);
  const SKIP_RE = /(^\.env(\..+)?$)|(\.pem$)|(^id_(rsa|ed25519|ecdsa|dsa)$)|(\.local$)|(^npm-debug\.log)/i;
  const walk = (src, rel) => {
    let entries = [];
    try {
      entries = readdirSync(src, { withFileTypes: true });
    } catch {
      return;
    }
    for (const entry of entries) {
      if (SKIP_DIRS.has(entry.name) || SKIP_RE.test(entry.name)) continue;
      const from = join(src, entry.name);
      const to = join(dst, rel, entry.name);
      let st = null;
      try {
        st = lstatSync(from);
      } catch {
        continue;
      }
      if (st.isSymbolicLink()) continue;
      if (entry.isDirectory()) {
        mkdirSync(to, { recursive: true });
        walk(from, join(rel, entry.name));
      } else if (entry.isFile()) {
        mkdirSync(dirname(to), { recursive: true });
        try {
          copyFileSync(from, to);
        } catch {
          /* 单个文件读不了不该让整轮审查失败；该项会在样本数上体现出来 */
        }
      }
    }
  };
  walk(resolve(repo), '');
  OPEN_TREES.add(dst);
  return dst;
}

/** 收尾清理所有临时副本：崩溃/中断路径也要清，否则仓库副本会留在产物目录里被顺手分享出去。 */
export function cleanWorktrees() {
  for (const d of OPEN_TREES) {
    try {
      rmSync(d, { recursive: true, force: true });
    } catch { /* 清不掉就不清，不影响结论 */ }
  }
  OPEN_TREES.clear();
}

/**
 * Ctrl-C / 被 kill / 正常退出都要把副本清掉。
 *
 * 只做「正常路径 + 抛异常」两条是不够的：副本里含被审项目的源码，
 * 使用者按一次 Ctrl-C 就在 %TMP% 里留下一份没人知道的拷贝（第 3 轮实测残留）。
 * SIGINT/SIGTERM 里清完再以原语义退出码结束；exit 兜底处理没挂上信号的平台。
 */
let signalsBound = false;
export function bindWorktreeCleanup() {
  if (signalsBound) return;
  signalsBound = true;
  for (const sig of ['SIGINT', 'SIGTERM', 'SIGHUP']) {
    try {
      process.on(sig, () => {
        cleanWorktrees();
        process.exit(sig === 'SIGINT' ? 130 : 143);
      });
    } catch { /* 平台不支持该信号 */ }
  }
  process.on('exit', () => { try { cleanWorktrees(); } catch { /* 退出路径上尽力而为 */ } });
}

/**
 * 扫掉历史残留的副本：按名字前缀认自己的东西，只删 6 小时前的。
 * 上一次运行被硬杀（kill -9 / 断电）时没有任何钩子能跑，只能靠下次开局补收。
 */
export function sweepStaleWorktrees(maxAgeMs = 6 * 3600 * 1000) {
  const removed = [];
  const root = tmpdir();
  let names = [];
  try { names = readdirSync(root); } catch { return { removed, root, failed: true }; }
  const now = Date.now();
  for (const n of names) {
    if (!n.startsWith('site-audit-')) continue;
    const p = join(root, n);
    try {
      const st = lstatSync(p);
      if (!st.isDirectory()) continue;
      if (OPEN_TREES.has(p) || now - st.mtimeMs < maxAgeMs) continue;
      rmSync(p, { recursive: true, force: true });
      removed.push(n);
    } catch { /* 不属于自己的东西或正被占用：不动 */ }
  }
  return { removed, root, failed: false };
}

/** 跑被审项目自己的 npm script。返回结构化结果，调用方必须处理 ok=false。 */
export function npmScript(cwd, script, extraArgs = []) {
  const npm = resolveNpm();
  if (!npm) return { ok: false, code: -1, stdout: '', stderr: '未找到 npm', how: 'none' };
  const r = run(npm.cmd, [...npm.prefix, 'run', script, ...extraArgs], {
    cwd: resolve(cwd),
    shell: npm.shell,
    timeout: 300000,
  });
  return { ok: r.ok, code: r.ok ? 0 : r.code, stdout: r.stdout, stderr: r.stderr, how: npm.how };
}

/** 用当前 node 直接跑被审项目里的一个脚本文件。 */
export function nodeScript(cwd, relFile, args = []) {
  const r = run(process.execPath, [join(resolve(cwd), relFile), ...args], {
    cwd: resolve(cwd),
    timeout: 180000,
  });
  return { ok: r.ok, code: r.ok ? 0 : r.code, stdout: r.stdout, stderr: r.stderr };
}

/**
 * 只读地跑被审仓库的 git。
 *
 * 为什么要包一层：这些命令读的是被审项目自己的 `.git/config`，而那个文件里的
 * `core.fsmonitor` / `ext::` 远端 / `credential.helper=!cmd` 会让一次「只是查历史」
 * 的命令在审查机上执行程序，或者把**使用者的凭据**发给被审仓库指定的第三方主机
 * （`git ls-remote` 会调用凭据助手）。SEC-8 负责把这些键报出来，这一层负责让它们
 * 至少在审查过程中点不着：不加载系统级配置、不弹交互、不调凭据助手、
 * 不走 ext:: 传输、不写可选锁（共享工作树里也不留锁文件）。
 */
export function gitRo(repo, subArgs, opt = {}) {
  return run('git', [
    '--no-optional-locks',
    '-c', 'credential.helper=',
    '-c', 'core.fsmonitor=false',
    '-c', 'protocol.ext.allow=never',
    '-c', 'core.askPass=true',
    ...(repo ? ['-C', resolve(repo)] : []),
    ...subArgs,
  ], {
    timeout: opt.timeout ?? 60000,
    env: { GIT_CONFIG_NOSYSTEM: '1', GIT_TERMINAL_PROMPT: '0', GIT_PAGER: 'cat', ...(opt.env || {}) },
  });
}
