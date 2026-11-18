#!/usr/bin/env node
// version-store.mjs — 版本库引擎（P5，对应 data/versions）
// 能力:
//   1. 快照写入: 每次构建/优化产出 {id, input_hash, fingerprint, prompt, qscore 各维, intent, ts}
//   2. before/after 对比: 输出各维增量（Q-Score 变化可追溯, P6 版本化）
//   3. 回滚: 恢复到指定版本（git 友好, 文件可 diff）
//   4. 目录可注入: --dir <path> 支持测试时指向临时目录（不污染真实 data/）
// 设计原则: 确定性、可追溯、版本不可变（写后不修改）
// 用法:
//   node scripts/version-store.mjs snapshot --prompt <text> --score 78 --dims '{"clarity":88}' --intent improve
//   node scripts/version-store.mjs list
//   node scripts/version-store.mjs compare --from <id> --to <id>
//   node scripts/version-store.mjs rollback --to <id> --prompt <text>   # 将 prompt 恢复到目标版本
import { readFileSync, writeFileSync, existsSync, readdirSync } from "node:fs";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";
import { createHash } from "node:crypto";
import { ensureDir, ts, safeDir, safeId, safePath, isMain , makeOpt } from "./lib.mjs";

const ROOT = join(dirname(fileURLToPath(import.meta.url)), "..");
const DEFAULT_DIR = join(ROOT, "data", "versions");

// ensureDir / ts 由 lib.mjs 提供（消除跨脚本重复）
function hash(text) { return createHash("sha256").update(String(text)).digest("hex").slice(0, 12); }

// ================= 核心 API =================
export function snapshot({ dir = DEFAULT_DIR, prompt, score, dims = {}, intent = "build", fingerprint = {}, id = null } = {}) {
  if (!prompt || !prompt.trim()) throw new Error("snapshot 需要 prompt");
  dir = safePath(dir); // v1.0.3 安全修复: API 层纵深防护，禁止写入包外任意位置
  ensureDir(dir);
  // v1.0.3 安全修复: 用户传入的 --id 须经 safeId 清洗，防止 "../../" 路径穿越逃逸数据目录
  const versionId = id ? safeId(id) : `${safeId(intent)}-${ts()}-${hash(prompt).slice(0, 6)}`;
  // 版本不可变：同名快照已存在时不覆盖，追加 -r{n} 后缀（保留历史）
  let finalId = versionId;
  if (!id) {
    let n = 1;
    const base = versionId;
    // v1.0.3 修复: 防重循环加上界，避免极端情况下无限循环
    while (existsSync(join(dir, `${finalId}.json`)) && n <= 10000) finalId = `${base}-r${n++}`;
  }
  const record = {
    id: finalId,
    input_hash: hash(prompt),
    fingerprint,
    intent,
    qscore: typeof score === "number" ? score : null,
    dims,
    prompt,
    ts: ts(),
    immutable: true,
  };
  writeFileSync(join(dir, `${finalId}.json`), JSON.stringify(record, null, 2) + "\n", "utf8");
  return record;
}

export function loadVersion({ dir = DEFAULT_DIR, id }) {
  const p = join(dir, `${id}.json`);
  if (!existsSync(p)) throw new Error(`版本不存在: ${id}`);
  return JSON.parse(readFileSync(p, "utf8"));
}

export function listVersions({ dir = DEFAULT_DIR } = {}) {
  if (!existsSync(dir)) return [];
  return readdirSync(dir)
    .filter((f) => f.endsWith(".json") && !f.startsWith("."))
    .map((f) => {
      // fail-safe：损坏 JSON 优雅跳过，不拖垮整个列表（攻击 A-20 修复）
      try {
        return JSON.parse(readFileSync(join(dir, f), "utf8"));
      } catch {
        return null; // 跳过损坏文件
      }
    })
    // v1.0.3 修复: 仅保留真正的版本记录（含 id 与 prompt 字段）。
    // 共享/数据目录中混入的其他 JSON（如 search-cache、evolve 记录）此前会让
    // CLI 渲染 v.prompt.slice() 崩溃（Cannot read properties of undefined）
    .filter((v) => v !== null && typeof v === "object" && typeof v.id === "string" && typeof v.prompt === "string")
    // v1.0.3 修复: 排序比较器补全相等分支，避免依赖实现的未定义行为
    .sort((a, b) => (a.ts > b.ts ? 1 : a.ts < b.ts ? -1 : 0));
}

export function compareVersions({ dir = DEFAULT_DIR, from, to }) {
  const a = loadVersion({ dir, id: from });
  const b = loadVersion({ dir, id: to });
  const dimKeys = new Set([...Object.keys(a.dims || {}), ...Object.keys(b.dims || {})]);
  const dimDeltas = {};
  for (const k of dimKeys) {
    const av = a.dims?.[k];
    const bv = b.dims?.[k];
    if (typeof av === "number" && typeof bv === "number") dimDeltas[k] = bv - av;
  }
  return {
    from: { id: a.id, qscore: a.qscore },
    to: { id: b.id, qscore: b.qscore },
    qscore_delta: b.qscore != null && a.qscore != null ? b.qscore - a.qscore : null,
    dim_deltas: dimDeltas,
    prompt_changed: a.prompt !== b.prompt,
    prompt_old: a.prompt.slice(0, 60),
    prompt_new: b.prompt.slice(0, 60),
  };
}

export function rollbackPrompt({ dir = DEFAULT_DIR, to, currentPrompt }) {
  const target = loadVersion({ dir, id: to });
  // v1.0.3 修复: 不再忽略 currentPrompt 参数，返回新旧对比供调用方确认
  return {
    rolled_back_to: target.id,
    prompt: target.prompt,
    previous_prompt: typeof currentPrompt === "string" ? currentPrompt.slice(0, 120) : null,
    changed: typeof currentPrompt === "string" ? currentPrompt !== target.prompt : null,
    note: "回滚到历史版本（原版本不可变，请保存新快照）",
  };
}

// ================= 提示词 diff（人类可读行级对比，v1.0.3 新增） =================
// 基于 LCS 的行级差异：输出 删除行/新增行 及统计，替代仅截断字符串的对比视图。
export function promptDiff({ textA, textB }) {
  const a = String(textA ?? "").split(/\r?\n/);
  const b = String(textB ?? "").split(/\r?\n/);
  const n = a.length;
  const m = b.length;
  // LCS DP（O(n*m)，提示词行数通常很小）
  const dp = Array.from({ length: n + 1 }, () => new Array(m + 1).fill(0));
  for (let i = n - 1; i >= 0; i--) {
    for (let j = m - 1; j >= 0; j--) {
      dp[i][j] = a[i] === b[j] ? dp[i + 1][j + 1] + 1 : Math.max(dp[i + 1][j], dp[i][j + 1]);
    }
  }
  const removed = [];
  const added = [];
  let i = 0;
  let j = 0;
  while (i < n && j < m) {
    if (a[i] === b[j]) {
      i++;
      j++;
    } else if (dp[i + 1][j] >= dp[i][j + 1]) {
      removed.push(a[i]);
      i++;
    } else {
      added.push(b[j]);
      j++;
    }
  }
  while (i < n) {
    removed.push(a[i]);
    i++;
  }
  while (j < m) {
    added.push(b[j]);
    j++;
  }
  return {
    changed: removed.length > 0 || added.length > 0,
    removed,
    added,
    removed_count: removed.length,
    added_count: added.length,
    unchanged_count: n - removed.length,
  };
}

// ================= CLI =================
// v1.0.3 修复: 改用 lib.isMain 的稳健判定（Windows 含空格/中文路径下不再误判）
if (isMain(import.meta)) {
  const args = process.argv.slice(2);
  if (args.includes("--help") || args.includes("-h")) {
    console.log("用法: node " + process.argv[1].split(/[\\/]/).pop() + " [选项]（完整用法见脚本头部注释）");
    process.exit(0);
  }
  const cmd = args[0];
  const opt = makeOpt(args); // v1.0.3 去重: 公共库统一参数解析
  // v1.0.3 安全修复: --dir 须经安全边界校验，禁止写入包外任意位置（原路径穿越漏洞）
  const dir = safeDir(opt("dir"), DEFAULT_DIR);
  const wantJson = args.includes("--json");

  try {
    let out;
    switch (cmd) {
      case "snapshot": {
        const prompt = opt("prompt");
        const score = opt("score") != null ? Number(opt("score")) : null;
        let dims = {};
        if (opt("dims")) dims = JSON.parse(opt("dims"));
        out = snapshot({ dir, prompt, score, dims, intent: opt("intent") || "build" });
        break;
      }
      case "list":
        out = listVersions({ dir });
        break;
      case "compare":
        out = compareVersions({ dir, from: opt("from"), to: opt("to") });
        break;
      case "rollback":
        out = rollbackPrompt({ dir, to: opt("to") });
        break;
      case "diff": {
        const a = loadVersion({ dir, id: opt("from") });
        const b = loadVersion({ dir, id: opt("to") });
        const d = promptDiff({ textA: a.prompt, textB: b.prompt });
        out = { from: a.id, to: b.id, ...d };
        break;
      }
      default:
        throw new Error("用法: snapshot|list|compare|rollback|diff（--dir 可注入目录）");
    }
    if (wantJson) process.stdout.write(JSON.stringify(out, null, 2) + "\n");
    else if (cmd === "list") {
      // v1.0.3 修复: 渲染前防御（listVersions 已过滤非版本记录，此处兜底）
      for (const v of out) console.log(`  ${v.id}  ${v.intent}  QScore=${v.qscore ?? "-"}  ${v.ts}  ${String(v.prompt ?? "").slice(0, 40)}`);
      console.log(`共 ${out.length} 个版本`);
    } else if (cmd === "compare") {
      console.log(`对比 ${out.from.id} → ${out.to.id}`);
      console.log(`Q-Score: ${out.from.qscore} → ${out.to.qscore}（Δ${out.qscore_delta}）`);
      console.log(`维度增量: ${JSON.stringify(out.dim_deltas)}`);
      console.log(`提示词变更: ${out.prompt_changed ? "是" : "否"}`);
    } else if (cmd === "rollback") {
      console.log(`已回滚到 ${out.rolled_back_to}（新内容请另存快照）`);
    } else if (cmd === "diff") {
      console.log(`提示词 diff ${out.from} → ${out.to}（删除 ${out.removed_count} / 新增 ${out.added_count} / 未变 ${out.unchanged_count}）`);
      for (const l of out.removed) console.log(`  - ${l}`);
      for (const l of out.added) console.log(`  + ${l}`);
      if (!out.changed) console.log("  （无差异）");
    } else {
      console.log(`快照已写入: ${out.id}（QScore=${out.qscore}）`);
    }
  } catch (e) {
    console.error(`错误: ${e.message}`);
    process.exit(1);
  }
}
