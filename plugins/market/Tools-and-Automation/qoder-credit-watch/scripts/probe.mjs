import { readFileSync, appendFileSync, existsSync, mkdirSync } from 'node:fs';
import { spawn } from 'node:child_process';
import os from 'node:os';
import path from 'node:path';

const CONFIG = process.argv[2] && !process.argv[2].startsWith('--')
  ? process.argv[2]
  : path.join(os.homedir(), '.qoder-cn', 'credit-watch', 'accounts.json');
const HISTORY = path.join(os.homedir(), '.qoder-cn', 'credit-watch', 'history.jsonl');
const HEADLESS = process.argv.includes('--headless');
// --ids prints port -> userId/name/tier only, writes nothing: used to register accounts
// that live in an Edge profile the in-app browser cannot reach.
const IDS = process.argv.includes('--ids');
// --scan only reports "which ports hold a logged-in session" for the dashboard's
// register wizard: no collection, no history write, no window launching.
const SCAN = process.argv.includes('--scan');

if (!existsSync(CONFIG)) {
  console.error(`找不到配置文件：${CONFIG}`);
  console.error('先运行 /credit-start 登记账号（从已登录的网页会话读取真实 userId），或手动复制');
  console.error(`插件内 config/accounts.example.json 到上述路径后再试。`);
  process.exit(1);
}

const cfg = JSON.parse(readFileSync(CONFIG, 'utf8'));
const ports = cfg.probePorts || [9222, 9223, 9224];
// 登记向导要能发现"名单之外的新槽位"，所以扫描范围在 probePorts 之上再探 3 个连续端口。
const SCAN_PORTS = [...new Set([...ports, ...Array.from({ length: 3 }, (_, k) => Math.max(...ports) + 1 + k)])];
const threshold = cfg.threshold ?? 200;
const EDGE = ['C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe',
  'C:\\Program Files\\Microsoft\\Edge\\Application\\msedge.exe'].find((p) => existsSync(p));
const BASE = path.join(process.env.LOCALAPPDATA || os.homedir(), 'QoderMultiAccount');

const EXPR = `(async () => {
  const j = async (p) => (await (await fetch(p, { credentials: 'include' })).json());
  const me = await j('/api/v1/me');
  const u = await j('/api/v2/me/usages/big_model_credits');
  const p = await j('/api/v1/me/userplan');
  const s = (q) => (q && q.quota_summary) || {};
  const a = s(u.plan_quota), b = s(u.resource_package_quota);
  return JSON.stringify({
    userId: me.id, name: me.name, tier: p.plan_tier, nextRefresh: p.next_refresh_date,
    planRem: a.remaining_value, packRem: b.remaining_value,
    packs: ((u.resource_package_quota || {}).quota_detail || []).map((d) => ({
      rem: d.remaining_value, exp: d.expires_at, src: d.source
    }))
  });
})()`;

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const getJson = async (url, ms = 2000) =>
  (await fetch(url, { signal: AbortSignal.timeout(ms) })).json();

function cdp(wsUrl, method, params, timeoutMs) {
  return new Promise((resolve, reject) => {
    const ws = new WebSocket(wsUrl);
    const timer = setTimeout(() => { ws.close(); reject(new Error(`CDP ${method} 超时`)); }, timeoutMs);
    ws.onopen = () => ws.send(JSON.stringify({ id: 1, method, params }));
    ws.onmessage = (ev) => {
      const msg = JSON.parse(ev.data);
      if (msg.id !== 1) return;
      clearTimeout(timer);
      ws.close();
      if (msg.error) return reject(new Error(msg.error.message));
      resolve(msg.result);
    };
    ws.onerror = () => { clearTimeout(timer); ws.close(); reject(new Error('CDP WebSocket 失败')); };
  });
}

function launch(port, dir) {
  mkdirSync(dir, { recursive: true });
  const args = [`--user-data-dir=${dir}`, `--remote-debugging-port=${port}`,
    '--no-first-run', '--no-default-browser-check',
    ...(HEADLESS ? ['--headless=new'] : []), 'https://qoder.com.cn/account/usage'];
  const child = spawn(EDGE, args, { detached: true, stdio: 'ignore' });
  child.unref();
}

async function waitQoderPage(port, ms) {
  const deadline = Date.now() + ms;
  while (Date.now() < deadline) {
    try {
      const list = await getJson(`http://127.0.0.1:${port}/json/list`, 1500);
      const page = list.find((t) => t.type === 'page' && t.url.startsWith('https://qoder.com.cn'));
      if (page) return page;
    } catch { /* 端口还没起 */ }
    await sleep(700);
  }
  return null;
}

// 只认「可解析且带 userId 的字符串」：刚拉起的 Profile 里页面可能还没就绪，
// 同源 fetch 会返回别的东西，重试比误判成"登录失效"诚实。
async function readIdentity(page, tries = 4) {
  for (let attempt = 0; attempt < tries; attempt++) {
    if (attempt) await sleep(2000);
    const res = await cdp(page.webSocketDebuggerUrl, 'Runtime.evaluate',
      { expression: EXPR, awaitPromise: true, returnByValue: true }, 25000);
    const v = res?.result?.value;
    if (typeof v !== 'string') continue;
    try {
      const parsed = JSON.parse(v);
      if (parsed && parsed.userId) return parsed;
    } catch { /* 页面未就绪，下一轮重试 */ }
  }
  return null;
}

const day = (ms) => (ms ? new Date(ms).toLocaleDateString('sv-SE', { timeZone: 'Asia/Shanghai' }) : '—');

if (SCAN) {
  const sessions = [];
  for (const port of SCAN_PORTS) {
    try {
      await getJson(`http://127.0.0.1:${port}/json/version`, 700);
    } catch { continue; }                     // 这个槽位没有窗口，别浪费时间
    const page = await waitQoderPage(port, 1500);
    if (!page) { sessions.push({ port, loggedIn: false, reason: 'no-page' }); continue; }
    const d = await readIdentity(page, 2);
    if (!d) { sessions.push({ port, loggedIn: false, reason: 'not-logged-in' }); continue; }
    const hit = (cfg.accounts || []).find((x) => x.userId === d.userId);
    sessions.push({
      port,
      loggedIn: true,
      userId: d.userId,
      name: d.name,
      tier: String(d.tier || '').replace('PLAN_TIER_', ''),
      registered: !!hit,
      label: hit ? hit.label : null,
      totalRemaining: (d.planRem || 0) + (d.packRem || 0),
    });
  }
  // 一行 JSON 给本机服务；userId 留在服务端持有，页面只拿端口当凭据。
  console.log(JSON.stringify({ cw: 'credit-watch-scan', probePorts: ports, sessions }));
  process.exit(0);
}

const owned = [];
if (EDGE) {
  for (const [i, port] of ports.entries()) {
    const up = await waitQoderPage(port, 800);
    if (!up) {
      launch(port, path.join(BASE, `p${i + 1}`));
      owned.push(port);
    }
  }
}

const rows = [];
for (const [i, port] of ports.entries()) {
  try {
    if (!EDGE && owned.length === 0) throw new Error('未找到 Edge');
    const page = await waitQoderPage(port, owned.includes(port) ? 25000 : 3000);
    if (!page) throw new Error('没有 qoder.com.cn 页面');
    const d = await readIdentity(page);
    if (!d) throw new Error('取值失败：页面未就绪或登录态可能已失效，需在该 Profile 窗口重新登录');
    const hit = (cfg.accounts || []).find((x) => x.userId === d.userId);
    const total = (d.planRem || 0) + (d.packRem || 0);
    const live = (d.packs || []).filter((p) => p.rem > 0 && p.exp > 0).sort((x, y) => x.exp - y.exp);
    const label = hit ? hit.label : `未登记(${d.name})`;
    const tier = String(d.tier).replace('PLAN_TIER_', '');
    const expiry = live.length ? day(live[0].exp) : '—';
    const refresh = day(d.nextRefresh);
    if (IDS) {
      rows.push({ label, port, userId: d.userId, name: d.name, tier });
      console.error(`[cw-progress] ${rows.length}/${ports.length} ${label} 已识别`);
      continue;
    }
    rows.push({ label, tier, total, expiry, refresh });
    console.error(`[cw-progress] ${rows.length}/${ports.length} ${label} 剩余 ${total}`);
    try {
      mkdirSync(path.dirname(HISTORY), { recursive: true });
      appendFileSync(HISTORY, JSON.stringify({
        ts: new Date().toISOString(), via: HEADLESS ? 'probe-headless' : 'probe-headed',
        userId: d.userId, label, planTier: tier, debugPort: port,
        planRemaining: d.planRem, packRemaining: d.packRem, totalRemaining: total,
        earliestExpiry: expiry, nextRefresh: refresh,
        // 逐包明细（只有余额的包）：每个资源包到期时间不同，看板要能分行展示
        packs: (d.packs || []).filter((p) => (p.rem || 0) > 0)
          .map((p) => ({ remaining: p.rem, expires: day(p.exp), source: p.src || '' }))
      }) + '\n');
    } catch (e) {
      console.error(`历史写入失败（不影响本次结果）：${e?.message || e}`);
    }
  } catch (e) {
    rows.push({ label: `端口 ${port}`, error: String(e?.message || e) });
    console.error(`[cw-progress] ${rows.length}/${ports.length} 端口 ${port} 失败：${String(e?.message || e)}`);
  }
}

for (const port of owned) {
  try {
    const v = await getJson(`http://127.0.0.1:${port}/json/version`, 2000);
    await cdp(v.webSocketDebuggerUrl, 'Browser.close', {}, 4000);
  } catch { /* 已经关了 */ }
}

const width = (s) => String(s).replace(/[^\x00-\xff]/g, 'xx').length;
const pad = (s, n) => String(s) + ' '.repeat(Math.max(1, n - width(s)));

if (IDS) {
  console.log(pad('端口', 8) + pad('userId', 38) + pad('登录名', 22) + pad('套餐', 12) + '登记状态');
  for (const r of rows) {
    if (r.error) { console.log(pad(r.label, 8) + '读取失败：' + r.error); continue; }
    console.log(pad(r.port, 8) + pad(r.userId, 38) + pad(r.name, 22) + pad(r.tier, 12) + r.label);
  }
  console.log(`\n共 ${rows.filter((r) => !r.error).length}/${ports.length} 个 Profile 有活动会话。`
    + '把未登记的 userId 交给 /credit-start 即可加入名单。本模式不查余量、不写历史。');
  process.exit(0);
}

console.log(pad('账号', 16) + pad('套餐', 12) + pad('合计剩余', 12) + pad('最近到期', 14) + '状态');
for (const r of rows) {
  if (r.error) { console.log(pad(r.label, 16) + '读取失败：' + r.error); continue; }
  console.log(pad(r.label, 16) + pad(r.tier, 12) + pad(r.total, 12) + pad(r.expiry, 14)
    + (r.total <= threshold ? `⚠ 低于阈值 ${threshold}` : '✓'));
}
const ok = rows.filter((r) => !r.error).length;
console.log(`\n覆盖 ${ok}/${ports.length} · 阈值 ${threshold} · 模式 ${HEADLESS ? 'headless' : 'headed'}`
  + (owned.length ? ` · 本次自动开启并已关闭端口 ${owned.join('/')}` : ' · 复用已在运行的 Profile'));
