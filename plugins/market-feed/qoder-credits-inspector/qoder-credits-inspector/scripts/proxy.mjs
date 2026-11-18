#!/usr/bin/env node
// proxy.mjs — 本地 usage 记录代理：OpenAI 兼容端点的透明转发 + 逐请求 token 落盘。
//
// 为什么需要它：自定义模型（BYOK，如千问 tokenplan）不经 Qoder 计费网关，转录里
// message.usage 整个字段缺失（见根因文档第十一节），插件端无米下锅。但提供商响应里
// 的 usage（prompt_tokens/completion_tokens）真实存在，只是客户端不落盘——本代理在
// 中间把它记下来，插件再按 message.id（chatcmpl-*，两端同源）精确 join。
//
// 用法：
//   node scripts/cli.mjs --setup-proxy --upstream <真实供应商根地址>   # 一键写配置 + 后台拉起（推荐）
//   node scripts/cli.mjs --check-proxy     # 链路自检
//   node scripts/cli.mjs --stop-proxy      # 停用（停进程 + 置 enabled:false，改回官方模型时用）
//   node scripts/proxy.mjs                 # 前台运行（排查用；需已配好 upstream）
//
// 配置（优先级：环境变量 > ~/.qoder-credits-proxy/config.json > 默认值）：
//   QODER_CREDITS_PROXY_PORT      监听端口，默认 49787（--setup-proxy 会自动挑一个空闲端口并写回配置）
//   QODER_CREDITS_PROXY_UPSTREAM  上游根地址，**无默认**：必须显式配置，否则代理拒绝启动
//   QODER_CREDITS_PROXY_LOG       usage 日志文件，默认 ~/.qoder-credits-proxy/usage.jsonl
//   QODER_CREDITS_PROXY_REQUEST_LOG  请求诊断日志，默认 ~/.qoder-credits-proxy/requests.jsonl
//                                 （每请求一行元数据：状态/耗时/编码/中断原因——排查「代理 vs 供应商 vs 客户端」）
//   QODER_CREDITS_PROXY_ENABLED   'false'/'0' 停用（等价 config.json 里 enabled:false）
//
// 「upstream 有效」是自动拉起的总门槛：只有 config.json 里 upstream 是合法 http(s) 地址
// 且 enabled 不为 false 时，SessionStart 钩子才会拉起代理。纯官方模型用户没有这个配置，
// 无感、不会平白多个常驻进程。占位符 / 空串 / 中文都不匹配 ^https?://，天然安全。
//
// 路径完全透明：转发目标 = upstream + 原始 path + query。
// 用户把 Qoder 自定义模型的 Base URL 的 host:port 换成 127.0.0.1:<port>，路径原样保留：
//   真实 https://token-plan.cn-beijing.maas.aliyuncs.com/compatible-mode/v1
//   → Qoder 里填 http://127.0.0.1:<port>/v1，config.upstream = …/compatible-mode
//   /v1/chat/completions 转发后拼回 …/compatible-mode/v1/chat/completions。
// 即 upstream = 「真实 Base URL 去掉你在 Qoder 里保留的那段路径（通常 /v1）」。
//
// 流式处理：请求注入 stream_options.include_usage=true；逐行解析 SSE，
// **仅当客户端自己没要求 include_usage 时**，才把末尾那个 choices 为空、只带 usage 的 chunk
// 记录后吞掉（客户端无感知）；客户端原本就要的 usage 必须原样下发——那是它算上下文占比、
// 判断何时自动压缩的唯一输入，吞掉等于让压缩判据永远瞎着。其余字节原样转发。
// 流式还是整包缓冲，按**客户端有没有要流式**（请求体 stream:true）判，与代理有没有注入 usage 无关；
// 流式逐行透传保持实时下发，非流式则缓冲响应体解析 usage 后原样回传。
//
// 红线：只做旁路记录，绝不改语义——请求/响应除上述注入与吞 chunk 外逐字节透传；
// API key 只在 Authorization 头里过路，不落日志。usage 日志只存 token 计数，
// 请求诊断日志只存元数据（状态/耗时/字节数/编码/中断原因），两者都不含任何请求或响应内容。
// 唯一的头部改写是 content-encoding：
// fetch(undici) 已把响应体解压成明文，头若照转就是「明文 body + gzip 头」，客户端解压必炸，
// 故仅在确认 undici 解过压时剥掉（未知编码 undici 原样透传，那时头必须留着）。

import http from 'node:http';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import zlib from 'node:zlib';
import { spawn } from 'node:child_process';
import { pathToFileURL, fileURLToPath } from 'node:url';

const CONFIG_DIR = path.join(os.homedir(), '.qoder-credits-proxy');
export const CONFIG_FILE = path.join(CONFIG_DIR, 'config.json');
export const STATUS_FILE = path.join(CONFIG_DIR, 'status.json');
const DEFAULTS = {
  // 端口默认落在动态段、避开常见服务（8787 是 Cloudflare Wrangler 默认 dev 端口，易撞）。
  // --setup-proxy 会从这个值起自动挑一个空闲端口并写回 config.json，故实际端口以配置为准。
  port: 49787,
  // 无默认上游：必须显式配置，否则 startProxy 拒绝监听（避免静默转发到错误供应商）。
  upstream: '',
  log: path.join(CONFIG_DIR, 'usage.jsonl'),
  // 请求级诊断日志：每请求一行元数据（状态/耗时/编码/中断原因），用来分清「代理错 vs 供应商错 vs 客户端错」
  reqLog: path.join(CONFIG_DIR, 'requests.jsonl'),
  enabled: true,
  // 用户压缩阈值（可选）：Qoder「模型管理 · 上下文窗口」里你设的上限（如 200000）。
  // 报表用它算「当前占用 / 该不该压」，并识别 BYOK 下「设了 200K 但自动压缩实际按模型窗口 1M 的 ~85% 才触发」。
  // 留空(null) → 报表回退内置默认 200K、来源标 'default'；填了 → 来源标 'config'。
  userContextLimit: null,
};

/** upstream 是否为可转发的合法地址：只有 http(s) 才算数。空串/占位符/中文一律 false。 */
export function isValidUpstream(u) {
  return typeof u === 'string' && /^https?:\/\/[^\s]+$/i.test(u.trim());
}

/** 直接读 config.json 原始对象；不存在/坏档返回 null（不抛）。用于判断「用户是否已配置」。 */
export function readConfigRaw() {
  try {
    const j = JSON.parse(fs.readFileSync(CONFIG_FILE, 'utf8').replace(/^\uFEFF/, ''));
    return j && typeof j === 'object' ? j : null;
  } catch {
    return null;
  }
}

/** 合并写 config.json（保留已有字段，浅合并 patch），原子落盘。返回最终对象。 */
export function writeConfig(patch = {}) {
  const cur = readConfigRaw() || {};
  const next = { ...cur, ...patch };
  fs.mkdirSync(CONFIG_DIR, { recursive: true });
  const tmp = `${CONFIG_FILE}.tmp`;
  fs.writeFileSync(tmp, JSON.stringify(next, null, 2) + '\n', 'utf8');
  try {
    fs.rmSync(CONFIG_FILE, { force: true });
  } catch {
    /* 目标不存在 */
  }
  fs.renameSync(tmp, CONFIG_FILE);
  return next;
}

/** 首次生成 config.json 模板（已存在则不动，幂等）。upstream 留空 → 门槛不满足 → 不启动代理，
 *  纯官方模型用户无感。_说明 字段仅供人读，loadConfig 忽略未知键。返回是否新建。 */
export function ensureConfigTemplate() {
  if (readConfigRaw()) return false;
  writeConfig({
    _说明: '自定义模型（BYOK）token 统计代理配置。把 upstream 填成你的真实供应商根地址（= Qoder 里那个 Base URL 去掉你保留的 /v1 路径），保存后新开一个会话即自动生效；用官方模型则无需理会本文件。',
    _示例: 'https://dashscope.aliyuncs.com/compatible-mode  或  https://token-plan.cn-beijing.maas.aliyuncs.com/compatible-mode',
    _上下文阈值: '可选 userContextLimit（整数）：填你在 Qoder「模型管理·上下文窗口」设的上限（如 200000），报表据此算「当前占用/该不该压」；不填则用内置默认 200000。',
    upstream: '',
    enabled: true,
  });
  return true;
}

/** 从 preferred 起向上找一个可监听的空闲端口；找不到返回 preferred（交给 startProxy 报错）。 */
export async function pickFreePort(preferred, host = '127.0.0.1', tries = 40) {
  for (let i = 0; i < tries; i++) {
    const port = preferred + i;
    if (port > 65535) break;
    const free = await new Promise((resolve) => {
      const srv = http.createServer();
      srv.once('error', () => resolve(false));
      srv.once('listening', () => srv.close(() => resolve(true)));
      srv.listen(port, host);
    });
    if (free) return port;
  }
  return preferred;
}

/** 读代理健康端点；无响应/超时返回 null。 */
export async function proxyHealth(cfg, timeoutMs = 1500) {
  try {
    const ctl = new AbortController();
    const timer = setTimeout(() => ctl.abort(), timeoutMs);
    const r = await fetch(`http://127.0.0.1:${cfg.port}/__proxy_health`, { signal: ctl.signal });
    clearTimeout(timer);
    return r.ok ? await r.json() : null;
  } catch {
    return null;
  }
}

/** 写 status.json（最近一次拉起结果），供报告端提示「代理未起来/端口被占」。绝不抛。 */
export function writeStatus(obj) {
  try {
    fs.mkdirSync(CONFIG_DIR, { recursive: true });
    fs.writeFileSync(STATUS_FILE, JSON.stringify({ ...obj, at: new Date().toISOString() }, null, 2), 'utf8');
  } catch {
    /* 状态文件只是便利 */
  }
}

export function readStatus() {
  try {
    return JSON.parse(fs.readFileSync(STATUS_FILE, 'utf8'));
  } catch {
    return null;
  }
}

/** 后台拉起代理子进程（detached + unref）。execPath 缺省用 process.execPath——
 *  经 .cmd 走 Qoder 内置 Electron 时它就是 Qoder CN.exe（ELECTRON_RUN_AS_NODE 由 env 继承），
 *  故连一次性命令都不需要用户自装 node。返回 child。 */
export function spawnProxy(cfg) {
  const script = fileURLToPath(import.meta.url);
  const child = spawn(process.execPath, [script], {
    detached: true,
    stdio: ['ignore', 'ignore', 'ignore'],
    env: process.env,
    windowsHide: true,
  });
  child.unref();
  return child;
}

/** 轮询健康端点直到就绪或超时；返回 health 或 null。 */
export async function waitForHealth(cfg, { tries = 15, delay = 200 } = {}) {
  for (let i = 0; i < tries; i++) {
    const h = await proxyHealth(cfg, 800);
    if (h) return h;
    await new Promise((r) => setTimeout(r, delay));
  }
  return null;
}

/**
 * SessionStart 钩子的自动拉起逻辑（静默、幂等、绝不抛、绝不写 stdout）。
 * 门槛：config.json 存在 且 upstream 合法 且 enabled != false。否则直接返回（官方用户无感）。
 * @returns {Promise<{started:boolean, reason:string, health:object|null}>}
 */
export async function ensureProxy() {
  const raw = readConfigRaw();
  if (!raw) {
    ensureConfigTemplate(); // 首次生成模板，方便用户发现并填写
    return { started: false, reason: 'no-config', health: null };
  }
  const cfg = loadConfig();
  if (cfg.enabled === false) return { started: false, reason: 'disabled', health: null };
  if (!isValidUpstream(cfg.upstream)) return { started: false, reason: 'no-upstream', health: null };
  const running = await proxyHealth(cfg, 800);
  if (running) return { started: false, reason: 'already-running', health: running };
  try {
    spawnProxy(cfg);
  } catch (err) {
    writeStatus({ ok: false, error: `spawn-failed: ${err.message}`, port: cfg.port });
    return { started: false, reason: 'spawn-failed', health: null };
  }
  const health = await waitForHealth(cfg, { tries: 12, delay: 200 });
  if (health) {
    writeStatus({ ok: true, pid: health.pid, port: cfg.port, upstream: cfg.upstream, by: 'session-start' });
    try {
      fs.writeFileSync(path.join(CONFIG_DIR, 'proxy.pid'), String(health.pid), 'utf8');
    } catch {
      /* 便利文件 */
    }
    return { started: true, reason: 'started', health };
  }
  writeStatus({ ok: false, error: 'health-timeout', port: cfg.port, upstream: cfg.upstream });
  return { started: false, reason: 'health-timeout', health: null };
}

/** 停用代理：杀掉监听进程（按健康端点回报的 pid），并置 config.enabled=false。返回是否停了进程。 */
export async function stopProxy() {
  const cfg = loadConfig();
  const health = await proxyHealth(cfg, 800);
  let killed = false;
  if (health && health.pid) {
    try {
      process.kill(health.pid);
      killed = true;
    } catch {
      /* 进程已不在 */
    }
  }
  if (readConfigRaw()) writeConfig({ enabled: false });
  writeStatus({ ok: false, stopped: true, port: cfg.port });
  return killed;
}

export function loadConfig(env = process.env) {
  const cfg = { ...DEFAULTS };
  try {
    const file = JSON.parse(fs.readFileSync(CONFIG_FILE, 'utf8').replace(/^\uFEFF/, ''));
    if (Number.isFinite(file.port)) cfg.port = file.port;
    if (typeof file.upstream === 'string' && file.upstream) cfg.upstream = file.upstream;
    if (typeof file.log === 'string' && file.log) cfg.log = file.log;
    if (typeof file.reqLog === 'string' && file.reqLog) cfg.reqLog = file.reqLog;
    if (typeof file.enabled === 'boolean') cfg.enabled = file.enabled;
    if (Number.isFinite(file.userContextLimit) && file.userContextLimit > 0) cfg.userContextLimit = Math.round(file.userContextLimit);
  } catch {
    /* 无配置文件：用默认值 */
  }
  if (env.QODER_CREDITS_PROXY_PORT) cfg.port = parseInt(env.QODER_CREDITS_PROXY_PORT, 10) || cfg.port;
  if (env.QODER_CREDITS_PROXY_UPSTREAM) cfg.upstream = env.QODER_CREDITS_PROXY_UPSTREAM;
  if (env.QODER_CREDITS_PROXY_LOG) cfg.log = env.QODER_CREDITS_PROXY_LOG;
  if (env.QODER_CREDITS_PROXY_REQUEST_LOG) cfg.reqLog = env.QODER_CREDITS_PROXY_REQUEST_LOG;
  if (env.QODER_CREDITS_PROXY_ENABLED) cfg.enabled = !/^(false|0|no)$/i.test(env.QODER_CREDITS_PROXY_ENABLED);
  if (env.QODER_CREDITS_USER_CONTEXT_LIMIT) {
    const v = parseInt(env.QODER_CREDITS_USER_CONTEXT_LIMIT, 10);
    if (Number.isFinite(v) && v > 0) cfg.userContextLimit = v;
  }
  cfg.upstream = String(cfg.upstream || '').replace(/\/+$/, '');
  return cfg;
}

function readBody(req) {
  return new Promise((resolve, reject) => {
    const chunks = [];
    req.on('data', (c) => chunks.push(c));
    req.on('end', () => resolve(Buffer.concat(chunks)));
    req.on('error', reject);
  });
}

function appendLog(cfg, record) {
  try {
    fs.mkdirSync(path.dirname(cfg.log), { recursive: true });
    fs.appendFileSync(cfg.log, JSON.stringify(record) + '\n', 'utf8');
  } catch (err) {
    console.error(`[proxy] 日志写入失败：${err.message}`);
  }
}

/** 「下一步请跑这条」的自定位写法：绝不让调用方去猜 <plugin_root>。
 *  Windows 上优先用插件自带的 bin/credits-inspector.cmd（内含 Qoder 运行时探测，免装 Node）；
 *  没有启动器时退回绝对路径的 node 调用。 */
export function selfCmd() {
  const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
  const launcher = path.join(root, 'bin', 'credits-inspector.cmd');
  if (process.platform === 'win32' && fs.existsSync(launcher)) return `"${launcher}" cli`;
  return `node "${path.join(root, 'scripts', 'cli.mjs')}"`;
}

const REQ_LOG_MAX_BYTES = 8 * 1024 * 1024;
let reqLogWrites = 0;

/** 请求级诊断日志：**只记元数据**——方法/路径/状态/耗时/字节数/SSE 编码/中断原因，
 *  绝不写请求或响应内容，也绝不写任何鉴权头（Authorization 只在过路时存在）。
 *  写失败一律吞掉：诊断日志是便利设施，不能拖累转发主链路。 */
export function appendRequestLog(cfg, rec) {
  try {
    fs.mkdirSync(path.dirname(cfg.reqLog), { recursive: true });
    if (++reqLogWrites % 50 === 0) {
      try {
        if (fs.statSync(cfg.reqLog).size > REQ_LOG_MAX_BYTES) {
          fs.renameSync(cfg.reqLog, `${cfg.reqLog}.1`); // 只留一份归档，上限 ~16MB
        }
      } catch {
        /* 文件还不存在 */
      }
    }
    fs.appendFileSync(cfg.reqLog, JSON.stringify(rec) + '\n', 'utf8');
  } catch {
    /* 忽略 */
  }
}

/** 读最近 n 条请求诊断记录（文件缺失/坏行一律安全返回）。 */
export function readRequestLog(cfg, n = 30) {
  let lines;
  try {
    lines = fs.readFileSync(cfg.reqLog, 'utf8').split(/\r?\n/).filter(Boolean);
  } catch {
    return [];
  }
  const out = [];
  for (const l of lines.slice(-n)) {
    try {
      out.push(JSON.parse(l));
    } catch {
      /* 跳过损坏行 */
    }
  }
  return out;
}

/** readRequestLog 的有界版：只读文件末尾 maxBytes。
 *  诊断日志滚动上限 8MB，而报告生成跑在 Stop 钩子链路里，每轮整读一遍不划算。
 *  落在行中间的截断由 JSON.parse 失败自然跳过，不需要额外判断。 */
export function readRequestLogTail(cfg, maxBytes = 512 * 1024, n = 400) {
  let text;
  try {
    const size = fs.statSync(cfg.reqLog).size;
    const len = Math.min(size, maxBytes);
    const buf = Buffer.alloc(len);
    const fd = fs.openSync(cfg.reqLog, 'r');
    try {
      fs.readSync(fd, buf, 0, len, size - len);
    } finally {
      fs.closeSync(fd);
    }
    text = buf.toString('utf8');
  } catch {
    return [];
  }
  const out = [];
  for (const l of text.split(/\r?\n/).filter(Boolean).slice(-n)) {
    try {
      const j = JSON.parse(l);
      // 只收对象：这个文件由代理进程并发追加，末尾可能读到截半的行，
      // 而截半后仍可能解析成标量，下游取字段就会抛。
      if (j && typeof j === 'object') out.push(j);
    } catch {
      /* 截半的首行 */
    }
  }
  return out;
}

/** 断开前上游静默超过这个毫秒数，才算「上游卡住把客户端拖到放弃」；否则是客户端自己取消。 */
export const STALL_MS = 15000;

/** 汇总请求诊断记录，给出「代理 / 上游 / 客户端」三方可归因的计数。纯函数，便于测试。
 *  归因靠 err 标记而非状态码：上游自己返回 502 时代理只是转达，不能算代理失败。 */
export function summarizeRequests(recs) {
  const s = {
    n: recs.length, ok: 0, upstreamRejected: 0, proxyError: 0, clientAbort: 0, clientAbortMaxMs: 0,
    aborted: 0, interrupted: 0, truncated: 0, truncatedStalled: 0, unknownInterrupt: 0, noUsage: 0, slowest: null,
  };
  for (const r of recs) {
    const errStr = typeof r.err === 'string' ? r.err : '';
    // "This operation was aborted" 只可能来自 ctl.abort()，而 ctl 仅由 res 'close' 触发
    // = 客户端在响应走完前就关了连接（首字节前的客户端超时、或用户手动停 / 换模型）。
    // 这不是代理故障：旧版把它并进 proxyError，会把「客户端等不及」误报成「代理挂了」，把排查带偏。
    const clientGaveUp = /aborted/i.test(errStr);
    const own = /^(upstream unreachable|handler threw)/.test(errStr) && !clientGaveUp;
    if (/^upstream unreachable/.test(errStr) && clientGaveUp) {
      s.clientAbort++; // 连首字节都没拿到就被客户端断开
      if (typeof r.ms === 'number' && r.ms > s.clientAbortMaxMs) s.clientAbortMaxMs = r.ms;
    } else if (own) s.proxyError++;
    else if (r.status && r.status >= 400) s.upstreamRejected++;
    else s.ok++;
    if (r.aborted) s.aborted++;
    if (r.interrupted) s.interrupted++;
    if (r.truncated) s.truncated++;
    if (r.truncated && typeof r.idleMs === 'number' && r.idleMs >= STALL_MS) s.truncatedStalled++;
    if (r.interrupted && typeof r.doneSeen !== 'boolean') s.unknownInterrupt++;
    if (r.status === 200 && r.path?.includes('chat/completions') && !r.usageSeen) s.noUsage++;
    if (typeof r.ms === 'number' && (!s.slowest || r.ms > s.slowest.ms)) {
      s.slowest = { ms: r.ms, path: r.path, status: r.status, model: r.model };
    }
  }
  return s;
}

function newDiag(req, url) {
  return {
    ts: new Date().toISOString(),
    method: req.method,
    path: url.pathname,
    t0: Date.now(),
    reqBytes: 0,
    status: null,
    stream: null,
    wantUsage: false,
    injected: false,
    swallowed: 0,
    usageSeen: false,
    doneSeen: false,
    truncated: false,
    model: null,
    id: null,
    lines: 0,
    fwdBytes: 0,
  };
}

/** 从 OpenAI 风格 usage 对象抽取整型字段（缺失记 null，不冒充 0）。 */
function pickUsage(u) {
  if (!u || typeof u !== 'object') return null;
  const n = (v) => (Number.isFinite(v) ? v : null);
  return {
    promptTokens: n(u.prompt_tokens),
    completionTokens: n(u.completion_tokens),
    totalTokens: n(u.total_tokens),
    cachedTokens: n(u.prompt_tokens_details?.cached_tokens),
  };
}

/** 请求体是 JSON 且 stream:true 时注入 include_usage；
 *  返回 {body, injected, clientStream, clientWantedUsage, isChat, model}。
 *  clientWantedUsage = 客户端**自己**就已要求 include_usage。此时那个 usage chunk 是它等着要的，
 *  代理绝不能吞——否则客户端的上下文占比与自动压缩判据永远拿不到真实 token。 */
function injectStreamOptions(buf) {
  try {
    const obj = JSON.parse(buf.toString('utf8'));
    const model = typeof obj?.model === 'string' ? obj.model : null;
    const clientStream = obj?.stream === true;
    const no = { injected: false, clientStream, clientWantedUsage: false, model };
    if (!obj || !clientStream) {
      return { body: buf, isChat: !!obj && Array.isArray(obj.messages), ...no };
    }
    const clientWantedUsage = obj.stream_options?.include_usage === true;
    obj.stream_options = { ...(obj.stream_options || {}), include_usage: true };
    return {
      body: Buffer.from(JSON.stringify(obj), 'utf8'),
      injected: true,
      clientStream,
      clientWantedUsage,
      isChat: true,
      model,
    };
  } catch {
    // body 不是合法 JSON：注入不了 include_usage，但绝不能因此把「流式」误判成非流式——
    // 否则 doHandle 会走整包缓冲，把客户端正等着的 SSE 憋到最后一把吐，长压缩调用必炸。
    // 用最省的正则从原文探 stream:true，保持逐字节透传语义（此时 injected=false，不吞任何 chunk）。
    let clientStream = false;
    try {
      clientStream = /"stream"\s*:\s*true/.test(buf.toString('utf8'));
    } catch {
      /* 连解码都失败：只能按非流式处理 */
    }
    return { body: buf, injected: false, clientStream, clientWantedUsage: false, isChat: false, model: null };
  }
}

function forwardHeaders(req) {
  const h = {};
  for (const [k, v] of Object.entries(req.headers)) {
    const lk = k.toLowerCase();
    if (lk === 'host' || lk === 'content-length' || lk === 'connection') continue;
    h[k] = v;
  }
  return h;
}

// fetch（undici）会自动解压这些 coding：响应体到手已是明文，但 content-encoding 头仍原样留着。
// 直接把这个头转发给客户端 = 「明文 body + gzip 头」，客户端 gunzip 必炸（incorrect header check）。
// 未知编码 undici 不解压、原样透传，那种情况下头必须保留，否则反向损坏。
// zstd 只在运行时 zlib 真有能力时才算 undici 可解，避免老运行时上误剥头。
const DECODED_CODINGS = new Set(['gzip', 'x-gzip', 'deflate', 'br', 'identity']);
if (typeof zlib.zstdDecompressSync === 'function') DECODED_CODINGS.add('zstd');

/** 该 content-encoding 值是否已被 fetch 解压（多级编码需每一级都可解才算）。 */
export function isDecodedByFetch(value) {
  if (!value) return false;
  const parts = String(value)
    .split(',')
    .map((s) => s.trim().toLowerCase())
    .filter(Boolean);
  return parts.length > 0 && parts.every((p) => DECODED_CODINGS.has(p));
}

/** 转发给客户端的响应头：剔掉长度/编码类头。undici 已解压时连 content-encoding 一起剔。 */
function responseHeaders(upstream) {
  const h = {};
  const dropEncoding = isDecodedByFetch(upstream.headers.get('content-encoding'));
  upstream.headers.forEach((v, k) => {
    const lk = k.toLowerCase();
    if (lk === 'content-length' || lk === 'transfer-encoding' || lk === 'connection') return;
    if (lk === 'content-encoding' && dropEncoding) return;
    h[k] = v;
  });
  return h;
}

async function doHandle(req, res, cfg, d) {
  const url = new URL(req.url, 'http://127.0.0.1');
  if (url.pathname === '/__proxy_health') {
    d.skip = true;
    let records = 0;
    try {
      records = fs.readFileSync(cfg.log, 'utf8').split('\n').filter(Boolean).length;
    } catch {
      /* 日志尚不存在 */
    }
    res.writeHead(200, { 'content-type': 'application/json' });
    res.end(JSON.stringify({ ok: true, upstream: cfg.upstream, log: cfg.log, reqLog: cfg.reqLog, records, pid: process.pid }));
    return;
  }

  const rawBody = req.method === 'GET' || req.method === 'HEAD' ? Buffer.alloc(0) : await readBody(req);
  const { body, injected, clientStream, clientWantedUsage, isChat, model } = injectStreamOptions(rawBody);
  // 只吞「代理自己注入 include_usage 才多出来」的那个 chunk；客户端原本就要的必须下发。
  const swallowUsageChunk = injected && !clientWantedUsage;
  const target = cfg.upstream + req.url;

  d.reqBytes = rawBody.length;
  d.stream = clientStream;
  d.wantUsage = clientWantedUsage;
  d.injected = injected;
  d.model = model;

  // 上游 fetch 绝不能绑 req.signal：readBody 读完请求体后 IncomingMessage 流即 close、
  // req.signal 随之 abort，会把刚发出的上游请求自我掐断——所有带 body 的 chat 请求都会 502
  // "This operation was aborted"。改用独立 controller，只在响应连接关闭（客户端断开或正常
  // 结束）时才 abort，既保留「客户端走了就取消上游」的语义，又不会被请求体读完误触发。
  // 副作用：客户端读到 [DONE] 就挂断时，上游尾部还在传 → 报「流被打断」。这是常态而非故障，
  // 诊断记录用 doneSeen 把它和真丢内容的截断分开。
  const ctl = new AbortController();
  res.once('close', () => ctl.abort());

  let upstream;
  try {
    upstream = await fetch(target, {
      method: req.method,
      headers: forwardHeaders(req),
      body: req.method === 'GET' || req.method === 'HEAD' ? undefined : body,
      signal: ctl.signal,
    });
  } catch (err) {
    d.err = `upstream unreachable: ${err.message}`;
    res.writeHead(502, { 'content-type': 'application/json' });
    res.end(JSON.stringify({ error: { message: `proxy upstream unreachable: ${err.message}`, type: 'proxy_error' } }));
    return;
  }

  d.ttfb = Date.now() - d.t0;
  d.status = upstream.status;
  const encUp = upstream.headers.get('content-encoding');
  const resHeaders = responseHeaders(upstream);
  if (encUp) {
    // 记下这个编码是被代理剥掉的（undici 已解压）还是原样透传的——排查「客户端解压失败」类问题的关键
    if (isDecodedByFetch(encUp)) d.encStripped = encUp;
    else d.encPassed = encUp;
  }

  const contentType = upstream.headers.get('content-type') || '';
  d.ctype = contentType.split(';')[0];
  // 是否逐块下发由**客户端**要不要流式决定（与代理有没有注入 usage 无关），其余整包缓冲后原样回传。
  if (!clientStream || !upstream.body) {
    // 非流式（或上游没给 body）：整包缓冲 → 解析 usage → 原样回传。
    const buf = Buffer.from(await upstream.arrayBuffer());
    d.respBytes = buf.length;
    res.writeHead(upstream.status, resHeaders);
    res.end(buf);
    if (isChat && upstream.status === 200 && contentType.includes('json')) {
      try {
        const j = JSON.parse(buf.toString('utf8'));
        d.id = j.id ?? null;
        const usage = pickUsage(j.usage);
        if (usage && (usage.promptTokens != null || usage.completionTokens != null)) {
          d.usageSeen = true;
          appendLog(cfg, { ts: new Date().toISOString(), id: j.id ?? null, model: j.model ?? null, path: url.pathname, stream: false, ...usage });
        }
      } catch {
        /* 响应不是合法 JSON：透传即可，不记录 */
      }
    }
    return;
  }

  // 流式：逐行转发 SSE。带 usage 且 choices 为空的末尾 chunk 记录后吞掉。
  res.writeHead(upstream.status, resHeaders);
  const decoder = new TextDecoder();
  const encoder = new TextEncoder();
  let pending = '';
  let rec = { ts: new Date().toISOString(), id: null, model: null, path: url.pathname, stream: true, promptTokens: null, completionTokens: null, totalTokens: null, cachedTokens: null };
  let logged = false;

  const emit = (line) => {
    const b = encoder.encode(line);
    d.lines++;
    d.fwdBytes += b.byteLength;
    res.write(b);
  };

  const finish = () => {
    if (!logged && (rec.promptTokens != null || rec.completionTokens != null)) {
      logged = true;
      d.usageSeen = true;
      appendLog(cfg, rec);
    }
  };

  const processLine = (line) => {
    const trimmed = line.trimEnd();
    if (!trimmed.startsWith('data:')) {
      emit(line);
      return;
    }
    const payload = trimmed.slice(5).trim();
    if (!payload || payload === '[DONE]') {
      if (payload === '[DONE]') d.doneSeen = true; // 内容已发到流的自然终点
      emit(line);
      return;
    }
    let j;
    try {
      j = JSON.parse(payload);
    } catch {
      emit(line);
      return;
    }
    if (j.id && !rec.id) rec.id = j.id;
    if (j.id && !d.id) d.id = j.id;
    if (j.model && !rec.model) rec.model = j.model;
    const usage = pickUsage(j.usage);
    if (usage && (usage.promptTokens != null || usage.completionTokens != null)) {
      rec = { ...rec, ...usage };
      finish();
    }
    // 注入 include_usage 后新增的末尾 chunk：choices 为空、只带 usage——吞掉不下发。
    // 但客户端自己就要 include_usage 时，这个 chunk 是它等着用的（上下文占比 / 自动压缩判据），必须下发。
    // 判据必须同时要求「这一帧确实带 usage」：只有空 choices 不足以定性——供应商在长流（尤其压缩）
    // 里可能发心跳 / keepalive 等空 choices 帧，误吞会打断客户端的 SSE 解析。
    const isUsageTail = !!usage && (usage.promptTokens != null || usage.completionTokens != null);
    if (swallowUsageChunk && isUsageTail && Array.isArray(j.choices) && j.choices.length === 0) {
      d.swallowed++;
      return;
    }
    emit(line);
  };

  let lastChunkAt = Date.now();
  try {
    for await (const chunk of upstream.body) {
      const now = Date.now();
      // 上游静默多久才吐下一块：区分「供应商卡住导致客户端放弃」与「数据在流、客户端照样取消」
      if (now - lastChunkAt > (d.maxIdleMs || 0)) d.maxIdleMs = now - lastChunkAt;
      lastChunkAt = now;
      d.respBytes = (d.respBytes || 0) + chunk.byteLength;
      pending += decoder.decode(chunk, { stream: true });
      let idx;
      while ((idx = pending.indexOf('\n')) >= 0) {
        const line = pending.slice(0, idx + 1);
        pending = pending.slice(idx + 1);
        processLine(line);
      }
    }
    if (pending) processLine(pending.endsWith('\n') ? pending : pending + '\n');
  } catch (err) {
    d.interrupted = true;
    d.idleMs = Date.now() - lastChunkAt;
    // [DONE] 已下发才被断 = 客户端收完就挂电话，内容一个字没少（真实流量的常态）；
    // 没到 [DONE] 就是真截断，回答确实少了尾巴。二者绝不混为一谈。
    if (!d.doneSeen) d.truncated = true;
    d.err = `stream interrupted: ${err.message}`;
    console.error(`[proxy] 流转发中断${d.doneSeen ? '（DONE 之后的正常收尾取消）' : '（未收到 DONE，内容被截断）'}：${err.message}`);
  } finally {
    finish();
    res.end();
  }
}

/** 每个请求恰好写一行诊断记录后透传，异常照旧交给上层处理器回 500。 */
async function handle(req, res, cfg) {
  const url = new URL(req.url, 'http://127.0.0.1');
  const d = newDiag(req, url);
  try {
    await doHandle(req, res, cfg, d);
  } catch (err) {
    if (!d.err) d.err = `handler threw: ${err.message}`;
    throw err;
  } finally {
    if (!d.skip) {
      d.ms = Date.now() - d.t0;
      if (d.status == null) d.status = res.statusCode ?? null;
      // 响应没写完就收尾 = 客户端中途走了（或上游被掐），这正是「转着转着没了」的指纹
      if (!res.writableEnded) d.aborted = true;
      delete d.t0;
      appendRequestLog(cfg, d);
    }
  }
}

export function startProxy(cfg = loadConfig()) {
  if (!isValidUpstream(cfg.upstream)) {
    // 没配上游就拒绝监听：宁可起不来，也不静默把请求发往错误/空目标。
    console.error('[proxy] upstream 未配置或非法，代理未启动。');
    console.error(`  配置：${selfCmd()} --setup-proxy --upstream <真实供应商根地址>`);
    console.error('  或编辑 ~/.qoder-credits-proxy/config.json 的 upstream 字段。');
    return null;
  }
  const server = http.createServer((req, res) => {
    handle(req, res, cfg).catch((err) => {
      console.error(`[proxy] 请求处理异常：${err.stack || err}`);
      if (!res.headersSent) res.writeHead(500, { 'content-type': 'application/json' });
      try {
        res.end();
      } catch {
        /* 连接已断 */
      }
    });
  });
  server.on('error', (err) => {
    // 端口被占（EADDRINUSE）等：写状态供报告提示，不静默改端口（会让用户已填的 Base URL 失效）。
    console.error(`[proxy] 监听失败（127.0.0.1:${cfg.port}）：${err.message}`);
    if (err.code === 'EADDRINUSE') {
      console.error(`  端口被其它程序占用。换一个：${selfCmd()} --setup-proxy --port <新端口>`);
      console.error('  改完后记得把 Qoder 里自定义模型的 Base URL 端口也同步改掉。');
    }
    writeStatus({ ok: false, error: err.code || err.message, port: cfg.port });
  });
  server.listen(cfg.port, '127.0.0.1', () => {
    console.log(`[proxy] 监听 http://127.0.0.1:${cfg.port} → ${cfg.upstream}`);
    console.log(`[proxy] usage 日志：${cfg.log}`);
    console.log('[proxy] 把自定义模型的 Base URL 的 host:port 换成 127.0.0.1:' + cfg.port + '（路径保留）即可。');
  });
  return server;
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  const srv = startProxy();
  if (!srv) process.exit(1);
}
