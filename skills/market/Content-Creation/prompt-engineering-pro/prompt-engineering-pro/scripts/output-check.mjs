#!/usr/bin/env node
// output-check.mjs — 输出侧验证引擎（v1.1.0）
// 功能: 将 prompt 的实际输出与契约要求（格式/长度/引用/禁止项/验证标准）比对，
//       输出格式符合度 + 要素覆盖 + 偏差清单 + 修复建议。
// 与 prompt-contract-check.mjs 区别: 契约审计查"prompt 本身要素是否完整"；
//      本引擎查"模型实际输出是否满足 prompt 声明的约束"（输出侧）。
// 确定性: 纯规则提取契约约束并比对输出，同一输入恒同输出。
// 用法:
//   node scripts/output-check.mjs --contract <prompt.txt> --output <output.txt>
//   node scripts/output-check.mjs --contract <prompt.txt> --output <output.txt> --json
import { readFileSync } from "node:fs";
import { isMain, makeOpt } from "./lib.mjs";

// 从契约文本提取输出侧约束（确定性规则）
function extractConstraints(contract) {
  const t = String(contract || "");
  const cons = [];
  // 输出格式声明
  const fmtMap = [
    [/输出\s*(JSON|json)/, "JSON 格式"],
    [/格式\s*[:：]?\s*(JSON|json)/, "JSON 格式"],
    [/分点|列表|bullet/, "分点/列表格式"],
    [/表格|Markdown 表格/, "表格格式"],
    [/Markdown/, "Markdown 格式"],
    [/代码块|```/, "代码块格式"],
  ];
  for (const [re, label] of fmtMap) if (re.test(t)) cons.push({ type: "format", rule: label });
  // 长度约束
  const lenM = t.match(/(不超过|少于|小于|限制在|最多)\s*(\d+)\s*(字|词|token)/);
  if (lenM) cons.push({ type: "length", rule: `长度不超过 ${lenM[2]} ${lenM[3]}`, max: Number(lenM[2]) });
  // 引用/证据要求
  if (/(引用|附来源|给出处|标注来源|evidence|citation)/i.test(t)) cons.push({ type: "citation", rule: "需引用来源/证据" });
  // 禁止项
  if (/(不要编造|不编造|不得虚构|禁止虚构|不要虚构)/.test(t)) cons.push({ type: "no_fabricate", rule: "禁止编造" });
  if (/(不要|不能|不得|禁止)\s*(举例|例子|示例)/.test(t)) cons.push({ type: "no_examples", rule: "禁止示例" });
  // 验证标准
  if (/(验收|成功标准|如何判断|自检|符合.{0,6}要求)/.test(t)) cons.push({ type: "verification", rule: "声明了验证标准" });
  return cons;
}

export function outputCheck({ contract = "", output = "" } = {}) {
  if (!contract || !contract.trim()) {
    throw new Error("输入为空：请提供契约文本（--contract）");
  }
  if (!output || !output.trim()) {
    throw new Error("输入为空：请提供实际输出文本（--output）");
  }
  const constraints = extractConstraints(contract);
  const deviations = [];
  const satisfied = [];
  for (const c of constraints) {
    let pass = true;
    let detail = "";
    const out = String(output || "");
    if (c.type === "format") {
      if (c.rule === "JSON 格式") pass = /^[{[]/.test(out.trim());
      else if (c.rule === "分点/列表格式") pass = /(^|\n)[-*•]\s|(^|\n)\d+[.、]/m.test(out);
      else if (c.rule === "表格格式") pass = /\|.*\|/.test(out) || /(^|\n)\|/.test(out);
      else if (c.rule === "Markdown 格式") pass = /(^|\n)#{1,6}\s|(\*\*|__)|```/m.test(out);
      else if (c.rule === "代码块格式") pass = /```/.test(out);
      else pass = true;
    } else if (c.type === "length") {
      pass = out.length <= c.max;
      detail = `实际 ${out.length} 字`;
    } else if (c.type === "citation") {
      pass = /(来源|引用|\[.*\]\(|http|参考文献|注)/.test(out);
    } else if (c.type === "no_fabricate") {
      // 禁止编造：无法确定性验证内容真假，检查是否含来源/标注（诚实降级说明）
      pass = /(未核实|暂无来源|不确定|依据|来源)/.test(out);
      if (pass) detail = "输出含来源/不确定性标注";
    } else if (c.type === "no_examples") {
      pass = !/例如|比如|举例/.test(out);
    } else if (c.type === "verification") {
      pass = true; // 验证标准属于 prompt 自身要素，输出侧不判
      continue;
    }
    const item = { rule: c.rule, pass, detail };
    if (pass) satisfied.push(item);
    else deviations.push(item);
  }
  const coverage = constraints.length ? Math.round(((constraints.length - deviations.length) / constraints.length) * 100) : null;
  return {
    meta: { engine: "output-check.mjs v1.1.0", mode: "output-check", constraints: constraints.length },
    compliant: deviations.length === 0,
    coverage_pct: coverage,
    satisfied,
    deviations,
    fixes: deviations.map((d) => `[${d.rule}] ${d.detail ? `${d.detail}；` : ""}按契约修正输出后复验（run-eval.mjs --output 回归）`),
    verdict: deviations.length === 0 ? "输出符合契约约束" : deviations.length <= 2 ? "轻度偏差：建议按修复建议修订" : "明显偏差：建议系统修订后回归",
  };
}

// ================= CLI =================
if (isMain(import.meta)) {
  const args = process.argv.slice(2);
  const opt = makeOpt(args);
  if (args.includes("--help") || args.includes("-h")) {
    console.log("用法: node scripts/output-check.mjs --contract <prompt.txt> --output <output.txt> [--json]");
    console.log("说明: 输出侧契约验证（格式/长度/引用/禁止项），与契约审计互补。");
    process.exit(0);
  }
  const wantJson = args.includes("--json");
  const cp = opt("contract");
  const op = opt("output");
  if (!cp || !op) {
    console.error("✗ 需 --contract 与 --output 两个文件参数");
    process.exit(2);
  }
  let contract, output;
  try {
    contract = readFileSync(cp, "utf8").replace(/^\uFEFF/, "");
    output = readFileSync(op, "utf8").replace(/^\uFEFF/, "");
  } catch (e) {
    console.error(`✗ 读取失败: ${e.message}`);
    process.exit(2);
  }
  let result;
  try {
    result = outputCheck({ contract, output });
  } catch (e) {
    console.error(`✗ ${e.message}`);
    process.exit(1);
  }
  if (wantJson) {
    process.stdout.write(JSON.stringify(result, null, 2) + "\n");
  } else {
    console.log("=== 输出侧契约验证 ===");
    console.log(`覆盖: ${result.coverage_pct === null ? "-（无契约约束）" : `${result.coverage_pct}%（${result.meta.constraints - result.deviations.length}/${result.meta.constraints} 项约束）`}`);
    if (result.deviations.length) {
      console.log("偏差:");
      for (const d of result.deviations) console.log(`  ✗ ${d.rule}${d.detail ? `（${d.detail}）` : ""}`);
      console.log("\n修复建议:");
      for (const f of result.fixes) console.log(`  - ${f}`);
    } else {
      console.log("✓ 输出符合全部契约约束");
    }
    console.log(`判定: ${result.verdict}`);
  }
}
