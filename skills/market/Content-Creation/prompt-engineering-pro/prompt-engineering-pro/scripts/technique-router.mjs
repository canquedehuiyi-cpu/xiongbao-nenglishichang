#!/usr/bin/env node
// technique-router.mjs — 决策树路由引擎（v1.1.0）
// 功能: 按任务特征（复杂度/推理需求/格式要求/agent 化/长上下文/模型族）路由到推荐技法，
//       输出推荐技术 + 理由 + token 成本提示 + 不适用项。对齐 AgentX 决策树主张。
// 确定性: 纯规则匹配，同一输入恒得同一输出。
// 用法:
//   node scripts/technique-router.mjs "任务描述" [--fp '{"model_family":"claude"}'] [--json]
import { isMain } from "./lib.mjs";

// ================= 特征检测 =================

const FEATURES = [
  { key: "agentic", label: "agent/工具化", re: /(工具|调用|function|tool|agent|循环|工作流|自主|多步执行|检索|搜索|api|mcp|自主决策)/i },
  { key: "reasoning", label: "复杂推理", re: /(数学|逻辑|证明|推导|计算|代码|算法|推理|规划|优化|决策树|多条件)/i },
  { key: "format", label: "格式要求", re: /(格式|JSON|表格|列表|分点|结构|输出为|schema)/i },
  { key: "long_context", label: "长上下文", re: /(长文档|多文档|多来源|长文本|全文|报告|论文|聊天记录|对话历史|文档集)/i },
  { key: "multi_step", label: "多步/分阶段", re: /(分步|多步|先.{0,6}再|流程|pipeline|阶段|步骤)/i },
  { key: "iterative", label: "迭代/自查", re: /(自查|迭代|改进|优化|润色|校对|多稿|refine|revise|polish)/i },
  { key: "multi_hop", label: "多跳问答", re: /(多跳|串联|综合.{0,6}(信息|来源)|跨.{0,4}(资料|文档)|子问题)/i },
];

// 技法信息表
const TECHNIQUES = {
  zero_shot: { name: "Zero-shot（零样本）", token: "低", template: "默认（完整契约）", when: "简单事实/格式任务" },
  few_shot: { name: "Few-shot（少样本）", token: "中", template: "FEWSHOT", when: "输出格式需稳定" },
  cot: { name: "CoT（思维链）", token: "中高", template: "COT", when: "复杂推理（非推理模型）" },
  react: { name: "ReAct（推理+行动）", token: "高", template: "REACT", when: "agentic/工具循环" },
  reflection: { name: "Reflection（反思）", token: "中", template: "REFLECT", when: "生成后自查/迭代" },
  chaining: { name: "Chaining（任务链）", token: "中高", template: "PIPELINE", when: "超复杂/分阶段" },
  self_ask: { name: "Self-ask（自问自答）", token: "中高", template: "SELFASK", when: "复杂多跳问答" },
  context_mgmt: { name: "上下文管理", token: "中高", template: "RAG", when: "长文档/多来源" },
  tool_use: { name: "Tool Use 专门化", token: "中高", template: "TOOLCALL", when: "工具 schema/失败恢复" },
};

const REASONING_MODELS = ["o1", "o3", "o4", "deepseek-r1", "kimi-k2", "gemini-thinking", "claude-extended"];
const NON_REASONING_HINT = "（推理模型原生思考，不给显式 CoT 指令）";

// ================= 主函数 =================

export function routeTechnique(task, fp = {}) {
  if (!task || !task.trim()) {
    throw new Error("输入为空：请提供任务描述");
  }
  const family = String(fp.model_family || "").toLowerCase();
  const isReasoning = REASONING_MODELS.some((r) => family.includes(r)) || /推理|thinking|reasoning/i.test(String(fp.reasoning_model || ""));

  const hits = [];
  for (const f of FEATURES) {
    if (f.re.test(task)) hits.push(f.key);
  }

  const recs = [];
  const skip = [];
  const reasons = [];

  if (hits.includes("agentic")) {
    recs.push(TECHNIQUES.react, TECHNIQUES.tool_use);
    reasons.push("检测到 agent/工具/工作流 → 推荐 ReAct 编排 + Tool Use 专门化（工具 schema/失败恢复/输入输出隔离）");
  }
  if (hits.includes("long_context")) {
    recs.push(TECHNIQUES.context_mgmt);
    reasons.push("检测到长文档/多来源 → 上下文管理（置顶关键指令 + query 末尾 + 引用接地 + 必要时分块检索）");
  }
  if (hits.includes("reasoning")) {
    if (isReasoning) {
      recs.push(TECHNIQUES.zero_shot);
      reasons.push(`检测到推理需求且模型为推理族 → 简短直接 + 成功标准，不叠显式 CoT${NON_REASONING_HINT}`);
      skip.push({ technique: "CoT", reason: "推理模型内部已推理，显式 CoT 画蛇添足" });
    } else {
      recs.push(TECHNIQUES.cot);
      reasons.push("检测到推理需求且模型为非推理族 → 显式 CoT（拆步验证）");
    }
  }
  if (hits.includes("format")) {
    recs.push(TECHNIQUES.few_shot);
    reasons.push("检测到格式要求 → Few-shot 稳定输出格式（3-5 个多样相关示例）");
  }
  if (hits.includes("multi_step")) {
    recs.push(TECHNIQUES.chaining);
    reasons.push("检测到多步/分阶段 → 任务链（单步单目标 + 明确交接物，无锚 chain 禁用）");
  }
  if (hits.includes("iterative")) {
    recs.push(TECHNIQUES.reflection);
    reasons.push("检测到迭代/自查需求 → 反思（生成后二次调用纠错）");
  }
  if (hits.includes("multi_hop")) {
    recs.push(TECHNIQUES.self_ask);
    reasons.push("检测到多跳/综合问答 → Self-ask（拆子问题再综合）");
  }

  // 去重（保持推荐顺序）
  const seen = new Set();
  const techniques = recs.filter((r) => !seen.has(r.name) && seen.add(r.name));

  // 简单任务且无任何特征 → Zero-shot
  if (techniques.length === 0) {
    techniques.push(TECHNIQUES.zero_shot);
    reasons.push("任务特征不明显/简单 → Zero-shot + 完整契约（清晰指令即最优）");
  }

  // 兜底不适用项说明
  if (!hits.includes("agentic")) skip.push({ technique: "ReAct", reason: "无工具/agent 信号，ReAct 纯烧 token" });
  if (!hits.includes("reasoning")) skip.push({ technique: "CoT", reason: "无复杂推理需求，CoT 不必要" });
  if (!hits.includes("format")) skip.push({ technique: "Few-shot", reason: "无格式不稳定信号，示例非必需" });
  if (!hits.includes("long_context")) skip.push({ technique: "上下文管理", reason: "输入未超窗口，无需长上下文策略" });

  return {
    meta: {
      engine: "technique-router.mjs v1.1.0",
      mode: "decision-tree",
      model_family: family || "未指定（按通用处理）",
      model_type: isReasoning ? "推理模型" : "非推理模型",
      features_detected: hits,
    },
    route: techniques.map((t) => t.name),
    techniques,
    reasons,
    skip: skip.slice(0, 6),
  };
}

// ================= CLI =================

if (isMain(import.meta)) {
  const args = process.argv.slice(2);
  if (args.includes("--help") || args.includes("-h")) {
    console.log("用法: node scripts/technique-router.mjs \"任务描述\" [--fp '{\"model_family\":\"claude\"}'] [--json]");
    process.exit(0);
  }
  const wantJson = args.includes("--json");
  let fp = {};
  if (args.includes("--fp")) {
    try { fp = JSON.parse(args[args.indexOf("--fp") + 1] || "{}"); } catch { fp = {}; }
  }
  const taskArg = args.find((a) => !a.startsWith("--"));
  if (!taskArg) {
    console.error("错误：请提供任务描述（第一个非选项参数）");
    process.exit(1);
  }
  const result = routeTechnique(taskArg, fp);
  if (wantJson) {
    process.stdout.write(JSON.stringify(result, null, 2) + "\n");
  } else {
    console.log("=== 技法路由（决策树） ===");
    console.log(`模型族: ${result.meta.model_family}（${result.meta.model_type}）`);
    console.log(`检测特征: ${result.meta.features_detected.length ? result.meta.features_detected.join("、") : "无显著特征"}`);
    console.log("");
    console.log("推荐技法（按优先级）:");
    for (const t of result.techniques) {
      console.log(`  → ${t.name}（token ${t.token}，模板 ${t.template}）— ${t.when}`);
    }
    console.log("");
    for (const r of result.reasons) console.log(`  · ${r}`);
    if (result.skip.length) {
      console.log("");
      console.log("不适用项:");
      for (const s of result.skip) console.log(`  ✗ ${s.technique} — ${s.reason}`);
    }
  }
}
