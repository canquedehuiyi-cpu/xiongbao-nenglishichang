#!/usr/bin/env node
// diagnose.mjs — 诊断引擎（L1「diagnose」意图可执行落地）
// 能力: 输入「提示词 + 可选失败现象」→ 按失败分类定位根因 → 输出定向修补建议 + 受影响评分维度 + 推荐模板
// 设计原则:
//   1. 确定性: 纯规则 + 信号正则 + 安全扫描，同输入恒同结果
//   2. 证据引用: 每条诊断附 命中信号原文 + 行号 + 分类 + 严重度
//   3. 与 references/failure-taxonomy.md 与 Q-Score 维度对齐（dims 字段）
// 用法:
//   node scripts/diagnose.mjs <prompt.txt>
//   node scripts/diagnose.mjs <prompt.txt> --failure "回答总是编造"
//   node scripts/diagnose.mjs <prompt.txt> --fp '{"model_family":"claude","context_budget":8000}'
//   echo "..." | node scripts/diagnose.mjs
import { readFileSync, existsSync } from "node:fs";
import { isMain, makeOpt } from "./lib.mjs";
import { estimateTokens, detectRedundancy } from "./token-count.mjs";
import { scanSafety } from "./scan-safety.mjs";

// ================= 失败分类库（与 references/failure-taxonomy.md 对齐） =================
// 每类: whenPresent=命中即问题；whenAbsent=缺失即问题（两者至少其一）
const CATEGORIES = [
  {
    id: "unsafe",
    name: "安全风险（红线/注入/PII）",
    severity: "major",
    dims: ["safety"],
    template: null,
    diagnosis: "内容命中安全红线/注入特征/PII：安全优先，先处理安全再谈构建。",
    fixes: ["红线/注入 → 拒绝或隔离标注，不执行", "PII → 脱敏后再输出并提示用户"],
  },
  {
    id: "vague_goal",
    name: "目标含糊",
    severity: "major",
    dims: ["boundary", "task"],
    template: "COSTAR",
    diagnosis: "目标与完成标准不明确，模型只能猜测意图。",
    fixes: ["写明任务目标（做什么 / 给谁 / 用于哪个场景）", "写明完成标准（怎么算成功、验收点）", "写明范围（哪些不做）"],
    whenPresent: [/随便|大概|差不多|之类的|等等|弄(一?下)|搞(一?下)|处理(一?下)|优化(一?下)/],
  },
  {
    id: "generic",
    name: "空泛套话",
    severity: "minor",
    dims: ["economy", "task"],
    template: "COSTAR",
    diagnosis: "含无信息量套话，占用 token 且不增加约束。",
    fixes: ["删除套话（充分发挥/最大化/深入挖掘/赋能…）", "换成可测量的具体要求"],
    whenPresent: [/充分发挥|最大化|深入挖掘|赋能|顶尖|一流|无与伦比|全方位/],
  },
  {
    id: "missing_role",
    name: "缺角色定位",
    severity: "minor",
    dims: ["role"],
    template: "RISEN",
    diagnosis: "未给出角色/身份定位，专业性与视角不明确。",
    fixes: ["补充角色（你是一位…）", "说明立场与限制（如只基于公开资料）"],
    whenAbsent: [/你(是|作为|扮演)|作为(一?个)?|role\s*:/i],
  },
  {
    id: "missing_boundary",
    name: "缺边界/约束",
    severity: "minor",
    dims: ["boundary"],
    template: "COSTAR",
    diagnosis: "未声明禁止项或约束边界，模型可能越界发挥。",
    fixes: ["写明禁止项（不要…/不得…）", "写明范围与限制（只能在…内）"],
    whenAbsent: [/不要|不得|禁止|避免|只能|限制|范围(内|外)|不允许|切勿/],
  },
  {
    id: "missing_format",
    name: "缺输出格式",
    severity: "minor",
    dims: ["format"],
    template: "SCHEMA",
    diagnosis: "未指定输出格式/结构，结果排版不可预期。",
    fixes: ["指定输出格式（JSON / Markdown / 表格 / 代码）", "给出结构占位或字段清单"],
    whenAbsent: [/输出格式|输出.{0,12}(json|markdown|md|表格|列表|代码)|返回.{0,8}格式|格式\s*[：:]|以.{0,6}(json|markdown).{0,6}(输出|返回)/i],
  },
  {
    id: "no_hallucination",
    name: "防幻觉锚点缺失",
    severity: "minor",
    dims: ["verifiability"],
    template: "RAG",
    diagnosis: "未约束事实来源，模型可能在信息不足时编造。",
    fixes: ["要求引用来源/注明出处", "未知或不确定时明确说明（不编造）", "增加基于事实/无依据不回答的约束"],
    whenAbsent: [/不要?编造|不可?编造|引用来源|注明来源|如不?(确定|知道)|不确定就|基于事实|无依据不|据实回答|查证/],
  },
  {
    id: "no_fallback",
    name: "缺兜底指令",
    severity: "minor",
    dims: ["boundary", "verifiability"],
    template: "RISEN",
    diagnosis: "未给出无法完成/信息不足时的兜底行为。",
    fixes: ["写明兜底（无法…则…/默认…）", "允许请求澄清而非硬猜"],
    whenAbsent: [/无法.{0,12}(则|就|请)|如果.{0,12}(无法|不能|没有).{0,12}(则|就|请|默认|告诉)|默认|否则|fallback/i],
  },
  {
    id: "no_examples",
    name: "缺示例/上下文",
    severity: "minor",
    dims: ["task"],
    template: "FEWSHOT",
    diagnosis: "复杂/转换类任务未给示例或背景上下文。",
    fixes: ["补 1-2 个示例（few-shot）", "补充背景/输入样例，减少歧义"],
    whenAbsent: [/例如|比如|示例|例子|参照|参考示例|few.?shot/i],
  },
  {
    id: "verbosity",
    name: "冗长/冗余",
    severity: "minor",
    dims: ["economy"],
    template: null,
    diagnosis: "检测到高置信冗余（重复约束/套话/同义堆叠/过度修饰）。",
    fixes: ["按 compressSteps 删除冗余", "压缩 ≥30% 后用 compress-verify.mjs 回归"],
  },
  {
    id: "over_budget",
    name: "超长未预算",
    severity: "major",
    dims: ["economy"],
    template: null,
    diagnosis: "估算 token 明显超出预算/默认阈值，长提示词会稀释关键指令。",
    fixes: ["压缩至预算内", "拆分任务或精简背景"],
  },
];

// 失败现象 → 分类 映射（补充提示词本身之外的观察）
const FAILURE_MAP = [
  { kw: /编造|幻觉|胡编|胡说|不真实|瞎说/, id: "no_hallucination" },
  { kw: /太?长|啰嗦|冗长|重复|车轱辘/, id: "verbosity" },
  { kw: /格式|排版|乱|不整齐/, id: "missing_format" },
  { kw: /跑题|偏题|不相关|答非所问/, id: "vague_goal" },
  { kw: /没?按(照)?(指令|要求)|不听话|没执行|不遵守/, id: "missing_boundary" },
  { kw: /回答不了|不知道|没上下文|缺背景|信息不够/, id: "no_examples" },
  { kw: /不专业|空泛|套话|太?虚|泛泛/, id: "generic" },
  { kw: /不(懂|理解)|误解|理解错/, id: "vague_goal" },
  { kw: /没?给(格式|结构)|结构乱/, id: "missing_format" },
  { kw: /没?兜底|无法时|卡住|不处理异常/, id: "no_fallback" },
];

// 匹配信号：返回第一条命中的 {quote, line}
function matchFirst(text, reArr) {
  for (const re of reArr) {
    const r = new RegExp(re.source, re.flags.includes("g") ? re.flags : re.flags + "g");
    r.lastIndex = 0;
    const m = r.exec(text);
    if (m) {
      const lineNo = text.slice(0, m.index).split("\n").length;
      return { quote: m[0].slice(0, 40), line: lineNo };
    }
  }
  return null;
}

// 任一信号命中（用于 whenAbsent：命中任一即视为"具备"）
function anyMatch(text, reArr) {
  return matchFirst(text, reArr) !== null;
}

export function diagnosePrompt(prompt, { failure, fp } = {}) {
  const result = { findings: [], recommended_templates: [], summary: "" };
  if (!prompt || !prompt.trim()) {
    result.summary = "输入为空：请先提供待诊断的提示词。";
    return result;
  }

  const extraIds = new Set();
  if (failure) {
    for (const { kw, id } of FAILURE_MAP) {
      if (kw.test(failure)) extraIds.add(id);
    }
  }

  // 1. 安全扫描（最高优先级）
  const safe = scanSafety(prompt);
  const safeFinding = CATEGORIES.find((c) => c.id === "unsafe");
  if (safe.level !== "clean") {
    result.findings.push({
      ...safeFinding,
      evidence: safe.hits.map((h) => ({ quote: h.quote, line: h.line, rule: h.rule })),
      diagnosis: safeFinding.diagnosis + (safe.reason ? `（${safe.reason}）` : ""),
    });
  } else if (extraIds.has("unsafe")) {
    result.findings.push({ ...safeFinding, evidence: [{ quote: "[失败现象]", line: 0 }] });
  }

  // 2. 结构信号分类
  for (const cat of CATEGORIES) {
    if (cat.id === "unsafe") continue;
    let hit = null;
    if (cat.whenPresent && cat.whenAbsent) {
      const ev = matchFirst(prompt, cat.whenPresent);
      if (ev) hit = { evidence: [ev] };
      else if (!anyMatch(prompt, cat.whenAbsent)) hit = { evidence: [{ quote: "[缺失该项]", line: 0 }] };
    } else if (cat.whenPresent) {
      const ev = matchFirst(prompt, cat.whenPresent);
      if (ev) hit = { evidence: [ev] };
    } else if (cat.whenAbsent) {
      if (!anyMatch(prompt, cat.whenAbsent)) hit = { evidence: [{ quote: "[缺失该项]", line: 0 }] };
    }
    if (hit) {
      const extra = extraIds.has(cat.id);
      if (extra && !hit.evidence.some((e) => e.quote === "[缺失该项]")) {
        hit.evidence = [...hit.evidence, { quote: "[失败现象]", line: 0 }];
      }
      result.findings.push({ ...cat, evidence: hit.evidence });
    }
  }

  // 3. 冗余检测（复用 token-count 确定性规则）
  const red = detectRedundancy(prompt);
  if (red.findings.length >= 2) {
    result.findings.push({
      id: "verbosity",
      name: "冗长/冗余",
      severity: "minor",
      dims: ["economy"],
      template: null,
      diagnosis: "检测到高置信冗余（重复约束/套话/同义堆叠/过度修饰）。",
      fixes: ["按 compressSteps 删除冗余", "压缩 ≥30% 后用 compress-verify.mjs 回归"],
      evidence: red.findings.slice(0, 5).map((f) => ({ quote: f.quote, line: f.line, rule: f.rule })),
    });
  }

  // 4. token 预算
  const modelFamily = fp && fp.model_family ? fp.model_family : undefined;
  const est = estimateTokens(prompt, modelFamily);
  const budget = fp && fp.context_budget ? Number(fp.context_budget) : 0;
  const threshold = budget > 0 ? budget * 0.6 : 4000;
  if (est.tokens > threshold) {
    result.findings.push({
      id: "over_budget",
      name: "超长未预算",
      severity: "major",
      dims: ["economy"],
      template: null,
      diagnosis: `估算 ${est.tokens} token，超过阈值 ${Math.round(threshold)}（${budget > 0 ? "context_budget 的 60%" : "默认 4000"}）：长提示词会稀释关键指令。`,
      fixes: ["压缩至预算内", "拆分任务或精简背景"],
      evidence: [{ quote: `估算 ${est.tokens} token`, line: 0 }],
    });
  }

  // 去重（同一分类只保留一次：结构信号 vs 冗余 vs 失败现象）
  const seen = new Set();
  result.findings = result.findings.filter((f) => {
    if (seen.has(f.id)) return false;
    seen.add(f.id);
    return true;
  });

  // 5. 推荐模板（major 优先，其次 minor；安全优先时不给模板）
  const majors = result.findings.filter((f) => f.severity === "major");
  const templateSource = majors.length ? majors : result.findings;
  const templates = templateSource
    .map((f) => f.template)
    .filter(Boolean);
  result.recommended_templates = [...new Set(templates)].slice(0, 3);
  const hasUnsafe = result.findings.some((f) => f.id === "unsafe");
  if (hasUnsafe) result.recommended_templates = [];

  // 6. 摘要
  if (!result.findings.length) {
    result.summary = "未发现明显问题（基础结构尚可）；如需更高标准，可对照 references/scoring-rubric.md 逐维自查。";
  } else {
    const m = result.findings.filter((f) => f.severity === "major").length;
    const n = result.findings.length - m;
    result.summary = `共 ${result.findings.length} 项诊断（major ${m} / minor ${n}）；建议按 major → minor 顺序修补。`;
  }
  return result;
}

// ================= CLI =================
if (isMain(import.meta)) {
  const args = process.argv.slice(2);
  if (args.includes("--help") || args.includes("-h")) {
    console.log("用法: node " + process.argv[1].split(/[\\/]/).pop() + " <prompt.txt> [--failure <现象>] [--fp <json>] [--json]");
    process.exit(0);
  }
  const opt = makeOpt(args);
  const wantJson = args.includes("--json");
  const failure = opt("failure");
  const fpRaw = opt("fp");
  let fp;
  if (fpRaw !== undefined) {
    try {
      fp = JSON.parse(fpRaw);
    } catch {
      // v1.0.3 修复: 畸形 --fp 不静默忽略，向 stderr 警告后按无指纹继续（fail-soft 但可诊断）
      console.error(`警告: --fp 不是合法 JSON，已忽略（${String(fpRaw).slice(0, 40)}…）`);
      fp = null;
    }
  }
  // v1.0.3 修复: 已知选项的值位置不参与"文件参数"判定，避免 --failure/--fp 取值被误判为输入文件
  const knownOpts = new Set(["--failure", "--fp"]);
  const valueIdx = new Set();
  for (let i = 0; i < args.length; i++) if (knownOpts.has(args[i])) valueIdx.add(i + 1);
  const fileArg = args.find((a, i) => !valueIdx.has(i) && !a.startsWith("--") && !a.startsWith("{") && !a.startsWith("[") && !/^-?\d+$/.test(a));
  let input;
  if (fileArg) {
    if (!existsSync(fileArg)) {
      console.error(`错误: 输入文件不存在: ${fileArg}`);
      process.exit(1);
    }
    input = readFileSync(fileArg, "utf8").replace(/^\uFEFF/, ""); // v1.0.3 修复: 剥离 UTF-8 BOM
  } else input = readFileSync(0, "utf8").replace(/^\uFEFF/, "");
  // v1.0.3 修复: 空输入应非零退出（与其余引擎的"优雅报错"约定一致，避免脚本消费方误判成功）
  if (!input.trim()) {
    console.error("错误: 输入为空：请先提供待诊断的提示词。");
    process.exit(1);
  }

  const r = diagnosePrompt(input, { failure, fp });
  if (wantJson) {
    process.stdout.write(JSON.stringify(r, null, 2) + "\n");
  } else {
    console.log("=== 提示词诊断报告 ===");
    console.log(r.summary);
    for (const f of r.findings) {
      const sev = f.severity === "major" ? "🔴" : "🟡";
      console.log(`\n${sev} [${f.name}] 影响: ${f.dims.join("/")}${f.template ? ` 建议模板: ${f.template}` : ""}`);
      for (const e of f.evidence) {
        if (e.line > 0) console.log(`    第${e.line}行 "${e.quote}"${e.rule ? `（${e.rule}）` : ""}`);
        else console.log(`    ${e.quote}${e.rule ? `（${e.rule}）` : ""}`);
      }
      console.log(`    ${f.diagnosis}`);
      for (const fx of f.fixes) console.log(`    → ${fx}`);
    }
    if (r.recommended_templates.length) {
      console.log(`\n推荐模板: ${r.recommended_templates.join(" / ")}`);
    }
  }
}
