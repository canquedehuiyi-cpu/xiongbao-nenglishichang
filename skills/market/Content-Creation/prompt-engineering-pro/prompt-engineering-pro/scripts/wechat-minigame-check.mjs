#!/usr/bin/env node
// wechat-minigame-check.mjs — 微信小游戏合规自检引擎（P1，game/wechat 领域示范引擎）
// 能力:
//   1. 对一段游戏方案/宣传/配置描述文本做平台运营规范要点检查
//   2. 三档结论: pass（符合）/ warn（存在不合规风险）/ remind（建议补充）
//   3. 覆盖要点（基于微信小游戏官方运营规范，核验日期见下方）:
//      变现合规 / 广告占比 / 激励视频频次 / 适龄提示 / 防沉迷 / 资质备案 / 绝对化用语
//   4. 规范时效提示: 规则为离线快照，构建前请先 verify-spec 核验最新规范
// 设计原则: 只做规范要点检查，不改变任何评分结果；"提醒"不等于"违规"
// 规范核验日期: 2026-09-03（联网核实微信开发者文档）
// 用法:
//   node scripts/wechat-minigame-check.mjs --text "游戏宣传文案……"
//   node scripts/wechat-minigame-check.mjs --file <路径> --json
import { readFileSync, existsSync } from "node:fs";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";
import { isMain, makeOpt } from "./lib.mjs";

const ROOT = join(dirname(fileURLToPath(import.meta.url)), "..");

// 绝对化用语（广告法违禁词，用于宣传物料）
const ABSOLUTE_WORDS = ["最", "第一", "首个", "唯一", "国家级", "顶级", "全网最低", "史上最强", "绝对", "100%"];

// 检查项定义：type = pass(需满足) / warn(发现即提示风险) / remind(缺失即建议补充)
const RULES = [
  {
    key: "ads_ratio",
    name: "广告占比",
    type: "warn",
    test: (t) => {
      // 广告位/广告次数占比声明不得超过 50%
      const m = /广告(?:占比|比例)\s*[:：]?\s*(\d+(?:\.\d+)?)\s*%/.exec(t);
      if (!m) return null; // 未声明或未超限，不判
      return Number(m[1]) > 50 ? `广告占比 ${m[1]}% 超过 50%（微信小游戏广告比例规范上限）` : null;
    },
  },
  {
    key: "rewarded_freq",
    name: "激励视频频次",
    type: "warn",
    test: (t) => {
      // 激励视频单用户每日展示次数上限 3 次
      const m = /激励视频[^\d]{0,8}(\d+)\s*次/.exec(t);
      if (!m) return null;
      return Number(m[1]) > 3 ? `激励视频每日 ${m[1]} 次超过 3 次上限（微信官方单用户每日上限）` : null;
    },
  },
  {
    key: "third_party_ads",
    name: "第三方广告 SDK",
    type: "warn",
    test: (t) => {
      const hit = ["穿山甲", "优量汇", "admob", "adcolony", "第三方广告"].filter((w) => t.includes(w));
      return hit.length ? `出现第三方广告服务商字样（${hit.join("/")}），微信小游戏仅允许使用官方流量主广告` : null;
    },
  },
  {
    key: "absolute_claims",
    name: "绝对化用语",
    type: "warn",
    test: (t) => {
      const hit = ABSOLUTE_WORDS.filter((w) => t.includes(w));
      return hit.length ? `宣传物料含绝对化用语（${hit.join("/")}），可能违反广告法` : null;
    },
  },
  {
    key: "age_rating",
    name: "适龄提示",
    type: "remind",
    test: (t) => {
      const has = /适龄|8\+|12\+|16\+|18\+/.test(t);
      return has ? null : "未提及适龄提示（建议标注 8+ 适龄提示）";
    },
  },
  {
    key: "anti_addiction",
    name: "防沉迷",
    type: "remind",
    test: (t) => {
      const has = /防沉迷|每日\s*1\s*小时|22[:：]00|未成年人保护/.test(t);
      return has ? null : "未提及防沉迷说明（未成年人每日 ≤1 小时、22:00-8:00 禁玩）";
    },
  },
  {
    key: "qualification",
    name: "资质备案",
    type: "remind",
    test: (t) => {
      const has = /软著|软件著作权|备案|自审自查|版号/.test(t);
      return has ? null : "未提及上架资质（软著/备案/自审自查为微信小游戏上架必要项）";
    },
  },
];

export function checkWechatMinigame({ text = "", file = null, dir = ROOT } = {}) {
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
    note: "规则为离线快照（核验日期 2026-09-03）；正式发布前请先运行 verify-spec --platform wechat-minigame 核验最新官方规范",
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
  const r = checkWechatMinigame({ text, file, dir });
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
