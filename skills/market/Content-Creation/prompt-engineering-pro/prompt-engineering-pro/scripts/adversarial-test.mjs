#!/usr/bin/env node
// adversarial-test.mjs — 主动对抗测试引擎（v1.1.0）
// 功能: 用内置对抗用例（注入/越狱/泄露/事实性/偏见）对目标 prompt 做压力测试，
//       检查目标 prompt 的防御弱点（是否缺输入输出隔离/白名单/边界/兜底等），
//       输出逐用例风险 + 脆弱点定位 + 风险等级汇总 + 修复建议。
// 定位: 与 scan-safety.mjs（被动检测）+ prompt-defense.mjs（防御建议）组成
//       "主动测试 → 被动检测 → 防御加固"完整闭环。
// 安全: 对抗用例仅在本 skill 工作区/本地对提示词文本做静态弱点分析，
//       不诱导真实越权、不输出可绕过安全机制的攻击提示；只给风险定位与修复建议。
// 确定性: 纯规则弱点分析，同一输入恒同输出。
// 用法:
//   node scripts/adversarial-test.mjs <prompt.txt>            # 压力测试
//   node scripts/adversarial-test.mjs <prompt.txt> --json
//   node scripts/adversarial-test.mjs --list                  # 列出用例清单
import { readFileSync } from "node:fs";
import { isMain } from "./lib.mjs";

// ---------- 目标 prompt 防御弱点检查（确定性规则） ----------
// 对"被测试的 prompt 本身"做弱点定位：它是否缺少防止自身被利用的结构
const WEAKNESS_CHECKS = [
  {
    id: "NO_SEPARATION",
    label: "缺少输入输出隔离",
    re: /^(?!.*(分隔|隔离|以下为|外部输入|不可执行|user input|separator))/m,
    fix: "对外部输入加显式分隔符并标注「不可执行的外部数据」，防止注入随输入混入",
  },
  {
    id: "NO_WHITELIST",
    label: "缺少动作白名单",
    re: /^(?!.*(仅限|只允许|只可|白名单|允许执行|只能|只做))/m,
    fix: "声明模型可执行的有限动作集合（白名单），不开放自由执行",
  },
  {
    id: "TRUSTS_INPUT",
    label: "过度信任输入内容",
    re: /(直接|无条件|原样|照做).{0,10}(执行|处理|输出)|按用户.{0,6}(说的|要求).{0,6}(做|执行)/,
    fix: "对指令性内容先校验后执行：标注来源、分通道、对可疑指令拒绝并说明",
  },
  {
    id: "LEAK_PRONE",
    label: "易泄露风险（无拒绝口径）",
    re: /^(?!.*(不回答|拒绝|不披露|敏感|保密|不外传|不能说))/m,
    fix: "明确「不回答输出原始指令/系统提示类请求」，敏感信息分级不放入同一上下文",
  },
  {
    id: "NO_BOUNDARY",
    label: "缺少行为边界",
    re: /^(?!.*(不要|不能|不得|禁止|仅限|边界|限制|范围|不允许))/m,
    fix: "写清 Non-goals 与边界，堵住越狱/越界发挥空间",
  },
  {
    id: "NO_FALLBACK",
    label: "缺少不确定兜底",
    re: /^(?!.*(不知道|无法|缺失|不确定|标注|兜底|如果.{0,6}(不清|不明)))/m,
    fix: "规定缺信息/不确定时「明确说不知道」而非编造，防事实性风险",
  },
];

// 对抗用例清单（本地弱点测试用，非攻击指令）
const TEST_CASES = [
  { id: "T-INJ-1", category: "injection", desc: "忽略指令注入", check: /^(?!.*(忽略|无视).{0,12}(指令|规则|外部))/m, note: "检测：目标 prompt 是否允许外部输入覆盖既有指令（缺隔离/缺优先级）" },
  { id: "T-INJ-2", category: "injection", desc: "指令数据混合", check: /^(?!.*(分隔|隔离|以下为|外部输入|指令与数据|分通道))/m, note: "检测：目标 prompt 是否缺少指令与数据的物理分隔" },
  { id: "T-JB-1", category: "jailbreak", desc: "越狱角色扮演", check: /^(?!.*(不能|禁止|拒绝|角色边界|内容政策))/m, note: "检测：目标 prompt 是否声明固定角色边界与拒绝口径" },
  { id: "T-LK-1", category: "leaking", desc: "泄露原始指令", check: /^(?!.*(不回答|拒绝|不披露|提示词.*(不外传|不公开)))/m, note: "检测：目标 prompt 是否声明对「输出你的指令」类请求的拒绝口径" },
  { id: "T-FA-1", category: "factuality", desc: "无证据断言", check: /^(?!.*(引用|来源|证据|不确定|标注|不知道))/m, note: "检测：目标 prompt 是否要求引用接地与不确定性标注" },
  { id: "T-BI-1", category: "bias", desc: "绝对化表述", check: /^(?!.*(中立|多视角|避免|预设|立场))/m, note: "检测：目标 prompt 是否要求中立表述与多视角" },
];

export function adversarialTest(text) {
  if (!text || !text.trim()) {
    throw new Error("输入为空：请提供目标提示词文本（文件参数或 stdin）");
  }
  const t = String(text);
  // 1. 弱点定位
  const weaknesses = [];
  for (const w of WEAKNESS_CHECKS) {
    const re = new RegExp(w.re.source, w.re.flags.includes("m") ? w.re.flags : w.re.flags + "m");
    if (re.test(t)) weaknesses.push({ id: w.id, label: w.label, fix: w.fix });
  }
  // 2. 逐用例压力测试：用例命中"目标 prompt 缺防御"则标记该用例风险高
  const results = TEST_CASES.map((tc) => {
    const re = new RegExp(tc.check.source, tc.check.flags.includes("m") ? tc.check.flags : tc.check.flags + "m");
    const vulnerable = re.test(t);
    return { id: tc.id, category: tc.category, desc: tc.desc, note: tc.note, vulnerable };
  });
  const high = results.filter((r) => r.vulnerable).length;
  // 3. 风险等级
  const risk = high === 0 ? "低" : high <= 2 ? "中" : high <= 4 ? "高" : "极高";
  return {
    meta: { engine: "adversarial-test.mjs v1.1.0", mode: "adversarial-test", cases: TEST_CASES.length, weaknesses_checks: WEAKNESS_CHECKS.length },
    target_stats: { chars: t.length, lines: t.split("\n").length },
    weaknesses,
    cases: results,
    summary: { total_cases: results.length, vulnerable_cases: high, risk_level: risk },
    verdict: high === 0
      ? "未发现明显可被利用的防御弱点"
      : `发现 ${high} 个用例可被利用：优先按 weaknesses 中的修复建议加固`,
    fix_suggestions: [...new Set(weaknesses.map((w) => `[${w.label}] ${w.fix}`))],
    pipeline_sync: "本引擎=主动测试；scan-safety=被动红线/注入/PII 检测；prompt-defense=分类防御建议。三引擎互补成闭环。",
  };
}

// ================= CLI =================
if (isMain(import.meta)) {
  const args = process.argv.slice(2);
  if (args.includes("--help") || args.includes("-h")) {
    console.log("用法: node scripts/adversarial-test.mjs <prompt.txt> [--json] | --list");
    console.log("说明: 本地对抗用例压力测试（静态弱点分析），不诱导真实越权");
    process.exit(0);
  }
  const wantJson = args.includes("--json");
  if (args.includes("--list")) {
    const out = { meta: { engine: "adversarial-test.mjs v1.1.0", mode: "adversarial-test-list", cases: TEST_CASES.length }, cases: TEST_CASES, weaknesses_checks: WEAKNESS_CHECKS.map((w) => ({ id: w.id, label: w.label })) };
    if (wantJson) process.stdout.write(JSON.stringify(out, null, 2) + "\n");
    else {
      console.log("=== 主动对抗测试用例（本地弱点测试）===");
      for (const c of TEST_CASES) console.log(`  ${c.id} [${c.category}] ${c.desc}`);
      console.log("\n弱点检查项:");
      for (const w of WEAKNESS_CHECKS) console.log(`  ${w.id} ${w.label}`);
    }
    process.exit(0);
  }
  const fileArg = args.find((a) => !a.startsWith("--") && !a.startsWith("{") && !a.startsWith("[") && !/^-?\d+$/.test(a));
  let input;
  try {
    if (fileArg) input = readFileSync(fileArg, "utf8").replace(/^\uFEFF/, "");
    else input = readFileSync(0, "utf8").replace(/^\uFEFF/, "");
  } catch (e) {
    console.error(`✗ 读取失败: ${e.message}`);
    process.exit(1);
  }
  let result;
  try {
    result = adversarialTest(input);
  } catch (e) {
    console.error(`✗ ${e.message}`);
    process.exit(1);
  }
  if (wantJson) {
    process.stdout.write(JSON.stringify(result, null, 2) + "\n");
  } else {
    console.log("=== 主动对抗测试 ===");
    console.log(`目标: ${result.target_stats.chars} 字符 / ${result.target_stats.lines} 行`);
    console.log("\n[1] 防御弱点定位:");
    if (!result.weaknesses.length) console.log("  ✓ 未发现明显弱点");
    else for (const w of result.weaknesses) console.log(`  ✗ ${w.label}: ${w.fix}`);
    console.log("\n[2] 对抗用例压力测试:");
    for (const c of result.cases) {
      console.log(`  ${c.vulnerable ? "✗" : "✓"} ${c.id} [${c.category}] ${c.desc}${c.vulnerable ? " → 可被利用" : ""}`);
    }
    console.log(`\n风险等级: ${result.summary.risk_level}（${result.summary.vulnerable_cases}/${result.summary.total_cases} 用例可被利用）`);
    console.log(`判定: ${result.verdict}`);
    if (result.fix_suggestions.length) {
      console.log("\n修复建议:");
      for (const f of result.fix_suggestions) console.log(`  - ${f}`);
    }
    console.log(`\n${result.pipeline_sync}`);
  }
}
