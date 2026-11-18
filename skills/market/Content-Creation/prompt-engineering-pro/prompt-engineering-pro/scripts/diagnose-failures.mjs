#!/usr/bin/env node
// diagnose-failures.mjs — 失败模式诊断引擎（v1.1.0）
// 功能: 分析 outcomes（track-outcome.mjs 记录）+ 契约审计/反模式结果，识别反复出现的失败模式，
//       按模式聚类并归因（契约缺 Non-goals / 无验证标准 / 反模式命中 / 评分低于阈值 / 输出未达标），
//       输出 pattern + root_cause + confidence。
// 实证原则: 无真实数据不空谈——诊断必须有 outcomes 或显式输入支撑；无数据时诚实返回"样本不足"。
// 确定性: 纯规则聚合，同一输入恒同输出。
// 用法:
//   node scripts/diagnose-failures.mjs              # 读 data/outcomes 聚合诊断
//   node scripts/diagnose-failures.mjs --from <outcomes.json>   # 从文件诊断
//   node scripts/diagnose-failures.mjs --json
import { readFileSync } from "node:fs";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";
import { isMain, makeOpt } from "./lib.mjs";
import { readOutcomes } from "./track-outcome.mjs";

const ROOT = join(dirname(fileURLToPath(import.meta.url)), "..");
const MIN_SAMPLE = 3; // 最少样本才给归因（防噪音）

// 失败模式识别规则（确定性聚类）
const PATTERN_RULES = [
  { id: "NO_NONGOALS", label: "契约缺 Non-goals", test: (r) => r.contract_hits && r.contract_hits > 0 && !r.ok, hint: "补显式 Non-goals / Constraints" },
  { id: "NO_VERIFICATION", label: "无验证标准", test: (r) => r.ok === false && !r.adopted, hint: "补验收条件（怎么算做对）" },
  { id: "LOW_SCORE", label: "评分低于阈值", test: (r) => typeof r.score === "number" && r.score < 55, hint: "按 Q-Score 低分维度逐项修订" },
  { id: "OUTPUT_MISMATCH", label: "输出未达标", test: (r) => r.ok === false && /output|输出/.test(r.note || ""), hint: "用 output-check.mjs 定位输出偏差" },
];

export function diagnoseFailures({ records = null, dir = ROOT } = {}) {
  const recs = records !== null ? records : readOutcomes({ dir });
  if (!Array.isArray(recs) || !recs.length) {
    return { ok: true, total: 0, patterns: [], root_causes: [], confidence: 0, verdict: "样本不足：暂无 outcomes 数据（track-outcome.mjs --event 记录后再诊断）", note: "实证原则：无真实数据不空谈失败诊断" };
  }
  const failed = recs.filter((r) => r.ok === false);
  if (!failed.length) {
    return { ok: true, total: recs.length, patterns: [], root_causes: [], confidence: 100, verdict: "近期记录无失败样本", note: "样本充足但无失败，无需诊断" };
  }
  // 聚类：按 PATTERN_RULES 统计
  const counts = {};
  for (const p of PATTERN_RULES) counts[p.id] = 0;
  for (const r of failed) {
    for (const p of PATTERN_RULES) {
      if (p.test(r)) counts[p.id]++;
    }
  }
  const patterns = Object.entries(counts)
    .filter(([, c]) => c > 0)
    .sort((a, b) => b[1] - a[1])
    .map(([id, count]) => {
      const rule = PATTERN_RULES.find((p) => p.id === id);
      return { id, label: rule.label, count, hint: rule.hint };
    });
  // 归因：按引擎分布 + 最高频模式
  const byEngine = {};
  for (const r of failed) {
    if (!r.engine) continue;
    byEngine[r.engine] = (byEngine[r.engine] || 0) + 1;
  }
  const topEngine = Object.entries(byEngine).sort((a, b) => b[1] - a[1])[0] || null;
  const rootCauses = patterns.slice(0, 3).map((p) => ({
    pattern: p.label,
    root_cause: `反复出现「${p.label}」（${p.count} 次）`,
    confidence: Math.min(95, Math.round((p.count / failed.length) * 100)),
    hint: p.hint,
  }));
  const confidence = recs.length >= MIN_SAMPLE ? Math.min(95, Math.round((patterns.reduce((a, p) => a + p.count, 0) / failed.length) * 100)) : 30;
  return {
    ok: true,
    total: recs.length,
    failed: failed.length,
    success_rate: recs.length ? Math.round(((recs.length - failed.length) / recs.length) * 100) : null,
    patterns,
    root_causes: rootCauses,
    top_engine: topEngine ? { engine: topEngine[0], fail_count: topEngine[1] } : null,
    confidence,
    verdict: confidence >= 60 ? `诊断置信度 ${confidence}%：建议按 root_causes 逐项修订，再跑 run-eval 回归` : `样本/信号不足（置信度 ${confidence}%）：建议累积更多 outcomes 再诊断`,
  };
}

// ================= CLI =================
if (isMain(import.meta)) {
  const args = process.argv.slice(2);
  const opt = makeOpt(args);
  if (args.includes("--help") || args.includes("-h")) {
    console.log("用法: node scripts/diagnose-failures.mjs [--from <outcomes.json>] [--json]");
    console.log("说明: 实证原则——无真实 outcomes 数据不空谈诊断；样本 ≥3 才给归因。");
    process.exit(0);
  }
  const wantJson = args.includes("--json");
  const fromPath = opt("from");
  const dir = opt("dir") || ROOT;
  let records = null;
  if (fromPath) {
    try {
      records = JSON.parse(readFileSync(fromPath, "utf8").replace(/^\uFEFF/, ""));
    } catch (e) {
      console.error(`✗ 读取失败: ${e.message}`);
      process.exit(2);
    }
  }
  let result;
  try {
    result = diagnoseFailures({ records, dir });
  } catch (e) {
    console.error(`✗ ${e.message}`);
    process.exit(1);
  }
  if (wantJson) {
    process.stdout.write(JSON.stringify(result, null, 2) + "\n");
  } else {
    console.log("=== 失败模式诊断 ===");
    console.log(`样本: ${result.total} 条 · 失败 ${result.failed || 0}${result.success_rate !== null ? ` · 成功率 ${result.success_rate}%` : ""}`);
    if (result.patterns && result.patterns.length) {
      console.log("失败模式:");
      for (const p of result.patterns) console.log(`  ${p.label} ×${p.count}`);
      console.log("\n归因:");
      for (const rc of result.root_causes) console.log(`  [${rc.confidence}%] ${rc.root_cause} → ${rc.hint}`);
    } else {
      console.log(`\n${result.verdict}`);
    }
    if (result.top_engine) console.log(`\n最高失败引擎: ${result.top_engine.engine}（${result.top_engine.fail_count} 次）`);
    if (result.note) console.log(`\n${result.note}`);
  }
}
