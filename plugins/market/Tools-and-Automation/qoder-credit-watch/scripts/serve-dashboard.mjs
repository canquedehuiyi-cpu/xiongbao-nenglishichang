// serve-dashboard.mjs — 本地预览 + 真触发接口。
// 只绑 127.0.0.1，默认端口 49788（--port 可改），启动时生成一次性令牌注入进页面；写操作必须带令牌，
// 且 Host/Origin 必须是本服务自身，避免本机其它网页拿它当跳板去拉起浏览器。
// 写接口只允许"跑哪几个既有启动器"和"改 accounts.json 的哪几个白名单字段"，
// 不接受任意命令、任意文件路径。
// 用法：node scripts/serve-dashboard.mjs [--site <静态站目录>] [--port <端口>]
import { createServer } from "node:http";
import { spawn } from "node:child_process";
import { readFile, stat, writeFile, copyFile, rename, unlink } from "node:fs/promises";
import { randomBytes } from "node:crypto";
import { extname, join, normalize, resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";
import { existsSync, mkdirSync } from "node:fs";
import { homedir } from "node:os";

const HERE = dirname(fileURLToPath(import.meta.url));
const PLUGIN_ROOT = resolve(HERE, "..");
const arg = (name, fallback = null) => {
  const i = process.argv.indexOf(`--${name}`);
  return i >= 0 && process.argv[i + 1] ? process.argv[i + 1] : fallback;
};

const ROOT = resolve(arg("site", join(PLUGIN_ROOT, "dashboard", "site")));
const CLI_PORT = arg("port", null);        // 命令行 --port 优先级最高
let WANT_PORT = 49788;                      // 实际启动端口在 listen 前解析：--port > accounts.json.port > 49788
let RUNNING_PORT = 0;                       // 真正绑定成功的端口，回给页面显示“当前运行端口”
const TOKEN = randomBytes(16).toString("hex");
const IS_WIN = process.platform === "win32";
// 采集与“开登录窗口”都已在 Node 里跑，不再套 .cmd 启动器：
// probe / build-site-data 用 process.execPath 直跑；开 Edge 窗口用下面的 openProfileWindow
// 直接 spawn（与 probe.mjs 里的启动逻辑同源，pN ↔ 调试端口 9221+N）。
const PROBE = join(PLUGIN_ROOT, "scripts", "probe.mjs");
const EDGE = ["C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe",
  "C:\\Program Files\\Microsoft\\Edge\\Application\\msedge.exe"].find((p) => existsSync(p));
const PROFILE_BASE = join(process.env.LOCALAPPDATA || homedir(), "QoderMultiAccount");
const openProfileWindow = (index) => {
  const n = Number(index);
  if (!Number.isInteger(n) || n < 1 || n > 20) throw new Error(`非法 Profile 序号 ${index}`);
  const dir = join(PROFILE_BASE, `p${n}`);
  mkdirSync(dir, { recursive: true });
  const child = spawn(EDGE, [
    `--user-data-dir=${dir}`, `--remote-debugging-port=${9221 + n}`,
    "--no-first-run", "--no-default-browser-check", "https://qoder.com.cn/account/usage",
  ], { detached: true, stdio: "ignore" });
  child.unref();
};

const types = {
  ".html": "text/html; charset=utf-8",
  ".css": "text/css; charset=utf-8",
  ".js": "text/javascript; charset=utf-8",
  ".json": "application/json; charset=utf-8",
  ".svg": "image/svg+xml",
};

const job = { running: false, kind: null, phase: "idle", lines: [], done: 0, total: 0, error: null, startedAt: null };

const reset = (kind, total) => {
  job.running = true;
  job.kind = kind;
  job.phase = "running";
  job.lines = [];
  job.done = 0;
  job.total = total;
  job.error = null;
  job.startedAt = new Date().toISOString();
};

const note = (line) => {
  job.lines.push(line);
  if (job.lines.length > 60) job.lines.shift();
};

// 采集脚本把进度打在 stderr 上，stdout 的汇总表保持原样不动。
const PROGRESS = /^\[cw-progress\]\s+(\d+)\/(\d+)\s+(.*)$/;
// 转换器给"完成"准备的一句短提示（比"已写出 <长路径>"适合放在页面上）。
const SUMMARY = /^\[cw-summary\]\s+(.*)$/;
const pickSummary = (stdout) => {
  const hit = (stdout || "").split("\n").map((l) => l.trim()).find((l) => SUMMARY.test(l));
  return hit ? SUMMARY.exec(hit)[1] : null;
};

function run(cmd, args, opts = {}) {
  return new Promise((resolvePromise) => {
    const inner = `"${cmd}" ${args.map((a) => (/\s/.test(a) ? `"${a}"` : a)).join(" ")}`;
    // cmd /s /c 要求整条命令再套一层引号，否则带空格的路径会被从中间截断。
    // detach 用于会派生浏览器的启动器：子进程会继承 stdout 管道，不接管道 close 事件就永远不来。
    const child = IS_WIN
      ? spawn("cmd.exe", ["/d", "/s", "/c", `"${inner}"`], {
          windowsVerbatimArguments: true,
          ...(opts.detach ? { stdio: "ignore" } : {}),
        })
      : spawn(cmd, args, opts.detach ? { stdio: "ignore" } : {});
    if (opts.detach) {
      child.on("close", (code) => resolvePromise({ code, stdout: "", stderr: "" }));
      child.on("error", (e) => resolvePromise({ code: -1, stdout: "", stderr: String(e?.message || e) }));
      return;
    }
    let stdout = "";
    let stderr = "";
    child.stdout.on("data", (b) => { stdout += b.toString(); });
    child.stderr.on("data", (b) => {
      const text = b.toString();
      stderr += text;
      for (const line of text.split("\n")) {
        const hit = PROGRESS.exec(line.trim());
        if (hit) {
          job.done = Number(hit[1]);
          job.total = Number(hit[2]);
          note(hit[3]);
        } else if (line.trim()) {
          note(line.trim());
        }
      }
    });
    child.on("close", (code) => resolvePromise({ code, stdout, stderr }));
    child.on("error", (e) => resolvePromise({ code: -1, stdout, stderr: String(e?.message || e) }));
  });
}

// 账号配置与看板数据都在插件目录之外：升级、重装、打包都不会把它们带出去。
const DATA_DIR = join(homedir(), ".qoder-cn", "credit-watch");
const CFG_FILE = join(DATA_DIR, "accounts.json");
const SITE_DATA = resolve(join(ROOT, "data", "credits.json"));
const LIVE_DATA = resolve(join(DATA_DIR, "credits.json"));
const DEFAULT_PORTS = [9222, 9223, 9224];

async function loadCfg() {
  return JSON.parse(await readFile(CFG_FILE, "utf8"));
}

async function probeCount() {
  try {
    const cfg = await loadCfg();
    return (cfg.probePorts || DEFAULT_PORTS).length;
  } catch {
    return 3;
  }
}

async function refresh(headless) {
  const total = await probeCount();
  reset("refresh", total);
  if (!existsSync(PROBE)) {
    job.running = false;
    job.phase = "failed";
    job.error = `找不到采集脚本 ${PROBE}`;
    return;
  }
  const probe = await run(process.execPath, [PROBE, ...(headless ? ["--headless"] : [])]);
  if (probe.code !== 0) {
    job.phase = "failed";
    job.error = `采集脚本退出码 ${probe.code}：${(probe.stderr || probe.stdout).slice(-300)}`;
  }
  await rebuild(true);
  if (probe.code === 0) job.phase = "done";
  job.running = false;
}

async function rebuild(silent) {
  if (!silent) reset("rebuild", 1);
  note("重算看板数据…");
  // 真实数据只写插件外那一份；插件内的 credits.json 永远是随包发出去的样例。
  const res = await run(process.execPath, [join(PLUGIN_ROOT, "scripts", "build-site-data.mjs"), "--out", LIVE_DATA]);
  if (res.code !== 0) {
    job.phase = "failed";
    job.error = `数据转换失败（退出码 ${res.code}）：${(res.stderr || res.stdout).slice(-300)}`;
  } else {
    note(pickSummary(res.stdout) || res.stdout.trim().split("\n")[0] || "数据已更新");
    if (!silent) job.phase = "done";
  }
  if (!silent) job.running = false;
}

const LIMITS = { label: 24, accountName: 40 };
// 控制字符一律拒收，不做"悄悄帮你改掉"——文案里承诺的是"不含换行"，行为就得跟它一致。
const oneLine = (v, max) => {
  if (typeof v !== "string") return null;
  if (/[\u0000-\u001f\u007f]/.test(v)) return null;
  const s = v.replace(/\s{2,}/g, " ").trim();
  return s.length >= 1 && s.length <= max ? s : null;
};

/* 名单只有一份、只认这一个路径；写之前先把上一份留成 .bak。 */
const writeCfg = async (next) => {
  const tmp = `${CFG_FILE}.tmp`;
  try {
    await writeFile(tmp, `${JSON.stringify(next, null, 2)}\n`, "utf8");
    if (existsSync(CFG_FILE)) await copyFile(CFG_FILE, `${CFG_FILE}.bak`);
    await rename(tmp, CFG_FILE);
    return null;
  } catch (e) {
    await unlink(tmp).catch(() => {});
    return `写入 accounts.json 失败：${e?.message || e}`;
  }
};

/* 只改 accounts.json 里白名单字段的值：全局只认 threshold / port，每个账号只认 label / accountName；
   userId、probePorts 等一律原样带过去。任一条目不合法就整份不写——不做部分成功。 */
async function saveSettings(body) {
  let cfg;
  try {
    cfg = await loadCfg();
  } catch {
    return { errors: [`读不到账号配置 ${CFG_FILE}，先用 /credit-start 登记账号`] };
  }
  if (!cfg || !Array.isArray(cfg.accounts)) return { errors: ["账号配置里没有 accounts 名单"] };

  const next = JSON.parse(JSON.stringify(cfg));
  const changes = [];
  const errors = [];

  if (body.threshold !== undefined && body.threshold !== null && body.threshold !== "") {
    const t = Number(body.threshold);
    if (!Number.isInteger(t) || t < 0 || t > 1e7) errors.push("告警阈值要取 0–10000000 之间的整数");
    else if (t !== Number(next.threshold)) {
      changes.push(`告警阈值 ${next.threshold} → ${t}`);
      next.threshold = t;
    }
  }

  // 默认启动端口：写进配置，只影响下次启动；当前进程仍跑在 RUNNING_PORT 上，不改绑。
  if (body.port !== undefined && body.port !== null && body.port !== "") {
    const p = Number(body.port);
    if (!Number.isInteger(p) || p < 1024 || p > 65535) errors.push("端口要取 1024–65535 之间的整数");
    else if (p !== Number(next.port)) {
      changes.push(`默认启动端口 ${next.port ?? "（未设，暂用 49788）"} → ${p}（下次启动生效，当前仍在 ${RUNNING_PORT}）`);
      next.port = p;
    }
  }

  const byLabel = new Map(next.accounts.map((a) => [String(a.label), a]));
  const items = Array.isArray(body.accounts) ? body.accounts.slice(0, 50) : [];
  for (const item of items) {
    const label = oneLine(item.label, LIMITS.label);
    const target = label && byLabel.get(label);
    if (!target) {
      errors.push(`名单里没有账号「${label || "（空标签）"}」，请刷新页面后再改`);
      continue;
    }
    const want = item.newLabel ?? item.label;
    if (want !== undefined && want !== target.label) {
      const nl = oneLine(want, LIMITS.label);
      if (!nl) errors.push(`「${target.label}」的新标签要是 1–${LIMITS.label} 个字符、不含换行`);
      else if (byLabel.has(nl)) errors.push(`标签「${nl}」已被另一个账号占用`);
      else {
        changes.push(`标签 ${target.label} → ${nl}`);
        byLabel.delete(target.label);
        target.label = nl;
        byLabel.set(nl, target);
      }
    }
    if (item.accountName !== undefined && item.accountName !== target.accountName) {
      const an = oneLine(item.accountName, LIMITS.accountName);
      if (!an) errors.push(`「${target.label}」的账号名称要是 1–${LIMITS.accountName} 个字符、不含换行`);
      else {
        changes.push(`${target.label} 的账号名称 → ${an}`);
        target.accountName = an;
      }
    }
  }

  if (errors.length) return { errors };
  if (!changes.length) return { changes, rebuilt: false };

  const fail = await writeCfg(next);
  if (fail) return { errors: [fail] };
  reset("settings", 1);
  note(`配置已保存（上一份留成 accounts.json.bak）：${changes.join("；")}`);
  await rebuild(true);
  const rebuildError = job.phase === "failed" ? job.error : null;
  if (!rebuildError) job.phase = "done";
  job.running = false;
  return { changes, rebuilt: true, rebuildError };
}

// 窗口开出来不等于能采集：调试端口真在监听才算。Profile 已经有窗口开着时，
// 后发的 --remote-debugging-port 会被忽略，所以必须回查端口，不能报假成功。
async function portUp(port, ms) {
  const deadline = Date.now() + ms;
  while (Date.now() < deadline) {
    try {
      const res = await fetch(`http://127.0.0.1:${port}/json/version`, { signal: AbortSignal.timeout(1200) });
      if (res.ok) return true;
    } catch { /* 还没起来 */ }
    await new Promise((r) => setTimeout(r, 600));
  }
  return false;
}

async function openProfiles(body) {
  if (!EDGE) return { errors: ["未找到 Microsoft Edge，开不了登录窗口"] };
  let ports = DEFAULT_PORTS;
  try { ports = (await loadCfg()).probePorts || DEFAULT_PORTS; } catch { /* 用缺省端口 */ }
  const indices = [];
  const asked = body && body.port;
  let target = null;
  if (asked !== undefined && asked !== null && asked !== "") {
    const port = Number(asked);
    if (!Number.isInteger(port) || !ports.includes(port)) return { errors: [`端口 ${asked} 不在监控名单里`] };
    target = port;
    indices.push(ports.indexOf(port) + 1);
  } else {
    indices.push(...ports.map((_, i) => i + 1));
  }
  reset("profiles", 1);
  note(target === null ? "正在打开各账号的登录窗口…" : `正在打开端口 ${target} 的登录窗口…`);
  try {
    for (const n of indices) openProfileWindow(n);
  } catch (e) {
    job.phase = "failed";
    job.error = `开窗口失败：${e?.message || e}`;
    job.running = false;
    return { started: false };
  }
  const want = target === null ? ports : [target];
  const up = [];
  const waiting = [];
  for (const p of want) {
    if (await portUp(p, target === null ? 4000 : 9000)) up.push(p);
    else waiting.push(p);
  }
  if (waiting.length) {
    job.phase = "failed";
    job.error = `窗口开了，但端口 ${waiting.join("、")} 没在监听——那个 Profile 大概已经有窗口开着（不带调试端口）。把那个窗口整个关掉再点一次。`;
  } else {
    note(target === null ? "各账号的登录窗口已打开，请逐个完成登录" : "登录窗口已打开，请在里面完成该号的登录");
    job.phase = "done";
  }
  job.running = false;
  return { started: true, ports: up, waiting };
}

/* ---------------- 新增账号：开新窗口 → 用户登录 → 读会话 → 登记 ---------------- */

// userId 只在服务端这一侧待着：页面拿到的是端口号，登记时凭端口回查。
// 这样页面无法往名单里塞一个它自己编造的 userId。
const pendingIds = new Map();

// openProfileWindow 与 probe.mjs 同规则：pN ↔ 调试端口 9221+N；probe 又按 probePorts 下标开目录，
// 两边只有在"从 9222 起连续排"时才一致。自定义过端口段就如实拒绝，别开一扇对不上号的窗口。
const nextFreePort = (ports) => {
  if (!ports.length || ports.length >= 9) return null;
  for (let i = 0; i < ports.length; i++) if (ports[i] !== 9222 + i) return null;
  return 9222 + ports.length;
};

async function registerOpen() {
  let ports = DEFAULT_PORTS;
  try { ports = (await loadCfg()).probePorts || DEFAULT_PORTS; } catch { /* 用缺省端口 */ }
  const free = nextFreePort(ports);
  if (!free) {
    return { errors: ["端口段不是从 9222 起连续排的（或槽位已用满），这里开不了新窗口；请回 Qoder 用 /credit-start 登记"] };
  }
  if (!EDGE) {
    job.running = false;
    return { errors: ["未找到 Microsoft Edge，开不了新窗口"] };
  }
  reset("register-open", 1);
  note("正在开一个干净的浏览器窗口…");
  try {
    openProfileWindow(free - 9221);
  } catch (e) {
    job.phase = "failed";
    job.error = `开窗口失败：${e?.message || e}`;
    job.running = false;
    return { errors: [`开窗口失败：${e?.message || e}`] };
  }
  if (!(await portUp(free, 12000))) {
    job.phase = "failed";
    job.error = "窗口开了但没连上调试端口：把那个窗口整个关掉再点一次";
    job.running = false;
    return { errors: ["新窗口没起调试端口，读不到里面的登录态"] };
  }
  note("窗口已就绪，请在里面登录要新增的那个号");
  job.phase = "done";
  job.running = false;
  return { opened: free };
}

async function registerScan() {
  reset("register-scan", 1);
  note("正在读各窗口里的登录态…");
  const res = await run(process.execPath, [PROBE, "--scan"]);
  if (res.code !== 0) {
    job.phase = "failed";
    job.error = `读取失败（退出码 ${res.code}）：${(res.stderr || res.stdout).slice(-200)}`;
    job.running = false;
    return { errors: ["读不到窗口里的会话"] };
  }
  let parsed = null;
  for (const line of (res.stdout || "").split("\n")) {
    const t = line.trim();
    if (!t.startsWith("{")) continue;
    try { parsed = JSON.parse(t); } catch { /* 别的输出行 */ }
  }
  const sessions = Array.isArray(parsed?.sessions) ? parsed.sessions : null;
  if (!sessions) {
    job.phase = "failed";
    job.error = "读取结果解析不了（probe.mjs --scan 输出不是预期的一行 JSON）";
    job.running = false;
    return { errors: ["扫描结果异常"] };
  }
  pendingIds.clear();
  const list = [];
  const waiting = [];
  for (const s of sessions) {
    if (!s.loggedIn) { waiting.push(s.port); continue; }
    pendingIds.set(Number(s.port), { userId: s.userId, name: s.name, tier: s.tier });
    list.push({ port: s.port, name: s.name, tier: s.tier, registered: !!s.registered, label: s.label || null });
  }
  const fresh = list.filter((x) => !x.registered);
  note(fresh.length
    ? `读到 ${fresh.length} 个还没登记的号`
    : (waiting.length ? `${waiting.length} 个窗口还没登录` : "读到的号都已在名单里"));
  job.phase = "done";
  job.running = false;
  return { sessions: list, waiting };
}

/* 追加条目沿用与既有一致的形状：label + userId + accountName。
   userId 只认扫描结果，标签/名称仍走同一套文本校验；任一条不合法整份不写。 */
async function registerCommit(body) {
  let cfg;
  try {
    cfg = await loadCfg();
  } catch {
    return { errors: [`读不到账号配置 ${CFG_FILE}`] };
  }
  if (!cfg || !Array.isArray(cfg.accounts)) return { errors: ["账号配置里没有 accounts 名单"] };
  const next = JSON.parse(JSON.stringify(cfg));
  // 没写过 probePorts 的配置文件就别凭空给他补一份缺省值：只有真用到新端口时才落盘
  const hadPorts = Array.isArray(next.probePorts) && next.probePorts.length;
  const ports = hadPorts ? next.probePorts : [...DEFAULT_PORTS];
  let portsChanged = false;
  const items = Array.isArray(body.items) ? body.items.slice(0, 9) : [];
  const errors = [];
  const added = [];
  const byLabel = new Set(next.accounts.map((a) => String(a.label)));
  const byUserId = new Set(next.accounts.map((a) => String(a.userId)));

  for (const item of items) {
    const port = Number(item.port);
    const seen = pendingIds.get(port);
    if (!seen) {
      errors.push(`端口 ${item.port} 没有可登记的扫描结果，请先点「读一下待登记的号」`);
      continue;
    }
    if (byUserId.has(String(seen.userId))) {
      errors.push(`窗口里的号已经在名单里了，不用再登记`);
      continue;
    }
    const label = oneLine(item.label, LIMITS.label);
    if (!label) {
      errors.push(`标签要是 1–${LIMITS.label} 个字符、不含换行`);
      continue;
    }
    if (byLabel.has(label)) {
      errors.push(`标签「${label}」已被另一个账号占用`);
      continue;
    }
    const accountName = oneLine(item.accountName ?? seen.name, LIMITS.accountName) || seen.name || label;
    next.accounts.push({ label, userId: seen.userId, accountName });
    if (!ports.includes(port)) { ports.push(port); portsChanged = true; }
    byLabel.add(label);
    byUserId.add(String(seen.userId));
    added.push(label);
  }

  if (errors.length) return { errors };
  if (!added.length) return { added, rebuilt: false };
  if (portsChanged) next.probePorts = ports.sort((a, b) => a - b);

  const fail = await writeCfg(next);
  if (fail) return { errors: [fail] };
  // 登记完立刻采一次：能采到就说明这个 userId 真的可查，形成"登记即可用"的闭环
  await refresh(false);
  const rebuildError = job.phase === "failed" ? job.error : null;
  return { added, rebuilt: !rebuildError, rebuildError };
}

const readJsonBody = (req) =>
  new Promise((resolveBody, rejectBody) => {
    let text = "";
    req.on("data", (c) => {
      text += c;
      if (text.length > 2e4) rejectBody(new Error("body_too_large"));
    });
    req.on("end", () => {
      try { resolveBody(text ? JSON.parse(text) : {}); }
      catch { rejectBody(new Error("bad_json")); }
    });
    req.on("error", rejectBody);
  });

const json = (res, code, body) => {
  res.writeHead(code, { "content-type": "application/json; charset=utf-8", "cache-control": "no-store" });
  res.end(JSON.stringify(body));
};

const allowedHost = (req) => {
  const host = String(req.headers.host || "");
  return /^(127\.0\.0\.1|localhost)(:\d+)?$/.test(host);
};

const authorized = (req) => req.headers["x-cw-token"] === TOKEN;

const server = createServer(async (req, res) => {
  const url = new URL(req.url, "http://127.0.0.1");
  if (!allowedHost(req)) return json(res, 403, { error: "forbidden_host" });
  const path = url.pathname;

  if (path === "/api/health") return json(res, 200, { ok: true, refresh: true, settings: true, token: false });
  if (path === "/api/refresh/status") {
    if (!authorized(req)) return json(res, 401, { error: "need_token" });
    return json(res, 200, job);
  }
  if (req.method === "POST" && path.startsWith("/api/")) {
    if (!authorized(req)) return json(res, 401, { error: "need_token" });
    if (job.running) return json(res, 409, { error: "busy", job });
    let body;
    try {
      body = await readJsonBody(req);
    } catch (e) {
      return json(res, 400, { error: String(e?.message || e) });
    }
    if (path === "/api/refresh") {
      refresh(!!body.headless);
      return json(res, 202, { started: true });
    }
    if (path === "/api/rebuild") {
      rebuild(false);
      return json(res, 202, { started: true });
    }
    if (path === "/api/profiles") {
      const out = await openProfiles(body);
      return out.errors ? json(res, 400, out) : json(res, 200, out);
    }
    // 新增账号的三步：都跑完才回应，页面上用按钮自己的 loading 态，不占采集的进度条
    if (path === "/api/register/open") {
      const out = await registerOpen();
      return out.errors ? json(res, 400, out) : json(res, 200, out);
    }
    if (path === "/api/register/scan") {
      const out = await registerScan();
      return out.errors ? json(res, 400, out) : json(res, 200, out);
    }
    if (path === "/api/register/commit") {
      const out = await registerCommit(body);
      return out.errors ? json(res, 400, out) : json(res, 200, out);
    }
    if (path === "/api/settings") {
      const out = await saveSettings(body);
      return out.errors ? json(res, 400, out) : json(res, 200, out);
    }
  }
  if (path.startsWith("/api/")) return json(res, 404, { error: "not_found" });

  let file = normalize(join(ROOT, decodeURIComponent(path)));
  if (!file.startsWith(ROOT)) return json(res, 403, { error: "forbidden_path" });
  // 页面只认包内那一个地址：本机服务把插件外那份真实数据顶上去，没采过数就照旧给样例。
  if (resolve(file) === SITE_DATA && existsSync(LIVE_DATA)) file = LIVE_DATA;
  try {
    if ((await stat(file)).isDirectory()) file = join(file, "index.html");
    let body = await readFile(file);
    if (file.endsWith("index.html")) {
      // 令牌只在本机服务里注入，静态发布出去的包里不存在这段，前端据此判断能力。
      const inject = `<script>window.__CW_LOCAL__={token:"${TOKEN}",port:${RUNNING_PORT}};</script>`;
      body = Buffer.from(body.toString().replace("</head>", `${inject}</head>`));
    }
    res.writeHead(200, { "content-type": types[extname(file)] || "application/octet-stream", "cache-control": "no-store" });
    res.end(body);
  } catch {
    res.writeHead(404, { "content-type": "text/plain; charset=utf-8" }).end("not found");
  }
});

// 解析启动端口：--port > accounts.json.port（看板设置页写入）> 49788。改端口只影响下次启动，当前服务不改绑。
WANT_PORT = CLI_PORT != null ? Number(CLI_PORT) : 0;
if (!Number.isInteger(WANT_PORT) || WANT_PORT < 1024 || WANT_PORT > 65535) {
  WANT_PORT = 0;
  try { const p = Number((await loadCfg()).port); if (Number.isInteger(p) && p >= 1024 && p <= 65535) WANT_PORT = p; } catch { /* 无配置就用兑底 */ }
}
if (!WANT_PORT) WANT_PORT = 49788;

// 端口固定后可能撞车（上一次的服务还开着）：给一句人话退出，而不是抛 EADDRINUSE 崩栈。
server.on("error", (e) => {
  if (e && e.code === "EADDRINUSE") {
    console.error(`端口 ${WANT_PORT} 已被占用——多半是上一次的本地服务还开着。关掉那个终端窗口，或用 --port <其它端口> 再起。`);
  } else {
    console.error(`本地服务起不来：${e?.message || e}`);
  }
  process.exit(1);
});

server.listen(WANT_PORT, "127.0.0.1", () => {
  RUNNING_PORT = server.address().port;
  console.log(`credit-watch 本地服务：http://127.0.0.1:${RUNNING_PORT}/`);
  console.log(`站点目录 ${ROOT}`);
  console.log(`看板数据 ${LIVE_DATA}`);
  console.log(`一次性令牌 ${TOKEN}`);
  console.log("关闭此窗口即停止；接口只监听 127.0.0.1。");
  // 起服务即按现有 history 重算一次，保证打开就是最新；无配置/未采集时非致命，页面照样起
  rebuild(true).catch(() => {});
});
