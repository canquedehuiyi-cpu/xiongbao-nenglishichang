// proxylog.mjs — 读取 usage 记录代理（scripts/proxy.mjs）落盘的 jsonl，按 message.id 建索引。
//
// 背景：自定义模型（BYOK）不经 Qoder 计费网关，转录 assistant entry 的 message.usage 整个
// 字段缺失；但提供商响应里的 usage 真实存在，代理把它逐请求记在这里。join 键是 message.id
// （chatcmpl-*）：它由提供商生成、同时出现在转录与代理日志里，两端同源、天然精确对齐。
//
// 日志行格式（proxy.mjs 写入）：
//   { ts, id, model, path, stream, promptTokens, completionTokens, totalTokens, cachedTokens }
//
// 健壮性：本模块跑在 Stop 钩子链路里，任何读取/解析失败都返回空索引，绝不抛。

import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';

/** 代理日志默认路径（与 proxy.mjs 的 DEFAULTS.log 一致），可用环境变量改。 */
export function proxyLogPath(env = process.env) {
  return env.QODER_CREDITS_PROXY_LOG || path.join(os.homedir(), '.qoder-credits-proxy', 'usage.jsonl');
}

/**
 * 读取代理日志并建 id → 记录 索引。
 * @param {string} [logPath] 缺省用 proxyLogPath()
 * @returns {{map: Map<string, object>, records: number, logPath: string, exists: boolean}}
 *   records = 有效行总数；同 id 多行（重试）时后写的覆盖先写的。
 */
export function loadProxyUsage(logPath) {
  const file = logPath || proxyLogPath();
  const out = { map: new Map(), records: 0, logPath: file, exists: false };
  try {
    if (!fs.existsSync(file)) return out;
    out.exists = true;
    const text = fs.readFileSync(file, 'utf8');
    for (const line of text.split(/\r?\n/)) {
      if (!line) continue;
      let j;
      try {
        j = JSON.parse(line);
      } catch {
        continue; // 半截行（写入瞬间被读）直接跳过
      }
      if (!j || typeof j.id !== 'string' || !j.id) continue;
      if (j.promptTokens == null && j.completionTokens == null) continue;
      out.records++;
      out.map.set(j.id, j);
    }
  } catch {
    /* 读不了当没有：报告退回「无 usage」口径 */
  }
  return out;
}
