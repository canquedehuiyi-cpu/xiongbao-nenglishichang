// 扫描 ~/.qoder(-cn)/projects/<工作目录>/<sessionId>.jsonl 的每请求 usage 与每轮模型。
// 自定义（BYOK）模型有真实 token；旧版客户端（1.1.79）的内置模型请求带 credits（新版本改写进 SQLite）。
// 每轮模型取 user 记录的 businessModelKey（requestSetId 与 SQLite 的 turn_id 一致），
// 会话中途切换模型时也能按轮精确归属。
import { readdir } from "node:fs/promises"
import { join } from "node:path"
import { createReadStream } from "node:fs"
import { createInterface } from "node:readline"

function parseLine(line) {
  try { return JSON.parse(line) } catch { return null }
}

// 只解析带 usage 的 assistant 行：一个 request_id 一行，已实测无重复。
// 带 businessModelKey 的 user 行即每轮模型（工具结果行没有这两个字段，自动跳过）。
async function parseSessionFile(path, sessionId, pushUsage, pushTurn) {
  try {
    const rl = createInterface({ input: createReadStream(path, { encoding: "utf8" }), crlfDelay: Infinity })
    for await (const line of rl) {
      if (line.includes('"usage"')) {
        const o = parseLine(line)
        if (o?.type === "assistant") {
          const u = o?.message?.usage
          if (u && typeof u === "object") {
            const inTok = Number(u.input_tokens) || 0
            const outTok = Number(u.output_tokens) || 0
            const cacheRead = Number(u.cache_read_input_tokens) || 0
            const cacheWrite = Number(u.cache_creation_input_tokens) || 0
            const credits = Number(u.credits) || 0
            if (inTok || outTok || cacheRead || cacheWrite || credits) {
              pushUsage({
                sessionId,
                ts: Date.parse(o.timestamp || "") || 0,
                model: o.message.model || "",
                // 每请求的 BYOK 标记：自定义请求带 modelSource=custom / customProviderId，
                // 内置请求没有这两个字段（旧版内置行另带 credits）。比会话级模型更精确。
                byok: o.modelSource === "custom" || Boolean(o.customProviderId),
                inTok, outTok, cacheRead, cacheWrite, credits,
              })
            }
          }
        }
      }
      if (line.includes('"businessModelKey"')) {
        const o = parseLine(line)
        if (o?.type === "user" && o.requestSetId && o.businessModelKey) {
          pushTurn({ sessionId, turnId: o.requestSetId, model: o.businessModelKey })
        }
      }
    }
  } catch {
    // 文件被占用或编码异常：跳过该文件
  }
}

// 一个客户端的 projects 目录 → { records: 每请求 usage, turns: 每轮模型 }
export async function scanProjects(client) {
  const records = []
  const turns = []
  let dirs
  try { dirs = await readdir(client.projectsDir, { withFileTypes: true }) } catch { return { records, turns } }
  for (const dir of dirs) {
    if (!dir.isDirectory()) continue
    let files
    try { files = await readdir(join(client.projectsDir, dir.name)) } catch { continue }
    for (const file of files) {
      if (!file.endsWith(".jsonl")) continue
      await parseSessionFile(
        join(client.projectsDir, dir.name, file),
        file.slice(0, -".jsonl".length),
        (r) => records.push(r),
        (t) => turns.push(t)
      )
    }
  }
  return { records, turns }
}
