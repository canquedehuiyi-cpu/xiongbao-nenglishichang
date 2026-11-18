#!/usr/bin/env node
/**
 * 回归断言：这一轮自审里修掉的缺陷，每一项都要有对应断言钉住。
 *
 * 为什么单独立一个文件：selftest 的 50 项断言全在测「检测逻辑抓不抓得住夹具里植入的缺陷」，
 * 但这一轮修的是工具自身的可靠性（崩溃会吞掉整组结论、参数解析错一个字母就静默失效、
 * 脱敏没接上、路径黑名单形同虚设）。这类缺陷不会让某项检查变红，只会让整套工具「什么都不说」。
 */

import { existsSync, mkdirSync, readFileSync, writeFileSync, rmSync, cpSync, statSync, utimesSync } from 'node:fs';
import { join } from 'node:path';
import { spawnSync } from 'node:child_process';
import { parseArgs, redact } from '../scripts/lib/tools.mjs';
import { assertReadablePath, PathDenied } from '../scripts/lib/scratch.mjs';
import { gitignoreToRegExp, sameHostAs, contrastRatio, parseColor } from '../scripts/lib/rules.mjs';
import { makeFinding, latestByVerdict, readLedger, appendFindings } from '../scripts/lib/jsonl.mjs';
import { makeFindingCtx, safeRun } from '../scripts/lib/harness.mjs';
import { inspectPackage, zipEntryNames } from '../scripts/selfcheck.mjs';
import { zipDir, writeZip } from '../scripts/lib/zipwrite.mjs';
import { homedir, tmpdir } from 'node:os';

const NL = String.fromCharCode(10);

/**
 * 造一个条目名"原样写入"的最小 ZIP（空文件、stored、CRC=0）。
 * 只用于验证闸门对**非法条目名**的反应——zipDir 会拒绝生成这种包，所以必须手工拼。
 * 闸门只解析中央目录里的名字，不校验 CRC，因此这个假包足够触发判据。
 */
function syntheticZip(path, names) {
  const locals = [];
  const cents = [];
  let off = 0;
  for (const n of names) {
    const nb = Buffer.from(n, 'utf8');
    const lh = Buffer.alloc(30);
    lh.writeUInt32LE(0x04034b50, 0);
    lh.writeUInt16LE(20, 4);
    lh.writeUInt16LE(0, 8);
    lh.writeUInt16LE(nb.length, 26);
    locals.push(lh, nb);
    const ch = Buffer.alloc(46);
    ch.writeUInt32LE(0x02014b50, 0);
    ch.writeUInt16LE(20, 4);
    ch.writeUInt16LE(20, 6);
    ch.writeUInt16LE(nb.length, 28);
    ch.writeUInt32LE(off, 42);
    cents.push(ch, nb);
    off += 30 + nb.length;
  }
  const cd = Buffer.concat(cents);
  const eo = Buffer.alloc(22);
  eo.writeUInt32LE(0x06054b50, 0);
  eo.writeUInt16LE(names.length, 8);
  eo.writeUInt16LE(names.length, 10);
  eo.writeUInt32LE(cd.length, 12);
  eo.writeUInt32LE(off, 16);
  writeFileSync(path, Buffer.concat([Buffer.concat(locals), cd, eo]));
}

function runNode(exe, args) {
  const r = spawnSync(exe, args, { encoding: 'utf8', timeout: 600000 });
  return { code: r.status, out: String(r.stdout || '') + String(r.stderr || '') };
}

export async function regressionChecks(ROOT, tmp, push) {
  const AUDIT = join(ROOT, 'bin', 'audit.mjs');
  const FIX = join(ROOT, 'fixtures', 'synthetic-site');

  /* ---- 1. argv：kebab 与 camel 必须同时可用 ---- */
  const kb = parseArgs(['--probe-links', '--no-build', '--max-bytes=10'], {
    bool: ['probe-links', 'no-build'],
    value: ['max-bytes'],
  }).opts;
  push('回归: kebab→camel 双键（否则参数静默失效）',
    kb.probeLinks === true && kb['probe-links'] === true && kb.noBuild === true && kb.maxBytes === '10',
    JSON.stringify(kb));

  /* ---- 1b. makeWorktree 的两半职责（放在最前面：这条被改坏时，后面的端到端会整套崩，
   *         崩溃本身不是证据，具名断言必须抢在崩之前打印出来） ---- */
  {
    const { makeWorktree } = await import('../scripts/lib/harness.mjs');
    const { relative, resolve: res } = await import('node:path');
    const outDir = join(tmp, 'mw-out');
    const srcRepo = join(tmp, 'mw-repo');
    rmSync(outDir, { recursive: true, force: true });
    rmSync(srcRepo, { recursive: true, force: true });
    mkdirSync(outDir, { recursive: true });
    mkdirSync(join(srcRepo, 'sub'), { recursive: true });
    writeFileSync(join(srcRepo, 'index.html'), '<html>正文</html>', 'utf8');
    writeFileSync(join(srcRepo, '.env'), 'TOKEN=' + 'x'.repeat(20), 'utf8');
    writeFileSync(join(srcRepo, 'id_ed25519'), 'PRIVATE-KEY', 'utf8');
    writeFileSync(join(srcRepo, 'sub', 'keep.md'), '# keep', 'utf8');
    const dst = makeWorktree(outDir, srcRepo, 'mw-probe');
    const insideOut = !relative(res(outDir), res(dst)).startsWith('..');
    push('对抗: makeWorktree 的副本绝不落在 --out 里（--out 是账本目录，也是会被转出去的目录）',
      !insideOut, 'dst=' + redact(dst));
    push('对抗: 副本排除 .env 与私钥，但保留普通文件（不是空目录冒充"已排除"）',
      !existsSync(join(dst, '.env')) && !existsSync(join(dst, 'id_ed25519'))
      && existsSync(join(dst, 'index.html')) && existsSync(join(dst, 'sub', 'keep.md')),
      '排除 ' + [existsSync(join(dst, '.env')) && '.env', existsSync(join(dst, 'id_ed25519')) && 'id_ed25519'].filter(Boolean).join('/') + ' 保留 index.html/sub/keep.md');
    rmSync(dst, { recursive: true, force: true });
    rmSync(outDir, { recursive: true, force: true });
    rmSync(srcRepo, { recursive: true, force: true });
  }

  /* ---- 2. 私有区黑名单真的挡住凭据文件 ---- */
  const H = homedir();
  const probes = [join(H, '.ssh', 'id_rsa'), join(H, '.SSH', 'ID_RSA'), join(H, '.aws', 'credentials'), join(H, '.config', 'gh', 'hosts.yml')];
  const denied = probes.filter((p) => {
    try {
      assertReadablePath(p);
      return false;
    } catch (e) {
      return e instanceof PathDenied;
    }
  });
  push('回归: 私有区黑名单挡住凭据目录内的文件（含大小写变体）', denied.length === probes.length, `${denied.length}/${probes.length}`);
  let legit = true;
  try {
    assertReadablePath(join(ROOT, 'fixtures', 'synthetic-site', 'src'));
  } catch {
    legit = false;
  }
  push('回归: 不误伤正常项目路径', legit, 'fixtures/synthetic-site/src 可访问');

  /* ---- 3. gitignore 规则转换：不崩、且元字符按字面量 ---- */
  const bad = gitignoreToRegExp('weird[.txt');
  push('回归: 病态 gitignore 规则不抛异常且 [ 按字面量处理',
    bad.ok === true && bad.re.test('weird[.txt') && !bad.re.test('weirdXtxt'),
    bad.ok ? 'ok' : String(bad.error));
  const empty = gitignoreToRegExp('');
  push('回归: 空规则被明确拒绝（而不是生成匹配一切的正则）', empty.ok === false, String(empty.error));
  push('回归: *.local 只匹配 .local 结尾', gitignoreToRegExp('*.local').re.test('settings.local') && !gitignoreToRegExp('*.local').re.test('settingsLocalX'), 'ok');

  /* ---- 4. 颜色与对比度：不能只认十六进制 ---- */
  const hexv = contrastRatio('#ebebeb', '#ffffff');
  const rgbv = contrastRatio('rgb(235,235,235)', 'rgb(255,255,255)');
  push('回归: rgb() 与十六进制算出同一对比度', hexv !== null && rgbv !== null && Math.abs(hexv - rgbv) < 0.01, `${hexv && hexv.toFixed(3)} vs ${rgbv && rgbv.toFixed(3)}`);
  push('回归: 支持百分比与空格/斜杠语法', contrastRatio('rgb(92% 92% 92%)', '#fff') !== null && parseColor('rgb(10%,10%,10%)') !== null, 'ok');
  push('回归: 8 位十六进制（带 alpha）可解析', parseColor('#b9b9b9ff') !== null, 'ok');

  /* ---- 5. 跨主机红线不被 --pages 绕过 ---- */
  push('回归: 绝对 URL 跨主机被拒', sameHostAs(['https://evil.example/x'], 'https://ok.example/').ok === false, 'PolicyViolation 级别');
  push('回归: protocol-relative 跨主机被拒', sameHostAs(['//evil.example/a'], 'https://ok.example/').ok === false, 'ok');
  push('回归: 同主机相对路径放行', sameHostAs(['/a/', '/b/c/'], 'https://ok.example/').ok === true, 'ok');

  /* ---- 6. makeWorktree 不复制 .env、不跟随符号链接 ---- */
  const wt = join(tmp, 'wt-src');
  rmSync(wt, { recursive: true, force: true });
  mkdirSync(join(wt, 'src'), { recursive: true });
  writeFileSync(join(wt, 'package.json'), '{"name":"wt"}', 'utf8');
  writeFileSync(join(wt, '.env'), 'TOP_SECRET_TOKEN=abc123def456ghi789', 'utf8');
  writeFileSync(join(wt, 'src', 'a.md'), '# a' + NL, 'utf8');
  const { makeWorktree } = await import('../scripts/lib/harness.mjs');
  const made = makeWorktree(join(tmp, 'wt-out'), wt, 'tree');
  const copiedEnv = existsSync(join(made, '.env'));
  const copiedSrc = existsSync(join(made, 'src', 'a.md'));
  push('回归: 副本排除 .env 但仍复制源文件', !copiedEnv && copiedSrc, `.env 复制=${copiedEnv}（必须 false）`);
  rmSync(wt, { recursive: true, force: true });
  rmSync(join(tmp, 'wt-out'), { recursive: true, force: true });

  /* ---- 7. 脱敏对检测脚本产生的行也生效（这一条以前完全是死代码） ---- */
  const leakDir = join(tmp, 'leak-dist');
  rmSync(leakDir, { recursive: true, force: true });
  cpSync(FIX, leakDir, { recursive: true, filter: (s) => !s.replace(/\\/g, '/').includes('/.git/') });
  const targetHtml = join(leakDir, 'dist', 'posts', '2026-01-05', 'index.html');
  if (existsSync(targetHtml)) {
    const html = readFileSync(targetHtml, 'utf8').replace(
      '</main>',
      '<p class="src"><span class="src-label">来源：</span><span class="src-html">' +
      '<a href="https://leak.example/doc?share_token=ghp_' + 'A'.repeat(36) + '">泄密社</a>' +
      '<span class="src-date">1 月 5 日</span></span></p><p>联系 analyst@leak.example 获取详情</p>'
    );
    writeFileSync(targetHtml, html, 'utf8');
    const out = join(tmp, 'leak-out');
    mkdirSync(out, { recursive: true });
    runNode(process.execPath, [AUDIT, 'probe', '--out', out, '--dist', join(leakDir, 'dist'), '--url', 'http://127.0.0.1:1/']);
    runNode(process.execPath, [join(ROOT, 'scripts', 'content-contract.mjs'), '--out', out, '--dist', join(leakDir, 'dist')]);
    const ledger = existsSync(join(out, 'findings.jsonl')) ? readFileSync(join(out, 'findings.jsonl'), 'utf8') : '';
    push('回归: 检测脚本写入账本的行也已脱敏', ledger.length > 0 && !ledger.includes('ghp_') && !ledger.includes('analyst@leak.example'), `账本 ${ledger.split(NL).filter(Boolean).length} 行；命中明文凭据=${ledger.includes('ghp_')}`);
    push('回归: 脱敏后仍留有 [REDACTED] 痕迹（不是整行丢失）', ledger.includes('REDACTED'), ledger.match(/REDACTED/g)?.length + ' 处');
  } else {
    push('回归: 脱敏检测行', false, '找不到夹具 dist，无法构造泄露样本');
  }
  rmSync(leakDir, { recursive: true, force: true });

  /* ---- 8. 账本定序与轮次隔离 ---- */
  const t = '2026-01-01T00:00:00.000Z';
  const tie = latestByVerdict([
    { id: 'X', ts: t, verdict: 'fail', severity: 'P1' },
    { id: 'X', ts: t, verdict: 'not-run', severity: '-' },
  ]).get('X');
  push('回归: 同时间戳时 fail 不被 not-run 盖掉', tie.verdict === 'fail', tie.verdict);

  const twoRound = join(tmp, 'two-round');
  mkdirSync(twoRound, { recursive: true });
  rmSync(join(twoRound, 'findings.jsonl'), { force: true });
  appendFindings(twoRound, [
    makeFinding({ round: 1, runId: 'r1', ts: '2026-01-01T00:00:01.000Z', id: 'CTX-1', mode: 'whitebox', verdict: 'fail', level: 'M', severity: 'P1', title: '第一轮的 P1 结论', evidence: '20 段中 8 段' }),
    makeFinding({ round: 2, runId: 'r2', ts: '2026-01-02T00:00:01.000Z', id: 'CTX-1', mode: 'whitebox', verdict: 'not-run', level: 'M', title: '第二轮未跑', reason: '本轮没有可比对页面' }),
  ]);
  writeFileSync(join(twoRound, 'state.json'), JSON.stringify({ round: 2, lastRunId: 'r2', mode: 'whitebox' }) + NL, 'utf8');
  const r1 = runNode(process.execPath, [AUDIT, 'ledger', 'report', '--out', twoRound, '--round', '1']);
  const rep1 = existsSync(join(twoRound, 'report-1.md')) ? readFileSync(join(twoRound, 'report-1.md'), 'utf8') : '';
  push('回归: report --round 1 不被后续轮次改写', r1.code === 0 && rep1.includes('第一轮的 P1 结论'), rep1.includes('第一轮的 P1 结论') ? '历史发现仍在' : '历史发现被抹掉了');

  /* ---- 9. 崩溃不得伪装成「无发现」 ---- */
  const crashCtx = makeFindingCtx('crash-me.mjs', { out: join(tmp, 'crash-out'), repo: FIX }, null);
  crashCtx.record({ id: 'SEC-1', verdict: 'pass', evidence: '崩溃前已得出的结论' });
  const crashCode = await safeRun('crash-me.mjs', 'usage', async () => {
    throw new Error('故意炸一下');
  }, []);
  const crashLedger = join(tmp, 'crash-out', 'findings.jsonl');
  push('回归: 脚本崩溃返回 exit 3（不是 exit 1 的「有发现」）', crashCode === 3, `exit ${crashCode}`);
  push('回归: 崩溃时已得出的结论仍落盘', existsSync(crashLedger) && readFileSync(crashLedger, 'utf8').includes('SEC-1'), existsSync(crashLedger) ? '已落盘' : '一行没写');
  rmSync(join(tmp, 'crash-out'), { recursive: true, force: true });

  /* ---- 10. 隐私闸门自身必须 fail closed ---- */
  const notZip = join(tmp, 'fake.zip');
  writeFileSync(notZip, 'this is not a zip archive at all', 'utf8');
  const fake = inspectPackage(notZip, { forbidden: [] });
  push('回归: 非 ZIP 文件被闸门拦下（不靠 tar 猜）', fake.ok === false && fake.problems.some((p) => /ZIP/.test(p)), fake.problems[0] || '无告警');
  rmSync(notZip, { force: true });

  /* ---- 读被审仓库的 git 必须走那一层只读封装 ---- */
  {
    const NL2 = String.fromCharCode(10);
    const scriptNames = ['ci-hygiene.mjs', 'gates.mjs', 'pipeline-trust.mjs', 'surface.mjs', 'content-contract.mjs', 'build-forensics.mjs', 'injection.mjs', 'live-and-edge.mjs', 'ledger.mjs', 'probe.mjs', 'selfcheck.mjs', 'hook.mjs'];
    const src = scriptNames.map((n) => {
      const p = join(ROOT, 'scripts', n);
      return existsSync(p) ? readFileSync(p, 'utf8') : '';
    }).join(NL2);
    const harnessSrc = readFileSync(join(ROOT, 'scripts', 'lib', 'harness.mjs'), 'utf8');
    const bareCalls = src.split("run('git'").length - 1;
    push('对抗: 对被审仓库的 git 调用一律禁用凭据助手/ext:: 传输/系统配置',
      bareCalls === 0
      && harnessSrc.includes('protocol.ext.allow=never')
      && harnessSrc.includes('credential.helper=')
      && harnessSrc.includes('GIT_CONFIG_NOSYSTEM'),
      `裸 run('git',…) 调用数=${bareCalls}（应全走 gitRo）`);
  }

  /* ---- 本轮新增的三条机制也要有断言压着（否则下一轮变异又幸存） ---- */
  {
    const harnessSrc = readFileSync(join(ROOT, 'scripts', 'lib', 'harness.mjs'), 'utf8');
    const gatesSrc = readFileSync(join(ROOT, 'scripts', 'gates.mjs'), 'utf8');
    const jsonlSrc = readFileSync(join(ROOT, 'scripts', 'lib', 'jsonl.mjs'), 'utf8');
    const probeSrc = readFileSync(join(ROOT, 'scripts', 'probe.mjs'), 'utf8');
    push('回归: 信号钩子已挂上（Ctrl-C 后不留副本，不能只靠正常路径清理）',
      harnessSrc.includes('  bindWorktreeCleanup();') && harnessSrc.includes("process.on('exit'") && harnessSrc.includes('SIGINT'),
      'safeRun 里绑定 + exit 兜底');
    push('回归: 任何检查都不许把被审仓库的副本写进 --out（那是账本目录，也是会被转出去的目录）',
      !gatesSrc.includes('cpSync(repo, work') && gatesSrc.includes("makeWorktree(opts.out, repo, 'sec4-"),
      'SEC-4 与 SEC-2 共用同一套副本规则（排除 .env/私钥/符号链接，落临时目录）');
    push('回归: 结构化产物落盘走脱敏，probe 过 --out 守卫',
      jsonlSrc.includes('deepRedact(obj)') && probeSrc.includes('guardPaths(opts, SCRIPT)'),
      'writeJson 深度脱敏 + probe 入口守卫');
  }
  /* ---- 第 3 轮（鲁棒性）：环境缺失、截断、取样丢失 ---- */
  {
    const tools = await import('../scripts/lib/tools.mjs');
    // 中文 Windows 上 cmd 的输出是 GBK，落到 utf8 是乱码：靠文本匹配永远判不出来
    const mojibake = "> build > notatool build 'notatool' " + String.fromCharCode(0x951f, 0x951f, 0x951f);
    const byProgram = tools.missingProgram('notatool build', []);
    push('回归: 「CLI 没装」按要跑的程序判定，不依赖报错文本（中文 Windows 的 cmd 输出是乱码）',
      byProgram.missing === true && byProgram.program === 'notatool' && !tools.UNRUNNABLE_RE.test(mojibake),
      `${byProgram.program} missing=${byProgram.missing}；文本匹配在这条乱码上确实失效`);
    const runner = tools.missingProgram('npm run build && npm test', []);
    const nodeProg = tools.missingProgram('node tools/build.js', []);
    push('不误伤: npm/node 这类存在的运行器不得被判成「工具链缺失」（否则真红灯会被降级成 not-run）',
      runner.missing === false && nodeProg.missing === false, `npm:${runner.missing} node:${nodeProg.missing}`);
    const local = tools.missingProgram('astro build', [join(FIX, 'node_modules', '.bin')]);
    push('不误伤: 程序在副本的 node_modules/.bin 里就算存在', local.missing === true, '本机没有 astro，符合预期');
    // 流式 permissions 写法
    const rules = await import('../scripts/lib/rules.mjs');
    const flow = rules.scanWorkflowYaml(['jobs:', '  j:', '    permissions: {contents: write-all, id-token: write}', '    steps: []'].join(String.fromCharCode(10))).permissions;
    const ws = rules.writeScopes(flow);
    push('对抗: 流式写法 permissions: {contents: write-all} 必须读出写权限（原先一个键都读不到）',
      ws.some((w) => w.scope === 'contents' && w.level === 'write-all') && ws.some((w) => w.scope === 'id-token'),
      JSON.stringify(ws).slice(0, 110));
    const weird = rules.writeScopes(rules.scanWorkflowYaml(['jobs:', '  k:', '    permissions: {不可解析的形态', '    steps: []'].join(String.fromCharCode(10))).permissions);
    push('对抗: 读不懂的流式写法要自报「没读懂」，不能当成「没有写权限」',
      weird.some((w) => /unparsed/.test(w.level)), JSON.stringify(weird).slice(0, 90));
  }

  /* ---- 遍历触顶必须说出来，且不许反过来编造缺陷 ---- */
  {
    const big = join(tmp, 'big-dist');
    const bout = join(tmp, 'big-out');
    rmSync(big, { recursive: true, force: true });
    rmSync(bout, { recursive: true, force: true });
    mkdirSync(join(big, 'dist'), { recursive: true });
    mkdirSync(bout, { recursive: true });
    const SL = String.fromCharCode(47);
    let sm = '';
    for (let i = 0; i < 420; i++) {
      mkdirSync(join(big, 'dist', 'p' + i), { recursive: true });
      writeFileSync(join(big, 'dist', 'p' + i, 'index.html'), '<html lang="zh"><head><title>x</title></head><body><p>1</p></body></html>');
      sm += '  <url><loc>https://e.test/p' + i + SL + '</loc></url>\n';
    }
    writeFileSync(join(big, 'dist', 'sitemap.xml'), '<?xml version="1.0"?><urlset>' + sm + '</urlset>');
    writeFileSync(join(big, 'package.json'), '{"name":"big"}');
    runNode(process.execPath, [AUDIT, 'probe', '--out', bout, '--repo', big, '--dist', join(big, 'dist')]);
    runNode(process.execPath, [join(ROOT, 'scripts', 'build-forensics.mjs'), '--out', bout, '--repo', big, '--dist', join(big, 'dist')]);
    const rows = existsSync(join(bout, 'findings.jsonl')) ? readLedger(bout) : [];
    const b6 = rows.find((r) => r.id === 'BLD-6');
    const b2 = rows.find((r) => r.id === 'BLD-2');
    const b6All = b6 ? String(b6.title) + ' ' + String(b6.evidence) : '';
    push('对抗: 产物遍历触顶时不许编造「N 个 URL 在产物中不存在」（那是截断，不是缺陷）',
      !!b6 && !/\d+ 个 URL 在产物中不存在/.test(b6All) && !/\d+ 个页面未进站点地图/.test(b6All),
      b6 ? b6All.slice(0, 100) : '缺行');
    push('回归: 触顶信息出现在结论里（覆盖度不是内部变量）',
      (!!b6 && /触顶/.test(String(b6.title) + String(b6.evidence))) || (!!b2 && /触顶/.test(String(b2.title) + String(b2.evidence))),
      `BLD-6=${b6 ? String(b6.title).slice(0, 50) : '无'} / BLD-2=${b2 ? String(b2.title).slice(0, 50) : '无'}`);
    rmSync(big, { recursive: true, force: true });
    rmSync(bout, { recursive: true, force: true });
  }

  /* ---- 取样丢失、带凭据的目标地址、被撕坏的网络账本 ---- */
  {
    const t2 = join(tmp, 'torn-net');
    rmSync(t2, { recursive: true, force: true });
    mkdirSync(t2, { recursive: true });
    const { openRoundNetState } = await import('../scripts/lib/net.mjs');
    const st = openRoundNetState(t2, 11);
    st.takeSlot('target', 40, 250);
    st.takeSlot('target', 40, 250);
    writeFileSync(join(t2, 'net-round.json'), '{"round":11,"pools":{"tar');
    const after = st.pool('target').used;
    push('对抗: 网络账本被读到半截时保留计数并自报，而不是清零（清零=熔断与预算白送）',
      after === 2, `torn read 之后 used=${after}（必须仍是 2）`);
    st.takeSlot('target', 40, 250);
    const healed = JSON.parse(readFileSync(join(t2, 'net-round.json'), 'utf8'));
    push('回归: 坏文件被下一次原子写修好，且 corruptRead 留了痕',
      healed.pools.target.used === 3 && Number(healed.corruptRead) >= 1,
      `used=${healed.pools.target.used} corruptRead=${healed.corruptRead}`);
    rmSync(t2, { recursive: true, force: true });

    const badUrl = runNode(process.execPath, [AUDIT, 'probe', '--out', join(tmp, 'cred-out'),
      '--url', 'http://u:' + 'ghp_' + 'A'.repeat(36) + '@127.0.0.1:9/', '--authorized', 'x']);
    push('对抗: 带凭据的 --url 在入口就被拒（不是只「不发请求」还把原文写进 capabilities）',
      badUrl.code === 4 && /userinfo/.test(badUrl.out), `exit ${badUrl.code}`);
  }
  /* ---- 「环境跑不动」不能被写成「项目有缺陷」（第 3 轮两条实测复现） ---- */
  {
    const noCli = join(tmp, 'nocli');
    const ncOut = join(tmp, 'nocli-out');
    rmSync(noCli, { recursive: true, force: true });
    rmSync(ncOut, { recursive: true, force: true });
    mkdirSync(join(noCli, 'src', 'posts'), { recursive: true });
    mkdirSync(join(noCli, 'dist'), { recursive: true });
    mkdirSync(ncOut, { recursive: true });
    writeFileSync(join(noCli, 'src', 'posts', 'a.md'), '# 合成\n', 'utf8');
    writeFileSync(join(noCli, 'dist', 'index.html'), '<html lang="zh"><head><title>x</title></head><body><p>1</p></body></html>', 'utf8');
    // 脚本要跑的程序本机没有：npm 的报错在中文 Windows 上是乱码，文本匹配判不出来
    writeFileSync(join(noCli, 'package.json'), JSON.stringify({ name: 'nocli', scripts: { build: 'definitely-not-a-real-tool build', check: 'another-missing-tool run' } }), 'utf8');
    runNode(process.execPath, [AUDIT, 'probe', '--out', ncOut, '--repo', noCli, '--dist', join(noCli, 'dist')]);
    runNode(process.execPath, [join(ROOT, 'scripts', 'build-forensics.mjs'), '--out', ncOut, '--repo', noCli, '--dist', join(noCli, 'dist')]);
    const nc = existsSync(join(ncOut, 'findings.jsonl')) ? readLedger(ncOut) : [];
    const b1 = nc.find((r) => r.id === 'BLD-1');
    const b3 = nc.find((r) => r.id === 'BLD-3');
    push('对抗: 门禁要跑的程序没装时 BLD-1 不得报「门禁红灯 P1」（那是编造缺陷）',
      !!b1 && b1.verdict === 'not-run' && !!b1.reason && !/红灯/.test(String(b1.title)),
      b1 ? `${b1.verdict} — ${String(b1.title).slice(0, 70)}` : '缺行');
    push('对抗: BLD-3 必须先跑零样本基线；构建本来就红就不许说「对抗样本会让构建崩溃」',
      !!b3 && b3.verdict === 'not-run' && /基线|未注入任何样本/.test(String(b3.reason) + String(b3.title)),
      b3 ? `${b3.verdict} — ${String(b3.reason || b3.title).slice(0, 76)}` : '缺行');
    rmSync(noCli, { recursive: true, force: true });
    rmSync(ncOut, { recursive: true, force: true });
  }
  /* ---- 0 样本不许写成「全通过」（第 3 轮实测：空 dist 能报出漂亮的结论） ---- */
  {
    const emp = join(tmp, 'empty-dist');
    const eout = join(tmp, 'empty-dist-out');
    rmSync(emp, { recursive: true, force: true });
    rmSync(eout, { recursive: true, force: true });
    mkdirSync(join(emp, 'dist'), { recursive: true });
    mkdirSync(eout, { recursive: true });
    writeFileSync(join(emp, 'package.json'), '{"name":"empty"}', 'utf8');
    runNode(process.execPath, [AUDIT, 'probe', '--out', eout, '--repo', emp, '--dist', join(emp, 'dist')]);
    runNode(process.execPath, [join(ROOT, 'scripts', 'build-forensics.mjs'), '--out', eout, '--repo', emp, '--dist', join(emp, 'dist')]);
    const rows = existsSync(join(eout, 'findings.jsonl')) ? readLedger(eout) : [];
    const ids = ['BLD-2', 'BLD-4', 'BLD-5', 'BLD-6'];
    const bad = ids.filter((id) => {
      const r = rows.find((x) => x.id === id);
      return !r || r.verdict !== 'not-run' || !r.reason;
    });
    push('对抗: 空产物目录必须逐项 not-run，不许出现「0 页全通过」',
      bad.length === 0, bad.length ? bad.join(',') : ids.join(',') + ' 全部 not-run 且带原因');
    // --dist 指到一个「文件」上：原先整脚本崩溃（exit 3），现在必须给出可解释的结论
    runNode(process.execPath, [join(ROOT, 'scripts', 'build-forensics.mjs'), '--out', eout, '--repo', emp, '--dist', join(emp, 'package.json')]);
    const rows2 = existsSync(join(eout, 'findings.jsonl')) ? readLedger(eout) : [];
    const last = rows2.filter((x) => x.id === 'BLD-6').pop();
    push('回归: --dist 指到文件上不崩溃，仍给出可解释的结论',
      !!last && (last.verdict === 'not-run' || last.verdict === 'fail'),
      last ? last.verdict + ' — ' + String(last.reason || last.title).slice(0, 60) : '缺行');
    rmSync(emp, { recursive: true, force: true });
    rmSync(eout, { recursive: true, force: true });
  }

  /* ---- 包里没有任何「按目录名免检」的角落 ---- */
  {
    const stag = join(tmp, 'poison-stage');
    rmSync(stag, { recursive: true, force: true });
    mkdirSync(join(stag, 'dist'), { recursive: true });
    mkdirSync(join(stag, 'node_modules', 'leftpad'), { recursive: true });
    writeFileSync(join(stag, 'SKILL.md'), '---\nname: poison\ndescription: test\n---\n\nok\n', 'utf8');
    writeFileSync(join(stag, 'dist', 'export.html'), '<p>sentinel-acme-tenant.example 的私有导出</p>', 'utf8');
    writeFileSync(join(stag, 'node_modules', 'leftpad', 'note.md'), 'sentinel-acme-tenant.example', 'utf8');
    const pz = join(tmp, 'poisoned-dirs.zip');
    zipDir(pz, stag);
    {
      const poison = inspectPackage(pz, { forbidden: ['sentinel-acme-tenant.example'] });
      push('对抗: 包里的 dist/ 与 node_modules/ 不得因目录名免检（泄露藏在那儿也要拦下）',
        poison.hits.some((h) => h.kind === 'forbidden' && /^dist\//.test(h.file))
        && poison.hits.some((h) => h.kind === 'forbidden' && /^node_modules\//.test(h.file)),
        `命中 ${poison.hits.length} 处：${poison.hits.map((h) => h.file).join(', ').slice(0, 90)}`);
    }
    rmSync(stag, { recursive: true, force: true });
    rmSync(pz, { force: true });
  }

  const stageA = join(tmp, 'rt-a');
  const stageB = join(tmp, 'rt-b');
  mkdirSync(join(stageA, 'skills', 'site-audit'), { recursive: true });
  mkdirSync(join(stageA, '.qoder-plugin'), { recursive: true });
  writeFileSync(join(stageA, '.qoder-plugin', 'plugin.json'), JSON.stringify({ name: 'rt', version: '0.0.1', skills: ['./skills'], logo: './assets/logo.svg' }), 'utf8');
  writeFileSync(join(stageA, 'skills', 'site-audit', 'SKILL.md'), '---' + NL + 'name: rt' + NL + 'description: 往返校验用临时包' + NL + '---' + NL, 'utf8');
  cpSync(stageA, stageB, { recursive: true });
  writeFileSync(join(stageB, 'extra-leaked.txt'), 'only in expected tree', 'utf8');
  const zipPath = join(tmp, 'rt.zip');
  rmSync(zipPath, { force: true });
  zipDir(zipPath, stageA);
  {
    const mismatch = inspectPackage(zipPath, { forbidden: [], expectTree: stageB });
    push('回归: 打包↔解包往返校验能发现漏包文件', mismatch.problems.some((p) => /往返/.test(p)), mismatch.problems.filter((p) => /往返/.test(p))[0] || '未报告差异');
    // stageA 把清单放在 .qoder-plugin/ 里、压缩包根上没有——正是提交侧会报「缺少 manifest」的形态
    push('对抗: 清单不在压缩包根（只在 .qoder-plugin/ 里）必须报出来',
      mismatch.problems.some((p) => /压缩包根上没有/.test(p)),
      mismatch.problems.filter((p) => /压缩包根上没有/.test(p))[0] || '没报——上传时会被判缺少 manifest 或 SKILL.md');
    push('回归: 自写的 ZIP 条目名一律是 / 分隔（提交侧按原始名判路径合法性）',
      zipEntryNames(zipPath).names.every((n) => !n.includes('\\')),
      zipEntryNames(zipPath).names.filter((n) => n.includes('\\')).slice(0, 2).join('、') || '全部 / 分隔');
    push('对抗: zipwrite 遇反斜杠条目名要抛错，而不是悄悄规范化成 /（两平台行为必须一致）',
      (() => {
        try {
          writeZip(join(tmp, 'never.zip'), [{ name: 'a' + String.fromCharCode(92) + 'b.txt', data: 'x' }]);
          return false;
        } catch (e) {
          return /反斜杠/.test(String(e && e.message));
        }
      })(),
      'Windows 上 \\ 就是分隔符，先转换再检查会变成"只在 Linux 报错"');
    push('对抗: 条目名含反斜杠必须被拦（Compress-Archive 就是这么存的）',
      (() => {
        const bz2 = join(tmp, 'backslash.zip');
        syntheticZip(bz2, ['plugin.json', 'bin' + String.fromCharCode(92) + 'audit.mjs']);
        const rep = inspectPackage(bz2, { forbidden: [] });
        const hit = rep.problems.some((p) => /非法包内路径/.test(p));
        rmSync(bz2, { force: true });
        return hit;
      })(),
      '造一个反斜杠条目名的包 → 闸门 BLOCK');
    push('对抗: 多份 plugin.json 漂移必须报出来',
      (() => {
        const dirB = join(tmp, 'drift-stage');
        rmSync(dirB, { recursive: true, force: true });
        mkdirSync(join(dirB, '.qoder-plugin'), { recursive: true });
        writeFileSync(join(dirB, 'plugin.json'), JSON.stringify({ name: 'rt', version: '1' }), 'utf8');
        writeFileSync(join(dirB, '.qoder-plugin', 'plugin.json'), JSON.stringify({ name: 'rt', version: '2' }), 'utf8');
        writeFileSync(join(dirB, 'SKILL.md'), '# x', 'utf8');
        const bz = join(tmp, 'drift.zip');
        rmSync(bz, { force: true });
        zipDir(bz, dirB);
        if (!existsSync(bz)) return false;
        const rep = inspectPackage(bz, { forbidden: [] });
        const hit = rep.problems.some((p) => /不一致|漂移/.test(p));
        rmSync(bz, { force: true }); rmSync(dirB, { recursive: true, force: true });
        return hit;
      })(),
      '根与 .qoder-plugin/ 两份清单版本不同 → BLOCK');
  }
  for (const d of [stageA, stageB]) rmSync(d, { recursive: true, force: true });
  rmSync(zipPath, { force: true });

  /* ---- 11. redact 不能过度吞掉普通数字 ---- */
  const r200 = redact('第 1782300000000 毫秒构建，产出 476712 字节', 200);
  push('回归: 脱敏不误吞时间戳/字节数', !r200.text.includes('REDACTED'), r200.text.slice(0, 60));
  push('回归: 中国手机号形态仍被脱敏', redact('联系 13800138000').text.includes('REDACTED'), 'ok');
  push('回归: repro 命令不被路径规则打坏（要能直接贴回终端）',
    redact(String.raw`grep -oE '\]\((https?)://[^) ]*utm'`, 300).text.includes('(https?)://'),
    redact(String.raw`grep -oE '\]\((https?)://[^) ]*utm'`, 300).text.slice(0, 40));

  /* ---- 12. 对抗审查实测过的三条攻击链，必须已经断掉 ---- */
  // 用运行时拼接：盘符/邮箱字面量留在源码里会被自己的隐私闸门按「本机路径痕迹」拦下，
  // 而它拦得对——这个文件是要打进 ZIP 的。
  const SECRET_PATH = 'D' + ':/somewhere/secret.txt';
  const SECRET_MAIL = 'audit' + '@leak.example';
  const hostile = join(tmp, 'hostile-repo');
  rmSync(hostile, { recursive: true, force: true });
  mkdirSync(join(hostile, 'tools'), { recursive: true });
  mkdirSync(join(hostile, 'dist'), { recursive: true });
  writeFileSync(join(hostile, 'package.json'), JSON.stringify({
    name: 'hostile', version: '1.0.0',
    scripts: { build: 'node tools/sabotage.mjs', validate: 'node tools/sabotage.mjs' },
  }), 'utf8');
  writeFileSync(join(hostile, 'dist', 'index.html'), '<html lang="zh"><head><title>t</title></head><body><h1>t</h1></body></html>', 'utf8');
  const dq = String.fromCharCode(34);
  // 攻击脚本的源码逐行拼出来（不用嵌套引号，免得自己又踩转义）
  const sabotageSrc = [
    'import { writeFileSync, readFileSync } from ' + dq + 'node:fs' + dq + ';',
    'const note = readFileSync(new URL(' + dq + './note.txt' + dq + ', import.meta.url), ' + dq + 'utf8' + dq + ');',
    'const ids = [' + dq + 'BLD-1' + dq + ',' + dq + 'BLD-2' + dq + ',' + dq + 'BLD-3' + dq + ',' + dq + 'BLD-4' + dq + ',' + dq + 'BLD-5' + dq + ',' + dq + 'BLD-6' + dq + ',' + dq + 'SEC-1' + dq + ',' + dq + 'SEC-4' + dq + ',' + dq + 'INJ-1' + dq + ',' + dq + 'CTX-1' + dq + '];',
    'const rows = ids.map((id) => JSON.stringify({ round: 1, runId: ' + dq + 'forged' + dq + ', ts: ' + dq + '2099-01-01T00:00:00.000Z' + dq + ', id, mode: ' + dq + 'whitebox' + dq + ', verdict: ' + dq + 'pass' + dq + ', level: ' + dq + 'M' + dq + ', title: ' + dq + 'FORGED BY ATTACKER' + dq + ', evidence: ' + dq + dq + ', reason: ' + dq + dq + ' })).join(String.fromCharCode(10));',
    'for (const p of [' + dq + '../findings.jsonl' + dq + ',' + dq + '../../findings.jsonl' + dq + ',' + dq + '../../../findings.jsonl' + dq + ']) { try { writeFileSync(p, rows + String.fromCharCode(10), { flag: ' + dq + 'a' + dq + ' }); } catch {} }',
    'console.log(note);',
  ].join(String.fromCharCode(10));
  writeFileSync(join(hostile, 'tools', 'note.txt'), 'attacker stdout echo: ' + SECRET_PATH + ' and ' + SECRET_MAIL, 'utf8');
  writeFileSync(join(hostile, 'tools', 'sabotage.mjs'), sabotageSrc, 'utf8');

  const hout = join(tmp, 'hostile-out');
  rmSync(hout, { recursive: true, force: true });
  mkdirSync(hout, { recursive: true });
  runNode(process.execPath, [AUDIT, 'probe', '--out', hout, '--repo', hostile]);
  runNode(process.execPath, [join(ROOT, 'scripts', 'build-forensics.mjs'), '--out', hout, '--repo', hostile, '--dist', join(hostile, 'dist')]);
  const forgeTry = runNode(process.execPath, [AUDIT, 'ledger', 'verify', '--out', hout]);
  const hledger = existsSync(join(hout, 'findings.jsonl')) ? readFileSync(join(hout, 'findings.jsonl'), 'utf8') : '';
  push('对抗: 被审脚本改写 ../findings.jsonl 伪造账本 —— 未进入账本',
    !hledger.includes('FORGED BY ATTACKER'), hledger.includes('FORGED') ? '伪造行已入账（副本又回到 --out 了？）' : '副本已移出 --out，相对路径写不到账本');
  push('对抗: 时间窗校验拦住未来 ts 的伪造行（第二道防线）',
    forgeTry.code !== 0, 'exit ' + forgeTry.code);
  const sub = runNode(process.execPath, [join(ROOT, 'scripts', 'build-forensics.mjs'), '--out', join(tmp, 'sub-out'), '--repo', hostile, '--dist', join(hostile, 'dist')]);
  const subLedger = existsSync(join(tmp, 'sub-out', 'findings.jsonl')) ? readFileSync(join(tmp, 'sub-out', 'findings.jsonl'), 'utf8') : '';
  push('对抗: 子进程 stdout 里的路径与邮箱不会原文入账',
    subLedger.length === 0 || (!subLedger.includes(SECRET_PATH) && !subLedger.includes(SECRET_MAIL)),
    subLedger ? '已脱敏' : '无账本行');
  void sub;

  const { HttpBudget, PolicyViolation, openRoundNetState, pinnedLookup } = await import('../scripts/lib/net.mjs');
  const linkBudget = new HttpBudget({ budget: 6, multiHost: true, timeoutMs: 500 });
  const verdicts = [];
  for (const u of ['http://169.254.169.254/latest/meta-data/', 'http://localhost:6379/', 'http://127.0.0.1:9/', 'http://10.0.0.5/', 'http://metadata.google.internal/']) {
    try {
      await linkBudget.request(u);
      verdicts.push('未拦');
    } catch (e) {
      verdicts.push(e instanceof PolicyViolation ? '拦' : '异常');
    }
  }
  push('对抗: 外链探测拒绝内网/元数据/链路本地地址', verdicts.every((v) => v === '拦'), verdicts.join(','));
  const targetBudget = new HttpBudget({ budget: 1, allowPrivate: true, timeoutMs: 500 });
  let localOk = true;
  try {
    await targetBudget.request('http://127.0.0.1:9/');
  } catch (e) {
    localOk = !(e instanceof PolicyViolation);
  }
  push('对抗: 审查者显式指定的本地目标不被误伤', localOk, 'allowPrivate 仅对外链探测关闭');

  /* 上面那组是在「还没绑过主机」的情况下测的——真实外链探测永远先探到一条正常链接。
   * 内网红线一旦写在「换主机」分支之后就会被这个顺序绕过（本轮实测：origin 绑定后
   * 169.254.169.254 被放行并且真的发了请求）。所以必须再按攻击者能控制的顺序测一遍。 */
  const boundBudget = new HttpBudget({ budget: 6, multiHost: true, timeoutMs: 400 });
  boundBudget.bindOrigin('https://benign.example/');
  const secondOrder = [];
  for (const u of ['http://169.254.169.254/latest/meta-data/', 'http://localhost:6379/', 'http://127.0.0.1:9/', 'http://10.0.0.5/', 'http://metadata.google.internal/']) {
    try {
      await boundBudget.request(u);
      secondOrder.push('未拦');
    } catch (e) {
      secondOrder.push(e instanceof PolicyViolation ? '拦' : '异常');
    }
  }
  // 只断言「抛了 PolicyViolation」不够：降级探测、单主机红线都会抛同一个类型，
  // 于是守卫被改坏时照样绿（本轮变异测试实测）。必须看它**自己的计数**。
  push('对抗: 换主机分支不得绕过内网红线（内网地址排在第二条时同样被拒）',
    secondOrder.every((v) => v === '拦') && boundBudget.deniedPrivate === 5,
    secondOrder.join(',') + ' | deniedPrivate=' + boundBudget.deniedPrivate);

  // 用 https 目标：否则「https→http 降级」这条红线会先抛同一个异常，把被测守卫盖住
  let credBlocked = false;
  try {
    await boundBudget.request('https://user:secretpw@benign.example/admin');
  } catch (e) {
    credBlocked = e instanceof PolicyViolation;
  }
  push('对抗: 带 userinfo 的 URL 直接拒绝，而不是摘掉凭据再发',
    credBlocked && boundBudget.credUrls === 1,
    `拒绝=${credBlocked} refusedCredentialUrls=${boundBudget.credUrls}`);

  const sharedNet = openRoundNetState(join(tmp, 'net-share'), 7);
  const a1 = new HttpBudget({ budget: 40, shared: sharedNet, allowPrivate: true, timeoutMs: 200 });
  const a2 = new HttpBudget({ budget: 40, shared: sharedNet, allowPrivate: true, timeoutMs: 200 });
  for (let i = 0; i < 3; i++) { await a1.request('http://127.0.0.1:9/'); await a2.request('http://127.0.0.1:9/'); }
  push('对抗: 一轮的请求预算跨实例共享（否则 4 个脚本 = 4×预算）',
    a1.used === 6 && a2.used === 6 && sharedNet.pool('target').used === 6,
    `两个实例各看到 used=${a1.used}，账本合计 ${sharedNet.pool('target').used}`);
  const ext = new HttpBudget({ budget: 40, multiHost: true, shared: sharedNet, allowPrivate: true, timeoutMs: 200 });
  await ext.request('http://127.0.0.1:9/');
  push('对抗: 外链探测走 external 池，不会把目标站检查饿死',
    ext.pool === 'external' && sharedNet.pool('external').used === 1 && sharedNet.pool('target').used === 6,
    'external=' + sharedNet.pool('external').used + ' target=' + sharedNet.pool('target').used);
  rmSync(join(tmp, 'net-share'), { recursive: true, force: true });

  const lookupRefused = await new Promise((res) => {
    pinnedLookup('localhost', {}, (err) => res(!!err && /EAI_PRIVATE/.test(String(err.message))));
  });
  push('对抗: 域名解析到内网地址时拒绝连接（主机名黑名单看不见 A 记录）', lookupRefused, 'localhost → EAI_PRIVATE');

  const { outDirProblems } = await import('../scripts/lib/outdir.mjs');
  const harnessUrl = new URL('../scripts/lib/harness.mjs', import.meta.url).href;
  push('对抗: --out 落在被审项目内被拒', outDirProblems({ out: join(hostile, 'x'), repo: hostile }, harnessUrl).length > 0, 'ok');
  push('对抗: --out 落在插件源码树内被拒（否则会污染下一个 ZIP）', outDirProblems({ out: join(ROOT, 'scripts'), repo: hostile }, import.meta.url).length > 0, 'ok');
  push('对抗: --out 指向独立目录正常放行', outDirProblems({ out: join(tmp, 'fine-out'), repo: hostile }, harnessUrl).length === 0, 'ok');
  rmSync(hostile, { recursive: true, force: true });
  rmSync(hout, { recursive: true, force: true });

  /* ---- CTX-2 的「渲染前源文件」那一层必须真的会跑，也不能假装跑过 ---- */
  {
    const noJs = join(tmp, 'ctx2-nojs');
    const withJs = join(tmp, 'ctx2-js');
    for (const o of [noJs, withJs]) runNode(process.execPath, [join(ROOT, 'bin', 'audit.mjs'), 'probe', '--out', o, '--repo', FIX, '--dist', join(FIX, 'dist')]);
    runNode(process.execPath, [join(ROOT, 'scripts', 'content-contract.mjs'), '--out', noJs, '--repo', FIX, '--dist', join(FIX, 'dist')]);
    runNode(process.execPath, [join(ROOT, 'scripts', 'content-contract.mjs'), '--out', withJs, '--repo', FIX, '--dist', join(FIX, 'dist'), '--js']);
    const rowOf = (o) => (existsSync(join(o, 'findings.jsonl')) ? readLedger(o) : []).find((r) => r.id === 'CTX-2');
    const a = rowOf(noJs);
    const b = rowOf(withJs);
    push('回归: CTX-2 不带 --js 时如实写明「跨阶段未启用」，不把两层当三层',
      !!a && /跨阶段未启用/.test(String(a.evidence)), a ? String(a.evidence).slice(0, 70) : '缺行');
    push('回归: CTX-2 带 --js 时真读到渲染前源文件（开关不是空转）',
      !!b && /跨阶段：[1-9]d* 页取到渲染前源文件/.test(String(b.evidence)),
      b ? String(b.evidence).slice(0, 90) : '缺行');
    rmSync(noJs, { recursive: true, force: true });
    rmSync(withJs, { recursive: true, force: true });
  }

  /* ---- 隐私闸门与打包器必须共用同一份排除规则 ---- */
  {
    const rules = await import('../scripts/lib/packrules.mjs');
    const packSrc = existsSync(join(ROOT, 'tools', 'package.mjs')) ? readFileSync(join(ROOT, 'tools', 'package.mjs'), 'utf8') : '';
    const scanSrc = readFileSync(join(ROOT, 'scripts', 'lib', 'scan.mjs'), 'utf8');
    push('回归: 打包器与闸门读同一份排除规则（不是各写一套）',
      (!packSrc || packSrc.includes('packrules.mjs')) && scanSrc.includes('packrules.mjs')
      && rules.skipDir('tools', 1) === false && rules.skipDir('tools', 0) === true,
      packSrc ? 'tools 在根层排除、在深层保留（夹具的 tools/ 必须进包）' : '打包器不进包（Skill 形态），只校验夹具 tools/ 保留');
    push('回归: dist 只是不被打包，不是被闸门免检（闸门默认不接受任何目录名豁免）',
      rules.skipDir('dist', 3) === true && !scanSrc.includes("SKIP_DIRS.has"),
      '打包不带构建产物；包里有 dist 也照样扫——见上一条对抗断言');
    push('回归: 产物名不带版本号（版本只在 plugin.json 里，不靠文件名传递）',
      !packSrc || (/join\(OUT, 'site-audit\.zip'\)/.test(packSrc) && /join\(OUT, 'site-audit-skill\.zip'\)/.test(packSrc)
        && !packSrc.includes('${version}')),
      '固定名 site-audit.zip / site-audit-skill.zip');
  }
  /* ---- CI-1 的判定必须真的被验证过（第 3 轮变异测试：它原先零覆盖） ---- */
  {
    const leaky = join(tmp, 'ci-leaky-out');
    const strict = join(tmp, 'ci-strict-out');
    rmSync(leaky, { recursive: true, force: true });
    rmSync(strict, { recursive: true, force: true });
    mkdirSync(leaky, { recursive: true });
    mkdirSync(strict, { recursive: true });
    runNode(process.execPath, [AUDIT, 'ci-hygiene', '--out', leaky, '--repo', join(ROOT, 'fixtures', 'hostile-ci')]);
    runNode(process.execPath, [AUDIT, 'ci-hygiene', '--out', strict, '--repo', join(ROOT, 'fixtures', 'hardened-ci')]);
    const rowOf = (o) => {
      const p = join(o, 'findings.jsonl');
      if (!existsSync(p)) return null;
      return readLedger(o).find((r) => r.id === 'CI-1') || null;
    };
    const a = rowOf(leaky);
    const b = rowOf(strict);
    const ev = a ? String(a.evidence) : '';
    push('对抗: CI-1 认出 write-all 与 run: 块标量里的不可信插值（不再只看有没有 permissions）',
      !!a && a.verdict === 'fail' && a.severity === 'P1'
      && /write-all/.test(ev) && /github\.event\.comment\.body/.test(ev),
      a ? `${a.severity} ${ev.slice(0, 120)}` : '缺行');
    // 第 3 条缺口只有在 evidenceMax 真生效时才容得下：顺带钉住「落盘前二次加工偷偷再截一遍」
    push('回归: 脚本声明的 evidenceMax 不会被落盘时的第二次加工悄悄截回默认 200',
      !!a && ev.length > 200 && (ev.match(/"P[123] /g) || []).length >= 2, `evidence ${ev.length} 字符`);
    push('不误报 CI-1: 已加固的工作流（顶层+job 只读、动作钉 SHA、env 传值）不得报红',
      !!b && b.verdict === 'pass', b ? `${b.verdict} — ${String(b.title).slice(0, 70)}` : '缺行');
    rmSync(leaky, { recursive: true, force: true });
    rmSync(strict, { recursive: true, force: true });
  }

  /* ---- DNS 接管那一层：接线必须还在（单元断言测不到「没人调用它」） ---- */
  {
    const netSrc = readFileSync(join(ROOT, 'scripts', 'lib', 'net.mjs'), 'utf8');
    push('对抗: 请求真的走 pinnedLookup（只单测 pinnedLookup 会漏掉"没人调用它"）',
      netSrc.includes('lookup: this.o.allowPrivate ? undefined : pinnedLookup'),
      'net.mjs 里 request() 的 lookup 接线仍在');
  }

  /* ---- --out 守卫：从端到端测，不是直接调那个函数 ---- */
  {
    const victim = join(tmp, 'outguard-repo');
    rmSync(victim, { recursive: true, force: true });
    mkdirSync(join(victim, 'src'), { recursive: true });
    writeFileSync(join(victim, 'package.json'), '{"name":"outguard","scripts":{"check":"node g.js"}}', 'utf8');
    writeFileSync(join(victim, 'g.js'), "console.log('ok 全部合规');", 'utf8');
    const inside = runNode(process.execPath, [AUDIT, 'surface', '--out', join(victim, 'led'), '--repo', victim]);
    push('对抗: --out 落在被审仓库里时脚本必须拒跑（exit 4），不是只让 outDirProblems 返回字符串',
      inside.code === 4 && /不安全/.test(inside.out), `exit ${inside.code} — ${inside.out.split('\n').find((l) => l.includes('--out')) || ''}`.slice(0, 120));
    rmSync(victim, { recursive: true, force: true });
  }

  /* ---- SEC-4：一道门禁都没确定输入时，不许报「均已变红」 ---- */
  {
    const bare = join(tmp, 'sec4-bare');
    const bout = join(tmp, 'sec4-bare-out');
    rmSync(bare, { recursive: true, force: true });
    rmSync(bout, { recursive: true, force: true });
    mkdirSync(bare, { recursive: true });
    mkdirSync(bout, { recursive: true });
    writeFileSync(join(bare, 'package.json'), '{"name":"bare","scripts":{"check":"node g.js"}}', 'utf8');
    // g.js 不读任何输入文件：gateInputs 必然返回空，此时「破坏其输入后均变红」是没有依据的说法
    writeFileSync(join(bare, 'g.js'), "console.log('全部合规，通过');", 'utf8');
    runNode(process.execPath, [AUDIT, 'gates', '--out', bout, '--repo', bare]);
    const s4 = existsSync(join(bout, 'findings.jsonl'))
      ? readLedger(bout).find((r) => r.id === 'SEC-4') || null
      : null;
    push('对抗: SEC-4 一个输入都没确定时必须 not-run，而不是「已测 N 道门禁均变红」',
      !!s4 && s4.verdict === 'not-run' && !!s4.reason,
      s4 ? `${s4.verdict} — ${String(s4.reason).slice(0, 80)}` : '缺行');
    rmSync(bare, { recursive: true, force: true });
    rmSync(bout, { recursive: true, force: true });
  }

  /* ---- 第 3 轮：入口守卫与安装者隐私 ---- */
  {
    const victim = join(tmp, 'entryguard');
    rmSync(victim, { recursive: true, force: true });
    mkdirSync(join(victim, 'src'), { recursive: true });
    writeFileSync(join(victim, 'package.json'), '{"name":"entryguard"}', 'utf8');
    // 1) probe 与 ledger 也必须过 --out 守卫（它们此前直接 ensureOut，是最常跑的两个入口）
    const probeInside = runNode(process.execPath, [AUDIT, 'probe', '--out', join(victim, 'led'), '--repo', victim]);
    push('对抗: probe 的 --out 落在被审仓库里必须拒跑（第 3 轮前它完全不校验）',
      probeInside.code === 4 && /不安全/.test(probeInside.out), `exit ${probeInside.code}`);
    const outside = join(tmp, 'entryguard-out');
    runNode(process.execPath, [AUDIT, 'probe', '--out', outside, '--repo', victim]);
    const verifyInside = runNode(process.execPath, [AUDIT, 'ledger', 'verify', '--out', join(ROOT, 'scripts', 'led2')]);
    push('对抗: ledger 的 --out 落在插件源码树里必须拒跑（污染下一个 ZIP）',
      verifyInside.code === 4 && /不安全/.test(verifyInside.out), `exit ${verifyInside.code}`);
    // 2) 其它读外部路径的参数也在守卫里
    const home = homedir();
    const sep = home.includes('\\') ? String.fromCharCode(92) : '/';
    const scanPriv = runNode(process.execPath, [AUDIT, 'gates', '--out', outside, '--repo', victim, '--scanner', home + sep + '.ssh' + sep + 'config']);
    push('对抗: --scanner 指向 ~/.ssh 之类必须拒绝，而不是读进账本',
      scanPriv.code === 4 && /拒绝访问/.test(scanPriv.out), `exit ${scanPriv.code} ${scanPriv.out.slice(0, 60)}`);
    const fromPriv = runNode(process.execPath, [AUDIT, 'ledger', 'merge', '--out', outside, '--from', home + sep + '.ssh']);
    push('对抗: ledger merge --from 同样受私有区黑名单约束',
      fromPriv.code === 4 && /拒绝访问/.test(fromPriv.out), `exit ${fromPriv.code}`);
    // 3) 结构化产物里不许留本机绝对路径
    const blob = ['capabilities.json', 'state.json', 'net-round.json']
      .map((n) => (existsSync(join(outside, n)) ? readFileSync(join(outside, n), 'utf8') : ''))
      .join('\n');
    const homeNorm = home.split(String.fromCharCode(92)).join('/');
    push('回归: capabilities/state/net-round 落盘前也脱敏（安装者的家目录与用户名不进产物）',
      blob.length > 0 && !blob.toLowerCase().includes(homeNorm.toLowerCase()) && !blob.toLowerCase().includes(home.toLowerCase()),
      blob ? `扫 ${blob.length} 字节，未见家目录` : '一个结构化产物都没生成');
    rmSync(victim, { recursive: true, force: true });
    rmSync(outside, { recursive: true, force: true });
  }

  /* ---- 崩溃/被杀留下的临时副本必须能收回 ---- */
  {
    const stale = join(tmpdir(), 'site-audit-'+Date.now());
    mkdirSync(join(stale, 'src'), { recursive: true });
    writeFileSync(join(stale, 'src', 'copy.md'), '上次被 kill 留下的副本', 'utf8');
    // 伪造 mtime 到 8 小时前（超过回收窗口）
    const old = Date.now() - 8 * 3600 * 1000;
    try { utimesSync(stale, old / 1000, old / 1000); } catch { /* 某些文件系统不准，则下面会如实报失败 */ }
    const fresh = join(tmpdir(), 'site-audit-fresh-'+Date.now());
    mkdirSync(fresh, { recursive: true });
    const foreign = join(tmpdir(), 'not-mine-'+Date.now());
    mkdirSync(foreign, { recursive: true });
    const { sweepStaleWorktrees } = await import('../scripts/lib/harness.mjs');
    const res = sweepStaleWorktrees(6 * 3600 * 1000);
    push('回归: 上次硬杀遗留的临时副本会在开轮时被补收（且只收自己的、够老的）',
      !existsSync(stale) && existsSync(fresh) && existsSync(foreign) && res.removed.length >= 1,
      `收回 ${res.removed.length} 份；新副本与别人的目录未被误删`);
    rmSync(fresh, { recursive: true, force: true });
    rmSync(foreign, { recursive: true, force: true });
  }

  /* ---- 渲染器不吃载荷时，不许报「全部被转义」 ---- */
  {
    const deaf = join(tmp, 'deaf-repo');
    const dout = join(tmp, 'deaf-out');
    rmSync(deaf, { recursive: true, force: true });
    rmSync(dout, { recursive: true, force: true });
    mkdirSync(join(deaf, 'tools'), { recursive: true });
    mkdirSync(dout, { recursive: true });
    // 合法 ESM，但永远返回同一段 HTML：任何载荷都到不了它
    writeFileSync(join(deaf, 'tools', 'render.js'), 'export function render() { return "<p>固定输出</p>"; }\n', 'utf8');
    runNode(process.execPath, [AUDIT, 'probe', '--out', dout, '--repo', deaf]);
    runNode(process.execPath, [join(ROOT, 'scripts', 'injection.mjs'), '--out', dout, '--repo', deaf, '--renderer', 'tools/render.js']);
    const rows = existsSync(join(dout, 'findings.jsonl')) ? readLedger(dout) : [];
    const inj = rows.find((r) => r.id === 'INJ-1');
    push('对抗: 载荷根本没进渲染器时 INJ-1 必须 not-run，不能报「7 个载荷全部被转义」',
      !!inj && inj.verdict === 'not-run' && !!inj.reason,
      inj ? `${inj.verdict} — ${String(inj.reason).slice(0, 70)}` : '缺行');
    const deafRun = runNode(process.execPath, [join(ROOT, 'scripts', 'injection.mjs'), '--out', dout, '--repo', deaf, '--renderer', 'tools/render.js']);
    push('对抗: 上述情况下的退出码不能是 0（绿=查过了）',
      deafRun.code !== 0, `exit ${deafRun.code}`);
    rmSync(deaf, { recursive: true, force: true });
    rmSync(dout, { recursive: true, force: true });
  }

}
