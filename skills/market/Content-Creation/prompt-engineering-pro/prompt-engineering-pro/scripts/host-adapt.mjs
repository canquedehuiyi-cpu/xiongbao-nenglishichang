#!/usr/bin/env node
// host-adapt.mjs — 多宿主适配引擎（v1.1.0）
// 功能: 把核心包自动生成各宿主部署格式——Claude Code / Codex(AGENTS.md) / Cursor / ChatGPT 指令 / 通用 SKILL.md（默认），
//       校验 frontmatter（name/description）合规；输出到本工作区 host-out/ 供用户自行放置。
// 安全: 仅生成部署文件骨架，不执行任何宿主侧命令、不写宿主配置目录（输出到 host-out/）。
// 确定性: 纯模板拼接 + frontmatter 校验，同一输入恒同输出。
// 用法:
//   node scripts/host-adapt.mjs --host claude     # 生成 Claude Code 部署格式到 host-out/claude/
//   node scripts/host-adapt.mjs --host all        # 生成全部宿主格式
//   node scripts/host-adapt.mjs --list            # 列出宿主
//   node scripts/host-adapt.mjs --host claude --json
import { readFileSync, writeFileSync, existsSync, mkdirSync } from "node:fs";
import { join, resolve, sep } from "node:path";
import { ROOT, safeId, isMain, makeOpt } from "./lib.mjs";

// 宿主定义：目录结构 + 部署说明（不执行宿主命令，仅生成骨架）
const HOSTS = {
  claude: { dir: ".claude/skills", file: "SKILL.md", note: "Claude Code：将文件放入项目 .claude/skills/<name>/SKILL.md 后自动加载" },
  codex: { dir: ".codex", file: "AGENTS.md", note: "Codex/OpenAI：将生成内容追加到项目根 AGENTS.md（作为技能段落）" },
  cursor: { dir: ".cursor/rules", file: "SKILL.md.mdc", note: "Cursor：将文件放入 .cursor/rules/SKILL.md.mdc，在 Rules 中启用" },
  chatgpt: { dir: ".chatgpt", file: "instructions.txt", note: "ChatGPT：将内容粘贴到项目 Instructions（自定义指令）" },
  generic: { dir: "skills", file: "SKILL.md", note: "通用 SKILL.md（默认）：放入宿主 skills 目录或随包分发" },
};

// frontmatter 校验：name 3-64 且小写/数字/连字符；description 1-1024；version SemVer
export function checkFrontmatter({ name = "", description = "", version = "" } = {}) {
  const issues = [];
  if (!/^[a-z][a-z0-9-]{2,63}$/.test(name)) issues.push(`name 不合法（须 3-64 位小写字母/数字/连字符且字母开头）: ${name || "（空）"}`);
  if (!description || description.length < 1 || description.length > 1024) issues.push(`description 长度须 1-1024（当前 ${description.length}）`);
  if (!/^\d+\.\d+\.\d+$/.test(version)) issues.push(`version 须为 x.y.z 格式: ${version || "（空）"}`);
  return { ok: issues.length === 0, issues };
}

// 读取并解析 SKILL.md frontmatter（仅头部 --- 块）
export function parseFrontmatter(skillMd) {
  const m = String(skillMd || "").match(/^---\r?\n([\s\S]*?)\r?\n---/);
  if (!m) return { ok: false, issues: ["SKILL.md 缺少 frontmatter（--- 块）"], data: null };
  const data = {};
  for (const line of m[1].split(/\r?\n/)) {
    const kv = line.match(/^([A-Za-z_][\w-]*):\s*(.*)$/);
    if (kv) data[kv[1].trim()] = kv[2].trim();
  }
  const check = checkFrontmatter({ name: data.name, description: data.description, version: data.version });
  return { ok: check.ok, issues: check.issues, data };
}

// 核心指令摘要：取 SKILL.md 中 frontmatter 之后的"概述/使用场景"节文本（供宿主格式复用）
function coreSection(skillMd) {
  const m = String(skillMd || "").match(/^---\r?\n[\s\S]*?\r?\n---\r?\n([\s\S]{0,1800})/);
  return (m ? m[1] : String(skillMd || "").slice(0, 1800)).trim();
}

// 输出目录安全边界：仅允许包内 host-out（写宿主配置目录被禁止）
function safePathOut(outDir) {
  const abs = join(ROOT, "host-out");
  const userAbs = resolve(ROOT, String(outDir));
  if (userAbs !== abs && !userAbs.startsWith(abs + sep)) {
    throw new Error(`安全边界: host-adapt 输出仅允许 host-out/（不写宿主配置目录）: ${outDir}`);
  }
  return abs;
}

// 生成单宿主部署文件
export function adapt({ host = "generic", skillMdPath = join(ROOT, "SKILL.md"), outDir = join(ROOT, "host-out") } = {}) {
  const def = HOSTS[host];
  if (!def) throw new Error(`未知宿主: ${host}（可用 --list 查看；支持 ${Object.keys(HOSTS).join("/")}）`);
  if (!existsSync(skillMdPath)) throw new Error(`SKILL.md 不存在: ${skillMdPath}`);
  const raw = readFileSync(skillMdPath, "utf8");
  const fm = parseFrontmatter(raw);
  const name = fm.data?.name || "prompt-engineering-pro";
  const safe = safeId(name);
  const core = coreSection(raw);
  let content = "";
  if (host === "claude" || host === "generic") {
    content = raw; // 原样 SKILL.md
  } else if (host === "codex") {
    content = `# ${name}（由 host-adapt 生成，v1.1.0）\n\n> 追加到项目 AGENTS.md 的技能段落。核心包见 skills/${safe}/。\n\n## 技能：${name}\n\n${core}`;
  } else if (host === "cursor") {
    content = `---\ndescription: ${fm.data?.description || ""}\nglobs: []\n---\n\n# ${name}\n\n${core}`;
  } else if (host === "chatgpt") {
    content = `# ${name} 技能指令（由 host-adapt 生成，v1.1.0）\n\n${core}`;
  }
  const targetDir = join(safePathOut(outDir), safe);
  mkdirSync(targetDir, { recursive: true });
  const file = join(targetDir, def.file);
  writeFileSync(file, content + (content.endsWith("\n") ? "" : "\n"), "utf8");
  return {
    ok: true,
    meta: { engine: "host-adapt.mjs v1.1.0" },
    host,
    target: file,
    note: def.note,
    frontmatter: { ok: fm.ok, issues: fm.issues, name, version: fm.data?.version },
  };
}

// ================= CLI =================
if (isMain(import.meta)) {
  const args = process.argv.slice(2);
  const opt = makeOpt(args);
  if (args.includes("--help") || args.includes("-h") || args.includes("--list")) {
    console.log("用法: node scripts/host-adapt.mjs --host <claude|codex|cursor|chatgpt|generic|all> [--json]");
    console.log("说明: 仅生成部署骨架到 host-out/，不执行宿主命令、不写宿主配置目录。");
    console.log("宿主:");
    for (const [k, v] of Object.entries(HOSTS)) console.log(`  ${k}: ${v.note}`);
    process.exit(0);
  }
  const wantJson = args.includes("--json");
  const host = opt("host") || "generic";
  if (!HOSTS[host] && host !== "all") {
    console.error(`✗ 未知宿主: ${host}（--list 查看）`);
    process.exit(2);
  }
  const hosts = host === "all" ? Object.keys(HOSTS) : [host];
  const results = [];
  let fail = 0;
  for (const h of hosts) {
    try {
      const r = adapt({ host: h });
      results.push(r);
      if (r.frontmatter.ok) console.log(`✓ ${h}: → ${r.target}（${r.note}）`);
      else { console.log(`⚠ ${h}: 生成成功但 frontmatter 有 ${r.frontmatter.issues.length} 项问题`); for (const i of r.frontmatter.issues) console.log(`    - ${i}`); }
    } catch (e) {
      fail++;
      console.error(`✗ ${h}: ${e.message}`);
    }
  }
  if (wantJson) process.stdout.write(JSON.stringify({ ok: fail === 0, results }, null, 2) + "\n");
  process.exit(fail ? 1 : 0);
}
