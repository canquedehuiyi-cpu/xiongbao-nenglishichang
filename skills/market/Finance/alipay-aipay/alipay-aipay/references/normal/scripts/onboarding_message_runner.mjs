#!/usr/bin/env node

import { createHash } from 'node:crypto';
import path from 'node:path';
import process from 'node:process';
import { fileURLToPath } from 'node:url';
import { isWindowsPlatform } from './platform_compat.mjs';
import { buildWindowsOnboardingRedirectUrl, loadMccRecords, renderMessage } from './render_customer_message.mjs';
import {
  currentRunContext,
  emitStageMetricAsync,
  emitTerminalMetric,
  terminalMetricContextFromArgs
} from './telemetry.mjs';

const internalPrefix = 'ALIPAY_AIPAY_INTERNAL:';
const productTypes = {
  aipay: { variant: 'AIPAY', productName: 'AI 按量付费' },
  webpay: { variant: 'WEBPAY', productName: 'AI 网页应用收款' },
  apppay: { variant: 'APPPAY', productName: 'AI 移动应用收款' }
};

const signingStatusMap = {
  NOT_SIGNED: '未签约',
  SIGN_SUBMITTED: '已提交待生效',
  SIGNED_EFFECTIVE: '已生效',
  OTHER_STATUS: '其他状态待核验',
  QUERY_FAILED: '查询失败',
  FAILED: '查询失败',
  ERROR: '查询失败'
};

const serviceFlowMap = {
  'FLOW:CREATE_NEW': '无已有服务',
  'FLOW:SELECT': '已有服务候选',
  QUERY_FAILED: '查询失败',
  'FLOW:ERROR': '查询失败',
  ERROR: '查询失败'
};

const applicationFlowMap = {
  'FLOW:CREATE_NEW': '无同类型应用',
  'FLOW:SELECT': '有上线应用可复用',
  'FLOW:PENDING_APPLICATIONS': '仅有未上线应用',
  QUERY_FAILED: '查询失败',
  'FLOW:ERROR': '查询失败',
  ERROR: '查询失败'
};

const categoryNames = {
  signing: '签约材料',
  service: '服务资料',
  application: '应用资料'
};

const materialFieldsByCategory = Object.freeze({
  signing: ['APP名称', '首页截图', '商品页截图', '支付页截图'],
  service: ['服务名称', '服务描述', '服务地址', '服务单价', '请求示例JSON'],
  application: ['应用平台和对应资料', 'iOS Bundle ID（bundleId）', 'Android 应用包名（appPackage）', 'Android 应用签名摘要（appSign）', '应用公钥']
});

const materialStates = {
  INITIAL: { variant: 'INITIAL', currentStatus: '待补充' },
  PARTIAL: { variant: 'PARTIAL', currentStatus: '部分已提供，待补充' },
  INVALID: { variant: 'INVALID', currentStatus: '校验失败，需更正' },
  APP_WEB_INITIAL: { variant: 'APP_WEB_INITIAL', currentStatus: '待补充' },
  APP_MOBILE_INITIAL: { variant: 'APP_MOBILE_INITIAL', currentStatus: '待补充' }
};

const directFieldAliases = new Map([
  ['APP名称', ['APP名称']],
  ['appName', ['APP名称']],
  ['首页截图', ['首页截图']],
  ['商品页截图', ['商品页截图']],
  ['支付页截图', ['支付页截图']],
  ['服务名称', ['服务名称']],
  ['serviceName', ['服务名称']],
  ['服务描述', ['服务描述']],
  ['serviceDesc', ['服务描述']],
  ['服务地址', ['服务地址']],
  ['资源 URL', ['服务地址']],
  ['资源URL', ['服务地址']],
  ['resourceUrl', ['服务地址']],
  ['服务单价', ['服务单价']],
  ['单次价格', ['服务单价']],
  ['pricing', ['服务单价']],
  ['请求示例JSON', ['请求示例JSON']],
  ['请求示例 JSON', ['请求示例JSON']],
  ['序列化 JSON 请求示例', ['请求示例JSON']],
  ['schemaUrl', ['请求示例JSON']],
  ['应用平台和对应资料', ['应用平台和对应资料']],
  ['mobilePlatform', ['应用平台和对应资料']],
  ['iOS Bundle ID（bundleId）', ['iOS Bundle ID（bundleId）']],
  ['iOS Bundle ID', ['iOS Bundle ID（bundleId）']],
  ['bundleId', ['iOS Bundle ID（bundleId）']],
  ['Android 应用包名（appPackage）', ['Android 应用包名（appPackage）']],
  ['Android 应用包名', ['Android 应用包名（appPackage）']],
  ['appPackage', ['Android 应用包名（appPackage）']],
  ['Android 应用签名摘要（appSign）', ['Android 应用签名摘要（appSign）']],
  ['Android 应用签名摘要', ['Android 应用签名摘要（appSign）']],
  ['appSign', ['Android 应用签名摘要（appSign）']],
  ['应用公钥', ['应用公钥']],
  ['publicKey', ['应用公钥']]
]);

function parseArgs(argv) {
  const command = argv[2];
  const args = {};
  for (let index = 3; index < argv.length; index += 1) {
    const key = argv[index];
    if (!key.startsWith('--')) throw new Error(`未知参数 ${key}`);
    const value = argv[index + 1];
    if (value === undefined || value.startsWith('--')) throw new Error(`参数 ${key} 缺少取值`);
    const name = key.slice(2);
    if (Object.prototype.hasOwnProperty.call(args, name)) throw new Error(`参数 ${key} 重复`);
    args[name] = value;
    index += 1;
  }
  return { command, args };
}

function required(args, name) {
  const value = args[name];
  if (typeof value !== 'string' || value.length === 0) throw new Error(`缺少参数 --${name}`);
  return value;
}

function optional(args, name) {
  return typeof args[name] === 'string' && args[name].length > 0 ? args[name] : undefined;
}

function productFor(args) {
  const productType = required(args, 'product-type');
  const mapping = productTypes[productType];
  if (!mapping) throw new Error('product-type 非法，仅支持 aipay、webpay、apppay');
  return mapping;
}

function normalizeEnum(value, map, label) {
  if (typeof value !== 'string' || value.length === 0) throw new Error(`缺少 ${label}`);
  const normalized = map[value];
  if (!normalized) throw new Error(`${label} 不在允许脚本标记中；允许值：${Object.keys(map).join('、')}`);
  return normalized;
}

async function readStdin() {
  let input = '';
  for await (const chunk of process.stdin) input += chunk;
  return input.trim() ? JSON.parse(input) : {};
}

function runPlatformEntry(args = {}) {
  if (!isWindowsPlatform()) return '';
  const runContext = currentRunContext();
  if (!runContext || runContext.terminal || !['onboarding_only', 'full_process'].includes(runContext.root_intent)) {
    throw new Error('Windows 产品开通引导缺少有效的当前 Onboarding run context');
  }
  return renderMessage('onboarding.windows.redirect', 'DEFAULT', {
    officialUrl: buildWindowsOnboardingRedirectUrl(runContext.run_id)
  }, terminalMetricContextFromArgs(args, { terminalReason: 'unsupported_platform' }));
}

function parseJsonArg(args, name, label) {
  const raw = required(args, name);
  try {
    return JSON.parse(raw);
  } catch {
    throw new Error(`${label} 必须是合法 JSON`);
  }
}

function runProductClarify() {
  return renderMessage('product.clarify', 'DEFAULT', {});
}

function runEnterpriseUnsupported(args) {
  const variant = required(args, 'variant');
  if (!['ONBOARDING_ONLY', 'FULL_PROCESS'].includes(variant)) {
    throw new Error('variant 非法，仅支持 ONBOARDING_ONLY、FULL_PROCESS');
  }
  return renderMessage(
    'onboarding.enterprise.unsupported',
    variant,
    {},
    terminalMetricContextFromArgs(args, { terminalReason: 'enterprise_account_unsupported' })
  );
}

async function runMccClarify(args) {
  const productType = required(args, 'product-type');
  const product = productFor({ ...args, 'product-type': productType });
  emitStageMetricAsync('onboarding.mcc_prepare.start', { productType });
  return renderMessage('onboarding.mcc.clarify', 'DEFAULT', {
    productName: product.productName
  }, { productType });
}

function normalizeSearch(value) {
  return value.toLocaleLowerCase('zh-CN').replace(/[\s，,。；;、/（）()\-_]/gu, '');
}

function assertMccQuery(query) {
  if (query.length > 500 || /[\u0000-\u001f\u007f]/u.test(query)) throw new Error('query 包含控制字符或过长');
  const normalizedQuery = normalizeSearch(query);
  if (normalizedQuery.length < 2) throw new Error('query 过短，无法执行确定性 MCC 检索');
  return normalizedQuery;
}

const mccAliasRules = [
  {
    queryTerms: ['电商', '电子商务', '网上商城', '线上商城', '网络购物'],
    targetTerms: ['电商', '网上商城', '线上商城']
  }
];
const agentMccStatuses = new Set(['MATCHED', 'INSUFFICIENT', 'UNSUPPORTED']);
const mccSelectionReceiptPrefix = 'AIPAY_MCC_SELECTION_V1.';

function mccCandidateFromRecord(record) {
  return {
    mccCode: record.code,
    mccName: record.name,
    applicableBusinesses: record.applicableBusinesses,
    qualification: record.qualification
  };
}

function mccTableSummary(records = loadMccRecords()) {
  const entries = [...records.values()]
    .map((record) => [record.code, record.name, record.applicableBusinesses, record.qualification].join('\t'))
    .sort()
    .join('\n');
  return {
    recordCount: records.size,
    sha256: createHash('sha256').update(entries).digest('hex')
  };
}

function normalizeMccCode(value, records) {
  const raw = value.trim().toUpperCase();
  if (/^A\d{4}_B\d{4}$/u.test(raw)) return records.has(raw) ? raw : '';
  if (!/^B\d{4}$/u.test(raw)) return '';
  const matches = [...records.keys()].filter((code) => code.endsWith(`_${raw}`));
  if (matches.length > 1) throw new Error(`MCC 二级编码 ${raw} 在当前表中不唯一，必须提供完整 Axxxx_Bxxxx 编码`);
  return matches[0] || '';
}

function directMccCode(query, records) {
  const raw = query.trim().toUpperCase();
  if (!/^(?:A\d{4}_)?B\d{4}$/u.test(raw)) return '';
  const normalized = normalizeMccCode(raw, records);
  if (!normalized) throw new Error(`当前 MCC 表不存在编码：${raw}`);
  return normalized;
}

function deterministicMccMatches(query, { limit = 8 } = {}) {
  const normalizedQuery = assertMccQuery(query);
  const scored = [];
  for (const record of loadMccRecords().values()) {
    const name = normalizeSearch(record.name);
    const businesses = normalizeSearch(record.applicableBusinesses);
    const code = normalizeSearch(record.code);
    const haystack = `${name}${businesses}`;
    let score = 0;
    if (code === normalizedQuery || normalizedQuery.includes(code) || name === normalizedQuery) score = Math.max(score, 100);
    if (normalizedQuery.includes(name) || name.includes(normalizedQuery)) score = Math.max(score, 80);
    if (businesses.includes(normalizedQuery)) score = Math.max(score, 70);
    for (const rule of mccAliasRules) {
      if (rule.queryTerms.some((term) => normalizedQuery.includes(term)) && rule.targetTerms.some((term) => haystack.includes(term))) {
        score = Math.max(score, 50);
      }
    }
    if (score > 0) scored.push({ record, score, strength: score >= 70 ? 'STRONG' : 'WEAK' });
  }
  const strongMatches = scored.filter(({ score }) => score >= 70);
  const ranked = strongMatches.length > 0 ? strongMatches : scored;
  return ranked
    .sort((left, right) => right.score - left.score || left.record.code.localeCompare(right.record.code))
    .slice(0, limit);
}

function parseAgentMccCodes(args, records) {
  const raw = optional(args, 'agent-mcc-codes') || '';
  const inputs = raw.trim()
    ? raw.split(/[,，、\s]+/u).map((code) => code.trim().toUpperCase()).filter(Boolean)
    : [];
  if (inputs.length > 3) throw new Error('agent-mcc-codes 最多允许 3 个编码');
  const codes = inputs.map((code) => {
    if (!/^(?:A\d{4}_)?B\d{4}$/u.test(code)) {
      throw new Error(`agent-mcc-codes 包含非法 MCC 编码：${code}；应使用 Axxxx_Bxxxx，当前表内唯一 Bxxxx 可兼容归一化`);
    }
    const normalized = normalizeMccCode(code, records);
    if (!normalized) throw new Error(`agent-mcc-codes 包含当前 MCC 表不存在的编码：${code}`);
    return normalized;
  });
  if (new Set(codes).size !== codes.length) throw new Error('agent-mcc-codes 包含重复 MCC 编码');
  return codes;
}

function agentMccInput(args, query, records) {
  const exactCode = directMccCode(query, records);
  if (exactCode && args['agent-mcc-status'] === undefined && args['agent-mcc-codes'] === undefined) {
    return {
      semanticStatus: 'NOT_REQUIRED_DIRECT_CODE',
      codes: [],
      directCode: exactCode
    };
  }

  const semanticStatus = required(args, 'agent-mcc-status');
  if (!agentMccStatuses.has(semanticStatus)) {
    throw new Error('agent-mcc-status 非法，仅支持 MATCHED、INSUFFICIENT、UNSUPPORTED');
  }
  const codes = parseAgentMccCodes(args, records);
  if (semanticStatus === 'MATCHED' && codes.length === 0) throw new Error('agent-mcc-status=MATCHED 时必须提供 1 到 3 个 agent-mcc-codes');
  if (semanticStatus !== 'MATCHED' && codes.length > 0) throw new Error('agent-mcc-status=INSUFFICIENT|UNSUPPORTED 时不得提供 agent-mcc-codes');
  return { semanticStatus, codes, directCode: '' };
}

function createMccSelectionReceipt(productType, query, result) {
  const codes = result.mergedCandidateCodes.join(',');
  const table = result.mccTableSummary;
  const binding = [productType, assertMccQuery(query), table.sha256, table.recordCount, codes].join('\n');
  return `${mccSelectionReceiptPrefix}${codes}.${createHash('sha256').update(binding).digest('base64url')}`;
}

function resolveMccSelection(productType, query, selectedInput, receipt) {
  const records = loadMccRecords();
  if (typeof receipt !== 'string' || !receipt.startsWith(mccSelectionReceiptPrefix)) {
    throw new Error('MCC selection receipt 格式非法');
  }
  const body = receipt.slice(mccSelectionReceiptPrefix.length);
  const separator = body.lastIndexOf('.');
  const candidateCodes = separator > 0 ? body.slice(0, separator).split(',') : [];
  const currentTable = mccTableSummary(records);
  if (candidateCodes.length < 2 || candidateCodes.length > 8
    || new Set(candidateCodes).size !== candidateCodes.length
    || candidateCodes.some((code) => !records.has(code))
    || receipt !== createMccSelectionReceipt(productType, query, { mergedCandidateCodes: candidateCodes, mccTableSummary: currentTable })) {
    throw new Error('MCC selection receipt 已失效或与当前产品、经营描述、候选表不匹配');
  }
  const selectedCode = normalizeMccCode(selectedInput, records);
  if (!selectedCode || !candidateCodes.includes(selectedCode)) {
    throw new Error('所选 MCC 不属于当前候选快照');
  }
  const candidate = mccCandidateFromRecord(records.get(selectedCode));
  return {
    matchType: 'UNIQUE',
    semanticStatus: 'NOT_REQUIRED_SELECTION',
    deterministicCandidateCodes: [],
    deterministicStrongCandidateCodes: [],
    deterministicWeakCandidateCodes: [],
    agentCandidateCodes: [],
    mergedCandidateCodes: [selectedCode],
    mccTableSummary: currentTable,
    candidates: [candidate]
  };
}

function resolveMccResult(query, args) {
  const records = loadMccRecords();
  const agent = agentMccInput(args, query, records);
  if (agent.directCode) {
    const candidate = mccCandidateFromRecord(records.get(agent.directCode));
    return {
      matchType: 'UNIQUE',
      semanticStatus: agent.semanticStatus,
      deterministicCandidateCodes: [agent.directCode],
      deterministicStrongCandidateCodes: [agent.directCode],
      deterministicWeakCandidateCodes: [],
      agentCandidateCodes: [],
      mergedCandidateCodes: [agent.directCode],
      mccTableSummary: mccTableSummary(records),
      candidates: [candidate]
    };
  }

  const deterministicMatches = deterministicMccMatches(query, { limit: 5 });
  const deterministicStrongCodes = deterministicMatches.filter(({ strength }) => strength === 'STRONG').map(({ record }) => record.code);
  const deterministicWeakCodes = deterministicMatches.filter(({ strength }) => strength === 'WEAK').map(({ record }) => record.code);
  const deterministicCodes = deterministicMatches.map(({ record }) => record.code);
  const agentCodes = agent.codes;
  if (agent.semanticStatus !== 'MATCHED') {
    const finalCodes = deterministicStrongCodes.slice(0, 8);
    const candidates = finalCodes.map((code) => mccCandidateFromRecord(records.get(code)));
    return {
      matchType: candidates.length === 1 ? 'UNIQUE' : candidates.length === 0 ? 'NONE' : 'MULTIPLE',
      semanticStatus: agent.semanticStatus,
      deterministicCandidateCodes: deterministicCodes,
      deterministicStrongCandidateCodes: deterministicStrongCodes,
      deterministicWeakCandidateCodes: deterministicWeakCodes,
      agentCandidateCodes: agentCodes,
      mergedCandidateCodes: finalCodes,
      mccTableSummary: mccTableSummary(records),
      candidates
    };
  }
  const deterministicCodeSet = new Set(deterministicCodes);
  const agentCodeSet = new Set(agentCodes);
  const appendUnique = (target, codes) => {
    for (const code of codes) {
      if (!target.includes(code)) target.push(code);
    }
  };
  const mergedCodes = [];
  appendUnique(mergedCodes, deterministicCodes.filter((code) => agentCodeSet.has(code)));
  appendUnique(mergedCodes, deterministicStrongCodes.filter((code) => !agentCodeSet.has(code)));
  appendUnique(mergedCodes, agentCodes.filter((code) => !deterministicCodeSet.has(code)));
  appendUnique(mergedCodes, deterministicWeakCodes.filter((code) => !agentCodeSet.has(code)));
  const finalCodes = mergedCodes.slice(0, 8);
  const candidates = finalCodes.map((code) => mccCandidateFromRecord(records.get(code)));
  return {
    matchType: candidates.length === 1 ? 'UNIQUE' : candidates.length === 0 ? 'NONE' : 'MULTIPLE',
    semanticStatus: agent.semanticStatus,
    deterministicCandidateCodes: deterministicCodes,
    deterministicStrongCandidateCodes: deterministicStrongCodes,
    deterministicWeakCandidateCodes: deterministicWeakCodes,
    agentCandidateCodes: agentCodes,
    mergedCandidateCodes: finalCodes,
    mccTableSummary: mccTableSummary(records),
    candidates
  };
}

function renderPlanConfirm(productType, mccCandidate) {
  const product = productFor({ 'product-type': productType });
  return renderMessage('onboarding.plan.confirm', product.variant, {
    mccCode: mccCandidate.mccCode,
    mccName: mccCandidate.mccName,
    mccQualification: mccCandidate.qualification
  }, { productType });
}

function requireCustomerMessageDelivery(messageId, message) {
  process.stderr.write(`${internalPrefix}CUSTOMER_MESSAGE_DELIVERY_REQUIRED=${messageId}\n`);
  return message;
}

async function runPlanConfirm(args) {
  const productType = required(args, 'product-type');
  productFor({ ...args, 'product-type': productType });
  return requireCustomerMessageDelivery('onboarding.plan.confirm', renderPlanConfirm(productType, {
    mccCode: required(args, 'mcc-code'),
    mccName: required(args, 'mcc-name'),
    qualification: required(args, 'mcc-qualification')
  }));
}

async function runMccResolvePlan(args) {
  const productType = required(args, 'product-type');
  productFor({ ...args, 'product-type': productType });
  emitStageMetricAsync('onboarding.mcc_prepare.start', { productType });
  const query = required(args, 'query');
  const selected = optional(args, 'select');
  const selectionReceipt = optional(args, 'selection-receipt');
  if ((selected === undefined) !== (selectionReceipt === undefined)) {
    throw new Error('--select 与 --selection-receipt 必须同时提供');
  }
  if (selected !== undefined && (args['agent-mcc-status'] !== undefined || args['agent-mcc-codes'] !== undefined)) {
    throw new Error('MCC 候选选择不得重新传入 Agent 语义候选');
  }
  const result = selected === undefined
    ? resolveMccResult(query, args)
    : resolveMccSelection(productType, query, selected, selectionReceipt);
  const { candidates: _internalCandidates, ...controlResult } = result;
  process.stderr.write(`ALIPAY_AIPAY_INTERNAL:MCC_RESOLUTION=${JSON.stringify(controlResult)}\n`);
  if (result.matchType === 'UNIQUE') {
    return requireCustomerMessageDelivery(
      'onboarding.plan.confirm',
      renderPlanConfirm(productType, result.candidates[0])
    );
  }
  if (result.matchType === 'NONE') {
    return renderMessage('onboarding.mcc.no_match', 'DEFAULT', {}, { productType });
  }
  process.stderr.write(`ALIPAY_AIPAY_INTERNAL:MCC_SELECTION_RECEIPT=${createMccSelectionReceipt(productType, query, result)}\n`);
  return renderMessage('onboarding.mcc.candidates', 'DEFAULT', {
    mccCandidates: result.candidates
  }, { productType });
}

export function renderDiscoverySummary(productType, input) {
  const product = productFor({ 'product-type': productType });
  const variables = {
    signingStatus: normalizeEnum(input.signStatus, signingStatusMap, 'signStatus'),
    applicationStatus: normalizeEnum(input.appFlow, applicationFlowMap, 'appFlow')
  };
  if (product.variant === 'AIPAY') {
    variables.serviceStatus = normalizeEnum(input.serviceFlow, serviceFlowMap, 'serviceFlow');
  }
  return renderMessage('onboarding.discovery.summary', product.variant, variables);
}

function splitFieldInput(value) {
  if (Array.isArray(value)) return value.flatMap((item) => splitFieldInput(item));
  if (typeof value !== 'string') throw new Error('missingFields 必须是字符串或字符串数组');
  return value
    .split(/[、,，\n]/u)
    .map((item) => item.trim())
    .filter(Boolean);
}

function normalizeMaterialField(category, raw) {
  let fields;
  if (directFieldAliases.has(raw)) fields = directFieldAliases.get(raw);
  else if (category === 'signing' && /签约.*截图/.test(raw)) fields = ['首页截图', '商品页截图', '支付页截图'];
  else if (/首页.*截图/.test(raw)) fields = ['首页截图'];
  else if (/商品.*截图/.test(raw)) fields = ['商品页截图'];
  else if (/支付.*截图/.test(raw)) fields = ['支付页截图'];
  else if (category === 'signing' && /^(?:截图|三张截图|3张截图)$/.test(raw)) fields = ['首页截图', '商品页截图', '支付页截图'];
  else if (/服务.*价格|服务.*单价/.test(raw)) fields = ['服务单价'];
  else if (/请求.*示例.*JSON/i.test(raw)) fields = ['请求示例JSON'];
  else if (/iOS.*Bundle/i.test(raw)) fields = ['iOS Bundle ID（bundleId）'];
  else if (/Android.*包名/i.test(raw)) fields = ['Android 应用包名（appPackage）'];
  else if (/Android.*签名/i.test(raw)) fields = ['Android 应用签名摘要（appSign）'];

  const allowed = materialFieldsByCategory[category] || [];
  if (!fields || fields.some((field) => !allowed.includes(field))) {
    throw new Error(`材料字段不适用于 ${category}：${raw}；允许字段：${allowed.join('、')}`);
  }
  return fields;
}

function normalizeMissingFields(category, missingFields) {
  const normalized = [];
  for (const raw of splitFieldInput(missingFields)) {
    for (const field of normalizeMaterialField(category, raw)) {
      if (!normalized.includes(field)) normalized.push(field);
    }
  }
  if (normalized.length === 0) throw new Error('缺少 missingFields');
  return normalized.join('、');
}

async function runMaterialCollect(args) {
  const productType = required(args, 'product-type');
  productFor({ ...args, 'product-type': productType });
  const category = required(args, 'category');
  const categoryName = categoryNames[category];
  if (!categoryName) throw new Error('category 非法，仅支持 signing、service、application');

  const state = required(args, 'state').toUpperCase().replace(/-/g, '_');
  const stateRule = materialStates[state];
  if (!stateRule) throw new Error('state 非法，仅支持 INITIAL、PARTIAL、INVALID、APP_WEB_INITIAL、APP_MOBILE_INITIAL');

  if (state === 'APP_WEB_INITIAL' || state === 'APP_MOBILE_INITIAL') {
    if (category !== 'application') throw new Error(`${state} 只适用于 application 类别`);
    if (state === 'APP_WEB_INITIAL' && productType === 'apppay') {
      throw new Error('APP_WEB_INITIAL 只适用于 aipay、webpay');
    }
    if (state === 'APP_MOBILE_INITIAL' && productType !== 'apppay') {
      throw new Error('APP_MOBILE_INITIAL 只适用于 apppay');
    }
    return renderMessage('materials.category.collect', stateRule.variant, {
      categoryName: '应用资料',
      currentStatus: stateRule.currentStatus,
      missingFields: state === 'APP_WEB_INITIAL' ? '应用公钥' : '应用平台和对应资料、应用公钥'
    }, { productType });
  }

  const input = optional(args, 'missing-fields') !== undefined
    ? { missingFields: args['missing-fields'] }
    : await readStdin();
  const variant = state === 'INITIAL' && category === 'service'
    ? 'SERVICE_INITIAL'
    : stateRule.variant;
  const missingFields = normalizeMissingFields(category, input.missingFields);
  if (category === 'application' && productType !== 'apppay') {
    const incompatibleFields = missingFields.split('、').filter((field) => field !== '应用公钥');
    if (incompatibleFields.length > 0) {
      throw new Error(`${productType} 的应用资料只允许应用公钥`);
    }
  }
  return renderMessage('materials.category.collect', variant, {
    categoryName,
    currentStatus: stateRule.currentStatus,
    missingFields
  }, { productType });
}

function renderApplicationCandidates(applicationType, applicationCandidates, selectionState = 'initial') {
  const onlineCount = applicationCandidates.filter((candidate) => candidate?.status === 'ON_LINE').length;
  const variant = applicationCandidates.length === 0
    ? 'EMPTY'
    : onlineCount === 0
      ? 'PENDING_ONLY'
      : 'ONLINE_WITH_OPTIONAL_PENDING';
  const facts = renderMessage('application.candidates.facts', variant, { applicationType, applicationCandidates });
  if (applicationCandidates.length === 0) return facts;
  const selectionVariant = `${onlineCount === 0 ? 'PENDING' : 'ONLINE'}_${applicationType === 'WEBAPP' ? 'WEB' : 'MOBILE'}_OR_NEW`;
  const selection = renderMessage('application.candidate.select', selectionVariant, {});
  const message = selectionState === 'initial'
    ? `${facts}\n\n${selection}`
    : `${facts}\n\n${renderMessage('application.candidate.invalid', 'DEFAULT', {})}\n\n${selection}`;
  return message;
}

async function runApplicationCandidates(args) {
  const applicationType = required(args, 'application-type');
  if (!['WEBAPP', 'MOBILEAPP'].includes(applicationType)) throw new Error('application-type 非法，仅支持 WEBAPP、MOBILEAPP');
  const selectionState = optional(args, 'selection-state') ?? 'initial';
  if (!['initial', 'invalid'].includes(selectionState)) throw new Error('selection-state 非法，仅支持 initial、invalid');
  const applicationCandidates = optional(args, 'candidates-json') !== undefined
    ? parseJsonArg(args, 'candidates-json', '应用候选输入')
    : await readStdin();
  if (!Array.isArray(applicationCandidates)) throw new Error('应用候选输入必须是 JSON 数组');
  canonicalCandidates(applicationCandidates);
  if (selectionState === 'invalid' && applicationCandidates.length === 0) {
    throw new Error('应用候选为空时不得使用 invalid 选择状态');
  }
  const message = renderApplicationCandidates(applicationType, applicationCandidates, selectionState);
  return applicationCandidates.length === 0
    ? message
    : requireCustomerMessageDelivery('application.candidate.select', message);
}

async function runServiceCandidates(args) {
  const selectionState = optional(args, 'selection-state') ?? 'initial';
  if (!['initial', 'invalid'].includes(selectionState)) {
    throw new Error('selection-state 非法，仅支持 initial、invalid');
  }
  const serviceCandidates = optional(args, 'candidates-json') !== undefined
    ? parseJsonArg(args, 'candidates-json', '服务候选输入')
    : await readStdin();
  if (!Array.isArray(serviceCandidates)) throw new Error('服务候选输入必须是 JSON 数组');
  if (selectionState === 'invalid' && serviceCandidates.length === 0) {
    throw new Error('服务候选为空时不得使用 invalid 选择状态');
  }
  const variant = serviceCandidates.length === 0 ? 'EMPTY' : 'DEFAULT';
  const facts = renderMessage('service.candidates.facts', variant, { serviceCandidates });
  if (serviceCandidates.length === 0) return facts;
  const selection = renderMessage('service.candidate.select', 'DEFAULT', {});
  if (selectionState === 'initial') return `${facts}\n\n${selection}`;
  const invalid = renderMessage('service.candidate.invalid', 'DEFAULT', {});
  return `${facts}\n\n${invalid}\n\n${selection}`;
}

function canonicalCandidates(candidates) {
  if (!Array.isArray(candidates)) throw new Error('应用候选快照必须是 JSON 数组');
  const allowedKeys = new Set(['appId', 'appName', 'status']);
  const seenIds = new Set();
  const rows = candidates.map((candidate) => {
    if (!candidate || typeof candidate !== 'object' || Array.isArray(candidate)) {
      throw new Error('应用候选快照项必须是 JSON 对象');
    }
    const keys = Object.keys(candidate);
    if (keys.some((key) => !allowedKeys.has(key))
        || !['appId', 'appName', 'status'].every((key) => Object.prototype.hasOwnProperty.call(candidate, key))) {
      throw new Error('应用候选快照项必须且只能包含 appId、appName、status');
    }
    if (![candidate.appId, candidate.appName, candidate.status].every((value) => typeof value === 'string')) {
      throw new Error('应用候选快照字段必须是字符串');
    }
    if (candidate.appId && candidate.appId !== '未知') {
      if (seenIds.has(candidate.appId)) throw new Error(`应用候选快照包含重复 appId: ${candidate.appId}`);
      seenIds.add(candidate.appId);
    }
    return {
      appId: candidate.appId,
      appName: candidate.appName,
      status: candidate.status
    };
  });
  return JSON.stringify(rows.sort((left, right) => {
    const leftValue = JSON.stringify(left);
    const rightValue = JSON.stringify(right);
    return leftValue < rightValue ? -1 : leftValue > rightValue ? 1 : 0;
  }));
}

async function runApplicationRecheck(args) {
  const applicationType = required(args, 'application-type');
  if (!['WEBAPP', 'MOBILEAPP'].includes(applicationType)) throw new Error('application-type 非法，仅支持 WEBAPP、MOBILEAPP');
  const input = optional(args, 'previous-candidates-json') !== undefined || optional(args, 'current-candidates-json') !== undefined
    ? {
        previousCandidates: parseJsonArg(args, 'previous-candidates-json', '上一轮应用候选快照'),
        currentCandidates: parseJsonArg(args, 'current-candidates-json', '当前应用候选快照')
      }
    : await readStdin();
  if (!input || typeof input !== 'object' || Array.isArray(input)) throw new Error('应用候选重查输入必须是 JSON 对象');
  const previousCanonical = canonicalCandidates(input.previousCandidates);
  const currentCanonical = canonicalCandidates(input.currentCandidates);
  // Rendering both snapshots applies the same content and sensitivity checks even on the silent path.
  renderApplicationCandidates(applicationType, input.previousCandidates);
  const output = renderApplicationCandidates(applicationType, input.currentCandidates);
  if (previousCanonical === currentCanonical) {
    process.stderr.write(`${internalPrefix}APPLICATION_RECHECK_RESULT=UNCHANGED\n`);
    return '';
  }
  const result = input.currentCandidates.length === 0 ? 'CHANGED_EMPTY' : 'CHANGED_NONEMPTY';
  process.stderr.write(`${internalPrefix}APPLICATION_RECHECK_RESULT=${result}\n`);
  process.stderr.write(`${internalPrefix}APPLICATION_RECHECK_MESSAGE=READY\n`);
  return output;
}

function closeoutInputFromArgs(args) {
  const retiredArgs = [
    'input-json',
    'product-name',
    'process-result-title',
    'application-operation-actual-status',
    'next-flow-reminder'
  ].filter((name) => Object.prototype.hasOwnProperty.call(args, name));
  if (retiredArgs.length > 0) {
    throw new Error(`closeout 已移除旧参数：${retiredArgs.map((name) => `--${name}`).join('、')}`);
  }
  const productType = required(args, 'product-type');
  const product = productFor({ 'product-type': productType });
  const rootIntent = required(args, 'root-intent');
  if (!['onboarding_only', 'full_process'].includes(rootIntent)) {
    throw new Error('root-intent 非法，仅支持 onboarding_only、full_process');
  }
  if (productType !== 'aipay' && Object.prototype.hasOwnProperty.call(args, 'service-result')) {
    throw new Error('webpay/apppay closeout 的 service-result 由 runner 派生，禁止传入 --service-result');
  }
  if (rootIntent === 'onboarding_only' && Object.prototype.hasOwnProperty.call(args, 'integration-result')) {
    throw new Error('onboarding_only closeout 的 integration-result 由 runner 派生，禁止传入 --integration-result');
  }
  const signingResult = required(args, 'signing-result');
  const applicationResult = required(args, 'application-result');
  const remainingActions = required(args, 'remaining-actions');
  const serviceResult = productType === 'aipay' ? required(args, 'service-result') : '无需处理';
  const integrationResult = rootIntent === 'onboarding_only'
    ? '不在本轮执行范围'
    : required(args, 'integration-result');
  const manualVerificationItems = optional(args, 'manual-verification-items');
  const hasManualVerificationItems = manualVerificationItems !== undefined && manualVerificationItems !== '无';
  const serviceComplete = productType === 'aipay'
    ? ['已复用', '创建成功，状态未取得', '修改成功，状态未取得', '已完成'].includes(serviceResult)
    : true;
  const branchesComplete = signingResult === '已生效'
    && serviceComplete
    && applicationResult === '已上线且配置完整'
    && remainingActions === '无'
    && !hasManualVerificationItems;
  const input = {
    productName: product.productName,
    processResultTitle: branchesComplete ? '支付产品-产品开通已完成' : '流程进展',
    integrationResult,
    signingResult,
    serviceResult,
    applicationResult,
    remainingActions,
    nextFlowReminder: rootIntent === 'onboarding_only'
      ? '还需完成支付产品-代码开发，才能在业务系统中实际发起支付。'
      : '代码开发已在本轮执行；后续只按上表实际待办继续。'
  };
  const optionalMapping = {
    'sandbox-config-state': 'sandboxConfigState',
    'manual-verification-items': 'manualVerificationItems',
    'application-operation-app-id': 'applicationOperationAppId',
    'application-operation-next-action': 'applicationOperationNextAction',
    'application-operation-app-key-save-path': 'applicationOperationAppKeySavePath'
  };
  for (const [argName, fieldName] of Object.entries(optionalMapping)) {
    if (Object.prototype.hasOwnProperty.call(args, argName)) input[fieldName] = required(args, argName);
  }
  if (input.applicationOperationAppId) input.applicationOperationActualStatus = applicationResult;
  return input;
}

async function runCloseout(args) {
  const variables = closeoutInputFromArgs(args);
  const rendered = renderMessage('process.partial_result', 'DEFAULT', variables);
  const terminalReason = args['root-intent'] === 'full_process' && variables.integrationResult !== '已完成'
    ? 'partial_with_remaining_actions'
    : variables.processResultTitle === '支付产品-产品开通已完成'
      ? 'completed'
      : 'partial_with_remaining_actions';
  emitTerminalMetric({
    productName: variables.productName,
    rootIntent: args['root-intent'],
    ...terminalMetricContextFromArgs(args, {
      rootIntent: args['root-intent'],
      terminalReason
    })
  });
  return rendered;
}

function runServiceCreateSummary(args) {
  return renderMessage('service.create.summary', 'DEFAULT', {
    serviceName: required(args, 'service-name'),
    serviceDescription: required(args, 'service-description'),
    serviceUrl: required(args, 'service-url'),
    servicePricing: required(args, 'service-pricing'),
    serviceSchema: required(args, 'service-schema')
  });
}

function runServiceUpdateConfirm(args) {
  return renderMessage('onboarding.write.confirm', 'SERVICE_UPDATE_ONLY', {
    sessionSummary: required(args, 'session-summary'),
    subjectSummary: required(args, 'subject-summary'),
    productName: 'AI 按量付费',
    actionTypes: '服务修改',
    serviceId: required(args, 'service-id'),
    serviceName: required(args, 'service-name'),
    serviceDescription: required(args, 'service-description'),
    serviceUrl: required(args, 'service-url'),
    servicePricing: required(args, 'service-pricing'),
    serviceSchema: required(args, 'service-schema')
  });
}

function runHarmonyManualCreate() {
  return renderMessage('application.harmony.manual_create', 'DEFAULT', {});
}

function runApplicationReuseNoKey(args) {
  return renderMessage('application.reuse.no_key', 'DEFAULT', {
    appId: required(args, 'app-id')
  });
}

function runSigningResult(args) {
  const variables = {
    actualStatus: required(args, 'actual-status'),
    nextAction: required(args, 'next-action')
  };
  const feeDisplay = optional(args, 'fee-display');
  if (feeDisplay !== undefined) variables.feeDisplay = feeDisplay;
  return renderMessage('signing.operation.result', feeDisplay === undefined ? 'WITHOUT_FEE' : 'WITH_FEE', variables);
}

function runServiceResult(args) {
  return renderMessage('service.operation.result', 'DEFAULT', {
    serviceId: required(args, 'service-id'),
    actualResult: required(args, 'actual-result')
  });
}

function runApplicationResult(args) {
  const actualStatus = required(args, 'actual-status');
  if (actualStatus === '需人工配置') {
    if (optional(args, 'next-action') !== undefined) throw new Error('需人工配置的下一步由消息目录固定，不接收 --next-action');
    if (optional(args, 'app-key-save-path') !== undefined) throw new Error('需人工配置表示支付宝公钥未本地保存，禁止传入 --app-key-save-path');
    return renderMessage('application.operation.result', 'ALIPAY_PUBLIC_KEY_MANUAL_CONFIGURATION', {
      appId: required(args, 'app-id'),
      actualStatus
    });
  }
  const variables = {
    appId: required(args, 'app-id'),
    actualStatus,
    nextAction: required(args, 'next-action')
  };
  const appKeySavePath = optional(args, 'app-key-save-path');
  if (appKeySavePath !== undefined) variables.appKeySavePath = appKeySavePath;
  return renderMessage('application.operation.result', 'DEFAULT', variables);
}

export async function runOnboardingMessageCli(argv = process.argv) {
  const { command, args } = parseArgs(argv);
  if (command === 'platform-entry') {
    const message = runPlatformEntry(args);
    if (message) console.log(message);
    return;
  }
  if (command === 'product-clarify') {
    console.log(runProductClarify());
    return;
  }
  if (command === 'enterprise-unsupported') {
    console.log(runEnterpriseUnsupported(args));
    return;
  }
  if (command === 'mcc-clarify') {
    console.log(await runMccClarify(args));
    return;
  }
  if (command === 'mcc-resolve-plan') {
    const message = await runMccResolvePlan(args);
    if (message) console.log(message);
    return;
  }
  if (command === 'plan-confirm') {
    console.log(await runPlanConfirm(args));
    return;
  }
  if (command === 'material-collect') {
    console.log(await runMaterialCollect(args));
    return;
  }
  if (command === 'application-candidates') {
    console.log(await runApplicationCandidates(args));
    return;
  }
  if (command === 'service-candidates') {
    console.log(await runServiceCandidates(args));
    return;
  }
  if (command === 'application-recheck') {
    const message = await runApplicationRecheck(args);
    if (message) console.log(message);
    return;
  }
  if (command === 'closeout') {
    console.log(await runCloseout(args));
    return;
  }
  if (command === 'service-create-summary') {
    console.log(runServiceCreateSummary(args));
    return;
  }
  if (command === 'service-update-confirm') {
    console.log(runServiceUpdateConfirm(args));
    return;
  }
  if (command === 'application-harmony-manual-create') {
    console.log(runHarmonyManualCreate());
    return;
  }
  if (command === 'application-reuse-no-key') {
    console.log(runApplicationReuseNoKey(args));
    return;
  }
  if (command === 'signing-result') {
    console.log(runSigningResult(args));
    return;
  }
  if (command === 'service-result') {
    console.log(runServiceResult(args));
    return;
  }
  if (command === 'application-result') {
    console.log(runApplicationResult(args));
    return;
  }
  throw new Error('用法: onboarding_message_runner.mjs <platform-entry|product-clarify|enterprise-unsupported|mcc-resolve-plan|plan-confirm|mcc-clarify|material-collect|application-candidates|service-candidates|application-recheck|closeout|service-create-summary|service-update-confirm|application-harmony-manual-create|application-reuse-no-key|signing-result|service-result|application-result> ...');
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  runOnboardingMessageCli().catch((error) => {
    console.error(`ONBOARDING_MESSAGE_ERROR:${error.message}`);
    process.exitCode = 1;
  });
}
