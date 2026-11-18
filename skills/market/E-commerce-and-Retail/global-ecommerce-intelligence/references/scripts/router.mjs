#!/usr/bin/env node
/**
 * router.mjs — 意图路由器 (v1.0.7)
 *
 * 把用户的自然语言意图映射到知识入口与推荐工具, 供编排/助手快速定位。
 * 入口清单与 knowledge-filter 保持一致(通过 --list 动态读取, 避免双源);
 * 本文件仅维护"意图关键词→入口"与"入口→推荐工具"两类唯一映射。
 *
 * 用法:
 *   node references/scripts/router.mjs --intent "算一下利润" --json
 *   node references/scripts/router.mjs --intent "怎么选品" --json
 *   node references/scripts/router.mjs --list --json
 *   node references/scripts/router.mjs --version
 *
 * 参数:
 *   --intent   用户意图文本
 *   --list     列出全部入口映射
 *   --json     输出JSON
 */

import { execFileSync } from 'node:child_process';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const VERSION = '1.0.7';
const __dirname = dirname(fileURLToPath(import.meta.url));
const args = process.argv.slice(2);
const wantJson = args.includes('--json');
const listMode = args.includes('--list');
if (args.includes('--version')) {
  process.stdout.write(VERSION + '\n');
  process.exit(0);
}
const KNOWN_FLAGS = new Set(['--json', '--list', '--version', '--intent']);
const unknownFlags = args.filter((a) => a.startsWith('--') && !KNOWN_FLAGS.has(a));
if (unknownFlags.length) {
  console.error('未知参数: ' + unknownFlags.join(' ') + '\n可用参数: --intent <意图文本> --list --json');
  process.exit(1);
}
function getArg(name) {
  const i = args.indexOf('--' + name);
  return i >= 0 ? args[i + 1] : null;
}
const intent = (getArg('intent') || '').trim();

// 意图关键词 → 入口(唯一映射)
const INTENT_KEYWORDS = {
  beginner: ['新手', '入门', '第一次开店', '从零开始', '开店流程', '小白'],
  selection: ['选品', '选什么', '品类', '蓝海', '机会产品'],
  compliance: ['合规', '违禁', '审核', '敏感词', '红线', '认证'],
  pricing: ['定价', '价格分析', '价格带', '定价策略', '价格合适', '这个价格', '价格是否合适'],
  profit: ['利润', '成本', '赚', '盈利', '报价', '毛利'],
  'cross-border': ['跨境', '物流', '清关', '关税', '海外仓', '汇率'],
  review: ['评价', '评论', 'review', '情感', '口碑'],
  monitor: ['价格监控', '竞品价格', '盯价', '比价'],
  trends: ['趋势', '市场', '行业', '大盘', '预测'],
  listing: ['listing', '优化', '标题', '五点', '关键词优化', 'ai搜索', 'agent推荐'],
  tiktok: ['tiktok', '抖音', '短视频', '直播带货', '内容电商'],
  ppc: ['广告', 'ppc', '投放', 'acos', '出价'],
  inventory: ['库存', '补货', '断货', '备货', '仓储'],
};

// 入口 → 推荐工具(唯一映射)
const ENTRY_SCRIPTS = {
  beginner: ['guidance.mjs'],
  selection: ['bsr_analyzer.py'],
  compliance: ['compliance-scan.mjs'],
  pricing: ['price-elasticity.mjs', 'price-monitor.mjs'],
  profit: ['profit_calculator.py', 'fetch-rates.mjs', 'tax_calculator.py'],
  'cross-border': ['fetch-rates.mjs', 'tax_calculator.py'],
  review: ['sentiment_analyzer.py'],
  monitor: ['price-monitor.mjs'],
  trends: ['bsr_analyzer.py'],
  listing: ['listing-scorer.mjs', 'compliance-scan.mjs', 'agent-readiness.mjs'],
  tiktok: ['listing-scorer.mjs'],
  ppc: ['price-elasticity.mjs'],
  inventory: ['inventory_calculator.py'],
};

// 动态读取 knowledge-filter 入口清单(单一数据源)
function loadEntries() {
  try {
    const out = execFileSync(process.execPath, [join(__dirname, 'knowledge-filter.mjs'), '--list', '--json'], { encoding: 'utf-8', timeout: 15000 });
    const data = JSON.parse(out);
    return data.entries || [];
  } catch {
    return [];
  }
}

function route(text) {
  const lower = (text || '').toLowerCase();
  let matched = [];
  for (const [entry, kws] of Object.entries(INTENT_KEYWORDS)) {
    if (kws.some((kw) => lower.includes(kw))) matched.push(entry);
  }
  const primary = matched[0] || null;
  return {
    matched,
    primary,
    scripts: primary ? (ENTRY_SCRIPTS[primary] || []) : [],
  };
}

if (listMode) {
  const entries = loadEntries();
  const payload = {
    ok: true, tool: 'router', version: VERSION,
    schema: 'global-ecommerce-intelligence/router',
    generatedAt: new Date().toISOString(), mode: 'list',
    entries: entries.map((e) => ({
      entry: e.entry, name: e.name,
      intentKeywords: INTENT_KEYWORDS[e.entry] || [],
      scripts: ENTRY_SCRIPTS[e.entry] || [],
    })),
  };
  if (wantJson) process.stdout.write(JSON.stringify(payload, null, 2) + '\n');
  else {
    console.log('意图路由表');
    console.log('='.repeat(56));
    for (const e of payload.entries) {
      console.log('  ' + e.entry.padEnd(14) + ' 触发词: ' + e.intentKeywords.join('/') + '  → ' + e.scripts.join(', '));
    }
    console.log('='.repeat(56));
  }
  process.exit(0);
}

if (!intent) {
  console.error('用法: node references/scripts/router.mjs --intent <意图文本> --json | --list --json');
  process.exit(1);
}

const r = route(intent);
const payload = {
  ok: true, tool: 'router', version: VERSION,
  schema: 'global-ecommerce-intelligence/router',
  generatedAt: new Date().toISOString(), mode: 'route',
  intent,
  matched: r.matched,
  primary: r.primary,
  scripts: r.scripts,
  note: r.primary ? null : '未匹配到明确入口, 建议由助手直接判断或结合 --list 查看全部入口',
};
if (wantJson) process.stdout.write(JSON.stringify(payload, null, 2) + '\n');
else {
  console.log('意图: "' + intent + '"');
  console.log('='.repeat(50));
  console.log('  匹配入口: ' + (r.matched.length ? r.matched.join(', ') : '无'));
  console.log('  主入口: ' + (r.primary || '—'));
  console.log('  推荐工具: ' + (r.scripts.length ? r.scripts.join(', ') : '—'));
  console.log('  提示: 先用 knowledge-filter --entry <入口> 加载知识, 再跑推荐工具');
  console.log('='.repeat(50));
}
process.exit(0);
