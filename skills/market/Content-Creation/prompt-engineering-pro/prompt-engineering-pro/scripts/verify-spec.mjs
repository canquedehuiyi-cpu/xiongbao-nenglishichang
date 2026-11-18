#!/usr/bin/env node
// verify-spec.mjs — 平台规范实时核验引擎（P0，对应规范核验层）
// 能力:
//   1. 按平台/领域拉取官方规范源，与本地缓存 diff，输出变更摘要
//   2. 输出"规范变更 → 对提示词设计的影响"提示
//   3. 缓存复用（TTL 7 天）；网络失败降级到最近缓存快照
//   4. SSRF 防护：默认仅允许 spec-sources.json 注册表内的官方域名
// 设计原则: 按需核验（不做全量轮询）；正文语义解析依赖 AI 联网能力或人工核对
// 用法:
//   node scripts/verify-spec.mjs --platform wechat-minigame --json
//   node scripts/verify-spec.mjs --domain game --json
//   node scripts/verify-spec.mjs --platform skillhub --force --json
import { readFileSync, writeFileSync, existsSync, mkdirSync } from "node:fs";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";
import { safePath, isMain, makeOpt } from "./lib.mjs";
import { recordSpecChange } from "./learner.mjs";

const ROOT = join(dirname(fileURLToPath(import.meta.url)), "..");
const SOURCES_PATH = join(ROOT, "references", "spec-sources.json");
const CACHE_DIR = join(ROOT, "data", "spec-cache");
const DEFAULT_TTL_MS = 7 * 24 * 3600 * 1000; // 7 天
const MAX_BODY = 2 * 1024 * 1024; // 2MB 截断
const SNIPPET_LEN = 800;

function loadSources() {
  try {
    if (!existsSync(SOURCES_PATH)) return { platforms: {} };
    return JSON.parse(readFileSync(SOURCES_PATH, "utf8").replace(/^\uFEFF/, ""));
  } catch {
    return { platforms: {} };
  }
}

function allowedHosts(sources) {
  const set = new Set();
  for (const p of Object.values(sources.platforms || {})) {
    for (const s of p.sources || []) {
      try {
        set.add(new URL(s.url).hostname);
      } catch { /* 忽略非法 URL */ }
    }
  }
  return [...set];
}

function validateUrl(raw, hosts) {
  let u;
  try {
    u = new URL(raw);
  } catch {
    return { ok: false, error: `非法 URL: ${raw}` };
  }
  if (u.protocol !== "https:" && u.protocol !== "http:") return { ok: false, error: "仅允许 http(s) URL" };
  if (!hosts.includes(u.hostname)) return { ok: false, error: `域名不在白名单: ${u.hostname}` };
  return { ok: true, url: u };
}

function cachePath(dir, platform) {
  return join(dir, `${platform}.json`);
}

function loadCache(dir, platform) {
  const p = cachePath(dir, platform);
  try {
    if (!existsSync(p)) return null;
    return JSON.parse(readFileSync(p, "utf8").replace(/^\uFEFF/, ""));
  } catch {
    return null;
  }
}

function saveCache(dir, platform, data) {
  mkdirSync(dir, { recursive: true });
  writeFileSync(cachePath(dir, platform), JSON.stringify(data, null, 2) + "\n", "utf8");
}

function simpleDiff(prev, cur) {
  if (!prev) return { added: [], removed: [], changed: false };
  const pLines = String(prev).split("\n").map((l) => l.trim()).filter(Boolean);
  const cLines = String(cur).split("\n").map((l) => l.trim()).filter(Boolean);
  const pSet = new Set(pLines);
  const cSet = new Set(cLines);
  const removed = pLines.filter((l) => !cSet.has(l));
  const added = cLines.filter((l) => !pSet.has(l));
  return { added: added.slice(0, 20), removed: removed.slice(0, 20), changed: added.length > 0 || removed.length > 0 };
}

export async function verifySpec({ platform = null, domain = null, layer = null, force = false, dir = ROOT, timeoutSec = 10, ttlMs = DEFAULT_TTL_MS } = {}) {
  const base = safePath(dir);
  const sources = loadSources();
  const platforms = sources.platforms || {};

  // 选定要核验的平台
  let targets = [];
  if (platform) {
    if (!platforms[platform]) return { ok: false, error: `未知平台: ${platform}（可选: ${Object.keys(platforms).join("/")}）` };
    targets = [{ key: platform, ...platforms[platform] }];
  } else if (domain) {
    targets = Object.entries(platforms)
      .filter(([, v]) => v.domain === domain)
      .map(([key, v]) => ({ key, ...v }));
    if (!targets.length) return { ok: false, error: `领域 ${domain} 未注册规范源` };
  } else if (layer) {
    targets = Object.entries(platforms)
      .filter(([, v]) => v.layer === layer)
      .map(([key, v]) => ({ key, ...v }));
    if (!targets.length) return { ok: false, error: `分层 ${layer} 未注册规范源（可选层: national/industry/platform/overseas）` };
  } else {
    targets = Object.entries(platforms).map(([key, v]) => ({ key, ...v }));
  }

  const hosts = allowedHosts(sources);
  const cacheDir = join(base, "data", "spec-cache");
  const results = [];

  for (const t of targets) {
    const cache = loadCache(cacheDir, t.key);
    const now = Date.now();
    const fresh = cache && !force && now - cache.fetched_ts < ttlMs;
    if (fresh) {
      results.push({
        platform: t.key,
        label: t.label,
        layer: t.layer || "platform",
        jurisdiction: t.jurisdiction || "cn",
        source: "cache",
        fetched_ts: cache.fetched_ts,
        entries: cache.entries,
        note: "缓存有效期内命中（7 天），未发起网络请求",
      });
      continue;
    }

    const entries = [];
    let networkOk = false;
    let degraded = false;
    for (const s of t.sources || []) {
      const v = validateUrl(s.url, hosts);
      if (!v.ok) {
        entries.push({ name: s.name, url: s.url, ok: false, error: v.error });
        continue;
      }
      try {
        const ctrl = new AbortController();
        const timer = setTimeout(() => ctrl.abort(), timeoutSec * 1000);
        // 携带标准浏览器 UA 与 Accept，提升官方站点可达性（部分厂商站对无 UA 请求返回 403/502）
        const res = await fetch(v.url, {
          signal: ctrl.signal,
          redirect: "follow",
          headers: {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
          },
        });
        clearTimeout(timer);
        const body = (await res.text()).slice(0, MAX_BODY);
        const ok = res.ok;
        const snapshot = body.replace(/\s+/g, " ").slice(0, SNIPPET_LEN);
        const prev = cache?.entries?.find((e) => e.name === s.name)?.snapshot || "";
        // 首次建立基线（无缓存快照）不算变更：与空串 diff 会误报 changed，故 prev 为空时直接标记 changed=false
        const diff = prev ? simpleDiff(prev, snapshot) : { added: [], removed: [], changed: false };
        entries.push({
          name: s.name,
          url: s.url,
          ok,
          status: res.status,
          size: body.length,
          snapshot,
          changed: diff.changed,
          diff_added: diff.added.length,
          diff_removed: diff.removed.length,
        });
        if (ok) networkOk = true;
      } catch (e) {
        entries.push({ name: s.name, url: s.url, ok: false, error: `网络失败: ${e.name || "error"}` });
      }
    }

    // 有可用数据则写缓存（即便部分失败，保留快照供下次 diff）
    const usable = entries.some((e) => e.ok);
    if (usable) {
      saveCache(cacheDir, t.key, { platform: t.key, fetched_ts: now, entries });
    }

    // 规范变更 → 写入学习记录（learner 汇总生命周期提醒）
    const changedEntries = entries.filter((e) => e.changed);
    if (usable && changedEntries.length) {
      recordSpecChange({
        platform: t.key,
        changed_names: changedEntries.map((e) => e.name),
        detail: `检测到 ${changedEntries.length} 处规范内容变更，请结合 AI 联网能力核对正文`,
        dir: base,
      });
    }

    const cacheFallback = !usable && cache;
    results.push({
      platform: t.key,
      label: t.label,
      layer: t.layer || "platform",
      jurisdiction: t.jurisdiction || "cn",
      source: usable ? "network" : "degraded",
      fetched_ts: now,
      entries,
      degraded: !usable,
      note: usable
        ? (entries.some((e) => e.changed) ? "规范内容较上次缓存有变更，请结合 AI 联网能力核对正文" : "拉取成功，与上次缓存一致")
        : (cacheFallback ? "网络失败，已降级返回最近缓存快照" : "网络失败且无缓存，建议手动核对官方规范"),
    });
  }

  const changedAny = results.some((r) => r.entries && r.entries.some((e) => e.changed));
  return {
    ok: true,
    checked_at: new Date().toISOString(),
    summary: `核验 ${results.length} 个平台源${changedAny ? "，存在变更" : "，无变更"}`,
    impact_hint: changedAny
      ? "发现规范变更：构建提示词前应先核对变更内容，确保引用最新平台约束。"
      : "规范核验无变更，可直接使用当前平台约束。",
    results,
  };
}

// ================= CLI =================
if (isMain(import.meta)) {
  const args = process.argv.slice(2);
  const opt = makeOpt(args);
  const json = args.includes("--json");
  const platform = opt("platform") || null;
  const domain = opt("domain") || null;
  const layer = opt("layer") || null;
  const force = args.includes("--force");
  const dir = opt("dir") || ROOT;
  const timeoutSec = Number(opt("timeout") || 10);
  if (!platform && !domain && !layer) {
    process.stderr.write("用法: 需指定 --platform <平台> 或 --domain <领域> 或 --layer <层>（--json 输出 JSON）\n");
    process.exit(2);
  }
  try {
    const r = await verifySpec({ platform, domain, layer, force, dir, timeoutSec });
    if (!r.ok) {
      process.stderr.write(`✗ ${r.error}\n`);
      process.exit(2);
    }
    if (json) {
      process.stdout.write(JSON.stringify(r, null, 2) + "\n");
    } else {
      process.stdout.write(`${r.summary}\n`);
      process.stdout.write(`${r.impact_hint}\n`);
      for (const res of r.results) {
        process.stdout.write(`- [${res.source}] ${res.label} (${res.platform}) [${res.layer}/${res.jurisdiction}]\n`);
        for (const e of res.entries || []) {
          process.stdout.write(`    ${e.ok ? "✓" : "✗"} ${e.name} ${e.status || ""}${e.changed ? " · 内容有变更" : ""}${e.diff_added ? ` · +${e.diff_added}` : ""}${e.diff_removed ? ` · -${e.diff_removed}` : ""}${e.error ? ` · ${e.error}` : ""}\n`);
        }
        process.stdout.write(`    ${res.note}\n`);
      }
    }
  } catch (e) {
    process.stderr.write(`✗ 核验失败: ${e.message}\n`);
    process.exit(1);
  }
}
