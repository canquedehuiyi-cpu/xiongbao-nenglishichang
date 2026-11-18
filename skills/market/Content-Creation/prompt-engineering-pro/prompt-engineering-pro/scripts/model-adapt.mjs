#!/usr/bin/env node
// model-adapt.mjs — 模型适配路由引擎（v1.1.0）
// 功能: 按 model_family（claude/gpt/gemini/deepseek/doubao/glm/qwen/kimi/open）返回技法包
//       （结构语法 / CoT 策略 / 输出格式 / 防幻觉 / 长上下文 / System Prompt 写法），
//       与 technique-router.mjs 组合成"模型 × 任务"双层路由。
// 确定性: 纯规则匹配 + 官方文档有据内容（来源见各技法包 source 字段）；同一输入恒同输出。
// 安全: 技法包全部来自官方公开文档（Anthropic/OpenAI/Google/DeepSeek 等 best practices），
//       不引入未证实技巧；不输出任何可绕过安全机制的提示。
// 用法:
//   node scripts/model-adapt.mjs --model claude            # 按模型族直接取技法包
//   node scripts/model-adapt.mjs --request "claude 3.7 写 agent"  # 文本内检测模型族
//   node scripts/model-adapt.mjs --model gpt-o4 --json
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";
import { isMain, makeOpt } from "./lib.mjs";

const ROOT = join(dirname(fileURLToPath(import.meta.url)), "..");

// ---------- 模型族技法包（官方有据内容） ----------
// 推理模型族（不给显式 CoT，走内部校验）: 在 FAMILIES 的 reasoning 字段标记
const FAMILIES = {
  claude: {
    label: "Claude",
    reasoning: false,
    structure: "XML 标签分节（<task>/<context>/<output>…）——官方推荐的结构化输入",
    cot: "支持 Extended Thinking；budget 建议从最低 1024 token 逐步调优；不要用“think”一词替代思考机制，措辞用“内部思考”",
    output: "正向指令声明输出格式（Output format 用“请”而非“不要”），Multishot 3-5 个多样相关示例",
    anti_hallucination: "引用接地 quote-before-answer、明确“不知道就说不知道”",
    long_context: "长文档置顶关键信息、query 放末尾、分块+引用",
    system_prompt: "高遵循度：可放详细规则与边界，控制标签（如自定义标签）标注工具结果来源",
    source: "Anthropic 官方文档（Claude best practices / Extended Thinking / Multishot）",
  },
  gpt: {
    label: "GPT",
    reasoning: true, // o 系推理模型族
    structure: "Markdown 标题分节 + 清晰指令——OpenAI 官方 best practices",
    cot: "o 系禁用显式 CoT 与逐字推理指令（模型内部推理）；非 o 系可给步骤式提示",
    output: "JSON mode / 结构化输出优先（response_format）；few-shot 示例位置在指令后",
    anti_hallucination: "要求先引用材料再作答、给“不确定就标注”的兜底",
    long_context: "关键信息前置、任务指令放末尾（recency bias）",
    system_prompt: "高遵循度：明确角色、任务、边界；工具调用给严格 schema",
    source: "OpenAI 官方 Prompt engineering best practices / Structured outputs",
  },
  gemini: {
    label: "Gemini",
    reasoning: true, // gemini-thinking 族
    structure: "清晰指令 + 结构化输出（JSON schema via responseSchema）",
    cot: "thinking 模型族（gemini-2.5-thinking 等）内部推理，不给显式 CoT；普通模型可逐步提示",
    output: "JSON schema / 结构化输出优先；示例给 1-2 个",
    anti_hallucination: "引用接地 + 低置信度标注",
    long_context: "长上下文窗口大：可放全文，但关键指令前置、末尾重申目标",
    system_prompt: "高遵循度：放规则与约束",
    source: "Google Gemini 官方文档（structured output / thinking）",
  },
  deepseek: {
    label: "DeepSeek",
    reasoning: true, // deepseek-r1 族
    structure: "中文简洁指令 + CoT 友好",
    cot: "R1 推理族走内部推理，不给显式 CoT；普通 V 系可逐步提示",
    output: "显式输出格式（JSON/Markdown）",
    anti_hallucination: "引用接地 + 缺料兜底",
    long_context: "长上下文处理一般：精简、置顶关键、分块",
    system_prompt: "中文指令最优：写清楚规则与边界",
    source: "DeepSeek 官方文档（reasoning model / prompt usage）",
  },
  doubao: {
    label: "豆包",
    reasoning: false,
    structure: "中文简洁指令",
    cot: "支持逐步推理（按需）",
    output: "显式输出格式",
    anti_hallucination: "引用接地 + 缺料兜底",
    long_context: "长上下文处理一般：精简、置顶关键",
    system_prompt: "中文指令最优：写清楚角色与边界",
    source: "字节豆包官方文档（prompt 最佳实践）",
  },
  glm: {
    label: "GLM",
    reasoning: false,
    structure: "中文结构化指令",
    cot: "支持逐步推理（按需）",
    output: "显式输出格式",
    anti_hallucination: "引用接地 + 缺料兜底",
    long_context: "可处理中等长度：置顶关键信息",
    system_prompt: "中文指令最优",
    source: "智谱 GLM 官方文档",
  },
  qwen: {
    label: "Qwen",
    reasoning: false,
    structure: "中文简洁指令",
    cot: "支持逐步推理（按需）",
    output: "显式输出格式",
    anti_hallucination: "引用接地 + 缺料兜底",
    long_context: "可处理较长输入：分块+关键前置",
    system_prompt: "中文指令最优",
    source: "阿里 Qwen 官方文档",
  },
  kimi: {
    label: "Kimi",
    reasoning: true, // kimi-k2 推理族
    structure: "中文简洁指令",
    cot: "k2 推理族走内部推理，不给显式 CoT",
    output: "显式输出格式",
    anti_hallucination: "引用接地 + 缺料兜底",
    long_context: "超长上下文（长文本处理强）：全文可放，关键指令前置",
    system_prompt: "中文指令最优",
    source: "月之暗面 Kimi 官方文档",
  },
  open: {
    label: "开源/通用",
    reasoning: false,
    structure: "保守结构：Markdown 分节 + 显式格式约束",
    cot: "弱指令模型避免过复杂 CoT；按模型能力给步骤",
    output: "显式格式 + 示例（few-shot 对弱模型更稳）",
    anti_hallucination: "强防幻觉：引用接地 + 缺料兜底 + 自检",
    long_context: "长上下文可能丢失：精简、分块",
    system_prompt: "指令格式敏感：写清楚、不依赖隐式理解",
    source: "dair-ai Prompt Engineering Guide（开源模型章节）",
  },
};

// 推理模型族别名（统一到 family）
const REASONING_ALIAS = {
  "claude-extended": "claude",
  "gpt-o1": "gpt", "gpt-o3": "gpt", "gpt-o4": "gpt", "o1": "gpt", "o3": "gpt", "o4": "gpt",
  "gemini-thinking": "gemini",
  "deepseek-r1": "deepseek", "r1": "deepseek",
  "kimi-k2": "kimi", "k2": "kimi",
};

const FAMILY_KEYWORDS = [
  ["claude", ["claude"]],
  ["gpt", ["gpt-4", "gpt-5", "gpt-", "openai", "chatgpt"]],
  ["gemini", ["gemini"]],
  ["deepseek", ["deepseek"]],
  ["doubao", ["豆包", "doubao", "豆包大模型", "volcengine"]],
  ["glm", ["glm", "智谱"]],
  ["qwen", ["qwen", "通义", "通义千问"]],
  ["kimi", ["kimi", "moonshot"]],
];

// 从请求文本检测 model_family（未命中返回 null）
export function detectModelFamily(text) {
  const t = String(text || "").toLowerCase();
  if (!t.trim()) return null;
  // 先查推理族别名（更精确）
  for (const [alias, family] of Object.entries(REASONING_ALIAS)) {
    if (t.includes(alias.toLowerCase())) return { family, alias, reasoning: true };
  }
  for (const [family, kws] of FAMILY_KEYWORDS) {
    if (kws.some((k) => t.includes(k.toLowerCase()))) {
      return { family, alias: null, reasoning: FAMILIES[family].reasoning };
    }
  }
  return null;
}

// 解析 --model 参数（支持 claude / claude-3.7 / gpt-o4 / deepseek-r1 等）
export function resolveModel(modelArg) {
  const s = String(modelArg || "").toLowerCase().trim();
  if (!s) return null;
  for (const [alias, family] of Object.entries(REASONING_ALIAS)) {
    if (s === alias || s.startsWith(alias + "-") || s.startsWith(alias + "/") || s.startsWith(alias + ".")) {
      return { family, alias, reasoning: true, raw: s };
    }
  }
  for (const [family, kws] of FAMILY_KEYWORDS) {
    if (kws.some((k) => s === k || s.startsWith(k + "-") || s.startsWith(k + "/"))) {
      return { family, alias: null, reasoning: FAMILIES[family].reasoning, raw: s };
    }
  }
  if (FAMILIES[s]) return { family: s, alias: null, reasoning: FAMILIES[s].reasoning, raw: s };
  return null;
}

export function modelAdapt({ model = null, request = "", dir = ROOT } = {}) {
  // 解析模型族：优先 --model，其次从 request 文本检测
  let resolved = model ? resolveModel(model) : null;
  let detected = null;
  if (!resolved) {
    detected = detectModelFamily(request);
    if (detected) resolved = { family: detected.family, alias: detected.alias, reasoning: detected.reasoning, raw: detected.alias || detected.family };
  }
  if (!resolved) {
    return {
      ok: false,
      error: "未识别到模型族：请用 --model 指定（claude/gpt/gemini/deepseek/doubao/glm/qwen/kimi/open）或在请求中提及模型名",
      supported: Object.keys(FAMILIES),
      reasoning_families: ["gpt-o系列", "gemini-thinking", "deepseek-r1", "kimi-k2", "claude-extended"],
    };
  }
  const fam = FAMILIES[resolved.family];
  return {
    ok: true,
    model_family: resolved.family,
    label: fam.label,
    detected_from: model ? "参数 --model" : (detected ? "请求文本检测" : "未指定"),
    raw_model: resolved.raw || null,
    reasoning_model: resolved.reasoning,
    pack: {
      structure: fam.structure,
      cot: fam.cot,
      output: fam.output,
      anti_hallucination: fam.anti_hallucination,
      long_context: fam.long_context,
      system_prompt: fam.system_prompt,
    },
    technique_sync: "与 technique-router 组合为「模型 × 任务」双层路由：先用本引擎取模型技法包，再按任务特征选技法",
    token_tip: fam.reasoning ? "推理模型：少写显式推理步骤，省 token 且避免干扰内部推理" : "非推理模型：可给显式步骤，注意长度预算",
    source: fam.source,
  };
}

// ================= CLI =================
if (isMain(import.meta)) {
  const args = process.argv.slice(2);
  const opt = makeOpt(args);
  if (args.includes("--help") || args.includes("-h")) {
    console.log("用法: node scripts/model-adapt.mjs --model <族> | --request <文本> [--json]");
    console.log("模型族: claude/gpt/gemini/deepseek/doubao/glm/qwen/kimi/open；支持 claude-3.7、gpt-o4、deepseek-r1 等别名");
    process.exit(0);
  }
  const json = args.includes("--json");
  const model = opt("model");
  const request = opt("request") || "";
  const r = modelAdapt({ model, request });
  if (!r.ok) {
    process.stderr.write(`✗ ${r.error}\n`);
    process.exit(2);
  }
  if (json) {
    process.stdout.write(JSON.stringify(r, null, 2) + "\n");
  } else {
    console.log(`=== 模型适配路由 ===`);
    console.log(`模型族: ${r.label}${r.reasoning_model ? "（推理模型族）" : ""}${r.raw_model ? `  · 原始: ${r.raw_model}` : ""}`);
    console.log(`来源: ${r.detected_from}`);
    console.log(`结构: ${r.pack.structure}`);
    console.log(`CoT: ${r.pack.cot}`);
    console.log(`输出格式: ${r.pack.output}`);
    console.log(`防幻觉: ${r.pack.anti_hallucination}`);
    console.log(`长上下文: ${r.pack.long_context}`);
    console.log(`System Prompt: ${r.pack.system_prompt}`);
    console.log(`\n${r.token_tip}`);
    console.log(`依据: ${r.source}`);
  }
}
