/**
 * 受预算约束的 HTTP 客户端。红线写在代码里，不写在文档里——
 * 因为黑盒模式打的是可能不属于使用者的站点，一条「建议不要刷太狠」等于没有。
 *
 * 不变量（都不指望调用方自觉，全部在这里实现）：
 *  - **一轮**（不是「一个脚本」）的请求预算：target 池 40 次、external 池 20 次，
 *    计数与请求时刻落在 --out/net-round.json，跨脚本共享；耗尽后返回 skipped 而不是继续发。
 *  - 最小请求间隔同样跨脚本共享（各记各的时间戳时，实测平均间隔只有 129ms）。
 *  - 只允许 GET / HEAD，其他方法直接抛 PolicyViolation。
 *  - target 池只允许单一 origin；external 池可换主机，但内网/元数据地址**永远**先判先拒
 *    （判定若放在「换主机」分支之后，恶意页面把内网地址排在第二条链接就能拨出去）。
 *  - 域名先解析再连：解析结果落在内网段一样拒绝（主机名黑名单看不见 A 记录）。
 *  - 同主机连续 429/403 触发熔断，熔断计数跨脚本共享（否则攒几个 403 就能白送一次「无死链」）。
 *  - 不发送任何凭据：无 cookie、无 authorization，带 userinfo 的 URL 直接拒绝而不是摘掉再发。
 */

import http from 'node:http';
import https from 'node:https';
import dns from 'node:dns';
import { URL } from 'node:url';
import { readFileSync, writeFileSync, renameSync, mkdirSync, rmSync } from 'node:fs';
import { join, resolve } from 'node:path';

export const DEFAULTS = {
  budget: 60,
  // 一轮里两个池各算各的：外链探测不该把目标站的检查饿死，两者相加才是文档里的 60。
  poolBudget: { target: 40, external: 20 },
  allowPrivate: false,
  concurrency: 2,
  timeoutMs: 8000,
  minIntervalMs: 250,
  // 没有 maxRedirects：本客户端**从不跟随重定向**。
  // 3xx 一律原样记账（`-L` 式跟随会把单主机红线交给对方服务器决定），
  // 因此「重定向终点是否仍活着」不在本工具的能力范围内。
  breakerTripsOn429: 2,
  breakerTripsOn403: 3,
  // 必须有默认值：header 值为 undefined 时 node 直接抛 ERR_HTTP_INVALID_HEADER_VALUE。
  // 默认不带任何联系方式——UA 里塞邮箱等于把使用者身份写进别人的访问日志。
  userAgent: 'site-audit/1.0',
};

export class PolicyViolation extends Error {}

/**
 * 内网与云元数据地址：外链探测会抓被审页面里的任意 http(s) 链接，
 * 一个恶意站点只要放 `http://169.254.169.254/latest/meta-data/` 或 `http://localhost:6379/`
 * 就能把审查机变成它的内网探针（对抗审查实测：真的拨出去了，还把状态码当 oracle 回了报告）。
 */
const PRIVATE_HOST = /^(?:127\.|10\.|192\.168\.|172\.(?:1[6-9]|2\d|3[01])\.|169\.254\.|100\.(?:6[4-9]|[7-9]\d|1[01]\d|12[0-7])\.|0\.)/;

/** IP 字面量（含 IPv6 与 v4-mapped 形式）是否属于内网/回环/链路本地/元数据段。 */
export function isPrivateAddress(ip) {
  let h = String(ip || '').toLowerCase().replace(/^\[(.*)\]$/, '$1');
  if (!h) return true;
  const mapped = /^::ffff:((?:\d{1,3}\.){3}\d{1,3})$/.exec(h);
  if (mapped) h = mapped[1];
  if (h === '::1' || h === '::') return true;
  if (/^fe80/.test(h) || /^f[cd]/.test(h)) return true;
  if (/^(?:\d{1,3}\.){3}\d{1,3}$/.test(h)) return PRIVATE_HOST.test(h + '.');
  return false; // 形态未知的字符串交给主机名层规则，这里不臆测
}

function isPrivateHost(host) {
  const h = String(host || '').toLowerCase().replace(/^\[(.*)\]$/, '$1');
  if (!h) return true;
  if (h === 'localhost' || h === '::1' || h === '0.0.0.0') return true;
  if (h.endsWith('.local') || h.endsWith('.internal') || h.endsWith('.lan') || h.endsWith('.home.arpa')) return true;
  if (h.includes(':')) return isPrivateAddress(h);
  return PRIVATE_HOST.test(h);
}

/**
 * 先解析、判完内网再连。用 node 的 lookup 钩子而不是自己把 host 换成 IP：
 * 这样 Host 头与 TLS SNI 仍是原域名，只有实际连接的目标地址被把关。
 */
export function pinnedLookup(hostname, options, callback) {
  const cb = typeof options === 'function' ? options : callback;
  dns.lookup(hostname, { all: true }, (err, addrs) => {
    if (err) return cb(err);
    const list = Array.isArray(addrs) ? addrs : [addrs];
    const pub = list.filter((a) => a && a.address && !isPrivateAddress(a.address));
    if (!pub.length) {
      const e = new Error(`EAI_PRIVATE: ${hostname} 的解析结果全在内网/元数据段，已拒绝连接`);
      e.code = 'EAI_PRIVATE';
      return cb(e);
    }
    cb(null, pub[0].address, pub[0].family);
  });
}

/**
 * 一轮的 HTTP 账本：两个池各自的已用次数与上次请求时刻、各主机的 403/429 计数，
 * 落在 --out 里的一个文件。
 *
 * 为什么必须落盘共享：一轮审查由 4 个脚本各自 new 一个 HttpBudget，于是「本轮 60 次预算」
 * 实际是 4×预算，「最小间隔」各记各的（实测平均 129ms），而熔断计数每个新实例都从零开始。
 * @param {string|null} outDir
 * @param {number} round
 */
export function openRoundNetState(outDir, round) {
  if (!outDir) return null;
  const file = join(resolve(outDir), 'net-round.json');
  const blank = () => ({
    round: Number(round) || 1,
    pools: {
      target: { used: 0, lastAt: 0, cap: DEFAULTS.poolBudget.target },
      external: { used: 0, lastAt: 0, cap: DEFAULTS.poolBudget.external },
    },
    deniedPrivate: 0,
    credUrls: 0,
    hosts: {},
  });
  let mem = blank();
  let writable = false;
  const store = (s) => {
    // 先写临时文件再 rename：读-改-写并发时，半截 JSON 会被下一次 read()
    // 当成「新的一轮」清零——预算与熔断计数就这么白送了。
    const tmp = file + '.' + process.pid + '.tmp';
    try {
      writeFileSync(tmp, JSON.stringify(s));
      renameSync(tmp, file);
      writable = true;
      return true;
    } catch {
      try { rmSync(tmp, { force: true }); } catch { /* 临时文件也删不掉就算了 */ }
      return false;
    }
  };
  const read = () => {
    try {
      const j = JSON.parse(readFileSync(file, 'utf8'));
      if (Number(j.round) !== Number(round)) {
        mem = blank();
        store(mem);
        return mem;
      }
      const b = blank();
      mem = { ...b, ...j, pools: { ...b.pools, ...(j.pools || {}) }, hosts: { ...(j.hosts || {}) } };
      return mem;
    } catch {
      // 解析不了：保住内存里的计数（清零等于把这一轮的预算与熔断忘掉），并记下这次读了个坏文件
      mem.corruptRead = (Number(mem.corruptRead) || 0) + 1;
      if (!writable) {
        try { mkdirSync(resolve(outDir), { recursive: true }); } catch { /* 只读输出目录：退回实例内计数 */ }
        writable = store(mem);
      }
      return mem;
    }
  };
  return {
    file,
    read,
    pool(name) {
      const s = read();
      return (s.pools && s.pools[name]) || { used: 0, lastAt: 0, cap: DEFAULTS.poolBudget[name] || 20 };
    },
    /** 取槽位：返回要等待的毫秒数，null 表示该池预算已尽。 */
    takeSlot(name, budget, minIntervalMs) {
      const s = read();
      const p = s.pools[name] || (s.pools[name] = { used: 0, lastAt: 0 });
      const cap = Math.min(Number(p.cap) || budget, budget);
      if (Number(p.used) >= cap) return null;
      const now = Date.now();
      const wait = Math.max(0, (Number(p.lastAt) || 0) + minIntervalMs - now);
      p.used = Number(p.used) + 1;
      p.lastAt = now + wait;
      store(s);
      return wait;
    },
    bump(key) {
      const s = read();
      s[key] = (Number(s[key]) || 0) + 1;
      store(s);
      return s;
    },
    bumpStatus(status, host) {
      if (status !== 429 && status !== 403) return null;
      const s = read();
      const c = s.hosts[host] || { n429: 0, n403: 0 };
      if (status === 429) c.n429++; else c.n403++;
      s.hosts[host] = c;
      store(s);
      return c;
    },
    hostCounts(host) {
      const s = read();
      return (s.hosts && s.hosts[host]) || null;
    },
  };
}

export class HttpBudget {
  /**
   * @param {object} opt
   * @param {'target'|'external'} [opt.pool] 预算池：审目标站 / 探外链
   * @param {object} [opt.shared] openRoundNetState() 的句柄，用于跨脚本共享计数
   */
  constructor(opt = {}) {
    this.o = { ...DEFAULTS, ...opt };
    this.pool = opt.pool === 'external' || opt.multiHost ? 'external' : 'target';
    this.shared = opt.shared || null;
    this._used = 0;
    this._deniedPrivate = 0;
    this._credUrls = 0;
    this.inflight = 0;
    this.lastAt = new Map();
    this.queue = [];
    this.origin = null;
    // 熔断计数按主机分别累计：否则攻击者在自己的站上前 3 个链接都回 403，
    // 就能让本次运行对**所有**外链停止探测并交出一份「无死链」的假通过。
    this.breaker = { tripped: false, reason: '', byHost: new Map() };
    this.trippedHosts = new Set();
    this.log = [];
  }

  get cap() {
    if (!this.shared) return this.o.budget;
    return Math.min(Number(this.shared.pool(this.pool).cap) || this.o.budget, this.o.budget);
  }
  get used() {
    return this.shared ? Number(this.shared.pool(this.pool).used) || 0 : this._used;
  }
  get deniedPrivate() {
    return this.shared ? Number(this.shared.read().deniedPrivate) || 0 : this._deniedPrivate;
  }
  get credUrls() {
    return this.shared ? Number(this.shared.read().credUrls) || 0 : this._credUrls;
  }

  _count(key) {
    if (this.shared) {
      this.shared.bump(key);
      return;
    }
    if (key === 'deniedPrivate') this._deniedPrivate++;
    else if (key === 'credUrls') this._credUrls++;
  }

  /** 上一脚本/上一实例在该主机上攒下的 403/429：本实例必须继承，否则熔断等于白送。 */
  _inherited(host) {
    if (!this.shared) return;
    const c = this.shared.hostCounts(host);
    if (!c) return;
    if (c.n429 >= this.o.breakerTripsOn429 || c.n403 >= this.o.breakerTripsOn403) this.trippedHosts.add(host);
  }

  /**
   * 取一个请求槽位：预算够不够、什么时候发。返回等待毫秒数，null 表示该池已尽。
   * 共享状态下把本次请求的时刻写回账本，两个脚本同时开跑也不会挤在同一瞬间发。
   */
  _takeSlot(host) {
    if (this.shared) return this.shared.takeSlot(this.pool, this.cap, this.o.minIntervalMs);
    if (this._used >= this.o.budget) return null;
    this._used++;
    const now = Date.now();
    const wait = Math.max(0, (this.lastAt.get(host) || 0) + this.o.minIntervalMs - now);
    this.lastAt.set(host, now + wait);
    return wait;
  }

  /**
   * 红线按「主机」绑定：target 池跨主机一律拒绝。同主机的 http 降级探测是 HDR-2 唯一合法需求，
   * 必须显式 allowInsecure 且整个运行只允许一次——否则「单源」就名存实亡。
   */
  bindOrigin(url, opt = {}) {
    const u = new URL(url);
    if (!/^https?:$/.test(u.protocol)) throw new PolicyViolation(`只支持 http/https，收到 ${u.protocol}`);
    // 带凭据的 URL 直接拒，而不是「把 userinfo 摘掉再发」：摘掉后拿到的 200/401
    // 会被当成那条链接的死活结论，而本工具承诺过不发送任何凭据。
    if (u.username || u.password) {
      this._count('credUrls');
      throw new PolicyViolation(`URL 里带 userinfo（${u.hostname}）：本工具不发送任何凭据，此类链接一律不探测`);
    }
    // 内网红线必须在「换主机」分支之前：外链探测要换主机，若先换主机再判内网，
    // 恶意页面把内网地址排在第二条链接就能拨出去（对抗审查实测过）。
    if (!this.o.allowPrivate && isPrivateHost(u.hostname)) {
      this._count('deniedPrivate');
      throw new PolicyViolation(`拒绝访问内网/元数据地址 ${u.hostname}（外链探测不得把审查机变成内网探针）`);
    }
    if (this.origin && this.origin !== u.hostname) {
      if (this.pool === 'external') {
        // 外链存活检测天然要碰多个主机：允许换主机，但预算/间隔/熔断仍是全轮共享的，
        // 并把碰过的主机记进 hostsTouched 以便报告。单主机红线针对的是「审 A 站时顺手打 B 站」。
        this.hostsTouched = this.hostsTouched || new Set([this.origin]);
        this.hostsTouched.add(u.hostname);
        this.origin = u.hostname;
        return u.hostname;
      }
      throw new PolicyViolation(
        `越界请求被拒绝：本运行已绑定主机 ${this.origin}，不得访问 ${u.hostname}（单主机红线）`
      );
    }
    if (u.protocol === 'http:') {
      // 目标本身就是 http（本机夹具、http-only 站点）时，http 是常态，不该拦；
      // 只有「已绑定 https 目标却要去打它的 http」才是降级探测，必须显式开启且只允许一次。
      const downgrade = this.scheme === 'https:';
      if (downgrade && !opt.allowInsecure) {
        throw new PolicyViolation(
          `拒绝明文 http 请求 ${u.hostname}：从 https 目标降级探测必须显式 allowInsecure（只用于验证 http→https 首跳）`
        );
      }
      if (downgrade) {
        this.insecureUsed = (this.insecureUsed || 0) + 1;
        if (this.insecureUsed > 1) {
          throw new PolicyViolation('明文 http 降级探测每次运行只允许 1 次，已用完');
        }
      }
    }
    this.origin = u.hostname;
    if (!this.scheme) this.scheme = u.protocol;
    return u.hostname;
  }

  stats() {
    const skipped = {};
    for (const r of this.log) if (r.skipped) skipped[r.skipped] = (skipped[r.skipped] || 0) + 1;
    return {
      pool: this.pool,
      used: this.used,
      deniedPrivate: this.deniedPrivate,
      refusedCredentialUrls: this.credUrls,
      skipped,
      sharedRoundFile: this.shared ? this.shared.file : null,
      hostsTouched: this.hostsTouched ? [...this.hostsTouched].length : (this.origin ? 1 : 0),
      budget: this.cap,
      minIntervalMs: this.o.minIntervalMs,
      remaining: Math.max(0, this.cap - this.used),
      tripped: this.breaker.tripped,
      breakReason: this.breaker.reason,
      trippedHosts: [...this.trippedHosts],
      perUrl: this.log.slice(0, 400),
    };
  }

  _schedule(fn) {
    if (this.inflight < this.o.concurrency) {
      this.inflight++;
      fn(() => {
        this.inflight--;
        this._drain();
      });
    } else {
      this.queue.push(fn);
    }
  }

  _drain() {
    while (this.inflight < this.o.concurrency && this.queue.length) {
      const fn = this.queue.shift();
      this.inflight++;
      fn(() => {
        this.inflight--;
        this._drain();
      });
    }
  }

  _skip(host, kind) {
    this.log.push({ host, status: 0, ts: Date.now(), skipped: kind });
  }

  _note(host, status) {
    this.log.push({ host, status, ts: Date.now() });
    if (status !== 429 && status !== 403) return;
    const shared = this.shared ? this.shared.bumpStatus(status, host) : null;
    const c = shared || (() => {
      const x = this.breaker.byHost.get(host) || { n429: 0, n403: 0 };
      if (status === 429) x.n429++;
      else x.n403++;
      this.breaker.byHost.set(host, x);
      return x;
    })();
    // external（外链探测）只屏蔽那一个主机；审单站时全局熔断仍然有效
    if (c.n429 >= this.o.breakerTripsOn429 || c.n403 >= this.o.breakerTripsOn403) this.trippedHosts.add(host);
    if (this.pool === 'target') {
      this.breaker.tripped = true;
      this.breaker.reason = status === 429
        ? `该主机 ${c.n429} 次 429（限流）`
        : `该主机 ${c.n403} 次 403（WAF/屏蔽——据此无法区分死链与不可达）`;
    }
  }

  /**
   * @param {string} urlStr
   * @param {{method?: 'GET'|'HEAD', timeoutMs?: number, allowInsecure?: boolean}} [opt]
   * @returns {Promise<{ok:boolean, status:number, headers:object, body:string, err?:string, host:string}>}
   */
  request(urlStr, opt = {}) {
    const method = (opt.method || 'GET').toUpperCase();
    if (method !== 'GET' && method !== 'HEAD') {
      return Promise.reject(
        new PolicyViolation(`只允许 GET/HEAD，收到 ${method}：本工具不向任何站点提交数据`)
      );
    }
    let u;
    try {
      u = new URL(urlStr);
    } catch {
      return Promise.resolve({ ok: false, status: 0, headers: {}, body: '', host: '', err: `URL 无法解析: ${urlStr}`, skipped: 'bad-url' });
    }
    const host = u.host;
    this._inherited(host);
    if (this.breaker.tripped) {
      this._skip(host, 'breaker');
      return Promise.resolve({
        ok: false, status: 0, headers: {}, body: '', host,
        err: `已熔断：${this.breaker.reason}；跳过剩余请求（无法据此判断内容死活）`,
        skipped: 'breaker',
      });
    }
    if (this.trippedHosts.has(host)) {
      this._skip(host, 'breaker-host');
      return Promise.resolve({
        ok: false, status: 0, headers: {}, body: '', host,
        err: '该主机此前连续 403/429，已跳过（不能据此判断死活）',
        skipped: 'breaker-host',
      });
    }
    try {
      this.bindOrigin(u.href, opt);
    } catch (e) {
      return Promise.reject(e);
    }
    const wait = this._takeSlot(host);
    if (wait === null) {
      this._skip(host, 'budget');
      return Promise.resolve({
        ok: false, status: 0, headers: {}, body: '', host,
        err: `${this.pool} 池本轮请求预算 ${this.cap} 已用尽（跨脚本共享，见 net-round.json）`,
        skipped: 'budget',
      });
    }
    return new Promise((resolve) => {
      this._schedule((done) => {
        setTimeout(() => {
          const mod = u.protocol === 'https:' ? https : http;
          const req = mod.request(
            u,
            {
              method,
              headers: {
                'user-agent': this.o.userAgent,
                accept: 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
              },
              timeout: opt.timeoutMs || this.o.timeoutMs,
              // 先把域名解析出来、判完内网再连：否则一条把域名指到 127.0.0.1 的 A 记录
              // 就能绕过主机名层的全部规则。审查者显式指定内网目标时不接管解析。
              lookup: this.o.allowPrivate ? undefined : pinnedLookup,
              // 从不带凭据：显式清空，免得 URL 对象里的 auth 被 node 转成 Authorization 头
              auth: undefined,
            },
            (res) => {
              let body = '';
              if (method === 'HEAD') {
                this._note(host, res.statusCode);
                done();
                return resolve({
                  ok: res.statusCode < 400, status: res.statusCode || 0,
                  headers: res.headers, body: '', host,
                });
              }
              res.setEncoding('utf8');
              res.on('data', (c) => {
                if (body.length < 4_000_000) body += c;
              });
              res.on('end', () => {
                this._note(host, res.statusCode);
                done();
                resolve({ ok: (res.statusCode || 0) < 400, status: res.statusCode || 0, headers: res.headers, body, host });
              });
              res.on('error', () => {
                this._note(host, 0);
                done();
                resolve({ ok: false, status: 0, headers: {}, body: '', host, err: 'stream-error', skipped: 'stream-error' });
              });
            }
          );
          req.on('timeout', () => {
            req.destroy(new Error('timeout'));
          });
          req.on('error', (e) => {
            this._note(host, 0);
            done();
            resolve({
              ok: false, status: 0, headers: {}, body: '', host,
              err: String(e.message || e).slice(0, 160), skipped: 'connect-error',
            });
          });
          req.end();
        }, wait);
      });
    });
  }
}

/* ---------------- robots.txt ---------------- */

/**
 * 只解析本工具用得上的两条：User-agent: * 与 Disallow/Allow 路径。
 * 不实现完整 RFC（不需要，且过度解析会给出虚假的安全感）。
 * @param {string} text
 */
export function parseRobots(text) {
  const out = { disallow: [], allow: [], crawlDelay: null, sitemaps: [], parses: true };
  if (!text || /^\s*$/.test(text)) {
    out.parses = false;
    return out;
  }
  let applies = false;
  for (const raw of text.split(/\r?\n/)) {
    const line = raw.replace(/#.*$/, '').trim();
    if (!line) continue;
    const m = /^([A-Za-z-]+)\s*:\s*(.*)$/.exec(line);
    if (!m) {
      out.parses = false;
      continue;
    }
    const k = m[1].toLowerCase();
    const v = m[2].trim();
    if (k === 'user-agent') applies = v === '*' || /qoder|site-?audit/i.test(v);
    else if (applies && k === 'disallow' && v) out.disallow.push(v);
    else if (applies && k === 'allow' && v) out.allow.push(v);
    else if (applies && k === 'crawl-delay') out.crawlDelay = Number(v) || null;
    else if (k === 'sitemap') out.sitemaps.push(v);
  }
  return out;
}
