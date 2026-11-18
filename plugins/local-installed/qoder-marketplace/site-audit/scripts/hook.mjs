#!/usr/bin/env node
/**
 * UserPromptSubmit hook：把上一轮 outstanding 的 not-run 项顶到用户面前。
 *
 * 这是「无声放弃」的唯一结构性对策——检查项没跑不能靠人记得，必须在每次提问时提醒。
 * 默认不动作：只有使用者显式设了 SITE_AUDIT_OUT 才输出，避免在无关会话里插话，
 * 也避免把目标 URL 或本机路径带进上下文（这里只输出检查 ID 与计数）。
 */

import { existsSync } from 'node:fs';
import { resolve, dirname, join } from 'node:path';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';

const out = process.env.SITE_AUDIT_OUT;
if (!out || !existsSync(resolve(out))) process.exit(0);

// 必须用 fileURLToPath：在 Linux 上 url.pathname 去掉前导斜杠会变成相对路径，
// 提醒机制随之静默失效。Windows 只是碰巧能用。
const ledger = join(dirname(fileURLToPath(import.meta.url)), 'ledger.mjs');
if (!existsSync(ledger)) process.exit(0);
const r = spawnSync(process.execPath, [ledger, 'outstanding', '--out', resolve(out)], {
  encoding: 'utf8',
  timeout: 8000,
});
const text = String(r.stdout || '');
// 只放行「ID + 计数」这一类信息；任何像 URL/绝对路径的行一律丢弃
const safe = text
  .split(/\r?\n/)
  .filter((l) => l.trim())
  .filter((l) => !/https?:\/\//i.test(l) && !/(^|[^\w])([A-Za-z]:[\\/]|\/Users\/|\/home\/)/.test(l));
if (safe.length) process.stdout.write(safe.join('\n') + '\n');
process.exit(0);
