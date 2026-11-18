#!/usr/bin/env node
/**
 * price-monitor.mjs — 竞品价格快照与异动监控 (v1.0.7)
 *
 * 记录指定商品的价格观测快照到本地存储(OS 临时目录), 与上一次快照对比,
 * 当变化幅度超过 --threshold 时标记 alert。
 * 存储位置: <OS tmp>/gbi-price-store/<product>.json, 不污染 Skill 包。
 *
 * 合规核实说明:
 *   本工具不做任何自动抓取, 价格由用户按官方合规渠道观测后录入(--price),
 *   并记录观测来源(--source)。自动爬取竞品价违反平台服务条款, 不在能力范围。
 *
 * 用法:
 *   node references/scripts/price-monitor.mjs --product B0XXXXXX --price 29.99 --json
 *   node references/scripts/price-monitor.mjs --product B0XXXXXX --price 25.50 --threshold 5 --source official --json
 *   node references/scripts/price-monitor.mjs --product B0XXXXXX --export out.json --json
 *   node references/scripts/price-monitor.mjs --list --json
 *   node references/scripts/price-monitor.mjs --dry-run --product B0XXXXXX --price 29.99 --json
 *   node references/scripts/price-monitor.mjs --version
 *
 * 参数:
 *   --product   商品标识(ASIN/URL/关键词)
 *   --price     本次观测价
 *   --threshold 异动阈值%(默认5), |变化|>阈值 触发 alert
 *   --source    观测来源: official(平台官方渠道)/self-observed(自行观测,默认)/manual(手动录入)
 *   --export    导出该商品观测记录到文件(.json/.csv)
 *   --list      列出已跟踪商品
 *   --dry-run   不写入存储(仅演示)
 *   --json      输出JSON
 */

import { readFileSync, writeFileSync, mkdirSync, existsSync, readdirSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';

const VERSION = '1.0.7';
const args = process.argv.slice(2);
const wantJson = args.includes('--json');
const listMode = args.includes('--list');
const dryRun = args.includes('--dry-run');
if (args.includes('--version')) {
  process.stdout.write(VERSION + '\n');
  process.exit(0);
}
const KNOWN_FLAGS = new Set(['--product', '--price', '--threshold', '--source', '--export', '--list', '--dry-run', '--json', '--version']);
const unknownFlags = args.filter((a) => a.startsWith('--') && !KNOWN_FLAGS.has(a));
if (unknownFlags.length) {
  console.error('未知参数: ' + unknownFlags.join(' ') + '\n可用参数: --product <商品> --price <价> --threshold <N> --source <official|self-observed|manual> --export <路径> --list --dry-run --json');
  process.exit(1);
}
function getArg(name) {
  const i = args.indexOf('--' + name);
  return i >= 0 ? args[i + 1] : null;
}
const product = (getArg('product') || '').trim();
const priceRaw = Number(getArg('price'));
const thresholdArg = getArg('threshold');
const thresholdRaw = thresholdArg === null ? null : Number(thresholdArg);
if (thresholdRaw !== null && !(Number.isFinite(thresholdRaw) && thresholdRaw > 0 && thresholdRaw <= 50)) {
  console.error('--threshold 须为 (0,50] 的数字(百分比)');
  process.exit(1);
}
const threshold = thresholdRaw === null ? 5 : thresholdRaw;
const sourceRaw = (getArg('source') || '').toLowerCase();
const SOURCES = ['official', 'self-observed', 'manual'];
if (getArg('source') !== null && !SOURCES.includes(sourceRaw)) {
  console.error('--source 仅支持: official / self-observed / manual');
  process.exit(1);
}
const source = sourceRaw || 'self-observed';
const exportPath = (getArg('export') || '').trim();
const SANITY_DELTA_PCT = 40; // 相对上次观测偏差超过该值 -> 提示核实观测来源
const STORE_DIR = join(tmpdir(), 'gbi-price-store');

function sanitize(name) {
  return name.replace(/[^a-zA-Z0-9_\-\u4e00-\u9fa5]/g, '_').slice(0, 60) || 'product';
}
function readStore(key) {
  const p = join(STORE_DIR, key + '.json');
  if (!existsSync(p)) return { key, history: [] };
  try {
    return JSON.parse(readFileSync(p, 'utf-8'));
  } catch {
    return { key, history: [] };
  }
}
function writeStore(key, store) {
  if (dryRun) return;
  if (!existsSync(STORE_DIR)) mkdirSync(STORE_DIR, { recursive: true });
  writeFileSync(join(STORE_DIR, key + '.json'), JSON.stringify(store, null, 2), 'utf-8');
}

function listAll() {
  if (!existsSync(STORE_DIR)) return [];
  return readdirSync(STORE_DIR)
    .filter((f) => f.endsWith('.json'))
    .map((f) => {
      try {
        const s = JSON.parse(readFileSync(join(STORE_DIR, f), 'utf-8'));
        const last = s.history[s.history.length - 1];
        return { key: s.key, lastPrice: last ? last.price : null, lastTs: last ? last.ts : null, lastSource: last && last.source ? last.source : null, snapshots: s.history.length };
      } catch {
        return { key: f.replace(/\.json$/, ''), error: 'read-failed' };
      }
    });
}

if (exportPath) {
  if (!product) {
    console.error('用法: --export 需同时指定 --product');
    process.exit(1);
  }
  const store = readStore(sanitize(product));
  if (exportPath.toLowerCase().endsWith('.csv')) {
    const lines = ['ts,price,source'];
    for (const h of store.history) lines.push([h.ts, h.price, h.source || ''].join(','));
    writeFileSync(exportPath, lines.join('\n') + '\n', 'utf-8');
  } else {
    writeFileSync(exportPath, JSON.stringify(store, null, 2) + '\n', 'utf-8');
  }
  const payload = {
    ok: true, tool: 'price-monitor', version: VERSION,
    schema: 'global-ecommerce-intelligence/price-monitor',
    generatedAt: new Date().toISOString(), mode: 'export',
    product, exportedTo: exportPath, snapshots: store.history.length,
  };
  if (wantJson) process.stdout.write(JSON.stringify(payload, null, 2) + '\n');
  else console.log('已导出 ' + product + ' 观测记录 ' + store.history.length + ' 条 → ' + exportPath);
  process.exit(0);
}

if (listMode) {
  const items = listAll();
  const payload = {
    ok: true, tool: 'price-monitor', version: VERSION,
    schema: 'global-ecommerce-intelligence/price-monitor',
    generatedAt: new Date().toISOString(), mode: 'list',
    trackedCount: items.length, items,
  };
  if (wantJson) process.stdout.write(JSON.stringify(payload, null, 2) + '\n');
  else {
    console.log('已跟踪商品 (' + items.length + ')');
    console.log('='.repeat(50));
    for (const it of items) console.log('  ' + it.key + '  last=' + (it.lastPrice ?? '-') + ' (' + (it.lastTs || '-') + ') source=' + (it.lastSource || '-') + ' snapshots=' + it.snapshots);
    console.log('='.repeat(50));
  }
  process.exit(0);
}

if (!product || !Number.isFinite(priceRaw) || priceRaw <= 0) {
  console.error('用法: node references/scripts/price-monitor.mjs --product <商品> --price <价格> [--source official|self-observed|manual] [--threshold N] [--json]');
  process.exit(1);
}

const key = sanitize(product);
const store = readStore(key);
const prev = store.history[store.history.length - 1];
let deltaPct = null;
if (prev && prev.price > 0) deltaPct = Math.round(((priceRaw - prev.price) / prev.price) * 1000) / 10;
const alert = deltaPct !== null && Math.abs(deltaPct) > threshold;
const sanityNote = deltaPct !== null && Math.abs(deltaPct) > SANITY_DELTA_PCT
  ? '相对上次观测偏差超过 ' + SANITY_DELTA_PCT + '%, 请核实该观测价来源是否官方/真实有效'
  : null;
store.history.push({ ts: new Date().toISOString(), price: priceRaw, source });
writeStore(key, store);

const payload = {
  ok: true, tool: 'price-monitor', version: VERSION,
  schema: 'global-ecommerce-intelligence/price-monitor',
  generatedAt: new Date().toISOString(), mode: 'snapshot',
  product, price: priceRaw, thresholdPct: threshold, source,
  previousPrice: prev ? prev.price : null,
  previousTs: prev ? prev.ts : null,
  deltaPct,
  alert,
  sanityNote,
  snapshots: store.history.length,
  stored: !dryRun,
  note: source !== 'official' ? '该价格为' + (source === 'manual' ? '手动录入' : '自行观测') + ', 非官方实时价; 决策前建议以平台官方渠道核实' : null,
  advice: alert ? '价格异动超过阈值, 建议核实竞品调价意图(清库存/新品/促销)' : '价格在阈值内, 保持关注',
};

if (wantJson) process.stdout.write(JSON.stringify(payload, null, 2) + '\n');
else {
  console.log('价格快照: ' + product + ' = ' + priceRaw + (dryRun ? ' (dry-run 未写入)' : '') + ' [来源: ' + source + ']');
  console.log('='.repeat(50));
  console.log('  上次: ' + (prev ? prev.price + ' (' + prev.ts + ')' : '无'));
  console.log('  变化: ' + (deltaPct === null ? '首次快照' : (deltaPct >= 0 ? '+' : '') + deltaPct + '%'));
  console.log('  异动: ' + (alert ? '[异动] 超过阈值 ' + threshold + '%' : '未触发 (阈值 ' + threshold + '%)'));
  if (sanityNote) console.log('  核实: ' + sanityNote);
  if (payload.note) console.log('  提示: ' + payload.note);
  console.log('  快照数: ' + store.history.length);
  console.log('='.repeat(50));
}
process.exit(0);
