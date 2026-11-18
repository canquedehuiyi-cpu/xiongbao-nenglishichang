#!/usr/bin/env node
// learner.mjs — 自动学习引擎（P0，进化闭环的核心：从使用行为提炼用户画像）
// 能力:
//   1. 读 data/feedback/ 记录，统计领域/模板/评分/长度分布
//   2. 提炼画像建议（domain / template_pref / verbosity），样本不足时降级提示
//   3. 默认 dry-run 只给建议；--apply 才写入 habit-profile（用户可控）
//   4. 学习只影响"体验默认值"，不改变任何评分/质量门禁结果（中立性保证）
//   5. (v1.0.5) 规范变更学习: verify-spec 检测到规范变更时调用 recordSpecChange 写入学习记录
//   6. (v1.0.5) 生命周期提醒: specLearning 汇总规则快照的生效/废止状态，输出时效提醒
//   7. (v1.0.8) 路由偏好学习: routeLearning 记录"领域×模型族×技法"有效组合（画像层，只记不改）
//   8. (v1.0.9) 反馈驱动健康度: 读取 data/outcomes（track-outcome 记录）输出技能健康度（成功率/使用频次/最近活跃）
//   9. (v1.0.9) 数据治理: --purge 清除过期 outcomes、--export 导出（对齐 track-outcome 保留期 90 天）
// 设计原则: 无把握不臆造——只基于可观测信号给建议；样本 <3 不自动 apply
// 用法:
//   node scripts/learner.mjs
//   node scripts/learner.mjs --apply
//   node scripts/learner.mjs --json
//   node scripts/learner.mjs --purge --confirm      # 数据治理：清除过期 outcomes
//   node scripts/learner.mjs --export               # 数据治理：导出 outcomes
import { readdirSync, readFileSync, writeFileSync, existsSync, mkdirSync } from "node:fs";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";
import { safePath, isMain, makeOpt } from "./lib.mjs";
import { setKey, getProfile } from "./habit-profile.mjs";
import { readOutcomes, purgeOutcomes, exportOutcomes } from "./track-outcome.mjs";

const ROOT = join(dirname(fileURLToPath(import.meta.url)), "..");
const MIN_SAMPLE = 3; // 自动 apply 的最低样本数（保守阈值）
const MAX_SPEC_CHANGES = 100; // 规范变更学习记录上限

// ---------- 规范变更学习（v1.0.5 新增） ----------
export function specChangePath(base) {
  return join(safePath(base), "data", "learning", "spec-changes.json");
}

export function recordSpecChange({ platform = "", changed_names = [], detail = "", dir = ROOT } = {}) {
  const base = safePath(dir);
  const p = specChangePath(base);
  let list = [];
  try {
    if (existsSync(p)) list = JSON.parse(readFileSync(p, "utf8").replace(/^\uFEFF/, ""));
    if (!Array.isArray(list)) list = [];
  } catch { list = []; }
  list.push({
    ts: new Date().toISOString(),
    platform,
    changed_names: changed_names.slice(0, 20),
    detail: String(detail || "").slice(0, 500),
  });
  if (list.length > MAX_SPEC_CHANGES) list = list.slice(-MAX_SPEC_CHANGES);
  try {
    mkdirSync(dirname(p), { recursive: true });
    writeFileSync(p, JSON.stringify(list, null, 2) + "\n", "utf8");
    return { ok: true, count: list.length };
  } catch (e) {
    return { ok: false, error: e.message };
  }
}

export function readSpecChanges(dir = ROOT) {
  const p = specChangePath(dir);
  try {
    if (!existsSync(p)) return [];
    const v = JSON.parse(readFileSync(p, "utf8").replace(/^\uFEFF/, ""));
    return Array.isArray(v) ? v : [];
  } catch {
    return [];
  }
}

// ---------- 路由偏好学习（v1.0.8，画像层：只记不改） ----------
// 记录"哪些 领域×模型族×技法 组合对用户实际有效"，与 recordSpecChange 并列（data/learning/）。
// 边界：只做学习记录与观察输出，不产出模板/技能修改提案（那是 1.0.9 技能层职责）。
export function routeLearnPath(base) {
  return join(safePath(base), "data", "learning", "route-learning.json");
}

export function recordRouteLearn({ domain = "", model_family = "", technique = "", effective = true, dir = ROOT } = {}) {
  const base = safePath(dir);
  const p = routeLearnPath(base);
  let list = [];
  try {
    if (existsSync(p)) list = JSON.parse(readFileSync(p, "utf8").replace(/^\uFEFF/, ""));
    if (!Array.isArray(list)) list = [];
  } catch { list = []; }
  list.push({
    ts: new Date().toISOString(),
    domain: String(domain || "").slice(0, 40),
    model_family: String(model_family || "").slice(0, 40),
    technique: String(technique || "").slice(0, 40),
    effective: !!effective,
  });
  if (list.length > MAX_SPEC_CHANGES) list = list.slice(-MAX_SPEC_CHANGES);
  try {
    mkdirSync(dirname(p), { recursive: true });
    writeFileSync(p, JSON.stringify(list, null, 2) + "\n", "utf8");
    return { ok: true, count: list.length };
  } catch (e) {
    return { ok: false, error: e.message };
  }
}

export function readRouteLearn(dir = ROOT) {
  const p = routeLearnPath(dir);
  try {
    if (!existsSync(p)) return [];
    const v = JSON.parse(readFileSync(p, "utf8").replace(/^\uFEFF/, ""));
    return Array.isArray(v) ? v : [];
  } catch {
    return [];
  }
}

// 路由学习统计：按 领域×模型族×技法 组合聚合有效/无效计数，输出有效组合观察
export function routeLearning({ dir = ROOT, min_effective = 2 } = {}) {
  const recs = readRouteLearn(dir);
  if (!recs.length) return { ok: true, total: 0, effective_combos: [], weak_combos: [], note: "暂无路由学习记录（由 pipe/构建流程在优化完成后调用 recordRouteLearn 写入）" };
  const agg = new Map(); // key -> {effective, total}
  for (const r of recs) {
    const k = [r.domain || "?", r.model_family || "?", r.technique || "?"].join("|");
    if (!agg.has(k)) agg.set(k, { effective: 0, total: 0 });
    const a = agg.get(k);
    a.total++;
    if (r.effective) a.effective++;
  }
  const entries = Array.from(agg.entries()).map(([k, v]) => ({ combo: k, effective: v.effective, total: v.total, ratio: v.total ? Math.round((v.effective / v.total) * 100) : 0 }));
  entries.sort((a, b) => b.effective - a.effective);
  const effectiveCombos = entries.filter((e) => e.effective >= min_effective);
  const weakCombos = entries.filter((e) => e.total >= min_effective && e.ratio < 50);
  return {
    ok: true,
    total: recs.length,
    effective_combos: effectiveCombos,
    weak_combos: weakCombos,
    note: effectiveCombos.length
      ? `观察：${effectiveCombos.map((e) => e.combo).join(" / ")} 组合对用户有效（≥${min_effective} 次有效）`
      : `有效组合样本不足（≥${min_effective} 次有效才输出）`,
  };
}

// 生命周期提醒：读取 rules/*.json 快照的生效/废止状态，输出时效结论
export function specLearning({ dir = ROOT } = {}) {
  const base = safePath(dir);
  const rulesDir = join(base, "references", "rules");
  // 用本地日期（非 UTC），避免跨时区凌晨差一天导致生效日误判
  const d = new Date();
  const today = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
  const alerts = [];
  let snapshots = [];
  try {
    if (existsSync(rulesDir)) {
      for (const f of readdirSync(rulesDir)) {
        if (!f.endsWith(".json") || f === "_schema.json") continue;
        try {
          const s = JSON.parse(readFileSync(join(rulesDir, f), "utf8").replace(/^\uFEFF/, ""));
          snapshots.push(s);
        } catch { /* 跳过损坏快照 */ }
      }
    }
  } catch { /* 目录不存在忽略 */ }

  for (const s of snapshots) {
    if (s.status === "superseded") {
      alerts.push({ level: "info", key: s.domain, message: `规范快照 ${s.label} 已废止${s.superseded_by ? `，被「${s.superseded_by}」取代` : ""}` });
      continue;
    }
    if (s.status === "draft") {
      alerts.push({ level: "warn", key: s.domain, message: `规范快照 ${s.label} 为草案状态，正式发布前需核实` });
      continue;
    }
    if (s.effective_date && s.effective_date > today) {
      alerts.push({ level: "warn", key: s.domain, message: `规范 ${s.label} 将于 ${s.effective_date} 生效，当前未生效期间建议标注"征求意见/过渡期"` });
    }
  }

  const changes = readSpecChanges(dir);
  const recent = changes.slice(-10).reverse();
  return {
    ok: true,
    today,
    changes_count: changes.length,
    recent_changes: recent,
    alerts,
    summary: alerts.length
      ? `生命周期提醒 ${alerts.length} 项 / 近期规范变更 ${changes.length} 条`
      : `生命周期无异常，近期规范变更 ${changes.length} 条`,
  };
}

function fbDir(base) {
  return join(safePath(base), "data", "feedback");
}

function readFeedback(base) {
  const d = fbDir(base);
  if (!existsSync(d)) return [];
  const out = [];
  for (const f of readdirSync(d)) {
    if (!f.endsWith(".json")) continue;
    try {
      out.push(JSON.parse(readFileSync(join(d, f), "utf8").replace(/^\uFEFF/, "")));
    } catch { /* 跳过损坏记录 */ }
  }
  return out;
}

function topBy(arr, key) {
  const cnt = new Map();
  for (const it of arr) {
    const v = it[key];
    if (!v) continue;
    cnt.set(v, (cnt.get(v) || 0) + 1);
  }
  let best = null;
  for (const [k, c] of cnt) {
    if (!best || c > best.count) best = { value: k, count: c };
  }
  return best;
}

function inferVerbosity(recs) {
  const lens = recs.map((r) => r.len).filter((v) => v !== null && v > 0);
  if (lens.length < MIN_SAMPLE) return null;
  lens.sort((a, b) => a - b);
  const med = lens[Math.floor(lens.length / 2)];
  if (med < 1200) return "精简";
  if (med > 3000) return "详尽";
  return "标准";
}

export function learn({ apply = false, dir = ROOT } = {}) {
  const base = safePath(dir);
  const recs = readFeedback(base);
  const stats = {
    total: recs.length,
    implicit: recs.filter((r) => r.type === "implicit").length,
    explicit: recs.filter((r) => r.type === "explicit").length,
    by_domain: {},
    by_template: {},
    scores: recs.map((r) => r.score).filter((v) => v !== null),
    lens: recs.map((r) => r.len).filter((v) => v !== null && v > 0),
  };
  for (const r of recs) {
    if (r.domain) stats.by_domain[r.domain] = (stats.by_domain[r.domain] || 0) + 1;
    if (r.template) stats.by_template[r.template] = (stats.by_template[r.template] || 0) + 1;
  }

  const suggestions = [];
  const topDomain = topBy(recs, "domain");
  if (topDomain && topDomain.count >= MIN_SAMPLE) {
    suggestions.push({ key: "domain", value: topDomain.value, reason: `使用 ${topDomain.count} 次（最高频）` });
  }
  const topTemplate = topBy(recs, "template");
  if (topTemplate && topTemplate.count >= MIN_SAMPLE) {
    suggestions.push({ key: "template_pref", value: topTemplate.value, reason: `使用 ${topTemplate.count} 次（最高频）` });
  }
  const verb = inferVerbosity(recs);
  if (verb) {
    suggestions.push({ key: "verbosity", value: verb, reason: `由 ${stats.lens.length} 条提示词长度中位数推断` });
  }

  const applied = [];
  if (apply && suggestions.length) {
    for (const s of suggestions) {
      try {
        setKey({ dir: join(base, "data", "habit-profile"), key: s.key, value: s.value });
        applied.push(s.key);
      } catch (e) {
        // 画像 schema 拒绝时跳过该条（防脏数据）
      }
    }
  }

  const medianScore = stats.scores.length ? (() => {
    const s = [...stats.scores].sort((a, b) => a - b);
    return s[Math.floor(s.length / 2)];
  })() : null;

  // v1.0.9 反馈驱动健康度：读取 track-outcome 的 data/outcomes 聚合技能健康度
  const outcomes = readOutcomes({ dir: base });
  const healthByEngine = {};
  for (const o of outcomes) {
    if (!o.engine) continue;
    const h = (healthByEngine[o.engine] = healthByEngine[o.engine] || { total: 0, ok: 0, scoreSum: 0, scoreN: 0, first_seen: o.ts, last_seen: o.ts });
    h.total++;
    if (o.ok === true) h.ok++;
    if (typeof o.score === "number") { h.scoreSum += o.score; h.scoreN++; }
    if (o.ts < h.first_seen) h.first_seen = o.ts;
    if (o.ts > h.last_seen) h.last_seen = o.ts;
  }
  const health = Object.fromEntries(Object.entries(healthByEngine).map(([k, v]) => [k, {
    usage: v.total,
    success_rate: v.total ? Math.round((v.ok / v.total) * 100) : null,
    avg_score: v.scoreN ? Math.round((v.scoreSum / v.scoreN) * 10) / 10 : null,
    first_seen: v.first_seen,
    last_seen: v.last_seen,
  }]));

  return {
    ok: true,
    stats,
    suggestions,
    applied,
    profile: getProfile({ dir: join(base, "data", "habit-profile") }),
    spec: specLearning({ dir: base }),
    route: routeLearning({ dir: base }),
    health,
    health_summary: Object.keys(health).length
      ? `技能健康度: ${Object.keys(health).join("/")} 各引擎（usage/success_rate/avg_score/last_seen）`
      : "技能健康度: 暂无 outcomes（track-outcome.mjs --event 记录后可见）",
    median_score: medianScore,
    note: recs.length < MIN_SAMPLE
      ? `样本不足（${recs.length} < ${MIN_SAMPLE}），仅展示统计，未做任何写入`
      : (apply ? `已应用 ${applied.length} 项画像更新` : "dry-run：仅建议，未写入（--apply 才写入）"),
    neutrality: "学习结果仅写入 habit-profile 默认值层，不改变任何评分结果",
    learning_boundary: "画像层只记录偏好与路由有效性观察，不产出模板/技能修改提案（那是技能层职责）",
  };
}

// ================= CLI =================
if (isMain(import.meta)) {
  const args = process.argv.slice(2);
  const opt = makeOpt(args);
  const json = args.includes("--json");
  const apply = args.includes("--apply");
  const dir = opt("dir") || ROOT;

  // v1.0.9 数据治理：--purge / --export 直接处理 outcomes
  if (args.includes("--help") || args.includes("-h")) {
    console.log("用法:");
    console.log("  node scripts/learner.mjs [--apply] [--json]       学习画像 + 健康度");
    console.log("  node scripts/learner.mjs --purge --confirm        数据治理：清除过期 outcomes");
    console.log("  node scripts/learner.mjs --export                 数据治理：导出 outcomes");
    process.exit(0);
  }
  if (args.includes("--purge")) {
    const pr = purgeOutcomes({ dir, confirm: args.includes("--confirm") });
    if (!pr.ok) { console.error(`✗ ${pr.error}`); process.exit(2); }
    console.log(`已清除过期 outcomes（${pr.removed} 个文件）`);
    process.exit(0);
  }
  if (args.includes("--export")) {
    const er = exportOutcomes({ dir, format: opt("format") || "json" });
    if (!er.ok) { console.error(`✗ ${er.error}`); process.exit(2); }
    console.log(er.content);
    process.exit(0);
  }

  const r = learn({ apply, dir });
  if (json) {
    process.stdout.write(JSON.stringify(r, null, 2) + "\n");
  } else {
    process.stdout.write(`反馈样本: ${r.stats.total} 条（隐式 ${r.stats.implicit} / 显式 ${r.stats.explicit}）\n`);
    process.stdout.write(`领域分布: ${Object.keys(r.stats.by_domain).length ? Object.entries(r.stats.by_domain).map(([k, v]) => `${k}=${v}`).join(" ") : "无"}\n`);
    process.stdout.write(`模板分布: ${Object.keys(r.stats.by_template).length ? Object.entries(r.stats.by_template).map(([k, v]) => `${k}=${v}`).join(" ") : "无"}\n`);
    if (r.median_score !== null) process.stdout.write(`评分中位数: ${r.median_score}\n`);
    if (r.suggestions.length) {
      process.stdout.write(`学习建议:\n`);
      for (const s of r.suggestions) process.stdout.write(`  - ${s.key}=${s.value}（${s.reason}）\n`);
    } else {
      process.stdout.write(`学习建议: 暂无（样本不足或信号不足）\n`);
    }
    process.stdout.write(`${r.note}\n`);
    if (r.applied.length) process.stdout.write(`已写入画像: ${r.applied.join("/")}\n`);
    if (r.spec && r.spec.ok) {
      process.stdout.write(`\n[规范生命周期] ${r.spec.summary}\n`);
      for (const a of r.spec.alerts) process.stdout.write(`  ${a.level === "warn" ? "⚠" : "•"} ${a.message}\n`);
      for (const c of r.spec.recent_changes) process.stdout.write(`  • ${c.ts.slice(0, 10)} ${c.platform} 变更: ${c.changed_names.join("/")}\n`);
    }
    if (r.route && r.route.ok) {
      process.stdout.write(`\n[路由偏好学习] ${r.route.note}\n`);
      for (const e of r.route.effective_combos) process.stdout.write(`  • 有效: ${e.combo}（${e.effective}/${e.total} 次）\n`);
      for (const w of r.route.weak_combos) process.stdout.write(`  ⚠ 低效: ${w.combo}（${w.effective}/${w.total} 次有效）\n`);
    }
    if (r.health && Object.keys(r.health).length) {
      process.stdout.write(`\n[技能健康度]（data/outcomes 反馈驱动）\n`);
      for (const [k, h] of Object.entries(r.health)) {
        process.stdout.write(`  ${k}: usage ${h.usage} · 成功率 ${h.success_rate}% · 均分 ${h.avg_score === null ? "-" : h.avg_score} · 最近 ${(h.last_seen || "").slice(0, 10)}\n`);
      }
    } else if (r.health_summary) {
      process.stdout.write(`\n${r.health_summary}\n`);
    }
    if (r.learning_boundary) process.stdout.write(`\n边界: ${r.learning_boundary}\n`);
  }
}
