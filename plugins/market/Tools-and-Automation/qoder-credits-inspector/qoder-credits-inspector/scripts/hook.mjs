#!/usr/bin/env node
// hook.mjs — 钩子入口，按第一个参数分流两类事件：
//   on-session-start → 自动拉起 usage 记录代理（仅在已配置有效 upstream 且 enabled 时）
//   on-stop（默认）  → 读 stdin JSON → 重算报告 → 落盘（report.json + Canvas）
//
// 平台契约（docs.qoder.com/extensions/hooks）：
//   · stdin 收事件 JSON；exit 0 = 放行；exit 2 = 阻断；其他 = 非阻断错误。
//   · exit 0 时 stdout 会被当 JSON 解析——故本脚本【绝不向 stdout 打印】。
//   · Stop 钩子须防死循环：stop_hook_active=true 时立即放行。
// 两类事件都永不阻断，故恒 exit 0，异常一律吞掉写 stderr。

import fs from 'node:fs';
import { generateReport } from './lib/generate.mjs';
import { findTranscriptForSession, findLatestTranscript } from './lib/paths.mjs';
import { ensureProxy } from './proxy.mjs';

/** 同步读尽 stdin 并解析为对象；失败返回 {}（不抛）。 */
function readStdinJson() {
  try {
    const raw = fs.readFileSync(0, 'utf8');
    return raw ? JSON.parse(raw) : {};
  } catch {
    return {};
  }
}

/** 解析要读取的富转录路径：stdin → 环境变量 → 按会话定位 → 最近修改兜底。 */
function resolveTranscript(input) {
  const explicit = input.transcript_path || process.env.QODER_TRANSCRIPT_PATH;
  if (explicit && fs.existsSync(explicit)) return explicit;

  const sid = input.session_id || process.env.QODER_SESSION_ID;
  if (sid) {
    const found = findTranscriptForSession(sid);
    if (found) return found;
  }

  return findLatestTranscript();
}

function runStop() {
  const input = readStdinJson();

  // 防死循环：Stop 被阻断后的重试轮直接放行（本钩子不阻断，此为稳健性兜底）。
  if (input.stop_hook_active === true) return;

  const transcript = resolveTranscript(input);
  if (!transcript) return; // 无可用转录：静默放行

  const sessionId = input.session_id || process.env.QODER_SESSION_ID;
  const cwd = input.cwd || process.env.QODER_CWD;

  // 同步生成并原子落盘 report.json（当前会话）+ 每会话一个 <标题>__<id8>.canvas.tsx。
  generateReport({ transcript, sessionId, cwd, canvas: true });
}

const cmd = process.argv[2];

if (cmd === 'on-session-start') {
  // 自动拉起代理：ensureProxy 自带门槛（无有效配置直接返回），静默、幂等、绝不抛。
  // 顶层 await 让钩子进程等它就绪再退出（async:false，确保首个模型请求前代理已在监听）。
  try {
    await ensureProxy();
  } catch {
    /* 钩子不得阻断会话：吞掉一切异常 */
  }
} else {
  try {
    runStop();
  } catch (err) {
    // 非阻断：错误只写 stderr（exit 0 时被宿主忽略），绝不影响 Agent 停止。
    try {
      const msg = err && err.stack ? err.stack : String(err);
      process.stderr.write(`[credits-inspector] refresh failed: ${msg}\n`);
    } catch {
      /* 连 stderr 都写不了就算了 */
    }
  }
}
// 自然结束即 exit 0（放行）。
