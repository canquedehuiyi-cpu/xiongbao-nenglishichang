#!/usr/bin/env node
// skill.mjs — 管理 CLI 入口（v1.1.0，平台层）
// 统一管理命令集，让"管理能力"可被真实使用：
//   skill health  → 健康诊断报告（health-report.mjs）
//   skill check   → 发布门禁（validate.mjs P0-P10）
//   skill adapt   → 多宿主部署（host-adapt.mjs）
//   skill verify  → 规范核验（verify-spec.mjs）
//   skill report  → 汇总报告（health + check 摘要）
// 安全: 全部子命令只读或输出到本工作区 host-out/，不写宿主配置、不删改技能文件。
// 用法:
//   node scripts/skill.mjs health [--json]
//   node scripts/skill.mjs check
//   node scripts/skill.mjs adapt --host all
//   node scripts/skill.mjs verify --domain game
//   node scripts/skill.mjs report [--json]
import { spawnSync } from "node:child_process";
import { join } from "node:path";
import { ROOT, isMain, makeOpt } from "./lib.mjs";
import { healthReport } from "./health-report.mjs";
import { adapt } from "./host-adapt.mjs";

const COMMANDS = ["health", "check", "adapt", "verify", "report"];

// 运行内部引擎脚本（不经 shell，避免转义问题）；返回退出码与输出
function runScript(name, args) {
  const script = join(ROOT, "scripts", `${name}.mjs`);
  const r = spawnSync(process.execPath, [script, ...args], { encoding: "utf8" });
  return { code: r.status, stdout: r.stdout || "", stderr: r.stderr || "" };
}

function cmdHealth(json) {
  const r = healthReport({ dir: ROOT });
  if (json) process.stdout.write(JSON.stringify(r, null, 2) + "\n");
  else {
    console.log(`健康度: ${r.health}（得分 ${r.score}/100）`);
    console.log(`引擎: ${r.engine_stats.total} 个 · 未注册 ${r.engine_stats.unregistered} · 缺失 ${r.engine_stats.missing}`);
    if (r.findings.length) {
      console.log("发现:");
      for (const f of r.findings) console.log(`  [${f.level}] ${f.item}`);
      console.log("\n建议行动:");
      for (const a of r.actions) console.log(`  - ${a}`);
    } else console.log("✓ 无发现");
    console.log(`判定: ${r.verdict}`);
  }
  return r.health === "critical" ? 1 : 0;
}

function cmdCheck() {
  console.log("== 发布门禁（validate）==");
  const r = runScript("validate", []);
  process.stdout.write(r.stdout);
  if (r.stderr.trim()) process.stderr.write(r.stderr);
  return r.code === 0 && /P0-P10 全部门禁通过/.test(r.stdout) ? 0 : 1;
}

function cmdAdapt(args, json) {
  const host = makeOpt(args)("host") || "all";
  const hosts = host === "all" ? ["claude", "codex", "cursor", "chatgpt", "generic"] : [host];
  const results = [];
  let fail = 0;
  for (const h of hosts) {
    try {
      const r = adapt({ host: h });
      results.push(r);
      if (r.frontmatter.ok) console.log(`✓ ${h}: → ${r.target}`);
      else { console.log(`⚠ ${h}: frontmatter ${r.frontmatter.issues.length} 项问题`); for (const i of r.frontmatter.issues) console.log(`    - ${i}`); }
    } catch (e) { fail++; console.error(`✗ ${h}: ${e.message}`); }
  }
  if (json) process.stdout.write(JSON.stringify({ ok: fail === 0, results }, null, 2) + "\n");
  return fail ? 1 : 0;
}

function cmdVerify(args) {
  const opt = makeOpt(args);
  const layer = opt("layer") || "platform";
  const domain = opt("domain") || "";
  const vArgs = ["--layer", layer];
  if (domain) vArgs.push("--domain", domain);
  const r = runScript("verify-spec", vArgs);
  process.stdout.write(r.stdout);
  if (r.stderr.trim()) process.stderr.write(r.stderr);
  return r.code;
}

function cmdReport(json) {
  const h = healthReport({ dir: ROOT });
  const c = runScript("validate", []);
  const checkOk = c.code === 0 && /P0-P10 全部门禁通过/.test(c.stdout);
  const report = {
    engine: "skill.mjs v1.1.0",
    generated: new Date().toISOString(),
    health: h.health,
    health_score: h.score,
    check_gate: checkOk ? "PASS" : "FAIL",
    engine_total: h.engine_stats.total,
    findings: h.findings.length,
    verdict: `${h.verdict}；发布门禁 ${checkOk ? "通过" : "未通过"}`,
  };
  if (json) process.stdout.write(JSON.stringify(report, null, 2) + "\n");
  else {
    console.log("=== 技能管理汇总报告 ===");
    console.log(`健康度: ${report.health}（${report.health_score}/100）`);
    console.log(`发布门禁: ${report.check_gate}`);
    console.log(`引擎: ${report.engine_total} 个`);
    console.log(`发现: ${report.findings} 项`);
    console.log(`判定: ${report.verdict}`);
  }
  return checkOk && h.health !== "critical" ? 0 : 1;
}

if (isMain(import.meta)) {
  const args = process.argv.slice(2);
  const cmd = args.find((a) => !a.startsWith("-"));
  if (!cmd || !COMMANDS.includes(cmd) || args.includes("--help") || args.includes("-h")) {
    console.log("用法: node scripts/skill.mjs <命令> [参数]");
    console.log("命令:");
    for (const c of COMMANDS) console.log(`  ${c}`);
    console.log("示例: skill.mjs health | check | adapt --host all | verify --domain game | report");
    process.exit(0);
  }
  const json = args.includes("--json");
  const rest = args.filter((a) => a !== cmd);
  let code;
  switch (cmd) {
    case "health": code = cmdHealth(json); break;
    case "check": code = cmdCheck(); break;
    case "adapt": code = cmdAdapt(rest, json); break;
    case "verify": code = cmdVerify(rest); break;
    case "report": code = cmdReport(json); break;
    default: code = 2;
  }
  process.exit(code);
}
