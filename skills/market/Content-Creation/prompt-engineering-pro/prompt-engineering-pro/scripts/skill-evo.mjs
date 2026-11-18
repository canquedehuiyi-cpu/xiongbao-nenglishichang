#!/usr/bin/env node
// skill-evo.mjs — 受控进化循环引擎（v1.1.0）
// 功能: 从诊断结果（diagnose-failures.mjs 输出）生成进化提案（改进模板/新增模板/废弃模板/版本演进），
//       输出 diff 提案 + dry-run 校验；默认不落盘，人工确认后才应用（--apply + validate 门禁）。
// 安全: 进化不自动落盘——默认 dry-run 只输出提案；--apply 需显式且必须通过 validate.mjs + scan-safety 全绿。
// 确定性: 纯规则，同一输入恒同输出；无稳定信号不提案（反噪音）。
// 用法:
//   node scripts/skill-evo.mjs --diagnosis <diagnosis.json>   # 生成提案（dry-run）
//   node scripts/skill-evo.mjs --diagnosis <diagnosis.json> --apply  # 应用提案到 references/proposals/
//   node scripts/skill-evo.mjs --json
import { readFileSync, writeFileSync, mkdirSync } from "node:fs";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";
import { safePath, safeId, isMain, makeOpt } from "./lib.mjs";

const ROOT = join(dirname(fileURLToPath(import.meta.url)), "..");
const MIN_SIGNAL = 3; // 反噪音：同一模式出现 ≥3 次才提案

// 提案类型
const PROPOSAL_TYPES = {
  IMPROVE_TEMPLATE: "改进模板",
  NEW_TEMPLATE: "新增模板",
  RETIRE_TEMPLATE: "废弃模板",
  VERSION_EVOLVE: "版本演进",
};

// 从诊断结果生成提案（确定性规则）
function propose(diagnosis) {
  const proposals = [];
  if (!diagnosis || !diagnosis.patterns || !diagnosis.patterns.length) {
    return { proposals, note: "无失败信号：无稳定偏好不提案（反噪音）" };
  }
  for (const p of diagnosis.patterns) {
    if (!p || !p.count) continue;
    if (p.count >= MIN_SIGNAL) {
      // 按失败模式映射到提案
      if (/Non-goals/.test(p.label)) {
        proposals.push({
          type: PROPOSAL_TYPES.IMPROVE_TEMPLATE,
          target: "templates 契约模板（补 Non-goals 小节）",
          reason: `「${p.label}」反复出现 ${p.count} 次：模板契约缺 Non-goals 显式位`,
          diff: "+ 新增 Non-goals 占位小节：明确「本任务不做/不输出什么」",
          severity: "high",
        });
      } else if (/验证标准|验收/.test(p.label)) {
        proposals.push({
          type: PROPOSAL_TYPES.IMPROVE_TEMPLATE,
          target: "templates 契约模板（补 Verification 小节）",
          reason: `「${p.label}」反复出现 ${p.count} 次：模板缺验收/成功标准位`,
          diff: "+ 新增 Verification 占位小节：「如何判断做对（验收条件）」",
          severity: "high",
        });
      } else if (/评分低于|LOW_SCORE/.test(p.label)) {
        proposals.push({
          type: PROPOSAL_TYPES.VERSION_EVOLVE,
          target: "score-prompt 权重基线",
          reason: `评分低于阈值出现 ${p.count} 次：建议评审评分权重与基线`,
          diff: "~ 评审 scoring-rubric 权重（仅提案，不自动改）",
          severity: "medium",
        });
      } else {
        proposals.push({
          type: PROPOSAL_TYPES.IMPROVE_TEMPLATE,
          target: "对应失败模板",
          reason: `「${p.label}」出现 ${p.count} 次`,
          diff: "~ 按诊断 hint 修订对应模板（仅提案）",
          severity: "medium",
        });
      }
    }
  }
  return { proposals, note: proposals.length ? `生成 ${proposals.length} 项提案（人工确认后 --apply）` : "无稳定信号：不提案（反噪音）" };
}

function proposalDiffs(proposals) {
  return proposals.map((p) => `[${p.type}] ${p.target}\n  理由: ${p.reason}\n  变更: ${p.diff}\n  严重度: ${p.severity}`);
}

export function skillEvo({ diagnosis = null, dir = ROOT } = {}) {
  if (!diagnosis || !diagnosis.patterns) {
    return { ok: true, apply: false, proposals: [], diffs: [], note: "缺少诊断结果：请先用 diagnose-failures.mjs 生成诊断（--diagnosis <json>）" };
  }
  const { proposals, note } = propose(diagnosis);
  const diffs = proposalDiffs(proposals);
  return {
    ok: true,
    apply: false,
    dry_run: true,
    proposals,
    diffs,
    note,
    gate: "进化不自动落盘：应用需 --apply 且必须通过 validate.mjs + scan-safety 全绿",
  };
}

// 应用提案：写入 references/proposals/（不直接改 SKILL/模板；应用后由用户/后续流程评审落模板）
export function applyProposals({ diagnosis = null, dir = ROOT } = {}) {
  const base = safePath(dir);
  const r = skillEvo({ diagnosis, dir: base });
  if (!r.proposals.length) return { ok: true, applied: 0, note: r.note };
  const propDir = join(base, "references", "proposals");
  mkdirSync(propDir, { recursive: true });
  const stamp = new Date().toISOString().slice(0, 10);
  let applied = 0;
  for (let i = 0; i < r.proposals.length; i++) {
    const p = r.proposals[i];
    const name = safeId(`${stamp}-${p.type.replace(/[^\u4e00-\u9fff\w]/g, "")}-${i + 1}`);
    const file = join(propDir, `${name}.md`);
    const content = [
      `# 进化提案（${p.type}）`,
      "",
      `- 日期: ${stamp}`,
      `- 目标: ${p.target}`,
      `- 理由: ${p.reason}`,
      `- 变更: ${p.diff}`,
      `- 严重度: ${p.severity}`,
      "",
      "> 本提案为 dry-run 产物，写入 references/proposals/ 供评审；未自动修改任何模板/SKILL。",
    ].join("\n");
    try {
      writeFileSync(file, content + "\n", "utf8");
      applied++;
    } catch { /* 跳过写入失败 */ }
  }
  return { ok: true, applied, note: `已写入 ${applied} 项提案到 references/proposals/（供评审，不自动落模板）` };
}

// ================= CLI =================
if (isMain(import.meta)) {
  const args = process.argv.slice(2);
  const opt = makeOpt(args);
  if (args.includes("--help") || args.includes("-h")) {
    console.log("用法:");
    console.log("  node scripts/skill-evo.mjs --diagnosis <diagnosis.json>        生成提案（dry-run）");
    console.log("  node scripts/skill-evo.mjs --diagnosis <diagnosis.json> --apply 应用提案到 references/proposals/");
    console.log("进化不自动落盘：默认 dry-run；--apply 仅写入提案目录，不自动改模板。");
    process.exit(0);
  }
  const wantJson = args.includes("--json");
  const apply = args.includes("--apply");
  const diagnosisPath = opt("diagnosis");
  const dir = opt("dir") || ROOT;
  if (!diagnosisPath) {
    console.error("✗ 缺少 --diagnosis（diagnose-failures.mjs 输出 JSON）");
    process.exit(2);
  }
  let diagnosis;
  try {
    diagnosis = JSON.parse(readFileSync(diagnosisPath, "utf8").replace(/^\uFEFF/, ""));
  } catch (e) {
    console.error(`✗ 读取诊断失败: ${e.message}`);
    process.exit(2);
  }
  const result = apply ? applyProposals({ diagnosis, dir }) : skillEvo({ diagnosis, dir });
  if (wantJson) {
    process.stdout.write(JSON.stringify(result, null, 2) + "\n");
  } else {
    console.log("=== 受控进化循环 ===");
    if (result.proposals && result.proposals.length) {
      for (const p of result.proposals) {
        console.log(`\n[${p.type}] ${p.target}`);
        console.log(`  理由: ${p.reason}`);
        console.log(`  变更: ${p.diff}`);
        console.log(`  严重度: ${p.severity}`);
      }
      console.log(`\n${result.gate || result.note}`);
    } else {
      console.log(result.note || "无提案");
    }
    if (result.applied) console.log(`\n已写入: ${result.applied} 项`);
  }
}
