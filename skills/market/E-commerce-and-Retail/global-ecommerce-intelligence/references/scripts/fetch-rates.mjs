#!/usr/bin/env node
/**
 * fetch-rates.mjs — 实时汇率抓取工具 (v1.0.7)
 *
 * 从公开免费汇率 API 并行抓取实时汇率，输出与 profit_calculator.py 内置
 * FX_RATES 完全兼容的格式（基准 CNY：1 单位外币 = X 人民币）。
 *
 * 真实数据化原则（反幻觉）：
 *   - 只输出 API 真实返回的汇率，绝不编造/内插缺失币种
 *   - 输出带 fetchedAt（抓取时间）+ source（实际命中的源）+ disclaimer
 *   - 已知汇率对越界时输出 sanity 告警（不篡改数据，仅提示核实）
 *   - 全部数据源失败 → 尝试 OS 临时目录 TTL 缓存；仍失败 → exit 1 + JSON 错误
 *
 * 用法：
 *   node references/scripts/fetch-rates.mjs --json              # 全量输出（基准 CNY）
 *   node references/scripts/fetch-rates.mjs --base USD --json   # 指定基准
 *   node references/scripts/fetch-rates.mjs --no-cache --json   # 跳过缓存直连
 *   node references/scripts/fetch-rates.mjs --snapshot fx.json  # 抓取后额外落盘快照(基准CNY, 兼容内置FX_RATES格式)
 *   node references/scripts/fetch-rates.mjs --version
 *
 * 依赖：Node ≥18（全局 fetch）；无 API key。
 */

import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { readFileSync, writeFileSync } from 'node:fs';

const VERSION = '1.0.7';
const args = process.argv.slice(2);
const idx = args.indexOf('--base');
const BASE = idx >= 0 && args[idx + 1] ? args[idx + 1].toUpperCase() : 'CNY';
const wantJson = args.includes('--json');
const useCache = !args.includes('--no-cache');
const snapshotPath = (() => { const i = args.indexOf('--snapshot'); return i >= 0 ? args[i + 1] : null; })();
if (args.includes('--version')) {
  process.stdout.write(VERSION + '\n');
  process.exit(0);
}
const KNOWN_FLAGS = new Set(['--base', '--json', '--no-cache', '--snapshot', '--version']);
const unknownFlags = args.filter((a) => a.startsWith('--') && !KNOWN_FLAGS.has(a));
if (unknownFlags.length) {
  console.error('未知参数: ' + unknownFlags.join(' ') + '\n可用参数: --base <币种> --no-cache --snapshot <路径> --json');
  process.exit(1);
}

// 多源并行：公开、免费、无需 key。任一成功即返回。
const SOURCES = [
  {
    name: 'open.er-api.com (free, no key)',
    url: 'https://open.er-api.com/v6/latest/USD',
    parse: (j) => j && j.result === 'success' && j.rates ? j.rates : null,
  },
  {
    name: 'api.frankfurter.app (ECB data)',
    url: 'https://api.frankfurter.app/latest?from=USD',
    parse: (j) => j && j.rates ? j.rates : null,
  },
  {
    name: 'api.exchangerate-api.com (free, no key)',
    url: 'https://api.exchangerate-api.com/v4/latest/USD',
    parse: (j) => j && j.rates ? j.rates : null,
  },
];

const TIMEOUT_MS = 8000;
const CACHE_TTL_MS = 10 * 60 * 1000;
const CACHE_FILE = join(tmpdir(), 'gbi-fx-cache-' + BASE + '.json');

async function fetchSource(src) {
  const ctrl = new AbortController();
  const timer = setTimeout(() => ctrl.abort(), TIMEOUT_MS);
  try {
    const res = await fetch(src.url, { signal: ctrl.signal, headers: { 'User-Agent': 'global-ecommerce-intelligence/' + VERSION } });
    if (!res.ok) throw new Error('HTTP ' + res.status);
    const j = await res.json();
    const rates = src.parse(j);
    if (!rates || typeof rates !== 'object') throw new Error('响应格式异常');
    return rates;
  } finally {
    clearTimeout(timer);
  }
}

function fail(message) {
  const payload = { ok: false, error: message, hint: '请使用 profit_calculator.py 内置快照（标注"非实时"），或稍后重试' };
  if (wantJson) process.stdout.write(JSON.stringify(payload, null, 2) + '\n');
  else console.error('汇率抓取失败: ' + message);
  process.exit(1);
}

function readCache() {
  try {
    const raw = readFileSync(CACHE_FILE, 'utf8');
    const c = JSON.parse(raw);
    if (c && c.rates && typeof c.rates === 'object') return c;
  } catch (_) { /* 缓存缺失或损坏则忽略 */ }
  return null;
}

function writeCache(payload) {
  try {
    writeFileSync(CACHE_FILE, JSON.stringify(payload), 'utf8');
  } catch (_) { /* 缓存写入失败不影响主流程 */ }
}

// 已知汇率对 sanity 区间（基准 CNY 时，1 外币 = X 人民币的经验合理区间）。越界仅告警，不篡改数据。
function sanityCheck(rates) {
  const warnings = [];
  const checks = [
    { code: 'USD', lo: 5, hi: 9 },
    { code: 'EUR', lo: 6, hi: 10 },
    { code: 'GBP', lo: 7, hi: 12 },
    { code: 'JPY', lo: 0.02, hi: 0.07 },
    { code: 'KRW', lo: 0.003, hi: 0.008 },
  ];
  for (const c of checks) {
    const v = rates[c.code];
    if (typeof v === 'number' && (v < c.lo || v > c.hi)) {
      warnings.push(c.code + '=' + v + ' 超出经验区间 [' + c.lo + ',' + c.hi + ']，请核实');
    }
  }
  return warnings;
}

(async () => {
  let ratesUSD = null;
  let sourceName = null;
  const errors = [];
  // 并行抓取所有源，取首个成功
  const settled = await Promise.allSettled(SOURCES.map((src) => fetchSource(src)));
  for (let i = 0; i < settled.length; i++) {
    if (settled[i].status === 'fulfilled') {
      ratesUSD = settled[i].value;
      sourceName = SOURCES[i].name;
      break;
    }
    errors.push(SOURCES[i].name + ': ' + (settled[i].reason && settled[i].reason.name === 'AbortError' ? '超时' : (settled[i].reason && settled[i].reason.message || '失败')));
  }

  const now = new Date().toISOString();
  if (ratesUSD) {
    const usdPerBase = BASE === 'USD' ? 1 : (ratesUSD[BASE] ?? null);
    if (usdPerBase === null || typeof usdPerBase !== 'number') {
      fail('数据源不含基准货币 ' + BASE);
    }
    // 与 profit_calculator 内置 FX_RATES 键集对齐（不编造缺失币种）
    const SUPPORTED = ['CNY', 'USD', 'EUR', 'GBP', 'JPY', 'KRW', 'SGD', 'THB', 'MYR', 'PHP', 'VND', 'IDR', 'BRL', 'MXN', 'AUD', 'CAD', 'AED', 'SAR', 'INR', 'TRY'];
    const rates = {};
    const missing = [];
    for (const code of SUPPORTED) {
      const perUSD_fx = ratesUSD[code];
      if (typeof perUSD_fx === 'number' && perUSD_fx > 0) {
        // 1 code = (1 USD 兑换的外币量) 分之 (1 USD 兑换的基准量) 基准 = 1 外币 = X 基准
        rates[code] = Number((usdPerBase / perUSD_fx).toFixed(6));
      } else {
        missing.push(code);
      }
    }
    let snapshotSaved = null;
    const payload = {
      ok: true,
      tool: 'fetch-rates',
      version: VERSION,
      schema: 'global-ecommerce-intelligence/fetch-rates',
      generatedAt: now,
      base: BASE,
      rates,
      fetchedAt: now,
      source: sourceName,
      missingInSource: missing.length ? missing : undefined,
      // 已知汇率 sanity 区间按"基准 CNY"标定; 非 CNY 基准不套用, 否则会误报。
      sanityWarnings: BASE === 'CNY' ? sanityCheck(rates) : [],
      disclaimer: '实时汇率（抓取时间见 fetchedAt）；profit_calculator 内置 FX_RATES 为历史快照，两者不一致时以本输出为准；实际交易汇率请以银行/支付渠道为准',
    };
    if (useCache) writeCache(payload);
    if (snapshotPath) {
      const snap = {
        schema: 'global-ecommerce-intelligence/fx-snapshot',
        version: VERSION,
        base: BASE,
        rates,
        snapshotAt: now,
        source: sourceName,
        disclaimer: '实时汇率快照; 与 profit_calculator.py 内置 FX_RATES 格式兼容, 可据此更新离线快照',
      };
      try {
        writeFileSync(snapshotPath, JSON.stringify(snap, null, 2) + '\n', 'utf8');
        snapshotSaved = snapshotPath;
      } catch (_) { /* 快照写入失败不影响主输出 */ }
    }
    payload.snapshotSaved = snapshotSaved;
    if (wantJson) {
      process.stdout.write(JSON.stringify(payload, null, 2) + '\n');
    } else {
      console.log('实时汇率 (基准 ' + BASE + ') — ' + sourceName);
      console.log('═'.repeat(48));
      for (const [k, v] of Object.entries(rates)) {
        console.log('  ' + k.padEnd(5) + ' = ' + v.toFixed(4) + ' ' + BASE);
      }
      console.log('  ───────────────────────────────');
      console.log('  抓取时间: ' + payload.fetchedAt);
      if (payload.missingInSource) console.log('  源缺失币种: ' + payload.missingInSource.join(', '));
      if (payload.sanityWarnings && payload.sanityWarnings.length) console.log('  [注意] ' + payload.sanityWarnings.join('; '));
      console.log('═'.repeat(48));
    }
    process.exit(0);
  }

  // 全部源失败 → 尝试缓存兜底（标记为缓存值）
  const cached = useCache ? readCache() : null;
  if (cached) {
    const stale = (Date.now() - new Date(cached.fetchedAt || cached.generatedAt).getTime()) > CACHE_TTL_MS;
    const payload = {
      ok: true,
      tool: 'fetch-rates',
      version: VERSION,
      schema: 'global-ecommerce-intelligence/fetch-rates',
      generatedAt: now,
      base: BASE,
      rates: cached.rates,
      fetchedAt: cached.fetchedAt || cached.generatedAt,
      source: cached.source || '缓存兜底',
      cached: true,
      stale: stale,
      staleNote: '实时源不可用，使用 ' + (stale ? '过期' : '10分钟TTL内') + ' 缓存值，需注意时效',
      missingInSource: cached.missingInSource,
      disclaimer: cached.disclaimer || '缓存兜底汇率，非本轮实时抓取；请以银行/支付渠道为准',
    };
    if (wantJson) process.stdout.write(JSON.stringify(payload, null, 2) + '\n');
    else console.error('实时源不可用，使用缓存兜底（' + (stale ? '已过期' : 'TTL内') + '）');
    process.exit(0);
  }
  fail('所有数据源不可用且无缓存可用 [' + errors.join(' | ') + ']');
})().catch((e) => fail(e.message));
