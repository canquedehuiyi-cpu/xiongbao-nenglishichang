#!/usr/bin/env node
/**
 * fetch-prompt-practices.mjs 官方提示词实践联网核验（质量自检工具）
 * 用法：
 *   node scripts/fetch-prompt-practices.mjs [--urls <逗号分隔>] [--timeout <秒>] [--ttl-hours <小时>] [--force] [--json]
 *
 * 能力：
 *  - 拉取官方提示词工程最佳实践文档（默认：OpenAI / Anthropic 官方指南）
 *  - 本地缓存 + TTL 频率控制：有效期内重复执行命中缓存，避免频繁请求
 *  - 失败降级：网络失败/超时自动返回最近一次缓存快照并告警
 *  - 域名白名单：默认仅允许 OpenAI / Anthropic 官方域名，防止 SSRF
 * 退出码：
 *  - 0：拉取成功 / 缓存命中 / 降级命中缓存（有可用数据）
 *  - 1：全部 URL 失败且无缓存 / 参数非法 / Node 无内置 fetch
 *
 * 设计原则：
 *  - 零外部依赖：仅用 Node 内置 fetch（Node 18+）与 node: 模块
 *  - 无副作用：缓存写入系统临时目录（--cache-dir 可指定），不触碰 skill 包
 *  - 诚实边界：官方文档为动态渲染页面，本工具保证可达性监测与响应快照
 *    留存；正文语义解析需结合 AI 联网能力或人工核对
 *
 * 用途定位：落实 SKILL.md §3.4 情报检索的确定性兜底（"跟上最新实践"）。
 */

import { mkdirSync, readFileSync, writeFileSync, existsSync } from "node:fs";
import { join } from "node:path";
import { tmpdir } from "node:os";
import { isMain, safePath } from "./lib.mjs";

// ---- 命令行辅助（本脚本自实现，零外部依赖） ----

function parseArgs(argv = process.argv.slice(2)) {
  const args = {};
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (!a.startsWith("--")) continue;
    const eq = a.indexOf("=");
    if (eq > -1) {
      args[a.slice(2, eq)] = a.slice(eq + 1);
    } else if (i + 1 < argv.length && !argv[i + 1].startsWith("--")) {
      args[a.slice(2)] = argv[++i];
    } else {
      args[a.slice(2)] = true;
    }
  }
  return args;
}

function printHelp(helpText) {
  process.stdout.write(helpText + "\n");
  process.exit(0);
}

function outputSuccess(data, json) {
  const result = { ok: true, ...data };
  if (json) process.stdout.write(JSON.stringify(result, null, 2) + "\n");
  else process.stdout.write("✓ 操作成功\n" + JSON.stringify(result, null, 2) + "\n");
  process.exit(0);
}

function outputError(error, extra = {}, json) {
  const result = { ok: false, error, ...extra };
  if (json) process.stdout.write(JSON.stringify(result, null, 2) + "\n");
  else {
    process.stderr.write(`✗ ${error}\n`);
    if (extra.hint) process.stderr.write(`  提示: ${extra.hint}\n`);
  }
  process.exit(1);
}

// ---- 默认配置 ----

const DEFAULT_URLS = [
  'https://platform.openai.com/docs/guides/prompt-engineering',
  'https://docs.anthropic.com/en/docs/build-with-claude/prompt-engineering',
];
// 国内官方源（--region cn 时使用；均为厂商官方文档，域名已入白名单）
const CN_URLS = [
  'https://help.aliyun.com/zh/model-studio/prompt-engineering-guide',
  'https://www.volcengine.com/docs/82379/1221660',
];
const DEFAULT_ALLOWED_HOSTS = ['platform.openai.com', 'docs.anthropic.com', 'openai.com', 'anthropic.com'];
// 国内官方源白名单：仅精确域名（防 SSRF 面扩大，泛域由厂商控制但无需开放）
const CN_ALLOWED_HOSTS = ['help.aliyun.com', 'www.volcengine.com'];
const DEFAULT_TIMEOUT = 10; // 秒
const DEFAULT_TTL_HOURS = 7 * 24; // 7 天（与 search-cache TTL 对齐）
const SNIPPET_LEN = 500;

const NOTE =
  '官方文档为动态渲染页面（SPA），本工具保证可达性监测与响应快照留存；正文语义解析需结合 AI 联网能力或人工核对官方文档。';

const HELP = `官方提示词实践联网核验（拉取 OpenAI/Anthropic 官方指南，缓存 + 降级）
用法:
  node scripts/fetch-prompt-practices.mjs [选项]

选项:
  --json                 以 JSON 格式输出
  --region <地区>        官方源地区：international（默认，OpenAI/Anthropic）或 cn（阿里云百炼/火山方舟官方指南）
  --urls <逗号分隔>      指定要拉取的官方 URL（默认按 --region 选择官方指南）
  --timeout <秒>         单请求超时，默认 10
  --ttl-hours <小时>     缓存有效期，默认 168（7 天，期内重复执行命中缓存）
  --force                忽略缓存有效期，强制重新拉取
  --cache-dir <路径>     缓存目录（默认系统临时目录 prompt-practices-cache）
  --allow-domains <列表> 追加允许的域名（默认仅 OpenAI/Anthropic 官方域名，防 SSRF）
  --allow-any-domain     放开域名限制（谨慎：仅在你信任目标地址时使用）
  --help                 显示帮助

输出说明
  source=network  本次网络拉取成功
  source=cache    缓存有效期内命中，未发起网络请求
  source=degraded 网络失败，降级返回最近缓存快照（含 warning）

诚实边界
  官方文档为动态渲染页面（SPA），本工具只保证：可达性、HTTP 状态、
  响应体大小与内容片段快照。正文语义解析请结合 AI 联网能力或人工核对。

退出码:
  0  拉取成功 / 缓存命中 / 降级命中缓存（有可用数据）
  1  全部 URL 失败且无缓存 / 参数非法 / Node 版本过低（需 18+）

示例:
  node scripts/fetch-prompt-practices.mjs --json
  node scripts/fetch-prompt-practices.mjs --force --json
  node scripts/fetch-prompt-practices.mjs --urls https://platform.openai.com/docs/guides/prompt-engineering --timeout 15
`;

// ---- 参数校验 ----

function parsePositive(v, def, name, json) {
  if (v === undefined || v === true) return def;
  const n = Number(v);
  if (!Number.isFinite(n) || n <= 0) {
    outputError(`--${name} 参数非法: ${v}`, { hint: '需为正数' }, json);
  }
  return n;
}

/**
 * URL 校验：必须 http(s)，默认仅允许白名单域名（防 SSRF）
 */
function validateUrl(raw, allowedHosts, allowAny) {
  let u;
  try {
    u = new URL(raw);
  } catch {
    return { ok: false, error: `非法 URL: ${raw}` };
  }
  if (u.protocol !== 'https:' && u.protocol !== 'http:') {
    return { ok: false, error: `仅允许 http(s) URL: ${raw}` };
  }
  if (!allowAny && !allowedHosts.some((h) => u.hostname === h || u.hostname.endsWith('.' + h))) {
    return { ok: false, error: `域名不在白名单: ${u.hostname}（可用 --allow-domains 追加或 --allow-any-domain 放开）` };
  }
  return { ok: true, url: u };
}

// ---- 拉取 ----

// v1.0.3 修复: 响应体上限（防超大页面全量读入内存）
const MAX_BODY_BYTES = 2 * 1024 * 1024;

// v1.0.3 修复: content-length 超上限时改流式读取并截断，不再整体读入内存
async function readBodyCapped(res, cap) {
  const cl = Number(res.headers.get('content-length'));
  if (Number.isFinite(cl) && cl > cap && res.body) {
    const reader = res.body.getReader();
    const chunks = [];
    let total = 0;
    try {
      while (total < cap) {
        const { done, value } = await reader.read();
        if (done) break;
        total += value.byteLength;
        chunks.push(value);
      }
    } finally {
      try { await reader.cancel(); } catch { /* 忽略取消失败 */ }
    }
    return Buffer.concat(chunks).toString('utf8');
  }
  return res.text();
}

async function fetchUrl(urlStr, timeoutSec) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutSec * 1000);
  try {
    const res = await fetch(urlStr, { redirect: 'follow', signal: controller.signal });
    const body = await readBodyCapped(res, MAX_BODY_BYTES);
    return {
      ok: res.ok,
      httpStatus: res.status,
      size: Buffer.byteLength(body, 'utf8'),
      snippet: body.slice(0, SNIPPET_LEN),
      error: res.ok ? null : `HTTP ${res.status}`,
    };
  } catch (e) {
    return {
      ok: false,
      httpStatus: null,
      size: 0,
      snippet: '',
      error: e && e.name === 'AbortError' ? `超时(${timeoutSec}s)` : `网络错误: ${e && e.message ? e.message : e}`,
    };
  } finally {
    clearTimeout(timer);
  }
}

// ---- 缓存 ----

function cachePathOf(cacheDir) {
  return join(cacheDir, 'prompt-practices-cache.json');
}

function loadCache(cacheDir) {
  const p = cachePathOf(cacheDir);
  if (!existsSync(p)) return null;
  try {
    return JSON.parse(readFileSync(p, 'utf8'));
  } catch {
    return null; // 缓存损坏视为无缓存
  }
}

function saveCache(cacheDir, data) {
  try {
    mkdirSync(cacheDir, { recursive: true });
    writeFileSync(cachePathOf(cacheDir), JSON.stringify(data, null, 2), 'utf8');
  } catch {
    // 缓存写失败不致命：仅失去快照能力
  }
}

function cacheFresh(cache, ttlHours) {
  if (!cache || !cache.fetchedAt || !Array.isArray(cache.results)) return false;
  const t = new Date(cache.fetchedAt).getTime();
  if (Number.isNaN(t)) return false;
  return (Date.now() - t) / 3600000 < ttlHours;
}

// ---- 主流程 ----

async function main() {
  const args = parseArgs();
  if (args.help) printHelp(HELP);

  const json = !!args.json;

  if (typeof fetch !== 'function') {
    outputError('当前 Node 版本无内置 fetch，需 Node 18+', { hint: '升级 Node 版本后重试' }, json);
  }

  const timeoutSec = parsePositive(args.timeout, DEFAULT_TIMEOUT, 'timeout', json);
  const ttlHours = parsePositive(args['ttl-hours'], DEFAULT_TTL_HOURS, 'ttl-hours', json);
  const force = !!args.force;
  const allowAny = !!args['allow-any-domain'];
  // v1.0.3 安全修复: 放开白名单是高危操作，向 stderr 打印醒目警告（原实现仅 help 文本提示，运行时静默）
  if (allowAny) {
    process.stderr.write('⚠️ --allow-any-domain 已禁用域名白名单：将允许向任意 http(s) 地址发起请求（SSRF 风险），请确认目标可信。\n');
  }
  const region = args.region === 'cn' ? 'cn' : 'international';
  // v1.0.3 安全修复: --cache-dir 须经安全边界校验（仅限包内或系统临时目录），禁止指向任意目录写入
  let cacheDir = args['cache-dir'] ? String(args['cache-dir']) : join(tmpdir(), 'prompt-practices-cache');
  try {
    cacheDir = safePath(cacheDir);
  } catch (e) {
    outputError(e.message, { hint: '缓存目录仅限技能包内部或系统临时目录' }, json);
  }
  const extraHosts = args['allow-domains']
    ? String(args['allow-domains']).split(',').map((s) => s.trim()).filter(Boolean)
    : [];
  // v1.0.3 安全修复: 追加域名必须含点号，拒绝 "com" 这类顶级域通配
  // （原实现的 endsWith 子域匹配遇到顶级域会放行所有同后缀域名）
  for (const h of extraHosts) {
    if (!h.includes('.')) {
      outputError(`--allow-domains 拒绝顶级域通配: ${h}`, { hint: '追加项必须是完整域名（含点），如 docs.example.com' }, json);
    }
  }
  const allowedHosts = [...DEFAULT_ALLOWED_HOSTS, ...(region === 'cn' ? CN_ALLOWED_HOSTS : []), ...extraHosts];

  const urls = args.urls ? String(args.urls).split(',').map((s) => s.trim()).filter(Boolean) : (region === 'cn' ? CN_URLS : DEFAULT_URLS);
  if (urls.length === 0) {
    outputError('URL 列表为空', { hint: '用 --urls 传逗号分隔的官方文档地址' }, json);
  }
  for (const u of urls) {
    const v = validateUrl(u, allowedHosts, allowAny);
    if (!v.ok) outputError(v.error, { hint: '默认仅允许 OpenAI/Anthropic 官方域名（防 SSRF）' }, json);
  }

  // 缓存命中（TTL 内且未强制）
  const cache = loadCache(cacheDir);
  if (!force && cacheFresh(cache, ttlHours)) {
    outputSuccess(
      {
        action: 'fetch_prompt_practices',
        source: 'cache',
        cacheHit: true,
        fetchedAt: cache.fetchedAt,
        ttlHours,
        results: cache.results,
        note: NOTE,
      },
      json
    );
  }

  // 网络拉取
  const results = [];
  for (const u of urls) {
    results.push({ url: u, ...(await fetchUrl(u, timeoutSec)) });
  }

  if (results.every((r) => r.ok)) {
    const snapshot = { fetchedAt: new Date().toISOString(), results };
    saveCache(cacheDir, snapshot);
    outputSuccess(
      {
        action: 'fetch_prompt_practices',
        source: 'network',
        cacheHit: false,
        fetchedAt: snapshot.fetchedAt,
        ttlHours,
        results,
        note: NOTE,
      },
      json
    );
  }

  // 部分/全部失败 → 降级命中缓存
  if (cache && Array.isArray(cache.results) && cache.results.length > 0) {
    outputSuccess(
      {
        action: 'fetch_prompt_practices',
        source: 'degraded',
        cacheHit: true,
        fetchedAt: cache.fetchedAt,
        ttlHours,
        results,
        warning: '网络拉取失败，已降级返回最近缓存快照',
        note: NOTE,
      },
      json
    );
  }

  outputError('网络拉取失败且无可用缓存', { hint: '检查网络后重试，或 --urls 更换官方源' }, json);
}

// v1.0.3 修复: 增加主入口守卫——原实现在文件末尾无条件调用 main()，
// 任何模块导入本脚本都会意外触发网络请求；作为 CLI 直接运行时行为不变
if (isMain(import.meta)) {
  await main();
}
