// 可选数据源：magpie 网关的 usage.jsonl。
// 经网关调用的模型（含内置模型）有服务端下发的真实 token——这是内置模型 token 的唯一来源；
// 仅覆盖走网关的请求，桌面端直连的内置对话不在此列。
import { createReadStream } from "node:fs"
import { createInterface } from "node:readline"
import { access } from "node:fs/promises"
import { homedir } from "node:os"
import { join } from "node:path"

export const MAGPIE_USAGE_PATH = join(homedir(), ".config", "magpie", "usage.jsonl")

export async function scanMagpie(path) {
  try { await access(path) } catch { return [] }
  const records = []
  try {
    const rl = createInterface({ input: createReadStream(path, { encoding: "utf8" }), crlfDelay: Infinity })
    for await (const line of rl) {
      if (!line.trim() || line[0] !== "{") continue
      let o
      try { o = JSON.parse(line) } catch { continue }
      const inTok = Number(o.in) || 0
      const outTok = Number(o.out) || 0
      const cacheRead = Number(o.cache_read) || 0
      const cacheWrite = Number(o.cache_write) || 0
      if (!inTok && !outTok && !cacheRead && !cacheWrite) continue
      records.push({
        // 旧记录 t 为 ISO 字符串，新记录字段名一致
        ts: Date.parse(o.t || o.timestamp || "") || 0,
        model: o.served || o.model || "",
        agent: o.agent || "",
        inTok, outTok, cacheRead, cacheWrite,
      })
    }
  } catch {
    return records
  }
  return records
}
