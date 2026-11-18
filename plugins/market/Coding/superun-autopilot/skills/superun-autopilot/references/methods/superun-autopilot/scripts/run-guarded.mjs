#!/usr/bin/env node
// 本专家团后续业务前核对已正常完成托管，不改变旧CLI命令。@author xiuyu.yi
import { spawn, execFile } from 'node:child_process';
import { promisify } from 'node:util';
import path from 'node:path';

const args = process.argv.slice(2);
function fail(message, details = {}) {
  process.stdout.write(JSON.stringify({ schemaVersion: '1', ok: false, error: { code: 'INVALID_ARGUMENT', message, ...details } }) + '\n');
  process.exitCode = 5;
}
try {
  if (args[0] !== '--session-id' || !args[1] || args[2] !== '--run-id' || !args[3] || args[4] !== '--')
    throw Error('请传入当前 session-id、run-id 和实际 CLI 执行参数');
  const [sessionId, runId] = [args[1], args[3]], command = args.slice(5);
  const chat = command.indexOf('chat');
  if (chat < 1 || chat > 6 || !path.isAbsolute(command[0])) throw Error('CLI 必须使用本次准备回执中的绝对路径');
  const prefix = command.slice(1, chat), business = command.slice(chat), delimiter = business.indexOf('--');
  if (delimiter < 2 || business[delimiter + 1] !== sessionId || business.filter(v => v === '--').length !== 1)
    throw Error('业务命令必须用 -- 固定同一项目为第一个位置参数');
  const allowed = new Set(['send', 'design', 'test', 'review', 'security', 'agent-friendly', 'wait', 'state', 'retry', 'stop', 'publish', 'interaction', 'plugin']);
  if (!allowed.has(business[1])) throw Error('当前业务不属于本包允许的继续创作动作');
  if (business[1] === 'publish' && !['status', 'start', 'deploy', 'visibility', 'prepare'].includes(business[2]))
    throw Error('不支持的发布动作');
  if (business[1] === 'interaction' && !['reply', 'skip'].includes(business[2]))
    throw Error('不支持的交互动作');
  if (business[1] === 'plugin' && !['list', 'status', 'enable', 'disable'].includes(business[2]))
    throw Error('不支持的插件动作');
  // 业务选项不能另行覆盖认证来源、服务地址或项目；检查和执行使用相同的根参数。
  if (business.slice(2, delimiter).some(v => /^--(?:endpoint|locale|name|session-id|run-id)(?:=|$)/.test(v)))
    throw Error('业务参数不能覆盖本次检查的根连接或项目');
  const checking = promisify(execFile)(command[0], [...prefix, 'chat', 'auto-mode', 'require-completed', '--run-id', runId, '--', sessionId],
    { encoding: 'utf8', maxBuffer: 8 * 1024 * 1024, timeout: 120000, windowsHide: true });
  // 登录链接和人工处理提示必须即时显示，不能等整个检查结束才展示。
  checking.child.stderr?.on('data', chunk => process.stderr.write(chunk));
  const result = await checking;
  const checked = JSON.parse(result.stdout);
  if (!checked.ok || checked.data?.sessionId !== sessionId || checked.data?.managed?.runId !== runId || checked.data?.managed?.completionVerified !== true)
    throw Error('收费或完成托管状态未确认，未执行后续业务');
  const child = spawn(command[0], command.slice(1), { stdio: 'inherit', shell: false, windowsHide: true });
  const listeners = ['SIGINT', 'SIGTERM'].map(signal => {
    const handler = () => child.kill(signal); process.on(signal, handler); return [signal, handler];
  });
  await new Promise((resolve, reject) => {
    child.once('error', reject);
    child.once('close', (code, signal) => { process.exitCode = code ?? (signal === 'SIGINT' ? 130 : 1); resolve(); });
  }).finally(() => { for (const [signal, handler] of listeners) process.off(signal, handler); });
} catch (error) {
  // 既有CLI已经脱敏的机器错误保持原样；不输出子进程环境、命令全文或未知原始日志。
  let value;
  try { value = JSON.parse(error.stdout); } catch {}
  if (value?.ok === false && value.error?.code) {
    process.stdout.write(JSON.stringify(value) + '\n'); process.exitCode = Number.isInteger(error.code) ? error.code : 5;
  } else fail(error instanceof Error && !('stdout' in error) && !('stderr' in error) ? error.message : '完成托管检查未成功，未执行后续业务');
}
