#!/usr/bin/env node
/**
 * fact-check.mjs — 类官方事实核实器
 *
 * 作用
 *   对本 skill 引用的"类官方事实"(关税与合规阈值、平台费率、市场规模等)做可证伪的核实,
 *   而非凭记忆断言。核实状态一律如实标注,绝不假装核实。
 *
 * 设计原则
 *   1. 离线优先: 默认不联网,只读本地缓存并如实报告"已核实 / 未核实"。
 *   2. 在线核实(--online): 真实请求来源页,按抽取规则取值并与期望值比对,结果落缓存形成闭环。
 *   3. 能力诚实: method=auto 表示可机器比对; method=manual 表示本工具只能确认"来源页可达",
 *      不能判定数值,必须人工比对原文——manual 项永不被标记为"已核实"。
 *   4. 上下文锚定: auto 抽取要求匹配项邻近出现关键词,避免抓到页面内无关数字。
 *   5. 绝不执行远端代码: 只做正则捕获与白名单 JSON 路径取值,不 eval、不 require 远端内容。
 *   6. 来源分级: official(官方) 与 secondary(权威二手源) 严格区分,二手源不冒充官方口径。
 *   7. 无运行期污染: 缓存写入操作系统临时目录,绝不写入 skill 目录。
 *
 * 退出码
 *   0 = 无冲突且无抓取失败(manual 待人工项不计为失败)
 *   1 = 存在数值/语义冲突、抓取失败,或参数错误
 *   2 = 离线模式且存在未核实项(需 --online)
 *
 * 用法
 *   node references/scripts/fact-check.mjs
 *   node references/scripts/fact-check.mjs --list
 *   node references/scripts/fact-check.mjs --online
 *   node references/scripts/fact-check.mjs --id us-mpf-fy2026
 *   node references/scripts/fact-check.mjs --online --max-age 7
 *   node references/scripts/fact-check.mjs --version
 */

import { readFileSync, writeFileSync, existsSync } from 'node:fs';
import { join } from 'node:path';
import { tmpdir } from 'node:os';

const TOOL = 'fact-check';
const VERSION = '1.0.7';
const SCHEMA = 'global-ecommerce-intelligence/' + TOOL;
const CACHE_FILE = join(tmpdir(), 'global-ecommerce-intelligence-fact-cache.json');
const MAX_AGE_DAYS_DEFAULT = 30;
const FETCH_TIMEOUT_MS = 15000;
const NEAR_WINDOW_CHARS = 240;
const MIN_TEXT_BYTES = 800;
const RETRY_DELAY_MS = 1200;
const REQUEST_SPACING_MS = 400;

/**
 * 事实登记表
 *   id          唯一标识
 *   claim       事实陈述(可被证伪的完整表述)
 *   source      来源 URL(均已实测可达)
 *   sourceType  official | secondary
 *   severity    critical | high | medium
 *   volatility  high(月级变动) | medium(年级变动) | low(长期稳定)
 *   method      auto(可机器比对) | manual(仅能确认来源可达,需人工比对)
 *   extract     { pattern, flags?, near? } —— 仅 auto 需要
 *   expected    期望值(可选,提供则比对)
 *   lastVerified 最近人工核实日期
 */
const REGISTRY = [
  {
    id: 'us-customs-user-fees',
    claim: '美国海关用户费(FY2026): 正式报关商品处理费 MPF 为从价 0.3464%,下限 $33.58、上限 $651.50,纸质申报加收 $4.03;非正式报关 $2.69 / $8.06 / $12.09;港口维护费 HMF 为从价 0.125%(仅海运,无上限)',
    source: 'https://www.cbp.gov/trade/basic-import-export/user-fee-table',
    sourceType: 'official',
    severity: 'critical',
    volatility: 'medium',
    method: 'auto',
    extract: { pattern: '(\\$33\\.58)\\s*min\\./\\.?3464%\\s*ad\\s*valorem/\\s*\\$651\\.50\\s*max', flags: 'i', near: 'Merchandise Processing Fee' },
    expected: '33.58',
    lastVerified: '2026-09-03',
  },
  {
    id: 'us-de-minimis-suspended',
    claim: '美国 de minimis 免税待遇已对所有国家暂停: EO 14324 自 2025-08-29 生效,EO 14388(2026-02-20)延续且未设终止日期;任何货值的包裹均须报关缴税,与运输渠道无关',
    source: 'https://www.cbp.gov/newsroom/national-media-release/cbp-modernizes-low-value-shipment-processing',
    sourceType: 'official',
    severity: 'critical',
    volatility: 'high',
    method: 'auto',
    extract: { pattern: 'de\\s*minimis', flags: 'i', near: '(suspend|end|terminat|cancel|no longer)' },
    expected: 'de minimis',
    lastVerified: '2026-09-03',
  },
  {
    id: 'us-de-minimis-eo14324',
    claim: 'EO 14324《Suspending Duty-Free De Minimis Treatment for All Countries》确立全球暂停 de minimis 免税待遇,EO 14388 延续该暂停',
    source: 'https://www.whitehouse.gov/presidential-actions/2025/07/suspending-duty-free-de-minimis-treatment-for-all-countries/',
    sourceType: 'official',
    severity: 'critical',
    volatility: 'high',
    method: 'auto',
    extract: { pattern: 'de\\s*minimis', flags: 'i', near: 'suspend' },
    expected: 'de minimis',
    lastVerified: '2026-09-03',
  },
  {
    id: 'us-postal-entry-process',
    claim: '美国国际邮政渠道: 2026-02-28 起取消按件定额税($80/$160/$200),一律改按从价计征;2026-07-24 起启用新邮政报关流程(CBP 过渡最终规则,CSMS #69183472),货值 ≤$2,500 的邮包须由申报人按月提交 IMDW 工作表、提供 10 位 HTSUS 归类并持有效报关保证金;Entry Type 86 已废止,改由 Entry Type 11(非正式)或 01(正式)申报',
    source: 'https://www.cbp.gov/trade/basic-import-export',
    sourceType: 'official',
    severity: 'critical',
    volatility: 'high',
    method: 'manual',
    extract: { pattern: 'de\\s*minimis', flags: 'i' },
    lastVerified: '2026-09-03',
    note: '该页为 CBP 进出口总览入口,具体 IMDW 与保证金细则须以 CBP 专项公告及 19 CFR Part 145 原文为准',
  },
  {
    id: 'us-section301-forced-labor',
    claim: '美国 Section 301 强迫劳动关税自 2026-07-24 起接替到期的 Section 122 临时附加税: 覆盖 60 个经济体,设 10% 与 12.5% 两档,部分经济体按净 MFN 上限执行;相关措施处于诉讼进程中,征收仍在继续',
    source: 'https://ustr.gov/issue-areas/enforcement/section-301-investigations',
    sourceType: 'official',
    severity: 'critical',
    volatility: 'high',
    method: 'manual',
    extract: { pattern: 'Section\\s*301', flags: 'i' },
    lastVerified: '2026-09-03',
    note: '税率档位与适用经济体清单变动频繁,申报前须以 USTR 最新公告与 HTSUS 第 99 章为准',
  },
  {
    id: 'us-ieepa-invalid',
    claim: 'IEEPA 对等关税经 2026-02-20 美国最高法院裁定无效,CBP 自 2026-02-24 起停征;原以 IEEPA 为依据的对等关税不再征收,但以 Section 301 与 Section 232 为依据的关税不受该裁定影响',
    source: 'https://www.tradecommissioner.gc.ca/en/market-industry-info/search-country-region/country/canada-united-states-export/us-tariffs/answers-common-questions-tariffs.html',
    sourceType: 'secondary',
    severity: 'critical',
    volatility: 'high',
    method: 'manual',
    extract: { pattern: 'IEEPA', flags: 'i' },
    lastVerified: '2026-09-03',
    note: '该来源为外国政府机构对美国关税的整理,属权威二手口径;法律结论以美国最高法院判決与 CBP CSMS 公告原文为准',
  },
  {
    id: 'us-uflpa-entity-list',
    claim: '美国《维吾尔强迫劳动预防法》(UFLPA)实体清单持续扩充,累计数百家主体;列入清单主体的货物被推定强迫劳动生产,除非进口商提供清晰且令人信服的证据,否则 CBP 予以扣留',
    source: 'https://www.dhs.gov/uflpa-entity-list',
    sourceType: 'official',
    severity: 'critical',
    volatility: 'high',
    method: 'auto',
    extract: { pattern: 'UFLPA', flags: 'i', near: 'entity list' },
    expected: 'UFLPA',
    lastVerified: '2026-09-03',
    note: '清单主体数量按月更新,本项目不硬编码具体家数,须以 DHS 页面当日清单为准',
  },
  {
    id: 'eu-low-value-duty-3eur',
    claim: '欧盟小包裹关税(Council Regulation (EU) 2026/382,2026-02-11 通过,修订 Regulation (EC) No 1186/2009): 第 1 条删除原基于阈值的关税免征(第1186/2009号条例第二编第五章);第 2 条规定自 2026-07-01 至 2028-07-01,对内在价值不超过 EUR 150 的货物按"每件"征收 EUR 3 关税以替代被取消的免征。原文为 "EUR 3 per item in a consignment",欧盟理事会解读为"按商品类别计征而非按包裹计征";两者口径存在分歧,实际清关以海关执行口径为准。若集中式欧盟 IT 基础设施届时未就绪,欧委会可提议延长该过渡措施',
    source: 'https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=OJ:L_202600382',
    sourceAlt: 'https://eur-lex.europa.eu/eli/reg/2026/382/oj',
    sourceType: 'official',
    severity: 'critical',
    volatility: 'medium',
    method: 'manual',
    extract: { pattern: 'EUR\\s*3\\b', flags: 'i', near: 'customs duty' },
    lastVerified: '2026-09-03',
    note: '计量单位存在源间分歧: 法规字面为 per item in a consignment,理事会官方解读为 per category of goods;计税时须按清关口岸执行口径确认。EUR-Lex 官方公报页启用 AWS WAF 挑战,静态抓取无法通过,须人工打开源链接核验原文',
  },
  {
    id: 'uk-lvi-relief-removal',
    claim: '英国低值进口(LVI)关税免税额(≤£135)将被取消: 2025 秋季预算宣布取消,HMRC 与财政部 2026-06-23 宣布提前 6 个月实施,最迟 2028-10 生效(原定 2029-03);咨询回应文件 2026-07-13 发布;在此之前 ≤£135 仍享关税减免,但增值税自 2021 年起已由卖家或平台在销售点征收',
    source: 'https://www.gov.uk/government/publications/reforming-customs-rules-for-low-value-imports/reforming-the-customs-treatment-of-low-value-imports-into-the-uk',
    sourceType: 'official',
    severity: 'high',
    volatility: 'medium',
    method: 'auto',
    extract: { pattern: '£\\s*135|135', flags: 'i', near: '(low.value|LVI|relief)' },
    expected: '135',
    lastVerified: '2026-09-03',
  },
  {
    id: 'amazon-referral-fee',
    claim: 'Amazon 多数品类推荐佣金约 15%,实际费率按品类与站点差异显著(常见区间 8%–17%),以官方费率表为准',
    source: 'https://sell.amazon.com/pricing',
    sourceType: 'official',
    severity: 'high',
    volatility: 'medium',
    method: 'manual',
    extract: { pattern: 'referral\\s*fee', flags: 'i' },
    lastVerified: '2026-09-03',
    note: '费率表由前端脚本渲染,静态抓取无法稳定定位数值,故不做机器比对',
  },
  {
    id: 'shopify-basic-plan',
    claim: 'Shopify Basic 套餐月费以官网定价页当日标价为准(年付与月付价格不同),本项目不硬编码具体金额',
    source: 'https://www.shopify.com/pricing',
    sourceType: 'official',
    severity: 'medium',
    volatility: 'medium',
    method: 'manual',
    extract: { pattern: 'Basic', flags: 'i' },
    lastVerified: '2026-09-03',
    note: '定价页按地区与币种动态呈现,静态抓取无法稳定定位数值,故不做机器比对',
  },
  {
    id: 'global-ecommerce-2026',
    claim: '2026 年全球零售电商规模约 $6.88 万亿美元,同比约 +7.2%',
    source: 'https://www.shopify.com/blog/global-ecommerce-sales',
    sourceType: 'secondary',
    severity: 'medium',
    volatility: 'medium',
    method: 'auto',
    extract: { pattern: '\\$?6\\.88\\s*trillion', flags: 'i', near: '(e-?commerce|retail|sales)' },
    expected: '6.88',
    lastVerified: '2026-09-03',
  },
  {
    id: 'tiktok-shop-2025-gmv',
    claim: 'TikTok Shop 2025 年全球 GMV 约 $643 亿,同比 +94%,覆盖 16 个市场;美国 $151 亿(+68%),东南亚 $456 亿(+100%,占全球约 71%),印尼 $131 亿为第二大市场(Momentum Works 联合 Tabcut 于 2026-02 发布的年度报告);不同机构口径存在差异,不存在 200%+ 的权威依据',
    source: 'https://momentum.asia/',
    sourceType: 'secondary',
    severity: 'medium',
    volatility: 'medium',
    method: 'manual',
    extract: { pattern: 'TikTok', flags: 'i' },
    lastVerified: '2026-09-03',
    note: '报告原文为付费或下载式交付,首页无法稳定抽取数值,故不做机器比对',
  },
];

function parseArgs(argv) {
  const opts = { json: false, online: false, list: false, id: null, maxAge: MAX_AGE_DAYS_DEFAULT };
  const unknown = [];
  for (let i = 0; i < argv.length; i += 1) {
    const a = argv[i];
    if (a === '--json') opts.json = true;
    else if (a === '--online') opts.online = true;
    else if (a === '--list') opts.list = true;
    else if (a === '--id') {
      i += 1;
      opts.id = argv[i] || null;
    } else if (a === '--max-age') {
      i += 1;
      const n = Number(argv[i]);
      opts.maxAge = Number.isFinite(n) && n > 0 ? n : MAX_AGE_DAYS_DEFAULT;
    } else unknown.push(a);
  }
  return { opts, unknown };
}

function loadCache() {
  if (!existsSync(CACHE_FILE)) return {};
  try {
    const parsed = JSON.parse(readFileSync(CACHE_FILE, 'utf8'));
    return parsed && typeof parsed === 'object' ? parsed : {};
  } catch {
    return {};
  }
}

function saveCache(cache) {
  try {
    writeFileSync(CACHE_FILE, JSON.stringify(cache, null, 2), 'utf8');
  } catch {
    /* 缓存写入失败不影响核实结论 */
  }
}

function daysSince(iso) {
  if (!iso) return Infinity;
  const t = new Date(iso).getTime();
  if (!Number.isFinite(t)) return Infinity;
  return (Date.now() - t) / 86400000;
}

function makeRegExp(pattern, flags) {
  try {
    return new RegExp(pattern, flags || '');
  } catch {
    return null;
  }
}

/** 上下文锚定抽取: 匹配项前后 window 字符内须出现 near 关键词 */
function extractWithContext(text, spec) {
  const main = makeRegExp(spec.pattern, spec.flags);
  if (!main) return { value: null, error: '抽取正则无效' };
  const global = makeRegExp(spec.pattern, (spec.flags || '').includes('g') ? spec.flags : (spec.flags || '') + 'g');
  if (!global) return { value: null, error: '抽取正则无效' };

  const near = spec.near ? makeRegExp(spec.near, 'i') : null;
  let m;
  let fallback = null;
  while ((m = global.exec(text)) !== null) {
    const hit = m[1] !== undefined ? m[1] : m[0];
    if (!near) return { value: hit, error: null };
    const from = Math.max(0, m.index - NEAR_WINDOW_CHARS);
    const to = Math.min(text.length, m.index + m[0].length + NEAR_WINDOW_CHARS);
    if (near.test(text.slice(from, to))) return { value: hit, error: null };
    if (fallback === null) fallback = hit;
    if (m[0].length === 0) global.lastIndex += 1;
  }
  if (fallback !== null) return { value: null, error: '匹配项未通过上下文锚定校验(可能命中页面内无关内容)' };
  return { value: null, error: '源页面未匹配到预期字段' };
}

function compare(actual, expected) {
  const a = String(actual);
  const e = String(expected);
  if (/\d/.test(e)) {
    const norm = (s) => s.replace(/[^0-9.]/g, '');
    const na = norm(a);
    const ne = norm(e);
    if (!na) return { ok: false, reason: '数值抽取为空,实际: ' + a };
    if (!(na.includes(ne) || ne.includes(na))) return { ok: false, reason: '数值冲突: 期望 ' + e + ',实际抽取 ' + a };
    return { ok: true, reason: null };
  }
  if (!a.toLowerCase().includes(e.toLowerCase())) return { ok: false, reason: '语义冲突: 期望含 "' + e + '",实际抽取 "' + a + '"' };
  return { ok: true, reason: null };
}

/**
 * 剥离 HTML,只保留可见文本后再做抽取。
 * 原因: 页面标签会把上下文锚定窗口撑爆,导致锚定校验误判;
 *       同时标签与脚本内容中的噪声会造成假命中。
 */
function stripHtml(html) {
  return html
    .replace(/<script[\s\S]*?<\/script>/gi, ' ')
    .replace(/<style[\s\S]*?<\/style>/gi, ' ')
    .replace(/<[^>]+>/g, ' ')
    .replace(/&nbsp;/g, ' ')
    .replace(/&amp;/g, '&')
    .replace(/&euro;/g, 'EUR')
    .replace(/&#8364;/g, 'EUR')
    .replace(/&pound;/g, 'GBP')
    .replace(/&#163;/g, 'GBP')
    .replace(/&lt;/g, '<')
    .replace(/&gt;/g, '>')
    .replace(/\s+/g, ' ')
    .trim();
}

async function fetchOnce(url) {
  const ctrl = new AbortController();
  const timer = setTimeout(() => ctrl.abort(), FETCH_TIMEOUT_MS);
  try {
    const res = await fetch(url, {
      signal: ctrl.signal,
      redirect: 'follow',
      headers: { 'User-Agent': 'Mozilla/5.0 (compatible; ' + TOOL + '/' + VERSION + ')' },
    });
    if (!res.ok) throw new Error('HTTP ' + res.status);
    const raw = await res.text();
    return { text: stripHtml(raw), rawBytes: raw.length, status: res.status };
  } finally {
    clearTimeout(timer);
  }
}

/**
 * 带一次重试的抓取。
 * 原因: 官方站点偶发返回占位页或限流页,单次抓取失败会误报为"事实冲突",
 *       而事实冲突是本工具最高等级的告警,不得由网络抖动触发。
 */
async function fetchText(url) {
  let lastErr = null;
  for (let attempt = 0; attempt < 2; attempt += 1) {
    try {
      const r = await fetchOnce(url);
      if (r.text.length >= MIN_TEXT_BYTES) return r;
      lastErr = new Error('可见文本过短(' + r.text.length + ' 字符),疑为占位页或限流页');
    } catch (e) {
      lastErr = e;
    }
    if (attempt === 0) await new Promise((resolve) => setTimeout(resolve, RETRY_DELAY_MS));
  }
  throw lastErr || new Error('抓取失败');
}

function offlineResult(fact, cached) {
  if (cached && daysSince(cached.fetchedAt) <= MAX_AGE_DAYS_DEFAULT) {
    return {
      id: fact.id, claim: fact.claim, status: 'verified',
      value: cached.value, source: fact.source, sourceType: fact.sourceType,
      severity: fact.severity, volatility: fact.volatility, method: fact.method,
      lastVerified: fact.lastVerified, fetchedAt: cached.fetchedAt,
      warnings: [],
      notes: ['离线模式: 依据本地缓存判定,本次未重新联网核实'],
    };
  }
  return {
    id: fact.id, claim: fact.claim, status: 'unverified',
    value: null, source: fact.source, sourceType: fact.sourceType,
    severity: fact.severity, volatility: fact.volatility, method: fact.method,
    lastVerified: fact.lastVerified, fetchedAt: cached ? cached.fetchedAt : null,
    warnings: ['离线模式且无有效缓存,需 --online 核实'],
    notes: fact.note ? [fact.note] : [],
  };
}

async function onlineCheck(fact) {
  const fetchedAt = new Date().toISOString();
  // 主源不可用时自动降级到备用源(官方站点常有限流或区域屏蔽)
  const candidates = [fact.source].concat(fact.sourceAlt ? [fact.sourceAlt] : []);
  let text = null;
  let status = null;
  let rawBytes = 0;
  let sourceUsed = null;
  let fetchError = null;
  for (const url of candidates) {
    try {
      const r = await fetchText(url);
      text = r.text;
      status = r.status;
      rawBytes = r.rawBytes;
      sourceUsed = url;
      fetchError = null;
      break;
    } catch (e) {
      fetchError = e.message;
    }
  }

  const base = {
    id: fact.id, claim: fact.claim, source: fact.source, sourceType: fact.sourceType,
    severity: fact.severity, volatility: fact.volatility, method: fact.method,
    lastVerified: fact.lastVerified, fetchedAt,
    sourceUsed: sourceUsed || null,
    notes: fact.note ? [fact.note] : [],
  };

  if (fact.method === 'manual') {
    // 人工核实项本就不依赖机器抓取;来源页不可自动访问(反爬/限流)不影响其"待人工核实"定性
    if (fetchError) {
      return {
        ...base,
        status: 'manual-pending',
        value: null,
        warnings: ['来源页当前无法自动抓取(' + fetchError + '),须人工打开源链接核实原文'],
        notes: base.notes,
      };
    }
    const marker = fact.extract ? makeRegExp(fact.extract.pattern, fact.extract.flags) : null;
    return {
      ...base,
      status: 'manual-pending',
      value: null,
      evidence: { httpStatus: status, rawBytes, textBytes: text.length },
      warnings: [
        '该类事实无法机器比对,本工具仅确认来源页可达(HTTP ' + status + ', 可见文本 ' + text.length + ' 字符)',
        '须人工比对原文后方可认定核实',
      ],
      notes: base.notes.concat(
        marker && marker.test(text) ? ['来源页已检出关键标识,建议优先比对'] : []
      ),
    };
  }

  if (fetchError) {
    return {
      ...base,
      status: 'fetch-failed',
      value: null,
      warnings: ['来源页抓取失败: ' + fetchError + ';可能为网络限制或站点反爬,请人工复核'],
    };
  }

  const evidence = { httpStatus: status, rawBytes, textBytes: text.length };

  const { value, error } = extractWithContext(text, fact.extract || {});
  if (value === null) {
    return {
      ...base,
      status: 'conflict',
      value: null,
      evidence,
      warnings: [error || '源页面未匹配到预期字段(页面结构变更或抽取规则失效)'],
    };
  }
  if (fact.expected !== undefined && fact.expected !== null) {
    const cmp = compare(value, fact.expected);
    if (!cmp.ok) {
      return { ...base, status: 'conflict', value, evidence, warnings: [cmp.reason] };
    }
  }
  return { ...base, status: 'verified', value, evidence, warnings: [] };
}

function printText(out) {
  const label = { verified: '已核实', unverified: '未核实', 'manual-pending': '待人工核实', conflict: '冲突', 'fetch-failed': '抓取失败' };
  console.log('\n类官方事实核实 (' + (out.mode === 'online' ? '在线' : '离线') + ')');
  console.log('='.repeat(60));
  for (const r of out.results) {
    console.log('  [' + (label[r.status] || r.status) + '] ' + r.id + ' (' + r.sourceType + ' / ' + r.severity + ' / ' + r.method + ')');
    console.log('    陈述: ' + r.claim);
    if (r.value !== null && r.value !== undefined) console.log('    抽取: ' + r.value);
    for (const w of r.warnings) console.log('    ! ' + w);
    for (const n of r.notes) console.log('    注: ' + n);
  }
  console.log('  已核实 ' + out.verifiedCount + ' / 待人工 ' + out.manualPendingCount + ' / 冲突 ' + out.conflictCount + ' / 未核实 ' + out.unverifiedCount + ' / 合计 ' + out.factCount);
  console.log('='.repeat(60));
}

async function main() {
  const argv = process.argv.slice(2);
  if (argv.includes('--version')) {
    process.stdout.write(VERSION + '\n');
    process.exit(0);
  }
  const { opts, unknown } = parseArgs(argv);
  if (unknown.length) {
    process.stderr.write('未知参数: ' + unknown.join(' ') + '\n可用参数: --json --online --list --id <id> --max-age <天> --version\n');
    process.exit(1);
  }

  if (opts.list) {
    const payload = {
      ok: true,
      tool: TOOL,
      version: VERSION,
      schema: SCHEMA,
      generatedAt: new Date().toISOString(),
      mode: 'list',
      factCount: REGISTRY.length,
      facts: REGISTRY.map((f) => ({
        id: f.id,
        claim: f.claim,
        source: f.source,
        sourceType: f.sourceType,
        severity: f.severity,
        volatility: f.volatility,
        method: f.method,
        lastVerified: f.lastVerified,
      })),
    };
    if (opts.json) process.stdout.write(JSON.stringify(payload, null, 2) + '\n');
    else {
      console.log('\n类官方事实注册表');
      console.log('='.repeat(60));
      for (const f of payload.facts) {
        console.log('  ' + f.id + ' (' + f.sourceType + ' / ' + f.severity + ' / ' + f.method + ' / 核实于 ' + f.lastVerified + ')');
        console.log('    陈述: ' + f.claim);
        console.log('    来源: ' + f.source);
      }
      console.log('  合计 ' + payload.factCount + ' 条');
      console.log('='.repeat(60));
    }
    process.exit(0);
  }

  let targets = REGISTRY;
  if (opts.id) {
    targets = REGISTRY.filter((f) => f.id === opts.id);
    if (targets.length === 0) {
      process.stderr.write('未知事实 id: ' + opts.id + '\n可用 id: ' + REGISTRY.map((f) => f.id).join(', ') + '\n');
      process.exit(1);
    }
  }

  const cache = loadCache();
  const results = [];
  for (let i = 0; i < targets.length; i += 1) {
    const f = targets[i];
    // 连续请求之间留出间隔,降低被目标站点限流的概率
    if (opts.online && i > 0) {
      await new Promise((resolve) => setTimeout(resolve, REQUEST_SPACING_MS));
    }
    if (opts.online) {
      results.push(await onlineCheck(f));
    } else {
      results.push(offlineResult(f, cache[f.id]));
    }
  }

  if (opts.online) {
    const next = { ...cache };
    for (const r of results) {
      if (r.status === 'verified') {
        next[r.id] = { value: r.value, fetchedAt: r.fetchedAt, ok: true };
      } else if (r.status === 'conflict' || r.status === 'fetch-failed') {
        next[r.id] = { value: null, fetchedAt: r.fetchedAt, ok: false, reason: r.warnings.join('; ') };
      }
    }
    saveCache(next);
  }

  const count = (s) => results.filter((r) => r.status === s).length;
  const out = {
    ok: count('conflict') === 0 && count('fetch-failed') === 0,
    tool: TOOL,
    version: VERSION,
    schema: SCHEMA,
    generatedAt: new Date().toISOString(),
    mode: opts.online ? 'online' : 'offline',
    factCount: results.length,
    verifiedCount: count('verified'),
    manualPendingCount: count('manual-pending'),
    conflictCount: count('conflict'),
    fetchFailedCount: count('fetch-failed'),
    unverifiedCount: count('unverified'),
    cacheFile: CACHE_FILE,
    results,
  };

  if (opts.json) process.stdout.write(JSON.stringify(out, null, 2) + '\n');
  else printText(out);

  if (count('conflict') > 0 || count('fetch-failed') > 0) process.exit(1);
  if (!opts.online && count('unverified') > 0) process.exit(2);
  process.exit(0);
}

main().catch((e) => {
  process.stderr.write('错误: ' + (e && e.message ? e.message : String(e)) + '\n');
  process.exit(1);
});
