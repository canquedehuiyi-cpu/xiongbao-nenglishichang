// reward-window.mjs —「每日签到送 100 Credits」活动轮次口径与**只读**判定。
//
// 活动事实（docs.qoder.cn《每日签到送 100 Credits》条款）：
//   · 每天 0 点（UTC+8）刷新签到状态，当天未签到不补签；
//   · 每次签到领取的 100 Credits 单独成一个资源包，有效期 = 领取日 + 30 天；多包并存、最早到期优先扣减；
//   · 入口只有桌面端：客户端右上角签到浮窗，点「签到」即时到账，当天领过按钮置灰。
//
// 本模块只做**反推**：从已经采到的资源包明细判断某个号今天签没签。
// 它不发任何写请求、不代领、不碰那个签到接口——领取动作永远由本人在桌面端完成。
// scripts/build-site-data.mjs（真实数据）与外层 scripts/make-demo-data.mjs（演示数据）共用这一份口径。

export const REWARD_TTL_DAYS = 30; // 条款：资源包有效期 = 领取日 + 30 天

const CN_TZ_OFFSET = 8 * 3600 * 1000;
const IS_DAY = (s) => /^\d{4}-\d{2}-\d{2}$/.test(String(s || ""));

// 归日口径与 probe.mjs 的 day() 一致（Asia/Shanghai），不然到期日会和"今天"差一天
const cnDay = (ms) => new Date(ms + CN_TZ_OFFSET).toISOString().slice(0, 10);
const dayMs = (d) => Date.parse(`${d}T00:00:00+08:00`);

export const addDays = (d, n) => cnDay(dayMs(d) + n * 86400000);
// 签到状态按自然日 0 点刷新，所以"轮次日"就是东八区的今天
export const rewardWindowDay = (at = Date.now()) => cnDay(typeof at === "number" ? at : Date.parse(at));
export const windowOpenIso = (windowDay) => new Date(dayMs(windowDay)).toISOString();

// 来源码是内部标识，页面上不直接摆（前端另有中文映射）；演示数据用的本来就是中文标签，原样放过
const isSourceCode = (s) => String(s || "").startsWith("RESOURCE_PACKAGE_SOURCE_");
const bonusLike = (s) => !isSourceCode(s) || String(s).includes("BONUS");

/**
 * 反推某个号今天签没签。
 *
 * 判据是**到期日 == 今天 + 30 天**，不是余额：包签来就会被消耗，100 会变小
 * （实测过剩 75 的样本），拿 remaining == 100 当判据会把"签了又用了"误报成"没签"。
 *
 * @param {{packs?: Array<{remaining:number,expires:string,source:string}>, capturedAt?: string, at?: number|string}} input
 * @returns {{window:string, asOf:string|null, status:"claimed"|"unclaimed"|"unknown", uncertain:boolean, evidence:object|null, reason:string|null, dueDay:string}}
 */
export function judgeReward({ packs, capturedAt, at = Date.now() } = {}) {
  const nowMs = typeof at === "number" ? at : Date.parse(at);
  const window = rewardWindowDay(Number.isFinite(nowMs) ? nowMs : Date.now());
  const dueDay = addDays(window, REWARD_TTL_DAYS); // 今天签的包，到期日就该是这天
  const asOfMs = capturedAt ? Date.parse(capturedAt) : NaN;
  const base = { window, asOf: Number.isFinite(asOfMs) ? new Date(asOfMs).toISOString() : null, dueDay };

  if (!Array.isArray(packs) || !packs.length) {
    return { ...base, status: "unknown", uncertain: false, evidence: null, reason: "这次采集里没有资源包明细：记录太旧，或该号当前一个资源包都没有" };
  }
  // 采集发生在今天 0 点之前：今天签没签都还没被采到。这时必须报"无法判断"，
  // 报"没签"会天天误报，让人白切一趟号。
  if (Number.isFinite(asOfMs) && cnDay(asOfMs) !== window) {
    return { ...base, status: "unknown", uncertain: false, evidence: null, reason: `上次采集不是今天的（${cnDay(asOfMs)}），今天签没签还没采到` };
  }

  const hits = packs.filter((p) => p && IS_DAY(p.expires) && p.expires === dueDay);
  if (!hits.length) {
    return { ...base, status: "unclaimed", uncertain: false, evidence: null, reason: null };
  }
  const pick = hits.find((p) => bonusLike(p.source)) || hits[0];
  return {
    ...base,
    status: "claimed",
    // 命中的包一个都不是活动赠送来源：可能是加购包恰好今天到期，只能算疑似
    uncertain: !hits.some((p) => bonusLike(p.source)),
    evidence: { expires: pick.expires, remaining: Number(pick.remaining) || 0, source: String(pick.source || "") },
    reason: null,
  };
}
