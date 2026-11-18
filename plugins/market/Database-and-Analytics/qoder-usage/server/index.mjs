// qoder-usage MCP server：stdio 行分隔 JSON-RPC。
// 工具：usage_stats（模型可查）、usage_dashboard（App 面板入口）、usage_prefs（面板偏好读写）。
import { readFile, mkdir, writeFile } from "node:fs/promises"
import { join, dirname } from "node:path"
import { fileURLToPath } from "node:url"
import { homedir } from "node:os"
import { appendFileSync } from "node:fs"
import { buildStats, buildPanel, collect, peekCollect } from "./aggregate.mjs"
import { CLIENTS } from "./data.mjs"

const resourceUri = "ui://qoder-usage/main.html"
const VERSION = "0.3.0"
const html = await readFile(new URL("../app/main.html", import.meta.url), "utf8")
const qoderHome = process.env.QODER_HOME || join(homedir(), ".qoder")
const prefsPath = join(qoderHome, "plugins", "data", "qoder-usage", "prefs.json")
const snapshotPath = join(qoderHome, "plugins", "data", "qoder-usage", "panel-snapshot.json")
const logPath = join(qoderHome, "plugins", "data", "qoder-usage", "server.log")
const log = (...a) => { try { appendFileSync(logPath, `${new Date().toISOString()} ${a.join(" ")}\n`) } catch {} }
log(`server start v=${VERSION} pid=${process.pid} exec=${process.execPath} QODER_HOME=${process.env.QODER_HOME || "(unset)"}`)

// 装在哪个客户端里就只统计哪个客户端：QODER_HOME、插件路径、可执行文件路径任一含 qoder-cn 即为 CN 版。
function detectHostClient() {
  const here = fileURLToPath(import.meta.url)
  const markers = [qoderHome, process.execPath, here].join("|").toLowerCase()
  return markers.includes("qoder-cn") || markers.includes("qodercn") ? CLIENTS["qoder-cn"] : CLIENTS.qoder
}
const HOST = detectHostClient()

let prefs = {}
try { prefs = JSON.parse(await readFile(prefsPath, "utf8")) } catch { prefs = {} }
async function savePrefs() {
  try { await mkdir(dirname(prefsPath), { recursive: true }); await writeFile(prefsPath, JSON.stringify(prefs, null, 2)) } catch {}
}

const ok = (args) => args && typeof args === "object" && !Array.isArray(args)
const statsSchema = {
  type: "object",
  properties: {
    mode: { type: "string", enum: ["credits", "token"], description: "credits=只统计内置模型积分（自定义模型不纳入）；token=全部token合并。panel 载荷同时含双模式，此参数仅对 summary/full 生效" },
    days: { type: "integer", minimum: 1, maximum: 3650, description: "近 N 天；省略=全部。panel 载荷固定含近7/30日，此参数仅对 summary/full 生效" },
    source: { type: "string", enum: ["desktop", "gateway", "all"], description: "desktop=桌面会话；gateway=网关记录" },
    detail: { type: "string", enum: ["summary", "panel", "full"], description: "summary=省略明细（默认，对话查询）；panel=面板载荷（双模式+近7/30日+会话列表，含上次扫描快照）；full=全部" },
    refresh: { type: "boolean", description: "绕过缓存重新扫描并更新快照" },
  },
  additionalProperties: false,
}
const emptySchema = { type: "object", properties: {}, additionalProperties: false }

const tools = [
  {
    name: "usage_stats", title: "Qoder 用量统计", readOnlyHint: true,
    description: "查询 Qoder / Qoder CN 的 AI 用量。credits 模式只统计内置模型积分（自定义模型不纳入统计和展示）；token 模式返回全部模型合并的 Token。结果含按日、按会话、按模型分组。",
    inputSchema: statsSchema, annotations: { readOnlyHint: true },
  },
  {
    name: "usage_dashboard", title: "用量统计面板",
    description: "打开用量统计仪表盘。",
    inputSchema: emptySchema, annotations: { readOnlyHint: true },
    _meta: {
      ui: { resourceUri, visibility: ["app"] },
      "qoder/ui": { entrypoints: [{ type: "global" }, { type: "thread" }] },
    },
  },
  {
    name: "usage_prefs", title: "面板偏好",
    description: "读取或保存用量面板偏好（默认模式/时间范围）。不传参数=读取；set=保存。",
    inputSchema: {
      type: "object",
      properties: { set: { type: "object", description: "要保存的偏好字段" } },
      additionalProperties: false,
    },
    annotations: { readOnlyHint: false, destructiveHint: false, idempotentHint: true },
    _meta: { ui: { visibility: ["app"] } },
  },
]

// 数值格式化给 markdown 用
const fmtTok = (n) => (n >= 1e6 ? (n / 1e6).toFixed(1) + "M" : n >= 1e3 ? (n / 1e3).toFixed(1) + "k" : String(n))

const fmtDur = (ms) => (ms >= 3600000 ? (ms / 3600000).toFixed(1) + " 小时" : Math.round(ms / 60000) + " 分钟")

function markdown(stats) {
  const lines = []
  const sm = stats.summary
  if (sm) {
    const peak = Math.max(...sm.all.heat.values)
    lines.push(`**累计 ${fmtTok(sm.all.total)} ${sm.unit === "token" ? "Token" : "积分"}** · 峰值 ${fmtTok(peak)}（${sm.all.peakDate}） · 最长聊天 ${fmtDur(sm.all.chatMs)} · 当前连续 ${sm.all.streak.current} 天（最长 ${sm.all.streak.longest} 天）`, ``)
  }
  if (stats.mode === "credits") {
    const b = stats.builtin
    lines.push(`## 内置模型 Credits`, `${b.turns} 轮，共 ${b.credits} Credits`, ``, `| 日期 | 轮次 | Credits |`, `|---|---|---|`)
    for (const d of b.byDay) lines.push(`| ${d.date} | ${d.turns} | ${d.credits} |`)
  } else {
    const t = stats.token
    lines.push(`## 全部模型 Token（合并）`, `${t.requests} 次请求 · 输入 ${fmtTok(t.inTok)} · 输出 ${fmtTok(t.outTok)} · 缓存命中 ${fmtTok(t.cacheRead)}`, ``, `| 日期 | 输入 | 输出 | 缓存命中 |`, `|---|---|---|---|`)
    for (const d of t.byDay) lines.push(`| ${d.date} | ${fmtTok(d.inTok)} | ${fmtTok(d.outTok)} | ${fmtTok(d.cacheRead)} |`)
    const n = t.desktopBuiltinWithoutTokens
    if (n.turns) lines.push(``, `> 注：桌面端内置模型另有 ${n.turns} 轮（${n.credits} Credits）无 token 明细，未计入上表。`)
  }
  return lines.join("\n")
}

// 面板载荷：优先用内存缓存（fresh）；否则回退上次扫描快照（stale）；refresh 强制重扫并落盘快照
async function panelPayload(refresh) {
  if (!refresh) {
    const cached = peekCollect(HOST.key, "all")
    if (cached) return { ...buildPanel(cached), stale: false }
    try {
      const snap = JSON.parse(await readFile(snapshotPath, "utf8"))
      if (snap?.panel?.token) return { ...snap.panel, stale: true }
    } catch {}
  }
  const collected = await collect(HOST.key, "all", true)
  const panel = buildPanel(collected)
  try {
    await mkdir(dirname(snapshotPath), { recursive: true })
    await writeFile(snapshotPath, JSON.stringify({ at: Date.now(), panel }))
  } catch {}
  return { ...panel, stale: false }
}

async function callTool(name, args) {
  if (name === "usage_stats") {
    if (args.detail === "panel") {
      const payload = await panelPayload(args.refresh === true)
      log(`usage_stats panel host=${HOST.key} stale=${payload.stale} bytes=${JSON.stringify(payload).length}`)
      return { content: [{ type: "text", text: "面板统计数据已返回" }], structuredContent: payload }
    }
    const stats = await buildStats({
      mode: args.mode === "token" ? "token" : "credits",
      client: HOST.key,
      days: Number.isInteger(args.days) && args.days > 0 ? args.days : null,
      source: ["desktop", "gateway"].includes(args.source) ? args.source : "all",
      refresh: args.refresh === true,
    })
    let payload = stats
    if (args.detail !== "full") {
      payload = structuredClone(stats)
      delete payload.builtin.bySession
      delete payload.token.bySession
      delete payload.summary.all.heat
      delete payload.summary.range.series
    }
    log(`usage_stats ok mode=${args.mode} host=${HOST.key} bytes=${JSON.stringify(payload).length}`)
    return { content: [{ type: "text", text: markdown(stats) }], structuredContent: payload }
  }
  if (name === "usage_dashboard") {
    return { content: [{ type: "text", text: "打开用量统计面板" }], structuredContent: { ok: true } }
  }
  if (name === "usage_prefs") {
    if (args.set && typeof args.set === "object") {
      const s = args.set
      if (["credits", "token"].includes(s.mode)) prefs.mode = s.mode
      if (Number.isInteger(s.days) && s.days > 0) prefs.days = s.days
      delete prefs.source
      delete prefs.client
      await savePrefs()
    }
    return { content: [{ type: "text", text: JSON.stringify(prefs) }], structuredContent: prefs }
  }
  return { isError: true, content: [{ type: "text", text: `未知工具: ${name}` }] }
}

const reply = (message) => {
  try {
    const s = JSON.stringify(message)
    log(`reply id=${message.id ?? "-"} err=${message.error ? message.error.message : "no"} bytes=${s.length}`)
  } catch {}
  process.stdout.write(`${JSON.stringify({ jsonrpc: "2.0", ...message })}\n`)
}

function handle(request) {
  if (!request || request.jsonrpc !== "2.0" || typeof request.method !== "string") {
    return reply({ id: null, error: { code: -32600, message: "Invalid request" } })
  }
  if (request.id === undefined) { log(`notify ${request.method}`); return } // 通知直接忽略
  if (typeof request.id !== "string" && typeof request.id !== "number") {
    return reply({ id: null, error: { code: -32600, message: "Invalid request identifier" } })
  }
  const { id, method, params = {} } = request
  const fail = (code, message) => reply({ id, error: { code, message } })
  if (!ok(params)) return fail(-32602, "Parameters must be an object")
  log(`req id=${id} ${method} ${JSON.stringify(params).slice(0, 300)}`)
  switch (method) {
    case "initialize":
      return reply({ id, result: {
        protocolVersion: ["2024-11-05", "2025-03-26", "2025-06-18", "2025-11-25"].includes(params.protocolVersion) ? params.protocolVersion : "2025-11-25",
        capabilities: { tools: {}, resources: {} },
        serverInfo: { name: "qoder-usage", version: VERSION },
      } })
    case "ping": return reply({ id, result: {} })
    case "tools/list": return reply({ id, result: { tools } })
    case "resources/list":
      return reply({ id, result: { resources: [{ uri: resourceUri, name: "Qoder 用量统计面板", mimeType: "text/html;profile=mcp-app" }] } })
    case "resources/read":
      if (params.uri !== resourceUri) return fail(-32602, "Resource not found")
      return reply({ id, result: { contents: [{ uri: resourceUri, mimeType: "text/html;profile=mcp-app", text: html }] } })
    case "tools/call": {
      if (typeof params.name !== "string") return fail(-32602, "Invalid tool name")
      const args = params.arguments ?? {}
      if (!ok(args)) return fail(-32602, "Tool arguments must be an object")
      callTool(params.name, args)
        .then((result) => reply({ id, result }))
        .catch((e) => reply({ id, result: { isError: true, content: [{ type: "text", text: `统计失败: ${e?.message ?? e}` }] } }))
      return
    }
    default: return fail(-32601, "Method not supported")
  }
}

const maxLineBytes = 4 * 1024 * 1024 // 面板 HTML 走 resources/read，工具入参本身很小
let buffer = Buffer.alloc(0)
process.stdin.on("data", (chunk) => {
  buffer = Buffer.concat([buffer, chunk])
  let end
  while ((end = buffer.indexOf(10)) !== -1) {
    const line = buffer.subarray(0, end)
    buffer = buffer.subarray(end + 1)
    if (line.length > maxLineBytes) { process.exit(1) }
    if (!line.toString("utf8").trim()) continue
    try { handle(JSON.parse(line.toString("utf8"))) }
    catch { reply({ id: null, error: { code: -32700, message: "Invalid JSON" } }) }
  }
  if (buffer.length > maxLineBytes) process.exit(1)
})
