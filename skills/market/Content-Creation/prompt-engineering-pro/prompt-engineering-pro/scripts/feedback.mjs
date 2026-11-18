#!/usr/bin/env node
// feedback.mjs — 反馈采集引擎（P0，进化闭环的上游）
// 能力:
//   1. 记录隐式信号: 用户对 skill 的实际使用行为（构建/评分/压缩/诊断/领域/模板/分数）
//   2. 记录显式信号: 用户主动评分（--rate 星级）或接受/拒绝建议
//   3. 数据落盘 data/feedback/*.json；list 查看、clear 清空（用户可控逃生口）
//   4. 供 learner.mjs 读取，驱动画像自动学习
// 设计原则: 只采集用户对本 skill 的使用行为，不越权采集其他数据
// 用法:
//   node scripts/feedback.mjs record --action build --domain game --template GAME-DEV --score 78
//   node scripts/feedback.mjs rate --stars 4 --note 结构清晰
//   node scripts/feedback.mjs list --json
//   node scripts/feedback.mjs clear
import { readdirSync, readFileSync, writeFileSync, existsSync, mkdirSync, rmSync } from "node:fs";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";
import { safePath, safeId, isMain, makeOpt } from "./lib.mjs";

const ROOT = join(dirname(fileURLToPath(import.meta.url)), "..");
const ALLOWED_ACTIONS = new Set(["build", "score", "compress", "diagnose", "migrate", "verify", "generate", "rate"]);

function fbDir(base) {
  return join(safePath(base), "data", "feedback");
}

function listRecords(base) {
  const d = fbDir(base);
  if (!existsSync(d)) return [];
  const out = [];
  for (const f of readdirSync(d)) {
    if (!f.endsWith(".json")) continue;
    try {
      out.push(JSON.parse(readFileSync(join(d, f), "utf8").replace(/^\uFEFF/, "")));
    } catch { /* 跳过损坏记录 */ }
  }
  return out.sort((a, b) => (a.ts < b.ts ? -1 : 1));
}

export function recordFeedback({ action = null, domain = null, template = null, score = null, stars = null, note = null, len = null, dir = ROOT } = {}) {
  if (!action) return { ok: false, error: "缺少 --action（record 用法见注释）" };
  if (!ALLOWED_ACTIONS.has(action)) return { ok: false, error: `未知 action: ${action}（可选: ${[...ALLOWED_ACTIONS].join("/")}）` };
  if (stars !== null && (stars < 1 || stars > 5)) return { ok: false, error: "stars 须在 1-5 之间" };
  if (score !== null && (score < 0 || score > 100)) return { ok: false, error: "score 须在 0-100 之间" };
  if (len !== null && (len < 0 || len > 1000000)) return { ok: false, error: "len 越界" };
  if (note !== null && String(note).length > 200) return { ok: false, error: "note 过长（≤200 字符）" };
  const d = fbDir(dir);
  mkdirSync(d, { recursive: true });
  const id = safeId(`${Date.now()}-${Math.random().toString(36).slice(2, 8)}`);
  const rec = {
    id,
    ts: new Date().toISOString(),
    type: stars !== null ? "explicit" : "implicit",
    action,
    domain: domain || null,
    template: template || null,
    score: score !== null ? Number(score) : null,
    stars: stars !== null ? Number(stars) : null,
    len: len !== null ? Number(len) : null,
    note: note !== null ? String(note).slice(0, 200) : null,
  };
  writeFileSync(join(d, `${id}.json`), JSON.stringify(rec, null, 2) + "\n", "utf8");
  return { ok: true, record: rec };
}

export function clearFeedback({ dir = ROOT } = {}) {
  const d = fbDir(dir);
  if (!existsSync(d)) return { ok: true, cleared: 0 };
  let n = 0;
  for (const f of readdirSync(d)) {
    if (f.endsWith(".json")) {
      rmSync(join(d, f), { force: true });
      n++;
    }
  }
  return { ok: true, cleared: n };
}

// ================= CLI =================
if (isMain(import.meta)) {
  const args = process.argv.slice(2);
  const opt = makeOpt(args);
  const json = args.includes("--json");
  // 数值参数解析：缺失/空串 → null（避免 undefined/NaN 污染）
  const num = (v) => (v === undefined || v === null || v === "" ? null : Number(v));
  const cmd = args[0] || "list";
  if (cmd === "record") {
    const r = recordFeedback({ action: opt("action"), domain: opt("domain"), template: opt("template"), score: num(opt("score")), stars: num(opt("stars")), note: opt("note"), len: num(opt("len")) });
    if (!r.ok) {
      process.stderr.write(`✗ ${r.error}\n`);
      process.exit(2);
    }
    if (json) process.stdout.write(JSON.stringify(r.record, null, 2) + "\n");
    else process.stdout.write(`✓ 已记录反馈（id=${r.record.id}）\n`);
  } else if (cmd === "rate") {
    const r = recordFeedback({ action: "rate", domain: opt("domain"), stars: num(opt("stars")), note: opt("note") });
    if (!r.ok) {
      process.stderr.write(`✗ ${r.error}\n`);
      process.exit(2);
    }
    if (json) process.stdout.write(JSON.stringify(r.record, null, 2) + "\n");
    else process.stdout.write(`✓ 已记录评分（${r.record.stars} 星）\n`);
  } else if (cmd === "list") {
    const recs = listRecords(ROOT);
    if (json) process.stdout.write(JSON.stringify(recs, null, 2) + "\n");
    else {
      process.stdout.write(`反馈记录 ${recs.length} 条\n`);
      for (const r of recs) {
        process.stdout.write(`  ${r.ts} [${r.type}] ${r.action}${r.domain ? ` domain=${r.domain}` : ""}${r.template ? ` template=${r.template}` : ""}${r.score !== null ? ` score=${r.score}` : ""}${r.stars !== null ? ` stars=${r.stars}` : ""}${r.note ? ` note=${r.note}` : ""}\n`);
      }
    }
  } else if (cmd === "clear") {
    const r = clearFeedback({ dir: ROOT });
    if (json) process.stdout.write(JSON.stringify(r, null, 2) + "\n");
    else process.stdout.write(`✓ 已清空 ${r.cleared} 条反馈\n`);
  } else {
    process.stderr.write("用法: feedback record|rate|list|clear（--json 输出 JSON）\n");
    process.exit(2);
  }
}
