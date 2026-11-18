#!/usr/bin/env node
// cli.mjs — 编排：解析转录 → 构建报告 → 写 report.json → 终端榜（可选渲染 Canvas）。
//
// 用法（推荐用插件自带启动器，无需 PATH 上有 node；开发期直接 node 也一样）：
//   <插件根>/bin/credits-inspector.cmd cli --latest    # 等价于 node scripts/cli.mjs --latest
//   node scripts/cli.mjs --latest                 # 自动选最近修改的富转录
//   node scripts/cli.mjs --transcript <path>       # 指定转录
//   node scripts/cli.mjs --session <id>            # 按会话 id 定位
//   node scripts/cli.mjs --stdin                   # 从 stdin 读取 Stop 钩子 JSON
//   node scripts/cli.mjs --setup-proxy --upstream <url> [--port <n>]  # 写配置 + 后台拉起代理（自定义模型用）
//   node scripts/cli.mjs --check-proxy             # 代理链路自检
//   node scripts/cli.mjs --stop-proxy              # 停用代理（停进程 + enabled:false；改回官方模型时用）
//   node scripts/cli.mjs --request-log [--tail <n>] # 每请求诊断记录（状态/耗时/编码/中断原因）+ 归因
//   附加：--out <dir> --overrides <dir> --proxy-log <file> --top <n> --json --no-canvas

import fs from 'node:fs';
import path from 'node:path';
import { pathToFileURL } from 'node:url';
import { generateReport } from './lib/generate.mjs';
import { findLatestTranscript, findTranscriptForSession, overridePath } from './lib/paths.mjs';
import {
  loadConfig,
  isValidUpstream,
  readConfigRaw,
  writeConfig,
  pickFreePort,
  proxyHealth,
  spawnProxy,
  waitForHealth,
  stopProxy as stopProxyRuntime,
  readRequestLog,
  summarizeRequests,
  selfCmd,
} from './proxy.mjs';

function parseArgs(argv) {
  const a = { top: 15, json: false, canvas: true, stdin: false };
  for (let i = 0; i < argv.length; i++) {
    const k = argv[i];
    const next = () => argv[++i];
    switch (k) {
      case '--transcript': a.transcript = next(); break;
      case '--session': a.session = next(); break;
      case '--latest': a.latest = true; break;
      case '--out': a.out = next(); break;
      case '--overrides': a.overrides = next(); break;
      case '--proxy-log': a.proxyLog = next(); break;
      case '--setup-proxy': a.setupProxy = true; break;
      case '--check-proxy': a.checkProxy = true; break;
      case '--stop-proxy': a.stopProxy = true; break;
      case '--request-log': a.dumpRequests = true; break;
      case '--tail': a.tail = parseInt(next(), 10) || 30; break;
      case '--upstream': a.upstream = next(); break;
      case '--port': a.port = parseInt(next(), 10) || undefined; break;
      case '--cwd': a.cwd = next(); break;
      case '--top': a.top = parseInt(next(), 10) || 15; break;
      case '--json': a.json = true; break;
      case '--stdin': a.stdin = true; break;
      case '--no-canvas': a.canvas = false; break;
      case '--canvas': a.canvas = true; break;
      default: break;
    }
  }
  return a;
}

function readStdinJson() {
  try {
    const raw = fs.readFileSync(0, 'utf8');
    return raw ? JSON.parse(raw) : {};
  } catch {
    return {};
  }
}

export function humanTokens(n) {
  if (!isFinite(n)) return '—';
  const abs = Math.abs(n);
  if (abs >= 1e9) return (n / 1e9).toFixed(2) + 'B';
  if (abs >= 1e6) return (n / 1e6).toFixed(2) + 'M';
  if (abs >= 1e3) return (n / 1e3).toFixed(1) + 'K';
  return String(Math.round(n));
}

function pct(x) {
  return (x * 100).toFixed(1) + '%';
}

/** ISO 时间戳 → 本地 HH:MM；空或无效返回「—」（压缩明细的时刻列用）。 */
function hm(iso) {
  if (!iso) return '—';
  const d = new Date(iso);
  if (isNaN(d.getTime())) return '—';
  const p = (v) => String(v).padStart(2, '0');
  return `${p(d.getHours())}:${p(d.getMinutes())}`;
}

function bar(share, width = 22) {
  const filled = Math.max(0, Math.min(width, Math.round(share * width)));
  return '█'.repeat(filled) + '·'.repeat(width - filled);
}

function resolveTranscript(args) {
  if (args.stdin) {
    const hook = readStdinJson();
    if (hook.transcript_path && fs.existsSync(hook.transcript_path)) {
      return { transcript: hook.transcript_path, sessionId: hook.session_id, cwd: hook.cwd };
    }
    if (hook.session_id) {
      const p = findTranscriptForSession(hook.session_id);
      if (p) return { transcript: p, sessionId: hook.session_id, cwd: hook.cwd };
    }
  }
  if (args.transcript && fs.existsSync(args.transcript)) {
    return { transcript: args.transcript, sessionId: args.session, cwd: args.cwd };
  }
  if (args.session) {
    const p = findTranscriptForSession(args.session);
    if (p) return { transcript: p, sessionId: args.session, cwd: args.cwd };
  }
  const latest = findLatestTranscript();
  if (latest) return { transcript: latest, sessionId: args.session, cwd: args.cwd };
  return { transcript: null };
}

const SOURCE_ZH = {
  'desktop-rich': '桌面端富转录',
  'ide-lite': 'IDE 端精简转录',
  unknown: '来源未知',
};

/** 可用性徽标：与 Canvas 用同一套词，避免终端与报告各说一套。 */
const AVAIL_ZH = {
  measured: '实测',
  derived: '推导',
  fallback: '回退',
  manual: '手工',
  unavailable: '不可用',
};

const avail = (av, key) => AVAIL_ZH[av?.[key]] || AVAIL_ZH.unavailable;

// —— usage 记录代理（自定义模型 / BYOK 专用）：配置、拉起、自检、停用 ——

/** 把用户给的真实 Base URL 拆成「代理上游根」+「客户端会重发的路径（如 /v1）」。
 *  OpenAI 兼容客户端把 /v1 放在 Base URL 里，请求路径 = /v1/chat/completions；
 *  代理转发 = upstream + 请求路径，故 upstream 不能带 /vN，否则拼成 /v1/v1/…。
 *  把 /vN 挪到「指向代理的 Base URL」上，两端就对上了。 */
function splitUpstream(u) {
  const s = String(u || '').trim().replace(/\/+$/, '');
  const m = s.match(/^(.*?)(\/v\d+)$/i);
  if (m) return { upstream: m[1].replace(/\/+$/, ''), basePath: m[2] };
  return { upstream: s, basePath: '' };
}

/** basePath=null = 不知道用户原始 Base URL 的路径（重跑 --setup-proxy、沿用已存 upstream）。
 *  这时绝不猜一个 /v1 出来——猜错的路径会静默 404，比不印更坏。 */
function printBaseUrl(cfg, basePath) {
  console.log('');
  console.log('  下一步 · Qoder 设置 → 模型 → 添加/编辑「自定义供应商」（协议 OpenAI 兼容）：');
  console.log(
    basePath == null
      ? `    Base URL : 把你现在那条的 host:port 换成 127.0.0.1:${cfg.port}，路径段原样保留   ← 只改前半截`
      : `    Base URL : http://127.0.0.1:${cfg.port}${basePath}   ← 复制这一行`
  );
  console.log('    API Key  : 你原来的供应商 Key（代理只透传、绝不记录）');
  console.log('    Model ID : 你的模型名（如 qwen3-coder-plus）');
  console.log('  配好后新开一个会话即有实测 token；--check-proxy 可随时自检链路。');
}

async function setupProxy(args) {
  const raw = readConfigRaw() || {};
  const srcUp = args.upstream || (typeof raw.upstream === 'string' ? raw.upstream : '');
  const { upstream, basePath } = splitUpstream(srcUp);
  // 只有用户这次真给了原始 Base URL，才谈得上替他拼出完整替换值。
  const shownPath = args.upstream ? basePath : null;
  if (!isValidUpstream(upstream)) {
    console.error('✗ 需要有效的上游地址。用法：');
    console.error(`    ${selfCmd()} --setup-proxy --upstream <你的真实供应商 Base URL>`);
    console.error('  例：--upstream https://token-plan.cn-beijing.maas.aliyuncs.com/compatible-mode/v1');
    console.error('  （末尾 /v1 会被自动挪到指向代理的 Base URL 上，无需你操心）');
    process.exit(1);
  }
  // 端口：--port > 已有配置 > 自动挑一个空闲端口（避开 8787 等常见占用）。
  let port = Number.isFinite(args.port) ? args.port : Number.isFinite(raw.port) ? raw.port : null;
  if (port == null) port = await pickFreePort(loadConfig().port);
  writeConfig({ upstream, port, enabled: true });

  const cfg = loadConfig(); // 读回合并后的配置（含 env 覆盖）
  const running = await proxyHealth(cfg, 800);
  if (running) {
    console.log(`✓ 代理已在运行（pid ${running.pid}，端口 ${cfg.port}）；配置已更新。`);
    console.log(`  上游   ${cfg.upstream}`);
    console.log(`  日志   ${running.log}（已记 ${running.records} 条）`);
    printBaseUrl(cfg, shownPath);
    return;
  }
  spawnProxy(cfg);
  const health = await waitForHealth(cfg, { tries: 15, delay: 200 });
  if (!health) {
    console.error(`✗ 代理启动失败（127.0.0.1:${cfg.port} 无响应）。`);
    console.error('  常见原因：端口被占（换 --port <新端口> 并同步改 Base URL）。');
    console.error(`  自检：${selfCmd()} --check-proxy`);
    process.exit(1);
  }
  try {
    fs.mkdirSync(path.dirname(cfg.log), { recursive: true });
    fs.writeFileSync(path.join(path.dirname(cfg.log), 'proxy.pid'), String(health.pid), 'utf8');
  } catch {
    /* pid 文件只是便利，写不了不影响 */
  }
  console.log(`✓ 代理已后台启动（pid ${health.pid}）`);
  console.log(`  监听   http://127.0.0.1:${cfg.port}`);
  console.log(`  上游   ${cfg.upstream}`);
  console.log(`  日志   ${cfg.log}`);
  printBaseUrl(cfg, shownPath);
}

/** 一行的短标记：把诊断记录里值得注意的旗标拼成人话片段。 */
function diagFlags(r) {
  const f = [];
  if (r.injected) f.push('代理注usage');
  if (r.wantUsage) f.push('客户端自求usage');
  if (r.swallowed) f.push(`吞chunk${r.swallowed}`);
  if (r.encStripped) f.push(`剥${r.encStripped}`);
  if (r.encPassed) f.push(`透传${r.encPassed}`);
  if (r.interrupted) f.push(typeof r.doneSeen !== 'boolean' ? '中断(旧版未分类)' : r.doneSeen ? '收完即断' : '截断!未到DONE');
  if (r.truncated) f.push(`断前静默${r.idleMs == null ? '?' : r.idleMs}ms 最长间隔${r.maxIdleMs || 0}ms`);
  if (r.aborted) f.push('客户端提前断开');
  if (r.status === 200 && !r.usageSeen && String(r.path).includes('chat')) f.push('无usage');
  // DONE 之后的中断只是客户端收完挂电话的余波，别再贴 err 吓人
  if (r.err && !(r.doneSeen && /^stream interrupted/.test(String(r.err)))) f.push(`err:${String(r.err).slice(0, 60)}`);
  return f.join(' ');
}

/** 请求诊断日志的归因结论：把「代理错 / 供应商拒 / 客户端走」分开说，避免互相甩锅。 */
function triageLines(s) {
  const out = [];
  out.push(
    `  合计：正常 ${s.ok} · 上游报错 ${s.upstreamRejected} · 代理失败 ${s.proxyError} · 首字节前客户端断开 ${s.clientAbort}` +
      ` · 客户端提前断开 ${s.aborted} · 流被打断 ${s.interrupted}（真截断 ${s.truncated}${s.unknownInterrupt ? ` · 旧版未分类 ${s.unknownInterrupt}` : ''}） · 成功但无 usage ${s.noUsage}`
  );
  if (s.slowest && s.slowest.ms > 30000) {
    out.push(`  最慢一笔 ${s.slowest.ms}ms（${s.slowest.path}，HTTP ${s.slowest.status}）——长响应超过 30s 容易被客户端判超时。`);
  }
  out.push('  归因：');
  if (s.proxyError) {
    out.push('    · 有「代理失败」记录 = 请求没出得去或代理自己抛了，看上面 err 字段（多为 upstream 地址/网络/端口）。');
  }
  if (s.clientAbort) {
    out.push(`    · ${s.clientAbort} 笔在拿到首字节前就被客户端断开（最长 ${s.clientAbortMaxMs}ms）——不是代理故障。若耗时集中在某个整数（如 ~60000ms），即 Qoder 客户端的首字节超时阈值：压缩请求体过大、供应商 prefill 超过该阈值时必现。方向在「压得太晚 / 上下文太大」，把压缩提前到更低占比即可避开，代理与供应商都没错。`);
  }
  if (s.upstreamRejected) {
    out.push('    · 有「上游报错」= 供应商直接拒绝（额度、鉴权、参数、模型名），代理只是原样转达，不是代理的问题。');
  }
  if (s.truncatedStalled) {
    out.push(`    · ${s.truncatedStalled} 笔「截断 + 断前上游静默 ≥15s」= 供应商长时间不吐字，客户端等不下去自己断的，方向在模型/供应商侧。`);
  }
  if (s.truncated > s.truncatedStalled) {
    out.push(`    · ${s.truncated - s.truncatedStalled} 笔「截断但数据一直在流」= 上游正常吐字、客户端中途自己取消（界面那句「系统发生异常，请重试」通常就是这类），代理与供应商都没出错。`);
  }
  if (s.aborted) {
    out.push('    · 有「客户端提前断开」= Qoder 侧在响应走完前关了连接（取消、超时或换模型）。');
  }
  if (s.interrupted > s.truncated + s.unknownInterrupt) {
    out.push(`    · ${s.interrupted - s.truncated - s.unknownInterrupt} 笔「收完即断」= [DONE] 已下发后客户端才挂断，是 SSE 的正常收尾，不是故障、不丢内容。`);
  }
  if (s.unknownInterrupt) {
    out.push(`    · ${s.unknownInterrupt} 笔是旧版代理写的历史记录，日志里没有 doneSeen 字段，事后无法再分诊；新记的请求才带。`);
  }
  if (s.noUsage) {
    out.push('    · 有「成功但无 usage」= 供应商返回了回答却没带 token 计数，报告只能显示「—」，与代理无关。');
  }
  if (!s.proxyError && !s.upstreamRejected && !s.clientAbort && !s.aborted && !s.truncated && !s.noUsage) {
    out.push('    · 全部 200 且都拿到 usage：代理链路干净。若界面仍显示 0 token / 不压缩，方向在客户端或模型档案配置，不在代理。');
  }
  return out;
}

async function requestLogCmd(args) {
  const cfg = loadConfig();
  const recs = readRequestLog(cfg, args.tail || 30);
  console.log(`请求诊断日志：${cfg.reqLog}`);
  if (!recs.length) {
    console.log('  日志为空或不存在。两种可能：');
    console.log('  1) 运行中的代理是旧版（还没这功能）——先停再重开：');
    console.log(`     ${selfCmd()} --stop-proxy && ${selfCmd()} --setup-proxy`);
    console.log('  2) 代理起着但一个请求都没收到（Base URL 没指向代理），跑 --check-proxy 看 records。');
    return;
  }
  for (const r of recs) {
    const hm = r.ts ? new Date(r.ts).toLocaleTimeString('zh-CN', { hour12: false }) : '—';
    const model = String(r.model ?? '—');
    const path = String(r.path ?? '').replace(/^.*\/v\d+\//, '/');
    console.log(
      `  ${hm}  ${String(r.status ?? '—').padStart(3)}  ${String(r.ms ?? '—').padStart(6)}ms` +
        `  首字${String(r.ttfb ?? '—').padStart(6)}ms` +
        `  ${r.stream ? '流' : '整'}` +
        `  ${(r.method || '?') + ' ' + path.padEnd(20)}` +
        `  ${(model.length > 28 ? model.slice(-28) : model).padEnd(28)}` +
        `  req=${Math.round((r.reqBytes || 0) / 1024)}KB resp=${Math.round((r.respBytes || 0) / 1024)}KB` +
        `  ${diagFlags(r)}`
    );
  }
  console.log(triageLines(summarizeRequests(recs)).join('\n'));
}

async function checkProxy() {
  const cfg = loadConfig();
  if (!readConfigRaw()) {
    console.log('✗ 还没有配置（~/.qoder-credits-proxy/config.json 不存在）。');
    console.log(`  配置：${selfCmd()} --setup-proxy --upstream <真实供应商 Base URL>`);
    process.exit(1);
  }
  console.log('代理配置：');
  console.log(`  enabled : ${cfg.enabled !== false}`);
  console.log(`  upstream: ${cfg.upstream || '(空)'}${isValidUpstream(cfg.upstream) ? '' : '   ← 未填/非法'}`);
  console.log(`  port    : ${cfg.port}`);
  if (cfg.enabled === false) {
    console.log('  已被 --stop-proxy 停用，SessionStart 不会自动拉起。重新启用：--setup-proxy');
    return;
  }
  if (!isValidUpstream(cfg.upstream)) {
    console.log('  ⚠ upstream 未填或非法，代理不会启动。用 --setup-proxy --upstream <url> 配置。');
    process.exit(1);
  }
  const health = await proxyHealth(cfg, 1000);
  if (!health) {
    console.log(`✗ 代理未运行（127.0.0.1:${cfg.port} 无响应）。`);
    console.log(`  启动：${selfCmd()} --setup-proxy  （或新开一个会话，SessionStart 钩子自动拉起）`);
    process.exit(1);
  }
  console.log(`✓ 代理运行中（pid ${health.pid}）`);
  console.log(`  上游   ${health.upstream}`);
  console.log(`  日志   ${health.log}（已记 ${health.records} 条 usage）`);
  if (health.records === 0) {
    console.log('  ⚠ 日志还是空的 = 流量没走代理（不是代理坏了）。按顺序排查，照念给用户即可：');
    console.log(`    1) Qoder 设置 → 模型 → 你那个自定义模型：Base URL 的 host:port 换成 http://127.0.0.1:${cfg.port}，`);
    console.log('       结尾路径段（通常是 /v1）原样保留、API Key 与 Model ID 一律不动。');
    console.log('    2) 完全退出并重启 Qoder —— 改完 Base URL 只「新开会话」常常不生效，端点会被缓存。');
    console.log('    3) 重启后新开会话，确认对话框顶部选中的就是这个自定义模型（别用成官方模型或别的配置）。');
    console.log('    4) 随便发一句话，再跑一次 --check-proxy：records 开始 > 0 就是链路打通了。');
    console.log('    （只对之后的新会话生效；改 Base URL 之前的历史会话不会有数据，可用 overrides 回填。）');
  } else {
    console.log('  链路已通：报告生成时会自动按 message.id join 出实测 token。');
  }
  if (!health.reqLog) {
    console.log('  诊断   ⚠ 运行中的代理是旧版，不记请求诊断日志（要分清「压缩失败是代理还是模型」就得靠它）。重启即得：');
    console.log(`         ${selfCmd()} --stop-proxy && ${selfCmd()} --setup-proxy`);
  } else {
    const reqs = readRequestLog(cfg, 200);
    console.log(`  诊断   ${cfg.reqLog}${reqs.length ? `（最近 ${reqs.length} 笔）` : '（还没有记录）'}`);
    if (reqs.length) console.log(triageLines(summarizeRequests(reqs)).join('\n'));
  }
}

async function stopProxyCmd() {
  const cfg = loadConfig();
  const killed = await stopProxyRuntime();
  console.log(
    killed
      ? `✓ 已停止代理进程（端口 ${cfg.port}），并置 enabled:false。`
      : '✓ 未发现运行中的代理；已置 enabled:false（若之前配置过）。'
  );
  console.log(`  之后 SessionStart 不再自动拉起（适合改回官方模型）。重新启用：${selfCmd()} --setup-proxy`);
}

function printTerminal(report, transcript, outDir) {
  const t = report.totals;
  const s = report.session;
  const c = report.context;
  const av = report.availability || {};
  const m = report.manual;
  const line = '─'.repeat(64);
  const out = [];
  // roundTrips 是否为实测 = 转录里到底有没有 usage。手工回填的 credits 不能让它变 true，
  // 否则下面那套按 ratio 推导的 token 榜会照印一屏 0。
  const hasUsage = av.roundTrips === 'measured';
  const dash = (v) => (v == null ? '—' : v);

  out.push(line);
  out.push(`  会话 token 消耗截析  ·  ${s.model || '未知模型'}${s.modelSource === 'manual' ? '（手工录入）' : ''}`);
  out.push(
    `  ${SOURCE_ZH[report.source] || report.source || '来源未知'}  ·  会话 ${String(s.id || '').slice(0, 8)}` +
      `  ·  往返 ${hasUsage ? `${s.roundTrips} 次` : '—'}` +
      `  ·  压缩 ${av.compactions === 'unavailable' ? '—' : `${s.compactions} 次`}` +
      `  ·  用户轮 ${s.turns}`
  );
  out.push(`  插件 v${report.pluginVersion || '?'}  ·  schema v${report.schemaVersion}` +
    (report.usageSource ? `  ·  usage 来源 ${report.usageSource === 'proxy' ? '代理实测' : report.usageSource === 'mixed' ? '转录+代理混合' : '转录'}` : ''));
  out.push(line);

  // —— 无 usage：不印任何 token / Credits / 占比榜（印出来全是 0，会被误读成「没花钱」）——
  if (!hasUsage) {
    if (report.source === 'desktop-rich') {
      // 富转录但无 usage = 自定义模型（BYOK）：响应不经 Qoder 计费网关，指引走代理。
      out.push('  ✗ 本转录不含 message.usage —— 自定义模型（BYOK）不经 Qoder 计费网关，');
      out.push('    credits/ratio 无来源，提供商返回的 usage 客户端也不落盘。');
      if (report.proxy && report.proxy.logExists && report.proxy.logRecords > 0 && report.proxy.matched === 0) {
        out.push(`    ⚠ 代理日志存在（${report.proxy.logRecords} 条）但没有一条按 message.id 对上本会话：`);
        out.push('      本会话可能发生在改 Base URL 之前，或代理未覆盖该模型的端点。');
      } else {
        out.push('    补救（改一个配置文件即可，免装 Node、之后全自动）：');
        out.push('      1) 编辑 ~/.qoder-credits-proxy/config.json，把 upstream 填成你的供应商根地址（= Base URL 去掉结尾 /v1）');
        out.push(`      2) Qoder 设置 → 模型 → 自定义模型：Base URL 的 host:port 换成 127.0.0.1:${(report.proxy && report.proxy.port) || 49787}（路径保留）`);
        out.push('      3) 新开一个会话，代理自动拉起；装了 Node 也可用 --setup-proxy / --check-proxy 一步到位');
        out.push('    之后的会话即有实测 token（含输出 token）；credits 仍无本地真值。');
      }
      out.push('    也可把外部真值（如 DashScope 控制台用量）写进下面的文件后重跑（字段全部可选）：');
      out.push(`      ${overridePath(outDir || '.', s.id || '<sessionId>')}`);
    } else {
      out.push('  ✗ 本转录不含 message.usage —— IDE 端客户端根本不写这个字段。');
      out.push('    Credits / token / 各类占比本地不可恢复，故下方一律不印；0 不代表没花钱。');
      out.push('    要真值：看官方 UI；或把官方数字写进下面这个文件后重跑（字段全部可选）：');
      out.push(`      ${overridePath(outDir || '.', s.id || '<sessionId>')}`);
      out.push('      { "credits": 19.43, "originalCredits": 50.51, "model": "Qwen3.8-Flash", "durationMin": 28 }');
    }
    if (m) {
      out.push(line);
      out.push('  官方 UI 真值（手工录入，已与本地并列，未覆盖任何本地数字）：');
      out.push(
        `    Credits ${dash(m.credits)}  (原价 ${dash(m.originalCredits)})` +
          `${m.durationMin != null ? `  ·  ${m.durationMin} min` : ''}${m.model ? `  ·  ${m.model}` : ''}`
      );
      if (m.note) out.push(`    备注：${m.note}`);
      out.push(
        `    本地对它的覆盖率：${m.localCoverage == null ? '—（本地无 usage）' : `${m.localCredits} / ${m.credits} = ${(m.localCoverage * 100).toFixed(1)}%`}`
      );
    }
    out.push(line);
    out.push('  以下计数不依赖 usage，仍为真值：');
    out.push(
      `    工具调用 ${t.toolCalls} 次（${avail(av, 'toolCalls')}）  ·  文件读取 ${t.fileReads} 次（${avail(av, 'fileReads')}）  ·  用户轮 ${s.turns}（${avail(av, 'userTurns')}）`
    );
    const tools = report.byTool.filter((r) => r.calls > 0).sort((a, b) => b.calls - a.calls);
    if (tools.length > 0) {
      out.push(line);
      out.push('  按工具调用次数：');
      for (const row of tools.slice(0, 10)) {
        out.push(`    ${String(row.calls).padStart(5)} 次  ${row.tool}`);
      }
    }
    const files = report.byFile.filter((r) => r.reads > 0).sort((a, b) => b.reads - a.reads);
    if (files.length > 0) {
      out.push(line);
      out.push('  按文件读取次数：');
      for (const row of files.slice(0, 10)) {
        out.push(`    读 ${String(row.reads).padStart(4)} 次  [${row.kind}] ${row.label}`);
      }
    }
    out.push(line);
    out.push(`  转录： ${transcript}`);
    console.log(out.join('\n'));
    return;
  }

  // —— 有 usage：完整榜。转录路径 token 为推导值（ratio×窗口，usage 的 token 子字段恒 0）标「推导」；
  //    代理路径为提供商实测 prompt_tokens，标「实测」。——
  const cwText = av.contextWindow === 'fallback' ? `≈${humanTokens(c.contextWindow)}（回退值）` : humanTokens(c.contextWindow);
  const tokensMeasured = av.tokens === 'measured';
  out.push(
    tokensMeasured
      ? `  计费输入总量   ${humanTokens(t.billedInputTokens)} tokens 实测   (Σ prompt_tokens，代理记录)`
      : `  计费输入总量   ${humanTokens(t.billedInputTokens)} tokens 推导   (Σ context_usage_ratio 实测 × ${cwText})`
  );
  if (av.outputTokens === 'measured') {
    out.push(`  输出总量       ${humanTokens(t.outputTokens)} tokens 实测   (Σ completion_tokens，代理记录)`);
  }
  if (av.cachedTokens === 'measured') {
    out.push(
      `  其中缓存命中   ${humanTokens(t.cachedTokens)} tokens 实测   (${pct(t.cachedShare)}，${t.cachedTrips} 笔往返带缓存；供应商对重复前缀打折，故按 token 的节省大于按计费的节省)`
    );
  }
  // —— 当前占用（头条）：以「最新上下文对用户压缩阈值」的占比为准，附来源标注与「该不该压」结论。
  //    段内上下文单调递增 ⇒ 旧版「峰值」与「当前」恒等（43.4%=43.4%），故合并为一条，峰值仅在跨压缩
  //    历史高点明显更高时才作灰字单列。——
  const limitSrcLabel =
    c.userContextLimitSource === 'manual' ? '手工'
    : c.userContextLimitSource === 'config' ? '配置'
    : c.userContextLimitSource === 'derived' ? '实测反推'
    : '默认';
  const curCtx = c.currentContextTokens != null ? c.currentContextTokens : t.netContextTokens;
  const netAdvice = c.netUserAdvice || c.peakUserAdvice || c.peakAdvice;
  out.push(`  你真实的上下文 ${humanTokens(curCtx)} tokens`);
  if (netAdvice && c.userContextLimit != null) {
    out.push(`                 ├ 真实占用 ${pct(c.netUserRatio ?? 0)}（${humanTokens(curCtx)} / 你实设的 ${humanTokens(c.userContextLimit)}・${limitSrcLabel}）：${netAdvice.text}`);
  }
  // 第二条：Qoder 界面进度条按模型物理窗口显示——揭穿它系统性偏低（仅窗口>实设上限时报偏低+倍数；相等则标无偏差，不误报）
  if (c.userContextLimit != null && Number.isFinite(c.contextWindow) && c.contextWindow > c.userContextLimit) {
    const mult = (c.contextWindow / c.userContextLimit).toFixed(1);
    out.push(`                 └ ⚠ Qoder 界面进度条只显示 ${pct(c.netWindowRatio ?? c.peakContextRatio)}（按物理窗口 ${cwText} 算，非你实设的 ${humanTokens(c.userContextLimit)}）；真实约为显示的 ${mult} 倍，系统性偏低、别信它，该不该压以上面为准`);
  } else if (c.userContextLimit != null) {
    out.push(`                 └ Qoder 界面进度条按 ${cwText} 显示 ${pct(c.netWindowRatio ?? c.peakContextRatio)}（与你实设上限一致，无偏差）`);
  } else {
    out.push(`                 └ 对模型窗口 ${pct(c.netWindowRatio ?? c.peakContextRatio)}（${humanTokens(curCtx)} / ${cwText}）`);
  }
  // 阈值来源为「默认」⇒ 这个 200K 是内置兜底、非用户在 Qoder 的真实设置，显式告知如何改成真实值。
  if (c.userContextLimit != null && limitSrcLabel === '默认') {
    out.push(`                 · ⚙ 阈值 ${humanTokens(c.userContextLimit)} 是内置默认值，非你在 Qoder 设的真实上限（插件读不到）；要按真实阈值算：config.json 填 "userContextLimit": <上限>（全局）或 overrides/<会话id>.json 填同名字段（单场），重跑生效`);
  }
  if (c.thresholdNotEnforced) {
    const autoAt = Number.isFinite(c.contextWindow) ? humanTokens(Math.round(c.contextWindow * 0.85)) : '—';
    // 单独成块、空行隔开、⚠⚠ 标记：这是整份报告最重要的提示（用户设的阈值根本不会触发自动压缩），不能淹没在缩进行里。
    out.push('');
    out.push('  ⚠⚠ 重要：自动压缩不会在你设的阈值触发 ⚠⚠');
    out.push(`     模型窗口 ${cwText} → Qoder 要涨到窗口 ~85%（≈${autoAt}）才会自动压缩；`);
    out.push(`     你设的 ${humanTokens(c.userContextLimit)} 阈值远在其下，永远不会自动触发。请照上面「你真实的上下文」那条，到点自己手动压。`);
  }
  if (c.observedAutoCompactions > 0 && c.observedAutoTriggerTokens != null) {
    out.push(`                 · 本场 Qoder 实际自动压缩 ${c.observedAutoCompactions} 次，触发点在 ~${humanTokens(c.observedAutoTriggerTokens)}（窗口的 ${pct(c.autoTriggerRatio ?? 0)}）`);
  } else if (report.session.compactions > 0) {
    out.push('                 · 本场压缩均为你手动触发（未见自动压缩）');
  }
  if (c.peakSessionNotable) {
    out.push(`                 · 压缩前本场历史高点曾达 ${humanTokens(c.peakSessionTokens)} (${pct(c.peakSessionRatio)})`);
  }
  out.push(`  重发放大       ${t.amplification}×     系统提示词 ${humanTokens(c.systemPromptTokens)}/请求 推导`);
  const cov = report.creditsCoverage;
  const covNote =
    cov && !cov.full && cov.roundTrips > 0
      ? `   ← 仅覆盖 ${cov.trips}/${cov.roundTrips} 笔往返（占计费输入 ${pct(cov.tokenShare)}），别拿它除以计费输入总量算单价`
      : '';
  out.push(
    av.credits === 'unavailable'
      ? report.usageSource === 'proxy'
        ? '  Credits        —（自定义模型不经 Qoder 计费，无本地真值；可走 overrides 回填外部账单）'
        : hasUsage
          ? '  Credits        —（转录带 usage 但没有 credits 字段，本地无计费真值；可走 overrides 回填外部账单）'
          : '  Credits        —（本地不可用；可走 overrides 回填外部账单）'
      : `  Credits        ${t.credits} 实测  (原始 ${t.originalCredits})${covNote}`
  );
  if (m) {
    // 官方 UI 的一场会话扣费 = 主链 + 子代理，故有子代理时覆盖率拿 combined 算，否则会被低估。
    const scopeZh = m.localScope === 'combined' ? '合计（主链+子代理）' : '主链';
    out.push(
      `  官方 UI 真值   ${dash(m.credits)} 手工  (原始 ${dash(m.originalCredits)})` +
        `   本地${scopeZh} ${dash(m.localCredits)}，覆盖率 ${m.localCoverage == null ? '—' : (m.localCoverage * 100).toFixed(1) + '%'}`
    );
  }
  const a1 = report.identity.ok === null ? '— 不适用' : report.identity.ok ? '✓ 通过' : '✗ 失败';
  out.push(`  归因覆盖       ${pct(t.coverage)} 推导   恒等式 A1 ${a1} (|Δ|=${report.identity.absDiff})`);
  const sub = report.subagents;
  if (sub && sub.count > 0) {
    out.push(line);
    out.push(`  子代理账（${sub.count} 个，以下数字均不计入上方主链）：`);
    for (const a of sub.items) {
      out.push(
        `    ${String(a.roundTrips).padStart(4)} 次  ${humanTokens(a.billedInputTokens).padStart(8)}  ${String(a.credits).padStart(8)} Cr  峰值 ${pct(a.peakContextRatio).padStart(6)}  [${a.agentType || '?'}] ${a.description || a.agentId}${a.error ? `  ← ${a.error}` : ''}`
      );
    }
    out.push(
      `    合计（主链 + 子代理）  ${sub.combined.roundTrips} 次  ${humanTokens(sub.combined.billedInputTokens)}  ${sub.combined.credits} Cr  (原始 ${sub.combined.originalCredits})`
    );
  } else if (sub && sub.reason && sub.reason !== 'no-dir') {
    out.push(`  子代理账       未汇总（${sub.reason}）`);
  }
  const cc = report.compactionCost;
  if (cc && cc.items.length > 0 && av.compactionCost !== 'unavailable') {
    out.push(line);
    out.push('  压缩单笔成本（每次压缩 = 整份上下文当 prompt、摘要当 completion 的一笔调用）：');
    for (const e of cc.items) {
      const px = e.proxy || null;
      out.push(
        `    #${e.index}  ${hm(e.at)}  ${String(e.trigger || '—').padEnd(6)}` +
          `  输入 ${e.effectiveInputTokens == null ? '—' : humanTokens(e.effectiveInputTokens)}` +
          ` → 摘要 ${e.effectiveOutputTokens == null ? '—' : humanTokens(e.effectiveOutputTokens)}` +
          ` → 压缩后首轮 ${e.nextInputTokens == null ? '—' : humanTokens(e.nextInputTokens)}` +
          `  省 ${e.savedTokens == null ? '—' : humanTokens(e.savedTokens)}` +
          `${px && px.ms != null ? `  耗时 ${Math.round(px.ms / 1000)}s` : ''}` +
          `  [${px ? '实测' : '自估'}]`
      );
    }
    out.push(
      `    合计：输入 ${humanTokens(cc.totals.preTokens)} · 摘要 ${humanTokens(cc.totals.postTokens)} · 省下 ${humanTokens(cc.totals.savedTokens)} · 其中 ${cc.totals.measured || 0} 笔为供应商实测`
    );
  }
  out.push(line);
  out.push('  按类别占比（推导）：');
  for (const row of report.byCategory) {
    out.push(`    ${bar(row.share)} ${pct(row.share).padStart(6)}  ${humanTokens(row.tokens).padStart(8)}  ${row.label}`);
  }
  out.push(line);
  out.push('  按工具占比（推导；次数为实测；单次 = 平均每次调用的重发 token）：');
  for (const row of report.byTool.slice(0, 10)) {
    out.push(
      `    ${bar(row.share)} ${pct(row.share).padStart(6)}  ${humanTokens(row.tokens).padStart(8)}  ${row.tool} (${row.calls} 次，单次 ${row.perCall == null ? '—' : humanTokens(row.perCall)})`
    );
  }
  out.push(line);
  out.push(`  按文件占比 Top ${Math.min(15, report.byFile.length)}（推导；单次 = 平均每次读取最终烧掉多少）：`);
  for (const row of report.byFile.slice(0, 15)) {
    out.push(
      `    ${bar(row.share)} ${pct(row.share).padStart(6)}  ${humanTokens(row.billed).padStart(8)}  ×${String(row.trips).padStart(4)}程  单次 ${row.perRead == null ? '—' : humanTokens(row.perRead).padStart(7)}  [${row.kind}] ${row.label}`
    );
  }
  const lh = report.linkHealth;
  if (lh && ((report.proxy && report.proxy.configured) || lh.matched > 0)) {
    out.push(line);
    out.push(
      `  链路健康度     代理覆盖 ${lh.matched}/${lh.requests} 笔往返 (${pct(lh.coverage)})` +
        `  ·  最近记录 ${hm(lh.lastRecordAt)}` +
        (lh.recentRequests
          ? `  ·  最近 ${lh.recentRequests} 笔：代理失败 ${lh.proxyErrors} / 上游报错 ${lh.upstreamRejected} / 客户端断开 ${lh.aborted} / 无 usage ${lh.noUsage}`
          : '  ·  请求诊断日志为空（代理是旧版或还没记到）')
    );
    if (lh.breakdown) {
      out.push(
        `                 └ 拆分：代理 ${lh.breakdown.proxy} 笔 · 转录 input_tokens ${lh.breakdown.transcriptTokens} 笔 · 转录 ratio×窗口 ${lh.breakdown.transcriptRatio} 笔`
      );
    }
    if (lh.supersededFailure) {
      out.push(
        `                 ${hm(lh.supersededFailure.at)} 那条「拉起失败（${lh.supersededFailure.error}）」已被之后的流量推翻，无需处理`
      );
    }
  }
  out.push(line);
  out.push(`  转录： ${transcript}`);
  console.log(out.join('\n'));
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  if (args.setupProxy) return setupProxy(args);
  if (args.checkProxy) return checkProxy();
  if (args.stopProxy) return stopProxyCmd();
  if (args.dumpRequests) return requestLogCmd(args);
  const { transcript, sessionId, cwd } = resolveTranscript(args);
  if (!transcript) {
    console.error('未找到可用转录。请用 --transcript <path> 指定，或确认 ~/.qoder-cn/projects 下存在富转录。');
    process.exit(2);
  }
  const { report, outDir: usedDir, reportJson, canvas } = generateReport({
    transcript,
    sessionId,
    cwd: args.cwd || cwd,
    outDir: args.out,
    overridesDir: args.overrides,
    proxyLog: args.proxyLog,
    canvas: args.canvas,
  });
  if (args.json) {
    console.log(JSON.stringify(report, null, 2));
  } else {
    printTerminal(report, transcript, usedDir || path.dirname(reportJson));
    console.log(`  已写入 report.json → ${reportJson}`);
    if (canvas) console.log(`  已渲染 Canvas → ${canvas}`);
  }
}

// 仅作为脚本直接运行时执行 main（被 import 时不自动跑）。
if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  main().catch((err) => {
    console.error(err);
    process.exit(1);
  });
}

export { main };
