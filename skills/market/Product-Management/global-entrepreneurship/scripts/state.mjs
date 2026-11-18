#!/usr/bin/env node
/**
 * state.mjs — 项目状态管理（跨平台 Node.js，仅依赖 Node 内置模块，Node >= 18）
 *
 * 状态文件生成在「运行命令时所在的项目目录」下的 .project-state/ 中，
 * 不写入 Skill 安装目录，以保持 Skill 本体干净、并支持多项目各自独立。
 *
 * 用法:
 *   node scripts/state.mjs init
 *   node scripts/state.mjs status
 *   node scripts/state.mjs commit
 *   node scripts/state.mjs layer <1-15>
 *   node scripts/state.mjs goal <target> [actual]
 */
import { readFileSync, writeFileSync, existsSync, mkdirSync, appendFileSync } from 'node:fs';
import { resolve, dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const SKILL_VERSION = '1.0.5';

const STATE_DIR = join(process.cwd(), '.project-state');
const STATE_FILE = join(STATE_DIR, 'state.yaml');
const HISTORY_FILE = join(STATE_DIR, 'history.jsonl');

const LAYER_NAMES = [
  '用户深度画像', '实时市场扫描', '智能方向推荐', '需求验证设计',
  '全维度合规检查', '启动计划', '内容获客策略', '产品体系设计',
  '变现模型构建', '增长引擎设计', '风险管控体系', '自动监控仪表盘',
  '创新创意方案', '全球拓展规划', '长期发展蓝图'
];
const TOTAL_LAYERS = LAYER_NAMES.length;

function timestamp() {
  return new Date().toISOString().replace(/\.\d+Z$/, 'Z');
}

function appendHistory(entry) {
  appendFileSync(HISTORY_FILE, JSON.stringify(entry) + '\n', 'utf8');
}

function init() {
  if (!existsSync(STATE_DIR)) mkdirSync(STATE_DIR, { recursive: true });

  if (!existsSync(STATE_FILE)) {
    const yaml = [
      `version: "${SKILL_VERSION}"`,
      `last_updated: "${timestamp()}"`,
      'business:',
      '  name: ""',
      '  stage: "探索期"',
      '  monthly_revenue: 0',
      '  target_revenue: 0',
      '  currency: "CNY"',
      'layers_completed: []',
      'pending_actions: []',
      'decisions: []',
      'goals:',
      '  monthly_targets: []',
      '  actuals: []',
      ''
    ].join('\n');
    writeFileSync(STATE_FILE, yaml, 'utf8');
  }

  if (!existsSync(HISTORY_FILE)) {
    writeFileSync(HISTORY_FILE, '', 'utf8');
  }

  appendHistory({ action: 'init', skill_version: SKILL_VERSION, timestamp: timestamp() });
  console.log(`State initialized at ${STATE_DIR}`);
}

function readStateYaml() {
  if (!existsSync(STATE_FILE)) return null;
  return readFileSync(STATE_FILE, 'utf8');
}

function writeStateYaml(content) {
  writeFileSync(STATE_FILE, content, 'utf8');
}

function requireState() {
  if (!existsSync(STATE_DIR)) {
    console.error("No project state in current directory. Run 'state.mjs init' first");
    process.exit(1);
  }
  const content = readStateYaml();
  if (!content) {
    console.error("No state file found. Run 'state.mjs init' first");
    process.exit(1);
  }
  return content;
}

function updateTimestamp(content) {
  if (/last_updated: .*/m.test(content)) {
    return content.replace(/last_updated: .*/m, `last_updated: "${timestamp()}"`);
  }
  return content;
}

function getCompletedLayers(content) {
  const match = content.match(/layers_completed:\s*\n((?:  - \d+\n)*)/);
  if (!match) return [];
  return match[1].match(/\d+/g)?.map(Number) || [];
}

function status() {
  const content = requireState();

  console.log('=== Project State ===');
  console.log(content);

  const completed = getCompletedLayers(content);
  console.log('=== Layer Progress ===');
  console.log(`Completed: ${completed.length}/${TOTAL_LAYERS} layers`);
  completed.forEach(n => {
    console.log(`  ✓ Layer ${n}: ${LAYER_NAMES[n - 1] || '未知'}`);
  });

  console.log('');
  console.log('=== Goal Tracking ===');
  const hasGoal = /target_revenue:\s*[1-9]/.test(content);
  console.log(hasGoal ? 'See state.yaml for monthly targets vs actuals' : 'No goals set yet');
}

function commit() {
  let content = requireState();
  content = updateTimestamp(content);
  writeStateYaml(content);
  appendHistory({ action: 'commit', timestamp: timestamp() });
  console.log(`State committed at ${timestamp()}`);
}

function layer(num) {
  if (!Number.isInteger(num) || num < 1 || num > TOTAL_LAYERS) {
    console.error(`Usage: state.mjs layer <1-${TOTAL_LAYERS}>`);
    process.exit(1);
  }
  let content = requireState();

  const completed = getCompletedLayers(content);
  if (completed.includes(num)) {
    console.log(`Layer ${num} (${LAYER_NAMES[num - 1]}) already completed`);
    return;
  }

  // 追加(保留完成顺序): 在现有列表后追加 num 并重建 YAML 列表块
  const newList = completed.concat([num]);
  let block = 'layers_completed:';
  block += '\n' + newList.map(n => '  - ' + n + '\n').join('');

  if (content.includes('layers_completed: []')) {
    content = content.replace('layers_completed: []', block.trimEnd());
  } else {
    content = content.replace(/layers_completed:\s*\n(?:  - \d+\n)*/, block);
  }

  content = updateTimestamp(content);
  writeStateYaml(content);
  appendHistory({ action: 'layer_complete', layer: num, name: LAYER_NAMES[num - 1], timestamp: timestamp() });
  console.log(`Layer ${num} (${LAYER_NAMES[num - 1]}) marked as completed`);
}

function parseNonNegativeNumber(raw, label) {
  if (raw === undefined || raw === null || String(raw).trim() === '') {
    console.error(`Usage: state.mjs goal <target> [actual] — ${label} must be a non-negative number`);
    process.exit(1);
  }
  const value = Number(raw);
  if (!Number.isFinite(value) || value < 0) {
    console.error(`Invalid ${label}: "${raw}" — must be a non-negative number`);
    process.exit(1);
  }
  return value;
}

function goal(targetArg, actualArg = '0') {
  const target = parseNonNegativeNumber(targetArg, 'target');
  const actual = parseNonNegativeNumber(actualArg, 'actual');
  let content = requireState();

  content = content.replace(/target_revenue: .*/m, `target_revenue: ${target}`);
  content = content.replace(/monthly_revenue: .*/m, `monthly_revenue: ${actual}`);
  content = updateTimestamp(content);
  writeStateYaml(content);
  appendHistory({ action: 'goal_update', target, actual, timestamp: timestamp() });
  console.log(`Goal updated: target=${target}, actual=${actual}`);
}

// 主入口
const action = process.argv[2];
try {
  switch (action) {
    case 'init': init(); break;
    case 'status': status(); break;
    case 'commit': commit(); break;
    case 'layer': layer(parseInt(process.argv[3], 10)); break;
    case 'goal': goal(process.argv[3], process.argv[4]); break;
    default:
      console.log(`Usage: state.mjs {init|status|commit|layer <1-${TOTAL_LAYERS}>|goal <target> [actual]}`);
      process.exit(0);
  }
} catch (err) {
  console.error(`Error: ${err.message}`);
  process.exit(1);
}
