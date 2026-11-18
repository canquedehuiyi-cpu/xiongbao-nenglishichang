#!/usr/bin/env node
// domain-compliance-check.mjs — 领域合规画像引擎（L2 总入口，v1.0.5）
// 能力:
//   1. 读取 references/rules/*.json 领域规则快照（schema 校验后执行）
//   2. 按 domain + jurisdiction + modality 匹配快照，逐条规则检查
//   3. 三档结论: pass（符合）/ warn（存在风险）/ remind（建议补充）
//   4. 规则与引擎分离：新增行业/法域 = 加一份快照，不改引擎代码
// 规则语义:
//   - type=warn   : triggers 命中即风险
//   - type=remind : triggers 为"该要素已体现"的检测词，未命中即建议补充
// 规范时效: 快照带 snapshot_checked/effective_date/status/superseded_by；已废止(status=superseded)快照不参与检查
// 用法:
//   node scripts/domain-compliance-check.mjs --text "理财宣传文案……"
//   node scripts/domain-compliance-check.mjs --text "……" --domain finance --jurisdiction cn --json
//   node scripts/domain-compliance-check.mjs --file <目录内路径>
import { readFileSync, existsSync, readdirSync } from "node:fs";
import { join, dirname, resolve, sep } from "node:path";
import { fileURLToPath } from "node:url";
import { isMain, makeOpt } from "./lib.mjs";

const ROOT = join(dirname(fileURLToPath(import.meta.url)), "..");

// ---------- schema 校验（与 references/rules/_schema.json 一致） ----------
export function validateSnapshot(snap, schema) {
  if (!snap || typeof snap !== "object") return "快照非对象";
  const missing = (schema.required_fields || []).filter((f) => snap[f] === undefined || snap[f] === null);
  if (missing.length) return `缺必填字段: ${missing.join(",")}`;
  if (schema.jurisdiction_values && !schema.jurisdiction_values.includes(snap.jurisdiction)) return `法域非法: ${snap.jurisdiction}`;
  if (schema.status_values && !schema.status_values.includes(snap.status)) return `状态非法: ${snap.status}`;
  if (snap.status === "superseded") return "SUPERSEDED";
  if (schema.modality_values) {
    for (const m of snap.modalities || []) {
      if (!schema.modality_values.includes(m)) return `模态非法: ${m}`;
    }
  }
  for (const r of snap.rules || []) {
    const rm = (schema.rule_required_fields || []).filter((f) => r[f] === undefined || r[f] === null);
    if (rm.length) return `规则 ${r.key || "?"} 缺字段: ${rm.join(",")}`;
    if (schema.rule_type_values && !schema.rule_type_values.includes(r.type)) return `规则 ${r.key} 类型非法: ${r.type}`;
    if (schema.severity_values && !schema.severity_values.includes(r.severity)) return `规则 ${r.key} 严重度非法: ${r.severity}`;
  }
  const mm = (schema.meta_required_fields || []).filter((f) => !snap.meta || snap.meta[f] === undefined);
  if (mm.length) return `meta 缺字段: ${mm.join(",")}`;
  return null;
}

// ---------- 快照加载 ----------
export function loadSnapshots(dir = ROOT) {
  const rulesDir = join(dir, "references", "rules");
  if (!existsSync(rulesDir)) return { ok: false, error: `规则目录不存在: ${rulesDir}` };
  const snapshots = {};
  let schema = null;
  for (const f of readdirSync(rulesDir)) {
    if (!f.endsWith(".json")) continue;
    try {
      const data = JSON.parse(readFileSync(join(rulesDir, f), "utf8"));
      if (f === "_schema.json") { schema = data; continue; }
      const key = f.replace(/\.json$/, "");
      snapshots[key] = data;
    } catch (e) {
      return { ok: false, error: `规则快照解析失败 ${f}: ${e.message}` };
    }
  }
  if (!schema) return { ok: false, error: "缺少 _schema.json" };
  return { ok: true, snapshots, schema };
}

function matchSnapshots(snapshots, { domain = null, jurisdiction = null, modality = null } = {}) {
  return Object.entries(snapshots).filter(([, s]) => {
    if (domain && s.domain !== domain) return false;
    if (jurisdiction && s.jurisdiction !== jurisdiction) return false;
    if (modality && !(s.modalities || []).includes(modality)) return false;
    return true;
  });
}

// ---------- 规则执行 ----------
export function runRule(rule, content) {
  const triggers = Array.isArray(rule.triggers) ? rule.triggers : [];
  if (rule.type === "warn") {
    const hit = triggers.filter((w) => content.includes(w));
    if (hit.length) return { status: "warn", note: `${rule.name}：命中 ${hit.join("/")}（依据：${rule.basis}）` };
    return null;
  }
  if (rule.type === "remind") {
    const hit = triggers.filter((w) => content.includes(w));
    if (hit.length) return null; // 要素已体现
    return { status: "remind", note: `${rule.suggestion}` };
  }
  return null;
}

// ---------- 主检查函数 ----------
export function checkCompliance({ text = "", file = null, domain = null, jurisdiction = null, modality = null, dir = ROOT } = {}) {
  let content = text;
  if (!content && file) {
    // 路径边界防护：file 只能指向 dir 内的文件，防止路径穿越读取越权内容
    const baseAbs = resolve(dir);
    const fileAbs = resolve(dir, file);
    if (!fileAbs.startsWith(baseAbs + sep)) return { ok: false, error: `文件路径越界: ${file}` };
    if (!existsSync(fileAbs)) return { ok: false, error: `文件不存在: ${file}` };
    content = readFileSync(fileAbs, "utf8").replace(/^\uFEFF/, "");
  }
  content = String(content || "");
  if (!content.trim()) {
    return { ok: false, error: "输入为空：请用 --text 或 --file 提供要检查的文本" };
  }

  const loaded = loadSnapshots(dir);
  if (!loaded.ok) return loaded;
  const { snapshots, schema } = loaded;

  // 全量 schema 预校验（任何快照不合法即拒绝执行，防规则注入）
  for (const [key, snap] of Object.entries(snapshots)) {
    const err = validateSnapshot(snap, schema);
    if (err && err !== "SUPERSEDED") return { ok: false, error: `快照 ${key} 不合法: ${err}` };
  }

  const matched = matchSnapshots(snapshots, { domain, jurisdiction, modality });
  if (!matched.length) {
    const scope = [domain && `domain=${domain}`, jurisdiction && `jurisdiction=${jurisdiction}`, modality && `modality=${modality}`].filter(Boolean).join(" ");
    return { ok: true, summary: `未匹配到规则快照（${scope || "无筛选"}），跳过领域合规检查`, results: [], warn_keys: [], remind_keys: [], matched_snapshots: [] };
  }

  const results = [];
  for (const [key, snap] of matched) {
    if (snap.status === "superseded") continue;
    for (const rule of snap.rules || []) {
      const res = runRule(rule, content);
      if (res) results.push({ snapshot: key, domain: snap.domain, jurisdiction: snap.jurisdiction, key: rule.key, name: rule.name, status: res.status, note: res.note, severity: rule.severity });
    }
  }

  const warns = results.filter((r) => r.status === "warn");
  const reminds = results.filter((r) => r.status === "remind");
  const snapLabels = matched.map(([k, s]) => `${k}(${s.label})`);
  return {
    ok: true,
    summary: warns.length
      ? `存在 ${warns.length} 项合规风险，${reminds.length} 项建议补充`
      : (reminds.length ? `未发现明确违规，${reminds.length} 项建议补充` : "全部检查通过"),
    results,
    warn_keys: warns.map((r) => r.key),
    remind_keys: reminds.map((r) => r.key),
    matched_snapshots: snapLabels,
    note: "规则为离线快照（快照内标注核验日期）；正式发布前建议先运行 verify-spec 核验最新官方规范",
  };
}

// ================= CLI =================
if (isMain(import.meta)) {
  const args = process.argv.slice(2);
  const opt = makeOpt(args);
  const json = args.includes("--json");
  const r = checkCompliance({
    text: opt("text") || "",
    file: opt("file") || null,
    domain: opt("domain") || null,
    jurisdiction: opt("jurisdiction") || null,
    modality: opt("modality") || null,
    dir: opt("dir") || ROOT,
  });
  if (!r.ok) {
    process.stderr.write(`✗ ${r.error}\n`);
    process.exit(2);
  }
  if (json) {
    process.stdout.write(JSON.stringify(r, null, 2) + "\n");
  } else {
    process.stdout.write(`${r.summary}\n`);
    process.stdout.write(`  匹配快照: ${r.matched_snapshots.join(" / ") || "无"}\n`);
    for (const res of r.results) {
      const icon = res.status === "warn" ? "⚠" : "•";
      process.stdout.write(`  ${icon} [${res.snapshot}] ${res.name}: ${res.note}\n`);
    }
    process.stdout.write(`\n${r.note}\n`);
  }
}
