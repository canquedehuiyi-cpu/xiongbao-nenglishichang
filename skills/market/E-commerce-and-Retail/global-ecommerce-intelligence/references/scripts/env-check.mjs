#!/usr/bin/env node
/**
 * env-check.mjs — 环境验证脚本 (v1.0.7)
 *
 * 检测 Python / Node 可用性、各脚本存在性，返回 JSON 报告。
 * --audit 模式会真实运行每个脚本的固定用例并断言关键字段，作为发行前门禁。
 *
 * 用法：
 *   node references/scripts/env-check.mjs --json          # 环境+脚本存在性
 *   node references/scripts/env-check.mjs --audit --json  # 额外逐脚本运行冒烟用例
 *   node references/scripts/env-check.mjs --version
 *
 * 退出码：0 全部可用，1 Python不可用（部分脚本降级），2 关键工具缺失
 */

import { existsSync } from 'node:fs';
import { spawnSync } from 'node:child_process';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const SCRIPTS_DIR = __dirname;
const VERSION = '1.0.7';

const args = process.argv.slice(2);
const wantJson = args.includes('--json');
const wantAudit = args.includes('--audit');
if (args.includes('--version')) {
  process.stdout.write(VERSION + '\n');
  process.exit(0);
}
const KNOWN_FLAGS = new Set(['--json', '--audit', '--version']);
const unknownFlags = args.filter((a) => a.startsWith('--') && !KNOWN_FLAGS.has(a));
if (unknownFlags.length) {
  console.error('未知参数: ' + unknownFlags.join(' ') + '\n可用参数: --audit --json');
  process.exit(1);
}

// 每条目: [文件名, 语言, 冒烟参数, 断言关键词(JSON输出中必须出现)]
const PY_SCRIPTS = [
  ['profit_calculator.py', 'python', ['--price', '199', '--cost', '80', '--commission', '15', '--json'], '"tool"'],
  ['bsr_analyzer.py', 'python', ['--bsr', '1500', '--category', 'home', '--json'], '"tool"'],
  ['sentiment_analyzer.py', 'python', ['--text', '质量很好，发货快', '--lang', 'zh', '--json'], '"tool"'],
  ['inventory_calculator.py', 'python', ['--daily-sales', '10', '--lead-time', '15', '--safety-days', '7', '--on-hand', '100', '--json'], '"tool"'],
  ['tax_calculator.py', 'python', ['--country', 'US', '--state', 'CA', '--price', '100', '--json'], '"tool"'],
];
const MJS_SCRIPTS = [
  ['env-check.mjs', 'node', ['--json'], '"node"'],
  ['fetch-rates.mjs', 'node', ['--no-cache', '--json'], '"rates"'],
  ['price-elasticity.mjs', 'node', ['--p1', '29.99', '--q1', '1000', '--p2', '27.99', '--q2', '1300', '--json'], '"tool"'],
  ['knowledge-filter.mjs', 'node', ['--entry', 'selection', '--json'], '"entry"'],
  ['sop-timeliness-check.mjs', 'node', ['--json'], '"totalFiles"'],
  ['competitor-checklist.mjs', 'node', ['--product', 'B0123456', '--platform', 'amazon', '--json'], '"tool"'],
  ['compliance-scan.mjs', 'node', ['--text', '高品质不锈钢保温杯', '--json'], '"tool"'],
  ['listing-scorer.mjs', 'node', ['--title', 'Test title', '--bullets', 'a', '--json'], '"tool"'],
  ['price-monitor.mjs', 'node', ['--product', 'TEST-001', '--price', '99', '--dry-run', '--json'], '"tool"'],
  ['router.mjs', 'node', ['--intent', '算利润', '--json'], '"entry"'],
  ['orchestrator.mjs', 'node', ['--dry-run', '--tool', 'profit', '--json'], '"tool"'],
  ['guidance.mjs', 'node', ['--detect', '新手第一次开店', '--json'], '"profile"'],
  ['fact-check.mjs', 'node', ['--list', '--json'], '"factCount"'],
  ['agent-readiness.mjs', 'node', ['--demo', '--json'], '"score"'],
];

function checkCommand(cmd) {
  const c = ['--version'];
  try {
    const r = spawnSync(cmd, c, { encoding: 'utf-8', timeout: 5000 });
    if (r.status === 0 || (r.stdout && r.stdout.trim())) {
      return { available: true, version: (r.stdout || r.stderr || '').trim().split('\n')[0] };
    }
  } catch { /* fallthrough */ }
  try {
    const r = spawnSync(cmd, c, { encoding: 'utf-8', shell: true, timeout: 5000 });
    if (r.status === 0 || (r.stdout && r.stdout.trim())) {
      return { available: true, version: (r.stdout || r.stderr || '').trim().split('\n')[0] };
    }
  } catch { /* ignore */ }
  return { available: false, version: null };
}

function runSmoke(file, lang, smokeArgs) {
  const cmd = lang === 'python' ? (pyBin()) : 'node';
  const abs = join(SCRIPTS_DIR, file);
  try {
    const r = spawnSync(cmd, [abs, ...smokeArgs], { encoding: 'utf-8', timeout: 30000 });
    if (r.status !== 0) return { ok: false, note: '退出码 ' + r.status + ': ' + (r.stderr || '').trim().slice(0, 120) };
    if (!r.stdout || !r.stdout.trim()) return { ok: false, note: '无输出' };
    return { ok: true, note: '输出 ' + r.stdout.length + ' 字符' };
  } catch (e) {
    return { ok: false, note: '异常: ' + e.message };
  }
}

let _pyInfo = null;
function detectPy() {
  if (_pyInfo) return _pyInfo;
  const c3 = checkCommand('python3');
  if (c3.available) { _pyInfo = { bin: 'python3', available: true, version: c3.version }; return _pyInfo; }
  const cpy = checkCommand('python');
  if (cpy.available) { _pyInfo = { bin: 'python', available: true, version: cpy.version }; return _pyInfo; }
  _pyInfo = { bin: 'python3', available: false, version: null };
  return _pyInfo;
}
function pyBin() { return detectPy().bin; }

const nodeInfo = checkCommand('node');
const pyInfo = detectPy();

const scripts = {};
for (const [f] of PY_SCRIPTS) {
  const exists = existsSync(join(SCRIPTS_DIR, f));
  scripts[f] = {
    ok: exists && pyInfo.available,
    note: !exists ? '文件缺失' : (!pyInfo.available ? 'Python不可用，降级到知识模式' : null),
    lang: 'python',
  };
}
for (const [f] of MJS_SCRIPTS) {
  const exists = existsSync(join(SCRIPTS_DIR, f));
  scripts[f] = {
    ok: exists && nodeInfo.available,
    note: !exists ? '文件缺失' : null,
    lang: 'node',
  };
}

if (wantAudit) {
  for (const [f, lang, smokeArgs] of [...PY_SCRIPTS, ...MJS_SCRIPTS]) {
    if (!scripts[f].ok) {
      scripts[f].smoke = { ok: false, note: '前置不可用，跳过冒烟' };
      continue;
    }
    scripts[f].smoke = runSmoke(f, lang, smokeArgs);
    if (!scripts[f].smoke.ok) scripts[f].ok = false;
  }
}

const allPyOk = PY_SCRIPTS.every(([f]) => scripts[f].ok);
const allMjsOk = MJS_SCRIPTS.every(([f]) => scripts[f].ok);
let summary, exitCode;
if (allPyOk && allMjsOk) {
  summary = '全部工具可用，可执行完整分析' + (wantAudit ? '（冒烟全部通过）' : '');
  exitCode = 0;
} else if (allMjsOk) {
  summary = 'Python相关脚本降级到知识模式';
  exitCode = 1;
} else {
  summary = '关键工具缺失，仅可用知识模式';
  exitCode = 2;
}

const payload = {
  ok: exitCode === 0,
  tool: 'env-check',
  version: VERSION,
  schema: 'global-ecommerce-intelligence/env-check',
  generatedAt: new Date().toISOString(),
  node: nodeInfo,
  python: pyInfo,
  scripts,
  summary,
  exitCode,
};

if (wantJson) {
  process.stdout.write(JSON.stringify(payload, null, 2) + '\n');
} else {
  console.log('环境验证报告' + (wantAudit ? '（含冒烟）' : ''));
  console.log('='.repeat(40));
  console.log('  Node.js: ' + (nodeInfo.available ? nodeInfo.version : '不可用'));
  console.log('  Python:  ' + (pyInfo.available ? pyInfo.version : '不可用'));
  console.log('  脚本状态:');
  for (const [name, s] of Object.entries(scripts)) {
    const smoke = s.smoke ? (s.smoke.ok ? ' 冒烟✓' : ' 冒烟✗') : '';
    console.log('    ' + (s.ok ? '✓' : '✗') + ' ' + name + (s.note ? ' (' + s.note + ')' : '') + smoke);
  }
  console.log('  ' + summary);
  console.log('='.repeat(40));
}
process.exit(exitCode);
