#!/usr/bin/env node
// national-game-check.mjs — 国家层游戏合规自检引擎（全平台统一）
// 能力:
//   1. 对一段游戏方案/宣传/配置描述文本做国家层合规要点检查（所有平台小游戏通用）
//   2. 三档结论: pass（符合）/ warn（存在不合规风险）/ remind（建议补充）
//   3. 覆盖要点（源于国家新闻出版署/中国政府网官方文件，核验日期见下方）:
//      防沉迷时段阈值（国新出发〔2021〕14号）/ 实名注册登录 / 版号与出版物审批 / 健康游戏忠告 / 内容安全 / 未成年人保护
//   4. 规范时效提示: 规则为离线快照，构建前请先 verify-spec 核验最新规范
// 设计原则: 只做规范要点检查，不改变任何评分结果；"提醒"不等于"违规"；一套事实适用全平台
// 规范核验日期: 2026-09-03（联网核实国家新闻出版署 nppa.gov.cn + 中国政府网 gov.cn）
// 用法:
//   node scripts/national-game-check.mjs --text "游戏方案描述……"
//   node scripts/national-game-check.mjs --file <路径> --json
import { readFileSync, existsSync } from "node:fs";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";
import { isMain, makeOpt } from "./lib.mjs";

const ROOT = join(dirname(fileURLToPath(import.meta.url)), "..");

// 检查项定义：type = pass(需满足) / warn(发现即提示风险) / remind(缺失即建议补充)
const RULES = [
  {
    key: "addiction_window",
    name: "防沉迷时段",
    type: "warn",
    test: (t) => {
      // 声明时段与国新出发〔2021〕14号不符（官方：仅周五/周六/周日及法定节假日 20-21 时）
      const bad = /每日(?!仅|只限|限于)[周五六日]|每日都可|全天开放|随时可玩/.exec(t);
      return bad ? `防沉迷时段声明与国新出发〔2021〕14号不符（${bad[0]}）；官方为仅周五/周六/周日及法定节假日 20-21 时向未成年人提供服务` : null;
    },
  },
  {
    key: "addiction_duration",
    name: "防沉迷时长",
    type: "warn",
    test: (t) => {
      // 未成年人单日时长声明超过官方 1 小时上限
      const m = /未成年人[^\d]{0,12}(\d+(?:\.\d+)?)\s*小时/.exec(t);
      if (!m) return null;
      return Number(m[1]) > 1 ? `未成年人单日 ${m[1]} 小时超过官方 1 小时上限（国新出发〔2021〕14号）` : null;
    },
  },
  {
    key: "real_name",
    name: "实名注册",
    type: "remind",
    test: (t) => /实名|真实身份|防沉迷实名验证系统/.test(t) ? null : "未提及实名注册/登录要求（所有网络游戏必须接入国家新闻出版署网络游戏防沉迷实名验证系统）",
  },
  {
    key: "version_number",
    name: "版号与审批",
    type: "remind",
    test: (t) => /版号|批准文号|出版号|网络游戏出版物|出版物审批/.test(t) ? null : "未提及版号/出版物审批（上线前须取得国家新闻出版署批准，游戏画面显著位置标注批准文号/出版号/著作权登记号）",
  },
  {
    key: "health_advice",
    name: "健康游戏忠告",
    type: "remind",
    test: (t) => /健康游戏忠告|抵制不良游戏/.test(t) ? null : "未提及《健康游戏忠告》（须在游戏开始画面显著位置全文登载）",
  },
  {
    key: "content_safety",
    name: "内容安全",
    type: "warn",
    test: (t) => {
      const hit = ["赌博", "博彩", "扎金花", "梭哈", "百家乐", "色情", "低俗", "血腥", "暴力教唆"].filter((w) => t.includes(w));
      return hit.length ? `内容含违禁要素（${hit.join("/")}），违反网络游戏内容安全管理` : null;
    },
  },
  {
    key: "minor_protection",
    name: "未成年人保护",
    type: "remind",
    test: (t) => /未成年人|家长监护|充值限制|防沉迷/.test(t) ? null : "未提及未成年人保护措施（付费限制/家长监护/防沉迷）",
  },
];

export function checkNationalGame({ text = "", file = null, dir = ROOT } = {}) {
  let content = text;
  if (!content && file) {
    const p = join(dir, file);
    if (!existsSync(p)) return { ok: false, error: `文件不存在: ${file}` };
    content = readFileSync(p, "utf8").replace(/^\uFEFF/, "");
  }
  content = String(content || "");
  if (!content.trim()) {
    return { ok: false, error: "输入为空：请用 --text 或 --file 提供要检查的文本" };
  }

  const results = RULES.map((r) => {
    const msg = r.test(content);
    if (msg === null) return { key: r.key, name: r.name, status: "pass", note: r.type === "remind" ? "已包含" : "未发现相关声明" };
    if (r.type === "warn") return { key: r.key, name: r.name, status: "warn", note: msg };
    return { key: r.key, name: r.name, status: "remind", note: msg };
  });

  const warns = results.filter((r) => r.status === "warn");
  const reminds = results.filter((r) => r.status === "remind");
  return {
    ok: true,
    summary: warns.length
      ? `存在 ${warns.length} 项合规风险，${reminds.length} 项建议补充`
      : (reminds.length ? `未发现明确违规，${reminds.length} 项建议补充` : "全部检查通过"),
    results,
    warn_keys: warns.map((r) => r.key),
    remind_keys: reminds.map((r) => r.key),
    note: "规则为离线快照（核验日期 2026-09-03，来源国家新闻出版署/中国政府网）；一套事实适用全平台；正式发布前请先运行 verify-spec --platform national-game 核验最新规范",
  };
}

// ================= CLI =================
if (isMain(import.meta)) {
  const args = process.argv.slice(2);
  const opt = makeOpt(args);
  const json = args.includes("--json");
  const text = opt("text") || "";
  const file = opt("file") || null;
  const dir = opt("dir") || ROOT;
  const r = checkNationalGame({ text, file, dir });
  if (!r.ok) {
    process.stderr.write(`✗ ${r.error}\n`);
    process.exit(2);
  }
  if (json) {
    process.stdout.write(JSON.stringify(r, null, 2) + "\n");
  } else {
    process.stdout.write(`${r.summary}\n`);
    for (const res of r.results) {
      const icon = res.status === "pass" ? "✓" : res.status === "warn" ? "⚠" : "•";
      process.stdout.write(`  ${icon} ${res.name}: ${res.note}\n`);
    }
    process.stdout.write(`\n${r.note}\n`);
  }
}
