import fs from 'node:fs';
import { compute, findTranscript, fmtClock } from './engine.mjs';

function readStdin() {
  try {
    const raw = fs.readFileSync(0, 'utf8');
    return raw ? JSON.parse(raw) : {};
  } catch {
    return {};
  }
}

const input = readStdin();
if (input.stop_hook_active === true) process.exit(0);

try {
  const transcript = findTranscript({ transcript: input.transcript_path, session: input.session_id });
  if (!transcript) process.exit(0);
  const r = compute(transcript);
  const t = r.totals;
  let msg;
  if (t.roundTrips > 0) {
    // 本轮口径：Credits/耗时/峰值/次数取本轮，累计Credits为整场真值求和。
    const clock = fmtClock(t.turnDurationMs);
    const bits = [];
    if (t.turnRoundTrips > 0) {
      bits.push(`Credits: ${t.turnCredits}`);
      bits.push(`耗时: ${clock}`);
      bits.push(`上下文峰值: ${(t.turnPeakRatio * 100).toFixed(1)}%`);
      bits.push(`模型请求-响应次数: ${t.turnRoundTrips}`);
    }
    msg = `累计Credits: ${t.credits}｜${bits.length ? bits.join('｜') : (clock ? `耗时: ${clock}｜本轮无计费往返` : '本轮无计费往返')}`;
  } else {
    msg = `本场转录无计费数据（credits 不可用）｜计数：${t.userTurns} 轮对话 / ${t.toolCalls} 次工具调用`;
  }
  // CN 不渲染 systemMessage，用 block 让 agent 续一轮打印；异常恒 exit 0 绝不阻断。
  const reason = `原样输出下面这一行（不要解释、不要调用工具）：\n${msg}`;
  try { fs.writeSync(1, JSON.stringify({ decision: 'block', reason }) + '\n'); } catch {}
  try { fs.writeSync(2, reason + '\n'); } catch {}
  process.exit(2);
} catch {
  process.exit(0);
}