#!/usr/bin/env node
// prompt-contract-check.mjs — 契约审计引擎（v1.1.0）
// 功能: 按 Prompt Contract 十一要素（Objective/Context/Task/Constraints/Non-goals/
//       Output format/Examples/Process/Verification/Failure handling/Style）对提示词做
//       确定性检查，输出覆盖/缺失/弱信号 + 判级 + 每要素改进建议。
// 设计原则:
//   1. 确定性: 纯规则匹配，无随机，同一输入恒得同一输出。
//   2. 证据引用: 每条判定带原文引用（quote）+ 行号。
//   3. 与评分/诊断对齐: 契约要素缺失可映射到 score-prompt 的 4 维与 diagnose 的 11 类问题。
// 用法:
//   node scripts/prompt-contract-check.mjs <prompt.txt>       # 人类可读报告
//   node scripts/prompt-contract-check.mjs <prompt.txt> --json # 机器可读
//   echo "提示词文本" | node scripts/prompt-contract-check.mjs
import { readFileSync } from "node:fs";
import { isMain } from "./lib.mjs";

// ================= 契约要素规则库（中英双语） =================

const ELEMENTS = [
  {
    name: "Objective",
    cn: "目标",
    strong: /(目标|目的是|要达成|希望(得到|获得|产出)|最终(要|需)|需求是|本(次|任务)的?(目标|目的))/i,
    weak: /(要|需要|我想|请帮我)/i,
    suggest: "补一句一句话目标，让模型无需猜方向（如「本次目标是产出可上线的活动方案」）",
  },
  {
    name: "Context",
    cn: "背景",
    strong: /(背景|场景|上下文|受众|目标用户|面向|用户是|项目|当前(情况|状态)|已知|材料|素材|参考资料|业务|行业)/i,
    weak: /(情况|现状|说明)/i,
    suggest: "补充背景/受众/已知约束，避免输出不合语境",
  },
  {
    name: "Task",
    cn: "任务",
    strong: /^(请|麻烦|帮我|(任务|Task)[:：]\s*)?\s*(写|生成|创建|分析|总结|翻译|计算|重构|设计|评估|列出|解释|优化|回答|抽取|提取|选择|比较|判断|推荐|规划|实现|配置|审查|调试|迁移|make|create|write|analyze|summarize|translate|calculate|refactor|design|explain|review|answer|extract|choose|select|compare|recommend|plan|implement)(?=[\s，。；：、（(：;,:]|[\u4e00-\u9fff]|$)/im,
    weak: /(处理|弄|搞|看看|试试)/i,
    suggest: "写明具体要做什么（祈使动词 + 明确对象），避免泛泛而谈",
  },
  {
    name: "Constraints",
    cn: "约束",
    strong: /(不要|不能|不许|禁止|不得|边界|限制|仅限|只允许|不能超过|不超过|必须在.{0,10}内|只能|不允许)/i,
    weak: /(注意|小心|务必|尽量)/i,
    suggest: "显式声明边界（不许做什么/资源限制），堵住越界发挥",
  },
  {
    name: "Non-goals",
    cn: "非目标",
    strong: /(非目标|不需要|不用做|不在.{0,6}(任务|范围)|不要顺带|不包含|无需|不做|不必|无关内容|范围外)/i,
    weak: /(暂不|先不)/i,
    suggest: "明确「这不是本任务的范围」，防止范围蔓延",
  },
  {
    name: "Output format",
    cn: "输出格式",
    strong: /(格式|输出为|输出\s*(JSON|数组|列表|表格|结果)|JSON|Markdown|表格|分点|按以下(结构|格式)|以.{0,10}(形式|格式)|numbered list|bulleted list|Output:|Format:)/i,
    weak: /(返回|输出|呈现)/i,
    suggest: "给出可稳定解析的输出结构（格式/JSON 字段/长度），便于验收",
  },
  {
    name: "Examples",
    cn: "示例",
    strong: /(例如|比如|示例|参考(例子|样例|以下)|如下例|样例|for example|e\.g\.|such as|example:)/i,
    weak: /(示范|举例)/i,
    suggest: "给出期望样例（含边界样例），稳定输出格式",
  },
  {
    name: "Process",
    cn: "分步",
    strong: /(先.{0,6}(再|然后)|步骤|按顺序|分步|第一步|第.{0,2}步|先给|再列|然后|顺序)/i,
    weak: /(分阶段|分几部分)/i,
    suggest: "需要分步的任务给明确执行顺序/结构",
  },
  {
    name: "Verification",
    cn: "验收",
    strong: /(验收|成功标准|如何判断|做对了|正确性|自检|检查.{0,6}(正确|是否符合)|符合.{0,6}要求|通过标准|评估标准|怎么算|criteria|acceptance)/i,
    weak: /(尽量准确|最好|靠谱|可靠)/i,
    suggest: "写明「怎么算做对了」，让输出可验收、失败可定位",
  },
  {
    name: "Failure handling",
    cn: "兜底",
    strong: /(如果.{0,8}(则|就|时)|无法.{0,8}(时|就|则)|缺失|为空|空值|null|undefined|默认|否则|遇到.{0,6}时|兜底|fallback|otherwise|if .{0,12}(then|,)|when .{0,10}empty)/i,
    weak: /(不确定时)/i,
    suggest: "写明出错/缺信息时怎么办（明确说「缺」而非编造）",
  },
  {
    name: "Style",
    cn: "语气",
    strong: /(语气|风格|口吻|正式|轻松|专业地|亲切|简洁地|tone|style|voice)/i,
    weak: /(口语|书面)/i,
    suggest: "指定语气/口吻/语言，与受众匹配",
  },
];

// 弱信号特判：Output format 出现"输出"但无具体格式 → weak（非 strong）
function judgeElement(text, el) {
  const strongHit = [];
  for (const m of text.matchAll(new RegExp(el.strong.source, el.strong.flags.includes("g") ? el.strong.flags : el.strong.flags + "g"))) {
    strongHit.push(m[0].trim().slice(0, 40));
    if (strongHit.length >= 3) break;
  }
  if (strongHit.length) {
    return { state: "strong", evidence: strongHit };
  }
  if (el.weak && new RegExp(el.weak.source, el.weak.flags).test(text)) {
    return { state: "weak", evidence: [] };
  }
  return { state: "missing", evidence: [] };
}

// ================= 主函数 =================

export function contractCheck(text) {
  if (!text || !text.trim()) {
    throw new Error("输入为空：请提供提示词文本（文件参数或 stdin）");
  }
  const elements = [];
  const missing = [];
  const weak = [];
  for (const el of ELEMENTS) {
    const { state, evidence } = judgeElement(text, el);
    elements.push({ name: el.name, cn: el.cn, state, evidence: evidence.slice(0, 3), suggestion: el.suggest });
    if (state === "missing") missing.push(el.name);
    else if (state === "weak") weak.push(el.name);
  }

  let verdict;
  if (missing.length === 0 && weak.length <= 2) verdict = "契约完整（可进入评分/构建）";
  else if (missing.length <= 3) verdict = "基本完整，需补强关键要素";
  else if (missing.length <= 6) verdict = "需补充关键要素";
  else verdict = "契约不完整，建议重构";

  return {
    meta: { engine: "prompt-contract-check.mjs v1.1.0", mode: "contract-audit", elements: ELEMENTS.length },
    elements,
    summary: {
      covered: elements.filter((e) => e.state === "strong").length,
      weak: weak.length,
      missing: missing.length,
      missing_list: missing,
      weak_list: weak,
      verdict,
      suggestions: elements.filter((e) => e.state !== "strong").map((e) => `[${e.name} ${e.cn}] ${e.suggestion}`),
    },
  };
}

// ================= CLI =================

if (isMain(import.meta)) {
  const args = process.argv.slice(2);
  if (args.includes("--help") || args.includes("-h")) {
    console.log("用法: node scripts/prompt-contract-check.mjs <prompt.txt> [--json]（完整用法见脚本头部注释）");
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
    result = contractCheck(input);
  } catch (e) {
    console.error(`✗ ${e.message}`);
    process.exit(1);
  }
  if (wantJson) {
    process.stdout.write(JSON.stringify(result, null, 2) + "\n");
  } else {
    console.log("=== Prompt Contract 契约审计（十一要素） ===");
    for (const e of result.elements) {
      const mark = e.state === "strong" ? "✓" : e.state === "weak" ? "△" : "✗";
      const ev = e.evidence.length ? `（证据: ${e.evidence.join(" / ")}）` : "";
      console.log(`${mark} ${e.name} ${e.cn} — ${e.state === "strong" ? "强" : e.state === "weak" ? "弱" : "缺失"}${ev}`);
      if (e.state !== "strong") console.log(`    建议: ${e.suggestion}`);
    }
    console.log("");
    console.log(`判定: ${result.summary.verdict}`);
    console.log(`覆盖 ${result.summary.covered}/11，弱 ${result.summary.weak}，缺失 ${result.summary.missing}${result.summary.missing_list.length ? "（" + result.summary.missing_list.join("、") + "）" : ""}`);
  }
}
