#!/usr/bin/env node
// capability-digest.mjs — 能力摘要引擎（「跟上最新实践」的执行端）
// 能力: 从联网拉取的官方文档/缓存文本中按关键词提取模型能力信号
//       （上下文窗口 / 工具调用 / 推理 / 多模态 / 结构化输出 / 知识截止），
//       供 Fit 维度标注"可能过时/已更新"，防止依据静态矩阵做陈旧判断。
// 设计原则:
//   1. 确定性: 纯关键词信号，同输入恒同输出
//   2. 诚实标注: 提取结果标注来源与口径，不做超出文本的推断
// 输入来源:
//   - 文本（stdin 或文件）
//   - --cache <fetch-prompt-practices 缓存 json>：对缓存中每个结果的 snippet 做信号提取
// 用法:
//   node scripts/capability-digest.mjs <doc.txt>
//   node scripts/capability-digest.mjs --cache <fetch-cache.json> --json
//   echo "<文档文本>" | node scripts/capability-digest.mjs
import { readFileSync, existsSync } from "node:fs";
import { isMain, makeOpt } from "./lib.mjs";

// 能力信号库（关键词 + 口径说明）
const SIGNALS = [
  {
    name: "context_window",
    label: "上下文窗口",
    detail: "文档是否给出上下文长度（如 128k/200k/1M）",
    re: /(context window|context length|上下文(长度|窗口)|128k|200k|1m\b|2m\b|1m token|1m tokens|百万级)/i,
  },
  {
    name: "function_calling",
    label: "工具调用",
    detail: "是否支持 function calling / 工具调用",
    re: /(function calling|tool use|tools?\b|工具调用|函数调用)/i,
  },
  {
    name: "reasoning",
    label: "推理能力",
    detail: "是否提及推理/思维链/扩展思考",
    re: /(reasoning|chain[- ]of[- ]thought|extended thinking|推理|思维链|深度思考)/i,
  },
  {
    name: "vision",
    label: "多模态/图像",
    detail: "是否支持图像/多模态输入",
    re: /(vision|multimodal|multi[- ]modal|image input|图像输入|多模态|视觉理解)/i,
  },
  {
    name: "structured_output",
    label: "结构化输出",
    detail: "是否支持结构化输出 / JSON Schema",
    re: /(structured output|json schema|json mode|structured outputs|结构化输出)/i,
  },
  {
    name: "knowledge_cutoff",
    label: "知识截止",
    detail: "是否给出知识截止时间",
    re: /(knowledge cutoff|knowledge as of|training data|知识截止|训练数据至)/i,
  },
];

const MODEL_PATTERN = /(?:gpt[- ]?[45](?:\.\d)?(?:[- ]?(?:mini|turbo|pro|omni))?|claude[- ](?:3|4|5)(?:\.\d)?(?:[- ]?(?:sonnet|opus|haiku))?|gemini[- ]?(?:1|2|3)\.?\d?(?:[- ]?(?:pro|flash|ultra))?|deepseek[- ](?:v|r)\d?|qwen\d*(?:[- ]?(?:max|plus|turbo))?|doubao[- ]?\d?\.?\d?(?:[- ]?(?:pro|lite))?|kimi(?:[- ](?:k1\.5|k2))?|glm[- ]\d(?:[- ]?air)?|llama[- ]\d)/gi;

// 从单段文本提取信号
function extractFrom(text) {
  const signals = [];
  for (const s of SIGNALS) {
    const m = text.match(s.re);
    if (m) {
      // 提取可能的数值/日期细节（上下文窗口或知识截止）
      let detail = null;
      if (s.name === "context_window") {
        // 优先抓带单位的长度（如 128k/200k/1M），避免把版本号/日期混入
        const withUnit = text.match(/\b\d+(?:\.\d+)?[kKmM]\b/g);
        const n = withUnit && withUnit.length ? withUnit : (text.match(/\b\d{4,}\b/g) || []);
        if (n) detail = n.slice(0, 4).join(", ");
      } else if (s.name === "knowledge_cutoff") {
        const d = text.match(/\b(19|20)\d{2}[-/.]?\d{0,2}[-/.]?\d{0,2}\b/g);
        if (d) detail = d.slice(0, 2).join(", ");
      }
      signals.push({ name: s.name, label: s.label, present: true, detail, quote: m[0].slice(0, 40) });
    } else {
      signals.push({ name: s.name, label: s.label, present: false, detail: null, quote: null });
    }
  }
  const models = [...new Set((text.match(MODEL_PATTERN) || []).map((x) => x.toLowerCase()))].slice(0, 10);
  return { signals, models };
}

export function capabilityDigest({ text, cachePath } = {}) {
  const sources = [];
  if (cachePath) {
    if (!existsSync(cachePath)) throw new Error(`缓存文件不存在: ${cachePath}`);
    let cache;
    try {
      cache = JSON.parse(readFileSync(cachePath, "utf8").replace(/^\uFEFF/, "")); // v1.0.3 修复: 剥离 UTF-8 BOM
    } catch {
      throw new Error(`缓存文件不是合法 JSON: ${cachePath}`);
    }
    const results = Array.isArray(cache.results) ? cache.results : cache.results ? [cache.results] : [];
    for (const r of results) {
      if (!r || !r.snippet) continue;
      const ext = extractFrom(String(r.snippet));
      sources.push({ url: r.url || null, httpStatus: r.httpStatus ?? null, ...ext });
    }
    if (!sources.length && text) sources.push({ url: null, httpStatus: null, ...extractFrom(text) });
  } else {
    if (!text || !text.trim()) throw new Error("输入为空：请提供文档文本或 --cache 路径");
    sources.push({ url: null, httpStatus: null, ...extractFrom(text) });
  }

  // 汇总：任一来源命中即 present
  const aggregated = [];
  for (const s of SIGNALS) {
    const any = sources.filter((src) => src.signals.some((sig) => sig.name === s.name && sig.present));
    aggregated.push({
      name: s.name,
      label: s.label,
      present: any.length > 0,
      hit_sources: any.length,
      detail: any.map((src) => src.signals.find((sig) => sig.name === s.name && sig.present)?.detail).find(Boolean) || null,
    });
  }
  const models = [...new Set(sources.flatMap((s) => s.models))];

  return {
    source_count: sources.length,
    sources: sources.map((s) => ({ url: s.url, httpStatus: s.httpStatus, models: s.models })),
    signals: aggregated,
    models,
    note: "信号基于文档关键词提取（确定性），不代表模型实时能力；关键结论请以目标模型官方文档为准。",
  };
}

// ================= CLI =================
if (isMain(import.meta)) {
  const args = process.argv.slice(2);
  if (args.includes("--help") || args.includes("-h")) {
    console.log("用法: node " + process.argv[1].split(/[\\/]/).pop() + " [--cache <fetch缓存json> | <文本文件> | stdin] [--json]");
    process.exit(0);
  }
  const opt = makeOpt(args);
  const wantJson = args.includes("--json");
  const cachePath = opt("cache");
  // v1.0.3 修复: 已知选项的值位置不参与"文件参数"判定，避免 --cache 取值被误判
  const knownOpts = new Set(["--cache"]);
  const valueIdx = new Set();
  for (let i = 0; i < args.length; i++) if (knownOpts.has(args[i])) valueIdx.add(i + 1);
  const fileArg = args.find((a, i) => !valueIdx.has(i) && !a.startsWith("--") && !a.startsWith("{") && !a.startsWith("["));
  let text;
  if (cachePath) {
    // 从缓存提取
  } else if (fileArg) {
    if (!existsSync(fileArg)) {
      console.error(`错误: 输入文件不存在: ${fileArg}`);
      process.exit(1);
    }
    text = readFileSync(fileArg, "utf8").replace(/^\uFEFF/, ""); // v1.0.3 修复: 剥离 UTF-8 BOM
  } else {
    text = readFileSync(0, "utf8").replace(/^\uFEFF/, "");
  }

  let r;
  try {
    r = capabilityDigest({ text, cachePath });
  } catch (e) {
    console.error(`错误: ${e.message}`);
    process.exit(1);
  }
  if (wantJson) {
    process.stdout.write(JSON.stringify(r, null, 2) + "\n");
  } else {
    console.log("=== 能力摘要 ===");
    console.log(`来源数: ${r.source_count}`);
    for (const s of r.sources) console.log(`  ${s.url || "(文本)"}${s.httpStatus != null ? ` HTTP ${s.httpStatus}` : ""} 提及模型: ${s.models.join(", ") || "无"}`);
    console.log("");
    for (const sig of r.signals) {
      const mark = sig.present ? "✅" : "—";
      console.log(`  ${mark} ${sig.label}${sig.detail ? `（${sig.detail}）` : ""}`);
    }
    if (r.models.length) console.log(`\n提及模型: ${r.models.join(", ")}`);
    console.log(`\n${r.note}`);
  }
}
