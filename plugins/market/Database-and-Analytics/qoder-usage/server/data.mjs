// 两个 Qoder 客户端的本地数据库与会话日志定位。
import { homedir } from "node:os"
import { join } from "node:path"

const home = homedir()
const appData = process.env.APPDATA || join(home, "AppData", "Roaming")

export const CLIENTS = {
  qoder: {
    key: "qoder",
    label: "Qoder",
    dbPath: join(appData, "com.qoder.app.stable", "main.sqlite"),
    projectsDir: join(home, ".qoder", "projects"),
    dynamicText: join(appData, "com.qoder.app.stable", "dynamic-text", "qoder.v1.json"),
  },
  "qoder-cn": {
    key: "qoder-cn",
    label: "Qoder CN",
    dbPath: join(appData, "com.qodercn.app.stable", "main.sqlite"),
    projectsDir: join(home, ".qoder-cn", "projects"),
    dynamicText: join(appData, "com.qodercn.app.stable", "dynamic-text", "qoder.v1.json"),
  },
}

let DatabaseSync = null
try {
  ;({ DatabaseSync } = await import("node:sqlite"))
} catch {
  DatabaseSync = null
}

// 只读打开 main.sqlite；文件缺失、被锁或不支持 node:sqlite 时返回 null。
export function openDb(path) {
  if (!DatabaseSync) return null
  try {
    return new DatabaseSync(path, { readOnly: true })
  } catch {
    return null
  }
}

// 一个客户端的全部本地数据：会话元数据 + 每轮 credits（内置模型）。
// 出错一律返回空结果，调用方按空数据降级。
// credits 不再按会话整段剔除 BYOK——每轮模型由聚合层按 jsonl 的 businessModelKey 精确判定。
export function readClient(client) {
  const out = { key: client.key, label: client.label, sessions: new Map(), turns: [], messages: [] }
  const db = openDb(client.dbPath)
  if (!db) return out
  try {
    for (const row of db.prepare(
      "SELECT session_id, title, cwd, model, created_at, updated_at FROM chat_sessions"
    ).all()) {
      out.sessions.set(row.session_id, {
        sessionId: row.session_id,
        title: row.title || "",
        cwd: row.cwd || "",
        model: row.model || "",
        createdAt: Number(row.created_at) || 0,
        updatedAt: Number(row.updated_at) || 0,
      })
    }
    for (const row of db.prepare(
      "SELECT session_id, turn_id, turn_credits, created_at FROM chat_session_messages WHERE role='assistant' AND turn_credits IS NOT NULL"
    ).all()) {
      out.turns.push({
        sessionId: row.session_id,
        turnId: row.turn_id || "",
        credits: Number(row.turn_credits) || 0,
        ts: Number(row.created_at) || 0,
      })
    }
    for (const row of db.prepare(
      "SELECT session_id, created_at FROM chat_session_messages WHERE created_at > 0 ORDER BY session_id, created_at"
    ).all()) {
      out.messages.push({ sessionId: row.session_id, ts: Number(row.created_at) || 0 })
    }
  } catch {
    // 表不存在等结构差异：返回已读到的部分
  } finally {
    try { db.close() } catch {}
  }
  return out
}
