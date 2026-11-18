#!/usr/bin/env node
// health-report.mjs — 健康诊断报告引擎（v1.1.0）
// 功能: 技能健康体检——引擎注册完整性、依赖图一致性、死技能/冗余检测、关键文档覆盖、
//       JSON 有效性、版本一致性，输出结构化健康报告 {health, findings[], actions[]}。
// 安全: 只读扫描，不删除/修改任何技能文件（死技能只标记不删除）。
// 确定性: 纯本地文件系统扫描 + 规则判定，同一输入恒同输出。
// 用法:
//   node scripts/health-report.mjs            # 全仓健康扫描（人类可读）
//   node scripts/health-report.mjs --json     # 机器可读
//   node scripts/health-report.mjs --dir <p>  # 指定目录（仅限包内）
import { readFileSync, existsSync, readdirSync } from "node:fs";
import { join, resolve, sep } from "node:path";
import { ROOT, isMain, makeOpt } from "./lib.mjs";

const VERSION = "1.1.0";

// 关键文档清单（依赖图：SKILL.md/engine-catalog 引用的核心文件）
const KEY_DOCS = [
  "SKILL.md",
  "CHANGELOG.md",
  "references/GUIDE.md",
  "references/installation-guide.md",
  "references/engine-catalog.md",
  "references/templates.md",
  "references/techniques.md",
  "references/technique-quickref.md",
  "references/prompt-contract.md",
  "references/scoring-rubric.md",
  "references/anti-patterns.md",
  "references/safety-policy.md",
  "references/failure-taxonomy.md",
  "references/token-economy.md",
  "references/domain-architecture.md",
  "references/platform-spec-registry.md",
  "references/environment-matrix.md",
  "references/self-evolution.md",
  "references/host-deploy.md",
  "references/health-report.md",
  "references/lexicon/red.json",
  "references/lexicon/gray.json",
  "domains/registry.json",
];

// 扫描引擎注册完整性：scripts/*.mjs 与 engine-catalog.md 双向核对
// 口径: scripts/ 下全部 .mjs 均为引擎（含验证/安全设施），除 skill.mjs（管理 CLI 入口，非业务引擎）
function engineRegistry(dir) {
  const scriptsDir = join(dir, "scripts");
  const catalogPath = join(dir, "references", "engine-catalog.md");
  const engines = existsSync(scriptsDir)
    ? readdirSync(scriptsDir).filter((f) => f.endsWith(".mjs") && f !== "skill.mjs").sort()
    : [];
  const catalogText = existsSync(catalogPath) ? readFileSync(catalogPath, "utf8") : "";
  const unregistered = []; // 死技能：scripts 存在但 engine-catalog 未注册
  for (const e of engines) {
    if (!catalogText.includes(e)) unregistered.push(e);
  }
  const registered = (catalogText.match(/`([a-z0-9-]+\.mjs)`/g) || []).map((s) => s.slice(1, -1));
  const missing = []; // scripts 缺失但 engine-catalog 注册
  for (const r of registered) {
    if (!existsSync(join(scriptsDir, r))) missing.push(r);
  }
  return { engines, unregistered, missing, registered };
}

// 版本一致性：脚本 engine 标注与词库版本
function versionConsistency(dir) {
  const redPath = join(dir, "references", "lexicon", "red.json");
  let expected = null;
  try { expected = JSON.parse(readFileSync(redPath, "utf8")).meta?.version || null; } catch { /* 损坏按 null */ }
  const scriptsDir = join(dir, "scripts");
  const offenders = [];
  if (expected && existsSync(scriptsDir)) {
    for (const f of readdirSync(scriptsDir).filter((x) => x.endsWith(".mjs"))) {
      const src = readFileSync(join(scriptsDir, f), "utf8");
      for (const m of src.matchAll(/engine:\s*"([^"]*?)v(\d+\.\d+\.\d+)"/g)) {
        if (m[2] !== expected) offenders.push(`${f}: ${m[1]}v${m[2]}`);
      }
    }
  }
  return { expected, offenders };
}

// JSON 有效性扫描
function jsonHealth(dir) {
  const bad = [];
  function walk(d) {
    for (const e of readdirSync(d, { withFileTypes: true })) {
      const p = join(d, e.name);
      if (e.isDirectory()) { if (e.name !== "data" && e.name !== "host-out" && e.name !== "node_modules") walk(p); }
      else if (e.name.endsWith(".json")) {
        try { JSON.parse(readFileSync(p, "utf8")); } catch { bad.push(p.slice(dir.length + 1)); }
      }
    }
  }
  walk(dir);
  return bad;
}

export function healthReport({ dir = ROOT } = {}) {
  const base = resolve(ROOT, String(dir));
  if (base !== ROOT && !base.startsWith(ROOT + sep)) throw new Error(`安全边界: health-report 仅扫描技能包内部: ${dir}`);
  const findings = [];
  const actions = [];
  let score = 100;
  const dec = (n) => { score = Math.max(0, score - n); };

  // 1. 关键文档覆盖
  for (const d of KEY_DOCS) {
    if (!existsSync(join(base, d))) {
      findings.push({ level: "critical", item: `文档缺失: ${d}` });
      actions.push(`补齐 ${d}（SKILL.md/engine-catalog 引用了它）`);
      dec(5);
    }
  }

  // 2. 引擎注册完整性
  const reg = engineRegistry(base);
  for (const e of reg.unregistered) {
    findings.push({ level: "warning", item: `死技能（scripts 存在但 engine-catalog 未注册）: ${e}` });
    actions.push(`在 references/engine-catalog.md 注册 ${e}，或在确认废弃后移除`);
    dec(3);
  }
  for (const m of reg.missing) {
    findings.push({ level: "critical", item: `引擎缺失（engine-catalog 注册但 scripts 不存在）: ${m}` });
    actions.push(`补回 scripts/${m} 或从 engine-catalog 移除注册`);
    dec(6);
  }

  // 3. 版本一致性
  const ver = versionConsistency(base);
  if (ver.expected && ver.offenders.length) {
    findings.push({ level: "warning", item: `引擎版本标注不一致（词库 v${ver.expected}，${ver.offenders.length} 处偏离）` });
    actions.push(`统一 engine 标注到 v${ver.expected}（validate §4b 强制）`);
    dec(4);
  }
  if (!ver.expected) {
    findings.push({ level: "warning", item: "版本源 red.json meta.version 缺失或损坏" });
    actions.push("修复 references/lexicon/red.json meta.version（单一版本源）");
    dec(4);
  }

  // 4. JSON 有效性
  const badJson = jsonHealth(base);
  if (badJson.length) {
    findings.push({ level: "critical", item: `JSON 解析失败 ${badJson.length} 个: ${badJson.join("，")}` });
    actions.push("修复损坏 JSON 文件");
    dec(8);
  }

  // 5. 死文件扫描：references/ 下未被 SKILL.md 引用（含省略 .md 后缀）的 .md
  const skillText = existsSync(join(base, "SKILL.md")) ? readFileSync(join(base, "SKILL.md"), "utf8") : "";
  const deadDocs = [];
  const refsDir = join(base, "references");
  if (existsSync(refsDir)) {
    for (const f of readdirSync(refsDir).filter((x) => x.endsWith(".md"))) {
      const stem = f.replace(/\.md$/, "");
      if (!skillText.includes(f) && !skillText.includes(stem)) deadDocs.push(f);
    }
  }
  for (const d of deadDocs) {
    findings.push({ level: "info", item: `references/${d} 未被 SKILL.md 引用（可能为独立参考文档）` });
    // info 不扣分，不强制行动
  }

  const health = score >= 90 ? "healthy" : score >= 70 ? "warning" : "critical";
  return {
    ok: true,
    meta: { engine: "health-report.mjs v1.1.0", version: VERSION, scanned: base },
    health,
    score,
    engine_stats: { total: reg.engines.length, unregistered: reg.unregistered.length, missing: reg.missing.length },
    findings,
    actions: actions.length ? actions : ["无需修复：全仓健康"],
    verdict: health === "healthy" ? "技能健康：全仓扫描无 critical/warning 问题" : health === "warning" ? "技能亚健康：存在可修复的 warning（不影响主流程）" : "技能不健康：存在 critical 问题，修复后再发布",
  };
}

// ================= CLI =================
if (isMain(import.meta)) {
  const args = process.argv.slice(2);
  const opt = makeOpt(args);
  if (args.includes("--help") || args.includes("-h")) {
    console.log("用法: node scripts/health-report.mjs [--json] [--dir <p>]");
    console.log("说明: 全仓健康扫描（引擎注册/依赖图/版本一致性/JSON/死技能），只读不修改。");
    process.exit(0);
  }
  const wantJson = args.includes("--json");
  const dir = opt("dir") || ROOT;
  let result;
  try {
    result = healthReport({ dir });
  } catch (e) {
    console.error(`✗ ${e.message}`);
    process.exit(1);
  }
  if (wantJson) {
    process.stdout.write(JSON.stringify(result, null, 2) + "\n");
  } else {
    console.log("=== 技能健康诊断 ===");
    console.log(`健康度: ${result.health}（得分 ${result.score}/100）`);
    console.log(`引擎: ${result.engine_stats.total} 个 · 未注册 ${result.engine_stats.unregistered} · 缺失 ${result.engine_stats.missing}`);
    if (result.findings.length) {
      console.log("发现:");
      for (const f of result.findings) console.log(`  [${f.level}] ${f.item}`);
      console.log("\n建议行动:");
      for (const a of result.actions) console.log(`  - ${a}`);
    } else {
      console.log("✓ 无发现");
    }
    console.log(`判定: ${result.verdict}`);
  }
}
