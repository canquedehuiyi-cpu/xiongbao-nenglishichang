#!/usr/bin/env node
/**
 * guidance.mjs — 用户分层引导引擎 (v1.0.7)
 *
 * 目的: 让全流程引导"既不让用户反感, 又真实可靠有用"。
 *   - 画像识别: 从用户首轮表述判定 新手/进阶/成熟, 引导深度自适应
 *   - 偏好/进度记忆: 本地 JSON 记录已确认的平台/国家/品类 与 上次进行的 SOP 步骤,
 *     支持"接着上次继续", 避免每次重复询问
 *   - 下一步推荐: 基于画像+进度推荐最合适的入口/SOP/工具
 *   - 隐私安全: 仅存本地(OS 临时目录), 可 --reset 一键清理, 不收集账号等敏感信息
 *
 * 用法:
 *   node references/scripts/guidance.mjs --detect "第一次做跨境电商, 完全不懂怎么开始"
 *   node references/scripts/guidance.mjs --profile 新手
 *   node references/scripts/guidance.mjs --get
 *   node references/scripts/guidance.mjs --set platform amazon
 *   node references/scripts/guidance.mjs --set country US
 *   node references/scripts/guidance.mjs --save-progress SOP-02-product-selection step3
 *   node references/scripts/guidance.mjs --next
 *   node references/scripts/guidance.mjs --reset
 *   node references/scripts/guidance.mjs --version
 *
 * 参数:
 *   --detect <文本>      根据表述自动判定画像(启发式关键词, 非AI语义)
 *   --profile <档位>     手动设置画像: 新手/进阶/成熟
 *   --get                读取当前画像/偏好/进度
 *   --set <key> <val>    记录一条偏好(如 platform/country/category/budget)
 *   --save-progress <sop> <step>  记录进行到的 SOP 步骤
 *   --next               基于画像+进度推荐下一步
 *   --reset              清空本地状态
 *   --json               输出JSON
 */

import { readFileSync, writeFileSync, mkdirSync, existsSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';

const VERSION = '1.0.7';
const PROFILE_FILE = join(tmpdir(), 'gbi-guidance', 'profile.json');
const PROFILES = ['新手', '进阶', '成熟'];

const args = process.argv.slice(2);
const wantJson = args.includes('--json');
if (args.includes('--version')) {
  process.stdout.write(VERSION + '\n');
  process.exit(0);
}
const KNOWN_FLAGS = new Set(['--detect', '--profile', '--set', '--save-progress', '--next', '--get', '--reset', '--json', '--version']);
const unknownFlags = args.filter((a) => a.startsWith('--') && !KNOWN_FLAGS.has(a));
if (unknownFlags.length) {
  console.error('未知参数: ' + unknownFlags.join(' ') + '\n可用参数: --detect <文本> --profile <画像> --set <键> <值> --save-progress <键> <值> --next --get --reset --json');
  process.exit(1);
}
function getArg(name) {
  const i = args.indexOf('--' + name);
  return i >= 0 ? args[i + 1] : null;
}

const NEWBIE_KW = ['第一次', '新手', '刚开始', '怎么开始', '从哪开始', '完全不懂', '小白', '零基础', '没做过', '怎么开店', '入驻', '开店流程', '什么都不懂', '一点都不会'];
const INTERMEDIATE_KW = ['在卖', '做了', '在运营', '上架了', '有点经验', '现在做', '目前', '还没', '补货', '选品', '测款', '上架', '发货'];
const ADVANCED_KW = ['roi', 'acos', '毛利', '利润率', '月销', '旺季', '备货', '多账号', '规模', '优化', '复购', '批量', '止损', 'scaling', '库存周转', '广告'];

function emptyState() {
  return { profile: null, prefs: {}, progress: null };
}
function readState() {
  if (!existsSync(PROFILE_FILE)) return emptyState();
  try {
    const s = JSON.parse(readFileSync(PROFILE_FILE, 'utf-8'));
    return { profile: s.profile || null, prefs: s.prefs || {}, progress: s.progress || null };
  } catch {
    return emptyState();
  }
}
function writeState(state) {
  mkdirSync(join(tmpdir(), 'gbi-guidance'), { recursive: true });
  writeFileSync(PROFILE_FILE, JSON.stringify(state, null, 2), 'utf-8');
}

function detect(text) {
  const t = (text || '').toLowerCase();
  const count = (list) => list.filter((kw) => t.includes(kw)).length;
  const signals = { newbie: count(NEWBIE_KW), intermediate: count(INTERMEDIATE_KW), advanced: count(ADVANCED_KW) };
  const profile = signals.advanced >= 1 ? '成熟'
    : signals.newbie >= 1 && signals.newbie >= signals.intermediate ? '新手'
    : signals.intermediate >= 1 ? '进阶'
    : null;
  return { signals, profile };
}

function recommend(state) {
  const p = state.profile;
  const prog = state.progress;
  const prefs = state.prefs;
  const hasCorePref = !!(prefs.platform && prefs.country);
  if (!p && !prog) {
    return { stage: 'welcome', message: '建议先确认三要素: 目标国家/目标平台/目标类目 (可依次 --set country/platform/category)', tools: [] };
  }
  if (!prog) {
    if (p === '新手') return { stage: 'onboarding', sop: 'SOP-01-first-time-setup', step: 'Step 1 注册主体', message: '新手建议从开店入驻 SOP 起步', tools: ['knowledge-filter --entry selection'] };
    if (p === '成熟') return { stage: 'direct', entry: 'profit', message: '成熟卖家直接看利润/经营数据', tools: ['profit_calculator.py', 'bsr_analyzer.py'] };
    return { stage: 'mid', entry: 'selection', message: hasCorePref ? '已确认 ' + prefs.platform + '/' + prefs.country + ', 可直接进入选品或定价' : '建议先确认平台/国家后进入选品', tools: ['knowledge-filter --entry selection', 'router --intent 选品'] };
  }
  return { stage: 'resume', sop: prog.sopId, step: prog.step || '下一步', message: '接着上次进度继续: ' + prog.sopId + (prog.step ? ' @ ' + prog.step : ''), tools: [] };
}

function payload(extra) {
  return Object.assign({
    ok: true, tool: 'guidance', version: VERSION,
    schema: 'global-ecommerce-intelligence/guidance',
    generatedAt: new Date().toISOString(),
  }, extra);
}
function emit(obj, text) {
  if (wantJson) process.stdout.write(JSON.stringify(obj, null, 2) + '\n');
  else if (text) console.log(text);
  else process.stdout.write(JSON.stringify(obj, null, 2) + '\n');
}

const detectText = getArg('detect');
if (detectText !== null && detectText !== undefined) {
  const r = detect(detectText);
  const state = readState();
  if (r.profile) {
    state.profile = r.profile;
    writeState(state);
  }
  emit(payload({ mode: 'detect', text: detectText.slice(0, 120), profile: r.profile, signals: r.signals, detectedFrom: r.profile ? '关键词启发式(非AI语义)' : null, note: r.profile ? '已应用为当前画像, 可用 --profile 手动调整' : '未识别到明确画像信号, 可用 --profile 手动设置画像' }),
    r.profile ? '画像识别: ' + r.profile + ' (信号: 新手=' + r.signals.newbie + ', 进阶=' + r.signals.intermediate + ', 成熟=' + r.signals.advanced + ')' : '未识别到明确画像信号, 可用 --profile 手动设置画像');
  process.exit(0);
}

const profileArg = getArg('profile');
if (profileArg) {
  if (!PROFILES.includes(profileArg)) {
    console.error('--profile 仅支持: ' + PROFILES.join('/'));
    process.exit(1);
  }
  const state = readState();
  state.profile = profileArg;
  writeState(state);
  emit(payload({ mode: 'profile', profile: profileArg }), '已设置画像: ' + profileArg);
  process.exit(0);
}

const setKey = getArg('set');
if (setKey) {
  const valIdx = args.indexOf('--set') + 2;
  const val = args[valIdx] ? args[valIdx] : null;
  if (!val) {
    console.error('用法: --set <key> <value> (如 --set platform amazon)');
    process.exit(1);
  }
  const state = readState();
  state.prefs[setKey] = val;
  writeState(state);
  emit(payload({ mode: 'set', key: setKey, value: val, prefs: state.prefs }), '已记录偏好: ' + setKey + ' = ' + val);
  process.exit(0);
}

const progArg = getArg('save-progress');
if (progArg) {
  const stepIdx = args.indexOf('--save-progress') + 2;
  const step = args[stepIdx] ? args[stepIdx] : null;
  const state = readState();
  state.progress = { sopId: progArg, step, updatedAt: new Date().toISOString() };
  writeState(state);
  emit(payload({ mode: 'save-progress', progress: state.progress }), '已记录进度: ' + progArg + (step ? ' @ ' + step : ''));
  process.exit(0);
}

if (args.includes('--next')) {
  const state = readState();
  const rec = recommend(state);
  emit(payload({ mode: 'next', profile: state.profile, prefs: state.prefs, progress: state.progress, recommendation: rec }), '下一步建议: ' + rec.message + (rec.tools && rec.tools.length ? '  工具: ' + rec.tools.join(', ') : ''));
  process.exit(0);
}

if (args.includes('--get')) {
  const state = readState();
  emit(payload({ mode: 'get', state }), '当前画像: ' + (state.profile || '未设置') + '\n偏好: ' + JSON.stringify(state.prefs) + '\n进度: ' + (state.progress ? state.progress.sopId + (state.progress.step ? ' @ ' + state.progress.step : '') : '无'));
  process.exit(0);
}

if (args.includes('--reset')) {
  writeState(emptyState());
  emit(payload({ mode: 'reset', cleared: true }), '已清空本地状态');
  process.exit(0);
}

console.error('用法: node references/scripts/guidance.mjs --detect <文本> | --profile 新手|进阶|成熟 | --set <key> <val> | --save-progress <sop> <step> | --next | --get | --reset | --version');
process.exit(1);
