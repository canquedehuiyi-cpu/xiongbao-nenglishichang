// build-site-data.mjs — 把 credit-watch 的本机采集记录转成看板数据契约。
// 输入：~/.qoder-cn/credit-watch/accounts.json 与 history.jsonl（probe.mjs 追加的真实记录）
// 输出：--out 指定的 credits.json，字段与 dashboard/site/app.js 的读取端一致。
// 只读输入、只写 --out 一个文件；不接触任何凭据。
import { readFileSync, writeFileSync, mkdirSync, existsSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { homedir } from "node:os";
import { fileURLToPath } from "node:url";
import { judgeReward, rewardWindowDay, windowOpenIso, addDays, REWARD_TTL_DAYS } from "./reward-window.mjs";

const HERE = dirname(fileURLToPath(import.meta.url));
const PLUGIN_ROOT = resolve(HERE, "..");
const DATA_DIR = join(homedir(), ".qoder-cn", "credit-watch");
// 页脚与「关于」里要说清这是哪个版本的插件产的数，别让人对着旧包读新说明。
let pluginVersion = null;
try {
  pluginVersion = JSON.parse(readFileSync(join(PLUGIN_ROOT, ".qoder-plugin", "plugin.json"), "utf8")).version || null;
} catch { /* 读不到就不显示版本 */ }
const PLAN_QUOTA = { PRO: 2000, PRO_PLUS: 6000, ULTRA: 20000, FREE: 0 };
const CN_TZ_OFFSET = 8 * 3600 * 1000;
const IS_DAY = (s) => /^\d{4}-\d{2}-\d{2}$/.test(String(s || ""));

const argv = process.argv.slice(2);
const flag = (name, fallback = null) => {
  const i = argv.indexOf(`--${name}`);
  return i >= 0 && argv[i + 1] ? argv[i + 1] : fallback;
};
const OUT = flag("out") ? resolve(flag("out")) : null;
const ACCOUNTS_FILE = resolve(flag("accounts", join(DATA_DIR, "accounts.json")));
const HISTORY_FILE = resolve(flag("history", join(DATA_DIR, "history.jsonl")));
const DAYS = Math.max(2, Number(flag("days", "30")) || 30);

const die = (msg, hint) => {
  console.error(msg);
  if (hint) console.error(hint);
  process.exit(1);
};

if (!OUT) die("缺少 --out <credits.json 路径>", "例：--out \"$HOME/.qoder-cn/credit-watch/credits.json\"（本机服务默认就写这里）");
if (!existsSync(ACCOUNTS_FILE)) die(`找不到账号配置：${ACCOUNTS_FILE}`, "先用 /credit-start 登记账号，或用 --accounts 指定路径。");

let cfg;
try {
  cfg = JSON.parse(readFileSync(ACCOUNTS_FILE, "utf8"));
} catch (e) {
  die(`账号配置解析失败：${e?.message || e}`);
}
const threshold = Number(cfg.threshold) || 200;
const registered = cfg.accounts || [];
const warnings = [];

let raw = [];
if (!existsSync(HISTORY_FILE)) {
  warnings.push(`没有历史文件 ${HISTORY_FILE}：在看板上点「刷新余量数据」采集（或跑 node scripts/probe.mjs）`);
} else {
  readFileSync(HISTORY_FILE, "utf8").split("\n").forEach((line, i) => {
    const s = line.trim();
    if (!s) return;
    try {
      const r = JSON.parse(s);
      if (r && r.userId && r.ts && Number.isFinite(Date.parse(r.ts))) raw.push(r);
      else warnings.push(`第 ${i + 1} 行缺 userId 或合法 ts，已跳过`);
    } catch {
      warnings.push(`第 ${i + 1} 行不是合法 JSON，已跳过`);
    }
  });
}

// 采集时间按东八区归到哪一天，与 probe 里 nextRefresh 的日期口径一致。
const dayOf = (ts) => new Date(new Date(ts).getTime() + CN_TZ_OFFSET).toISOString().slice(0, 10);
const toMs = (d) => Date.parse(`${d}T00:00:00+08:00`);

const byUser = new Map();
for (const r of raw) {
  if (!byUser.has(r.userId)) byUser.set(r.userId, []);
  byUser.get(r.userId).push(r);
}

// 按 accounts.json 的登记顺序输出，未登记的号排在后面：
// 端口等派生字段依赖这个顺序，不能跟着 history.jsonl 的行序漂。
const orderedUsers = new Map();
for (const a of registered) {
  if (byUser.has(a.userId)) orderedUsers.set(a.userId, byUser.get(a.userId));
}
for (const [u, list] of byUser) {
  if (!orderedUsers.has(u)) orderedUsers.set(u, list);
}

const output = [];
const accountMeta = [];
const seenLabels = new Map();

for (const [userId, list] of orderedUsers) {
  list.sort((a, b) => (a.ts < b.ts ? -1 : a.ts > b.ts ? 1 : 0));
  const hit = registered.find((a) => a.userId === userId);
  const label = hit ? hit.label : list.at(-1).label || `未登记(${String(userId).slice(0, 8)})`;
  if (seenLabels.has(label) && seenLabels.get(label) !== userId) {
    warnings.push(`标签「${label}」被两个 userId 共用，看板会把它们合并成一个号`);
  }
  seenLabels.set(label, userId);

  const tier = String(list.at(-1).planTier || "").replace("PLAN_TIER_", "") || "UNKNOWN";
  let quota = PLAN_QUOTA[tier];
  if (!quota) {
    const observed = Math.max(...list.map((r) => r.planRemaining || 0), 0);
    quota = observed ? Math.ceil(observed / 1000) * 1000 : 0;
    warnings.push(`${label} 的套餐 ${tier} 不在额度表里，按观测峰值推断周期额度为 ${quota}`);
  }

  const lastOfDay = new Map();
  let prev = null;
  let maxGap = 0;
  let seenPort = null;
  const refillDays = [];

  for (const r of list) {
    const d = dayOf(r.ts);
    if (r.debugPort) seenPort = r.debugPort;
    let consumed = 0;
    let refilled = 0;
    if (prev) {
      refilled = Math.max(0, (r.planRemaining || 0) - (prev.planRemaining || 0));
      consumed = Math.max(0, prev.totalRemaining + refilled - (r.totalRemaining || 0));
      if (refilled > 0) refillDays.push(d);
      const gap = Math.round((toMs(d) - toMs(prev.day)) / 86400000);
      if (gap > maxGap) maxGap = gap;
    }
    const cur = {
      ts: r.ts,
      day: d,
      label,
      accountName: (hit && (hit.accountName || hit.label)) || list.at(-1).name || label,
      planTier: tier,
      via: r.via || "probe",
      planRemaining: r.planRemaining || 0,
      packRemaining: r.packRemaining || 0,
      totalRemaining: r.totalRemaining || 0,
      consumed,
      refilled,
      planQuota: quota,
      nextRefresh: IS_DAY(r.nextRefresh) ? r.nextRefresh : null,
      earliestExpiry: IS_DAY(r.earliestExpiry) ? r.earliestExpiry : null,
    };
    const earlier = lastOfDay.get(d);
    if (earlier) {
      // 同一天多次采集：余量取末次，消耗累加，避免把重复查询画成两次消耗。
      earlier.consumed += consumed;
      earlier.refilled = Math.max(earlier.refilled, refilled);
      Object.assign(earlier, cur, { consumed: earlier.consumed, refilled: earlier.refilled, ts: r.ts });
    } else {
      const row = { ...cur };
      lastOfDay.set(d, row);
      output.push(row);
    }
    prev = cur;
  }

  if (maxGap >= 3) {
    warnings.push(`${label} 最长采集间隔 ${maxGap} 天：区间内的消耗会归到后一次采集日，趋势柱偏高`);
  }
  const days = [...lastOfDay.keys()].sort();
  const last = lastOfDay.get(days.at(-1));
  // 逐包明细取自该号最近一次采集（旧记录没有 packs 就是空数组，前端容错）
  const packs = Array.isArray(list.at(-1).packs) ? list.at(-1).packs : [];
  accountMeta.push({
    label,
    accountName: last.accountName,
    planTier: tier,
    debugPort: seenPort || 9222 + accountMeta.length,
    cycleRefreshDay: last.nextRefresh ? Number(last.nextRefresh.slice(8, 10)) : Number(refillDays.at(-1)?.slice(8, 10) || 1),
    earliestExpiry: last.earliestExpiry || last.nextRefresh || "—",
    planQuota: quota,
    lastDay: last.day,
    lastTotal: last.totalRemaining,
    packs,
    // 今日签到状态：纯只读反推，判据与局限见 scripts/reward-window.mjs。看板不代领。
    reward: judgeReward({ packs, capturedAt: list.at(-1).ts }),
  });
}

const REWARD_TEXT = { claimed: "今日已签", unclaimed: "今日未签", unknown: "无法判断" };

output.sort((a, b) => (a.ts < b.ts ? -1 : a.ts > b.ts ? 1 : 0));

const allDays = [...new Set(output.map((r) => r.day))].sort();
const windowEnd = allDays.at(-1) || dayOf(new Date().toISOString());
const windowStart = allDays.length > DAYS ? allDays[allDays.length - DAYS] : allDays[0] || windowEnd;
const history = output.filter((r) => r.day >= windowStart);
const latest = new Map();
for (const r of history) latest.set(r.label, r);
const below = [...latest.values()].filter((r) => r.totalRemaining < threshold);

const rewardWindow = rewardWindowDay();
const payload = {
  meta: {
    demo: false,
    note: "本机真实采集数据：由 scripts/build-site-data.mjs 从 ~/.qoder-cn/credit-watch/history.jsonl 生成，不含凭证。",
    unit: "credits",
    threshold,
    pluginVersion,
    planQuota: PLAN_QUOTA,
    generatedAt: new Date().toISOString(),
    windowStart,
    windowEnd,
    brand: "credit-watch",
    viewer: null,
    source: "scripts/build-site-data.mjs",
    reward: {
      window: rewardWindow,
      ttlDays: REWARD_TTL_DAYS,
      // 页面拿它判断"这份数据还是不是今天的"：一过明天 0 点，本轮状态必须重新采集才能判
      nextWindowOpenAt: windowOpenIso(addDays(rewardWindow, 1)),
      note: "只读反推：今天签到的奖励必然是一个「今天 + 30 天」到期的活动资源包。签到只能在 Qoder 桌面端点，看板不代领。",
    },
    derived: {
      consumed: "相邻两次采集的余量差值，归到后一次采集所在日（东八区）",
      refilled: "planRemaining 向上跳变视为周期额度刷新，不计入消耗",
      reward: "存在到期日 = 今天 + 30 天的活动资源包即视为今日已签；上次采集不是今天时报无法判断，不去猜「未签」",
    },
    warnings,
  },
  accounts: accountMeta,
  history,
};

mkdirSync(dirname(OUT), { recursive: true });
writeFileSync(OUT, `${JSON.stringify(payload, null, 2)}\n`, "utf8");

console.log(`已写出 ${OUT}`);
// 本地服务抓这行当"完成"提示：路径太长，页面上那行显示不下。
console.log(`[cw-summary] 看板数据已更新：${accountMeta.length} 个账号 · ${history.length} 条记录 · 区间 ${windowStart} 至 ${windowEnd}`);
console.log(`区间 ${windowStart} 至 ${windowEnd} · 记录 ${history.length} 条 · 账号 ${accountMeta.length} 个 · 阈值 ${threshold}`);
for (const a of accountMeta) {
  console.log(`  ${a.label}（${a.accountName}）${a.planTier} 周期额度 ${a.planQuota} · 剩余 ${a.lastTotal} · 末次采集 ${a.lastDay} · ${REWARD_TEXT[a.reward?.status] || "无法判断"}`);
}
const pending = accountMeta.filter((a) => a.reward?.status === "unclaimed");
if (pending.length) console.log(`今日签到：${pending.length} 个号还没签（${pending.map((a) => a.label).join("、")}）——去 Qoder 桌面端点，看板代不了`);
if (below.length) console.log(`低于阈值：${below.map((r) => `${r.label} ${r.totalRemaining}`).join("、")}`);
for (const w of warnings) console.log(`注意：${w}`);
