#!/usr/bin/env node
// golden-learner.mjs — 好稿学习引擎（自进化闭环：历史好稿 → 学习建议）
// 能力: 从 data/golden 与 data/versions 统计高分提示词的结构模式（角色/目标/格式/边界/防幻觉/兜底/示例/步骤），
//       产出带置信度的学习建议，写入 data/memory/golden-suggestions.json 供后续构建参考。
// 设计原则:
//   1. 确定性: 纯规则 + 覆盖率统计，同输入恒同结果
//   2. 只建议不改评分: 学习建议仅作组装参考，不进评分（防偏好固化）
//   3. 证据引用: 每条建议附 支持数 / 覆盖率 / 置信度
// 用法:
//   node scripts/golden-learner.mjs              # 分析默认 data/ 目录
//   node scripts/golden-learner.mjs --dir <dir>   # 注入数据目录（测试/隔离用）
//   node scripts/golden-learner.mjs --json
import { readFileSync, writeFileSync, existsSync, readdirSync } from "node:fs";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";
import { ensureDir, ts, safeDir, isMain, makeOpt } from "./lib.mjs";

const ROOT = join(dirname(fileURLToPath(import.meta.url)), "..");
const DEFAULT_DATA_DIR = join(ROOT, "data");

// 高分阈值：qscore ≥ 80 视为"好稿"（与 Q-Score 优秀档一致）
const GOOD_SCORE = 80;
// 覆盖率阈值：好稿中 ≥50% 含该模式才作为建议输出
const MIN_COVERAGE = 0.5;

// 结构模式库（与 build 组装要素对齐）
const STRUCTURE_PATTERNS = [
  { key: "role", label: "角色定位", re: /你(是|作为|扮演)|作为(一?个)/ },
  { key: "goal", label: "目标与完成标准", re: /完成标准|验收|成功标准|目标|需(要)?(满足|做到)/ },
  { key: "format", label: "输出格式", re: /输出格式|输出.{0,12}(json|markdown|md|表格|列表)|返回.{0,8}格式|以.{0,6}(json|markdown)/i },
  { key: "boundary", label: "边界/禁止项", re: /不要|不得|禁止|避免|只能|限制|不允许/ },
  { key: "hallucination", label: "防幻觉锚点", re: /不要?编造|引用来源|注明来源|不确定就|基于事实|据实回答/ },
  { key: "fallback", label: "兜底指令", re: /无法.{0,12}(则|就|请)|默认|否则|fallback/i },
  { key: "examples", label: "示例/few-shot", re: /例如|比如|示例|例子/ },
  { key: "steps", label: "步骤/流程", re: /步骤|第一步|流程|分.{0,4}(步|阶段)/ },
];

// fail-safe 读取 JSON 数组/对象（损坏文件跳过；目录损坏/被文件占用时降级为空）
function readRecords(dir) {
  if (!existsSync(dir)) return [];
  let entries;
  try {
    entries = readdirSync(dir);
  } catch {
    // v1.0.3 修复: 路径存在但非目录（如被文件占用）时 readdir 抛错 → 降级为空，不崩溃
    return [];
  }
  return entries
    .filter((f) => f.endsWith(".json") && !f.startsWith("."))
    .slice(0, 300) // 上限防极端超大目录
    .map((f) => {
      try {
        // v1.0.3 修复: 剥离 UTF-8 BOM（Windows 编辑器常见），避免带 BOM 的 JSON 被静默跳过
        return JSON.parse(readFileSync(join(dir, f), "utf8").replace(/^\uFEFF/, ""));
      } catch {
        return null;
      }
    })
    .filter((v) => v !== null);
}

function containsPattern(text, re) {
  if (!text) return false;
  const r = new RegExp(re.source, re.flags.includes("g") ? re.flags : re.flags + "g");
  r.lastIndex = 0;
  return r.test(text);
}

export function goldenLearn({ dir = DEFAULT_DATA_DIR } = {}) {
  dir = safeDir(dir, DEFAULT_DATA_DIR);
  const result = { analyzed: { versions: 0, golden: 0, good: 0, low: 0 }, suggestions: [], summary: "" };

  const versionRecords = readRecords(join(dir, "versions"));
  const goldenRecords = readRecords(join(dir, "golden"));
  result.analyzed.versions = versionRecords.length;
  result.analyzed.golden = goldenRecords.length;

  // 好稿池：golden（按定义即精选好稿）+ qscore ≥ GOOD_SCORE 的版本
  const goodPool = [];
  for (const g of goldenRecords) {
    const p = g.prompt || g.prompt_text;
    if (p) goodPool.push({ text: p, source: "golden" });
  }
  for (const v of versionRecords) {
    const s = typeof v.qscore === "number" ? v.qscore : null;
    if (s != null && s >= GOOD_SCORE && v.prompt) goodPool.push({ text: v.prompt, source: "version" });
    if (s != null && s < 60 && v.prompt) result.analyzed.low++;
  }
  result.analyzed.good = goodPool.length;

  if (goodPool.length < 2) {
    result.summary = `样本不足（好稿 ${goodPool.length} 个，需 ≥2 个高分稿）：请先积累 data/versions 或 data/golden 再学习。`;
    return result;
  }

  // 计算各模式在好稿中的覆盖率
  const rows = [];
  for (const p of STRUCTURE_PATTERNS) {
    const support = goodPool.filter((g) => containsPattern(g.text, p.re)).length;
    const coverage = support / goodPool.length;
    rows.push({ key: p.key, label: p.label, support, coverage });
  }
  rows.sort((a, b) => (b.coverage - a.coverage) || (b.support - a.support) || (a.label < b.label ? -1 : 1));

  const suggestions = rows
    .filter((r) => r.coverage >= MIN_COVERAGE)
    .map((r) => ({
      pattern: r.key,
      label: r.label,
      coverage_pct: Math.round(r.coverage * 100),
      support: r.support,
      confidence: r.coverage >= 0.8 ? "高" : r.coverage >= 0.6 ? "中" : "低",
      note: `高分稿中 ${r.support}/${goodPool.length} 含「${r.label}」；新构建可优先补齐该要素`,
    }));
  result.suggestions = suggestions;

  result.summary = `基于 ${goodPool.length} 个高分稿产出 ${suggestions.length} 条学习建议（覆盖率阈值 ${Math.round(MIN_COVERAGE * 100)}%）。`;

  // 持久化供 pipe/后续构建参考（只写不改评分）
  if (suggestions.length) {
    const memoryDir = join(dir, "memory");
    ensureDir(memoryDir);
    const out = { ts: ts(), good_analyzed: goodPool.length, suggestions };
    writeFileSync(join(memoryDir, "golden-suggestions.json"), JSON.stringify(out, null, 2) + "\n", "utf8");
  }

  return result;
}

// ================= CLI =================
if (isMain(import.meta)) {
  const args = process.argv.slice(2);
  if (args.includes("--help") || args.includes("-h")) {
    console.log("用法: node " + process.argv[1].split(/[\\/]/).pop() + " [--dir <data目录>] [--json]");
    process.exit(0);
  }
  const opt = makeOpt(args);
  const wantJson = args.includes("--json");
  const dir = safeDir(opt("dir"), DEFAULT_DATA_DIR);

  const r = goldenLearn({ dir });
  if (wantJson) {
    process.stdout.write(JSON.stringify(r, null, 2) + "\n");
  } else {
    console.log("=== 好稿学习报告 ===");
    console.log(`样本: versions ${r.analyzed.versions} / golden ${r.analyzed.golden} / 好稿 ${r.analyzed.good} / 低分 ${r.analyzed.low}`);
    console.log(r.summary);
    for (const s of r.suggestions) {
      console.log(`\n[${s.label}] 置信度:${s.confidence} 覆盖 ${s.coverage_pct}%（${s.support} 个高分稿）`);
      console.log(`  ${s.note}`);
    }
    if (!r.suggestions.length) console.log("\n（暂无达到阈值的学习建议）");
  }
}
