#!/usr/bin/env node
import fs from 'node:fs/promises';
import path from 'node:path';
import os from 'node:os';
import { createHash } from 'node:crypto';
const host = JSON.parse(await fs.readFile(new URL('./mode-gate.config.json', import.meta.url), 'utf8'));


const question = '你希望使用哪种方式继续开发？';
const labels = { 'superun-ai': '云端生成（superun-ai）', 'sxq-cli': '本地开发（sxq-cli）' };
const reminder = `superun 已返回待开发功能清单。先在正文展示真实清单，再调用 AskUserQuestion 单独询问“${question}”，两个选项为“${labels['superun-ai']}”（消耗 superun 生成 token）和“${labels['sxq-cli']}”（不消耗 superun 生成 token，客户端模型与云资源费用另计）。收到真实答案后才继续；默认 superun-ai 不算已选择。`;

function context(event, text) {
  console.log(JSON.stringify({ hookSpecificOutput: { hookEventName: event, additionalContext: text } }));
}
function deny(text) { process.stderr.write(text + '\n'); process.exitCode = 2; }
async function read(file) {
  try { return await fs.readFile(file, 'utf8'); }
  catch (e) { if (e.code === 'ENOENT') return ''; throw e; }
}
async function write(file, value) {
  await fs.mkdir(path.dirname(file), { recursive: true, mode: 0o700 });
  const temp = `${file}.${process.pid}.tmp`;
  await fs.writeFile(temp, value, { mode: 0o600 });
  await fs.rename(temp, file);
}

// Read 支持带行号的文本，Bash 支持直接返回 NDJSON。
// 只有包含真实功能选择交互的结构化 superun 回执，才会建立模式检查。
function envelopes(value, depth = 0) {
  if (depth > 8 || value == null) return [];
  if (typeof value === 'string') {
    try { return envelopes(JSON.parse(value), depth + 1); } catch {}
    return value.split('\n').flatMap(line => {
      try { return envelopes(JSON.parse(line.replace(/^\s*\d+[\t→]\s*/, '')), depth + 1); }
      catch { return []; }
    });
  }
  if (Array.isArray(value)) return value.flatMap(item => envelopes(item, depth + 1));
  if (typeof value !== 'object') return [];
  if (String(value.schemaVersion) === '1' && value.ok === true && value.data?.sessionId &&
      value.data.interactions?.some(item => ['SELECT_FEATURES', 'FEATURE_SELECTION'].includes(item.kind))) return [value.data];
  return ['content', 'text', 'stdout', 'output', 'data', 'file', 'result'].flatMap(key => envelopes(value[key], depth + 1));
}

function modeQuestion(input) {
  const questions = input?.questions;
  if (!Array.isArray(questions) || questions.length !== 1 || questions[0].multiSelect !== false) return false;
  const options = questions[0].options;
  return options?.length === 2 && Object.values(labels).every(label => options.some(o => o.label === label));
}
function answeredMode(response, asked) {
  if (!response || response.is_error || response.isError) return null;
  if (typeof response === 'object') {
    const answer = response.answers?.[asked];
    for (const [mode, label] of Object.entries(labels)) if (answer === label) return mode;
    for (const key of ['content', 'text', 'output']) {
      const values = Array.isArray(response[key]) ? response[key] : [response[key]];
      for (const value of values) { const mode = answeredMode(value, asked); if (mode) return mode; }
    }
    return null;
  }
  if (typeof response !== 'string') return null;
  // Actual Qoder answer format, not an occurrence in an echoed question/options.
  for (const [mode, label] of Object.entries(labels)) {
    if (response.includes(`${JSON.stringify(asked)}=${JSON.stringify(label)}`)) return mode;
  }
  return null;
}

async function memoryMode(root) {
  const dir = host.ruleDirectory ? path.join(root, host.ruleDirectory) : null;
  let entries = [];
  try { if (dir) entries = await fs.readdir(dir, { withFileTypes: true }); }
  catch (e) { if (e.code !== 'ENOENT') throw e; }
  const modes = new Set();
  const files = entries.filter(entry => entry.isFile() && entry.name.endsWith('.md')).map(entry => path.join(dir, entry.name));
  files.push(...host.memoryFiles.map(file => path.join(root, file))); 
  for (const file of files) {
    const text = (await read(file)).replace(/[*`]/g, '');
    for (const m of text.matchAll(/^\s*(?:-\s*)?[sS]uperun 执行模式[：:]\s*(superun-ai|sxq-cli)(?=[（\s;；]|$)/gm)) modes.add(m[1]);
  }
  if (modes.size > 1) throw Error('项目记忆存在冲突的 superun 执行模式，请先核对作用域');
  return [...modes][0] ?? null;
}

async function main(input) {
  const event = input.hook_event_name;
  if (!['PreToolUse', 'PostToolUse'].includes(event) || !input.cwd || !input.session_id) return;
  const root = await fs.realpath(input.cwd);
  const key = createHash('sha256').update(root + '\0' + input.session_id).digest('hex');
  // This is recoverable hook bookkeeping, never the project's mode preference.
  const stateFile = path.join(process.env[host.dataVariable] || path.join(os.tmpdir(), host.stateNamespace), 'mode-gate', key + '.json');
  const raw = await read(stateFile);
  let state = raw ? JSON.parse(raw) : null;
  const tool = input.tool_name;
  const args = input.tool_input || {};
  if (event === 'PostToolUse' && ['Read', 'Bash'].includes(tool)) {
    const results = envelopes(input.tool_response);
    if (results.length) {
      const result = results.at(-1);
      if (state?.project !== result.sessionId) state = { project: result.sessionId };
      await write(stateFile, JSON.stringify(state));
      const mode = await memoryMode(root);
      context(event, mode ? `当前项目已明确选择 ${mode}，沿用项目记忆。${mode === 'sxq-cli' ? '不提交云端功能选择，继续 link → pull → dev → 展示本地预览。' : '可以继续收集功能选择。'}` : reminder);
    }
  }
  if (!state) return;
  if (event === 'PostToolUse' && tool === 'AskUserQuestion' && modeQuestion(args)) {
    const mode = answeredMode(input.tool_response, args.questions[0].question);
    if (!mode) return; // cancellation, timeout and preselection never persist a mode
    // The composition entry owns memory edits, preserving arbitrary user rules.
    state.answer = mode;
    await write(stateFile, JSON.stringify(state));
    context(event, `用户真实选择了 ${mode}。仅更新${host.memoryLabel}的“superun 执行模式”条目并回读，保存“样式选择后已介绍执行模式”；不要保存到全局。${mode === 'sxq-cli' ? '继续关联、拉取、启动本地 dev 并展示预览；不提交云端功能答案。' : '保存后继续收集功能选择。'}`);
  }
  if (event !== 'PreToolUse') return;
  const saved = await memoryMode(root);
  if (state.answer && saved === state.answer) {
    delete state.answer;
    await write(stateFile, JSON.stringify(state));
  }
  const mode = state.answer || saved;
  const pendingQuestion = (!mode || (state.answer && saved !== state.answer)) &&
    tool === 'AskUserQuestion' && !modeQuestion(args);
  const featureQuestion = tool === 'AskUserQuestion' && !modeQuestion(args) &&
    args.questions?.some(q => /功能|勾选|全选|研发|feature/i.test(`${q.header || ''} ${q.question || ''}`));
  const command = args.command || '';
  const cloudWrite = tool === 'Bash' && /superun-ai|run-cli\.mjs/.test(command) &&
    command.includes(state.project) && /\bchat\s+(?:interaction\s+reply|send|style\s+select)\b/.test(command);
  if (!pendingQuestion && !featureQuestion && !cloudWrite) return;
  if (!mode) return deny(reminder + '本次功能选择/研发调用未执行。');
  if (mode === 'sxq-cli') return deny('当前项目已选择 sxq-cli，本次云端功能选择/研发调用未执行。使用 sxq-cli Skill 继续 link → pull → 本地 dev → 展示预览。用户要切回云端时先完成明确模式切换。');
  if (state.answer && saved !== state.answer) return deny('用户已选择云端生成，请先将真实选择写入当前项目原生记忆并回读，再继续功能选择；无需重复询问模式。');
}

let input;
try {
  let text = '';
  for await (const chunk of process.stdin) text += chunk;
  input = JSON.parse(text);
  await main(input);
} catch (error) {
  const message = `superun 模式检查失败：${error.message}。请读取组合入口和项目记忆，核对真实选择后重试；不要把检查失败当作默认云端授权。`;
  if (input?.hook_event_name === 'PreToolUse') deny(message);
  else if (input?.hook_event_name === 'PostToolUse') context('PostToolUse', message);
  else { process.stderr.write(message + '\n'); process.exitCode = 1; }
}
