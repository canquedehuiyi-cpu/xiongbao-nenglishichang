#!/usr/bin/env node
// eval-case-gen.mjs — 评测用例生成引擎（v1.1.0）
// 功能: 从 prompt + 需求生成可执行的 JSON 评测清单（输入场景/期望输出/通过标准/类型），
//       供 run-eval / 人工验收使用。对齐 Anthropic 官方"先建评测再优化"方法论。
// 安全边界:
//   - 生成的用例仅为"文本级通过标准"，不包含任何可执行/危险内容生成指令。
//   - 不编造输入数据；需要真实输入的用例以 {占位} 标注并提示人工补充。
// 用法:
//   node scripts/eval-case-gen.mjs <prompt.txt> [--requirement "需求描述"] [--json]
//   echo "提示词文本" | node scripts/eval-case-gen.mjs --json
import { readFileSync } from "node:fs";
import { isMain } from "./lib.mjs";

// ================= 约束信号 → 用例生成规则 =================

const RULES = [
  {
    key: "format_json",
    signal: /JSON|json|结构化输出|机器可读/,
    type: "positive",
    input_desc: "正常输入",
    expected: "输出必须为合法 JSON",
    pass: "可被 JSON.parse 解析，字段符合 prompt 声明的结构",
    coverage: "Output format",
  },
  {
    key: "format_markdown",
    signal: /Markdown|markdown|标题|表格|列表|分点|## /,
    type: "positive",
    input_desc: "正常输入",
    expected: "输出按 prompt 指定的 Markdown 结构组织",
    pass: "标题层级/表格/列表与 prompt 要求一致",
    coverage: "Output format",
  },
  {
    key: "length_limit",
    signal: /不超过\s*\d+|字数.{0,6}\d+|在\s*\d+\s*字内|at most|within\s*\d+|max\s*\d+/i,
    type: "positive",
    input_desc: "正常输入",
    expected: "输出长度不超过 prompt 声明上限",
    pass: "统计输出字符/词数 ≤ 上限",
    coverage: "Constraints",
  },
  {
    key: "citation",
    signal: /引用|来源|原文|cite|source|reference/i,
    type: "positive",
    input_desc: "含可引用材料",
    expected: "结论必须引用原文",
    pass: "每条关键结论带原文引用或定位",
    coverage: "Verification",
  },
  {
    key: "anti_hallucination",
    signal: /不要编造|不编造|无依据|无来源|不要虚构|do not (invent|fabricate)/i,
    type: "boundary",
    input_desc: "缺少关键信息/材料",
    expected: "无依据时明确标注「未找到依据」而非编造",
    pass: "输出含「未找到依据/无法确认」显式声明",
    coverage: "Failure handling",
  },
  {
    key: "tone",
    signal: /语气|风格|口吻|正式|轻松|tone|style/i,
    type: "positive",
    input_desc: "正常输入",
    expected: "语气/风格符合 prompt 声明",
    pass: "抽样评审语气与声明一致",
    coverage: "Style",
  },
  {
    key: "constraint_forbidden",
    signal: /不要|不能|不许|禁止|不得|avoid|do not|must not/i,
    type: "negative",
    input_desc: "诱导 prompt 明令禁止的行为",
    expected: "不执行禁止项，拒绝或明确说明",
    pass: "输出不含被禁止内容，且有明确拒绝/说明",
    coverage: "Constraints",
  },
  {
    key: "edge_missing_info",
    signal: /边界|缺|空|不确定|边缘|edge|empty|missing/i,
    type: "boundary",
    input_desc: "信息缺失/输入为空",
    expected: "按 prompt 的兜底指令处理（默认值/明确说缺）",
    pass: "不僵住、不编造，遵循兜底路径",
    coverage: "Failure handling",
  },
  {
    key: "multi_step",
    signal: /先.{0,6}(再|然后)|步骤|分步|第.{0,2}步|顺序/i,
    type: "positive",
    input_desc: "分步输入",
    expected: "按声明顺序分步产出",
    pass: "步骤顺序与 prompt 一致，交接物明确",
    coverage: "Process",
  },
];

// 主题抽取（不编造；无显式主题则用通用占位）
function extractTopic(prompt) {
  const m = prompt.match(/(?:关于|围绕|主题是|内容是)\s*([\u4e00-\u9fffA-Za-z0-9]{2,20})/);
  return m ? m[1] : "{任务主题}";
}

// ================= 主函数 =================

export function evalCaseGen(prompt, requirement = "") {
  if (!prompt || !prompt.trim()) {
    throw new Error("输入为空：请提供提示词文本（文件参数或 stdin）");
  }
  const topic = extractTopic(prompt);
  const cases = [];
  const coverage = new Set();
  let seq = 0;
  for (const rule of RULES) {
    if (rule.signal.test(prompt)) {
      seq++;
      cases.push({
        id: `EVAL-${String(seq).padStart(2, "0")}`,
        key: rule.key,
        type: rule.type,
        input_desc: rule.input_desc,
        expected: rule.expected,
        pass_criteria: rule.pass,
        note: rule.key === "anti_hallucination" ? "输入材料故意缺该信息" : rule.key === "edge_missing_info" ? "输入可留空/缺字段" : undefined,
      });
      coverage.add(rule.coverage);
    }
  }
  // 始终补基础用例：正常输入可达性 + 结果可理解
  if (!cases.some((c) => c.key === "format_json" && c.type === "positive")) {
    seq++;
    cases.push({
      id: `EVAL-${String(seq).padStart(2, "0")}`,
      key: "basic_complete",
      type: "positive",
      input_desc: `围绕「${topic}」的正常输入`,
      expected: "产出完整、可用的结果",
      pass_criteria: "结果覆盖 prompt 全部显式要求，无遗漏项",
    });
    coverage.add("Objective");
  }
  seq++;
  cases.push({
    id: `EVAL-${String(seq).padStart(2, "0")}`,
    key: "basic_understandable",
    type: "positive",
    input_desc: `围绕「${topic}」的正常输入`,
    expected: "结果清晰可读，无需追问即可理解",
      pass_criteria: "冷读测试通过（第三方可独立理解）",
  });
  coverage.add("Verification");

  return {
    meta: {
      engine: "eval-case-gen.mjs v1.1.0",
      mode: "eval-case-generation",
      source_prompt_theme: topic,
      requirement: requirement || "未提供（仅基于 prompt 自动推断）",
      safety_note: "用例仅为文本级通过标准，不含可执行/危险指令；真实输入以占位符标注需人工补充",
    },
    cases,
    coverage: Array.from(coverage),
    summary: { total: cases.length, positive: cases.filter((c) => c.type === "positive").length, boundary: cases.filter((c) => c.type === "boundary").length, negative: cases.filter((c) => c.type === "negative").length },
  };
}

// ================= CLI =================

if (isMain(import.meta)) {
  const args = process.argv.slice(2);
  if (args.includes("--help") || args.includes("-h")) {
    console.log("用法: node scripts/eval-case-gen.mjs <prompt.txt> [--requirement \"需求\"] [--json]");
    process.exit(0);
  }
  const wantJson = args.includes("--json");
  const reqArg = args.includes("--requirement") ? args[args.indexOf("--requirement") + 1] || "" : "";
  const fileArg = args.find((a) => !a.startsWith("--") && !a.startsWith("{") && !a.startsWith("[") && !/^-?\d+$/.test(a));
  let input;
  if (fileArg) {
    input = readFileSync(fileArg, "utf8").replace(/^\uFEFF/, "");
  } else {
    input = readFileSync(0, "utf8").replace(/^\uFEFF/, "");
  }
  let result;
  try {
    result = evalCaseGen(input, reqArg);
  } catch (e) {
    console.error(`✗ ${e.message}`);
    process.exit(1);
  }
  if (wantJson) {
    process.stdout.write(JSON.stringify(result, null, 2) + "\n");
  } else {
    console.log("=== 评测用例生成 ===");
    console.log(`主题: ${result.meta.source_prompt_theme}`);
    console.log(`覆盖契约要素: ${result.coverage.join("、")}`);
    console.log("");
    for (const c of result.cases) {
      const tag = { positive: "正向", boundary: "边界", negative: "负向" }[c.type];
      console.log(`[${c.id}] ${tag} — ${c.input_desc}`);
      console.log(`    期望: ${c.expected}`);
      console.log(`    通过标准: ${c.pass_criteria}`);
      if (c.note) console.log(`    注: ${c.note}`);
    }
    console.log(`\n合计 ${result.summary.total} 条（正向 ${result.summary.positive} / 边界 ${result.summary.boundary} / 负向 ${result.summary.negative}）`);
  }
}
