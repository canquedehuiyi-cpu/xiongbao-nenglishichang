// generate.mjs — 共享编排：转录 → 报告 → 落盘（report.json + canvas.tsx）。
// CLI 与 Stop 钩子都走这里，避免逻辑重复。

import { readFileSync, existsSync } from 'node:fs';
import { readEntries, resolveCwd, resolveSessionId } from './transcript.mjs';
import { buildReport, summarizeCompactions, AVAIL } from './breakdown.mjs';
import { loadProxyUsage } from './proxylog.mjs';
import { loadConfig, readConfigRaw, isValidUpstream, readStatus, selfCmd, readRequestLogTail, summarizeRequests } from '../proxy.mjs';
import { defaultOutDir, reportJsonPath, overridePath, sessionFileBase, atomicWriteFile } from './paths.mjs';
import { renderCanvasToFile } from './render-canvas.mjs';
import { summarizeSubagents } from './subagents.mjs';

/** 插件版本（读自 .qoder-plugin/plugin.json —— 版本唯一真值），写入报告以便区分产物由哪个版本生成；读取失败则 null。 */
const PLUGIN_VERSION = (() => {
  try {
    const manifest = JSON.parse(readFileSync(new URL('../../.qoder-plugin/plugin.json', import.meta.url), 'utf8'));
    return typeof manifest.version === 'string' ? manifest.version : null;
  } catch {
    return null;
  }
})();

/**
 * 官方 UI 真值回填：IDE 端转录不含 usage，本地怎么算都是 0，故留一个手工录入通道。
 * 文件位置 `<outDir>\overrides\<sessionId>.json`，字段全部可选：
 *   { credits, originalCredits, model, startedAt, endedAt, durationMin, note,
 *     contextWindow, userContextLimit }
 * contextWindow：手工锁定模型窗口（如 qwen3-max=1000000），优先于 runtime-config / 反推 / fallback；
 *   避免每场都从 usage 反推，也避免 runtime-config=null 时回退 200K 把绝对值系统性缩小 5×。
 * userContextLimit：手工指定 Qoder 压缩触发阈值（默认 200000），驱动 peakUserAdvice。
 * 读不到 / 写坏了都返回 null（本函数也跑在 Stop 钩子链路里，不能抛）。
 */
function loadManualOverride(dir, sessionId) {
  if (!dir || !sessionId) return null;
  const file = overridePath(dir, sessionId);
  try {
    if (!existsSync(file)) return null;
    // 去 BOM：这个文件是用户手写的，PowerShell `Set-Content -Encoding UTF8` 与记事本都会加 BOM，
    // 不去会让 JSON.parse 抛错、静默降级成「没填」，用户看不出手工真值为何不生效。
    const raw = JSON.parse(readFileSync(file, 'utf8').replace(/^\uFEFF/, ''));
    if (!raw || typeof raw !== 'object') return null;
    const m = {
      file,
      credits: null,
      originalCredits: null,
      model: null,
      startedAt: null,
      endedAt: null,
      durationMin: null,
      note: null,
      contextWindow: null,
      userContextLimit: null,
    };
    for (const k of ['credits', 'originalCredits', 'durationMin']) {
      if (typeof raw[k] === 'number' && isFinite(raw[k])) m[k] = Number(raw[k].toFixed(3));
    }
    // 窗口与阈值：正整数才采纳（避免 0 / 负数 / 小数把后续除法弄坏）。
    for (const k of ['contextWindow', 'userContextLimit']) {
      if (typeof raw[k] === 'number' && Number.isFinite(raw[k]) && raw[k] > 0) m[k] = Math.round(raw[k]);
    }
    for (const k of ['model', 'startedAt', 'endedAt', 'note']) {
      if (typeof raw[k] === 'string' && raw[k].trim()) m[k] = raw[k].trim();
    }
    const empty =
      m.credits == null && m.originalCredits == null && m.durationMin == null &&
      m.contextWindow == null && m.userContextLimit == null &&
      !m.model && !m.startedAt && !m.endedAt && !m.note;
    return empty ? null : m;
  } catch {
    return null;
  }
}

/**
 * 把手工真值挂到 report.manual，并改写受影响的 availability 与 model。
 * 红线：**绝不覆盖 report.totals**。手工数字一旦冒充本地实测，下次重算就对不上账；
 * 两者并列展示，并算出 localCoverage（本地值 ÷ 官方真值）供对账。
 * 对账口径：官方 UI 的一场会话扣费 = 主链 + 各子代理，故有子代理时拿 combined 比，
 * 否则覆盖率会被系统性低估（实测：ca2f7834 用主链比得 0.46、用 combined 比得 0.89）。
 * 因此本函数必须在 report.subagents 汇总完之后调用。
 */
function applyManual(report, m) {
  if (m.model && !report.session.model) {
    report.session.model = m.model;
    report.session.modelSource = 'manual';
    report.availability.model = AVAIL.MANUAL;
  }
  if (m.credits != null) {
    report.availability.credits = AVAIL.MANUAL;
    const sub = report.subagents;
    const useCombined = !!(sub && sub.count > 0);
    const local = useCombined ? sub.combined.credits : report.totals.credits;
    m.localScope = useCombined ? 'combined' : 'main';
    m.localCredits = local;
    m.localCoverage = local > 0 ? Number((local / m.credits).toFixed(4)) : null;
  }
}

/**
 * status.json 里的失败记录是否已被更新的证据推翻。
 * status.json 只记「最近一次自动拉起的结果」，且失败后不会被后续成功清理：用户重启代理、
 * 或钩子下次拉起成功之前，那条陈旧记录会一直让报告渲染「代理自动启动失败，自定义模型将无法
 * 对话」的红字——而同一份报告里的 lastRecordAt / matched 明明证明代理在跑。红字误报比不提示更坏：
 * 它把用户推去改本来正确的 Base URL，越修越坏。
 * 判据只认时间序：代理在失败记录之后还记到了流量，说明这条失败已不代表当前状态。
 * @param {{at?:string|null}|null} status status.json 里的失败记录
 * @param {string|null} lastRecordAt 代理 usage 日志里最近一条记录的时间
 */
export function statusSuperseded(status, lastRecordAt) {
  if (!status || !lastRecordAt) return false;
  if (!status.at) return true; // 没有时刻可比，而流量是硬证据：以流量为准
  const a = Date.parse(status.at);
  const b = Date.parse(lastRecordAt);
  if (!Number.isFinite(a) || !Number.isFinite(b)) return false;
  return b > a;
}

/**
 * 给压缩明细补供应商实测口径（prompt/completion/cached/耗时）。
 * 压缩那笔调用不在转录里（没有 message.id 可 join），只能按「完成时刻 ≈ 边界时刻 + 规模吻合」
 * 在代理 usage 记录里找。三个判据同时成立、且候选唯一才算命中，否则留 null 让渲染端显示「—」：
 * 宁可缺一格，也不能给一个对不上号的数字冒充实测。
 * 时间窗能把它与「压缩前的最后一笔正常请求」分开——那笔的 prompt 也接近 preTokens，
 * 但它在边界前 145–190s 就结束了（压缩耗时），落在窗外。
 * @param {object[]} events report.compactionCost.items
 * @param {Iterable<object>} usageRecords 代理 usage 记录（含未 join 上转录的那些）
 * @param {Map<string,object>} reqById 请求诊断记录按 id 索引，仅用于取 ms
 */
export function matchCompactionProxy(events, usageRecords, reqById) {
  const recs = [...usageRecords];
  for (const ev of events) {
    if (!ev || ev.proxy || !ev.at || ev.preTokens == null || ev.postTokens == null) continue;
    const at = Date.parse(ev.at);
    if (!Number.isFinite(at)) continue;
    const hits = recs.filter((rec) => {
      const ts = Date.parse(rec?.ts);
      if (!Number.isFinite(ts) || Math.abs(ts - at) > 20000) return false;
      if (!Number.isFinite(rec.promptTokens) || !Number.isFinite(rec.completionTokens)) return false;
      const p = rec.promptTokens / ev.preTokens;
      if (p < 0.7 || p > 1.6) return false;
      const q = rec.completionTokens / ev.postTokens;
      return q >= 0.5 && q <= 2.5;
    });
    if (hits.length !== 1) continue;
    const rec = hits[0];
    const meta = (reqById && reqById.get(rec.id)) || null;
    ev.proxy = {
      promptTokens: rec.promptTokens,
      completionTokens: rec.completionTokens,
      cachedTokens: Number.isFinite(rec.cachedTokens) ? rec.cachedTokens : null,
      ms: meta && Number.isFinite(meta.ms) ? meta.ms : null,
      matchedBy: 'time+size',
    };
  }
}

/**
 * 生成并落盘一次报告。
 * @param {object} p
 * @param {string} p.transcript 转录 .jsonl 路径
 * @param {string} [p.sessionId]
 * @param {string} [p.cwd] 工作目录（决定默认输出目录）
 * @param {string} [p.outDir] 显式输出目录
 * @param {string} [p.overridesDir] 官方 UI 真值回填目录（默认 <outDir>\overrides）
 * @param {boolean} [p.canvas=true] 是否渲染 .canvas.tsx
 * @returns {{report:object, outDir:string, reportJson:string, canvas:string|null, canvasName:string}}
 */
export function generateReport({ transcript, sessionId, cwd, outDir, overridesDir, canvas = true, proxyLog }) {
  const entries = readEntries(transcript);
  // ManualTruth 必须前置加载：contextWindow 会改变 S = ratio×window 的结果，若在 buildReport
  // 之后才覆盖，totals.billedInputTokens 会与 contextWindow 不一致（手工真值冒充实测、下次重算对不上账）。
  // 前置需要先知道 sessionId 与输出目录：从 entries 里先推一把（buildReport 里会再推一次，结果相同）。
  const preSessionId = sessionId || resolveSessionId(entries);
  const preCwd = cwd || resolveCwd(entries);
  const preDir = outDir || defaultOutDir(preCwd || process.cwd());
  const manual = loadManualOverride(overridesDir || preDir, preSessionId);
  // 代理 usage 索引：自定义模型（BYOK）转录无 message.usage 时的唯一本地真值来源。
  // loadProxyUsage 自身不抛；日志不存在时 map 为空，报告退回原「无 usage」口径。
  const proxyIdx = loadProxyUsage(proxyLog);
  // 用户压缩阈值来源优先级：manual（overrides 手写）> config（~/.qoder-credits-proxy/config.json）> default（内置 200K）。
  // 来源随值一起写进报告，渲染端标「·手工/·配置/·默认」，用户才知道这个阈值能不能信、去哪改。
  const cfgForLimit = loadConfig();
  const cfgUserLimit = Number.isFinite(cfgForLimit.userContextLimit) && cfgForLimit.userContextLimit > 0 ? Math.round(cfgForLimit.userContextLimit) : null;
  const resolvedUserLimit = manual?.userContextLimit ?? cfgUserLimit ?? undefined;
  const resolvedUserLimitSource = manual?.userContextLimit != null ? 'manual' : cfgUserLimit != null ? 'config' : 'default';
  const report = buildReport(entries, {
    sessionId: preSessionId,
    cwd: preCwd,
    proxyUsage: proxyIdx.map,
    contextWindow: manual?.contextWindow ?? undefined,
    userContextLimit: resolvedUserLimit,
    userContextLimitSource: resolvedUserLimitSource,
  });
  report.pluginVersion = PLUGIN_VERSION;
  // 代理配置/状态：供报告端提示「休眠」（已配置但长期无流量，多半已改回官方模型）与「启动失败」。
  // 全部只读、绝不抛——本函数跑在 Stop 钩子链路里。
  const rawCfg = readConfigRaw();
  const cfg = cfgForLimit;
  const status = readStatus();
  let lastRecordAt = null;
  for (const rec of proxyIdx.map.values()) {
    if (rec && typeof rec.ts === 'string' && (!lastRecordAt || rec.ts > lastRecordAt)) lastRecordAt = rec.ts;
  }
  const configured = !!(rawCfg && isValidUpstream(cfg.upstream));
  const enabled = cfg.enabled !== false;
  const dormant = configured && enabled && (lastRecordAt == null || Date.now() - Date.parse(lastRecordAt) > 14 * 864e5);
  const failedStatus =
    status && status.ok === false
      ? { error: status.error || 'unknown', port: status.port ?? cfg.port, at: status.at ?? null }
      : null;
  // 失败记录照原样留在报告里（那是历史事实），但另标「已被更新的流量推翻」——
  // 渲染端据此决定还报不报红字。
  const superseded = statusSuperseded(failedStatus, lastRecordAt);
  report.proxy = {
    ...report.proxy,
    logPath: proxyIdx.logPath,
    logExists: proxyIdx.exists,
    logRecords: proxyIdx.records,
    configured,
    enabled,
    port: cfg.port,
    lastRecordAt,
    dormant,
    status: failedStatus,
    statusSuperseded: superseded,
  };
  // 报告里出现的每条命令都用插件自定位的入口：模板是静态文本，拿不到 selfCmd()，
  // 此前只能硬编码 `node scripts/cli.mjs`——没装 Node 的用户既跑不了 node，也不知道
  // scripts/cli.mjs 相对谁，等于把「傻瓜式」的口子开在告警文案里。
  report.selfCmd = selfCmd();
  // 链路健康度：逐笔归因是排障工具、不是 token 解析，明细留在 CLI（--request-log），
  // 报告只回答一句「这条链路当前干不干净」。
  const reqTail = readRequestLogTail(cfg);
  const rs = reqTail.length ? summarizeRequests(reqTail) : null;
  report.linkHealth = {
    matched: report.proxy.matched,
    requests: report.proxy.requests,
    coverage: report.proxy.requests > 0 ? report.proxy.matched / report.proxy.requests : 0,
    usageSource: report.usageSource,
    // 三档拆分：代理实测 / 转录 input_tokens / 转录 ratio×window。让报告一眼看出各源占比，
    // 尤其当 usageSource='mixed' 时能定位是哪几笔走了推导。
    breakdown: report.proxy.breakdown,
    logRecords: proxyIdx.records,
    lastRecordAt,
    recentRequests: reqTail.length,
    proxyErrors: rs ? rs.proxyError : null,
    clientAbort: rs ? rs.clientAbort : null,
    clientAbortMaxMs: rs ? rs.clientAbortMaxMs : null,
    upstreamRejected: rs ? rs.upstreamRejected : null,
    aborted: rs ? rs.aborted : null,
    truncated: rs ? rs.truncated : null,
    noUsage: rs ? rs.noUsage : null,
    slowestMs: rs && rs.slowest ? rs.slowest.ms : null,
    supersededFailure: superseded ? failedStatus : null,
  };
  const reqById = new Map();
  for (const rec of reqTail) {
    if (rec && typeof rec.id === 'string' && rec.id) reqById.set(rec.id, rec);
  }
  matchCompactionProxy(report.compactionCost.items, proxyIdx.map.values(), reqById);
  // 有笔拿到了供应商实测，合计就得跟着换口径重算，否则明细行是实测、合计还是客户端自估。
  report.compactionCost.totals = summarizeCompactions(report.compactionCost.items);
  const dir = preDir;

  // 子代理账：Agent 派发的子代理消耗只落在各自独立转录，不计入主链，故单独汇总后挂在
  // report.subagents（totals = 子代理合计，combined = 主链 + 子代理，对齐官方 UI 的一场会话扣费）。
  // 包 try/catch：本函数也跑在 Stop 钩子链路里，抛异常会让钩子非 0 退出而阻断对话。
  try {
    report.subagents = summarizeSubagents(transcript, report, proxyIdx.map);
  } catch {
    const t = report.totals;
    report.subagents = {
      scanned: false,
      dir: null,
      probedPaths: [],
      reason: 'error',
      count: 0,
      items: [],
      totals: { roundTrips: 0, billedInputTokens: 0, credits: 0, originalCredits: 0 },
      combined: {
        roundTrips: report.session.roundTrips,
        billedInputTokens: t.billedInputTokens,
        credits: t.credits,
        originalCredits: t.originalCredits,
      },
    };
  }
  // 手工真值在子代理汇总之后才挂：localCoverage 要拿 combined（主链 + 子代理）跟官方 UI 对账。
  // contextWindow / userContextLimit 已在 buildReport 前置注入，applyManual 不再回改。
  report.manual = manual;
  if (manual) applyManual(report, manual);
  const base = sessionFileBase(report.session.id, report.session.title);
  const canvasName = `${base}.canvas.tsx`;
  report.artifacts = { report: 'report.json', canvas: canvasName };
  const reportJson = atomicWriteFile(reportJsonPath(dir), JSON.stringify(report, null, 2));
  const canvasOut = canvas ? renderCanvasToFile(report, dir, base) : null;
  return { report, outDir: dir, reportJson, canvas: canvasOut, canvasName };
}
