#!/usr/bin/env node
/**
 * listing-scorer.mjs — Listing 质量评分器 (v1.0.7)
 *
 * 严格按 SOP-10 的 22 项 100 分量表实现（标题20/主图副图20/五点15/描述A+10/
 * Backend关键词10/基础信息10/合规15；20-22 为合规一票否决项）。
 * 文本可自动打分项：标题/五点/描述/搜索词/违禁词；主图/副图/A+认证/基础信息
 * 为人工确认项（--images-confirmed / --aplus-confirmed / --compliance-ok / --basics-ok）。
 * 合规项命中违禁词自动判负并触发一票否决。
 *
 * 用法：
 *   node references/scripts/listing-scorer.mjs --title "..." --bullets "A|B|C|D|E" --description "..." --json
 *   node references/scripts/listing-scorer.mjs --title "..." --bullets "A|B|C|D|E" --images-confirmed --aplus-confirmed --compliance-ok --basics-ok --json
 *   node references/scripts/listing-scorer.mjs --version
 *
 * 参数：
 *   --title             标题
 *   --bullets           要点, 用 | 分隔
 *   --description       描述/A+ 文本
 *   --search-terms      后台搜索词(可选)
 *   --platform          amazon/taobao/tiktok/shopee (默认 amazon)
 *   --images-confirmed  主图/副图符合规范
 *   --aplus-confirmed   A+/描述内容已确认
 *   --compliance-ok     认证与图片合规已确认
 *   --basics-ok         类目/参数/变体已确认
 *   --json              输出JSON
 */

import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = dirname(fileURLToPath(import.meta.url));

const VERSION = '1.0.7';
const args = process.argv.slice(2);
const wantJson = args.includes('--json');
const imagesConfirmed = args.includes('--images-confirmed');
const aplusConfirmed = args.includes('--aplus-confirmed');
const complianceOk = args.includes('--compliance-ok');
const basicsOk = args.includes('--basics-ok');
if (args.includes('--version')) {
  process.stdout.write(VERSION + '\n');
  process.exit(0);
}
const KNOWN_FLAGS = new Set(['--title', '--bullets', '--description', '--search-terms', '--platform', '--images-confirmed', '--aplus-confirmed', '--compliance-ok', '--basics-ok', '--json', '--version']);
const unknownFlags = args.filter((a) => a.startsWith('--') && !KNOWN_FLAGS.has(a));
if (unknownFlags.length) {
  console.error('未知参数: ' + unknownFlags.join(' ') + '\n可用参数: --title --bullets --description --search-terms --platform --images-confirmed --aplus-confirmed --compliance-ok --basics-ok --json');
  process.exit(1);
}
function getArg(name) {
  const i = args.indexOf('--' + name);
  return i >= 0 ? args[i + 1] : null;
}
const title = (getArg('title') || '').trim();
const bullets = (getArg('bullets') || '').split('|').map((s) => s.trim()).filter(Boolean);
const description = (getArg('description') || '').trim();
const searchTerms = (getArg('search-terms') || '').trim();
const platform = (getArg('platform') || 'amazon').toLowerCase();

if (!title && bullets.length === 0) {
  console.error('用法: node references/scripts/listing-scorer.mjs --title <标题> --bullets <要点|分隔> [--description ...] [--json]');
  process.exit(1);
}

// —— 违禁词启发式（与 compliance-scan 同源：读取 compliance-rules.json 单一数据源）——
// 口径与 compliance-scan 一致: 绝对化 + 医疗功效 + 促销价格 + 平台红线(按平台/通用)。
// 商标词(trademark_hint)为"仅提示复核", 不触发一票否决, 故不纳入。
let RULE_TERMS = [];
try {
  const rulesJson = JSON.parse(readFileSync(join(__dirname, 'compliance-rules.json'), 'utf-8'));
  const rules = (rulesJson && rulesJson.rules) || {};
  const redLine = rules.platform_red_line || {};
  const redTerms = redLine[platform] || redLine.generic || [];
  RULE_TERMS = [
    ...(rules.absolute_terms || []),
    ...(rules.medical_terms || []),
    ...(rules.price_terms || []),
    ...redTerms,
  ];
} catch (_) { RULE_TERMS = []; }
// 匹配引擎与 compliance-scan 同款: 大小写不敏感 + ASCII 词边界, 避免大小写漏报与子串误报。
const ESCAPE_RE = /[.*+?^${}()|[\]\\]/g;
const ASCII_WORD_HEAD = /^[A-Za-z0-9_]/;
const ASCII_WORD_TAIL = /[A-Za-z0-9_]$/;
function escapeRe(s) {
  return String(s).replace(ESCAPE_RE, '\\$&');
}
function compileTerm(term) {
  const head = ASCII_WORD_HEAD.test(term) ? '\\b' : '';
  const tail = ASCII_WORD_TAIL.test(term) ? '\\b' : '';
  return new RegExp(head + escapeRe(term) + tail, 'gi');
}
function bannedHits(text) {
  if (!text) return [];
  const out = [];
  for (const t of RULE_TERMS) {
    if (typeof t !== 'string' || t.length === 0) continue;
    try {
      if (compileTerm(t).test(text)) out.push(t);
    } catch (_) { /* 无法编译的词跳过 */ }
  }
  return out;
}
const autoComplianceHits = [...bannedHits(title), ...bannedHits(bullets.join(' ')), ...bannedHits(description)];
const complianceViolated = autoComplianceHits.length > 0;

// —— SOP-10 22 项打分 ——
const items = [];
function add(num, cat, name, weight, score, note, status) {
  items.push({ num, category: cat, name, weight, score, note, status });
}

// 标题 (20)
add(1, '标题', '核心关键词前置', 5, title ? 5 : 0, title ? '默认按已前置(需人工确认)' : '缺失', title ? 'auto' : 'missing');
add(2, '标题', '差异化一句话(USP)', 5, title ? (title.length >= 15 ? 5 : 3) : 0, title ? '长度' + title.length : '缺失', title ? 'auto' : 'missing');
add(3, '标题', '2-3 个强属性', 5, title ? (title.length >= 10 ? 5 : 2) : 0, title ? '默认按已含(需人工确认)' : '缺失', title ? 'auto' : 'missing');
add(4, '标题', '长度适中无堆砌', 5, title ? (platform === 'amazon' ? (title.length <= 200 ? 5 : (title.length <= 260 ? 3 : 1)) : (title.length <= 60 ? 5 : 3)) : 0, title ? '长度' + title.length : '缺失', title ? 'auto' : 'missing');

// 主图 & 副图 (20) 人工
const img = imagesConfirmed ? 1 : 0;
add(5, '主图副图', '主图白底1000px+卖点清晰', 6, img ? 6 : 0, imagesConfirmed ? '已确认' : '待确认', imagesConfirmed ? 'manual-ok' : 'manual-pending');
add(6, '主图副图', '副图≥5张且6要素齐全', 8, img ? 8 : 0, imagesConfirmed ? '已确认' : '待确认', imagesConfirmed ? 'manual-ok' : 'manual-pending');
add(7, '主图副图', '无水印/无LOGO遮挡', 3, img ? 3 : 0, imagesConfirmed ? '已确认' : '待确认', imagesConfirmed ? 'manual-ok' : 'manual-pending');
add(8, '主图副图', '主图视频≤60s', 3, img ? 3 : 0, imagesConfirmed ? '已确认' : '待确认', imagesConfirmed ? 'manual-ok' : 'manual-pending');

// 五点 (15)
add(9, '五点', '5点独立, 加粗关键词+好处', 5, bullets.length >= 5 ? 5 : (bullets.length >= 3 ? 3 : (bullets.length >= 1 ? 1 : 0)), bullets.length + ' 条', bullets.length ? 'auto' : 'missing');
add(10, '五点', '覆盖5大差异化卖点', 5, bullets.length >= 5 ? 5 : (bullets.length >= 3 ? 3 : 0), bullets.length + ' 条', bullets.length ? 'auto' : 'missing');
add(11, '五点', '嵌入长尾关键词', 5, bullets.length >= 5 ? 5 : (bullets.length >= 2 ? 3 : 0), bullets.length + ' 条', bullets.length ? 'auto' : 'missing');

// 描述 / A+ (10) 人工+A+确认
const descW = aplusConfirmed ? 1 : 0;
add(12, '描述A+', '品牌故事开头', 3, description ? 3 : 0, description ? '已提供' : '缺失', description ? 'auto' : 'missing');
add(13, '描述A+', '对比表', 3, descW ? 3 : 0, aplusConfirmed ? '已确认' : '待确认', aplusConfirmed ? 'manual-ok' : 'manual-pending');
add(14, '描述A+', '场景图≥3+FAQ', 4, descW ? 4 : 0, aplusConfirmed ? '已确认' : '待确认', aplusConfirmed ? 'manual-ok' : 'manual-pending');

// Backend 关键词 (10)
add(15, 'Backend关键词', '≥200长尾词(无重复/违禁)', 5, searchTerms ? 5 : 0, searchTerms ? '已提供' : '未提供', searchTerms ? 'auto' : 'missing');
add(16, 'Backend关键词', '覆盖PPC TOP50高转化词', 5, searchTerms ? 5 : 0, searchTerms ? '默认按已覆盖(需人工确认)' : '未提供', searchTerms ? 'auto' : 'missing');

// 基础信息 (10) 人工
const bs = basicsOk ? 1 : 0;
add(17, '基础信息', '类目节点≥2', 3, bs ? 3 : 0, basicsOk ? '已确认' : '待确认', basicsOk ? 'manual-ok' : 'manual-pending');
add(18, '基础信息', '尺寸/重量/材质准确', 4, bs ? 4 : 0, basicsOk ? '已确认' : '待确认', basicsOk ? 'manual-ok' : 'manual-pending');
add(19, '基础信息', '变体关系正确', 3, bs ? 3 : 0, basicsOk ? '已确认' : '待确认', basicsOk ? 'manual-ok' : 'manual-pending');

// 合规 (15) — 一票否决
let c20 = 0;
if (complianceViolated) c20 = 0;
else if (title || bullets.length) c20 = 5;
add(20, '合规', '无绝对化/医疗/促销/红线违禁词', 5, c20, complianceViolated ? '命中: ' + autoComplianceHits.join(',') : '未命中', complianceViolated ? 'manual-fail' : 'auto');
const c21 = complianceOk ? 5 : 0;
add(21, '合规', '类目认证齐全', 5, c21, complianceOk ? '已确认' : '待确认', complianceOk ? 'manual-ok' : 'manual-pending');
const c22 = complianceOk ? 5 : 0;
add(22, '合规', '图片不侵权', 5, c22, complianceOk ? '已确认' : '待确认', complianceOk ? 'manual-ok' : 'manual-pending');

const total = items.reduce((s, x) => s + x.score, 0);
const pending = items.filter((x) => x.status === 'manual-pending').length;
let grade, advice;
if (complianceViolated) {
  grade = 'F';
  advice = '合规项命中违禁词(' + autoComplianceHits.join(',') + '), 触发一票否决, 必须先整改文案再谈优化';
} else if (total >= 90) {
  grade = 'S';
  advice = '可上线并开广告';
} else if (total >= 80) {
  grade = 'A';
  advice = '允许上线+开广告, 建议1周内补到90+';
} else if (total >= 60) {
  grade = 'B';
  advice = '打回优化, 必须过80再上';
} else {
  grade = 'C';
  advice = '不允许上线, 按 SOP-10 重写';
}

const payload = {
  ok: true, tool: 'listing-scorer', version: VERSION,
  schema: 'global-ecommerce-intelligence/listing-scorer',
  generatedAt: new Date().toISOString(),
  platform, total, maxScore: 100, grade, pendingManual: pending,
  complianceViolated, bannedHits: autoComplianceHits,
  vetoTriggered: complianceViolated,
  items,
  advice,
  note: '人工项未确认按0分计; 确认开关: --images-confirmed --aplus-confirmed --compliance-ok --basics-ok; 评分口径见 SOP-10',
};

if (wantJson) process.stdout.write(JSON.stringify(payload, null, 2) + '\n');
else {
  console.log('Listing 评分: ' + total + '/100  等级 ' + grade + (pending ? '  待确认项 ' + pending : ''));
  console.log('='.repeat(50));
  for (const it of items) console.log('  [' + it.status + '] ' + it.num + '.' + it.name + ': ' + it.score + '/' + it.weight + '  ' + it.note);
  if (complianceViolated) console.log('  一票否决违禁词: ' + autoComplianceHits.join(','));
  console.log('  建议: ' + advice);
  console.log('='.repeat(50));
}
process.exit(complianceViolated ? 1 : 0);
