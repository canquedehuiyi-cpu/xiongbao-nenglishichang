// attrib.mjs — 把内容块映射为归因键（类别 / 工具 / 文件 / 种类）。
//
// 实测真实工具名（黄金样本 tool_use 计数）：
//   Bash(319) Edit(256) Read(146) Grep(63) Write(49) TaskUpdate(28)
//   TaskCreate(22) Glob(6) AskUserQuestion(2)
// 注意：这些是兼容名，与设计文档早期草稿里的 edit_file/SearchReplace/LSP 等不同——
// 以本表为准。归因对未知工具保持开放（kind=other）。

import path from 'node:path';

export const CAT = {
  SYSTEM: 'system',
  COMPACT: 'compact_summary',
  USER: 'user_input',
  ATTACH: 'attachment',
  THINK: 'assistant_thinking',
  TEXT: 'assistant_text',
  TOOL_USE: 'assistant_tool_use',
  TOOL_RESULT: 'tool_result',
};

/** 类别展示顺序与中文标签（呈现层用）。 */
export const CATEGORY_ORDER = [
  CAT.TOOL_RESULT,
  CAT.SYSTEM,
  CAT.COMPACT,
  CAT.THINK,
  CAT.TOOL_USE,
  CAT.TEXT,
  CAT.USER,
  CAT.ATTACH,
];

export const CATEGORY_LABEL = {
  [CAT.SYSTEM]: '系统提示词',
  [CAT.COMPACT]: '压缩摘要',
  [CAT.USER]: '用户输入',
  [CAT.ATTACH]: '附件/技能',
  [CAT.THINK]: '模型思考',
  [CAT.TEXT]: '模型回复',
  [CAT.TOOL_USE]: '工具调用',
  [CAT.TOOL_RESULT]: '工具返回',
};

const WRITE_TOOLS = new Set(['Edit', 'Write', 'MultiEdit', 'SearchReplace']);
const READ_TOOLS = new Set(['Read']);
const SEARCH_TOOLS = new Set(['Grep', 'Glob', 'SearchCodebase', 'search_file']);

/** 从工具输入里提取相关文件/目录路径（若无则 null）。 */
export function fileFromToolInput(tool, input) {
  if (!input || typeof input !== 'object') return null;
  const cand = input.file_path || input.path || input.target_file || input.notebook_path || null;
  if (cand && typeof cand === 'string') return cand;
  if (READ_TOOLS.has(tool) || WRITE_TOOLS.has(tool)) return null;
  // 搜索类：退化用 pattern/query 作为标识
  const p = input.pattern || input.query || input.glob || null;
  return typeof p === 'string' ? p : null;
}

/** 工具 → 文件操作种类。 */
export function kindForTool(tool) {
  if (!tool) return 'other';
  if (READ_TOOLS.has(tool)) return 'read';
  if (WRITE_TOOLS.has(tool)) return 'write';
  if (SEARCH_TOOLS.has(tool)) return 'search';
  if (tool === 'Bash') return 'shell';
  return 'other';
}

/** 生成用于展示的文件标签：能相对 cwd 就相对，否则取目录+文件名。 */
export function fileLabel(file, cwd) {
  if (!file) return '';
  let f = String(file);
  if (cwd) {
    const rel = path.relative(cwd, f);
    if (rel && !rel.startsWith('..') && !path.isAbsolute(rel)) f = rel;
  }
  // 统一分隔符，便于展示
  return f.replace(/\\/g, '/');
}

/** assistant 内容块 → 归因信息（不含 est，由调用方用 tokens 估算填入）。 */
export function assistantBlockInfo(block) {
  const t = block?.type;
  if (t === 'thinking') {
    return { cat: CAT.THINK, attrKey: 'assistant_thinking', tool: null, file: null, kind: null, label: '模型思考' };
  }
  if (t === 'text') {
    return { cat: CAT.TEXT, attrKey: 'assistant_text', tool: null, file: null, kind: null, label: '模型回复' };
  }
  if (t === 'tool_use') {
    const tool = block.name || 'unknown';
    const file = fileFromToolInput(tool, block.input);
    return { cat: CAT.TOOL_USE, attrKey: `tool_use|${tool}`, tool, file, kind: kindForTool(tool), label: tool };
  }
  return { cat: CAT.TEXT, attrKey: 'assistant_other', tool: null, file: null, kind: null, label: '其他输出' };
}

/** tool_result 内容块 → 归因信息；pairedToolUse 用于回填工具名与文件路径。 */
export function toolResultInfo(block, pairedToolUse) {
  const tool = pairedToolUse?.name || null;
  const file = pairedToolUse ? fileFromToolInput(tool, pairedToolUse.input) : null;
  return { cat: CAT.TOOL_RESULT, attrKey: `tool_result|${tool || 'unknown'}`, tool, file, kind: kindForTool(tool), label: tool || '工具返回' };
}
