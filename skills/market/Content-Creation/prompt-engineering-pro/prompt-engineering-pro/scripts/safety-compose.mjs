#!/usr/bin/env node
// safety-compose.mjs — 四层安全组合器（L1→L4，v1.0.5）
// 流水线:
//   L1 内容安全   : scan-safety 红线/注入/PII（red 即短路拒绝）
//   L2 行业合规   : domain-compliance 领域快照（domain/jurisdiction/modality 匹配；未识别领域则跳过并提示）
//   L3 平台规范   : 可选。指定 --platform 时提示运行对应平台引擎与 verify-spec 联网核验
//   L4 国家法律   : domain 有对应 national- 快照时（ai-aigc→national-ai / finance→national-finance）附加检查；
//                   game 不在内容行业快照内，统一走专项引擎（wechat-minigame-check / national-game-check）指引
// 自动识别: 未指定 domain/jurisdiction/modality 时，用 domain-router 从文本识别；
//           法域未识别默认 cn（用户主体为中国），并在结果中说明
// 判定:
//   red  -> L1 命中红线，终止
//   warn -> L2/L4 存在明确违规风险
//   pass -> 无明确违规（remind 仅建议）
// 用法:
//   node scripts/safety-compose.mjs --text "……"
//   node scripts/safety-compose.mjs --text "……" --domain finance --jurisdiction cn --platform oceanengine
import { readFileSync, existsSync } from "node:fs";
import { join, dirname, resolve, sep } from "node:path";
import { fileURLToPath } from "node:url";
import { isMain, makeOpt } from "./lib.mjs";
import { scanSafety } from "./scan-safety.mjs";
import { checkCompliance, loadSnapshots } from "./domain-compliance-check.mjs";
import { detectJurisdictionModality } from "./domain-router.mjs";

const ROOT = join(dirname(fileURLToPath(import.meta.url)), "..");

// 领域 → 国家法律层快照映射（无对应则不强制 L4）
const NATIONAL_MAP = { "ai-aigc": "national-ai", finance: "national-finance" };
// 内容行业快照 domain 清单（区别于法域专项快照，如 eu-ai-act）
const INDUSTRY_DOMAINS = ["advertising", "ai-aigc", "deepsynthesis", "medical", "finance"];
// 法域专项快照（按 jurisdiction 匹配；平台类快照 app-store/google-play/oceanengine 走 L3 或对应平台引擎，不混入 L2）
const JURISDICTION_SNAPSHOTS = ["eu-ai-act"];

// 内容行业自动识别：加载 references/lexicon/content-domain-detect.json，命中词即识别
function detectContentDomain(text, dir) {
  const p = join(dir, "references", "lexicon", "content-domain-detect.json");
  if (!existsSync(p)) return { domain: null, terms: [] };
  try {
    const det = JSON.parse(readFileSync(p, "utf8").replace(/^\uFEFF/, ""));
    const t = String(text || "").toLowerCase();
    for (const [d, terms] of Object.entries(det.domains || {})) {
      const hit = terms.filter((w) => t.includes(w.toLowerCase()));
      if (hit.length) return { domain: d, terms: hit };
    }
  } catch { /* 词库损坏时按未识别处理 */ }
  return { domain: null, terms: [] };
}

export function composeSafety({ text = "", file = null, domain = null, jurisdiction = null, modality = null, platform = null, dir = ROOT } = {}) {
  let content = text;
  if (!content && file) {
    // 路径边界防护：file 只能指向 dir 内的文件
    const baseAbs = resolve(dir);
    const fileAbs = resolve(dir, file);
    if (!fileAbs.startsWith(baseAbs + sep)) return { ok: false, error: `文件路径越界: ${file}` };
    if (!existsSync(fileAbs)) return { ok: false, error: `文件不存在: ${file}` };
    content = readFileSync(fileAbs, "utf8").replace(/^\uFEFF/, "");
  }
  content = String(content || "");
  if (!content.trim()) return { ok: false, error: "输入为空：请用 --text 或 --file 提供内容" };

  const report = { ok: true, verdict: "pass", L1: null, L2: null, L3: null, L4: null, auto: null, reason: "", warn_keys: [], remind_keys: [], red_hits: [] };

  // ---- L1 内容安全（短路） ----
  const s1 = scanSafety(content);
  report.L1 = { level: s1.level, hits: s1.hits.length, redacted: s1.redacted };
  if (s1.level === "red") {
    report.verdict = "red";
    report.auto = "未执行（L1 内容安全短路）";
    report.reason = "L1 内容安全命中红线，终止后续检查";
    report.red_hits = s1.hits;
    return report;
  }

  // ---- 内容行业/法域/模态自动识别（未显式指定时） ----
  let effDomain = domain;
  let effJur = jurisdiction;
  let effMod = modality;
  const autoNotes = [];
  if (!effDomain) {
    const cd = detectContentDomain(content, dir);
    if (cd.domain) {
      effDomain = cd.domain;
      autoNotes.push(`行业=${cd.domain}`);
    } else {
      autoNotes.push("未识别行业");
    }
  }
  const jm = detectJurisdictionModality({ text: content, dir });
  if (!effJur) {
    effJur = jm.jurisdiction || "cn";
    autoNotes.push(jm.jurisdiction ? `法域=${jm.jurisdiction}` : "法域=cn(默认)");
  }
  if (!effMod) {
    effMod = jm.modality || null;
    if (jm.modality) autoNotes.push(`模态=${jm.modality}`);
  }
  report.auto = autoNotes.length ? autoNotes.join("，") : "用户显式指定";

  // ---- L2 行业合规 + L4 国家法律 ----
  if (!effDomain) {
    report.L2 = { summary: "未识别到行业领域，跳过领域合规（仅 L1 内容安全检查）", warns: [], reminds: [], matched: [] };
    report.L4 = { warns: [], reminds: [] };
  } else if (!INDUSTRY_DOMAINS.includes(effDomain)) {
    // 非内容行业（如 game 或平台类）：不重复实现行业规则，诚实指引到专项引擎，避免"全部通过"误判
    const hint = effDomain === "game"
      ? "游戏行业合规请运行专项引擎 wechat-minigame-check（微信）/ national-game-check（国家层：防沉迷/版号/实名/内容安全）"
      : `「${effDomain}」暂无内容行业快照，请使用对应平台引擎核验（--platform）`;
    report.L2 = { summary: hint, warns: [], reminds: [], matched: [], results: [] };
    report.L4 = { matched: [], warns: [], reminds: [], results: [] };
  } else {
    const comp = checkCompliance({ text: content, jurisdiction: effJur, modality: effMod, dir });
    if (!comp.ok) return { ok: false, error: comp.error };
    const loaded = loadSnapshots(dir);
    const snap = loaded.ok ? loaded.snapshots : {};
    const natKey = NATIONAL_MAP[effDomain] || null;
    const l2Res = comp.results.filter((r) => {
      if (String(r.snapshot).startsWith("national-")) return false; // L4 专属
      const s = snap[r.snapshot];
      if (!s) return false;
      if (s.domain === effDomain) return true; // 本行业快照
      if (INDUSTRY_DOMAINS.includes(s.domain)) return false; // 其它行业不混入
      if (JURISDICTION_SNAPSHOTS.includes(r.snapshot)) return s.jurisdiction === effJur; // 法域专项
      return false; // 平台类快照不进入 L2
    });
    const l4Res = natKey ? comp.results.filter((r) => r.snapshot === natKey) : [];
    report.L2 = {
      summary: l2Res.some((r) => r.status === "warn")
        ? `存在 ${l2Res.filter((r) => r.status === "warn").length} 项合规风险，${l2Res.filter((r) => r.status === "remind").length} 项建议补充`
        : (l2Res.some((r) => r.status === "remind") ? `未发现明确违规，${l2Res.filter((r) => r.status === "remind").length} 项建议补充` : "全部检查通过"),
      matched: [...new Set(l2Res.map((r) => r.snapshot))],
      warns: l2Res.filter((r) => r.status === "warn").map((r) => r.key),
      reminds: l2Res.filter((r) => r.status === "remind").map((r) => r.key),
      results: l2Res,
    };
    report.L4 = {
      matched: natKey ? [natKey] : [],
      warns: l4Res.filter((r) => r.status === "warn").map((r) => r.key),
      reminds: l4Res.filter((r) => r.status === "remind").map((r) => r.key),
      results: l4Res,
    };
    report.warn_keys = [...report.L2.warns, ...report.L4.warns];
    report.remind_keys = [...report.L2.reminds, ...report.L4.reminds];
  }

  // ---- L3 平台规范（可选提示） ----
  if (platform) {
    report.L3 = { platform, note: "平台规范建议运行对应平台引擎（如 wechat-minigame-check）并用 verify-spec 联网核验最新官方规范" };
  } else {
    report.L3 = { note: "未指定 --platform，跳过平台层（可选）" };
  }

  // ---- 判定 ----
  if (report.warn_keys.length) {
    report.verdict = "warn";
    report.reason = `L2/L4 存在 ${report.warn_keys.length} 项合规风险`;
  } else {
    report.verdict = "pass";
    report.reason = report.remind_keys.length ? "无明确违规，存在建议补充项" : "四层检查全部通过";
  }
  return report;
}

// ================= CLI =================
if (isMain(import.meta)) {
  const args = process.argv.slice(2);
  const opt = makeOpt(args);
  const json = args.includes("--json");
  const r = composeSafety({
    text: opt("text") || "",
    file: opt("file") || null,
    domain: opt("domain") || null,
    jurisdiction: opt("jurisdiction") || null,
    modality: opt("modality") || null,
    platform: opt("platform") || null,
    dir: opt("dir") || ROOT,
  });
  if (!r.ok) {
    process.stderr.write(`✗ ${r.error}\n`);
    process.exit(2);
  }
  if (json) {
    process.stdout.write(JSON.stringify(r, null, 2) + "\n");
  } else {
    const verdictIcon = r.verdict === "red" ? "✗ 拒绝" : r.verdict === "warn" ? "⚠ 风险" : "✓ 通过";
    process.stdout.write(`[四层安全] 结论: ${verdictIcon}\n`);
    process.stdout.write(`  识别: ${r.auto}\n`);
    process.stdout.write(`  L1 内容安全: ${r.L1.level}${r.L1.level === "yellow" ? `（已脱敏）` : ""}\n`);
    if (r.verdict === "red") {
      process.stdout.write(`  ${r.reason}\n`);
    } else {
      process.stdout.write(`  L2 行业合规: ${r.L2.summary}\n`);
      for (const k of r.L2.warns) process.stdout.write(`    ⚠ ${k}\n`);
      for (const k of r.L2.reminds) process.stdout.write(`    • 建议: ${k}\n`);
      if (r.L4.matched && r.L4.matched.length) {
        process.stdout.write(`  L4 国家法律: 风险 ${r.L4.warns.length} 项 / 建议 ${r.L4.reminds.length} 项\n`);
        for (const k of r.L4.warns) process.stdout.write(`    ⚠ ${k}\n`);
      }
      if (r.L3) process.stdout.write(`  L3 平台规范: ${r.L3.note}\n`);
      process.stdout.write(`  判定: ${r.reason}\n`);
    }
  }
}
