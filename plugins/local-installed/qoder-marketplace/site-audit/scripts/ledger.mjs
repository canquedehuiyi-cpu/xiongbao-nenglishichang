#!/usr/bin/env node
/**
 * 账本闸门：完备性检查、报告生成、跨轮结转、hook 提醒。
 *
 * 核心不变量（整套工具存在的理由）：
 *   一项检查「没跑」必须成为账本里的一行 verdict=not-run + reason，
 *   而不是被省略。省略 = 看起来通过；本脚本让省略在结构上不可能。
 */

import { existsSync, readFileSync, writeFileSync } from 'node:fs';
import { join, resolve } from 'node:path';
import { neutralizeCell } from './lib/mdcell.mjs';
import { guardPaths } from './lib/harness.mjs';
import { parseArgs, EXIT, usage, nowIso, targetHash, runId as mkRunId } from './lib/tools.mjs';
import { ensureOut, homePlaceholder, assertReadablePath } from './lib/scratch.mjs';
import { readLedger, appendFindings, makeFinding, ledgerPath, readJsonIfExists, writeJson, latestByVerdict } from './lib/jsonl.mjs';
import { CHECKS, IDS, MODES, applicable, renderChecklist, missingCaps, byId } from './lib/registry.mjs';

const HELP = `用法:
  audit ledger verify    --out <dir> [--mode whitebox|blackbox] [--round N]
  audit ledger report    --out <dir> [--round N]
  audit ledger merge     --out <dir> --from <other-out-dir>
  audit ledger checklist [--mode whitebox|blackbox]
  audit ledger outstanding --out <dir>      (供 hook 调用：只输出 ID 与计数)

verify 做三件事：
  1) 用本轮 capabilities.json 为「因缺能力而没跑」的检查补写 not-run 行；
  2) 为「有能力却没人跑」的检查补写 not-run 行（reason=未覆盖，这就是无声放弃本身）；
  3) 退出码区分：0 全通过 / 1 有 P1-P2 / 2 有 not-run / 3 全是 not-run / 4 用法错误。`;

/**
 * 轮次由 `probe` 开轮时写进 state.json，verify/report 只读不增——
 * 否则检测脚本写入的第 N 轮结论会被 verify 误算成第 N+1 轮，缺口也补错地方。
 */
function readState(outDir) {
  return readJsonIfExists(outDir, 'state.json') || null;
}

function currentRound(outDir, opts) {
  const state = readState(outDir);
  if (opts.round) return { round: Number(opts.round), runId: mkRunId(Number(opts.round)), state };
  if (state && Number.isFinite(state.round)) {
    return { round: state.round, runId: state.lastRunId || mkRunId(state.round), state };
  }
  const rows = readLedger(outDir);
  const max = rows.reduce((m, r) => Math.max(m, Number(r.round) || 0), 0);
  const round = max || 1;
  return { round, runId: mkRunId(round), state, unopened: true };
}

function persistRound(outDir, round, runId, extra = {}) {
  writeJson(outDir, 'state.json', { round, lastRunId: runId, ts: nowIso(), ...extra });
}

/** 把本轮应覆盖但缺失的 id 补成 not-run 行。返回补写的行。 */
function materializeGaps(outDir, round, mode, runId, hash) {
  const want = applicable(mode);
  const caps = readJsonIfExists(outDir, 'capabilities.json') || null;
  const rows = readLedger(outDir);
  const cur = latestByVerdict(rows);
  const covered = new Set(
    [...cur.values()].filter((r) => r.round === round && r.mode === mode).map((r) => r.id)
  );
  const added = [];
  for (const id of want) {
    if (covered.has(id)) continue;
    const c = byId(id);
    if (!c) continue;
    // caps 是整份 capabilities.json，能力表在 .capabilities 里；
    // 传错层级会让每一项都「缺能力」，从而永远走不到「无人覆盖」那条分支。
    const capTable = caps && caps.capabilities ? caps.capabilities : caps;
    const missing = capTable ? missingCaps(c, capTable) : c.caps;
    const why = missing.length
      ? `缺能力未跑: ${missing.join(', ')}`
      : '本轮无任何脚本覆盖该项（无声放弃——请排进下一轮或在命令行显式排除）';
    added.push(
      makeFinding({
        round,
        runId,
        mode,
        targetHash: hash,
        id,
        verdict: 'not-run',
        level: c.lvl,
        title: c.t,
        reason: why,
        unblockCommand: c.unblock || '',
        script: c.script,
      })
    );
  }
  appendFindings(outDir, added);
  return added;
}

function verify(outDir, opts) {
  const state = readState(outDir);
  const mode = opts.mode || (state && state.mode) || 'whitebox';
  if (!MODES.includes(mode)) return usage('ledger verify', HELP, `--mode 只能是 ${MODES.join('|')}`);
  const { round, runId, unopened } = currentRound(outDir, opts);
  const hash = opts.url ? targetHash(opts.url) : (state && state.targetHash) || '';
  const added = materializeGaps(outDir, round, mode, runId, hash);

  const all0 = readLedger(outDir);
  // 被审项目若能执行代码，写一条 ts:"2099-…" 的行就能盖掉所有真实结论（对抗审查实测过）。
  // 结构上真正堵住它的是「副本不再放在 --out 里」；这里是第二道：时间窗不合理的行不参与判定。
  const openedAt = state && state.ts ? Date.parse(state.ts) : NaN;
  const nowMs = Date.now();
  const bogus = [];
  const all = all0.filter((r) => {
    const t = Date.parse(r.ts || '');
    if (!Number.isFinite(t)) { bogus.push(r.id + '（ts 不可解析）'); return false; }
    if (t > nowMs + 300000) { bogus.push(r.id + '（ts 在未来）'); return false; }
    if (Number.isFinite(openedAt) && Number(r.round) === round && t < openedAt - 120000) {
      bogus.push(r.id + '（ts 早于本轮开轮）');
      return false;
    }
    return true;
  });
  if (bogus.length) {
    console.log('!! 账本有 ' + bogus.length + ' 行时间戳不可能成立，已忽略——若被审项目可执行代码，这是伪造账本的典型痕迹：');
    console.log('   ' + bogus.slice(0, 8).join(', ') + (bogus.length > 8 ? ' …' : ''));
  }
  const want = applicable(mode);
  const wantSet = new Set(want);
  const roundRows = [...latestByVerdict(all).values()].filter((r) => r.round === round && r.mode === mode);
  const cur = roundRows.filter((r) => wantSet.has(r.id));
  const stray = roundRows.filter((r) => !wantSet.has(r.id));
  const seen = new Set(cur.map((r) => r.id));
  const stillMissing = want.filter((id) => !seen.has(id));

  persistRound(outDir, round, runId, {
    mode,
    targetHash: hash,
    ...(state && state.openedBy ? { openedBy: state.openedBy } : {}),
  });

  const notRun = cur.filter((r) => r.verdict === 'not-run');
  const fails = cur.filter((r) => r.verdict === 'fail');
  const code =
    cur.length === 0 || (notRun.length === cur.length && cur.length > 0)
      ? EXIT.UNUSABLE
      : notRun.length
        ? EXIT.PARTIAL
        : fails.some((f) => f.severity === 'P1' || f.severity === 'P2')
          ? EXIT.FINDINGS
          : EXIT.CLEAN;

  console.log('');
  console.log('='.repeat(66));
  console.log(`ledger verify  round=${round} mode=${mode}  →  ${code === EXIT.CLEAN ? 'PASS' : code === EXIT.FINDINGS ? 'FINDINGS' : code === EXIT.PARTIAL ? 'PARTIAL' : 'NOT-RUN'} (exit ${code})`);
  console.log('='.repeat(66));
  console.log(`账本: ${ledgerPath(outDir)}`);
  if (unopened) {
    console.log('!! 本轮未经 probe 开轮（没有 capabilities.json），因此「缺能力」与「无人覆盖」无法区分。');
    console.log('   先跑 audit probe --out <dir> --url <url> [--repo <dir>]，再跑检测脚本，最后 verify。');
  }
  console.log(`适用 ${want.length} 项 / 本轮入账 ${cur.length} 项 / 补写 not-run ${added.length} 项 / 缺口 ${stillMissing.length} 项`);
  if (stray.length) console.log(`越界行 ${stray.length} 项（不属于 ${mode} 模式，不计入完备性）：${stray.map((r) => r.id).join(', ')}`);
  console.log(`fail ${fails.length}   not-run ${notRun.length}   pass ${cur.length - fails.length - notRun.length}`);
  if (stillMissing.length) {
    console.log('!! 以下 ID 连 not-run 行都没有（注册表与账本不一致，属工具缺陷）：');
    console.log('   ' + stillMissing.join(', '));
  }
  if (notRun.length) {
    console.log('');
    console.log('本轮未跑（不等于通过）：');
    for (const r of notRun) console.log(`  - ${r.id}${r.reason ? ` — ${r.reason}` : ''}`);
  }
  if (added.length === 0 && notRun.length === 0) {
    console.log('本轮未跑: 无（表为空，说明全部适用项都有结论）。');
  }
  if (code === EXIT.PARTIAL || code === EXIT.UNUSABLE) {
    console.log('');
    console.log('!! 存在未跑项。修好能力后重跑，或在下一轮显式处理；不要把它当通过。');
  }
  return code;
}

function report(outDir, opts) {
  const { round } = currentRound(outDir, opts);
  // 必须先按轮过滤再去重：否则第 2 轮的 not-run 会盖掉第 1 轮的 P1，
  // `report --round 1` 就变成一份把历史发现抹掉的报告。
  const allRows = readLedger(outDir);
  const scoped = opts.all ? allRows : allRows.filter((r) => Number(r.round) === Number(round));
  const thisRound = [...latestByVerdict(scoped).values()];
  const groups = { fail: [], notRun: [], pass: [] };
  for (const r of thisRound) {
    if (r.verdict === 'fail') groups.fail.push(r);
    else if (r.verdict === 'not-run') groups.notRun.push(r);
    else groups.pass.push(r);
  }
  groups.fail.sort((a, b) => (a.severity || 'P9').localeCompare(b.severity || 'P9') || a.id.localeCompare(b.id));

  const mode = thisRound[0]?.mode || 'whitebox';
  const want = applicable(mode).length;
  const lines = [];
  lines.push(`# 站点审查报告 · round ${round} · ${mode} 模式`);
  lines.push('');
  lines.push(
    `> 本文件含本站点安全缺陷细节，请按机密材料保管。勿整份贴入公开 issue、聊天群或第三方服务。` +
      `生成时间 ${nowIso()}，运行 ${thisRound.length}/${want} 项适用检查。`
  );
  lines.push('');
  lines.push(`## 发现（${groups.fail.length}）`);
  lines.push('');
  lines.push('| 级别 | 判据 | ID | 结论 | 证据位置 | 复现 |');
  lines.push('| --- | --- | --- | --- | --- | --- |');
  const cell = neutralizeCell;
  for (const r of groups.fail) {
    const loc = r.locator ? (r.locator.file ? `${r.locator.file}${r.locator.line ? ':' + r.locator.line : ''}` : r.locator.url || '') : '';
    lines.push(`| ${cell(r.severity)} | ${cell(r.level)} | ${cell(r.id)} | ${cell(r.title)} | ${cell(loc)} | ${cell(r.repro)} |`);
  }
  if (!groups.fail.length) lines.push('| — | — | — | 无 | — | — |');
  lines.push('');
  lines.push(`## 本轮未跑（${groups.notRun.length}）`);
  lines.push('');
  if (groups.notRun.length) {
    lines.push('| ID | 原因 | 解锁方式 |');
    lines.push('| --- | --- | --- |');
    for (const r of groups.notRun) lines.push(`| ${cell(r.id)} | ${cell(r.reason)} | ${cell(r.unblockCommand)} |`);
  } else {
    lines.push('（表为空：本轮全部适用检查都给出了结论。）');
  }
  lines.push('');
  lines.push(`## 通过（${groups.pass.length}）`);
  lines.push('');
  for (const r of groups.pass) lines.push(`- ${r.id} ${r.title}${r.lastVerified ? `（自 round ${r.lastVerified.round} 结转）` : ''}`);
  const md = lines.join('\n') + '\n';
  const file = join(outDir, `report-${round}.md`);
  writeFileSync(file, md, 'utf8');
  console.log(`报告: ${homePlaceholder(file)}`);
  console.log(`发现 ${groups.fail.length} / 未跑 ${groups.notRun.length} / 通过 ${groups.pass.length}`);
  return EXIT.CLEAN;
}

function mergeFrom(outDir, fromDir) {
  if (!existsSync(fromDir)) return usage('ledger merge', HELP, `--from 目录不存在: ${fromDir}`);
  const prev = readLedger(fromDir);
  const curIds = new Set(readLedger(outDir).map((r) => r.id));
  const carried = [];
  for (const r of prev) {
    if (curIds.has(r.id)) continue;
    carried.push(
      makeFinding({
        ...r,
        verdict: 'not-run',
        reason: `来自上一轮账本、本轮未再覆盖：${r.verdict === 'pass' ? '上轮通过' : r.verdict === 'fail' ? `上轮 ${r.severity} 发现` : '上轮未跑'}（结转，不等于本轮结论）`,
        lastVerified: { round: r.round, statement: r.verdict + (r.severity && r.severity !== '-' ? ':' + r.severity : '') },
      })
    );
  }
  const n = appendFindings(outDir, carried);
  console.log(`结转 ${n} 行（只补 lastVerified，不改历史判定）`);
  return EXIT.CLEAN;
}

/** hook 模式：只输出 ID 与计数，绝不输出 URL、路径或证据文本。 */
function outstanding(outDir) {
  const rows = [...latestByVerdict(readLedger(outDir)).values()];
  const lastRound = rows.reduce((m, r) => Math.max(m, Number(r.round) || 0), 0);
  const open = rows.filter((r) => r.verdict === 'not-run');
  if (!open.length) {
    console.log('[site-audit] 上轮无未跑项。');
    return EXIT.CLEAN;
  }
  console.log(`[site-audit] round ${lastRound} 有 ${open.length} 项未跑，需要处理：`);
  console.log('  ' + open.map((r) => r.id).join(', '));
  const byReason = new Map();
  for (const r of open) {
    const key = (r.reason || '').slice(0, 40);
    byReason.set(key, (byReason.get(key) || 0) + 1);
  }
  for (const [k, v] of byReason) console.log(`  ×${v} ${k}`);
  return EXIT.CLEAN;
}

function main(argv) {
  const sub = argv[0];
  if (!sub || sub === '-h' || sub === '--help') {
    console.log(HELP);
    return EXIT.USAGE;
  }
  let opts;
  try {
    opts = parseArgs(argv.slice(1), {
      value: ['out', 'mode', 'round', 'url', 'from', 'target-hash'],
      bool: ['all'],
    }).opts;
  } catch (e) {
    return usage('ledger', HELP, e.message);
  }

  if (sub === 'checklist') {
    console.log(renderChecklist(opts.mode));
    return EXIT.CLEAN;
  }
  if (!['verify', 'report', 'merge', 'outstanding'].includes(sub)) {
    return usage('ledger', HELP, `未知子命令 ${sub}`);
  }
  if (!opts.out) return usage('ledger ' + sub, HELP, '需要 --out');
  // --out 位置必须校验：ledger 会往那里写 report.md 并补记 not-run 行。不校验就允许把账本落进
  // 插件源码树（污染下一个 ZIP）或被审仓库（它的脚本之后会在里面被执行）。第 3 轮实测过这两种。
  guardPaths({ out: opts.out }, 'ledger.mjs');
  let outDir;
  try {
    outDir = ensureOut(opts.out);
  } catch (e) {
    // PathDenied 若一路抛出去会变成带绝对路径的栈回溯 + exit 1（看起来像「有发现」）
    return usage('ledger ' + sub, HELP, e.message);
  }

  if (sub === 'verify') return verify(outDir, opts);
  if (sub === 'report') return report(outDir, opts);
  if (sub === 'merge') {
    try {
      assertReadablePath(resolve(opts.from), { purpose: '--from 外部账本' });
    } catch (e) {
      console.error('ledger merge: ' + String(e.message || e).slice(0, 200));
      return EXIT.USAGE;
    }
    return mergeFrom(outDir, opts.from);
  }
  return outstanding(outDir);
}

process.exitCode = main(process.argv.slice(2));
