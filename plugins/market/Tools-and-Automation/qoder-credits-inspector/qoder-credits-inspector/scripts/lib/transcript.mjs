// transcript.mjs — 解析 Qoder CN 转录 (.jsonl) 为类型化 entry，并提供谓词/解析器。
//
// 两个客户端并存、各写一套转录（实测 ~/.qoder-cn/projects/ 下 40 个转录：22 个有 usage、全在
// 桌面端布局；18 个无、全在 IDE 布局），本模块对两者都能读，并把「哪些量可不可信」显式回传：
//
//   桌面端富转录  projects\<slug>\<sessionId>.jsonl
//     entry 类型：workspace-directories / runtime-config / user / attachment /
//                 active-leaf / assistant / file-history-snapshot / system(compact_boundary) /
//                 last-prompt / custom-title
//     assistant.message.usage 存在：credits / original_credits / context_usage_ratio 为真值，
//                 input_tokens / output_tokens 恒为 0（实测全库无非零值）
//
//   IDE 端精简转录  projects\<slug>\transcript\<sessionId>.jsonl
//     entry 类型：只有 session_meta / user / assistant / progress
//     message.usage 整个字段不存在，也无 runtime-config / custom-title / compact_boundary
//     → 所有计费与上下文数字本地不可恢复，只能取官方 UI（见 generate.mjs 的 overrides 回填）

import fs from 'node:fs';

/** 读取并逐行解析转录，跳过空行与损坏行。
 *  去 BOM：首行带 BOM 时 JSON.parse 会失败，而首行往往正是 runtime-config ——
 *  静默丢掉它会让窗口回退到 200000、source 误判为 unknown，整份报告口径跟着变。 */
export function readEntries(transcriptPath) {
  const text = fs.readFileSync(transcriptPath, 'utf8').replace(/^\uFEFF/, '');
  const out = [];
  for (const line of text.split(/\r?\n/)) {
    if (!line) continue;
    try {
      out.push(JSON.parse(line));
    } catch {
      /* 跳过损坏行，保持刷新链路健壮 */
    }
  }
  return out;
}

export const isAssistant = (e) => e?.type === 'assistant';
export const isUser = (e) => e?.type === 'user';
export const isAttachment = (e) => e?.type === 'attachment';
export const isRuntimeConfig = (e) => e?.type === 'runtime-config';
export const isWorkspaceDirs = (e) => e?.type === 'workspace-directories';
export const isCompactBoundary = (e) => e?.type === 'system' && e?.subtype === 'compact_boundary';

/** 一次请求（round-trip）= 携带 usage 计量载荷的 assistant entry。
 *  实测：每条响应按 message.id 拆成多个 entry，usage 恰在最后一个上。
 *  载荷判据：ratio 或 input_tokens 任一为正即算（官方网关写 ratio、直连供应商写 input_tokens）。 */
export function isRequest(e) {
  const u = e?.message?.usage;
  if (e?.type !== 'assistant' || u == null) return false;
  return (
    (typeof u.context_usage_ratio === 'number' && u.context_usage_ratio > 0) ||
    (typeof u.input_tokens === 'number' && u.input_tokens > 0)
  );
}

/** usage 里是否已有真实 token 数（BYOK 直连供应商时字段齐全；官方网关会抹零只剩 ratio）。 */
export function usageHasRealTokens(u) {
  return Number.isFinite(u?.input_tokens) && u.input_tokens > 0;
}

/** 归组一条响应所需的消息 id（同一次请求的多个内容块共享）。 */
export function messageId(e) {
  return e?.message?.id ?? null;
}

/** 取出 entry 的内容块数组（兼容字符串内容）。 */
export function contentBlocks(e) {
  const c = e?.message?.content;
  if (Array.isArray(c)) return c;
  if (typeof c === 'string') return [{ type: 'text', text: c }];
  return [];
}

/** 上下文窗口（token）。三级回退：runtime-config → 从 usage 反推 → fallback。 */
export function resolveContextWindow(entries, fallback = 200000) {
  return resolveContextWindowInfo(entries, fallback).contextWindow;
}

/** 同 resolveContextWindow，但额外回传来源。
 *  IDE 端转录没有 runtime-config，会静默回退到 fallback —— 而报告里每一个 token 数字都要乘它，
 *  所以「这是回退值」必须显式暴露，否则口径说明看上去像实测。
 *  source 枚举：runtime-config / derived-from-usage / fallback。 */
export function resolveContextWindowInfo(entries, fallback = 200000) {
  let contextWindow = null;
  let source = null;
  // 后写赢：会话中途可能重写 runtime-config（如切模型），以最后一条为准。
  for (const e of entries) {
    if (isRuntimeConfig(e) && typeof e.contextWindow === 'number' && e.contextWindow > 0) {
      contextWindow = e.contextWindow;
      source = 'runtime-config';
    }
  }
  if (contextWindow == null) {
    const derived = resolveContextWindowFromUsage(entries);
    if (derived.contextWindow != null) {
      contextWindow = derived.contextWindow;
      source = derived.source;
    }
  }
  if (contextWindow == null) {
    contextWindow = fallback;
    source = 'fallback';
  }
  return { contextWindow, source };
}

/** 从 usage 反推 contextWindow：input_tokens ÷ context_usage_ratio。
 *  BYOK 场景下 runtime-config.contextWindow=null，但供应商响应里两个字段同源同刻，
 *  相除即得真实窗口（实测 25445/0.025445 ≈ 1000000）。取整到千位吸收浮点噪声；
 *  仅当结果落在 [10K, 100M] 时采纳，避免 ratio 极小时放大误差。无有效样本返回 null。 */
export function resolveContextWindowFromUsage(entries) {
  for (const e of entries) {
    if (!isAssistant(e)) continue;
    const u = e?.message?.usage;
    if (!u) continue;
    const input = u.input_tokens;
    const ratio = u.context_usage_ratio;
    if (!Number.isFinite(input) || input <= 0) continue;
    if (!Number.isFinite(ratio) || ratio <= 0) continue;
    const raw = input / ratio;
    if (raw < 10_000 || raw > 100_000_000) continue;
    return { contextWindow: Math.round(raw / 1000) * 1000, source: 'derived-from-usage' };
  }
  return { contextWindow: null, source: null };
}

/** 转录来源（哪一代客户端写的）。 */
export const SOURCE_DESKTOP = 'desktop-rich';
export const SOURCE_IDE = 'ide-lite';
export const SOURCE_UNKNOWN = 'unknown';

/** 判别转录来自哪个客户端。
 *  判据取两种布局各自的专有 entry：runtime-config（桌面端必写）与 session_meta（IDE 端必写）。
 *  不用「有没有 usage」做判据：桌面端会话若一次往返都没完成，usage 也可能为空，
 *  但它仍是桌面端转录——客户端身份与数据完整度是两件事，后者由 availability 单独表达。 */
export function resolveSource(entries) {
  let sawRuntimeConfig = false;
  let sawSessionMeta = false;
  for (const e of entries) {
    if (isRuntimeConfig(e)) sawRuntimeConfig = true;
    else if (e?.type === 'session_meta') sawSessionMeta = true;
  }
  if (sawRuntimeConfig) return SOURCE_DESKTOP;
  if (sawSessionMeta) return SOURCE_IDE;
  return SOURCE_UNKNOWN;
}

/** 模型名，取自 runtime-config.model（实测 qmodel_38max）。 */
export function resolveModel(entries) {
  let model = null;
  for (const e of entries) if (isRuntimeConfig(e) && e.model) model = e.model;
  return model;
}

/** 工作目录，优先 workspace-directories.directories[0]，回退任意 entry.cwd。 */
export function resolveCwd(entries) {
  for (const e of entries) {
    if (isWorkspaceDirs(e) && Array.isArray(e.directories) && e.directories[0]) return e.directories[0];
  }
  for (const e of entries) if (e.cwd) return e.cwd;
  return null;
}

/** 会话 id。 */
export function resolveSessionId(entries) {
  for (const e of entries) if (e.sessionId) return e.sessionId;
  return null;
}

/** 会话标题（前端会话列表显示名），取自 custom-title.customTitle；多个取最后一个。
 *  注：平台仅在用户「重命名会话」后才写入 custom-title；新会话尚无此条目时返回 null。 */
export function resolveCustomTitle(entries) {
  let title = null;
  for (const e of entries) {
    if (e?.type === 'custom-title' && typeof e.customTitle === 'string' && e.customTitle.trim()) {
      title = e.customTitle.trim();
    }
  }
  return title;
}

/** 从用户消息文本剥离系统注入（<system-reminder>）与 <user_query> 包裹，取出真实提问正文。 */
function extractUserQuery(text) {
  let t = String(text || '');
  t = t.replace(/<system-reminder>[\s\S]*?<\/system-reminder>/gi, ' ');
  const m = t.match(/<user_query>([\s\S]*?)<\/user_query>/i);
  if (m) t = m[1];
  return t.replace(/\s+/g, ' ').trim();
}

/** 标题回退：无 custom-title 时，用「首条真实用户提问」的前若干字符派生标题。
 *  平台在新会话尚未重命名时不写 custom-title，导致文件名回退为 session-<id8>（用户视为“乱码”）；
 *  这里以首问派生一个可读标题，令首次生成的 .canvas.tsx 文件名即与前端会话对应，重命名后自动升级为 custom-title。
 *  只认文本块（跳过 tool_result 回填的 user entry）；按码点截断（Array.from）避免 emoji/代理对被截半。 */
export function resolveTitleFromFirstUser(entries, maxLen = 24) {
  for (const e of entries) {
    if (!(e?.type === 'user' || e?.role === 'user')) continue;
    const c = e?.message?.content;
    const raw =
      typeof c === 'string'
        ? c
        : Array.isArray(c)
          ? c.map((b) => (typeof b === 'string' ? b : b?.type === 'text' ? b.text || '' : '')).join(' ')
          : '';
    const text = extractUserQuery(raw);
    if (!text) continue;
    return Array.from(text).slice(0, maxLen).join('');
  }
  return null;
}

/** 时间范围（ISO 字符串）。 */
export function resolveTimeRange(entries) {
  let startedAt = null;
  let endedAt = null;
  for (const e of entries) {
    const ts = e?.timestamp;
    if (typeof ts === 'string') {
      if (!startedAt) startedAt = ts;
      endedAt = ts;
    }
  }
  return { startedAt, endedAt };
}
