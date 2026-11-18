#!/usr/bin/env node
/**
 * 门禁本身的健康检查：SEC-1..8。
 *
 * 立场：门禁「绿」不是安全，是「它还在工作」的证据。这一组检查审的是门禁自己——
 * 认不出正确凭据形态的扫描器、被调命令一出错就变绿的基线检查、
 * 一处确认就清掉整个文件的放行清单，都让其余结论失去支撑。
 */

import { existsSync, readFileSync, writeFileSync, readdirSync, statSync, rmSync, mkdirSync } from 'node:fs';
import { join, resolve, relative, dirname } from 'node:path';
import {parseArgs, EXIT, finish, usage, makeFindingCtx, safeRun, guardPaths, npmScript, run, resolveBin, resolveNpm, makeWorktree, gitRo} from './lib/harness.mjs';
import { readJsonIfExists } from './lib/jsonl.mjs';
import { assertReadablePath, PathDenied } from './lib/scratch.mjs';
import { gitignoreToRegExp, gitConfigRisks } from './lib/rules.mjs';

const SCRIPT = 'gates.mjs';
const USAGE = 'audit gates --out <dir> --repo <dir> [--scanner <path>] [--gates a,b] [--no-fuzz]';

/** 合成凭据：形态真实、值全为占位。绝不含任何真实凭据。 */
const CREDENTIAL_SHAPES = [
  { kind: 'GitHub classic PAT', sample: 'ghp_' + 'A'.repeat(36) },
  { kind: 'GitHub fine-grained PAT', sample: 'github_pat_' + 'B'.repeat(22) + '_' + 'c'.repeat(59) },
  { kind: 'npm token', sample: 'npm_' + 'D'.repeat(36) },
  { kind: 'AWS access key', sample: 'AKIA' + 'E'.repeat(16) },
  { kind: 'OpenAI-style key', sample: 'sk-' + 'F'.repeat(34) },
  { kind: 'Slack token', sample: 'xoxb-' + 'G'.repeat(24) },
  { kind: 'Google API key', sample: 'AIza' + 'H'.repeat(35) },
  { kind: 'PEM 私钥头', sample: '-----BEGIN OPENSSH ' + 'PRIVATE KEY-----' },
];

function walkFiles(dir, filter, out = [], limit = 900) {
  const skip = new Set(['node_modules', '.git', 'dist', '.next', '.astro', 'build', 'coverage', '.site-audit']);
  for (const name of readdirSync(dir)) {
    if (out.length >= limit || skip.has(name)) continue;
    const full = join(dir, name);
    let st;
    try {
      st = statSync(full);
    } catch {
      continue;
    }
    if (st.isDirectory()) walkFiles(full, filter, out, limit);
    else if (filter(name, full)) out.push(full);
  }
  return out;
}

/** 从源码里抠出正则字面量（够用即可；不做完整 JS 解析）。 */
function extractRegexes(src) {
  const out = [];
  for (const m of src.matchAll(/\/(\\.|[^/\\\n])+\/[gimsuy]*/g)) {
    const lit = m[0];
    try {
      out.push({ literal: lit.slice(0, 90), re: new RegExp(lit.slice(1, lit.lastIndexOf('/')), lit.slice(lit.lastIndexOf('/') + 1).replace(/[gy]/g, '')) });
    } catch {
      /* 非法或含后行的字面量，跳过 */
    }
  }
  return out;
}

/**
 * 从文档里抠凭据形态描述：`tkv2_<22 位>_<59 位>`、`ghp_<36 位>` 这类，
 * 按描述造合成样本。这是「扫描器认不认得本项目自己要用的凭据」的唯一可靠问法——
 * 光有一张固定形态清单，永远不知道文档推荐的那一种是不是恰好不在里面。
 * @param {string} text
 */
function shapesFromDocs(text) {
  const out = [];
  for (const m of String(text).matchAll(/([A-Za-z][A-Za-z0-9_]{1,20})_<(?:\d+|[0-9A-Za-z]*)\s*[位]?\s*>?_[<(]?(\d+)?/g)) {
    const prefix = m[1];
    const second = Number(m[2] || 0);
    const a = /github_pat/i.test(prefix) ? 22 : 32;
    out.push({
      kind: `${prefix}_<…> 形态（文档描述）`,
      sample: `${prefix}_${'a'.repeat(a)}${second ? '_' + 'b'.repeat(Math.min(60, second)) : ''}`,
      source: m[0].slice(0, 60),
    });
  }
  for (const m of String(text).matchAll(/\b(ghp|gho|ghu|ghs|ghr|github_pat|npm|sk|xoxb|AKIA)_(?![<>])/g)) {
    const p = m[1];
    out.push({ kind: `${p}_ 前缀（业界常见形态）`, sample: p + (p === 'github_pat' ? '_' + 'a'.repeat(22) + '_' + 'b'.repeat(59) : 'x'.repeat(36)), source: m[0] });
  }
  const seen = new Set();
  return out.filter((s) => (seen.has(s.sample) ? false : (seen.add(s.sample), true))).slice(0, 12);
}

async function main(argv) {
  let opts;
  try {
    opts = parseArgs(argv, { value: ['out', 'repo', 'scanner', 'gates'], bool: ['no-fuzz'] }).opts;
  } catch (e) {
    return usage(SCRIPT, USAGE, e.message);
  }
  guardPaths(opts, SCRIPT);
  if (!opts.out) return usage(SCRIPT, USAGE, '需要 --out');
  const caps = readJsonIfExists(resolve(opts.out), 'capabilities.json');
  const ctx = makeFindingCtx(SCRIPT, opts, caps);
  const { findings, record } = ctx;
  const repo = opts.repo ? resolve(opts.repo) : null;

  if (!repo || !existsSync(repo)) {
    for (const id of ['SEC-1', 'SEC-2', 'SEC-3', 'SEC-4', 'SEC-5', 'SEC-6', 'SEC-7', 'SEC-8']) {
      record({ id, verdict: 'not-run', reason: '需要 --repo：这一组要执行被审项目自己的门禁' });
    }
    return ctx.finish();
  }

  /* ---------- 找到扫描器与门禁脚本 ---------- */
  const candidates = walkFiles(repo, (n, f) => /\.(mjs|cjs|js|ts)$/.test(n) && /scan|secret|cred|audit|guard|validate|check|lint/i.test(n + f));
  const pkgPath = join(repo, 'package.json');
  const pkg = existsSync(pkgPath) ? JSON.parse(readFileSync(pkgPath, 'utf8')) : { scripts: {} };
  const scripts = pkg.scripts || {};
  if (opts.scanner) {
    try {
      assertReadablePath(resolve(join(repo || process.cwd(), opts.scanner)), { purpose: '--scanner' });
    } catch (e) {
      if (e instanceof PathDenied) { console.error('gates.mjs: ' + e.message); return EXIT.USAGE; }
      throw e;
    }
  }
  const scannerHint = opts.scanner ||
    candidates.find((f) => /scan[-_]?(secret|cred)|secret[-_]?scan/i.test(f)) ||
    '';
  const scannerSrc = scannerHint ? readFileSync(scannerHint, 'utf8') : '';
  const rel = (f) => relative(repo, f).split('\\').join('/');

  /* ---------- 文档声明的凭据形态：从描述里造合成样本 ---------- */
  const docs = walkFiles(repo, (n) => /^(README|readme)\.md$/.test(n) || /^docs[\\/].*\.md$/.test(n))
    .map((f) => readFileSync(f, 'utf8')).join('\n');
  const recommended = shapesFromDocs(docs);

  /* ---------- SEC-1 模式覆盖 vs 实际推荐的形态 ---------- */
  if (!scannerSrc) {
    record({ id: 'SEC-1', verdict: 'not-run', reason: '没找到凭据扫描器（试过文件名含 scan/secret/cred 的脚本）；用 --scanner 指明' });
  } else {
    const regexes = extractRegexes(scannerSrc);
    const missesStd = [];
    const missesRec = [];
    for (const shape of CREDENTIAL_SHAPES) {
      const hit = regexes.some(({ re }) => { re.lastIndex = 0; return re.test('const t = "' + shape.sample + '";'); });
      if (!hit) missesStd.push(shape.kind);
    }
    for (const shape of recommended) {
      const hit = regexes.some(({ re }) => { re.lastIndex = 0; return re.test('const t = "' + shape.sample + '";'); });
      if (!hit) missesRec.push(`${shape.kind} — 合成样本 ${shape.sample.slice(0, 14)}…（文档原文：${shape.source}）`);
    }
    record({
      id: 'SEC-1',
      verdict: missesRec.length || missesStd.length ? 'fail' : 'pass',
      severity: missesRec.length ? 'P1' : missesStd.length ? 'P3' : '-',
      title: missesRec.length
        ? `扫描器认不出本项目文档里写明的凭据形态（${missesRec.length} 种，含：${missesRec[0].split(' — ')[0]}）——「防凭据入库」这道闸对它自己的推荐配置完全无感`
        : missesStd.length
          ? `扫描器覆盖 ${CREDENTIAL_SHAPES.length - missesStd.length}/${CREDENTIAL_SHAPES.length} 种常见凭据形态，缺：${missesStd.join('、')}`
          : `扫描器覆盖全部 ${CREDENTIAL_SHAPES.length} 种常见形态与文档写明的 ${recommended.length} 种形态`,
      evidence: (missesRec[0] || `提取到 ${regexes.length} 条正则；文档声明形态 ${recommended.length} 种、常见形态 ${CREDENTIAL_SHAPES.length} 种全部命中`).slice(0, 200),
      locator: { file: rel(scannerHint) },
      repro: '把每种形态的合成串喂给扫描器提取出的正则，比对文档里写明的那一类',
      nextAction: missesRec.length ? '补齐文档形态的正则并加一条合成凭据测试' : missesStd.length ? '按需补充常见形态；先确认这些形态在本项目里真的会出现' : '',
    });

    /* ---------- SEC-2 自我触发 + 日志回显 ---------- */
    const echoes = /(?:console|process\.stdout)[^\n]{0,60}(?:m\[0\]|match\[0\]|matched)\.slice|slice\(0,\s*1?\d\)/.test(scannerSrc);
    // 在副本里执行被审项目的扫描器：它是项目代码，不该在真实树里就地运行
    const scanTreeDir = makeWorktree(opts.out, repo, 'sec2-worktree');
    const selfRun = run(process.execPath, [join(scanTreeDir, rel(scannerHint))], { cwd: scanTreeDir, timeout: 180000 });
    rmSync(scanTreeDir, { recursive: true, force: true });
    record({
      id: 'SEC-2',
      verdict: echoes || !selfRun.ok ? 'fail' : 'pass',
      severity: echoes ? 'P2' : !selfRun.ok ? 'P3' : '-',
      title: echoes
        ? '扫描器命中时会把匹配片段的一部分打进日志：对长令牌等于公开前缀，且被 CI 日志永久留存'
        : !selfRun.ok
          ? `扫描器在自身仓库上就不通过（exit ${selfRun.code}）——它会把每日发布硬停在自己身上（测试夹具/示例串）`
          : '扫描器不回显片段，且在自己仓库上干净通过',
      evidence: echoes ? '命中片段切片出现在输出语句里' : (selfRun.stdout + selfRun.stderr).replace(/\r?\n/g, ' ').slice(0, 180),
      locator: { file: rel(scannerHint) },
      repro: `node ${rel(scannerHint)} 于仓库根，观察退出码与输出`,
      nextAction: '只报文件与行号；把夹具里的真形态串改成可被自己的排除规则放行的占位',
    });
  }

  /* ---------- SEC-3 忽略清单 vs 实际被跟踪的文件 ---------- */
  const gi = join(repo, '.gitignore');
  if (existsSync(gi) && resolveBin('git')) {
    const patterns = readFileSync(gi, 'utf8')
      .split(/\r?\n/)
      .map((l) => l.trim())
      .filter((l) => l && !l.startsWith('!') && !l.startsWith('#'));
    const tracked = gitRo(repo, ['ls-files'], { timeout: 60000 });
    const violated = [];
    const violations = [];
    // 不能用早退：`return` 会连带跳过 SEC-4..SEC-8，一次 git 缺失就让五项检查静默消失
    const canList = tracked.ok;
    if (!canList) {
      record({ id: 'SEC-3', verdict: 'not-run', reason: 'git ls-files 没给出清单（三种可能：目录不是仓库 / 仓库还没有任何提交 / git 不可执行。不把其中任何一种说成确定的结论）：无法判断忽略规则与实际跟踪文件是否冲突' });
    }
    if (tracked.ok) {
      const files = tracked.stdout.split(/\r?\n/).filter(Boolean);
      for (const p of patterns) {
        // 转换逻辑抽到 gitignoreToRegExp()，由 selftest 单测覆盖：
        // gitignore 允许 `[`、`(`、`+` 作字面量，不转义就 new RegExp 会让整个 gates 崩掉，
        // 那时 7 行 SEC 结论一行都写不进账本，而 exit 1 看起来像「有发现」。
        const conv = gitignoreToRegExp(p);
        if (!conv.ok) {
          violations.push({ pattern: p, note: conv.error });
          continue;
        }
        const hit = files.filter((f) => conv.re.test(f));
        if (hit.length) violated.push({ pattern: p, files: hit.slice(0, 4) });
      }
    }
    if (canList) record({
      id: 'SEC-3',
      verdict: violated.length ? 'fail' : 'pass',
      severity: violated.some((v) => /env|secret|credential|local|\.pem|key/i.test(v.pattern)) ? 'P2' : 'P3',
      title: violated.length
        ? `${violated.length} 条忽略规则对应的路径其实已被跟踪：${violated.map((v) => v.pattern + ' → ' + v.files.length + ' 个').join('；')}`
        : `忽略清单的 ${patterns.length} 条规则与实际被跟踪文件不冲突${violations.length ? `（注意：其中 ${violations.length} 条含无法安全转换的元字符、已被跳过，「不冲突」不代表检查过）` : ''}`,
      evidence: violated.length ? JSON.stringify(violated[0]) : `${patterns.length} 条规则 / ${tracked.ok ? tracked.stdout.split(/\r?\n/).filter(Boolean).length : 0} 个被跟踪文件`,
      locator: { file: '.gitignore' },
      repro: 'git ls-files 与 .gitignore 规则逐条求交',
    });
  } else {
    record({ id: 'SEC-3', verdict: 'not-run', reason: !existsSync(gi) ? '无 .gitignore' : '环境里没有 git' });
  }

  /* ---------- SEC-4 门禁 fail-open 模糊测试 ---------- */
  const gateNames = (opts.gates ? opts.gates.split(',').map((s) => s.trim()) : Object.keys(scripts).filter((s) => /audit|baseline|validate|check|lint|scan|test/i.test(s)))
    .filter((s) => scripts[s] && s !== 'prepare');
  if (!gateNames.length) {
    record({ id: 'SEC-4', verdict: 'not-run', reason: 'package.json 里找不到任何名字像门禁的 script' });
  } else if (opts.noFuzz) {
    record({ id: 'SEC-4', verdict: 'not-run', reason: '显式 --no-fuzz：跳过在副本里破坏门禁输入的行为' });
  } else {
    const broken = [];
    const details = [];
    for (const g of gateNames.slice(0, 6)) {
      // 与 SEC-2 用同一套 makeWorktree。原先这里自己写 cpSync：过滤器只排了三样，
      // 于是 .env 与私钥被原样复制进 --out（正是要给人看、给人转的那个目录），
      // 而且副本落在账本目录内意味着被审脚本只要写 ../findings.jsonl 就能伪造账本。
      const work = makeWorktree(opts.out, repo, 'sec4-' + g);

      const normal = npmScript(work, g);
      const normalOut = String(normal.stdout + normal.stderr).replace(/\r?\n/g, ' ');
      // 只破坏「这个门禁确实会去读」的输入，否则判定没有意义
      const inputs = gateInputs(work, scripts[g]);
      let hit = null;
      for (const f of inputs.slice(0, 3)) {
        const p = join(work, f);
        if (!existsSync(p)) continue;
        // 一次只破坏一个输入，用完还原：累积删除会让后一个输入永远测不到
        const saved = readFileSync(p);
        rmSync(p);
        const sab = npmScript(work, g);
        writeFileSync(p, saved);
        const sabOut = String(sab.stdout + sab.stderr).replace(/\r?\n/g, ' ');
        const claimsClean = /通过|pass|ok|clean|无问题|均在基线内|no vulnerabilit|全部合规/i.test(sabOut);
        const admitsTrouble = /error|失败|异常|not found|ENOENT|无法/i.test(sabOut);
        // 判据：删掉一个「门禁自己去读」的文件后，它既不报错也不变红，还照样自称通过。
        // 这就是 fail-open 的定义——它根本没在消费自己的输入，输出变不变都一样。
        if (sab.ok && sab.code === 0 && claimsClean && !admitsTrouble) {
          hit = { input: f, code: sab.code, sameOutput: sabOut.slice(0, 120) === normalOut.slice(0, 120), out: sabOut.slice(0, 120) };
          break;
        }
      }
      details.push({ gate: g, normalCode: normal.code, inputsChecked: inputs.length, verdict: hit ? 'fail-open' : normal.code === 0 ? 'ok' : 'already-red' });
      if (hit) broken.push({ gate: g, ...hit });
      rmSync(work, { recursive: true, force: true });
    }
    // inputsChecked=0 的门禁从未真正破坏过任何输入：报 pass 等于把「没查」写成「查了没问题」
    const tested = details.filter((d) => d.inputsChecked > 0);
    record({
      id: 'SEC-4',
      verdict: broken.length ? 'fail' : tested.length ? 'pass' : 'not-run',
      severity: broken.length ? 'P1' : '-',
      reason: broken.length || tested.length ? '' : `${details.length} 道门禁都跑通了，但一道都没能确定它自己读取哪些输入文件（gateInputs 返回空）——没破坏任何输入，就没有「fail-open 与否」的结论。这是未跑，不是通过`,
      title: broken.length
        ? `${broken.length} 道门禁 fail-open：${broken.map((b) => `删掉它自己读取的 ${b.input} 后，${b.gate} 既不报错也不变红，仍 exit ${b.code} 并自称通过${b.sameOutput ? '（输出一字未变）' : ''}`).join('；')}`
        : `已测 ${tested.length} 道门禁：破坏其输入后均变红或明确报错（另有 ${details.length - tested.length} 道没能确定输入，未计入）${details.some((d) => d.verdict === 'already-red') ? '（注意：其中有门禁本来就是红的，那是另一个问题）' : ''}`,
      evidence: JSON.stringify(broken.length ? broken : details).slice(0, 240),
      repro: '复制仓库到输出目录 → 逐个删掉门禁自己 readFileSync 的输入 → 再跑该 npm script，看它是红是绿',
      nextAction: broken.length ? '解析被调命令结果后先判有效性（有 error/message 或结构缺键即硬失败）；并把「基线全部消失」当异常而不是提示' : '',
    });
  }

  /* ---------- SEC-5 放行清单语义 ---------- */
  if (scannerSrc) {
    const oneHitPerPattern = /for\s*\(const m of[\s\S]{0,400}?\bbreak;/.test(scannerSrc);
    const allowByLine = /(allowlist|ALLOWLIST|allow)[\s\S]{0,240}(path|file)[\w]*\s*[+:]\s*(line|n)|`\$\{[^}]+\}:\$\{[^}]+line[^}]*\}`/.test(scannerSrc);
    record({
      id: 'SEC-5',
      verdict: oneHitPerPattern && allowByLine ? 'fail' : 'pass',
      severity: oneHitPerPattern && allowByLine ? 'P3' : '-',
      title:
        oneHitPerPattern && allowByLine
          ? '放行清单以 path:line 为键，但扫描器每种模式每文件只报第一处命中——确认那一处等于放行该文件该模式的所有其他命中'
          : '放行清单的粒度与实际报告粒度一致',
      evidence: `每模式每文件只报首处=${oneHitPerPattern}；按行号放行=${allowByLine}`,
      locator: { file: rel(scannerHint) },
      nextAction: '报出全部命中（设上限），或要求文件级放行必须显式写 path:*',
    });
  } else {
    record({ id: 'SEC-5', verdict: 'not-run', reason: '无扫描器源码可判定' });
  }

  /* ---------- SEC-6 依赖告警漂移 ---------- */
  if (ctx.caps && ctx.caps.replay) {
    const r = run(...npmCmd(['audit', '--json']), { cwd: repo, timeout: 240000 });
    const baselineFile = walkFiles(repo, (n) => /audit[-_]baseline|vulnerabilit|advisory/i.test(n)).find((f) => f.endsWith('.json'));
    const netFail = /ENOTFOUND|EAI_AGAIN|ETIMEDOUT|ECONNREFUSED|ECONNRESET|EPIPE|socket hang up|ERR_SOCKET|network|unable to verify|self[- ]signed|self signed|401 |403 |registry/i.test(String(r.stderr) + String(r.stdout));
    let cur = null;
    try {
      cur = JSON.parse(String(r.stdout || '{}'));
    } catch {
      cur = null;
    }
    if (!cur) {
      record({ id: 'SEC-6', verdict: 'not-run', reason: `npm audit 输出不是有效 JSON（exit ${r.code}），无从判定告警数` });
    } else if (netFail && !cur.vulnerabilities) {
      record({ id: 'SEC-6', verdict: 'not-run', reason: '注册表不可达（离线或被墙）：本轮无告警计数，不等于零告警' });
    } else if (!cur.vulnerabilities) {
      record({
        id: 'SEC-6',
        verdict: 'fail',
        severity: 'P3',
        title: `npm audit 返回了合法 JSON 但没有 vulnerabilities 字段（exit ${r.code}）——若项目自己的门禁也这样解读，这次失败会被当成「零告警」`,
        evidence: String(r.stdout).replace(/\r?\n/g, ' ').slice(0, 160),
      });
    } else {
        const count = Object.keys(cur.vulnerabilities).length;
        const crit = Object.values(cur.vulnerabilities).filter((v) => /critical|high/.test(v.severity || ''));
        let baseCount = null;
        if (baselineFile) {
          try {
            const bj = JSON.parse(readFileSync(baselineFile, 'utf8'));
            baseCount = Array.isArray(bj.entries) ? bj.entries.length : bj.count ?? null;
          } catch { /* 让下面的措辞保守 */ }
        }
        record({
          id: 'SEC-6',
          verdict: baseCount !== null && count > baseCount ? 'fail' : 'pass',
          severity: baseCount !== null && count > baseCount ? 'P2' : '-',
          title:
            baseCount !== null && count > baseCount
              ? `依赖告警数从基线记录的 ${baseCount} 涨到 ${count}（含 ${crit.length} 条 high/critical），基线未随之更新`
              : `当前 ${count} 条依赖告警${baseCount !== null ? `，基线记录 ${baseCount} 条` : ''}；是否在产物里可达需人判定`,
          evidence: `high/critical ${crit.length} 条；基线文件 ${baselineFile ? rel(baselineFile) : '无'}`,
          nextAction: baseCount !== null && count > baseCount ? '逐条重做暴露面分析并更新基线，别只是加行' : '由人确认受影响特性在产物里是否可达（本工具只给证据）',
        });
    }
  } else {
    record({ id: 'SEC-6', verdict: 'not-run', reason: '需要可用的 npm 与被审项目（replay 能力）' });
  }

  /* ---------- SEC-7 lockfile 孤儿 + engines ---------- */
  const lockPath = join(repo, 'package-lock.json');
  if (existsSync(pkgPath) && existsSync(lockPath)) {
    const lock = JSON.parse(readFileSync(lockPath, 'utf8'));
    const pkgs = lock.packages || {};
    const declared = new Set([...Object.keys(pkg.dependencies || {}), ...Object.keys(pkg.devDependencies || {})]);
    const reachable = new Set();
    const queue = [...declared];
    while (queue.length) {
      const n = queue.shift();
      for (const key of Object.keys(pkgs)) {
        if (!key.endsWith('node_modules/' + n)) continue;
        if (reachable.has(key)) continue;
        reachable.add(key);
        for (const d of Object.keys(pkgs[key].dependencies || {})) queue.push(d);
      }
    }
    const orphans = Object.keys(pkgs).filter((k) => k && k !== '' && !k.startsWith('node_modules/.') && !reachable.has(k));
    const engines = pkg.engines && pkg.engines.node;
    const majors = (engines || '').match(/\d+/g);
    const want = majors ? Number(majors[majors.length - 1]) : null;
    const have = Number(process.versions.node.split('.')[0]);
    const tsLike = walkFiles(repo, (n, f) => /\.(test|spec)\.(mjs|js|ts)$/.test(n)).slice(0, 40)
      .some((f) => /from '[^']*\.ts'|import\([^)]*\.ts/.test(readFileSync(f, 'utf8')));
    record({
      id: 'SEC-7',
      verdict: orphans.length > 25 || (tsLike && want !== null && have < want) ? 'fail' : 'pass',
      severity: 'P3',
      title:
        orphans.length > 25
          ? `lockfile 里有 ${orphans.length} 个从 package.json 出发不可达的条目（移除依赖后未重新生成 lock）`
          : tsLike && want !== null && have < want
            ? `测试直接 import .ts，需要 node ≥ ${want}，当前 ${have}：engines 与实际要求不符`
            : `lockfile ${orphans.length} 个不可达条目（正常传递范围），engines ${engines || '未声明'} / 实际 node ${have}`,
      evidence: `声明 ${declared.size} 个直接依赖，lock 条目 ${Object.keys(pkgs).length}，不可达 ${orphans.length}`,
      locator: { file: 'package-lock.json' },
    });
  } else {
    record({ id: 'SEC-7', verdict: 'not-run', reason: '没有 package-lock.json，无法算可达闭包' });
  }

  /* ---------- SEC-8 令牌作用域 / 内嵌凭据 / 可执行 git 配置 ---------- */
  // .git/config 里的这几类键会在**下一次任意 git 操作**时执行命令：
  // `ext::` 远端、`credential.helper=!cmd`、`filter.*.smudge/clean`、`diff.*.textconv`、
  // `core.hooksPath` 指到工作树里、`include.path` 从别处再拉一段配置。
  // 只查内嵌凭据和 insteadOf 的话，克隆一个恶意仓库再跑 `git status` 就等于执行它的代码。
  const cfg = join(repo, '.git', 'config');
  const cfgText = existsSync(cfg) ? readFileSync(cfg, 'utf8') : '';
  const risks = cfgText ? gitConfigRisks(cfgText) : [];
  const embedded = risks.some((r) => r.k === 'embedded');
  let hooksNote = '非 git 仓库，未查钩子';
  if (existsSync(join(repo, '.git'))) {
    const ls = gitRo(repo, ['ls-files'], { timeout: 60000 });
    hooksNote = ls.ok && /hook/i.test(ls.stdout) ? '有钩子被仓库跟踪（会随克隆进入发布机）' : '无被跟踪的钩子';
  }
  // 不再调用 `gh auth token`：一个分发给别人的插件不该主动去取使用者的凭据，
  // 即便只是用来判断 scope。令牌作用域必须人在提供方侧核对。
  const ghToken = { ok: false };
  const hard = risks.filter((r) => r.exec);
  record({
    id: 'SEC-8',
    verdict: risks.length ? 'fail' : existsSync(cfg) ? 'pass' : 'not-run',
    severity: hard.length ? 'P1' : embedded ? 'P2' : risks.length ? 'P2' : '-',
    reason: existsSync(cfg) ? '' : '该树里没有 .git/config：内嵌凭据与可执行 git 配置都无从判断',
    title: hard.length
      ? `.git/config 里有 ${hard.length} 处会在下次 git 操作时执行命令的配置（${hard.map((r) => r.k).join('、')}）——克隆/打开这个仓库本身就是执行入口`
      : embedded
        ? 'git remote 里内嵌了凭据形态的串（会进 .git/config，也可能进日志）'
        : risks.length
          ? `.git/config 里有需人工确认的项：${risks.map((r) => r.k).join('、')}`
          : `远端配置干净（无内嵌凭据、无 insteadOf/ext::/hooksPath/textconv）；${hooksNote}${ghToken.ok ? '；令牌 scope 需人在提供方侧核对' : '；无 gh，未查 scope'}`,
    evidence: JSON.stringify(risks.length ? risks : { cfg: 'clean', hooksNote }).slice(0, 240),
    locator: { file: '.git/config' },
    nextAction: hard.length
      ? '删掉这些键（git config --unset-all），并把该仓库当作「已执行过任意代码」来复盘；日常操作 git 时带 GIT_CONFIG_NOSYSTEM=1'
      : embedded ? '改用凭据助手或 fine-grained 单仓令牌，并确认历史提交里没留下它' : '',
  });

  return ctx.finish();
}


/**
 * 猜出一个门禁 script 真正会读哪些输入文件：从 npm 命令里找它执行的本地脚本，
 * 再顺着本地 import 走一层，收集 readFileSync/existsSync 里的文件名字面量。
 * 目的只有一个——只破坏「与这道门禁有关的」输入，否则「仍 exit 0」毫无意义。
 */
function gateInputs(work, command) {
  const localScripts = new Set();
  for (const m of String(command).matchAll(/(?:node|npx|deno run|python3?)\s+((?:[\w.-]+\/)*[\w.-]+\.(?:mjs|cjs|js|ts|py))/g)) {
    localScripts.add(m[1]);
  }
  const expand = new Set(localScripts);
  // 一层传递：门禁脚本里以字符串形式引用的本地脚本（如 execFileSync 的目标）也要看
  const collect = (abs) => {
    if (!existsSync(abs)) return;
    const src = readFileSync(abs, 'utf8');
    for (const m of src.matchAll(/['"]((?:\.{0,2}[\\/][\w.-]+)+\.(?:mjs|cjs|js|ts))['"]|['"]([\w.-]+\.(?:mjs|cjs|js))['"]/g)) {
      const ref = m[1] || m[2];
      const resolved = relative(work, resolve(dirname(abs), ref)).split('\\').join('/');
      if (!resolved.startsWith('..') && existsSync(join(work, resolved))) expand.add(resolved);
    }
    return src;
  };
  for (const f of [...localScripts]) collect(join(work, f));
  for (const f of [...expand]) if (f !== 'package.json') collect(join(work, f));
  for (const f of expand) {
    const abs = join(work, f);
    if (!existsSync(abs)) continue;
    const src = readFileSync(abs, 'utf8');
    for (const m of src.matchAll(/from\s+['"](\.[^'"]+)['"]/g)) {
      const rel = relative(work, resolve(dirname(abs), m[1])).split('\\').join('/');
      if (existsSync(join(work, rel))) expand.add(rel);
      else if (existsSync(join(work, rel + '.js'))) expand.add(rel + '.js');
    }
  }
  const names = new Set();
  for (const f of expand) {
    const abs = join(work, f);
    if (!existsSync(abs)) continue;
    const src = readFileSync(abs, 'utf8');
    for (const m of src.matchAll(/(?:readFileSync|existsSync|open|statSync)\s*\(\s*[^)]*['"]((?:[\w.-]+[/\\])*[\w.-]+\.(?:json|lock|ya?ml|toml|txt|csv))['"]/g)) names.add(m[1].replace(/\\/g, '/'));
    for (const m of src.matchAll(/['"]((?:package-lock|pnpm-lock\.yaml|yarn\.lock|bun\.lockb)[\w.-]*)['"]/g)) names.add(m[1]);
  }
  const existing = [];
  for (const n of names) {
    // 带目录的字面量以前根本匹配不上（正则只吃 [\w.-]+，不含 /），于是 gateInputs 返回空数组、
    // SEC-4 一个输入都没破坏，却照样打印「已测 N 道门禁：破坏其输入后均变红」。
    if (n.startsWith('/') || /(^|\/)\.\.(\/|$)/.test(n) || /^[A-Za-z]:/.test(n)) continue;
    const base = n.split('/').pop();
    if (existsSync(join(work, n))) existing.push(n);
    else {
      const found = walkFiles(work, (f) => f === base, [], 400);
      const pick = found.find((f) => relative(work, f).split('\\').join('/').endsWith(n)) || found[0];
      if (pick) existing.push(relative(work, pick).split('\\').join('/'));
    }
  }
  return [...new Set(existing)].slice(0, 4);
}
function npmCmd(args) {
  const n = resolveNpm();
  if (!n) return ['npm', args];
  return [n.cmd, [...n.prefix, ...args]];
}

process.exitCode = await safeRun(SCRIPT, USAGE, main, process.argv.slice(2));
