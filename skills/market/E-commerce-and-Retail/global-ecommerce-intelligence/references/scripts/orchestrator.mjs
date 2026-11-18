#!/usr/bin/env node
/**
 * orchestrator.mjs — 工具链编排执行器 (v1.0.7)
 *
 * 统一入口: 先执行 env-check 环境门禁, 再按 --tool 运行目标工具,
 * 并把各阶段输出聚合成结构化报告。profit 未显式指定汇率时自动追加
 * --fx-live 获取实时汇率(方向已修正)。
 *
 * 用法:
 *   node references/scripts/orchestrator.mjs --tool profit -- --price 199 --cost 80 --json
 *   node references/scripts/orchestrator.mjs --tool tax -- --country DE --price 100 --shipping 15 --json
 *   node references/scripts/orchestrator.mjs --tool compliance -- --text "全网最低" --platform amazon --json
 *   node references/scripts/orchestrator.mjs --dry-run --tool profit -- --price 199 --cost 80 --json
 *   node references/scripts/orchestrator.mjs --list
 *   node references/scripts/orchestrator.mjs --version
 *
 * 参数:
 *   --tool      目标工具（见 --list 全量清单）
 *   --dry-run   只打印执行计划, 不实际运行
 *   --list      列出可编排工具
 *   --json      输出JSON
 *   --          其后参数原样透传给目标工具
 */

import { spawnSync } from 'node:child_process';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const VERSION = '1.0.7';
const __dirname = dirname(fileURLToPath(import.meta.url));
const args = process.argv.slice(2);
const wantJson = args.includes('--json');
const dryRun = args.includes('--dry-run');
const listMode = args.includes('--list');
if (args.includes('--version')) {
  process.stdout.write(VERSION + '\n');
  process.exit(0);
}
const KNOWN_FLAGS = new Set(['--tool', '--dry-run', '--list', '--json', '--version']);
const dashIdxForCheck = args.indexOf('--');
const preDashArgs = dashIdxForCheck === -1 ? args : args.slice(0, dashIdxForCheck);
const unknownFlags = preDashArgs.filter((a) => a.startsWith('--') && !KNOWN_FLAGS.has(a));
if (unknownFlags.length) {
  console.error('未知参数: ' + unknownFlags.join(' ') + '\n可用参数: --tool <工具> --dry-run --list --json (透传子工具参数请置于 -- 之后)');
  process.exit(1);
}
function getArg(name) {
  const i = args.indexOf('--' + name);
  return i >= 0 ? args[i + 1] : null;
}
const tool = (getArg('tool') || '').toLowerCase();
const dashIdx = args.indexOf('--');
const passthrough = dashIdx >= 0 ? args.slice(dashIdx + 1) : [];

const TOOLS = {
  profit: { file: 'profit_calculator.py', lang: 'py' },
  bsr: { file: 'bsr_analyzer.py', lang: 'py' },
  sentiment: { file: 'sentiment_analyzer.py', lang: 'py' },
  inventory: { file: 'inventory_calculator.py', lang: 'py' },
  tax: { file: 'tax_calculator.py', lang: 'py' },
  compliance: { file: 'compliance-scan.mjs', lang: 'node' },
  listing: { file: 'listing-scorer.mjs', lang: 'node' },
  'price-elasticity': { file: 'price-elasticity.mjs', lang: 'node' },
  'price-monitor': { file: 'price-monitor.mjs', lang: 'node' },
  'env-check': { file: 'env-check.mjs', lang: 'node' },
  'fetch-rates': { file: 'fetch-rates.mjs', lang: 'node' },
  router: { file: 'router.mjs', lang: 'node' },
  'knowledge-filter': { file: 'knowledge-filter.mjs', lang: 'node' },
  'sop-timeliness-check': { file: 'sop-timeliness-check.mjs', lang: 'node' },
  'competitor-checklist': { file: 'competitor-checklist.mjs', lang: 'node' },
  guidance: { file: 'guidance.mjs', lang: 'node' },
  'fact-check': { file: 'fact-check.mjs', lang: 'node' },
  'agent-readiness': { file: 'agent-readiness.mjs', lang: 'node' },
};

// 探测可用 Python 解释器（python 优先, 失败回退 python3）
function detectPython() {
  const probe = (p) => spawnSync(p, ['--version'], { encoding: 'utf-8', timeout: 15000 });
  return probe('python').status === 0 ? 'python' : 'python3';
}

function runScript(entry, extraArgs) {
  const file = join(__dirname, entry.file);
  const fullArgs = [...extraArgs];
  let cmd, allArgs;
  if (entry.lang === 'node') {
    cmd = process.execPath;
    allArgs = [file, ...fullArgs];
  } else {
    cmd = detectPython();
    allArgs = [file, ...fullArgs];
  }
  const res = spawnSync(cmd, allArgs, { encoding: 'utf-8', timeout: 120000 });
  return {
    cmd: cmd + ' ' + [entry.file, ...fullArgs].join(' '),
    status: res.status,
    stdout: (res.stdout || '').trim(),
    stderr: (res.stderr || '').trim(),
    error: res.error ? res.error.message : null,
  };
}

if (listMode) {
  const payload = {
    ok: true, tool: 'orchestrator', version: VERSION,
    schema: 'global-ecommerce-intelligence/orchestrator',
    generatedAt: new Date().toISOString(), mode: 'list',
    tools: Object.keys(TOOLS),
  };
  if (wantJson) process.stdout.write(JSON.stringify(payload, null, 2) + '\n');
  else {
    console.log('可编排工具: ' + Object.keys(TOOLS).join(', '));
    console.log('示例: node references/scripts/orchestrator.mjs --tool profit -- --price 199 --cost 80 --json');
  }
  process.exit(0);
}

if (!tool || !TOOLS[tool]) {
  console.error('用法: node references/scripts/orchestrator.mjs --tool <工具> -- [透传参数]');
  console.error('可用工具: ' + Object.keys(TOOLS).join(', '));
  process.exit(1);
}

const target = TOOLS[tool];
// profit 未显式给汇率时, 自动追加实时汇率
let effectiveArgs = [...passthrough];
if (tool === 'profit' && !effectiveArgs.includes('--fx-live') && !effectiveArgs.includes('--fx-rates')) {
  effectiveArgs.push('--fx-live');
}

const plan = {
  steps: [
    { name: 'env-check', cmd: join(__dirname, 'env-check.mjs') + ' --json' },
    { name: tool, cmd: (target.lang === 'node' ? process.execPath : detectPython()) + ' ' + join(__dirname, target.file) + ' ' + effectiveArgs.join(' ') },
  ],
};

if (dryRun) {
  const payload = {
    ok: true, tool: 'orchestrator', version: VERSION,
    schema: 'global-ecommerce-intelligence/orchestrator',
    generatedAt: new Date().toISOString(), mode: 'dry-run',
    target: tool, plan,
    note: 'dry-run: 未实际执行',
  };
  if (wantJson) process.stdout.write(JSON.stringify(payload, null, 2) + '\n');
  else console.log('执行计划:\n  ' + plan.steps.map((s) => s.name + ' → ' + s.cmd).join('\n  '));
  process.exit(0);
}

// Step 1: env-check 门禁
const env = runScript({ file: 'env-check.mjs', lang: 'node' }, ['--json']);
let envOk = false;
try {
  const parsed = JSON.parse(env.stdout);
  envOk = parsed.ok === true && parsed.exitCode === 0;
} catch { envOk = false; }
const envOutput = { status: env.status, stdout: env.stdout, stderr: env.stderr };

// Step 2: 目标工具
const out = runScript(target, effectiveArgs);
let toolJson = null;
try { toolJson = JSON.parse(out.stdout); } catch { toolJson = null; }

// compliance 命中违禁词时 exit 1 表示"发现违规"而非执行失败;
// fact-check 离线模式存在未核实项时 exit 2 表示"需 --online"而非执行失败
const toolSucceeded = tool === 'compliance' ? (out.status === 0 || out.status === 1)
  : tool === 'fact-check' ? (out.status === 0 || out.status === 2)
  : out.status === 0;
const ok = envOk && toolSucceeded;
const payload = {
  ok,
  tool: 'orchestrator',
  version: VERSION,
  schema: 'global-ecommerce-intelligence/orchestrator',
  generatedAt: new Date().toISOString(),
  mode: 'run',
  target: tool,
  envCheck: { passed: envOk, status: env.status, detail: envOutput.stderr || envOutput.stdout.slice(0, 500) },
  toolResult: {
    status: out.status,
    cmd: out.cmd,
    output: toolJson || out.stdout.slice(0, 2000),
    stderr: out.stderr || undefined,
    error: out.error || undefined,
  },
  advice: (tool === 'compliance' && out.status === 1) ? '合规扫描完成, 命中违规项, 请查看 toolResult 输出'
    : (tool === 'fact-check' && out.status === 2) ? '离线事实检查完成, 存在未核实项; 透传 --online 可在线核实'
    : (ok ? null : '编排失败: 请查看 envCheck/toolResult 定位原因'),
};

if (wantJson) {
  process.stdout.write(JSON.stringify(payload, null, 2) + '\n');
} else {
  console.log('编排执行: ' + tool + '  env-check=' + (envOk ? '通过' : '失败') + '  工具exit=' + out.status);
  console.log('='.repeat(50));
  if (envOutput.stderr) console.log('env: ' + envOutput.stderr.slice(0, 300));
  console.log(out.stdout.slice(0, 1200));
  console.log('='.repeat(50));
}
process.exit(ok ? 0 : 1);
