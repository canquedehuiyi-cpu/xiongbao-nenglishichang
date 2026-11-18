#!/usr/bin/env node
/**
 * knowledge-filter.mjs — 知识加载过滤工具 (v1.0.7)
 *
 * 按入口/优先级精准加载 references 下的知识文件,避免上下文爆炸。
 * 单次交互加载上限: 5个文件(P0必看+P1常用),超出仅记路径。
 * --entry 返回的 loaded 数组含 content 字段,可直接拼进 LLM 上下文。
 * --search 提供跨 references(含 SOP/engine) 的全文检索。
 *
 * 用法:
 *   node references/scripts/knowledge-filter.mjs --list --json
 *   node references/scripts/knowledge-filter.mjs --entry selection --json
 *   node references/scripts/knowledge-filter.mjs --entry cross-border --json --max 3
 *   node references/scripts/knowledge-filter.mjs --search 增值税 --json
 *   node references/scripts/knowledge-filter.mjs --version
 */

import { readdirSync, existsSync, readFileSync } from 'node:fs';
import { join, dirname, resolve, sep } from 'node:path';
import { fileURLToPath } from 'node:url';

const VERSION = '1.0.7';
const __dirname = dirname(fileURLToPath(import.meta.url));
const REFS_DIR = join(__dirname, '..');
const SKILL_ROOT = join(__dirname, '..', '..');

const args = process.argv.slice(2);
const wantJson = args.includes('--json');
const listMode = args.includes('--list');
if (args.includes('--version')) {
  process.stdout.write(VERSION + '\n');
  process.exit(0);
}
const KNOWN_FLAGS = new Set(['--entry', '--search', '--max', '--list', '--json', '--version']);
const unknownFlags = args.filter((a) => a.startsWith('--') && !KNOWN_FLAGS.has(a));
if (unknownFlags.length) {
  console.error('未知参数: ' + unknownFlags.join(' ') + '\n可用参数: --entry <入口> --search <关键词> --max <1-20> --list --json');
  process.exit(1);
}

function getArg(name) {
  const i = args.indexOf('--' + name);
  return i >= 0 ? args[i + 1] : null;
}
const entry = getArg('entry');
const search = getArg('search');
const maxArg = getArg('max');
let MAX = 5;
if (maxArg !== null) {
  const n = parseInt(maxArg, 10);
  if (!Number.isFinite(n) || n < 1 || n > 20) {
    console.error('无效的 --max 值: ' + maxArg + ' (须为 1-20 的整数)');
    process.exit(1);
  }
  MAX = n;
}
const OVER_LIMIT_WARNING = MAX > 5
  ? '--max ' + MAX + ' 超过默认预算 5, 单次加载过多会挤占上下文窗口; 建议 ≤5, 其余文件按需读取'
  : null;

// 入口 → 文件优先级映射
// P0: 必加载  P1: 当前任务涉及时加载  P2: 按需/用户主动问
const ENTRY_MAP = {
  selection: {
    name: '智能选品',
    P0: ['references/product-selection.md', 'references/product-categories.md'],
    P1: ['references/world-ecommerce.md', 'references/2026-ecommerce-trends.md'],
    P2: ['references/pricing-analysis.md', 'references/daily-price-monitor.md'],
  },
  compliance: {
    name: '平台合规',
    P0: ['references/platform-rules.md'],
    P1: ['references/cross-border-guide.md', 'references/gdpr-ccpa.md'],
    P2: ['references/us-sales-tax.md'],
  },
  pricing: {
    name: '定价分析',
    P0: ['references/pricing-analysis.md', 'references/daily-price-monitor.md'],
    P1: ['references/product-categories.md'],
    P2: ['references/world-ecommerce.md'],
  },
  profit: {
    name: '利润计算',
    P0: ['references/pricing-analysis.md'],
    P1: ['references/cross-border-guide.md', 'references/us-sales-tax.md'],
    P2: ['references/product-categories.md'],
  },
  'cross-border': {
    name: '跨境指导',
    P0: ['references/cross-border-guide.md', 'references/us-sales-tax.md'],
    P1: ['references/platform-rules.md', 'references/world-ecommerce.md'],
    P2: ['references/2026-ecommerce-trends.md'],
  },
  review: {
    name: '评价情感分析',
    P0: ['references/review-sentiment.md'],
    P1: ['references/product-selection.md'],
    P2: ['references/daily-price-monitor.md'],
  },
  monitor: {
    name: '竞品价格监控',
    P0: ['references/daily-price-monitor.md', 'references/pricing-analysis.md'],
    P1: ['references/product-selection.md'],
    P2: ['references/2026-ecommerce-trends.md'],
  },
  trends: {
    name: '市场趋势分析',
    P0: ['references/2026-ecommerce-trends.md', 'references/world-ecommerce.md'],
    P1: ['references/product-categories.md'],
    P2: ['references/product-selection.md'],
  },
  listing: {
    name: 'Listing优化',
    P0: ['references/listing-optimization.md'],
    P1: ['references/agent-readiness.md', 'references/language-guide.md'],
    P2: ['references/product-categories.md', 'references/pricing-analysis.md', 'references/review-sentiment.md'],
  },
  ppc: {
    name: 'PPC广告',
    P0: ['references/ppc-advertising.md'],
    P1: ['references/pricing-analysis.md', 'references/daily-price-monitor.md'],
    P2: ['references/product-selection.md'],
  },
  inventory: {
    name: '库存管理',
    P0: ['references/inventory-management.md'],
    P1: ['references/cross-border-guide.md'],
    P2: ['references/pricing-analysis.md'],
  },
  tiktok: {
    name: 'TikTok内容电商',
    P0: ['references/tiktok-shop-playbook.md'],
    P1: ['references/2026-ecommerce-trends.md'],
    P2: ['references/product-categories.md', 'references/listing-optimization.md'],
  },
  beginner: {
    name: '新手入门',
    P0: ['references/beginner-guide.md'],
    P1: ['references/world-ecommerce.md'],
    P2: ['references/platform-rules.md', 'references/product-selection.md'],
  },
};

function listFilesIn(dir) {
  if (!existsSync(dir)) return [];
  return readdirSync(dir).filter((f) => f.endsWith('.md'));
}

function listAll() {
  const refs = listFilesIn(REFS_DIR).map((f) => 'references/' + f);
  const sop = listFilesIn(join(REFS_DIR, 'sop')).map((f) => 'references/sop/' + f);
  const engine = listFilesIn(join(REFS_DIR, 'engine')).map((f) => 'references/engine/' + f);
  const entries = Object.entries(ENTRY_MAP).map(([k, v]) => ({ entry: k, name: v.name }));
  return {
    ok: true,
    tool: 'knowledge-filter',
    version: VERSION,
    schema: 'global-ecommerce-intelligence/knowledge-filter',
    generatedAt: new Date().toISOString(),
    mode: 'list',
    refsCount: refs.length,
    sopCount: sop.length,
    engineCount: engine.length,
    totalFiles: refs.length + sop.length + engine.length,
    files: [...refs, ...sop, ...engine],
    entries,
    loadLimit: MAX,
    note: '单次交互加载上限' + MAX + '个(P0+P1优先),P2仅记路径按需读; loaded[] 含 content 字段可直接拼上下文; --search 跨全部 md 全文检索',
  };
}

function readSafe(rel) {
  const abs = resolve(SKILL_ROOT, rel);
  if (!abs.startsWith(SKILL_ROOT + sep)) {
    return { ok: false, error: '路径越界: ' + rel };
  }
  if (!existsSync(abs)) return { ok: false, error: '文件不存在: ' + rel };
  try {
    return { ok: true, content: readFileSync(abs, 'utf-8') };
  } catch (e) {
    return { ok: false, error: '读文件失败: ' + rel + ' ' + e.message };
  }
}

function fileRelToBasename(rel) {
  const i = rel.lastIndexOf('/');
  return i >= 0 ? rel.slice(i + 1) : rel;
}

function resolveEntry(entryName) {
  const map = ENTRY_MAP[entryName];
  if (!map) {
    return { error: '未知入口: ' + entryName, available: Object.keys(ENTRY_MAP) };
  }
  const ordered = [];
  for (const f of map.P0 || []) ordered.push({ rel: f, tier: 'P0' });
  for (const f of map.P1 || []) ordered.push({ rel: f, tier: 'P1' });
  const loadedPlan = ordered.filter((x, i, a) => a.findIndex((y) => y.rel === x.rel) === i).slice(0, MAX);
  const loadedNames = new Set(loadedPlan.map((x) => x.rel));
  const deferredRels = [];
  for (const f of map.P1 || []) if (!loadedNames.has(f)) deferredRels.push(f);
  for (const f of map.P2 || []) if (!loadedNames.has(f)) deferredRels.push(f);
  const dedupDeferred = deferredRels.filter((x, i, a) => a.indexOf(x) === i);

  const totalAvailable = (map.P0 ? map.P0.length : 0) + (map.P1 ? map.P1.length : 0) + (map.P2 ? map.P2.length : 0);
  const matched = loadedPlan.length + dedupDeferred.length;
  const loaded = [];
  const loadErrors = [];
  for (const item of loadedPlan) {
    const r = readSafe(item.rel);
    if (r.ok) {
      loaded.push({ file: fileRelToBasename(item.rel), path: item.rel, tier: item.tier, content: r.content });
    } else {
      loadErrors.push({ path: item.rel, tier: item.tier, error: r.error });
      loaded.push({ file: fileRelToBasename(item.rel), path: item.rel, tier: item.tier, content: null, error: r.error });
    }
  }

  return {
    ok: true,
    tool: 'knowledge-filter',
    version: VERSION,
    schema: 'global-ecommerce-intelligence/knowledge-filter',
    generatedAt: new Date().toISOString(),
    mode: 'entry',
    entry: entryName,
    name: map.name,
    maxLimit: MAX,
    warning: OVER_LIMIT_WARNING || undefined,
    matched,
    totalAvailable,
    loaded,
    loadedCount: loaded.length,
    deferred: dedupDeferred,
    loadErrors: loadErrors.length > 0 ? loadErrors : undefined,
  };
}

function searchAll(keyword) {
  const targets = [];
  for (const f of listFilesIn(REFS_DIR)) targets.push('references/' + f);
  for (const f of listFilesIn(join(REFS_DIR, 'sop'))) targets.push('references/sop/' + f);
  for (const f of listFilesIn(join(REFS_DIR, 'engine'))) targets.push('references/engine/' + f);
  const hits = [];
  // 多词 AND 语义：空格分隔，行内须同时包含全部词（大小写不敏感）
  const terms = keyword.trim().toLowerCase().split(/\s+/).filter(Boolean);
  if (terms.length === 0) {
    return { ok: false, error: '搜索词为空' };
  }
  for (const rel of targets) {
    const r = readSafe(rel);
    if (!r.ok) continue;
    const lines = r.content.split('\n');
    for (let i = 0; i < lines.length; i++) {
      const line = lines[i].toLowerCase();
      if (terms.every((t) => line.includes(t))) {
        const text = lines[i].trim().slice(0, 120);
        hits.push({ file: rel, line: i + 1, text });
      }
    }
  }
  return {
    ok: true,
    tool: 'knowledge-filter',
    version: VERSION,
    schema: 'global-ecommerce-intelligence/knowledge-filter',
    generatedAt: new Date().toISOString(),
    mode: 'search',
    keyword,
    hitCount: hits.length,
    hits: hits.slice(0, 50),
    note: hits.length > 50 ? '仅显示前50条, 请细化关键词' : undefined,
  };
}

if (search) {
  const data = searchAll(search);
  if (wantJson) {
    process.stdout.write(JSON.stringify(data, null, 2) + '\n');
  } else {
    console.log('全文检索: "' + search + '" (' + data.hitCount + ' 条)');
    console.log('='.repeat(50));
    for (const h of data.hits) console.log('  ' + h.file + ':' + h.line + '  ' + h.text);
    console.log('='.repeat(50));
  }
} else if (listMode) {
  const data = listAll();
  if (wantJson) {
    process.stdout.write(JSON.stringify(data, null, 2) + '\n');
  } else {
    console.log('知识库索引 (共' + data.totalFiles + '个md: refs ' + data.refsCount + ' + sop ' + data.sopCount + ' + engine ' + data.engineCount + ')');
    console.log('='.repeat(50));
    console.log('入口列表:');
    for (const e of data.entries) console.log('  ' + e.entry.padEnd(18) + ' ' + e.name);
    console.log('\n加载上限: ' + data.loadLimit + '个/次');
    console.log('='.repeat(50));
  }
} else if (entry) {
  const data = resolveEntry(entry);
  if (data.error) {
    const payload = { ok: false, error: data.error, available: data.available };
    if (wantJson) {
      process.stdout.write(JSON.stringify(payload) + '\n');
    } else {
      console.error('错误: ' + data.error);
      console.error('可用入口: ' + data.available.join(', '));
    }
    process.exit(1);
  }
  if (wantJson) {
    process.stdout.write(JSON.stringify(data, null, 2) + '\n');
  } else {
    console.log('知识加载策略 — ' + data.name);
    console.log('='.repeat(50));
    console.log('立即加载(' + data.loadedCount + '/' + data.maxLimit + '):');
    for (const f of data.loaded) {
      const mark = f.content ? '✓' : '✗';
      const err = f.error ? '  (' + f.error + ')' : '';
      console.log('  ' + mark + ' [' + f.tier + '] ' + f.path + err);
    }
    if (data.deferred.length) {
      console.log('按需加载(仅记路径,' + data.deferred.length + '个):');
      for (const f of data.deferred) console.log('  [按需] ' + f);
    }
    console.log('\n上限: ' + data.maxLimit + '个/次  匹配总数: ' + data.matched + '/' + data.totalAvailable);
    if (data.warning) console.log(data.warning);
    if (data.loadErrors) console.log('加载失败: ' + data.loadErrors.length + '项');
    console.log('='.repeat(50));
  }
} else {
  console.error('用法: node references/scripts/knowledge-filter.mjs --list --json | --entry <入口> [--max N] --json | --search <关键词> --json');
  console.error('入口: ' + Object.keys(ENTRY_MAP).join(', '));
  process.exit(1);
}
