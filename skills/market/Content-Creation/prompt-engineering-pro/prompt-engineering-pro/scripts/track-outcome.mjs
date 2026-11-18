#!/usr/bin/env node
// track-outcome.mjs — 执行反馈追踪引擎（v1.1.0）
// 功能: 记录每次生成/评分/契约审计/评测的执行 outcome（成功/质量分/耗时/契约缺陷命中/采纳与否），
//       写入 data/outcomes/ 结构化按月记录；输出滚动统计（成功率/平均分/最近记录）。
// 数据治理: 仅存本 skill 工作区 data/；不采集任何可识别用户身份的信息（无 user/name 字段）；
//          默认保留 90 天；--purge 清除、--export 导出；字段白名单校验防脏数据。
// 确定性: 纯规则，同一输入恒同输出；outcome 不含可执行危险内容。
// 用法:
//   node scripts/track-outcome.mjs --event '{"engine":"score-prompt","ok":true,"score":78}'
//   node scripts/track-outcome.mjs --stats
//   node scripts/track-outcome.mjs --purge --confirm
//   node scripts/track-outcome.mjs --export
import { readFileSync, writeFileSync, existsSync, mkdirSync, readdirSync } from "node:fs";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";
import { safePath, isMain, makeOpt } from "./lib.mjs";

const ROOT = join(dirname(fileURLToPath(import.meta.url)), "..");
const DEFAULT_RETENTION_DAYS = 90; // 数据治理：默认保留期

// 字段白名单（防脏数据/防注入；不采集身份信息）
const ALLOWED_FIELDS = {
  engine: "string",
  task_type: "string",
  domain: "string",
  model_family: "string",
  technique: "string",
  ok: "boolean",
  score: "number",
  contract_hits: "number",
  duration_ms: "number",
  adopted: "boolean",
  note: "string",
};

function outcomesDir(base) {
  return join(safePath(base), "data", "outcomes");
}

function monthFile(base, d) {
  const y = d.getUTCFullYear();
  const m = String(d.getUTCMonth() + 1).padStart(2, "0");
  return join(outcomesDir(base), `${y}-${m}.jsonl`);
}

export function readOutcomes({ dir = ROOT, limit = 1000 } = {}) {
  const base = safePath(dir);
  const d = outcomesDir(base);
  if (!existsSync(d)) return [];
  const out = [];
  const months = readdirSync(d).filter((f) => f.endsWith(".jsonl")).sort();
  for (const f of months) {
    try {
      const lines = readFileSync(join(d, f), "utf8").split("\n").filter((l) => l.trim());
      for (const l of lines) {
        try {
          const rec = JSON.parse(l);
          out.push(rec);
          if (out.length >= limit) break;
        } catch { /* 跳过损坏行 */ }
      }
    } catch { /* 跳过不可读文件 */ }
    if (out.length >= limit) break;
  }
  return out;
}

// 净化记录：仅保留白名单字段 + 时间戳；丢弃身份/未知字段
function sanitizeRec(event) {
  if (!event || typeof event !== "object" || Array.isArray(event)) event = {}; // 防 null/数组脏输入
  const rec = { ts: new Date().toISOString() };
  for (const [k, type] of Object.entries(ALLOWED_FIELDS)) {
    const v = event[k];
    if (v === undefined || v === null) continue;
    if (type === "string" && typeof v === "string") rec[k] = String(v).slice(0, 200);
    else if (type === "boolean" && typeof v === "boolean") rec[k] = v;
    else if (type === "number" && typeof v === "number" && Number.isFinite(v)) rec[k] = v;
    // 其它类型静默丢弃（防脏数据）
  }
  return rec;
}

export function recordOutcome({ event = {}, dir = ROOT } = {}) {
  const base = safePath(dir);
  const rec = sanitizeRec(event);
  if (!Object.keys(rec).filter((k) => k !== "ts").length) {
    return { ok: false, error: "事件字段为空或全部非法（合法字段: engine/task_type/domain/model_family/technique/ok/score/contract_hits/duration_ms/adopted/note）" };
  }
  const d = outcomesDir(base);
  mkdirSync(d, { recursive: true });
  const file = monthFile(base, new Date());
  try {
    writeFileSync(file, JSON.stringify(rec) + "\n", { flag: "a", encoding: "utf8" });
    return { ok: true, recorded: rec };
  } catch (e) {
    return { ok: false, error: e.message };
  }
}

export function outcomeStats({ dir = ROOT } = {}) {
  const recs = readOutcomes({ dir });
  const ok = recs.filter((r) => r.ok === true).length;
  const scores = recs.filter((r) => typeof r.score === "number").map((r) => r.score);
  const adopted = recs.filter((r) => r.adopted === true).length;
  const avgScore = scores.length ? Math.round((scores.reduce((a, b) => a + b, 0) / scores.length) * 10) / 10 : null;
  const byEngine = {};
  for (const r of recs) {
    if (!r.engine) continue;
    byEngine[r.engine] = byEngine[r.engine] || { total: 0, ok: 0, scoreSum: 0, scoreN: 0 };
    const e = byEngine[r.engine];
    e.total++;
    if (r.ok) e.ok++;
    if (typeof r.score === "number") { e.scoreSum += r.score; e.scoreN++; }
  }
  return {
    ok: true,
    total: recs.length,
    ok_count: ok,
    success_rate: recs.length ? Math.round((ok / recs.length) * 100) : null,
    avg_score: avgScore,
    adopted_count: adopted,
    by_engine: Object.fromEntries(Object.entries(byEngine).map(([k, v]) => [k, { total: v.total, ok: v.ok, avg_score: v.scoreN ? Math.round((v.scoreSum / v.scoreN) * 10) / 10 : null }])),
    retention_days: DEFAULT_RETENTION_DAYS,
    note: "数据治理：仅存工作区 data/，不采集可识别身份信息，默认保留 90 天（--purge 清除 / --export 导出）",
  };
}

export function purgeOutcomes({ dir = ROOT, confirm = false, older_than_days = DEFAULT_RETENTION_DAYS } = {}) {
  if (!confirm) return { ok: false, error: "需显式 --confirm 才执行清除（数据治理保护）" };
  const base = safePath(dir);
  const d = outcomesDir(base);
  if (!existsSync(d)) return { ok: true, removed: 0 };
  const now = Date.now();
  let removed = 0;
  for (const f of readdirSync(d)) {
    if (!f.endsWith(".jsonl")) continue;
    const m = f.match(/^(\d{4})-(\d{2})\.jsonl$/);
    if (m) {
      const fileTime = new Date(Date.UTC(Number(m[1]), Number(m[2]) - 1, 1)).getTime();
      const ageDays = (now - fileTime) / 86400000;
      if (ageDays > older_than_days) {
        try {
          writeFileSync(join(d, f), "", "utf8");
          removed++;
        } catch { /* 跳过 */ }
      }
    }
  }
  return { ok: true, removed, note: `按默认保留期 ${DEFAULT_RETENTION_DAYS} 天清理过期月度文件` };
}

export function exportOutcomes({ dir = ROOT, format = "json" } = {}) {
  const recs = readOutcomes({ dir, limit: 100000 });
  if (format === "jsonl") return { ok: true, format, count: recs.length, content: recs.map((r) => JSON.stringify(r)).join("\n") };
  return { ok: true, format: "json", count: recs.length, content: JSON.stringify(recs, null, 2) };
}

// ================= CLI =================
if (isMain(import.meta)) {
  const args = process.argv.slice(2);
  const opt = makeOpt(args);
  if (args.includes("--help") || args.includes("-h")) {
    console.log("用法:");
    console.log("  node scripts/track-outcome.mjs --event '<JSON>'   记录一条 outcome（含空格建议用 --event-file）");
    console.log("  node scripts/track-outcome.mjs --event-file <ev.json>   从文件记录");
    console.log("  node scripts/track-outcome.mjs --stats             滚动统计");
    console.log("  node scripts/track-outcome.mjs --purge --confirm   清除过期记录");
    console.log("  node scripts/track-outcome.mjs --export [--format json|jsonl]  导出");
    process.exit(0);
  }
  const dir = opt("dir") || ROOT;
  if (args.includes("--stats")) {
    const r = outcomeStats({ dir });
    console.log(`总记录: ${r.total} · 成功 ${r.ok_count}（成功率 ${r.success_rate}%）`);
    if (r.avg_score !== null) console.log(`平均分: ${r.avg_score}`);
    console.log(`采纳数: ${r.adopted_count}`);
    const es = Object.entries(r.by_engine);
    if (es.length) {
      console.log("分引擎:");
      for (const [k, v] of es) console.log(`  ${k}: ${v.total} 条 · ok ${v.ok} · 均分 ${v.avg_score === null ? "-" : v.avg_score}`);
    }
    console.log(`\n${r.note}`);
    process.exit(0);
  }
  if (args.includes("--purge")) {
    const r = purgeOutcomes({ dir, confirm: args.includes("--confirm") });
    if (!r.ok) { console.error(`✗ ${r.error}`); process.exit(2); }
    console.log(`已清除过期记录 ${r.removed} 个文件`);
    process.exit(0);
  }
  if (args.includes("--export")) {
    const r = exportOutcomes({ dir, format: opt("format") || "json" });
    if (!r.ok) { console.error(`✗ ${r.error}`); process.exit(2); }
    console.log(r.content);
    process.exit(0);
  }
  const evRaw = opt("event");
  const evFile = opt("event-file");
  if (!evRaw && !evFile) {
    console.error("✗ 缺少 --event（记录）或 --stats/--purge/--export（查看/维护）；JSON 建议用 --event-file <json> 传（Windows 命令行双引号兼容）");
    process.exit(2);
  }
  let ev;
  if (evFile) {
    try {
      ev = JSON.parse(readFileSync(safePath(evFile), "utf8").replace(/^\uFEFF/, ""));
    } catch (e) {
      console.error(`✗ 读取 --event-file 失败: ${e.message}`);
      process.exit(2);
    }
  } else {
    try {
      ev = JSON.parse(evRaw);
    } catch {
      console.error("✗ --event 需为合法 JSON（含空格建议改用 --event-file <json 文件>）");
      process.exit(2);
    }
  }
  const r = recordOutcome({ event: ev, dir });
  if (!r.ok) {
    console.error(`✗ ${r.error}`);
    process.exit(2);
  }
  console.log(`已记录: ${JSON.stringify(r.recorded)}`);
}
