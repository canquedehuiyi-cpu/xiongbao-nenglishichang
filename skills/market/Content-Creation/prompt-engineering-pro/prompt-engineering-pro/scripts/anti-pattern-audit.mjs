#!/usr/bin/env node
// anti-pattern-audit.mjs — 反模式审计引擎（v1.1.0）
// 功能: 扫描 prompt 命中 Don't 清单（对齐 references/anti-patterns.md），输出命中点 + Do Instead 替代写法。
// 确定性: 纯规则匹配，同一输入恒得同一输出；每条命中带原文引用 + 行号 + 替代写法。
// 用法:
//   node scripts/anti-pattern-audit.mjs <prompt.txt>       # 人类可读报告
//   node scripts/anti-pattern-audit.mjs <prompt.txt> --json # 机器可读
import { readFileSync } from "node:fs";
import { isMain } from "./lib.mjs";

// ================= Don't 清单（反模式） =================

const PATTERNS = [
  {
    id: "VAGUE_VERB",
    label: "模糊指令（无具体动作）",
    re: /(帮我|弄|搞|看看|试试|处理一下|随便|大概|差不多)/,
    fix: "用具体祈使动词 + 明确对象（如「把 X 按 3 字段抽取为 JSON」）",
  },
  {
    id: "NO_FORMAT",
    label: "无输出格式",
    re: /^(?!.*(格式|输出为|JSON|Markdown|表格|分点|按以下|以.{0,10}(形式|格式)))/m,
    fix: "声明输出结构/格式/长度，让输出可稳定解析",
  },
  {
    id: "CONTRADICT",
    label: "矛盾指令",
    re: /(简短|简洁).{0,40}(详细|详尽|完整)|(详细|详尽).{0,40}(简短|简洁)|(不要举例|不用举例).{0,40}(例如|比如)|(不要格式).{0,40}(JSON|表格)/,
    fix: "消除冲突：明确优先级（如「正文简洁，关键点可展开」）",
  },
  {
    id: "TOO_LONG",
    label: "指令过长",
    re: null,
    checkLen: 800,
    fix: "拆分：一条指令一个目标，超长走任务链（prompt-chaining）",
  },
  {
    id: "NO_VERIFICATION",
    label: "无验收标准",
    re: /^(?!.*(验收|成功标准|如何判断|做对了|自检|符合.{0,6}要求|通过标准))/m,
    fix: "写明「怎么算做对了」（验收条件 + 可执行检查）",
  },
  {
    id: "MULTI_TASK",
    label: "多任务混杂（无优先级）",
    re: /(并且|同时|还要|顺便).{0,30}(写|生成|分析|总结|翻译|计算|设计)/,
    fix: "拆成独立子任务或声明优先级（先 X 再 Y）",
  },
  {
    id: "NO_BOUNDARY",
    label: "无边界约束",
    re: /^(?!.*(不要|不能|不许|禁止|不得|仅限|边界|限制|范围))/m,
    fix: "显式声明 Non-goals / Constraints，堵住越界发挥",
  },
  {
    id: "NO_FALLBACK",
    label: "无兜底指令",
    re: /^(?!.*(如果|若|无法|缺失|为空|默认|否则|遇到.{0,6}时))/m,
    fix: "写明缺信息/出错时怎么办（明确说「缺」而非编造）",
  },
  {
    id: "ABSOLUTE",
    label: "绝对化要求（无例外）",
    re: /(永远|绝对|必须全部|绝不|100%|百分之百|无例外)/,
    fix: "给例外空间（如「除非材料缺失，否则必须引用」）",
  },
  {
    id: "AMBIGUOUS_PRONOUN",
    label: "指代不明",
    re: /\b(它|这个|那个|这些|那些|它们)\b/,
    fix: "用具体名词替代代词，消除歧义",
  },
];

// ================= 主函数 =================

export function antiPatternAudit(text) {
  if (!text || !text.trim()) {
    throw new Error("输入为空：请提供提示词文本（文件参数或 stdin）");
  }
  const hits = [];
  for (const p of PATTERNS) {
    if (p.checkLen && text.length > p.checkLen) {
      hits.push({ id: p.id, label: p.label, line: 1, quote: text.slice(0, 60) + `…（全文 ${text.length} 字）`, fix: p.fix });
      continue;
    }
    if (p.re === null) continue;
    const re = new RegExp(p.re.source, p.re.flags.includes("g") ? p.re.flags : p.re.flags + "g");
    let m;
    while ((m = re.exec(text)) !== null) {
      const idx = m.index;
      const line = text.slice(0, idx).split("\n").length;
      const quote = (m[0] || text.slice(idx, idx + 30)).trim().slice(0, 50);
      hits.push({ id: p.id, label: p.label, line, quote, fix: p.fix });
      if (re.lastIndex === idx) re.lastIndex++;
      if (hits.filter((h) => h.id === p.id).length >= 3) break;
    }
  }
  // 合并同类（保留首条 + 计数）
  const seen = new Map();
  for (const h of hits) {
    if (!seen.has(h.id)) seen.set(h.id, { ...h, count: 1 });
    else seen.get(h.id).count++;
  }
  const merged = Array.from(seen.values());
  return {
    meta: { engine: "anti-pattern-audit.mjs v1.1.0", mode: "anti-pattern-audit", patterns: PATTERNS.length },
    hits: merged,
    fixes: merged.map((h) => `[${h.label}] ${h.fix}`),
    verdict: merged.length === 0 ? "未命中反模式清单" : merged.length <= 2 ? "轻度：建议按替代写法修订" : merged.length <= 5 ? "中度：建议系统修订" : "重度：建议重构",
  };
}

// ================= CLI =================

if (isMain(import.meta)) {
  const args = process.argv.slice(2);
  if (args.includes("--help") || args.includes("-h")) {
    console.log("用法: node scripts/anti-pattern-audit.mjs <prompt.txt> [--json]");
    process.exit(0);
  }
  const wantJson = args.includes("--json");
  const fileArg = args.find((a) => !a.startsWith("--") && !a.startsWith("{") && !a.startsWith("[") && !/^-?\d+$/.test(a));
  let input;
  if (fileArg) {
    input = readFileSync(fileArg, "utf8").replace(/^\uFEFF/, "");
  } else {
    input = readFileSync(0, "utf8").replace(/^\uFEFF/, "");
  }
  let result;
  try {
    result = antiPatternAudit(input);
  } catch (e) {
    console.error(`✗ ${e.message}`);
    process.exit(1);
  }
  if (wantJson) {
    process.stdout.write(JSON.stringify(result, null, 2) + "\n");
  } else {
    console.log("=== 反模式审计 ===");
    if (!result.hits.length) {
      console.log("✓ 未命中反模式清单");
    } else {
      for (const h of result.hits) {
        console.log(`✗ [${h.label}]（第${h.line}行）`);
        console.log(`    命中: "${h.quote}"${h.count > 1 ? `（×${h.count}）` : ""}`);
        console.log(`    替代: ${h.fix}`);
      }
      console.log(`\n判定: ${result.verdict}`);
    }
  }
}
