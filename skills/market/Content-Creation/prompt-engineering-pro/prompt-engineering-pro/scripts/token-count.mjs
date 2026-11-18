#!/usr/bin/env node
// token-count.mjs — Token 经济性引擎（P3）
// 能力:
//   1. token 估算（按模型族系数：中文 1 字≈系数 token，英文 1 词≈1.3 token，与 validate.mjs 口径一致）
//   2. 预算偏差计算（目标预算 vs 实际估算）
//   3. 冗余检测: 重复约束 / 同义堆叠 / 套话 / 过度修饰（确定性规则 + 证据引用）
//   4. 成本估算: 按模型族参考单价（--in-price/--out-price 可覆盖）
// 设计原则: 确定性（同输入恒同输出）；证据引用（每条冗余附原文+行号+规则名）；不误伤（只报高置信模式）
// 用法:
//   node scripts/token-count.mjs <prompt.txt>                 # 人类可读报告
//   node scripts/token-count.mjs <prompt.txt> --json
//   node scripts/token-count.mjs <prompt.txt> --budget 300     # 指定目标预算
//   node scripts/token-count.mjs <prompt.txt> --model-family claude  # 按模型族估算+成本
//   echo "..." | node scripts/token-count.mjs
import { readFileSync, existsSync } from "node:fs";
import { isMain, makeOpt } from "./lib.mjs";

// ================= 冗余模式库（高置信，避免误伤） =================

const REDUNDANCY_PATTERNS = {
  synonymStack: [
    { re: /请务必|务必|一定|千万(要|别)|切记/g, label: "同义堆叠（务必/一定/千万…）" },
    { re: /非常(非常|十分|特别|极其)/g, label: "同义堆叠（非常非常/十分…）" },
  ],
  emptyPhrases: [
    { re: /充分发挥(您)?(的)?(专业|全部)?(能力|水平)/g, label: "无信息量套话（请充分发挥您的专业能力…）" },
    { re: /(让我们|大家一起|携手|共同)努力/g, label: "无信息量套话（让我们一起努力…）" },
    { re: /(众所周知|不言而喻|显而易见)/g, label: "无信息量套话（众所周知…）" },
    { re: /(希望能|期待您|麻烦您)不吝/g, label: "无信息量套话（希望您不吝…）" },
  ],
  overModification: [
    { re: /(极其|非常|超级|十分|格外|特别)(重要|关键|必要|优秀|好|强大)/g, label: "过度修饰（极其重要/超级好…）" },
  ],
};

// 重复约束检测：同一约束短语（长度≥4 的关键句）出现 ≥2 次
function findRepeated(text) {
  const sentences = text.split(/[。；;！!？?\n]+/).map((s) => s.trim()).filter((s) => s.length >= 6);
  const counts = new Map();
  for (const s of sentences) counts.set(s, (counts.get(s) || 0) + 1);
  const hits = [];
  for (const [s, n] of counts) {
    if (n >= 2) {
      // v1.0.3 修复: 记录所有出现位置，行号报告第二次出现处（重复成立的位置），
      // 原实现恒报首次出现位置，对"第1行出现、第10行重复"的场景定位失准
      const positions = [];
      let from = 0;
      while (positions.length < n) {
        const idx = text.indexOf(s, from);
        if (idx < 0) break;
        positions.push(idx);
        from = idx + s.length;
      }
      const secondIdx = positions.length > 1 ? positions[1] : positions[0];
      const lineNo = text.slice(0, secondIdx).split("\n").length;
      hits.push({ rule: "重复约束（同一句出现 " + n + " 次）", quote: s.slice(0, 40), line: lineNo });
    }
  }
  return hits;
}

// ================= token 估算（按模型族系数，确定性） =================
// 系数为启发式近似：不同 tokenizer 对中文/英文的分词密度不同（如 Claude 的 BPE 对 CJK 更密集）。
// 未命中模型族时回退默认系数，保证任何输入都可估算。
export const MODEL_TOKEN_FACTORS = {
  claude: { cjk: 1.5, word: 1.3 },
  gpt: { cjk: 1.4, word: 1.3 },
  gemini: { cjk: 1.2, word: 1.3 },
  deepseek: { cjk: 1.0, word: 1.3 },
  doubao: { cjk: 1.0, word: 1.3 },
  glm: { cjk: 1.0, word: 1.3 },
  qwen: { cjk: 1.0, word: 1.3 },
  kimi: { cjk: 1.1, word: 1.3 },
  open: { cjk: 1.0, word: 1.3 },
};
const DEFAULT_FACTOR = { cjk: 1.0, word: 1.3 };

export function estimateTokens(text, modelFamily) {
  const fam = modelFamily ? String(modelFamily).toLowerCase() : "default";
  const factor = MODEL_TOKEN_FACTORS[fam] || DEFAULT_FACTOR;
  const cjk = (text.match(/[\u4e00-\u9fff\u3000-\u303f\uff00-\uffef]/g) || []).length;
  const nonCjkWords = text.split(/\s+/).filter(Boolean).filter((t) => !/[\u4e00-\u9fff\u3000-\u303f\uff00-\uffef]/.test(t)).length;
  const tokens = Math.round(cjk * factor.cjk + nonCjkWords * factor.word);
  return { cjk, nonCjkWords, tokens, model_family: fam, factor: { ...factor } };
}

// ================= token 报告（估算口径，确定性） =================
// 说明：估算为启发式，精确值以目标模型 API 计费口径为准。
export function tokenReport(text, modelFamily) {
  const est = estimateTokens(text, modelFamily);
  return {
    estimate: est,
    precise: null,
    engine: "estimate",
    note: `估算口径（模型族 ${est.model_family}；中文 1 字≈${est.factor.cjk} token，英文 1 词≈${est.factor.word} token）`,
  };
}

// ================= 成本估算（参考单价 + 用户覆盖） =================
// 参考单价为公开列表价的近似值（每百万 token，美元），可能变化；精确值以目标模型官方计费为准。
export const REFERENCE_PRICING = {
  claude: { input_per_1m: 3, output_per_1m: 15, currency: "USD", source: "参考公开列表价（近似）" },
  gpt: { input_per_1m: 2.5, output_per_1m: 10, currency: "USD", source: "参考公开列表价（近似）" },
  gemini: { input_per_1m: 1.25, output_per_1m: 5, currency: "USD", source: "参考公开列表价（近似）" },
  deepseek: { input_per_1m: 0.27, output_per_1m: 1.1, currency: "USD", source: "参考公开列表价（近似）" },
  doubao: { input_per_1m: 0.8, output_per_1m: 2, currency: "USD", source: "参考公开列表价（近似）" },
  glm: { input_per_1m: 0.5, output_per_1m: 2, currency: "USD", source: "参考公开列表价（近似）" },
  qwen: { input_per_1m: 0.5, output_per_1m: 2, currency: "USD", source: "参考公开列表价（近似）" },
  kimi: { input_per_1m: 0.6, output_per_1m: 2.5, currency: "USD", source: "参考公开列表价（近似）" },
};

export function costReport(text, modelFamily, { inPrice, outPrice, outputTokens = 0 } = {}) {
  const est = estimateTokens(text, modelFamily);
  const fam = est.model_family;
  const ref = REFERENCE_PRICING[fam];
  const inP = typeof inPrice === "number" ? inPrice : (ref ? ref.input_per_1m : null);
  const outP = typeof outPrice === "number" ? outPrice : (ref ? ref.output_per_1m : null);
  let cost = null;
  if (typeof inP === "number") {
    cost = (est.tokens / 1e6) * inP + (outputTokens / 1e6) * (typeof outP === "number" ? outP : 0);
    cost = Math.round(cost * 1e6) / 1e6;
  }
  return {
    model_family: fam,
    input_tokens: est.tokens,
    output_tokens: outputTokens,
    input_price_per_1m: inP ?? null,
    output_price_per_1m: outP ?? null,
    estimated_cost: cost,
    currency: ref ? ref.currency : "USD",
    source: ref ? ref.source : "用户指定单价",
    note: "参考单价为公开列表价的近似值，可能变化；精确值以目标模型官方计费为准（--in-price/--out-price 可覆盖）。",
  };
}

// ================= 冗余检测 =================
export function detectRedundancy(text) {
  const findings = [];
  const notes = [];

  // 1. 同义堆叠 / 套话 / 过度修饰（正则命中即报）
  for (const [cat, patterns] of Object.entries(REDUNDANCY_PATTERNS)) {
    for (const p of patterns) {
      const re = new RegExp(p.re.source, p.re.flags.includes("g") ? p.re.flags : p.re.flags + "g");
      let m;
      while ((m = re.exec(text)) !== null) {
        const lineNo = text.slice(0, m.index).split("\n").length;
        findings.push({ type: cat, rule: p.label, quote: m[0], line: lineNo, savings: m[0].length });
        if (re.lastIndex === m.index) re.lastIndex++;
        if (findings.length >= 15) break;
      }
      if (findings.length >= 15) break;
    }
    if (findings.length >= 15) break;
  }

  // 2. 重复约束
  const repeated = findRepeated(text);
  findings.push(...repeated.map((h) => ({ type: "duplicate", rule: h.rule, quote: h.quote, line: h.line, savings: h.quote.length })));

  return { findings: findings.slice(0, 20), notes };
}

// ================= 预算计算 =================
export function budgetReport(text, targetBudget, modelFamily) {
  const est = estimateTokens(text, modelFamily);
  const deviation = targetBudget != null && targetBudget > 0 ? ((est.tokens - targetBudget) / targetBudget) * 100 : null;
  return {
    estimate: est,
    target_budget: targetBudget ?? null,
    deviation_pct: deviation == null ? null : Math.round(deviation * 10) / 10,
    over_budget: deviation != null && deviation > 0,
    band: targetBudget == null
      ? null
      : deviation <= -20 ? "精简档（低于预算 20%+）"
        : deviation <= 0 ? "标准档"
          : deviation <= 30 ? "超预算（需压缩）"
            : "严重超预算（必须压缩）",
  };
}

// ================= 可执行压缩步骤（compress 意图落地，按 token-economy.md §4 优先级） =================
const COMPRESS_PRIORITY = {
  duplicate: 1,
  emptyPhrases: 2,
  synonymStack: 3,
  overModification: 4,
};
const COMPRESS_ACTION = {
  duplicate: "整句删除（重复约束，最高置信）",
  emptyPhrases: "整句删除（无信息量套话）",
  synonymStack: "保留一个强化词，删除其余堆叠",
  overModification: "删除过度修饰词（无测量对象）",
};

export function compressSteps(text) {
  const { findings } = detectRedundancy(text);
  const steps = findings
    .map((f) => ({
      priority: COMPRESS_PRIORITY[f.type] ?? 5,
      action: COMPRESS_ACTION[f.type] || "精简措辞（人工判断，引擎只提示）",
      rule: f.rule,
      quote: f.quote,
      line: f.line,
      savings: f.savings,
    }))
    .sort((a, b) => a.priority - b.priority);
  const totalSavings = steps.reduce((s, x) => s + (x.savings || 0), 0);
  return {
    steps: steps.slice(0, 10),
    total_savings_chars: totalSavings,
    note: "压缩优先级（token-economy.md §4）：1 重复约束 → 2 套话 → 3 同义堆叠 → 4 过度修饰 → 5 措辞精简（人工）；压缩 ≥30% 时建议 eval 回归验证不降性能",
  };
}

// ================= CLI =================
// v1.0.3 修复: 改用 lib.isMain 的稳健判定（Windows 含空格/中文路径下不再误判）
if (isMain(import.meta)) {
  const args = process.argv.slice(2);
  if (args.includes("--help") || args.includes("-h")) {
    console.log("用法: node " + process.argv[1].split(/[\\/]/).pop() + " [选项]（完整用法见脚本头部注释）");
    process.exit(0);
  }
  const opt = makeOpt(args);
  const wantJson = args.includes("--json");
  const budgetIdx = args.indexOf("--budget");
  const targetBudget = budgetIdx >= 0 ? Number(args[budgetIdx + 1]) : null;
  const modelFamily = opt("model-family");
  const inPrice = opt("in-price") != null ? Number(opt("in-price")) : undefined;
  const outPrice = opt("out-price") != null ? Number(opt("out-price")) : undefined;
  // v1.0.3 修复: 已知选项的值位置不参与"文件参数"判定，避免 --model-family claude 等取值被误判为输入文件
  const knownOpts = new Set(["--budget", "--model-family", "--in-price", "--out-price"]);
  const valueIdx = new Set();
  for (let i = 0; i < args.length; i++) if (knownOpts.has(args[i])) valueIdx.add(i + 1);
  const fileArg = args.find((a, i) => !valueIdx.has(i) && !a.startsWith("--") && !/^-?\d+$/.test(a) && !a.startsWith("{") && !a.startsWith("["));
  let input;
  if (fileArg) {
    // v1.0.3 修复: 文件不存在时给出友好错误，不再抛出原始 ENOENT
    if (!existsSync(fileArg)) {
      console.error(`错误: 输入文件不存在: ${fileArg}`);
      process.exit(1);
    }
    input = readFileSync(fileArg, "utf8");
  } else input = readFileSync(0, "utf8");

  const result = {
    budget: budgetReport(input, targetBudget, modelFamily),
    redundancy: detectRedundancy(input),
    compress: compressSteps(input),
    cost: costReport(input, modelFamily, { inPrice, outPrice }),
  };

  if (wantJson) {
    process.stdout.write(JSON.stringify(result, null, 2) + "\n");
  } else {
    const b = result.budget;
    console.log("=== Token 经济性报告 ===");
    console.log(`估算: ${b.estimate.tokens} token（中文 ${b.estimate.cjk} 字，英文 ${b.estimate.nonCjkWords} 词；模型族 ${b.estimate.model_family}）`);
    if (b.target_budget != null) {
      console.log(`目标预算: ${b.target_budget} token；偏差: ${b.deviation_pct}%；档位: ${b.band}`);
    } else {
      console.log("目标预算: 未指定（用 --budget <n> 设置）");
    }
    const c = result.cost;
    if (c.input_price_per_1m != null) {
      console.log(`成本估算: 输入 ${c.input_tokens} token × ${c.input_price_per_1m}/1M ≈ ${c.estimated_cost} ${c.currency}（${c.source}；精确值以官方计费为准）`);
    } else {
      console.log("成本估算: 未给出单价（--in-price/--out-price 可覆盖，或按目标模型官方计费）");
    }
    console.log("");
    console.log(`冗余检测: 命中 ${result.redundancy.findings.length} 处`);
    for (const f of result.redundancy.findings) {
      console.log(`  - [${f.type}] 第${f.line}行 "${f.quote}" ← ${f.rule}（可省 ~${f.savings} 字符）`);
    }
    if (!result.redundancy.findings.length) console.log("  （未发现高置信冗余）");
  }
}
