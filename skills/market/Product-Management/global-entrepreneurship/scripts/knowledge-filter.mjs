#!/usr/bin/env node
/**
 * knowledge-filter.mjs — 知识库精准加载过滤
 * 根据入口点/层级/行业精准匹配 reference 文件，每次最多加载 5 个。
 * 仅依赖 Node 内置模块，Node >= 18。
 *
 * 输出恒为 JSON：默认单行紧凑输出，加 --json 输出缩进格式。
 *
 * 用法:
 *   node scripts/knowledge-filter.mjs --entry market --json
 *   node scripts/knowledge-filter.mjs --entry fulllink
 *   node scripts/knowledge-filter.mjs --layer 5
 *   node scripts/knowledge-filter.mjs --industry saas
 *   node scripts/knowledge-filter.mjs            # 无参数：列出全部 reference（不加载正文）
 *
 * 参数优先级: --layer > --entry > --industry；同时给出时低优先级参数记入 ignored。
 */
import { readFileSync, existsSync, readdirSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const REFS_DIR = join(__dirname, '..', 'references');

const MAX_FILES = 5;

// 入口→reference文件映射
const ENTRY_MAP = {
  'fulllink': [
    'beginner-guide.md', 'layer-details.md', 'startup-health-score.md',
    'tools-guide.md', 'daily-operations.md'
  ],
  'market': [
    'world-markets.md', 'world-industries.md', 'global-markets.md',
    'english-markets.md', '2026-trends.md'
  ],
  'country': [
    'world-markets.md', 'global-markets.md', 'english-markets.md',
    'industry-knowledge.md', 'opc-policy.md'
  ],
  'industry': [
    'world-industries.md', 'industry-knowledge.md', 'industry-templates.md',
    'tools-guide.md', '2026-trends.md'
  ],
  'finance': [
    'tools-guide.md', 'startup-health-score.md', 'daily-operations.md',
    'industry-templates.md', '2026-trends.md'
  ],
  'compliance': [
    'industry-knowledge.md', 'opc-policy.md', 'world-markets.md',
    'global-markets.md', 'layer-details.md'
  ],
  'daily': [
    'daily-operations.md', 'tools-guide.md', 'startup-health-score.md',
    'agent-marketplace.md', 'context-engineering.md'
  ],
  'beginner': [
    'beginner-guide.md', 'tools-guide.md', 'layer-details.md',
    'daily-operations.md', 'startup-health-score.md'
  ],
  'global': [
    'world-markets.md', 'global-markets.md', 'english-markets.md',
    'language-guide.md', '2026-trends.md'
  ],
  'ai': [
    'agent-marketplace.md', 'context-engineering.md', '2026-trends.md',
    'tools-guide.md', 'industry-knowledge.md'
  ]
};

// 层级→reference文件映射（1-15层）
const LAYER_MAP = {
  1: ['beginner-guide.md', 'startup-health-score.md'],
  2: ['world-markets.md', 'world-industries.md', '2026-trends.md', 'global-markets.md', 'english-markets.md'],
  3: ['world-markets.md', 'world-industries.md', 'industry-knowledge.md', 'industry-templates.md', '2026-trends.md'],
  4: ['industry-templates.md', 'tools-guide.md', 'layer-details.md'],
  5: ['industry-knowledge.md', 'opc-policy.md', 'world-markets.md', 'global-markets.md', 'layer-details.md'],
  6: ['layer-details.md', 'tools-guide.md', 'daily-operations.md', 'industry-templates.md', 'beginner-guide.md'],
  7: ['tools-guide.md', 'agent-marketplace.md', 'daily-operations.md', 'context-engineering.md', '2026-trends.md'],
  8: ['industry-templates.md', 'industry-knowledge.md', 'tools-guide.md'],
  9: ['tools-guide.md', 'startup-health-score.md', 'daily-operations.md', 'industry-templates.md', 'layer-details.md'],
  10: ['tools-guide.md', 'agent-marketplace.md', 'daily-operations.md', 'context-engineering.md', '2026-trends.md'],
  11: ['industry-knowledge.md', 'opc-policy.md', 'layer-details.md', 'world-markets.md', 'global-markets.md'],
  12: ['startup-health-score.md', 'daily-operations.md', 'tools-guide.md'],
  13: ['2026-trends.md', 'agent-marketplace.md', 'context-engineering.md', 'world-industries.md', 'industry-templates.md'],
  14: ['world-markets.md', 'global-markets.md', 'english-markets.md', 'language-guide.md', 'agent-marketplace.md'],
  15: ['world-markets.md', 'global-markets.md', 'startup-health-score.md', 'layer-details.md', '2026-trends.md']
};

// 行业→reference文件映射（键名含常见别名，覆盖6大行业预设与主要方向；未命中走 default）
const INDUSTRY_MAP = {
  'saas': ['industry-knowledge.md', 'industry-templates.md', 'tools-guide.md', 'agent-marketplace.md', '2026-trends.md'],
  'tech': ['industry-knowledge.md', 'industry-templates.md', 'tools-guide.md', 'agent-marketplace.md', '2026-trends.md'],
  'software': ['industry-knowledge.md', 'industry-templates.md', 'tools-guide.md', 'agent-marketplace.md', '2026-trends.md'],
  'ecommerce': ['industry-knowledge.md', 'industry-templates.md', 'world-markets.md', 'tools-guide.md', 'daily-operations.md'],
  'retail': ['industry-knowledge.md', 'industry-templates.md', 'world-markets.md', 'tools-guide.md', 'daily-operations.md'],
  'fintech': ['industry-knowledge.md', 'opc-policy.md', 'world-markets.md', 'industry-templates.md', 'global-markets.md'],
  'finance': ['industry-knowledge.md', 'opc-policy.md', 'world-markets.md', 'industry-templates.md', 'global-markets.md'],
  'content': ['tools-guide.md', 'agent-marketplace.md', 'context-engineering.md', 'daily-operations.md', '2026-trends.md'],
  'self-media': ['tools-guide.md', 'agent-marketplace.md', 'context-engineering.md', 'daily-operations.md', '2026-trends.md'],
  'creator': ['tools-guide.md', 'agent-marketplace.md', 'context-engineering.md', 'daily-operations.md', '2026-trends.md'],
  'consulting': ['industry-knowledge.md', 'industry-templates.md', 'layer-details.md', 'tools-guide.md', 'startup-health-score.md'],
  'education': ['industry-knowledge.md', 'industry-templates.md', 'world-markets.md', 'tools-guide.md', 'language-guide.md'],
  'livestream': ['industry-knowledge.md', 'industry-templates.md', 'tools-guide.md', 'daily-operations.md', 'agent-marketplace.md'],
  'crossborder': ['world-markets.md', 'global-markets.md', 'english-markets.md', 'language-guide.md', 'industry-knowledge.md'],
  'cross-border': ['world-markets.md', 'global-markets.md', 'english-markets.md', 'language-guide.md', 'industry-knowledge.md'],
  'default': ['industry-knowledge.md', 'industry-templates.md', 'world-industries.md', 'tools-guide.md', '2026-trends.md']
};

// 解析参数
const args = process.argv.slice(2);
let entry = null, layer = null, industry = null, jsonMode = false;
let layerRaw = null;

for (let i = 0; i < args.length; i++) {
  if (args[i] === '--entry' && args[i + 1]) { entry = args[i + 1]; i++; }
  else if (args[i] === '--layer' && args[i + 1]) { layerRaw = args[i + 1]; layer = parseInt(args[i + 1], 10); i++; }
  else if (args[i] === '--industry' && args[i + 1]) { industry = String(args[i + 1]).toLowerCase(); i++; }
  else if (args[i] === '--json') { jsonMode = true; }
}

function fail(message) {
  const payload = { error: message };
  console.error(JSON.stringify(payload, null, 2));
  process.exit(1);
}

function emit(result) {
  console.log(jsonMode ? JSON.stringify(result, null, 2) : JSON.stringify(result));
  process.exit(0);
}

// 显式校验 --layer：给了但非法（非数字/越界）必须报错，不得静默回退
if (layerRaw !== null && (!Number.isInteger(layer) || !(layer in LAYER_MAP))) {
  fail(`Invalid --layer "${layerRaw}"：必须是 1-${Object.keys(LAYER_MAP).length} 之间的整数层级`);
}
// 显式校验 --entry：给了但不在映射表中必须报错，并列出合法值
if (entry !== null && !Object.prototype.hasOwnProperty.call(ENTRY_MAP, entry)) {
  fail(`Invalid --entry "${entry}"：合法值为 ${Object.keys(ENTRY_MAP).join(' / ')}`);
}

// 无任何有效筛选参数：列出全部 reference（不加载正文）
if (layer === null && entry === null && industry === null) {
  const allFiles = existsSync(REFS_DIR)
    ? readdirSync(REFS_DIR).filter(f => f.endsWith('.md')).sort()
    : [];
  emit({
    source: 'all',
    totalFiles: allFiles.length,
    loaded: allFiles.map(f => ({ file: f, path: `references/${f}` })),
    truncated: false
  });
}

// 按优先级 layer > entry > industry 选择，并记录被忽略的低优先级参数
let files = [];
let source = '';
const ignored = [];

if (layer !== null) {
  files = LAYER_MAP[layer];
  source = `layer-${layer}`;
  if (entry) ignored.push({ param: '--entry', value: entry, reason: 'lower priority than --layer' });
  if (industry) ignored.push({ param: '--industry', value: industry, reason: 'lower priority than --layer' });
} else if (entry !== null) {
  files = ENTRY_MAP[entry];
  source = `entry-${entry}`;
  if (industry) ignored.push({ param: '--industry', value: industry, reason: 'lower priority than --entry' });
} else {
  const matched = Object.prototype.hasOwnProperty.call(INDUSTRY_MAP, industry);
  files = matched ? INDUSTRY_MAP[industry] : INDUSTRY_MAP['default'];
  source = `industry-${industry}`;
  if (!matched) source = 'industry-default';
  if (!matched) {
    // 未命中具体行业映射时明确标注走了兜底，避免“表面匹配”
    ignored.push({ param: '--industry', value: industry, reason: 'no dedicated mapping, fell back to default set' });
  }
}

const truncated = files.length > MAX_FILES;
const loadedFiles = files.slice(0, MAX_FILES);

const warnings = [];
const loaded = loadedFiles.map(f => {
  const filePath = join(REFS_DIR, f);
  let content = null;
  if (existsSync(filePath)) {
    try {
      content = readFileSync(filePath, 'utf8');
    } catch {
      content = null;
    }
  }
  if (content === null) warnings.push(`reference file missing or unreadable: references/${f}`);
  return { file: f, path: `references/${f}`, exists: content !== null, content };
});

emit({
  source,
  totalRequested: files.length,
  loaded: loaded.length,
  maxFiles: MAX_FILES,
  truncated,
  ignored,
  warnings,
  files: loaded
});
