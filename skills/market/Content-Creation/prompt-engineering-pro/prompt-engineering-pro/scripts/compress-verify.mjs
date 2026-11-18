#!/usr/bin/env node
// compress-verify.mjs — 压缩回归引擎（把「压缩 ≥30% 应回归验证」从建议变成可执行闭环）
// 能力: 对比压缩前/后的评分（结构 4 维，或提供 --fp 时升 8 维）+ token 变化 + 保留/回退决策
// 模式:
//   compare: --original <file> --compressed <file>   （人工/他方压缩后回归验证）
//   auto:    <prompt.txt>                            （引擎按确定性安全规则生成压缩候选并回归）
// 设计原则:
//   1. 确定性: 同输入恒同输出；决策基于分数不降（decideKeep）
//   2. 只应用安全转换: 整行重复删除 + 无信息量套话删除；词级精简列为人工建议（引擎不自动改）
//   3. 证据引用: 应用/建议均附原文与行号
// 用法:
//   node scripts/compress-verify.mjs <prompt.txt> [--fp '{"model_family":"claude"}'] [--json]
//   node scripts/compress-verify.mjs --original a.txt --compressed b.txt [--json]
import { readFileSync, existsSync } from "node:fs";
import { isMain, makeOpt } from "./lib.mjs";
import { estimateTokens, compressSteps } from "./token-count.mjs";
import { scorePrompt } from "./score-prompt.mjs";
import { decideKeep } from "./run-evals.mjs";
import { scoreFull } from "./qscore-full.mjs";

// 安全转换 1：整行精确重复删除（保留首次出现）
function dedupeLines(text) {
  const lines = text.split(/\r?\n/);
  const seen = new Set();
  const kept = [];
  const applied = [];
  for (const ln of lines) {
    const t = ln.trim();
    if (t.length >= 6 && seen.has(t)) {
      applied.push({ action: "删除重复行", quote: t.slice(0, 40) });
      continue;
    }
    if (t.length >= 6) seen.add(t);
    kept.push(ln);
  }
  return { text: kept.join("\n"), applied };
}

// 安全转换 2：无信息量套话删除（quote 为完整正则命中，可直接替换）
function removeEmptyPhrases(text, steps) {
  let out = text;
  const applied = [];
  for (const s of steps) {
    if (s.priority !== 2) continue; // 仅套话（emptyPhrases）
    if (s.quote && out.includes(s.quote)) {
      out = out.split(s.quote).join("");
      applied.push({ action: "删除套话", quote: s.quote });
    }
  }
  return { text: out, applied };
}

// 自动生成压缩候选（确定性安全规则）
function buildCompressed(prompt) {
  const { steps } = compressSteps(prompt);
  const dedup = dedupeLines(prompt);
  const deempty = removeEmptyPhrases(dedup.text, steps);
  const applied = [...dedup.applied, ...deempty.applied];
  const manual = steps
    .filter((s) => s.priority >= 3)
    .map((s) => ({ action: s.action, rule: s.rule, quote: s.quote, line: s.line }));
  return { text: deempty.text, applied, manual };
}

function scoreOne(prompt, fp) {
  const st = scorePrompt(prompt);
  return { structural: st.structural_score, band: st.band };
}

export async function compressVerify({ prompt, original, compressed, fp } = {}) {
  let beforeText, afterText, mode, applied = [], manual = [];
  if (original && compressed) {
    mode = "compare";
    beforeText = original;
    afterText = compressed;
  } else {
    mode = "auto";
    beforeText = prompt;
    const cand = buildCompressed(prompt);
    afterText = cand.text;
    applied = cand.applied;
    manual = cand.manual;
  }
  if (!beforeText || !beforeText.trim()) {
    return { mode, decision: "revert", summary: "输入为空：无法压缩验证。", token: null, score: null, applied: [], manual_suggestions: [] };
  }

  const modelFamily = fp && fp.model_family ? fp.model_family : undefined;
  const estBefore = estimateTokens(beforeText, modelFamily);
  const estAfter = estimateTokens(afterText, modelFamily);
  const reductionPct = estBefore.tokens > 0 ? Math.round(((estBefore.tokens - estAfter.tokens) / estBefore.tokens) * 1000) / 10 : 0;

  let scoreBefore, scoreAfter;
  if (fp) {
    const sb = await scoreFull(beforeText, fp);
    const sa = await scoreFull(afterText, fp);
    scoreBefore = { total: sb.total, band: sb.band, engine: "qscore" };
    scoreAfter = { total: sa.total, band: sa.band, engine: "qscore" };
  } else {
    scoreBefore = { ...scoreOne(beforeText, fp), engine: "structural" };
    scoreAfter = { ...scoreOne(afterText, fp), engine: "structural" };
  }
  const base = scoreBefore.total != null ? scoreBefore.total : scoreBefore.structural;
  const curr = scoreAfter.total != null ? scoreAfter.total : scoreAfter.structural;
  const decisionObj = decideKeep({ baseline: base, current: curr, minImprovement: 0 });
  const decision = decisionObj.decision;

  const summary = mode === "auto"
    ? (afterText === beforeText
      ? "未发现可安全自动压缩的项（无重复行/套话）；如需进一步压缩请人工精简并再次回归。"
      : `自动压缩减少 ${reductionPct}% token（${estBefore.tokens} → ${estAfter.tokens}）；分数 ${base} → ${curr}，决策：${decision}。`)
    : `压缩后 token ${estBefore.tokens} → ${estAfter.tokens}（-${reductionPct}%）；分数 ${base} → ${curr}，决策：${decision}。`;

  return {
    mode,
    token: { before_tokens: estBefore.tokens, after_tokens: estAfter.tokens, reduction_pct: reductionPct },
    score: { engine: scoreBefore.engine, before: base, after: curr, delta: Math.round((curr - base) * 10) / 10 },
    decision: decisionObj,
    applied,
    manual_suggestions: manual,
    summary,
  };
}

// ================= CLI =================
if (isMain(import.meta)) {
  const args = process.argv.slice(2);
  if (args.includes("--help") || args.includes("-h")) {
    console.log("用法: node " + process.argv[1].split(/[\\/]/).pop() + " [--original <f> --compressed <f> | <prompt.txt>] [--fp <json>] [--json]");
    process.exit(0);
  }
  const opt = makeOpt(args);
  const wantJson = args.includes("--json");
  const fpRaw = opt("fp");
  let fp;
  if (fpRaw !== undefined) {
    try {
      fp = JSON.parse(fpRaw);
    } catch {
      // v1.0.3 修复: 畸形 --fp 不静默忽略，向 stderr 警告
      console.error(`警告: --fp 不是合法 JSON，已忽略（${String(fpRaw).slice(0, 40)}…）`);
      fp = null;
    }
  }
  const originalFile = opt("original");
  const compressedFile = opt("compressed");
  // v1.0.3 修复: 已知选项的值位置不参与"文件参数"判定
  const knownOpts = new Set(["--original", "--compressed", "--fp"]);
  const valueIdx = new Set();
  for (let i = 0; i < args.length; i++) if (knownOpts.has(args[i])) valueIdx.add(i + 1);
  const fileArg = args.find((a, i) => !valueIdx.has(i) && !a.startsWith("--") && !a.startsWith("{") && !a.startsWith("[") && !/^-?\d+$/.test(a));
  const read = (f) => {
    if (!existsSync(f)) { console.error(`错误: 输入文件不存在: ${f}`); process.exit(1); }
    return readFileSync(f, "utf8");
  };

  const inputs = {};
  if (originalFile && compressedFile) {
    inputs.original = read(originalFile);
    inputs.compressed = read(compressedFile);
  } else if (fileArg) {
    inputs.prompt = read(fileArg);
  } else {
    inputs.prompt = readFileSync(0, "utf8");
  }
  // v1.0.3 修复: 空输入应非零退出（与其余引擎的"优雅报错"约定一致）
  if (!String(inputs.prompt || "").trim()) {
    console.error("错误: 输入为空：请先提供待压缩/对比的提示词。");
    process.exit(1);
  }

  compressVerify({ ...inputs, fp }).then((r) => {
    if (wantJson) {
      process.stdout.write(JSON.stringify(r, null, 2) + "\n");
    } else {
      console.log("=== 压缩回归报告 ===");
      console.log(`模式: ${r.mode === "auto" ? "自动生成压缩候选" : "人工压缩对比"}`);
      if (r.token) console.log(`token: ${r.token.before_tokens} → ${r.token.after_tokens}（-${r.token.reduction_pct}%）`);
      if (r.score) console.log(`评分(${r.score.engine}): ${r.score.before} → ${r.score.after}（Δ${r.score.delta}）`);
      console.log(`决策: ${r.decision.decision}`);
      for (const a of r.applied) console.log(`  应用: ${a.action} "${a.quote}"`);
      for (const m of r.manual_suggestions) console.log(`  人工建议: ${m.action}（${m.rule}）`);
      console.log(r.summary);
    }
  });
}
