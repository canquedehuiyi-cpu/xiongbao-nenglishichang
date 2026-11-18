// tokens.mjs — 从文本估算 token 规模。
//
// 重要：绝对比例并非关键。breakdown.mjs 会用每次请求的真实上下文规模
// (context_usage_ratio × contextWindow) 作为权威总量，并把该总量按各块的
// 估算规模“比例分摊”。因此本模块只影响可见块之间的相对占比，估算 ratios
// 的系统性偏差在归一化时会被抵消。

const CJK_RE = /[\u3040-\u30ff\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff\uac00-\ud7af]/g;

/** 估算一段文本（或可序列化对象）的 token 数。 */
export function estimateTokens(input) {
  if (input == null) return 0;
  const s = typeof input === 'string' ? input : safeStringify(input);
  const n = s.length;
  if (!n) return 0;
  const cjk = (s.match(CJK_RE) || []).length;
  const other = n - cjk;
  // 经验比例：CJK ≈ 1.3 token/字；拉丁/代码 ≈ 1 token / 4 字符。
  return Math.max(0, Math.round(cjk * 1.3 + other / 4));
}

/** 稳定序列化，避免因循环引用抛错。 */
export function safeStringify(value) {
  try {
    return JSON.stringify(value) ?? String(value);
  } catch {
    return String(value);
  }
}

/** 从任意内容块中尽力抽取用于度量的文本。 */
export function blockText(block) {
  if (block == null) return '';
  if (typeof block === 'string') return block;
  if (typeof block.text === 'string') return block.text;
  if (typeof block.thinking === 'string') return block.thinking;
  if (typeof block.content === 'string') return block.content;
  if (block.input != null) return safeStringify(block.input);
  return safeStringify(block);
}
