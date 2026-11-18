// breakdown.mjs — 链式重建：把转录还原为“每次请求的真实上下文”，并按块比例分摊。
//
// 度量模型（已由黄金样本验证）：
//  1. 一次请求(round-trip) = 一个 assistant message.id（其最后一个 entry 带 usage）。
//     实测 804 个 message.id ↔ 804 次请求，每个恰有一个 usage。
//  2. 每次请求的真实输入规模 S_r = context_usage_ratio × contextWindow（权威真值，
//     token 子字段被置零，但 ratio 是真实的；段内严格单调、压缩后锯齿重置）。
//  3. 计费输入总量 = Σ S_r（无需估算）。
//  4. 分摊：请求 r 的输入上下文 = 系统提示词(不可见) + 当时“存活”的可见块。
//     - 系统提示词规模 Esys 在首个请求处自校准：Esys = max(0, S_1 − Σ可见块估算)。
//     - effSys = min(Esys, S_r) 记入 system；余下 pool = S_r − effSys 按各可见块
//       估算规模“比例分摊”。因每请求比例和为 1，故 Σ_attr billed = Σ_r S_r 精确成立(恒等式 A1)。
//  5. 压缩边界(system/compact_boundary)：清空存活块，置入“压缩摘要”块(est=postTokens 真值)。
//
// 关键顺序：请求自身的输出块(thinking/text/tool_use)不计入本次请求的输入，
// 而是在本次分摊完成后再进入存活集，供下一次请求消费。
//
// 兼容两代客户端：桌面端富转录有 usage 真值，IDE 端精简转录没有（见 transcript.mjs 头注释）。
// 故报告除数字外还带 source（哪一代客户端）与 availability（逐项标 measured / derived /
// fallback / unavailable），呈现层据此决定显示数值、「≈」还是「—」——否则 IDE 端的全 0
// 报告与桌面端的真值报告在 Canvas 上长得一模一样，还有几处会主动说谎（压缩 0 次、A1 通过）。

import { estimateTokens, blockText } from './tokens.mjs';
import {
  isAssistant,
  isUser,
  isAttachment,
  isCompactBoundary,
  isRequest,
  messageId,
  contentBlocks,
  resolveContextWindowInfo,
  resolveSource,
  SOURCE_DESKTOP,
  resolveModel,
  resolveCwd,
  resolveSessionId,
  resolveCustomTitle,
  resolveTitleFromFirstUser,
  resolveTimeRange,
  usageHasRealTokens,
} from './transcript.mjs';
import {
  CAT,
  CATEGORY_ORDER,
  CATEGORY_LABEL,
  assistantBlockInfo,
  toolResultInfo,
  fileLabel,
} from './attrib.mjs';

/**
 * 逐项可用性取值：随每个指标一起写进 report.availability。
 * 呈现层据此决定显示数值、加「≈」、还是显示「—」。
 */
export const AVAIL = {
  MEASURED: 'measured', // 客户端上报的真值
  DERIVED: 'derived', // 由真值推导（如 ratio × contextWindow、比例分摊）
  FALLBACK: 'fallback', // 读不到，用了回退默认值
  MANUAL: 'manual', // 本地没有，由 overrides\<sessionId>.json 从官方 UI 手工回填
  UNAVAILABLE: 'unavailable', // 本地数据源里根本没有，0 不代表没发生
};

/**
 * 峰值上下文占用 → 「该不该压」的结论。阈值取自仓库根实测账
 * `上下文压缩成本与阈值-实测账.md`：盈亏线 = 窗口的 39%（省下 P−F 要盖过摘要 S + 重读 F），
 * 性价比区间 65–85%，过 85% 越贴窗口越容易被自动压缩抢在最糟时机触发。
 * 结论算在这里、写进报告，渲染端只管展示——否则 Canvas 与终端各持一套阈值迟早走偏。
 * @param {number} ratio 峰值占比（peakContextTokens / contextWindow）
 * @returns {{level:string, tone:string, text:string}|null} 无有效占比时 null（渲染端整段不显示）
 */
export function peakAdvice(ratio) {
  if (!Number.isFinite(ratio) || ratio <= 0) return null;
  if (ratio > 1) {
    return {
      level: 'over',
      tone: 'danger',
      text: '已经超过上下文窗口本身，随时可能被截断或由客户端在最糟的时机自动压缩，立刻手动压一次',
    };
  }
  if (ratio > 0.85) {
    return {
      level: 'high',
      tone: 'warning',
      text: '已过 85%。再往上越贴窗口，越容易被自动压缩抢在你之前触发（实测失败样本都集中在这一档），建议尽快手动压',
    };
  }
  if (ratio >= 0.65) {
    return {
      level: 'sweet',
      tone: 'success',
      text: '正处性价比区间（65–85%）。此时压一次每轮省得最多，且第一轮就回本',
    };
  }
  if (ratio >= 0.39) {
    return {
      level: 'mid',
      tone: 'info',
      text: '已过盈亏线（39%）但还没进性价比区间，压缩有净收益但不大；不急着压',
    };
  }
  return {
    level: 'low',
    tone: 'info',
    text: '低于盈亏线（39%）。此时压缩在 token 上是亏的：省下的还不够付摘要输出加压缩后重读，别压',
  };
}

/**
 * 压缩明细的口径归一 + 合计。
 * 每笔的「输入 / 摘要输出」优先用代理实测值（供应商真值），没有就用客户端写在压缩边界里的
 * 自估规模，并把生效值写回 effective* 字段——渲染端直接取它，不必再自己判分支，
 * 也就不会出现「明细行是实测、合计却是自估」这种同表两套数。
 * 「省下」一律以压缩后首轮的实测输入为地板，而不是摘要大小（实测地板 30–44K 基本恒定）。
 * generate.mjs 在回填 proxy 之后会再调一次，故合计始终跟随明细口径。
 * @param {object[]} items compactionCost.items
 * @returns {{preTokens:number, postTokens:number, savedTokens:number, measured:number}}
 */
export function summarizeCompactions(items) {
  const totals = { preTokens: 0, postTokens: 0, savedTokens: 0, measured: 0 };
  for (const ev of items) {
    const inp = ev.proxy ? ev.proxy.promptTokens : ev.preTokens;
    const outp = ev.proxy ? ev.proxy.completionTokens : ev.postTokens;
    ev.effectiveInputTokens = inp == null ? null : inp;
    ev.effectiveOutputTokens = outp == null ? null : outp;
    ev.savedTokens = inp != null && ev.nextInputTokens != null ? inp - ev.nextInputTokens : null;
    totals.preTokens += inp == null ? 0 : inp;
    totals.postTokens += outp == null ? 0 : outp;
    totals.savedTokens += ev.savedTokens == null ? 0 : ev.savedTokens;
    if (ev.proxy) totals.measured++;
  }
  return totals;
}

/**
 * 由转录 entry 构建报告数据对象（纯函数，不做 I/O）。
 * @param {any[]} entries 已解析的转录 entry
 * @param {object} [opts]
 * @param {number} [opts.contextWindow] 手工指定窗口（ManualTruth），优先于 runtime-config / 反推 / fallback
 * @param {number} [opts.userContextLimit] 用户压缩阈值（默认 200000），与模型窗口独立；ManualTruth 可覆盖
 * @param {string} [opts.sessionId]
 * @param {string} [opts.cwd]
 * @param {Map<string,object>} [opts.proxyUsage] 代理日志索引 Map<message.id, {promptTokens, completionTokens,…}>（lib/proxylog.mjs）
 *
 * 真值优先级（每项独立选源）：
 *   S_r：proxy.promptTokens > usage.input_tokens > usage.context_usage_ratio × contextWindow
 *   outputTokens：proxy.completionTokens > usage.output_tokens
 *   cachedTokens：proxy.cachedTokens > usage.cache_read_input_tokens
 * 理由：代理与转录 usage 同源（均来自供应商响应），实测一致；代理略硬（落盘时机更早、
 * 字段更全），转录兜底（代理未启动时仍可用）；ratio×window 仅在前两者都缺时使用。
 */
export function buildReport(entries, opts = {}) {
  // 上下文窗口：ManualTruth 显式指定赢（source='manual'）→ runtime-config → 从 usage 反推 → fallback。
  // 报告里每个 token 数字都要乘它，故回退时必须能区分。
  const cwInfo = Number.isFinite(opts.contextWindow) && opts.contextWindow > 0
    ? { contextWindow: opts.contextWindow, source: 'manual' }
    : resolveContextWindowInfo(entries);
  const contextWindow = cwInfo.contextWindow;
  // 用户压缩阈值：Qoder 里用户可设「上下文限制 200K」作为压缩触发点，与模型 max window 不是一回事。
  // 当前 peakAdvice 只看 ratio（对模型窗口），BYOK 下模型窗口 1M、ratio 0.19 会判为 low，
  // 但实际已用掉用户阈值的 95%、马上要触发压缩——这个关键信号必须双轨展示。
  const hasUserLimitOpt = Number.isFinite(opts.userContextLimit) && opts.userContextLimit > 0;
  const userContextLimit = hasUserLimitOpt ? opts.userContextLimit : 200000;
  // 来源由调用方（generate.mjs）按 manual > config > default 优先级判定后传入；未传时按有无值兜底。
  // 报表里要把「这个 200K 是哪来的」标出来，用户才能判断该不该信、去哪改。
  const userContextLimitSource = typeof opts.userContextLimitSource === 'string' && opts.userContextLimitSource
    ? opts.userContextLimitSource
    : hasUserLimitOpt ? 'manual' : 'default';
  // 代理 usage 索引（可为 null）：只认 Map，其他形状静默忽略（钩子链路不能抛）。
  const proxyUsage = opts.proxyUsage instanceof Map && opts.proxyUsage.size > 0 ? opts.proxyUsage : null;
  const model = resolveModel(entries);
  const cwd = opts.cwd || resolveCwd(entries);
  const sessionId = opts.sessionId || resolveSessionId(entries);
  // 转录来自哪一代客户端。
  const source = resolveSource(entries);
  // 标题：优先用重命名后的 custom-title；新会话尚无此条目时，从首条用户提问派生（避免文件名回退为 session-<id8>）。
  const customTitle = resolveCustomTitle(entries);
  const derivedTitle = customTitle ? null : resolveTitleFromFirstUser(entries);
  const title = customTitle || derivedTitle;
  // 标题来源写进报告，令产物文件名可解释：IDE 端无 custom-title，全靠首问派生。
  const titleSource = customTitle ? 'custom-title' : derivedTitle ? 'first-user' : 'session-id';
  const { startedAt, endedAt } = resolveTimeRange(entries);

  // tool_use 索引：用于 tool_result 通过 tool_use_id 回填工具名与文件路径（实测配对率 100%）。
  const toolUseById = new Map();
  for (const e of entries) {
    if (!isAssistant(e)) continue;
    for (const b of contentBlocks(e)) {
      if (b?.type === 'tool_use' && b.id) toolUseById.set(b.id, b);
    }
  }

  // 存活可见块与其估算规模总和（增量维护，避免每请求 O(n) 重算）。
  let alive = [];
  let aliveEstSum = 0;
  const pushAlive = (blk) => {
    alive.push(blk);
    aliveEstSum += blk.est;
  };

  // 当前正在累积的 assistant 响应（按 message.id 归组）。
  let curMsg = null;

  // 逐请求（round-trip）序列：供“每一次”栏目展示（顶部四项是会话累计口径）。
  const requests = [];
  let pendingCompact = false; // 上一次压缩后、下一次请求前为 true，用于标注锯齿重置点

  let Esys = null; // 系统提示词规模，首请求处自校准
  let reqCount = 0;
  let compactions = 0;
  let userTurns = 0;
  let totalS = 0; // Σ S_r（真实计费输入）
  let totalCredits = 0;
  let totalOriginalCredits = 0;
  // 三档真值来源计数：代理实测 / 转录 input_tokens / 转录 ratio×window。
  // 旧语义：transcriptHits 一个计数器包干两种转录路径，无法区分「真值」与「推导」。
  let proxyHits = 0;
  let transcriptTokenHits = 0;
  let transcriptRatioHits = 0;
  let ratioMeasuredHits = 0; // usage 里带 ratio 真值的往返数（不论 S 选了哪源）
  let totalOutputTokens = 0; // 代理或转录任一有真值即累加
  let totalCachedTokens = 0; // 同上：供应商上下文缓存命中的那部分 prompt
  let cachedTrips = 0; // 带非零 cachedTokens 的往返数
  // credits 覆盖范围：混合会话里只有转录路径的往返可能带 credits，而 credits 总量与
  // 计费输入总量并排展示时会被当成「单价 = 总额 ÷ 全量输入」读，故必须记下分子是哪几笔。
  let creditsTrips = 0; // 真正累加进 totalCredits 的往返数
  let creditsTokens = 0; // 这些往返的计费输入之和
  let lastS = 0; // 最近一次请求的上下文规模
  let peakS = 0; // 本场历史峰值上下文规模（跨压缩，只增不减）
  let peakWinS = 0; // 当前窗口峰值：自最近一次压缩起算，压缩边界处归零重新累积
  const compactEvents = []; // 每次压缩一笔：客户端自估的前后规模 + 压缩后首轮实测

  const catBilled = new Map(); // cat -> tokens
  const attrBilled = new Map(); // attrKey -> tokens
  const toolAgg = new Map(); // tool -> { tokens, calls }
  const fileAgg = new Map(); // file -> { file, kind, tool, billed, estSingle, reads, trips }
  const catDetail = new Map(); // `${cat}\u0001${tool}\u0001${file}` -> { cat, tool, file, kind, tokens, trips }（类别→工具→文件三级下钻）

  const addCat = (k, v) => catBilled.set(k, (catBilled.get(k) || 0) + v);
  const addAttr = (k, v) => attrBilled.set(k, (attrBilled.get(k) || 0) + v);

  function ensureFile(file, kind, tool) {
    let rec = fileAgg.get(file);
    if (!rec) {
      rec = { file, kind: kind || 'other', tool: tool || null, billed: 0, estSingle: 0, reads: 0, trips: 0 };
      fileAgg.set(file, rec);
    }
    if (tool && !rec.tool) rec.tool = tool;
    return rec;
  }

  // 结算当前累积的 assistant 响应。
  function flushMsg() {
    if (!curMsg) return;
    const msg = curMsg;
    curMsg = null;

    // 真值三源优先级（每项独立选）：代理 > 转录 input_tokens > ratio × window。
    // 旧判据 hasTranscriptUsage = ratio>0 一旦命中就短路 proxy join，导致 BYOK 下
    // contextWindow=null、fallback 200K 时 S 被算成 ratio×200K（远小于真值）。
    const u = msg.usage || null;
    const proxyRec = proxyUsage && msg.id ? proxyUsage.get(msg.id) || null : null;
    const hasProxyPrompt = !!(proxyRec && Number.isFinite(proxyRec.promptTokens));
    const hasTranscriptTokens = usageHasRealTokens(u);
    const hasTranscriptRatio = !!(u && Number.isFinite(u.context_usage_ratio) && u.context_usage_ratio > 0);

    let S = null;
    let perReqSource = null; // 'proxy' | 'transcript-tokens' | 'transcript-ratio'
    if (hasProxyPrompt) {
      S = proxyRec.promptTokens;
      perReqSource = 'proxy';
    } else if (hasTranscriptTokens) {
      S = u.input_tokens;
      perReqSource = 'transcript-tokens';
    } else if (hasTranscriptRatio) {
      S = u.context_usage_ratio * contextWindow;
      perReqSource = 'transcript-ratio';
    }

    if (S != null) {
      // —— 这是一次请求：先按“分摊前”的存活集分配 S_r ——
      // ratio 展示口径：转录里带了就用真值，否则以 S/contextWindow 反算（代理路径）。
      const ratio = hasTranscriptRatio ? u.context_usage_ratio : contextWindow > 0 ? S / contextWindow : 0;
      if (hasTranscriptRatio) ratioMeasuredHits++;
      if (perReqSource === 'proxy') proxyHits++;
      else if (perReqSource === 'transcript-tokens') transcriptTokenHits++;
      else transcriptRatioHits++;
      reqCount++;
      totalS += S;
      lastS = S;
      if (S > peakS) peakS = S;
      if (S > peakWinS) peakWinS = S;
      // credits 只可能在转录 usage 里（代理不写 credits）；不论 S 走哪源都试一下。
      if (u && typeof u.credits === 'number') {
        totalCredits += u.credits;
        creditsTrips++;
        creditsTokens += S;
      }
      if (u && typeof u.original_credits === 'number') totalOriginalCredits += u.original_credits;

      // outputTokens 二源：proxy.completionTokens > usage.output_tokens（两者都没则 null，不写 0）。
      let outTok = null;
      if (proxyRec && Number.isFinite(proxyRec.completionTokens)) outTok = proxyRec.completionTokens;
      else if (u && Number.isFinite(u.output_tokens) && u.output_tokens > 0) outTok = u.output_tokens;
      if (outTok != null) totalOutputTokens += outTok;

      // cachedTokens 二源：proxy.cachedTokens > usage.cache_read_input_tokens。
      let cached = null;
      if (proxyRec && Number.isFinite(proxyRec.cachedTokens)) cached = proxyRec.cachedTokens;
      else if (u && Number.isFinite(u.cache_read_input_tokens) && u.cache_read_input_tokens > 0) cached = u.cache_read_input_tokens;
      if (cached != null && cached > 0) {
        totalCachedTokens += cached;
        cachedTrips++;
      }

      requests.push({
        index: reqCount,
        time: fmtTime(msg.usageAt || msg.lastAt),
        ratio: Number(ratio.toFixed(6)),
        inputTokens: Math.round(S),
        outputTokens: outTok,
        usageSource: perReqSource,
        credits: u && typeof u.credits === 'number' ? Number(u.credits.toFixed(3)) : 0,
        originalCredits: u && typeof u.original_credits === 'number' ? Number(u.original_credits.toFixed(3)) : 0,
        afterCompact: pendingCompact,
      });
      // 压缩后首轮的输入规模就是「压缩把上下文压到了多低」的实测地板，回填给该次压缩事件。
      if (pendingCompact && compactEvents.length > 0) {
        const ev = compactEvents[compactEvents.length - 1];
        if (ev.nextInputTokens == null) {
          ev.nextRequestIndex = reqCount;
          ev.nextInputTokens = Math.round(S);
        }
      }
      pendingCompact = false;

      if (Esys == null) Esys = Math.max(0, Math.round(S - aliveEstSum)); // 首请求自校准
      const effSys = Math.min(Esys, S);
      addCat(CAT.SYSTEM, effSys);
      addAttr('system', effSys);

      const pool = S - effSys;
      if (pool > 0) {
        if (aliveEstSum > 0) {
          for (const b of alive) {
            const share = pool * (b.est / aliveEstSum);
            addCat(b.cat, share);
            addAttr(b.attrKey, share);
            // 类别下钻：把同一份 share 记到 (类别, 工具, 文件) 三级键上。
            const dkey = b.cat + '\u0001' + (b.tool || '') + '\u0001' + (b.file || '');
            let d = catDetail.get(dkey);
            if (!d) { d = { cat: b.cat, tool: b.tool || null, file: b.file || null, kind: b.kind || null, tokens: 0, trips: 0 }; catDetail.set(dkey, d); }
            d.tokens += share;
            d.trips += 1;
            if (b.tool) {
              let t = toolAgg.get(b.tool);
              if (!t) { t = { tokens: 0, calls: 0 }; toolAgg.set(b.tool, t); }
              t.tokens += share;
            }
            if (b.file) {
              const rec = ensureFile(b.file, b.kind, b.tool);
              rec.billed += share;
              rec.trips += 1;
            }
          }
        } else {
          // 无可见块（理论上不发生于首请求之后）：余量并入 system。
          addCat(CAT.SYSTEM, pool);
          addAttr('system', pool);
        }
      }
    }

    // —— 请求自身输出块进入存活集，供后续请求消费 ——
    for (const blk of msg.blocks) pushAlive(blk);
  }

  for (const e of entries) {
    if (isAssistant(e)) {
      const id = messageId(e);
      if (!curMsg || curMsg.id !== id) {
        flushMsg();
        curMsg = { id, blocks: [], usage: null, usageAt: null, lastAt: null };
      }
      if (typeof e.timestamp === 'string') curMsg.lastAt = e.timestamp;
      if (isRequest(e) && !curMsg.usage) {
        curMsg.usage = e.message.usage;
        curMsg.usageAt = typeof e.timestamp === 'string' ? e.timestamp : null;
      }
      for (const b of contentBlocks(e)) {
        const info = assistantBlockInfo(b);
        pushMsgBlock(curMsg, info, estimateTokens(blockText(b)), toolAgg);
      }
      continue;
    }

    // 非 assistant entry：先结算打开的响应，保证请求边界正确。
    flushMsg();

    if (isCompactBoundary(e)) {
      compactions++;
      pendingCompact = true;
      const meta = e.compactMetadata || {};
      const post = meta.postTokens;
      const pre = meta.preTokens;
      // 压缩本身就是一笔普通模型调用（整份上下文当 prompt、摘要当 completion），是会话里单笔
      // 最贵的开销，此前报告只露一个次数。pre/post 是客户端自估口径，与供应商实测有出入，
      // 故 proxy 字段留空，由 generate.mjs 能在代理日志里唯一对上时再回填实测值。
      compactEvents.push({
        index: compactions,
        at: typeof e.timestamp === 'string' ? e.timestamp : null,
        trigger: typeof meta.trigger === 'string' && meta.trigger ? meta.trigger : null,
        preTokens: typeof pre === 'number' && pre > 0 ? pre : null,
        postTokens: typeof post === 'number' && post > 0 ? post : null,
        messagesSummarized: Number.isFinite(meta.messagesSummarized) ? meta.messagesSummarized : null,
        nextRequestIndex: null,
        nextInputTokens: null,
        savedTokens: null,
        proxy: null,
      });
      alive = [];
      aliveEstSum = 0;
      peakWinS = 0;
      if (typeof post === 'number' && post > 0) {
        pushAlive({ cat: CAT.COMPACT, attrKey: 'compact_summary', tool: null, file: null, kind: null, est: post });
      }
      continue;
    }

    if (isAttachment(e)) {
      const content = e.attachment?.content ?? e.attachment ?? '';
      pushAlive({ cat: CAT.ATTACH, attrKey: 'attachment', tool: null, file: null, kind: null, est: estimateTokens(content) });
      continue;
    }

    if (isUser(e)) {
      for (const b of contentBlocks(e)) {
        if (b?.type === 'tool_result') {
          const paired = toolUseById.get(b.tool_use_id) || null;
          const info = toolResultInfo(b, paired);
          const est = estimateTokens(b.content);
          const blk = { ...info, est };
          pushAlive(blk);
          if (info.tool) {
            let t = toolAgg.get(info.tool);
            if (!t) { t = { tokens: 0, calls: 0 }; toolAgg.set(info.tool, t); }
          }
          if (info.file) {
            const rec = ensureFile(info.file, info.kind, info.tool);
            rec.estSingle += est;
            rec.reads += 1;
          }
        } else if (b?.type === 'text') {
          userTurns++;
          pushAlive({ cat: CAT.USER, attrKey: 'user_input', tool: null, file: null, kind: null, est: estimateTokens(b.text) });
        }
      }
      continue;
    }
    // 其余类型（active-leaf / runtime-config / workspace-directories /
    // file-history-snapshot / last-prompt / custom-title）不参与上下文分摊。
  }
  flushMsg(); // 结算最后一次响应

  // tool_use 块的 estSingle 计入文件（调用参数也占上下文，但主要体量在 tool_result）。
  // 这里补记 tool_use 的 calls 计数（每次调用一次）。
  for (const e of entries) {
    if (!isAssistant(e)) continue;
    for (const b of contentBlocks(e)) {
      if (b?.type === 'tool_use' && b.name) {
        let t = toolAgg.get(b.name);
        if (!t) { t = { tokens: 0, calls: 0 }; toolAgg.set(b.name, t); }
        t.calls += 1;
        const file = assistantBlockInfo(b).file;
        if (file) {
          const rec = ensureFile(file, assistantBlockInfo(b).kind, b.name);
          rec.estSingle += estimateTokens(blockText(b));
        }
      }
    }
  }

  const billedInputTokens = Math.round(totalS);
  const attributedTokens = Math.round([...attrBilled.values()].reduce((a, b) => a + b, 0));
  const netContextTokens = Math.round(lastS);
  // 峰值口径 = 当前窗口（自最近一次压缩起算）。压缩的意义就是腾出窗口，压完仍拿压缩前的
  // 历史高点判「该不该再压」，结论会一直卡在红字且不随后续行为变化，故历史高点另存 peakSession*。
  // 退化情形：压完一程都没跑就出报告时，实测窗口峰值为 0 会被读成「窗口空着」，
  // 退而用压缩摘要规模（客户端自估）当地板——自估值不精确，但好过报一个 0。
  const lastCompactPost = compactions > 0 ? compactEvents[compactions - 1].postTokens || 0 : 0;
  const peakWin = peakWinS > 0 || reqCount === 0 ? peakWinS : lastCompactPost;
  const peakContextTokens = Math.round(peakWin);
  const peakContextRatio = contextWindow > 0 ? peakWin / contextWindow : 0;
  const peakSessionTokens = Math.round(peakS);
  const peakSessionRatio = contextWindow > 0 ? peakS / contextWindow : 0;
  // 历史峰值只在与当前窗口峰值差出可见量级（≥1 个百分点）时才值得单独交代：差几十 token 时
  // 两行会印成同一个数（实测黄金样本 166.9K vs 166.9K），读起来像重复。判据放数据层，两个渲染端共用。
  const peakSessionNotable = peakSessionRatio - peakContextRatio >= 0.01;
  const amplification = netContextTokens > 0 ? billedInputTokens / netContextTokens : 0;

  // 压缩明细：口径归一与合计都交给 summarizeCompactions——generate.mjs 回填代理实测后会再调一次。
  const compactionCost = {
    count: compactions,
    items: compactEvents,
    totals: summarizeCompactions(compactEvents),
  };

  // 计数类指标不依赖 usage（tool_use 块在两种转录里都有，末尾循环独立累加），故 IDE 端仍是真值；
  // 但 IDE 端出现 0 时无法区分「真没用过」与「转录里没记」，故 0 且非桌面端时判为不可用。
  const toolCalls = [...toolAgg.values()].reduce((a, v) => a + v.calls, 0);
  const fileReads = [...fileAgg.values()].reduce((a, v) => a + v.reads, 0);
  const countable = (n) =>
    n > 0 || source === SOURCE_DESKTOP ? AVAIL.MEASURED : AVAIL.UNAVAILABLE;
  const hasUsage = reqCount > 0;
  // usageSource 汇总：三档中只一档非零 → 用那档名；多档非零 → mixed。
  // 枚举值：proxy / transcript-tokens / transcript-ratio / mixed / null（无 usage）。
  let usageSource = null;
  if (hasUsage) {
    const active = [];
    if (proxyHits > 0) active.push('proxy');
    if (transcriptTokenHits > 0) active.push('transcript-tokens');
    if (transcriptRatioHits > 0) active.push('transcript-ratio');
    usageSource = active.length === 1 ? active[0] : 'mixed';
  }

  // 双阈值峰值结论：peakAdvice 对模型窗口（该不该手动压），peakUserAdvice 对用户压缩阈值
  // （Qoder 什么时候会自动触发压缩）。BYOK 下模型窗口 1M、用户阈值 200K，两者可以差一个量级，
  // 只看前者会错过「快自动压缩了」信号。
  const peakUserRatio = userContextLimit > 0 ? peakWin / userContextLimit : 0;
  const peakUserAdviceVal = peakAdvice(peakUserRatio);

  // —— 「当前占用」头条口径 ——
  // 段内上下文严格单调递增，故「自最近压缩起的峰值(peakWin)」在构造上就等于「当前上下文(lastS)」——
  // 旧版把两者并列印成同一个数（43.4%=43.4%）不是巧合，是冗余。改为以 netContextTokens 作头条，
  // peak 退居灰字（仅当跨压缩的历史高点明显更高时才单列）。netContextTokens=0（刚压完还没跑）时退回 peakWin。
  const currentContextTokens = netContextTokens > 0 ? netContextTokens : peakContextTokens;
  const netUserRatio = userContextLimit > 0 ? currentContextTokens / userContextLimit : 0;
  const netUserAdviceVal = peakAdvice(netUserRatio);
  const netWindowRatio = contextWindow > 0 ? currentContextTokens / contextWindow : 0;

  // —— Qoder 实际在哪触发自动压缩（从本场 compact_boundary 自校准，不依赖任何外部配置）——
  // 实测：trigger=auto 的触发点稳定落在窗口的 ~85%。据此反推「Qoder 真正用的窗口」，并识别
  // BYOK 常见坑：模型窗口 1M → 要到 ~850K 才自动压，用户设的 200K 根本没接进触发逻辑、形同虚设。
  const autoPres = compactEvents
    .filter((e) => e.trigger === 'auto' && Number.isFinite(e.preTokens) && e.preTokens > 0)
    .map((e) => e.preTokens)
    .sort((a, b) => a - b);
  const observedAutoCompactions = autoPres.length;
  const observedAutoTriggerTokens = observedAutoCompactions ? autoPres[Math.floor(observedAutoCompactions / 2)] : null;
  const autoTriggerRatio = observedAutoTriggerTokens != null && contextWindow > 0 ? observedAutoTriggerTokens / contextWindow : null;
  // 阈值未被强制：模型窗口显著大于用户阈值，且（本场从没自动压过 或 自动压点远高于用户阈值）。
  const thresholdNotEnforced = contextWindow >= userContextLimit * 1.5 &&
    (observedAutoCompactions === 0 || (observedAutoTriggerTokens != null && observedAutoTriggerTokens > userContextLimit * 1.2));

  // 逐项可用性：报告里每个数字到底是「模型上报的真值」「按真值推导」还是「本地根本没有」，
  // 必须随数字一起给出。三源优先级下：
  //   tokens → measured 当且仅当全部 S 来自 proxy 或 transcript-tokens（含任一 transcript-ratio 即 derived）
  //   contextRatio → measured 当且仅当至少一笔 usage 里带了 ratio 真值（否则只能 S/window 反算）
  //   contextWindow → measured （runtime-config / manual）、derived（从 usage 反推）、fallback（都没）
  const availability = {
    // 有 usage ≠ 有 credits：官方端点写进转录的 usage 不一定带 credits 字段，此时 totalCredits
    // 是 0 但那是「没这个数」，必须判不可用——否则报告渲染出「Credits 0（实测）」。
    credits: creditsTrips > 0 ? AVAIL.MEASURED : AVAIL.UNAVAILABLE,
    roundTrips: hasUsage ? AVAIL.MEASURED : AVAIL.UNAVAILABLE,
    contextRatio: hasUsage ? (ratioMeasuredHits > 0 ? AVAIL.MEASURED : AVAIL.DERIVED) : AVAIL.UNAVAILABLE,
    tokens: hasUsage ? (transcriptRatioHits === 0 ? AVAIL.MEASURED : AVAIL.DERIVED) : AVAIL.UNAVAILABLE,
    outputTokens: totalOutputTokens > 0 ? AVAIL.MEASURED : AVAIL.UNAVAILABLE,
    // 缓存命中：代理或转录 cache_read_input_tokens 任一有真值即 measured。
    cachedTokens: totalCachedTokens > 0 ? AVAIL.MEASURED : AVAIL.UNAVAILABLE,
    categoryShare: hasUsage ? AVAIL.DERIVED : AVAIL.UNAVAILABLE,
    toolShare: hasUsage ? AVAIL.DERIVED : AVAIL.UNAVAILABLE,
    fileShare: hasUsage ? AVAIL.DERIVED : AVAIL.UNAVAILABLE,
    systemPrompt: hasUsage ? AVAIL.DERIVED : AVAIL.UNAVAILABLE,
    contextWindow:
      cwInfo.source === 'runtime-config'
        ? AVAIL.MEASURED
        : cwInfo.source === 'manual'
          ? AVAIL.MANUAL
          : cwInfo.source === 'derived-from-usage'
            ? AVAIL.DERIVED
            : AVAIL.FALLBACK,
    // compact_boundary 是桌面端专有 entry：IDE 端恒 0 是「读不到」不是「没发生」，比空缺更误导。
    compactions: source === SOURCE_DESKTOP ? AVAIL.MEASURED : AVAIL.UNAVAILABLE,
    compactionCost: source === SOURCE_DESKTOP ? AVAIL.MEASURED : AVAIL.UNAVAILABLE,
    model: model ? AVAIL.MEASURED : AVAIL.UNAVAILABLE,
    title: titleSource === 'session-id' ? AVAIL.FALLBACK : AVAIL.MEASURED,
    toolCalls: countable(toolCalls),
    fileReads: countable(fileReads),
    userTurns: AVAIL.MEASURED,
    // 用户压缩阈值：manual 覆盖 → MANUAL；默认 200K → FALLBACK（未从环境探测到真实阈值）。
    userContextLimit: userContextLimitSource === 'manual' ? AVAIL.MANUAL : AVAIL.FALLBACK,
  };

  const byCategory = CATEGORY_ORDER.filter((k) => (catBilled.get(k) || 0) > 0).map((k) => ({
    key: k,
    label: CATEGORY_LABEL[k] || k,
    tokens: Math.round(catBilled.get(k)),
    share: billedInputTokens > 0 ? catBilled.get(k) / billedInputTokens : 0,
  }));

  const byTool = [...toolAgg.entries()]
    .map(([tool, v]) => ({
      tool,
      tokens: Math.round(v.tokens),
      calls: v.calls,
      // 单次 = 该工具平均每次调用带来的重发 token。总量榜会埋掉「次数少但每次极贵」的工具
      // （实测 Read 29 次吃 335 万，单次是 Edit 的 2.6 倍），故单列一维。
      perCall: v.calls > 0 ? Math.round(v.tokens / v.calls) : null,
      share: billedInputTokens > 0 ? v.tokens / billedInputTokens : 0,
    }))
    .sort((a, b) => b.tokens - a.tokens);

  const byFile = [...fileAgg.values()]
    .map((rec) => ({
      attr: `file:${rec.file}`,
      label: fileLabel(rec.file, cwd),
      kind: rec.kind,
      tool: rec.tool,
      selfTokens: Math.round(rec.estSingle),
      reads: rec.reads,
      trips: rec.trips,
      billed: Math.round(rec.billed),
      // 单次读取的总代价（含此后每一程的重发）：读一次就烧掉十几万的文件在总量榜上毫不起眼。
      perRead: rec.reads > 0 ? Math.round(rec.billed / rec.reads) : null,
      share: billedInputTokens > 0 ? rec.billed / billedInputTokens : 0,
    }))
    .sort((a, b) => b.billed - a.billed);

  const byAttr = [...attrBilled.entries()]
    .map(([attr, tokens]) => ({ attr, tokens: Math.round(tokens), share: billedInputTokens > 0 ? tokens / billedInputTokens : 0 }))
    .sort((a, b) => b.tokens - a.tokens);

  // 按类别下钻：每个类别再拆到工具 + 文件/路径（仅工具相关类别有子项；其余为整体）。
  const DETAIL_TOP = 15;
  const byCategoryDetail = byCategory.map((c) => {
    const rawCat = catBilled.get(c.key) || 0;
    const kids = [...catDetail.values()]
      .filter((d) => d.cat === c.key && (d.tool || d.file))
      .sort((a, b) => b.tokens - a.tokens);
    const children = kids.slice(0, DETAIL_TOP).map((d) => ({
      tool: d.tool,
      label: d.file ? fileLabel(d.file, cwd) : '（无路径）',
      kind: d.kind,
      tokens: Math.round(d.tokens),
      share: billedInputTokens > 0 ? d.tokens / billedInputTokens : 0,
      catShare: rawCat > 0 ? d.tokens / rawCat : 0,
      trips: d.trips,
    }));
    const rest = kids.slice(DETAIL_TOP);
    if (rest.length > 0) {
      const rt = rest.reduce((s, d) => s + d.tokens, 0);
      children.push({
        tool: null,
        label: `其他 ${rest.length} 项`,
        kind: null,
        tokens: Math.round(rt),
        share: billedInputTokens > 0 ? rt / billedInputTokens : 0,
        catShare: rawCat > 0 ? rt / rawCat : 0,
        trips: rest.reduce((s, d) => s + d.trips, 0),
      });
    }
    return { key: c.key, label: c.label, tokens: c.tokens, share: c.share, children };
  });

  return {
    // v3.1：在 v3 基础上新增 contextWindowSource 枚举（derived-from-usage / manual）、
    // usageSource 三档化（proxy / transcript-tokens / transcript-ratio / mixed）、
    // context.userContextLimit + peakUserAdvice 双阈值、proxy.breakdown 三档计数。
    // v3.2：新增「当前占用」头条口径（currentContextTokens / netUserRatio / netUserAdvice / netWindowRatio）、
    // 自动压缩自校准（observedAutoCompactions / observedAutoTriggerTokens / autoTriggerRatio / thresholdNotEnforced）、
    // userContextLimitSource 扩展 config / derived 两枚举值。
    // 均为新增字段/新增枚举值，向后兼容：旧报告读取新字段时得 undefined，渲染端均走可选链。
    schemaVersion: 3.2,
    generatedAt: new Date().toISOString(),
    source,
    usageSource,
    availability,
    session: {
      id: sessionId,
      title,
      titleSource,
      model,
      modelSource: model ? 'runtime-config' : 'unavailable',
      cwd,
      turns: userTurns,
      roundTrips: reqCount,
      compactions,
      startedAt,
      endedAt,
    },
    context: {
      contextWindow,
      contextWindowSource: cwInfo.source,
      systemPromptTokens: Esys == null ? 0 : Esys,
      netContextTokens,
      // 峰值两个口径：peakContext* = 当前窗口（自最近一次压缩起算），peakSession* = 跨压缩的本场历史高点。
      peakContextTokens,
      peakContextRatio,
      peakSessionTokens,
      peakSessionRatio,
      peakSessionNotable,
      // 峰值占比此前只在报告里存着、渲染端从不评判：实测 101.2%（已触顶）也静默无告警。
      // 判据取当前窗口峰值：压缩之后该重新起算，否则结论永远停在压缩前那次高点。
      peakAdvice: peakAdvice(peakContextRatio),
      // 用户压缩阈值双轨：与 peakAdvice 对模型窗口独立。BYOK 下模型窗口 1M、用户阈值 200K，
      // ratio 0.19 对模型判 low、对用户阈值已 over——两个信号都得给。
      userContextLimit,
      userContextLimitSource,
      peakUserRatio,
      peakUserAdvice: peakUserAdviceVal,
      // 当前占用头条口径（v3.2）：currentContextTokens 对用户阈值 / 对模型窗口两条占比 + 结论。
      currentContextTokens,
      netUserRatio,
      netUserAdvice: netUserAdviceVal,
      netWindowRatio,
      // 自动压缩自校准（v3.2）：Qoder 本场实际触发点，与「用户阈值是否被强制」的判定。
      observedAutoCompactions,
      observedAutoTriggerTokens,
      autoTriggerRatio,
      thresholdNotEnforced,
    },
    totals: {
      billedInputTokens,
      netContextTokens,
      peakContextTokens,
      amplification: Number(amplification.toFixed(2)),
      attributedTokens,
      coverage: billedInputTokens > 0 ? attributedTokens / billedInputTokens : 0,
      credits: Number(totalCredits.toFixed(3)),
      originalCredits: Number(totalOriginalCredits.toFixed(3)),
      // 输出 token：仅代理路径有真值（桌面端 usage 的 output_tokens 恒 0），无代理时为 0 且
      // availability.outputTokens 标 unavailable——0 不代表没输出。
      outputTokens: totalOutputTokens,
      // 缓存命中：供应商对重复前缀打折的那部分 prompt，同样只有代理路径有真值。
      cachedTokens: totalCachedTokens,
      cachedTrips,
      cachedShare: totalS > 0 ? totalCachedTokens / totalS : 0,
      // 两个不依赖 usage 的计数，供 IDE 端报告在占比全缺时仍有可展示的真值。
      toolCalls,
      fileReads,
    },
    // credits 的覆盖范围：credits 总量与计费输入总量并排放在报告头部，读者一除就得到单价，
    // 而混合会话里 credits 只来自转录路径的那几笔。部分覆盖必须显式说出来，否则就是把
    // 局部真值当全量展示（与「无值显示 — 不显示 0」是同一条红线的两面）。
    creditsCoverage: {
      trips: creditsTrips,
      roundTrips: reqCount,
      tokens: Math.round(creditsTokens),
      tokenShare: billedInputTokens > 0 ? creditsTokens / billedInputTokens : 0,
      full: reqCount > 0 && creditsTrips === reqCount,
    },
    compactionCost,
    // 代理 join 诊断：matched = 由代理记录结算的往返数（语义不变）；
    // breakdown 三档拆分，让报告能一眼看出各源占比（代理/转录 tokens/转录 ratio）。
    // logPath/records/configured/… 由 generate.mjs 补。
    proxy: {
      matched: proxyHits,
      requests: reqCount,
      breakdown: {
        proxy: proxyHits,
        transcriptTokens: transcriptTokenHits,
        transcriptRatio: transcriptRatioHits,
      },
    },
    byCategory,
    byCategoryDetail,
    byTool,
    byFile,
    byAttr,
    byRequest: requests,
    identity: {
      // 恒等式 A1：Σ 归因 == 计费输入总量（比例分摊下应精确成立，仅浮点误差）。
      // ok 三值：一次往返都没有时 0 <= max(2, 0) 恒成立，会把「没数据」判成「校验通过」，故记 null（不适用）。
      sumAttributed: attributedTokens,
      billedInputTokens,
      absDiff: Math.abs(attributedTokens - billedInputTokens),
      ok: reqCount === 0 ? null : Math.abs(attributedTokens - billedInputTokens) <= Math.max(2, reqCount),
    },
  };
}

/** ISO 时间戳 → "HH:MM"（本地时区）；无效或空则返回 null（呈现层回退为 #index）。 */
function fmtTime(iso) {
  if (!iso) return null;
  const d = new Date(iso);
  if (isNaN(d.getTime())) return null;
  const p = (v) => String(v).padStart(2, '0');
  return `${p(d.getHours())}:${p(d.getMinutes())}`;
}

// 把 assistant 输出块加入当前响应的块缓冲，并累计工具调用占位。
function pushMsgBlock(msg, info, est, toolAgg) {
  msg.blocks.push({ ...info, est });
  if (info.cat === CAT.TOOL_USE && info.file) {
    // tool_use 的文件体量在此不重复计 estSingle（随后统一在末尾补记 calls）。
  }
}
