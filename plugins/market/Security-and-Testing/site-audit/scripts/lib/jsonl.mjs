/**
 * finding 的读写与 schema 校验。JSONL：一行一项检查一轮。
 * 只追加；merge 只结转 lastVerified，不改历史行。
 */

import { existsSync, readFileSync, appendFileSync, writeFileSync, mkdirSync } from 'node:fs';
import { join } from 'node:path';
import { redact, nowIso } from './tools.mjs';

export const VERDICTS = new Set(['pass', 'fail', 'not-run']);
export const LEVELS = new Set(['M', 'S', 'J']);

export const LEDGER_FILE = 'findings.jsonl';

export function ledgerPath(outDir) {
  return join(outDir, LEDGER_FILE);
}

/**
 * 构造一行 finding。**所有**自由文本字段都在这里统一脱敏——
 * 只在 evidence 上脱敏是不够的：token 同样会出现在 title、repro、nextAction、
 * locator.url 里（例如一条带 `?share_token=ghp_…` 的外链）。
 * @param {object} f
 */
export function makeFinding(f) {
  const clean = (v, max) => (v == null || v === '' ? '' : redact(v, max).text);
  const loc = f.locator
    ? {
        ...(f.locator.file ? { file: clean(f.locator.file, 200) } : {}),
        ...(f.locator.line ? { line: Number(f.locator.line) } : {}),
        ...(f.locator.url ? { url: clean(f.locator.url, 240) } : {}),
      }
    : null;
  const row = {
    round: Number(f.round) || 0,
    runId: f.runId || '',
    ts: f.ts || nowIso(),
    id: f.id,
    mode: f.mode,
    targetHash: f.targetHash || '',
    verdict: f.verdict,
    level: f.level,
    severity: f.verdict === 'fail' ? f.severity || 'P3' : '-',
    title: clean(f.title, 200),
    evidence: clean(f.evidence, f.evidenceMax || 200),
    locator: loc,
    repro: clean(f.repro, 300),
    script: f.script || '',
    reason: f.verdict === 'not-run' ? clean(f.reason, 240) : '',
    unblockCommand: clean(f.unblockCommand, 240),
    lastVerified: f.lastVerified || null,
    supersedes: f.supersedes || null,
    nextAction: clean(f.nextAction, 240),
    authorizedBy: clean(f.authorizedBy, 120),
  };
  if (!row.id) throw new Error('finding 缺 id');
  if (!VERDICTS.has(row.verdict)) throw new Error(`finding ${row.id}: verdict=${row.verdict}`);
  if (!LEVELS.has(row.level)) throw new Error(`finding ${row.id}: level=${row.level}`);
  if (row.verdict === 'not-run' && !row.reason) {
    throw new Error(`finding ${row.id}: not-run 必须写 reason（静默跳过是这套工具要修的 bug）`);
  }
  return row;
}

export function appendFindings(outDir, rows) {
  if (!rows.length) return 0;
  if (!existsSync(outDir)) mkdirSync(outDir, { recursive: true });
  const p = ledgerPath(outDir);
  appendFileSync(p, rows.map((r) => JSON.stringify(r)).join('\n') + '\n', 'utf8');
  return rows.length;
}

/** @returns {Array<object>} 解析失败的行会被丢弃但计数返回到 meta 由调用方决定 */
export function readLedger(outDir) {
  const p = ledgerPath(outDir);
  if (!existsSync(p)) return [];
  const out = [];
  for (const line of readFileSync(p, 'utf8').split(/\r?\n/)) {
    const t = line.trim();
    if (!t) continue;
    try {
      const row = JSON.parse(t);
      if (row && typeof row === 'object' && row.id) out.push(row);
    } catch {
      /* 容忍被截断的尾行 */
    }
  }
  return out;
}

/**
 * capabilities.json / state.json 同样是会被转出去的产物：里面天然带本机绝对路径
 * （被审仓库、临时副本、node/npm/git 的解析路径）。账本行有 makeFinding 兜底，
 * 这两个文件此前是裸写 JSON——安装者的用户名与家目录就这么进了目录（第 3 轮实测）。
 * 落盘前深度脱敏：只处理字符串值，键名与结构不动。
 */
function deepRedact(v) {
  if (typeof v === 'string') return redact(v, 400).text;
  if (Array.isArray(v)) return v.map(deepRedact);
  if (v && typeof v === 'object') {
    const o = {};
    for (const [k, val] of Object.entries(v)) o[k] = deepRedact(val);
    return o;
  }
  return v;
}


export function writeJson(outDir, name, obj) {
  const NL = String.fromCharCode(10);
  writeFileSync(join(outDir, name), JSON.stringify(deepRedact(obj), null, 2) + NL, 'utf8');
}

export function readJsonIfExists(outDir, name) {
  const p = join(outDir, name);
  if (!existsSync(p)) return null;
  try {
    return JSON.parse(readFileSync(p, 'utf8'));
  } catch {
    return null;
  }
}

const VERDICT_RANK = { fail: 3, pass: 2, 'not-run': 1 };

/**
 * 每轮一个 runId；同一 id 取 ts 最大的一行。
 * ts 相同时按 verdict 强度取（fail > pass > not-run）：
 * 否则 verify 补写的 not-run 会在同一毫秒里盖掉刚记下的 P1，报告里凭空少一条发现。
 */
export function latestByVerdict(rows) {
  const byId = new Map();
  for (const r of rows) {
    const prev = byId.get(r.id);
    if (!prev) {
      byId.set(r.id, r);
      continue;
    }
    const a = String(prev.ts);
    const b = String(r.ts);
    if (b > a) byId.set(r.id, r);
    else if (b === a && (VERDICT_RANK[r.verdict] || 0) > (VERDICT_RANK[prev.verdict] || 0)) byId.set(r.id, r);
  }
  return byId;
}
