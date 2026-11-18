// 用量口径聚合：
//   credits 模式 —— 只统计内置模型 Credits（SQLite 每轮 + 旧版 jsonl 每请求），自定义模型不纳入
//   token   模式 —— 全部模型 token 合并（BYOK 桌面 + 网关记录）
// 内置 credits 按每轮模型归属（jsonl user 记录的 businessModelKey，缺失时退回会话模型）。
// 模型展示名优先读客户端 dynamic-text 缓存，BUILTIN_LABELS 仅作兜底。
// buildStats 供对话查询；buildPanel 供面板：双模式 × 近7/30日一次返回，UI 切换模式/范围不再请求。
import { readFileSync } from "node:fs"
import { CLIENTS, readClient } from "./data.mjs"
import { scanProjects } from "./jsonl.mjs"
import { scanMagpie, MAGPIE_USAGE_PATH } from "./magpie.mjs"

const pad2 = (n) => String(n).padStart(2, "0")
const dayKey = (ts) => { const d = new Date(ts); return `${d.getFullYear()}-${pad2(d.getMonth() + 1)}-${pad2(d.getDate())}` }
const addDays = (key, n) => { const [y, m, d] = key.split("-").map(Number); return dayKey(new Date(y, m - 1, d + n).getTime()) }
const weekday = (key) => { const [y, m, d] = key.split("-").map(Number); return (new Date(y, m - 1, d).getDay() + 6) % 7 }
const round2 = (n) => Math.round(n * 100) / 100
const CHAT_GAP_MS = 30 * 60 * 1000
const HEAT_DAYS = 364
const CACHE_TTL = 30_000

// 内置模型代号 → 官方展示名兜底表（旧版客户端的 dynamic-text 快照 + 人工确认值）。
// 运行时优先读客户端 dynamic-text（model.<code>.label），本表只补它缺失的代号，如新上线的旗舰预览版。
const BUILTIN_LABELS = {
  auto: { en: "Auto", zh: "Auto" },
  cmodel: { en: "Cantus", zh: "Cantus" },
  dfmodel: { en: "DeepSeek-Flash", zh: "DeepSeek-Flash" },
  dmodel: { en: "DeepSeek-V4-Pro", zh: "DeepSeek-V4-Pro" },
  efficient: { en: "Efficient", zh: "经济" },
  fast: { en: "Fast", zh: "快速" },
  gfmodel: { en: "GLM-5.3-Flash", zh: "GLM-5.3-Flash" },
  gm51model: { en: "GLM-5.2", zh: "GLM-5.2" },
  gmodel: { en: "GLM-5.3", zh: "GLM-5.3" },
  kmodel: { en: "Kimi-K2.8-Preview", zh: "Kimi-K2.8-Preview" },
  kmodel_latest: { en: "Kimi-K3.1-Pro", zh: "Kimi-K3.1-Pro" },
  lite: { en: "Lite", zh: "轻量" },
  mmodel: { en: "MiniMax-M3.1-Flash", zh: "MiniMax-M3.1-Flash" },
  performance: { en: "Performance", zh: "性能" },
  q37fmodel: { en: "Qwen3.7-Flash", zh: "Qwen3.7-Flash" },
  qfmodel: { en: "Qwen3.8-Flash", zh: "Qwen3.8-Flash" },
  qmodel: { en: "Qwen3.7-Plus", zh: "Qwen3.7-Plus" },
  qmodel_38max: { en: "Qwen3.8-Max", zh: "Qwen3.8-Max" },
  qmodel_latest: { en: "Qwen3.7-Max", zh: "Qwen3.7-Max" },
  qmodel_latest_preview: { en: "Qwen4-Max-Preview", zh: "Qwen4-Max-Preview" },
  smodel: { en: "Sonus", zh: "Sonus" },
  ultimate: { en: "Ultimate", zh: "极致" },
}

const shortModel = (m) => (m && m.includes("/") ? m.split("/").pop() : m)

// 客户端 dynamic-text 里的模型展示名（model.<code>.label），跟随客户端缓存自动更新。
const LABEL_TTL = 5 * 60_000
let labelCache = null
function dynamicLabels() {
  if (labelCache && Date.now() - labelCache.at < LABEL_TTL) return labelCache.map
  const map = new Map()
  for (const client of Object.values(CLIENTS)) {
    let j
    try { j = JSON.parse(readFileSync(client.dynamicText, "utf8")) } catch { continue }
    const zh = j?.data?.zh || {}, en = j?.data?.en || {}
    for (const [k, v] of Object.entries(zh)) {
      const m = /^model\.(.+)\.label$/.exec(k)
      if (m) map.set(m[1], { en: en[k] ?? v, zh: v })
    }
  }
  labelCache = { at: Date.now(), map }
  return map
}
const labelOf = (code) => dynamicLabels().get(code) || BUILTIN_LABELS[code]

// 统一记录的模型名 → 模型标识：builtin=内置代号（附展示名）、custom=用户自定义、gateway=网关服务。
// 内置/自定义由记录类型（hint）决定：credits 计费轮=builtin、BYOK 请求=custom；
// 无 hint 时（会话元数据）按 byok:/qoder-custom- 前缀推断，其余一律视为内置代号。
// UI 端拼 Qoder-/Custom- 前缀。
function modelMeta(raw, hint) {
  let s = String(raw || "").trim()
  if (s.startsWith("byok:")) s = s.slice(5)
  if (s.startsWith("qoder-custom-") || s.includes("/")) hint = "custom"
  if (!s) return { model: "", kind: "builtin", label: undefined }
  if (hint === "custom") return { model: shortModel(s) || "(unknown)", kind: "custom" }
  return { model: s, kind: "builtin", label: labelOf(s) }
}

const modelValue = (r, unit) => (unit === "token" ? (r.inTok || 0) + (r.outTok || 0) : r.credits || 0)

// rows 按 keyFn 分组，数值字段求和，count 计数
function groupBy(rows, keyFn, fields) {
  const map = new Map()
  for (const r of rows) {
    const k = keyFn(r)
    let acc = map.get(k)
    if (!acc) {
      acc = { key: k, count: 0 }
      for (const f of fields) acc[f] = 0
      map.set(k, acc)
    }
    acc.count++
    for (const f of fields) acc[f] += r[f] || 0
  }
  return [...map.values()]
}

const cache = new Map()
// 统一记录 kind ∈ builtin-turn | legacy-credit | byok-request | gateway-request
export async function collect(clientFilter, source, force = false) {
  const cacheKey = `${clientFilter}|${source}`
  const hit = cache.get(cacheKey)
  if (!force && hit && Date.now() - hit.at < CACHE_TTL) return hit.value
  const perClient = []
  for (const client of Object.values(CLIENTS)) {
    if (clientFilter !== "all" && clientFilter !== client.key) continue
    const db = readClient(client)
    const jsonl = source === "gateway" ? { records: [], turns: [] } : await scanProjects(client)
    perClient.push({ client, db, jsonlRecords: jsonl.records, turnModels: jsonl.turns })
  }
  const gatewayRecords = source === "desktop" ? [] : await scanMagpie(MAGPIE_USAGE_PATH)
  const value = { perClient, gatewayRecords }
  cache.set(cacheKey, { at: Date.now(), value })
  return value
}

// 只读命中未过期的缓存，不触发重扫
export function peekCollect(clientFilter, source) {
  const hit = cache.get(`${clientFilter}|${source}`)
  return hit && Date.now() - hit.at < CACHE_TTL ? hit.value : null
}

// 每个会话内相邻消息间隔 >30 分钟即断开，取最长的连续段
function longestChat(perClient) {
  let best = 0
  for (const { db } of perClient) {
    const bySession = new Map()
    for (const m of db.messages) {
      let list = bySession.get(m.sessionId)
      if (!list) bySession.set(m.sessionId, (list = []))
      list.push(m.ts)
    }
    for (const list of bySession.values()) {
      if (list.length < 2) continue
      list.sort((a, b) => a - b)
      let start = list[0]
      for (let i = 1; i < list.length; i++) {
        if (list[i] - list[i - 1] > CHAT_GAP_MS) start = list[i]
        else best = Math.max(best, list[i] - start)
      }
    }
  }
  return best
}

// collected → 统一记录（buildStats 与 buildPanel 共用）
function buildRecords({ perClient, gatewayRecords }, source = "all") {
  const records = []
  const sessionsByClient = new Map()
  const isByokModel = (m) => String(m || "").startsWith("byok:") || String(m || "").startsWith("qoder-custom-")
  for (const { client, db, jsonlRecords, turnModels } of perClient) {
    sessionsByClient.set(client.key, db.sessions)
    const turnModel = new Map()
    for (const t of turnModels) turnModel.set(`${t.sessionId}|${t.turnId}`, t.model)
    if (source !== "gateway") {
      // SQLite 每轮 credits（内置模型，2026-11-10 迁移后的新数据源）
      // 模型按轮归属：jsonl 的 businessModelKey 精确到轮；缺失时退回会话模型
      for (const t of db.turns) {
        const model = turnModel.get(`${t.sessionId}|${t.turnId}`) || db.sessions.get(t.sessionId)?.model || ""
        // BYOK 轮次不计入积分口径（会话中途切换过模型的也能精确剔除）
        if (isByokModel(model)) continue
        records.push({
          kind: "builtin-turn", client: client.key, ts: t.ts, day: t.ts ? dayKey(t.ts) : "",
          sessionId: t.sessionId, model, credits: t.credits,
        })
      }
      // jsonl 每请求 usage：BYOK = 真实 token；旧版内置 = 每请求 credits
      for (const r of jsonlRecords) {
        // BYOK 判定优先用每请求标记（modelSource/customProviderId）；
        // 无标记时退回旧启发式：内置旧版行必带 credits，故仅无 credits 的行才按会话/模型名前缀推断。
        // 这样会话中途切换模型（如 BYOK 切回内置）时，两类请求都不会被误判清零。
        const isByok = r.byok || (!r.credits && (isByokModel(db.sessions.get(r.sessionId)?.model) || isByokModel(r.model)))
        records.push({
          kind: isByok ? "byok-request" : "legacy-credit",
          client: client.key, ts: r.ts, day: r.ts ? dayKey(r.ts) : "", sessionId: r.sessionId,
          model: isByok ? shortModel(r.model || db.sessions.get(r.sessionId)?.model) : (r.model || db.sessions.get(r.sessionId)?.model || ""),
          credits: isByok ? 0 : r.credits,
          inTok: isByok ? r.inTok : 0, outTok: isByok ? r.outTok : 0,
          cacheRead: isByok ? r.cacheRead : 0, cacheWrite: isByok ? r.cacheWrite : 0,
        })
      }
    }
  }
  if (source !== "desktop") {
    for (const r of gatewayRecords) {
      records.push({
        kind: "gateway-request", client: "gateway", ts: r.ts, day: r.ts ? dayKey(r.ts) : "", sessionId: "", model: r.model,
        inTok: r.inTok, outTok: r.outTok, cacheRead: r.cacheRead, cacheWrite: r.cacheWrite,
      })
    }
  }
  return { records, sessionsByClient }
}

const KINDS_BY_MODE = {
  token: ["byok-request", "gateway-request"],
  credits: ["builtin-turn", "legacy-credit"],
}

// 面板：按模式的每日聚合，含模型标识（key = kind|model）
function buildDaily(records, mode) {
  const kinds = KINDS_BY_MODE[mode]
  const daily = new Map()
  for (const r of records) {
    if (!kinds.includes(r.kind) || !r.day) continue
    let e = daily.get(r.day)
    if (!e) daily.set(r.day, (e = { value: 0, byModel: new Map() }))
    const v = modelValue(r, mode)
    e.value += v
    const m = r.kind === "gateway-request"
      ? { model: shortModel(r.model) || "(unknown)", kind: "gateway", label: undefined }
      : modelMeta(r.model, r.kind === "byok-request" ? "custom" : "builtin")
    const key = `${m.kind}|${m.model}`
    let acc = e.byModel.get(key)
    if (!acc) e.byModel.set(key, (acc = { ...m, value: 0 }))
    acc.value += v
  }
  return daily
}

function buildHeat(daily, today) {
  const from = addDays(addDays(today, -HEAT_DAYS), -weekday(addDays(today, -HEAT_DAYS)))
  const values = []
  let total = 0, peak = 0, peakDate = from
  for (let key = from; key <= today; key = addDays(key, 1)) {
    const v = daily.get(key)?.value || 0
    values.push(round2(v))
    total += v
    if (v >= peak) { peak = v; peakDate = key }
  }
  let current = 0, longest = 0, run = 0
  const activeOffset = values[values.length - 1] > 0 ? 0 : 1
  for (let i = values.length - 1 - activeOffset; i >= 0 && values[i] > 0; i--) current++
  for (const v of values) { run = v > 0 ? run + 1 : 0; longest = Math.max(longest, run) }
  return { from, values, total: round2(total), peakDate, streak: { current, longest } }
}

function buildRange(daily, today, days) {
  const dates = []
  for (let i = days - 1; i >= 0; i--) dates.push(addDays(today, -i))
  const indexOf = new Map(dates.map((d, i) => [d, i]))
  const totals = new Map()
  for (const [day, e] of daily) {
    const idx = indexOf.get(day)
    if (idx === undefined) continue
    for (const [, m] of e.byModel) {
      const key = `${m.kind}|${m.model}`
      let acc = totals.get(key)
      if (!acc) totals.set(key, (acc = { model: m.model, kind: m.kind, label: m.label, value: 0, values: new Array(days).fill(0) }))
      acc.value += m.value
      acc.values[idx] += m.value
    }
  }
  const ranked = [...totals.values()].filter((m) => m.value > 0).sort((a, b) => b.value - a.value)
  const meta = (m) => ({ model: m.model, kind: m.kind, label: m.label })
  return {
    days,
    from: dates[0] || "",
    dates,
    models: ranked.map((m) => ({ ...meta(m), value: round2(m.value) })),
    series: ranked.map((m) => ({ ...meta(m), values: m.values.map(round2) })),
  }
}

// 最近会话列表（网关无会话，不纳入）
function sessionList(records, sessionsByClient) {
  const rows = new Map()
  for (const r of records) {
    if (!r.sessionId || r.kind === "gateway-request") continue
    const key = `${r.client}|${r.sessionId}`
    let acc = rows.get(key)
    if (!acc) {
      const meta = sessionsByClient.get(r.client)?.get(r.sessionId)
      acc = {
        sessionId: r.sessionId, title: meta?.title || "",
        model: modelMeta(meta?.model || r.model || ""),
        lastTs: meta?.updatedAt || 0, credits: 0, inTok: 0, outTok: 0,
      }
      rows.set(key, acc)
    }
    acc.credits += r.credits || 0
    acc.inTok += r.inTok || 0
    acc.outTok += r.outTok || 0
    acc.lastTs = Math.max(acc.lastTs, r.ts || 0)
  }
  return [...rows.values()]
    .sort((a, b) => b.lastTs - a.lastTs)
    .slice(0, 50)
    .map((s) => ({ ...s, credits: round2(s.credits) }))
}

export function buildPanel(collected) {
  const today = dayKey(Date.now())
  const { records, sessionsByClient } = buildRecords(collected)
  const chatMs = longestChat(collected.perClient)
  const out = { generatedAt: Date.now(), token: null, credits: null, sessions: sessionList(records, sessionsByClient) }
  for (const mode of ["token", "credits"]) {
    const daily = buildDaily(records, mode)
    const heat = buildHeat(daily, today)
    out[mode] = {
      unit: mode,
      all: { total: heat.total, peakDate: heat.peakDate, chatMs, streak: heat.streak, heat: { from: heat.from, values: heat.values } },
      d7: buildRange(daily, today, 7),
      d30: buildRange(daily, today, 30),
    }
  }
  return out
}

export async function buildStats({ mode = "credits", client = "all", days = null, source = "all", refresh = false } = {}) {
  const today = dayKey(Date.now())
  const fromDay = days && days > 0 ? addDays(today, -(days - 1)) : null
  const collected = await collect(client, source, refresh)
  const { perClient, gatewayRecords } = collected
  const { records, sessionsByClient } = buildRecords(collected, source)

  const dbReadable = {}
  for (const { client: c, db } of perClient) dbReadable[c.key] = db.sessions.size > 0

  // 旧口径字段按时间范围过滤；summary 使用全量
  const scoped = fromDay ? records.filter((r) => r.day && r.day >= fromDay) : records

  const builtinRows = scoped.filter((r) => r.kind === "builtin-turn" || r.kind === "legacy-credit")
  const tokenRows = scoped.filter((r) => r.kind === "byok-request" || r.kind === "gateway-request")

  const metaOf = (clientKey, sessionId) =>
    clientKey === "gateway" ? { title: "网关调用（magpie）", model: "" } :
    sessionsByClient.get(clientKey)?.get(sessionId) || { title: sessionId.slice(0, 8), model: "" }

  const sessionRows = (rows) =>
    groupBy(rows, (r) => r.client + "|" + r.sessionId, ["credits", "inTok", "outTok", "cacheRead", "cacheWrite"])
      .map(({ key, count, credits, inTok, outTok, cacheRead, cacheWrite }) => {
        const [cl, sid] = key.split("|")
        const meta = metaOf(cl, sid)
        return {
          client: cl, sessionId: sid, title: meta.title || "(无标题会话)", model: meta.model,
          count, credits: round2(credits), inTok, outTok, cacheRead, cacheWrite,
          lastTs: meta.updatedAt || 0,
        }
      })
      .sort((a, b) => (b.credits || b.inTok) - (a.credits || a.inTok))

  const modelRows = (rows, gatewayPrefix) =>
    groupBy(rows, (r) => (r.kind === "gateway-request" ? gatewayPrefix : "") + (r.model || "(未知模型)"), ["inTok", "outTok", "cacheRead", "cacheWrite"])
      .map(({ key, count, inTok, outTok, cacheRead, cacheWrite }) => ({ model: key, count, inTok, outTok, cacheRead, cacheWrite }))
      .sort((a, b) => b.inTok - a.inTok)

  const totalOf = (rows, f) => rows.reduce((a, r) => a + (r[f] || 0), 0)

  // ——— summary：面板专用的全量 + 范围视图（非 panel 详情） ———
  const unit = mode === "token" ? "token" : "credits"
  const daily = buildDaily(records, unit)

  const heat = buildHeat(daily, today)

  const rangeDays = fromDay ? days : 0
  const range = buildRange(daily, today, rangeDays || 7)
  const summary = {
    unit,
    all: {
      total: heat.total,
      peakDate: heat.peakDate,
      chatMs: longestChat(perClient),
      streak: heat.streak,
      heat: { from: heat.from, values: heat.values },
    },
    range: rangeDays ? range : { days: 0, from: "", dates: [], models: [], series: [] },
  }
  return {
    mode, days, generatedAt: Date.now(), cutoff: fromDay ? fromDay : 0, dbReadable,
    builtin: {
      turns: builtinRows.length,
      credits: round2(totalOf(builtinRows, "credits")),
      byDay: groupBy(builtinRows, (r) => dayKey(r.ts || 0), ["credits"])
        .map(({ key, count, credits }) => ({ date: key, turns: count, credits: round2(credits) }))
        .sort((a, b) => a.date.localeCompare(b.date)),
      bySession: sessionRows(builtinRows),
    },
    token: {
      requests: tokenRows.length,
      inTok: totalOf(tokenRows, "inTok"), outTok: totalOf(tokenRows, "outTok"),
      cacheRead: totalOf(tokenRows, "cacheRead"), cacheWrite: totalOf(tokenRows, "cacheWrite"),
      byDay: groupBy(tokenRows, (r) => dayKey(r.ts || 0), ["inTok", "outTok", "cacheRead"])
        .map(({ key, inTok, outTok, cacheRead }) => ({ date: key, inTok, outTok, cacheRead }))
        .sort((a, b) => a.date.localeCompare(b.date)),
      byModel: modelRows(tokenRows, "网关·"),
      bySession: sessionRows(tokenRows),
      desktopBuiltinWithoutTokens: {
        turns: builtinRows.filter((r) => r.kind === "builtin-turn").length,
        credits: round2(builtinRows.filter((r) => r.kind === "builtin-turn").reduce((a, r) => a + r.credits, 0)),
      },
    },
    summary,
  }
}
