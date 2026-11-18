#!/usr/bin/env node
// prompt-file-manager.mjs — 提示词资产化引擎（v1.1.0）
// 功能:
//   1. 生成 prompts/<name>.md 文件骨架（契约头模板: purpose / model / token estimate / 变量占位），
//      对齐 AgentX "文件化管理"主张——提示词作为可维护工件而非内联字符串。
//   2. 校验"禁止内联多行提示词"规则: 扫描文本中是否把完整提示词内联在单行/代码块内，建议抽成文件。
// 安全:
//   - 仅在本 skill 工作区（ROOT/prompts）内创建文件，safePath 前缀校验防目录穿越。
//   - 默认 dry-run 不落盘；--write 才真正写入。
// 用法:
//   node scripts/prompt-file-manager.mjs --name my-prompt --purpose "一句话目的" [--model claude] [--write]
//   echo "内联提示词文本" | node scripts/prompt-file-manager.mjs --check  # 内联规则检查
import { readFileSync, writeFileSync, mkdirSync } from "node:fs";
import { join, resolve, dirname } from "node:path";
import { ROOT, safeId, isMain, makeOpt, ts } from "./lib.mjs";

// ================= 内联规则检查 =================

export function inlinePromptCheck(text) {
  if (!text || !text.trim()) return { meta: { engine: "prompt-file-manager.mjs v1.1.0" }, ok: true, hits: [], suggestion: "" };
  const lines = text.split("\n");
  const hits = [];
  // 规则1: 超长单行（>300 字符）且含提示词特征（祈使/指令）
  lines.forEach((l, i) => {
    if (l.length > 300 && /(请|写|生成|输出|不要|格式|step|make|write|generate|output)/i.test(l)) {
      hits.push({ rule: "超长内联行", line: i + 1, len: l.length, quote: l.slice(0, 60) + "…" });
    }
  });
  // 规则2: 代码块内嵌完整提示词（连续 ≥5 行且有明确指令语义）
  const codeBlockRe = /```[\s\S]*?```/g;
  let m;
  while ((m = codeBlockRe.exec(text)) !== null) {
    const inner = m[0];
    const innerLines = inner.split("\n").length - 2;
    if (innerLines >= 5 && /(你是一个|请|步骤|输出|任务|指令)/i.test(inner)) {
      hits.push({ rule: "代码块内嵌完整提示词", line: text.slice(0, m.index).split("\n").length, len: inner.length, quote: inner.slice(0, 60) + "…" });
    }
  }
  return {
    meta: { engine: "prompt-file-manager.mjs v1.1.0", mode: "inline-rule-check" },
    ok: hits.length === 0,
    hits,
    suggestion: hits.length ? "建议把内联提示词抽成 prompts/<name>.md 工件（契约头 + 正文），便于版本管理与复用" : "未发现内联多行提示词",
  };
}

// ================= 文件骨架生成 =================

export function buildPromptFile({ name, purpose, model = "未指定", content = "" }) {
  const slug = safeId(name || "prompt");
  const estimate = estimateTokens(content);
  const header = [
    "---",
    `name: ${slug}`,
    `purpose: ${purpose || "（待补充：一句话说明该提示词要达成什么）"}`,
    `model: ${model}`,
    `token_estimate: ${estimate}`,
    `created: ${ts().slice(0, 10)}`,
    "variables:",
    "  # 声明变量占位符，构建时替换；禁止硬编码用户数据",
    "---",
    "",
    "# 提示词工件",
    "",
    "## 目标（Objective）",
    "",
    "## 背景（Context）",
    "",
    "## 任务（Task）",
    "",
    "## 约束（Constraints）",
    "",
    "## 非目标（Non-goals）",
    "",
    "## 输出格式（Output format）",
    "",
    "## 示例（Examples）",
    "",
    "## 分步（Process）",
    "",
    "## 验收（Verification）",
    "",
    "## 兜底（Failure handling）",
    "",
    "## 语气（Style）",
    "",
  ].join("\n");
  const body = content ? `\n${content}\n` : "";
  return {
    meta: { engine: "prompt-file-manager.mjs v1.1.0", mode: "asset-generate" },
    file: `prompts/${slug}.md`,
    slug,
    token_estimate: estimate,
    draft: header + body,
    inline_check: inlinePromptCheck(content || header),
  };
}

// token 估算（与 validate 同口径：中文 1 字≈1 token，英文 1 词≈1.3 token）
function estimateTokens(text) {
  const cjk = (text.match(/[\u4e00-\u9fff\u3000-\u303f\uff00-\uffef]/g) || []).length;
  const words = text.split(/\s+/).filter(Boolean).filter((t) => !/[\u4e00-\u9fff\u3000-\u303f\uff00-\uffef]/.test(t)).length;
  return Math.round(cjk * 1.0 + words * 1.3);
}

// 安全落盘：仅限 ROOT/prompts 内（safePath 前缀校验防目录穿越）
export function writePromptFile(draft, relFile) {
  const target = resolve(join(ROOT, relFile));
  const rootDir = resolve(join(ROOT, "prompts"));
  if (!target.startsWith(rootDir + sep())) {
    throw new Error(`路径越界拒绝：${relFile}（仅允许写入 ${"prompts/"} 下）`);
  }
  mkdirSync(dirname(target), { recursive: true });
  writeFileSync(target, draft, "utf8");
  return target;
}

function sep() {
  // Windows 与 POSIX 分隔符统一校验（resolve 后按平台分隔符）
  return process.platform === "win32" ? "\\" : "/";
}

// ================= CLI =================

if (isMain(import.meta)) {
  const args = process.argv.slice(2);
  if (args.includes("--help") || args.includes("-h")) {
    console.log("用法: node scripts/prompt-file-manager.mjs --name <slug> --purpose <目的> [--model <族>] [--write] | --check");
    process.exit(0);
  }
  const opt = makeOpt(args);
  const wantJson = args.includes("--json");
  const doWrite = args.includes("--write");
  const doCheck = args.includes("--check");

  if (doCheck) {
    const input = readFileSync(0, "utf8").replace(/^\uFEFF/, "");
    const r = inlinePromptCheck(input);
    if (wantJson) process.stdout.write(JSON.stringify(r, null, 2) + "\n");
    else {
      if (r.ok) console.log("✓ 未发现内联多行提示词");
      else {
        console.log(`✗ 发现 ${r.hits.length} 处内联问题`);
        for (const h of r.hits) console.log(`  - [${h.rule}] 第${h.line}行 ${h.quote}`);
        console.log(r.suggestion);
      }
    }
    process.exit(r.ok ? 0 : 1);
  }

  const name = opt("name") || "";
  const purpose = opt("purpose") || "";
  const model = opt("model") || "未指定";
  if (!name) {
    console.error("错误：--name 必填（文件 slug，小写字母/数字/连字符）");
    process.exit(1);
  }
  const result = buildPromptFile({ name, purpose, model });
  if (wantJson) {
    process.stdout.write(JSON.stringify({ ...result, draft: result.draft }, null, 2) + "\n");
  } else {
    console.log(`文件: ${result.file}（token 预估 ${result.token_estimate}）`);
    console.log("--- 骨架草稿 ---");
    console.log(result.draft);
    if (doWrite) {
      const target = writePromptFile(result.draft, result.file);
      console.log(`\n已写入: ${target}`);
    } else {
      console.log("\n（dry-run：未落盘；加 --write 写入 prompts/ 目录）");
    }
  }
}
