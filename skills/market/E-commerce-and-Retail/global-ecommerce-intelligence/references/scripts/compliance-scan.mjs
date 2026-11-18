#!/usr/bin/env node
/**
 * compliance-scan.mjs — 营销与 Listing 文案合规扫描器 (v1.0.7)
 *
 * 依据 SOP-04 合规审查流程实现的规则级扫描：
 *   - 绝对化用语：广告法明令禁止的极限表述
 *   - 医疗与功效宣称：普通商品不得使用
 *   - 促销与价格表述：须有真实、可举证依据
 *   - 平台红线与资质冒用
 *   - 商标词提示：仅提示复核，不构成侵权判定
 *
 * 匹配口径：
 *   - 扫描全文中每一处出现，不只取首处
 *   - 同一段文字被多个词条重叠命中时合并为一个区间、计一处，代表词取区间内最长词条；
 *     避免"全网最低价"被拆成 4 处命中而夸大风险
 *   - 拉丁字母词条启用词边界，避免 small 命中 mall、shelves 命中 lv 这类子串误报
 *
 * 说明：本工具为规则级启发式初筛，不替代平台审核与法律终审，命中项须按语境人工复核。
 *
 * 用法：
 *   node references/scripts/compliance-scan.mjs --text "全网最低价，百分百有效" --platform amazon --json
 *   node references/scripts/compliance-scan.mjs --file listing.txt --platform taobao
 *   node references/scripts/compliance-scan.mjs --version
 *
 * 参数：
 *   --text       待扫描文案
 *   --file       文本文件路径（UTF-8）
 *   --platform   amazon / taobao / tiktok / shopee / generic
 *   --json       输出 JSON
 *
 * 退出码：0=无命中；1=有命中或参数错误；2=规则库不可用
 */

import { readFileSync, existsSync } from 'node:fs';
import { resolve } from 'node:path';

const VERSION = '1.0.7';
const TOOL = 'compliance-scan';
const SCHEMA = 'global-ecommerce-intelligence/' + TOOL;

const args = process.argv.slice(2);
const wantJson = args.includes('--json');

function getArg(name) {
  const i = args.indexOf('--' + name);
  return i >= 0 ? args[i + 1] : null;
}

function emitError(message, code) {
  if (wantJson) {
    process.stdout.write(
      JSON.stringify({ ok: false, tool: TOOL, version: VERSION, schema: SCHEMA, error: message }, null, 2) + '\n'
    );
  }
  process.stderr.write('错误: ' + message + '\n');
  process.exit(code);
}

if (args.includes('--version')) {
  process.stdout.write(VERSION + '\n');
  process.exit(0);
}
const KNOWN_FLAGS = new Set(['--text', '--file', '--platform', '--json', '--version']);
const unknownFlags = args.filter((a) => a.startsWith('--') && !KNOWN_FLAGS.has(a));
if (unknownFlags.length) {
  emitError('未知参数: ' + unknownFlags.join(' ') + ' (可用: --text/--file/--platform/--json)', 1);
}

// —— 规则库（单一数据源 compliance-rules.json，与 listing-scorer.mjs 共用）——
let RULES;
try {
  RULES = JSON.parse(readFileSync(new URL('./compliance-rules.json', import.meta.url), 'utf-8'));
} catch (e) {
  emitError('规则库读取失败: ' + e.message, 2);
}

const CATEGORIES = [
  { key: 'absolute_terms', label: '绝对化用语', risk: '高' },
  { key: 'medical_terms', label: '医疗/功效宣称', risk: '高' },
  { key: 'price_terms', label: '促销/价格表述', risk: '中' },
];
const RED_LINE_LABEL = '平台红线/冒用';
const RED_LINE_RISK = '高';
const RISK_ORDER = { 中: 1, 高: 2 };

const ESCAPE_RE = /[.*+?^${}()|[\]\\]/g;
const ASCII_WORD_HEAD = /^[A-Za-z0-9_]/;
const ASCII_WORD_TAIL = /[A-Za-z0-9_]$/;

function escapeRe(s) {
  return String(s).replace(ESCAPE_RE, '\\$&');
}

/**
 * 编译词条正则。
 * 拉丁字母词条首尾加词边界，中文词条不加（中文无空格分词，\b 对汉字行为不可靠）。
 */
function compileTerm(term) {
  const head = ASCII_WORD_HEAD.test(term) ? '\\b' : '';
  const tail = ASCII_WORD_TAIL.test(term) ? '\\b' : '';
  return new RegExp(head + escapeRe(term) + tail, 'gi');
}

/** 收集某一类词条在全文中的所有出现 */
function collect(text, terms, label, risk) {
  const out = [];
  for (const term of terms) {
    if (typeof term !== 'string' || term.length === 0) continue;
    let re;
    try {
      re = compileTerm(term);
    } catch {
      continue;
    }
    let m;
    while ((m = re.exec(text)) !== null) {
      if (m[0].length === 0) {
        re.lastIndex += 1;
        continue;
      }
      out.push({ start: m.index, end: m.index + m[0].length, term, category: label, risk });
    }
  }
  return out;
}

/**
 * 合并重叠命中。
 * 同一区间只计一处：代表词取区间内最长词条，风险取最高，来源词清单保留以便复核。
 */
function mergeHits(hits) {
  const ordered = hits
    .slice()
    .sort(
      (a, b) =>
        a.start - b.start ||
        b.end - b.start - (a.end - a.start) ||
        (a.term < b.term ? -1 : a.term > b.term ? 1 : 0)
    );
  const merged = [];
  for (const h of ordered) {
    const last = merged[merged.length - 1];
    if (last && h.start < last.end) {
      last.end = Math.max(last.end, h.end);
      if (!last.terms.includes(h.term)) last.terms.push(h.term);
      if (!last.categories.includes(h.category)) last.categories.push(h.category);
      if ((RISK_ORDER[h.risk] || 0) > (RISK_ORDER[last.risk] || 0)) last.risk = h.risk;
      if (h.end - h.start > last.bestLen) {
        last.bestLen = h.end - h.start;
        last.term = h.term;
      }
      continue;
    }
    merged.push({
      start: h.start,
      end: h.end,
      term: h.term,
      category: h.category,
      risk: h.risk,
      terms: [h.term],
      categories: [h.category],
      bestLen: h.end - h.start,
    });
  }
  return merged;
}

function scan(text, platform) {
  let raw = [];
  for (const c of CATEGORIES) {
    const terms = (RULES.rules && RULES.rules[c.key]) || [];
    raw = raw.concat(collect(text, terms, c.label, c.risk));
  }
  const redLine = (RULES.rules && RULES.rules.platform_red_line) || {};
  const redTerms = redLine[platform] || redLine.generic || [];
  raw = raw.concat(collect(text, redTerms, RED_LINE_LABEL, RED_LINE_RISK));

  const merged = mergeHits(raw);
  const hits = merged.map((h) => ({
    category: h.category,
    categories: h.categories,
    term: h.term,
    terms: h.terms,
    matched: text.slice(h.start, h.end),
    index: h.start,
    risk: h.risk,
    context: text.slice(Math.max(0, h.start - 8), h.end + 8),
  }));

  const trademarkTerms = (RULES.rules && RULES.rules.trademark_hint) || [];
  const trademarkHints = trademarkTerms.filter(
    (t) => typeof t === 'string' && t.length > 0 && compileTerm(t).test(text)
  );

  return { hits, trademarkHints, rawCount: raw.length };
}

// —— 输入处理 ——
const text = getArg('text');
const file = getArg('file');
const platform = (getArg('platform') || 'generic').toLowerCase();
const SUPPORTED_PLATFORMS = ['amazon', 'taobao', 'tiktok', 'shopee', 'generic'];
if (!SUPPORTED_PLATFORMS.includes(platform)) {
  emitError('不支持的平台: ' + platform + '（可选: ' + SUPPORTED_PLATFORMS.join(', ') + '）', 1);
}

let source = typeof text === 'string' ? text : '';
if (!source && file) {
  const abs = resolve(process.cwd(), file);
  if (!existsSync(abs)) emitError('文件不存在: ' + abs, 1);
  try {
    source = readFileSync(abs, 'utf-8');
  } catch (e) {
    emitError('文件读取失败: ' + e.message, 1);
  }
}
if (!source.trim()) {
  emitError('用法: node references/scripts/compliance-scan.mjs --text <文案> --platform <平台> [--json]', 1);
}

const r = scan(source, platform);
const risk = r.hits.length === 0 ? 'low' : r.hits.some((h) => h.risk === '高') ? 'high' : 'medium';

const payload = {
  ok: true,
  tool: TOOL,
  version: VERSION,
  schema: SCHEMA,
  generatedAt: new Date().toISOString(),
  platform,
  textLength: source.length,
  risk,
  hitCount: r.hits.length,
  rawMatchCount: r.rawCount,
  hits: r.hits,
  trademarkHints: r.trademarkHints,
  note: '规则级启发式初筛；重叠命中已合并计一处；命中项须按语境复核，不替代平台审核与法律终审',
};

if (wantJson) {
  process.stdout.write(JSON.stringify(payload, null, 2) + '\n');
} else {
  console.log(
    '合规扫描 (' + platform + ') 去重后 ' + r.hits.length + ' 处命中' +
      (r.rawCount !== r.hits.length ? '（原始 ' + r.rawCount + ' 处，已合并重叠）' : '')
  );
  console.log('='.repeat(50));
  for (const h of r.hits) {
    console.log('  [' + h.risk + '] ' + h.category + ' 「' + h.term + '」 位置 ' + h.index + ' …' + h.context + '…');
    if (h.terms.length > 1) console.log('       合并自: ' + h.terms.join(', '));
  }
  if (r.trademarkHints.length) console.log('  商标提示: ' + r.trademarkHints.join(', ') + '（仅提示复核）');
  console.log('  说明: ' + payload.note);
  console.log('='.repeat(50));
}

process.exit(r.hits.length > 0 ? 1 : 0);
