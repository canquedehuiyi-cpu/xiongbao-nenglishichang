// subagents.mjs — 定位并汇总 Agent 子代理的独立富转录。
//
// 为什么必须单独读：子代理（Agent 工具）的每次往返只写进它自己的转录，主转录里只留
// 一条 tool_result（子代理的最终返回文本）。只算主转录会漏掉子代理的全部消耗
// （实测会话 ca2f7834：主链 58 次 8.88 Credits，3 个 Explore 子代理另有 87 次 8.41 Credits，
// 占官方总账 43%）。
//
// 平台事实（实测，旧布局）：
//   <slug>\<sessionId>\subagents\agent-<agentId>.jsonl      逐 entry 带 message.usage
//   <slug>\<sessionId>\subagents\agent-<agentId>.meta.json  agentType / description / toolUseId
//   <slug>\<sessionId>\subagents\task-<id>.json             TaskCreate 快照，不含 usage，跳过
//   新布局多一层：<slug>\transcript\<sessionId>\subagents\，故按候选目录逐个探。
//   主转录的 toolUseResult.transcriptPath 也直接给出子代理转录绝对路径，但本模块改用目录
//   扫描，不依赖该字段，对缺字段的客户端版本同样可用。
//   注意：isSidechain 在主转录里恒为 false，不能用它判子代理。
//
// 健壮性：本模块运行在 Stop 钩子链路里，钩子非 0 退出会阻断对话，故任何单个子代理
// 读失败都只记进 items[].error，绝不向上抛。

import fs from 'node:fs';
import path from 'node:path';
import { readEntries } from './transcript.mjs';
import { buildReport } from './breakdown.mjs';

const AGENT_RE = /^agent-(.+)\.jsonl$/;

/** 由主转录路径推出 subagents 目录候选（新旧布局都试）。 */
export function subagentDirCandidates(transcriptPath) {
  const dir = path.dirname(transcriptPath);
  const id = path.basename(transcriptPath, '.jsonl');
  return [path.join(dir, id, 'subagents'), path.join(dir, '..', id, 'subagents')];
}

/** 返回第一个存在的 subagents 目录；都不存在返回 null。 */
export function resolveSubagentDir(transcriptPath) {
  for (const d of subagentDirCandidates(transcriptPath)) {
    try {
      if (fs.statSync(d).isDirectory()) return d;
    } catch {
      /* 候选不存在，试下一个 */
    }
  }
  return null;
}

/** 扫出子代理清单：[{ agentId, transcript, meta }]，按同名 .meta.json 配对（缺失则 meta 为 null）。
 *  同时回传 probed（试过的候选目录），供报告区分「真没子代理」与「路径没找对」。 */
export function listSubagents(transcriptPath) {
  const probed = subagentDirCandidates(transcriptPath);
  const dir = resolveSubagentDir(transcriptPath);
  if (!dir) return { dir: null, probed, items: [] };
  let names;
  try {
    names = fs.readdirSync(dir);
  } catch {
    return { dir, probed, items: [] };
  }
  const items = [];
  for (const fn of names) {
    const m = AGENT_RE.exec(fn);
    if (!m) continue; // 跳过 task-*.json 与 .meta.json
    const transcript = path.join(dir, fn);
    const metaPath = path.join(dir, `agent-${m[1]}.meta.json`);
    let meta = null;
    try {
      meta = JSON.parse(fs.readFileSync(metaPath, 'utf8'));
    } catch {
      /* 无 meta 或损坏：agentType/description 留 null，不影响计费汇总 */
    }
    items.push({ agentId: m[1], transcript, meta });
  }
  return { dir, probed, items };
}

const num = (v) => (typeof v === 'number' && isFinite(v) ? v : 0);
const round3 = (v) => Number(num(v).toFixed(3));

function emptyTotals() {
  return { roundTrips: 0, billedInputTokens: 0, credits: 0, originalCredits: 0 };
}

/**
 * 汇总子代理消耗，并与主链合并成 combined（官方 UI 的一场会话扣费 ≈ 主链 + 各子代理）。
 * @param {string} transcriptPath 主转录路径
 * @param {object} main 主链报告（取其 totals 与 session.cwd）
 */
export function summarizeSubagents(transcriptPath, main, proxyUsage) {
  const mainTotals = main?.totals || {};
  const cwd = main?.session?.cwd || null;
  const { dir, probed, items: found } = listSubagents(transcriptPath);

  const items = [];
  const totals = emptyTotals();
  for (const f of found) {
    const row = {
      agentId: f.agentId,
      agentType: f.meta?.agentType ?? null,
      description: f.meta?.description ?? null,
      toolUseId: f.meta?.toolUseId ?? null,
      roundTrips: 0,
      billedInputTokens: 0,
      peakContextRatio: 0,
      credits: 0,
      originalCredits: 0,
      error: null,
    };
    try {
      const rep = buildReport(readEntries(f.transcript), { cwd, proxyUsage });
      row.roundTrips = num(rep.session.roundTrips);
      row.billedInputTokens = num(rep.totals.billedInputTokens);
      row.peakContextRatio = Number(num(rep.context.peakContextRatio).toFixed(4));
      row.credits = round3(rep.totals.credits);
      row.originalCredits = round3(rep.totals.originalCredits);
      // 转录存在但一次 usage 都没有：与「新布局客户端不写 usage」同症，标出来别当 0 消耗。
      if (row.roundTrips === 0) row.error = '转录不含 usage（客户端未写入）';
    } catch (err) {
      row.error = String(err?.message || err);
    }
    totals.roundTrips += row.roundTrips;
    totals.billedInputTokens += row.billedInputTokens;
    totals.credits = Number((totals.credits + row.credits).toFixed(3));
    totals.originalCredits = Number((totals.originalCredits + row.originalCredits).toFixed(3));
    items.push(row);
  }

  // 消耗大的排前面，与报告其余榜单口径一致。
  items.sort((a, b) => b.credits - a.credits || b.roundTrips - a.roundTrips);

  // reason：单一个 scanned:false 会把三种情况混在一起——本就没派子代理、目录在但没
  // agent 文件、文件在但转录无 usage（IDE 端症）。分开后才看得出是该修路径还是本来就空。
  const reason =
    items.length === 0
      ? dir
        ? 'dir-empty'
        : 'no-dir'
      : totals.roundTrips > 0
        ? 'ok'
        : 'no-usage';

  return {
    scanned: dir != null,
    dir,
    probedPaths: probed,
    reason,
    count: items.length,
    items,
    totals,
    combined: {
      roundTrips: num(mainTotals.roundTrips ?? main?.session?.roundTrips) + totals.roundTrips,
      billedInputTokens: num(mainTotals.billedInputTokens) + totals.billedInputTokens,
      credits: Number((num(mainTotals.credits) + totals.credits).toFixed(3)),
      originalCredits: Number((num(mainTotals.originalCredits) + totals.originalCredits).toFixed(3)),
    },
  };
}
