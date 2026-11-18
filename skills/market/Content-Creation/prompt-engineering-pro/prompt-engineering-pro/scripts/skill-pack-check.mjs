#!/usr/bin/env node
// skill-pack-check.mjs — Skill 包发布合规引擎（P0，对应发布闭环）
// 能力:
//   1. 检查模式: 按平台 Skill 包规范核验目录结构合规性
//      （SKILL.md 根目录 / name 3-64 小写数字连字符 / description 1-1024 / version SemVer /
//       文件数 ≤300 / ZIP 预估 ≤10MB / 无二进制 / data 目录不随包分发 / 无系统垃圾文件）
//   2. 打包模式: --build 生成 <名>.zip（零依赖 ZIP 写入器，排除运行时 data/ 与临时文件）
// 设计原则: 只做结构合规与打包；内容安全扫描交给 scan-safety（本引擎不重复）
// 用法:
//   node scripts/skill-pack-check.mjs --dir <skill目录>
//   node scripts/skill-pack-check.mjs --dir <skill目录> --build --out <输出.zip>
//   node scripts/skill-pack-check.mjs --dir <skill目录> --json
import { readFileSync, writeFileSync, readdirSync, statSync, existsSync, mkdirSync } from "node:fs";
import { join, dirname, relative, basename, extname } from "node:path";
import { fileURLToPath } from "node:url";
import { deflateRawSync } from "node:zlib";
import { safePath, isMain, makeOpt } from "./lib.mjs";

const ROOT = join(dirname(fileURLToPath(import.meta.url)), "..");

// ---- 规范常量（平台 Skill 包官方规范） ----
const LIMITS = {
  maxFiles: 300,
  maxZipMB: 10,
  nameMin: 3,
  nameMax: 64,
  descMax: 1024,
  descMaxBytes: 1024, // Coze 等平台按 UTF-8 字节校验 description（业界规范"1024 字符"在部分平台实现为字节）
  nameRe: /^[a-z0-9-]+$/,
  versionRe: /^\d+\.\d+\.\d+$/,
};
// 二进制扩展名（技能包规范：禁二进制，仅文本文件）
const BINARY_EXT = new Set([
  ".png", ".jpg", ".jpeg", ".gif", ".webp", ".ico", ".bmp", ".svg",
  ".zip", ".tar", ".gz", ".7z", ".rar",
  ".exe", ".dll", ".so", ".dylib", ".bin", ".o", ".a",
  ".mp3", ".mp4", ".wav", ".avi", ".mov",
]);
// 系统垃圾文件
const JUNK = new Set([".DS_Store", "Thumbs.db", "desktop.ini", ".gitkeep"]);
// 运行时目录（不随包分发；host-out 为 host-adapt 生成产物，data 为运行时数据）
const RUNTIME_DIRS = new Set(["data", "host-out"]);

function listFiles(root) {
  const out = [];
  const walk = (cur) => {
    for (const name of readdirSync(cur)) {
      const p = join(cur, name);
      const st = statSync(p);
      if (st.isDirectory()) walk(p);
      else out.push(p);
    }
  };
  walk(root);
  return out;
}

function parseFrontmatter(text) {
  const m = /^---\r?\n([\s\S]*?)\r?\n---/.exec(text);
  if (!m) return {};
  const out = {};
  for (const line of m[1].split("\n")) {
    const kv = /^([A-Za-z0-9_]+):\s*(.*)$/.exec(line);
    if (kv) out[kv[1]] = kv[2];
  }
  return out;
}

export function checkSkillPack({ dir = ROOT } = {}) {
  const base = safePath(dir);
  const issues = [];
  const checks = [];
  const add = (name, ok, detail) => checks.push({ name, ok, detail });

  // SKILL.md 根目录
  const skillMd = join(base, "SKILL.md");
  const hasSkill = existsSync(skillMd);
  add("SKILL.md 位于根目录", hasSkill, hasSkill ? basename(skillMd) : "未找到 SKILL.md");
  if (!hasSkill) {
    return { ok: false, checks, issues: ["缺少 SKILL.md"], summary: "缺少 SKILL.md，非合法 skill 包" };
  }

  // frontmatter
  const meta = parseFrontmatter(readFileSync(skillMd, "utf8"));
  const name = String(meta.name || "");
  const desc = String(meta.description || "");
  const version = String(meta.version || "");

  add("name 3-64 且小写/数字/连字符",
    name.length >= LIMITS.nameMin && name.length <= LIMITS.nameMax && LIMITS.nameRe.test(name),
    name ? `name="${name}"` : "name 缺失");
  add("description 1-1024 字符",
    desc.length >= 1 && desc.length <= LIMITS.descMax,
    `description ${desc.length} 字符`);
  const descBytes = Buffer.byteLength(desc, "utf8");
  add(`description UTF-8 字节 ≤${LIMITS.descMaxBytes}（跨平台兼容）`,
    descBytes <= LIMITS.descMaxBytes,
    `${descBytes} 字节（中文按 UTF-8 计字节，Coze 等平台按字节校验）`);
  add("version SemVer（x.y.z）",
    LIMITS.versionRe.test(version),
    version ? `version="${version}"` : "version 缺失");

  // 文件清单
  let files;
  try {
    files = listFiles(base);
  } catch (e) {
    return { ok: false, checks, issues: [`读取目录失败: ${e.message}`], summary: "读取目录失败" };
  }
  const rels = files.map((f) => relative(base, f).replace(/\\/g, "/"));

  // 二进制
  const binaries = rels.filter((r) => BINARY_EXT.has(extname(r).toLowerCase()));
  add("无二进制文件", binaries.length === 0, binaries.length ? `发现 ${binaries.length} 个: ${binaries.slice(0, 5).join(", ")}` : `共 ${files.length} 个文本/数据文件`);

  // 运行时目录（data/ 与 host-out/）
  const dataFiles = rels.filter((r) => RUNTIME_DIRS.has(r.split("/")[0]));
  add("运行时目录不随包分发", dataFiles.length === 0, dataFiles.length ? `发现 ${dataFiles.length} 个: ${dataFiles.slice(0, 5).join(", ")}` : "无 data/ host-out/ 文件");

  // 系统垃圾
  const junks = rels.filter((r) => JUNK.has(basename(r)) || extname(r) === ".tmp" || extname(r) === ".log" || basename(r).startsWith("~$"));
  add("无系统垃圾文件", junks.length === 0, junks.length ? `发现 ${junks.join(", ")}` : "无系统垃圾文件");

  // references/data 历史坑
  const refData = rels.filter((r) => r.startsWith("references/data/"));
  add("无 references/data 路径", refData.length === 0, refData.length ? `发现 ${refData.join(", ")}` : "无 references/data 路径");

  // 文件数
  add(`文件数 ≤${LIMITS.maxFiles}`, files.length <= LIMITS.maxFiles, `${files.length}/${LIMITS.maxFiles}`);

  // 预估 ZIP 大小（原始字节 ×0.6 粗估）
  let totalBytes = 0;
  for (const f of files) totalBytes += statSync(f).size;
  const estMB = totalBytes * 0.6 / (1024 * 1024);
  add(`ZIP 预估 ≤${LIMITS.maxZipMB}MB`, estMB <= LIMITS.maxZipMB, `${estMB.toFixed(2)}MB（原始 ${(totalBytes / 1024 / 1024).toFixed(2)}MB）`);

  const failed = checks.filter((c) => !c.ok);
  return {
    ok: failed.length === 0,
    checks,
    issues: failed.map((c) => c.name),
    summary: failed.length ? `合规检查未通过（${failed.length} 项）` : `合规检查通过（${checks.length} 项全部满足）`,
    file_count: files.length,
    est_zip_mb: estMB,
  };
}

// ---- 零依赖 ZIP 写入器（ZIP 格式：本地头 + 中央目录 + EOCD，数据用 deflateRaw） ----
const CRC_TABLE = (() => {
  const t = new Uint32Array(256);
  for (let n = 0; n < 256; n++) {
    let c = n;
    for (let k = 0; k < 8; k++) c = c & 1 ? 0xedb88320 ^ (c >>> 1) : c >>> 1;
    t[n] = c >>> 0;
  }
  return t;
})();

function crc32(buf) {
  let c = 0xffffffff;
  for (let i = 0; i < buf.length; i++) c = CRC_TABLE[(c ^ buf[i]) & 0xff] ^ (c >>> 8);
  return (c ^ 0xffffffff) >>> 0;
}

export function buildZip(files) {
  // files: [{ path: "SKILL.md", data: Buffer }]
  // 返回 Buffer；同一路径去重（保留后出现者），目录名规范为 <zipRoot>/<path>
  const seen = new Set();
  const entries = [];
  for (const f of files) {
    if (seen.has(f.path)) continue;
    seen.add(f.path);
    entries.push(f);
  }
  const localParts = [];
  const centralParts = [];
  let offset = 0;
  for (const e of entries) {
    const nameBuf = Buffer.from(e.path, "utf8");
    const crc = crc32(e.data);
    const compressed = deflateRawSync(e.data, { level: 6 });
    const method = compressed.length < e.data.length ? 8 : 0; // 8=deflate, 0=store
    const data = method === 8 ? compressed : e.data;
    const lh = Buffer.alloc(30);
    lh.writeUInt32LE(0x04034b50, 0);        // local header sig
    lh.writeUInt16LE(20, 4);                // version needed
    lh.writeUInt16LE(0x0800, 6);            // flags: UTF-8
    lh.writeUInt16LE(method, 8);
    lh.writeUInt16LE(0, 10);                // mod time
    lh.writeUInt16LE(0x21, 12);             // mod date
    lh.writeUInt32LE(crc, 14);
    lh.writeUInt32LE(data.length, 18);      // compressed size
    lh.writeUInt32LE(e.data.length, 22);    // uncompressed size
    lh.writeUInt16LE(nameBuf.length, 26);
    lh.writeUInt16LE(0, 28);                // extra len
    localParts.push(lh, nameBuf, data);

    const ch = Buffer.alloc(46);
    ch.writeUInt32LE(0x02014b50, 0);        // central sig
    ch.writeUInt16LE(20, 4);
    ch.writeUInt16LE(20, 6);
    ch.writeUInt16LE(0x0800, 8);
    ch.writeUInt16LE(method, 10);
    ch.writeUInt16LE(0, 12);
    ch.writeUInt16LE(0x21, 14);
    ch.writeUInt32LE(crc, 16);
    ch.writeUInt32LE(data.length, 20);
    ch.writeUInt32LE(e.data.length, 24);
    ch.writeUInt16LE(nameBuf.length, 28);
    ch.writeUInt16LE(0, 30);                // extra
    ch.writeUInt16LE(0, 32);                // comment
    ch.writeUInt16LE(0, 34);                // disk
    ch.writeUInt16LE(0, 36);                // internal attrs
    ch.writeUInt32LE(0, 38);                // external attrs
    ch.writeUInt32LE(offset, 42);           // local header offset
    centralParts.push(ch, nameBuf);

    offset += 30 + nameBuf.length + data.length;
  }
  const centralBuf = Buffer.concat(centralParts);
  const eocd = Buffer.alloc(22);
  eocd.writeUInt32LE(0x06054b50, 0);        // EOCD sig
  eocd.writeUInt16LE(0, 4);
  eocd.writeUInt16LE(0, 6);
  eocd.writeUInt16LE(entries.length, 8);
  eocd.writeUInt16LE(entries.length, 10);
  eocd.writeUInt32LE(centralBuf.length, 12);
  eocd.writeUInt32LE(offset, 16);
  eocd.writeUInt16LE(0, 20);
  return Buffer.concat([...localParts, centralBuf, eocd]);
}

export function buildSkillPack({ dir = ROOT, out = null, zipRoot = null } = {}) {
  const check = checkSkillPack({ dir });
  const base = safePath(dir);
  let files;
  try {
    files = listFiles(base);
  } catch (e) {
    return { ok: false, error: `读取目录失败: ${e.message}` };
  }
  const rootName = zipRoot || basename(base);
  const entries = [];
  for (const f of files) {
    const rel = relative(base, f).replace(/\\/g, "/");
    if (RUNTIME_DIRS.has(rel.split("/")[0])) continue;   // 排除运行时 data/
    if (JUNK.has(basename(f))) continue;                  // 排除系统垃圾
    if (extname(f).toLowerCase() === ".log") continue;    // 排除临时日志（validate/attack 重定向产物）
    if (BINARY_EXT.has(extname(f).toLowerCase())) continue; // 排除二进制（合规）
    entries.push({ path: `${rootName}/${rel}`, data: readFileSync(f) });
  }
  const zipBuf = buildZip(entries);
  if (out) {
    mkdirSync(dirname(out), { recursive: true });
    writeFileSync(out, zipBuf);
  }
  return {
    ok: true,
    check,
    entries: entries.length,
    zip_bytes: zipBuf.length,
    zip_mb: (zipBuf.length / 1024 / 1024).toFixed(2),
    out: out || null,
    note: check.ok ? "结构合规，已打包" : "结构存在不合规项（仍打包，请先修复）",
  };
}

// ================= CLI =================
if (isMain(import.meta)) {
  const args = process.argv.slice(2);
  const opt = makeOpt(args);
  const json = args.includes("--json");
  const build = args.includes("--build");
  const dir = opt("dir") || ROOT;
  const out = opt("out") || null;
  const zipRoot = opt("zip-root") || null;
  if (build) {
    // v1.0.4 修复: 与 check 分支一致，build 路径的 safePath 等错误同样友好输出
    let r;
    try {
      r = buildSkillPack({ dir, out, zipRoot });
    } catch (e) {
      process.stderr.write(`✗ ${e.message || String(e)}\n`);
      process.exit(2);
    }
    if (!r.ok) {
      process.stderr.write(`✗ ${r.error}\n`);
      process.exit(2);
    }
    if (json) {
      process.stdout.write(JSON.stringify(r, null, 2) + "\n");
    } else {
      process.stdout.write(`${r.check.summary}\n`);
      for (const c of r.check.checks) process.stdout.write(`  ${c.ok ? "✓" : "✗"} ${c.name}: ${c.detail}\n`);
      process.stdout.write(`已打包 ${r.entries} 个文件 → ${r.out || `${r.zip_mb}MB 内存`}（${r.zip_mb}MB）\n`);
    }
  } else {
    // v1.0.4 修复: 包裹 try/catch，safePath 等安全边界错误转为友好输出（非 0 退出，无堆栈）
    let r;
    try {
      r = checkSkillPack({ dir });
    } catch (e) {
      process.stderr.write(`✗ ${e.message || String(e)}\n`);
      process.exit(2);
    }
    if (json) {
      process.stdout.write(JSON.stringify(r, null, 2) + "\n");
    } else {
      process.stdout.write(`${r.summary}\n`);
      for (const c of r.checks) process.stdout.write(`  ${c.ok ? "✓" : "✗"} ${c.name}: ${c.detail}\n`);
    }
    if (!r.ok) process.exit(1);
  }
}
