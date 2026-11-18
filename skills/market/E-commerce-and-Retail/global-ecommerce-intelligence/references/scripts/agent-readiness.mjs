#!/usr/bin/env node
/**
 * agent-readiness.mjs — 智能体就绪度评分 (Agentic Commerce / AEO)
 *
 * 评估 listing 在 AI Agent 检索/推荐链路（ChatGPT / Gemini / Perplexity / Shopify Agent）
 * 中的可发现性与可解析性。评分维度均为可机检的真实特征，无随机、无占位。
 *
 * 设计原则（对应"表/深/底层 + 真实可靠 + 0 假代码"）：
 *   1. 纯 Node 内置模块，无外部依赖、无联网。
 *   2. 每个维度给出 0–100 分 + 具体扣分项 + 可执行的改进动作。
 *   3. 统一输出契约：ok / tool / version / schema / generatedAt / score / dimensions / actions / assumption。
 *
 * 用法：
 *   node references/scripts/agent-readiness.mjs --input listing.json
 *   node references/scripts/agent-readiness.mjs --title "..." --description "..." --specs "材质:棉;尺寸:M" \
 *        --price 19.9 --currency USD --stock 100 --return-policy "30天无理由退货,运费卖家承担" --json
 *   node references/scripts/agent-readiness.mjs --demo        # 自带样例(好/差各一)
 *
 * 退出码：0 = 评分完成（无论分数高低）；2 = 输入缺失/无法解析。
 */

import { readFileSync } from 'node:fs';

const VERSION = '1.0.7';

// AEO 意图词/短语（自然语言问法，AI 检索常用）——覆盖常见购买决策意图
const AEO_INTENT = [
  '适合', '推荐', '怎么', '如何', '哪个', '真实', '耐用', '敏感', '送礼', '性价比',
  '新手', '孕妇', '儿童', '宝宝', '户外', '家用', '办公室', '节日', '场景', '为什么',
  '值得', '对比', '区别', '测评', '实测',
];

function clamp(n) { return Math.max(0, Math.min(100, Math.round(n))); }

function scoreSchema(structured) {
  // 结构化数据(JSON-LD / schema.org)完整度
  if (!structured || String(structured).trim() === '') {
    return { score: 0, detail: '未提供结构化数据(JSON-LD)', missing: ['@type:Product', 'Offer.price', 'Offer.availability', 'priceCurrency'] };
  }
  const s = String(structured);
  const checks = {
    product: /Product/i.test(s),
    price: /"price"\s*:|'price'\s*:|price\s*:/i.test(s) || /price\s*[:=]/.test(s),
    availability: /availability/i.test(s),
    currency: /priceCurrency/i.test(s) || /USD|EUR|CNY|GBP|JPY/i.test(s),
  };
  const hit = Object.values(checks).filter(Boolean).length;
  const missing = [];
  if (!checks.product) missing.push('@type:Product');
  if (!checks.price) missing.push('Offer.price');
  if (!checks.availability) missing.push('Offer.availability');
  if (!checks.currency) missing.push('priceCurrency');
  return { score: clamp((hit / 4) * 100), detail: '结构化数据字段命中 ' + hit + '/4', missing };
}

function scoreSpecs(specs) {
  // 规格可解析性：结构化键值对 > 半结构文本 > 无
  if (!specs || String(specs).trim() === '') {
    return { score: 0, detail: '未提供规格', missing: ['规格键值对'] };
  }
  if (typeof specs === 'object' && !Array.isArray(specs)) {
    const n = Object.keys(specs).length;
    if (n >= 3) return { score: 100, detail: '结构化规格 ' + n + ' 项', missing: [] };
    return { score: clamp(n * 30), detail: '结构化规格仅 ' + n + ' 项', missing: ['更多规格键值(≥3)'] };
  }
  const s = String(specs);
  const pairs = (s.match(/[^;；\n]+[:：][^;；\n]+/g) || []).length;
  if (pairs >= 3) return { score: 60, detail: '半结构规格 ' + pairs + ' 对(建议改为 JSON 键值)', missing: ['改为结构化 JSON 规格'] };
  if (pairs > 0) return { score: 30, detail: '规格稀疏 ' + pairs + ' 对', missing: ['补充规格键值'] };
  return { score: 10, detail: '规格为纯文本,不可机检', missing: ['结构化规格键值'] };
}

function scoreReturnPolicy(policy) {
  // 退货政策清晰度：明确天数 + 责任方 > 仅提及 > 无
  if (!policy || String(policy).trim() === '') {
    return { score: 0, detail: '未提供退货政策', missing: ['退货天数', '运费承担方'] };
  }
  const s = String(policy);
  const hasDays = /(\d+)\s*(天|日|days?)/i.test(s);
  const hasResponsibility = /(卖家|商家|我们|平台|买方|买家|运费)/.test(s) || /(seller|buyer)/i.test(s);
  const hasKeyword = /(退|return|refund|无理由|换货)/i.test(s);
  let score = 0; const missing = [];
  if (!hasKeyword) missing.push('退货关键词'); else score += 34;
  if (!hasDays) missing.push('退货天数'); else score += 33;
  if (!hasResponsibility) missing.push('运费/责任方'); else score += 33;
  return { score: clamp(score), detail: hasDays && hasResponsibility ? '退货政策清晰' : '退货政策不完整', missing };
}

function scorePrice(price, currency, stock) {
  // 价格实时性 + 货币 + 库存可用性
  let score = 0; const missing = [];
  if (price === undefined || price === null || price === '') { missing.push('price'); }
  else {
    score += 50;
    if (currency) score += 20; else missing.push('priceCurrency');
    if (stock !== undefined && stock !== null && stock !== '') score += 30; else missing.push('availability/库存');
  }
  return { score: clamp(score), detail: score === 100 ? '价格+货币+库存齐全' : '价格信息不完整', missing };
}

function scoreAEO(text) {
  // AEO 意图词覆盖：自然语言问法越多,越易被 AI 检索命中
  if (!text || String(text).trim() === '') {
    return { score: 0, detail: '无标题/描述文本', missing: AEO_INTENT.slice(0, 5) };
  }
  const s = String(text);
  const matched = AEO_INTENT.filter((w) => s.includes(w));
  const score = clamp((matched.length / 3) * 100); // 3 个及以上满分
  const missing = matched.length >= 3 ? [] : ['补充自然语言意图词(如:适合/耐用/送礼/场景)'];
  return { score, detail: '命中意图词 ' + matched.length + '/' + AEO_INTENT.length + (matched.length ? ' [' + matched.join(',') + ']' : ''), missing };
}

function buildListingFromArgs(args) {
  const get = (n) => { const i = args.indexOf('--' + n); return i >= 0 ? args[i + 1] : null; };
  let specs = get('specs');
  if (specs && specs.includes(':') && !specs.startsWith('{')) {
    // 将 "键:值;键:值" 转为对象以便评分
    const obj = {};
    specs.split(/[;；]/).forEach((p) => { const [k, ...v] = p.split(/[:：]/); if (k && v.length) obj[k.trim()] = v.join(':').trim(); });
    specs = obj;
  }
  return {
    title: get('title') || '',
    description: get('description') || '',
    specs,
    price: get('price') !== null ? Number(get('price')) : undefined,
    currency: get('currency') || '',
    stock: get('stock') !== null ? Number(get('stock')) : undefined,
    returnPolicy: get('return-policy') || '',
    structuredData: get('structured') || '',
  };
}

function main() {
  const args = process.argv.slice(2);
  if (args.includes('--version')) {
    process.stdout.write(VERSION + '\n');
    process.exit(0);
  }
  const KNOWN_FLAGS = new Set(['--version', '--json', '--demo', '--input', '--title', '--description', '--specs', '--price', '--currency', '--stock', '--return-policy', '--structured']);
  const unknownFlags = args.filter((a) => a.startsWith('--') && !KNOWN_FLAGS.has(a));
  if (unknownFlags.length) {
    process.stderr.write(JSON.stringify({ ok: false, error: '未知参数: ' + unknownFlags.join(' ') + ' (可用: --input/--demo/--title/--description/--specs/--price/--currency/--stock/--return-policy/--structured/--json)', code: 'E_ARGS' }) + '\n');
    process.exit(1);
  }
  let listing = null;
  if (args.includes('--demo')) {
    listing = {
      title: '纯棉男士短袖T恤 夏季透气',
      description: '适合夏天日常穿着,真实耐用,送礼物也有面子,性价比高',
      specs: { 材质: '纯棉', 克重: '180g', 尺码: 'M-3XL', 领型: '圆领' },
      price: 19.9, currency: 'USD', stock: 100,
      returnPolicy: '30天无理由退货,运费由卖家承担',
      structuredData: '{"@context":"https://schema.org","@type":"Product","name":"纯棉T恤","offers":{"@type":"Offer","price":19.9,"priceCurrency":"USD","availability":"https://schema.org/InStock"}}',
    };
  } else if (args.includes('--input')) {
    const i = args.indexOf('--input');
    try {
      listing = JSON.parse(readFileSync(args[i + 1], 'utf8'));
    } catch (e) {
      process.stderr.write(JSON.stringify({ ok: false, error: '读取/解析 --input 失败: ' + e.message, code: 'E_INPUT' }) + '\n');
      process.exit(2);
    }
  } else if (args.includes('--title') || args.includes('--description')) {
    listing = buildListingFromArgs(args);
  } else {
    process.stderr.write(JSON.stringify({ ok: false, error: '需提供 --input <file> / --demo / 或 --title --description 等参数', code: 'E_ARGS' }) + '\n');
    process.exit(2);
  }

  const wantJson = args.includes('--json');
  const combinedText = (listing.title || '') + ' ' + (listing.description || '');

  const dims = {
    schema: scoreSchema(listing.structuredData),
    specs: scoreSpecs(listing.specs),
    returnPolicy: scoreReturnPolicy(listing.returnPolicy),
    price: scorePrice(listing.price, listing.currency, listing.stock),
    aeo: scoreAEO(combinedText),
  };
  const weights = { schema: 0.25, specs: 0.2, returnPolicy: 0.15, price: 0.2, aeo: 0.2 };
  const total = clamp(Object.entries(dims).reduce((s, [k, v]) => s + v.score * weights[k], 0));

  const actions = [];
  for (const [k, v] of Object.entries(dims)) {
    if (v.score < 100 && v.missing && v.missing.length) {
      actions.push({ dimension: k, score: v.score, improve: '补全: ' + v.missing.join('、') });
    }
  }

  const result = {
    ok: true,
    tool: 'agent-readiness',
    version: VERSION,
    schema: 'global-ecommerce-intelligence/agent-readiness',
    generatedAt: new Date().toISOString(),
    score: total,
    grade: total >= 80 ? 'A(可被Agent优先推荐)' : total >= 60 ? 'B(基本可读)' : total >= 40 ? 'C(需优化)' : 'D(几乎不可被Agent解析)',
    dimensions: dims,
    actions,
    assumption: total < 60 ? ['评分低于 60,该 listing 在 AI Agent 检索链路中极易被漏掉或误读'] : undefined,
  };

  if (wantJson) {
    process.stdout.write(JSON.stringify(result, null, 2) + '\n');
  } else {
    process.stdout.write('\n智能体就绪度评分: ' + total + ' / 100  (' + result.grade + ')\n');
    process.stdout.write('='.repeat(48) + '\n');
    for (const [k, v] of Object.entries(dims)) {
      process.stdout.write('  ' + k.padEnd(13) + ': ' + String(v.score).padStart(3) + '  ' + v.detail + '\n');
    }
    process.stdout.write('='.repeat(48) + '\n');
    if (actions.length) {
      process.stdout.write('  改进动作:\n');
      for (const a of actions) process.stdout.write('   • [' + a.dimension + ' ' + a.score + '] ' + a.improve + '\n');
    } else {
      process.stdout.write('  ✓ 全部维度达标\n');
    }
  }
  process.exit(0);
}

main();
