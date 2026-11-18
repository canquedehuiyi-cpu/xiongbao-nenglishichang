#!/usr/bin/env node
// domain-router.mjs — 领域路由引擎（P0，对应领域适配层）
// 能力:
//   1. 从需求文本识别领域（game/visual/ai/ecommerce/content）与命中词
//   2. 输出领域指纹：领域标签、平台、可用模板、词库、评分权重、引导语
//   3. 强制指定: --domain 直接指定领域（跳过识别）
//   4. 未命中: 返回 general（不虚构领域）
// 设计原则: 只做确定性路由，不改变任何评分/安全门禁结果
// 用法:
//   node scripts/domain-router.mjs --request "帮我写微信小游戏的 IAA 广告文案"
//   node scripts/domain-router.mjs --request "设计一个电商详情页提示词" --json
//   node scripts/domain-router.mjs --domain game --json
import { readFileSync, existsSync } from "node:fs";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";
import { safePath, isMain, makeOpt } from "./lib.mjs";

const ROOT = join(dirname(fileURLToPath(import.meta.url)), "..");
const REGISTRY_PATH = join(ROOT, "domains", "registry.json");
const DETECT_PATH = join(ROOT, "references", "lexicon", "domain-detect.json");
const DETECT_JUR_PATH = join(ROOT, "references", "lexicon", "jurisdiction-detect.json");

const GENERAL = {
  domain: "general",
  label: "通用",
  platforms: [],
  templates: [],
  lexicons: [],
  spec_sources: [],
  score_weights: {},
  hint: "未识别到明确领域，按通用提示词工程处理",
};

function loadJson(file, fallback) {
  try {
    if (!existsSync(file)) return fallback;
    return JSON.parse(readFileSync(file, "utf8").replace(/^\uFEFF/, ""));
  } catch {
    return fallback;
  }
}

export function getRegistry() {
  return loadJson(REGISTRY_PATH, { domains: {} });
}

// 统一智能路由雏形（v1.0.8）：从需求文本判定"走哪条业务线"
//   compliance_check   → 合规核验线（verify-spec / domain-compliance-check / safety-compose 等）
//   prompt_optimization→ 提示词技法线（L3 技术选择 / technique-router 等）
//   both              → 两条线都要（合规 + 优化）
//   none              → 不明确（调用方自行决定，通常按 prompt_optimization 处理）
const COMPLIANCE_TERMS = ["合规", "版号", "防沉迷", "资质", "上架", "过审", "审核", "备案", "实名", "广告法", "适龄", "平台规范", "官方规范", "规则", "内容安全", "绿标", "指引", "政策", "监管", "法规", "合法"];
const OPTIMIZATION_TERMS = ["提示词", "prompt", "system prompt", "system_prompt", "优化", "改进", "生成", "写一个", "帮我写", "评估", "评分", "不work", "不好用", "提升", "改写", "调试", "压缩", "迁移"];

export function classifyIntent({ request = "" } = {}) {
  const t = String(request || "").toLowerCase();
  if (!t.trim()) return { intent: "none", compliance_hit: [], optimization_hit: [], note: "输入为空，意图未判定" };
  const complianceHit = COMPLIANCE_TERMS.filter((w) => t.includes(w.toLowerCase()));
  const optHit = OPTIMIZATION_TERMS.filter((w) => t.includes(w.toLowerCase()));
  let intent;
  if (complianceHit.length && optHit.length) intent = "both";
  else if (complianceHit.length) intent = "compliance_check";
  else if (optHit.length) intent = "prompt_optimization";
  else intent = "none";
  return { intent, compliance_hit: complianceHit.slice(0, 5), optimization_hit: optHit.slice(0, 5), note: intent === "both" ? "合规核验 + 提示词优化双线" : intent === "compliance_check" ? "走合规核验线" : intent === "prompt_optimization" ? "走提示词技法线" : "意图未明确，按提示词技法线兜底" };
}

// 法域/模态识别（v1.0.5 新增）：从输入文本识别 jurisdiction 与 modality，未命中返回 null
export function detectJurisdictionModality({ text = "", dir = ROOT } = {}) {
  const det = loadJson(join(safePath(dir), "references", "lexicon", "jurisdiction-detect.json"), { jurisdictions: {}, modalities: {} });
  const t = String(text || "").toLowerCase();
  let jurisdiction = null;
  let jurisdictionTerms = [];
  const jurs = det.jurisdictions || {};
  for (const [j, terms] of Object.entries(jurs)) {
    const hit = terms.filter((w) => t.includes(w.toLowerCase()));
    if (hit.length) {
      jurisdiction = j;
      jurisdictionTerms = hit;
      break; // 取首个命中法域，避免多法域时引入不确定
    }
  }
  let modality = null;
  let modalityTerms = [];
  const mods = det.modalities || {};
  for (const [m, terms] of Object.entries(mods)) {
    const hit = terms.filter((w) => t.includes(w.toLowerCase()));
    if (hit.length) {
      modality = m;
      modalityTerms = hit;
      break;
    }
  }
  return { jurisdiction, jurisdictionTerms, modality, modalityTerms };
}

export function routeDomain({ request = "", domain = null, dir = ROOT } = {}) {
  const base = safePath(dir);
  const regPath = join(base, "domains", "registry.json");
  const detPath = join(base, "references", "lexicon", "domain-detect.json");
  const registry = loadJson(regPath, { domains: {} });
  const detect = loadJson(detPath, { domains: {} });
  const domains = registry.domains || {};
  const jurMod = detectJurisdictionModality({ text: request, dir: base });
  const intent = classifyIntent({ request });

  // 强制指定领域
  if (domain) {
    if (!domains[domain]) {
      return { ok: false, error: `未知领域: ${domain}（可选: ${Object.keys(domains).join("/")}）` };
    }
    const d = domains[domain];
    return { ok: true, domain, label: d.label, platforms: d.platforms, templates: d.templates, lexicons: d.lexicons, spec_sources: d.spec_sources, score_weights: d.score_weights, hint: d.hint, matched_terms: [], score: null, forced: true, general: false, jurisdiction: jurMod.jurisdiction, modality: jurMod.modality, intent: intent.intent, intent_note: intent.note };
  }

  // 关键词计分识别
  const text = String(request || "").toLowerCase();
  if (!text.trim()) {
    return { ok: true, ...GENERAL, matched_terms: [], score: 0, general: true, note: "输入为空，按通用处理", jurisdiction: null, modality: null, intent: "none", intent_note: "输入为空" };
  }
  const detectDomains = detect.domains || {};
  let best = { domain: null, score: 0, terms: [] };
  for (const [d, terms] of Object.entries(detectDomains)) {
    const hit = terms.filter((t) => text.includes(t.toLowerCase()));
    if (hit.length > best.score) {
      best = { domain: d, score: hit.length, terms: hit };
    }
  }
  if (!best.domain || !domains[best.domain]) {
    return { ok: true, ...GENERAL, matched_terms: [], score: 0, general: true, jurisdiction: jurMod.jurisdiction, modality: jurMod.modality, intent: intent.intent, intent_note: intent.note };
  }
  const d = domains[best.domain];
  return {
    ok: true,
    domain: best.domain,
    label: d.label,
    platforms: d.platforms,
    templates: d.templates,
    lexicons: d.lexicons,
    spec_sources: d.spec_sources,
    score_weights: d.score_weights,
    hint: d.hint,
    matched_terms: best.terms,
    score: best.score,
    forced: false,
    general: false,
    jurisdiction: jurMod.jurisdiction,
    modality: jurMod.modality,
    intent: intent.intent,
    intent_note: intent.note,
  };
}

// ================= 1.1.0 统一智能路由收口 =================
// 需求判定（合规核验/提示词优化/两者）→ 走对应引擎链，合规线与技法线统一入口，输出单份结构化报告。
// 依赖 registry.dependency_graph（1.1.0 依赖图）：引用依赖边说明链路，不重复登记。
export function routeRequest({ request = "", domain = null, dir = ROOT } = {}) {
  const base = safePath(dir);
  const route = routeDomain({ request, domain, dir: base });
  if (!route.ok) return route;
  const intent = route.intent || "none";
  const complianceChain = [];
  const techniqueChain = [];
  if (intent === "compliance_check" || intent === "both") {
    complianceChain.push("verify-spec", "domain-compliance-check", "safety-compose", "scan-safety");
    if (route.domain === "game" && (route.platforms || []).includes("wechat-minigame")) complianceChain.push("wechat-minigame-check");
    if (route.domain === "game") complianceChain.push("national-game-check");
  }
  if (intent === "prompt_optimization" || intent === "both" || intent === "none") {
    techniqueChain.push("technique-router", "build-prompt", "token-count", "score-prompt", "prompt-contract-check");
  }
  const registry = getRegistry();
  const dg = registry.dependency_graph || null;
  return {
    ok: true,
    domain: route.domain,
    label: route.label,
    general: route.general,
    platforms: route.platforms,
    templates: route.templates,
    jurisdiction: route.jurisdiction,
    modality: route.modality,
    unified: {
      engine: "domain-router.mjs v1.1.0",
      intent,
      intent_note: route.intent_note,
      compliance_chain: complianceChain,
      technique_chain: techniqueChain,
      route_summary: intent === "both" ? "合规核验 + 提示词优化双线执行" : intent === "compliance_check" ? "仅合规核验线" : intent === "prompt_optimization" ? "仅提示词技法线" : "意图未明确，按提示词技法线兜底",
      dependency_graph_version: dg ? dg.version : null,
    },
    hint: route.hint,
  };
}

// ================= CLI =================
if (isMain(import.meta)) {
  const args = process.argv.slice(2);
  const opt = makeOpt(args);
  const json = args.includes("--json");
  const request = opt("request") || "";
  const domain = opt("domain") || null;
  const dir = opt("dir") || ROOT;
  const unified = args.includes("--unified");
  const r = unified ? routeRequest({ request, domain, dir }) : routeDomain({ request, domain, dir });
  if (!r.ok) {
    process.stderr.write(`✗ ${r.error}\n`);
    process.exit(2);
  }
  if (json) {
    process.stdout.write(JSON.stringify(r, null, 2) + "\n");
  } else if (unified) {
    process.stdout.write(`领域: ${r.domain}（${r.label}）${r.general ? " · 通用" : ""}\n`);
    process.stdout.write(`意图: ${r.unified.intent}（${r.unified.intent_note}）\n`);
    process.stdout.write(`路线: ${r.unified.route_summary}\n`);
    if (r.unified.compliance_chain.length) process.stdout.write(`合规线: ${r.unified.compliance_chain.join(" → ")}\n`);
    if (r.unified.technique_chain.length) process.stdout.write(`技法线: ${r.unified.technique_chain.join(" → ")}\n`);
    if (r.unified.dependency_graph_version) process.stdout.write(`依赖图: v${r.unified.dependency_graph_version}\n`);
    process.stdout.write(`引导: ${r.hint}\n`);
  } else {
    process.stdout.write(`领域: ${r.domain}（${r.label}）${r.general ? " · 通用" : ""}\n`);
    if (!r.general) {
      if (r.forced) process.stdout.write(`来源: 强制指定 --domain\n`);
      else process.stdout.write(`来源: 关键词识别（命中 ${r.score} 项: ${r.matched_terms.join("/")}）\n`);
      if (r.platforms.length) process.stdout.write(`平台: ${r.platforms.join("/")}\n`);
      if (r.templates.length) process.stdout.write(`模板: ${r.templates.join("/")}\n`);
      if (r.score_weights && Object.keys(r.score_weights).length) {
        process.stdout.write(`评分权重: ${Object.entries(r.score_weights).map(([k, v]) => `${k}=${v}`).join(" ")}\n`);
      }
    }
    process.stdout.write(`引导: ${r.hint}\n`);
    process.stdout.write(`意图: ${r.intent}（${r.intent_note}）\n`);
  }
}
