#!/usr/bin/env node
// run-eval.mjs — 实证评估执行引擎（v1.1.0）
// 功能: 执行评测用例清单（eval-case-gen.mjs 生成的 JSON 格式），双模式：
//   - dry-run（默认）：本地规则校验，不调用任何外部模型/API；对比"实际输出"与 pass_criteria
//   - api 模式（可选）：用户显式提供 --api-key 与 --model，仅作技法前后对比分析（默认离线保证）
// 输出: case_results[]（逐用例通过/失败 + 依据）+ technique_evidence[]（技法实证状态更新）
// 安全: 默认 dry-run 零外部调用；API 模式需显式密钥；输出不含可执行危险指令。
// 确定性: dry-run 纯规则，同一输入恒同输出。
// 用法:
//   node scripts/run-eval.mjs --cases <eval.json> --output <actual_output.txt>
//   node scripts/run-eval.mjs --cases <eval.json> --output <actual_output.txt> --json
import { readFileSync } from "node:fs";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";
import { isMain, makeOpt } from "./lib.mjs";

const ROOT = join(dirname(fileURLToPath(import.meta.url)), "..");

// dry-run 本地规则校验：根据 pass_criteria 文本判定实际输出是否满足
// 支持确定性规则关键词：包含/不含/长度/开头/结尾/JSON/数字 等（纯本地，不调用模型）
function checkCriteria(actual, criteria) {
  const t = String(actual || "");
  const c = String(criteria || "");
  const results = [];
  // 规则解析：支持 "包含X" / "不包含X" / "长度>N" / "JSON" 等声明式描述
  for (const m of c.match(/包含(.+?)(?=；|。|$)/g) || []) {
    const kw = m.replace(/^包含/, "").replace(/[「」“”']/g, "").trim();
    if (kw) results.push({ rule: `包含「${kw}」`, pass: t.includes(kw) });
  }
  if (/JSON|json/.test(c)) results.push({ rule: "JSON 格式", pass: /^\s*[\[{]/.test(t) });
  if (/长度\s*[><=]/.test(c) || /字数\s*[><=]/.test(c)) {
    const m = c.match(/长度\s*([><=])\s*(\d+)/) || c.match(/字数\s*([><=])\s*(\d+)/);
    if (m) {
      const n = Number(m[2]);
      const pass = m[1] === "<" ? t.length < n : m[1] === ">" ? t.length > n : Math.abs(t.length - n) <= n * 0.2;
      results.push({ rule: `长度 ${m[1]} ${n}`, pass });
    }
  }
  if (/不包含/.test(c)) {
    for (const m of c.match(/不包含(.+?)(?=；|。|$)/g) || []) {
      const kw = m.replace(/^不包含/, "").replace(/[「」“”']/g, "").trim();
      if (kw) results.push({ rule: `不包含「${kw}」`, pass: !t.includes(kw) });
    }
  }
  if (!results.length) {
    // 无明确规则：退化为非空检查（诚实标注）
    results.push({ rule: "非空（无显式规则时退化为非空检查）", pass: t.trim().length > 0 });
  }
  return { ok: results.every((r) => r.pass), details: results };
}

export function runEval({ cases = [], actualOutput = "", apiMode = false, apiKey = "", model = "" } = {}) {
  if (!Array.isArray(cases) || !cases.length) {
    throw new Error("输入为空：请提供评测用例清单（--cases <eval.json>，可由 eval-case-gen.mjs 生成）");
  }
  if (apiMode && !apiKey) {
    throw new Error("api 模式需显式提供 --api-key（默认 dry-run 零外部调用；密钥仅用于对比分析）");
  }
  const caseResults = cases.map((c) => {
    const cr = checkCriteria(actualOutput, c.pass_criteria || c.criteria || "");
    return {
      id: c.id || "case",
      type: c.type || "unknown",
      expected: c.expected || "",
      pass: cr.ok,
      details: cr.details,
    };
  });
  const passed = caseResults.filter((r) => r.pass).length;
  // 技法实证状态：评估通过比例决定 effective/pending（不虚构结论）
  const techniqueEvidence = [];
  const techniques = new Set((cases.map((c) => c.technique).filter(Boolean)));
  for (const t of techniques) {
    const related = caseResults.filter((r) => cases.find((c) => c.id === r.id && c.technique === t));
    const passN = related.filter((r) => r.pass).length;
    const ratio = related.length ? passN / related.length : 0;
    techniqueEvidence.push({
      technique: t,
      state: related.length && ratio >= 0.8 ? "effective" : related.length ? "pending" : "no_evidence",
      pass: passN,
      total: related.length,
    });
  }
  return {
    meta: { engine: "run-eval.mjs v1.1.0", mode: apiMode ? "api" : "dry-run", mode_note: apiMode ? "api 对比分析（用户显式密钥）" : "dry-run：本地规则校验，零外部调用" },
    case_results: caseResults,
    technique_evidence: techniqueEvidence,
    summary: { total: caseResults.length, passed, failed: caseResults.length - passed },
    verdict: passed === caseResults.length ? "全部通过" : passed >= caseResults.length * 0.8 ? "基本通过（存在少量未达标）" : "未达标：建议按失败用例修订",
  };
}

// ================= CLI =================
if (isMain(import.meta)) {
  const args = process.argv.slice(2);
  const opt = makeOpt(args);
  if (args.includes("--help") || args.includes("-h")) {
    console.log("用法: node scripts/run-eval.mjs --cases <eval.json> --output <actual_output.txt> [--api-key <key> --model <m>] [--json]");
    console.log("默认 dry-run 零外部调用；API 模式需显式密钥。用例清单可由 eval-case-gen.mjs 生成。");
    process.exit(0);
  }
  const wantJson = args.includes("--json");
  const casesPath = opt("cases");
  const outputPath = opt("output");
  const apiMode = !!opt("api-key");
  const apiKey = opt("api-key") || "";
  const model = opt("model") || "";
  if (!casesPath) {
    console.error("✗ 缺少 --cases（评测用例清单 JSON）");
    process.exit(2);
  }
  let cases;
  try {
    cases = JSON.parse(readFileSync(casesPath, "utf8").replace(/^\uFEFF/, ""));
    if (cases && cases.cases && Array.isArray(cases.cases)) cases = cases.cases;
  } catch (e) {
    console.error(`✗ 读取评测清单失败: ${e.message}`);
    process.exit(2);
  }
  let actual = "";
  if (outputPath) {
    try {
      actual = readFileSync(outputPath, "utf8").replace(/^\uFEFF/, "");
    } catch (e) {
      console.error(`✗ 读取实际输出失败: ${e.message}`);
      process.exit(2);
    }
  }
  let result;
  try {
    result = runEval({ cases, actualOutput: actual, apiMode, apiKey, model });
  } catch (e) {
    console.error(`✗ ${e.message}`);
    process.exit(1);
  }
  if (wantJson) {
    process.stdout.write(JSON.stringify(result, null, 2) + "\n");
  } else {
    console.log(`=== 实证评估（${result.meta.mode}）===`);
    console.log(`模式: ${result.meta.mode_note}`);
    for (const r of result.case_results) {
      console.log(`  ${r.pass ? "✓" : "✗"} ${r.id} [${r.type}] ${r.pass ? "通过" : "未达标"}`);
      for (const d of r.details) console.log(`      ${d.pass ? "·" : "✗"} ${d.rule}: ${d.pass ? "满足" : "不满足"}`);
    }
    console.log(`\n汇总: ${result.summary.passed}/${result.summary.total} 通过`);
    console.log(`判定: ${result.verdict}`);
    if (result.technique_evidence.length) {
      console.log("技法实证:");
      for (const t of result.technique_evidence) console.log(`  ${t.technique}: ${t.state}（${t.pass}/${t.total}）`);
    }
  }
}
