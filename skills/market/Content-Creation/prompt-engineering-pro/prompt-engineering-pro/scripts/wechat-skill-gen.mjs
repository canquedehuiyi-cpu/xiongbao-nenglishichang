#!/usr/bin/env node
// wechat-skill-gen.mjs — 微信 AI 开发模式 Skill 包脚手架引擎（P1，game/ai 领域示范引擎）
// 能力:
//   1. 生成: 按微信 AI 开发模式（beta）规范生成 SKILL 包脚手架
//      （SKILL.md 业务说明 + mcp.json 能力声明），供后续填充原子接口/组件
//   2. 检查: --check 核验已有目录是否为合规 SKILL 包结构
//   3. 内测警示: 微信 AI 开发模式当前内测、未开放代码提审——生成内容仅供开发调试，
//      勿合入正式版本提交审核
// 官方依据: https://developers.weixin.qq.com/miniprogram/dev/ai/guide（2026-09-03 核验）
// 用法:
//   node scripts/wechat-skill-gen.mjs --name my-skill --desc "技能描述" --prompt "系统提示词或功能说明" --dir <输出目录>
//   node scripts/wechat-skill-gen.mjs --check --dir <待检查目录> --json
import { readFileSync, writeFileSync, existsSync, mkdirSync } from "node:fs";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";
import { isMain, makeOpt } from "./lib.mjs";

const ROOT = join(dirname(fileURLToPath(import.meta.url)), "..");
const NAME_RE = /^[a-z0-9-]{3,64}$/;
const VERSION_RE = /^\d+\.\d+\.\d+$/;

function buildSkillMd({ name, desc, prompt }) {
  const body = String(prompt || "").trim();
  const lines = [];
  lines.push("---");
  lines.push(`name: ${name}`);
  lines.push(`description: ${desc}`);
  lines.push("version: 0.1.0");
  lines.push("---");
  lines.push("");
  lines.push(`# ${name}`);
  lines.push("");
  lines.push("> 本技能由提示词工程系统生成，用于微信小程序 AI 开发模式（beta）。当前处于内测阶段，暂未开放代码提审，请勿合入正式版本。");
  lines.push("");
  if (body) {
    lines.push("## 功能");
    lines.push("");
    lines.push(body);
  }
  lines.push("");
  lines.push("## 边界");
  lines.push("");
  lines.push("- 仅处理本技能声明的场景，超出范围明确告知用户能力边界。");
  lines.push("- 所有产出须真实可执行；信息不确定时明确标注，不编造。");
  lines.push("");
  return lines.join("\n");
}

function buildMcpJson({ name, desc }) {
  // 最小能力声明骨架；原子接口/组件声明字段以微信官方「接入方式」文档为准
  return JSON.stringify({
    name,
    description: desc,
    version: "0.1.0",
    note: "此文件为能力声明占位骨架，请按微信小程序 AI 开发模式官方「接入方式」文档补充原子接口/组件声明（接入方式: https://developers.weixin.qq.com/miniprogram/dev/ai/guide）",
  }, null, 2) + "\n";
}

export function genSkillPack({ name = null, desc = "", prompt = "", dir = null } = {}) {
  if (!name) return { ok: false, error: "缺少 --name（3-64 位小写字母/数字/连字符）" };
  if (!NAME_RE.test(name)) return { ok: false, error: `name 非法: ${name}（须 3-64 位小写字母/数字/连字符）` };
  if (!desc) return { ok: false, error: "缺少 --desc（技能描述）" };
  const outDir = dir || join(ROOT, "data", "wechat-skill-gen", name);
  mkdirSync(outDir, { recursive: true });
  writeFileSync(join(outDir, "SKILL.md"), buildSkillMd({ name, desc, prompt }), "utf8");
  writeFileSync(join(outDir, "mcp.json"), buildMcpJson({ name, desc }), "utf8");
  return {
    ok: true,
    name,
    dir: outDir,
    files: ["SKILL.md", "mcp.json"],
    note: "已生成 SKILL 包脚手架；微信 AI 开发模式内测中、未开放提审，请勿合入正式版本；原子接口/组件声明字段请按官方「接入方式」文档补充。",
  };
}

export function checkGenDir({ dir = null } = {}) {
  const base = dir || ROOT;
  const checks = [];
  const add = (name, ok, detail) => checks.push({ name, ok, detail });
  const skillMd = join(base, "SKILL.md");
  const mcpJson = join(base, "mcp.json");
  add("SKILL.md 存在", existsSync(skillMd), existsSync(skillMd) ? "已找到" : "缺失");
  add("mcp.json 存在", existsSync(mcpJson), existsSync(mcpJson) ? "已找到" : "缺失");
  if (existsSync(skillMd)) {
    const text = readFileSync(skillMd, "utf8").replace(/^\uFEFF/, "");
    const m = /^---\r?\n([\s\S]*?)\r?\n---/.exec(text);
    const meta = m ? Object.fromEntries(m[1].split("\n").filter(Boolean).map((l) => { const kv = /^([A-Za-z0-9_]+):\s*(.*)$/.exec(l); return kv ? [kv[1], kv[2]] : null; }).filter(Boolean)) : {};
    add("SKILL.md frontmatter 含 name/description/version", Boolean(meta.name && meta.description && meta.version), `name=${meta.name || "无"} description=${(meta.description || "").length}字符 version=${meta.version || "无"}`);
    add("SKILL.md 大小 ≤100KB", text.length <= 100 * 1024, `${text.length} 字符`);
  }
  const failed = checks.filter((c) => !c.ok);
  return {
    ok: failed.length === 0,
    checks,
    issues: failed.map((c) => c.name),
    summary: failed.length ? `SKILL 包结构未通过（${failed.length} 项）` : `SKILL 包结构通过（${checks.length} 项全部满足）`,
  };
}

// ================= CLI =================
if (isMain(import.meta)) {
  const args = process.argv.slice(2);
  const opt = makeOpt(args);
  const json = args.includes("--json");
  if (args.includes("--check")) {
    const r = checkGenDir({ dir: opt("dir") || null });
    if (json) process.stdout.write(JSON.stringify(r, null, 2) + "\n");
    else {
      process.stdout.write(`${r.summary}\n`);
      for (const c of r.checks) process.stdout.write(`  ${c.ok ? "✓" : "✗"} ${c.name}: ${c.detail}\n`);
    }
    if (!r.ok) process.exit(1);
  } else {
    const r = genSkillPack({ name: opt("name"), desc: opt("desc") || "", prompt: opt("prompt") || "", dir: opt("dir") || null });
    if (!r.ok) {
      process.stderr.write(`✗ ${r.error}\n`);
      process.exit(2);
    }
    if (json) process.stdout.write(JSON.stringify(r, null, 2) + "\n");
    else {
      process.stdout.write(`✓ 已生成 SKILL 包脚手架: ${r.name}\n`);
      process.stdout.write(`  位置: ${r.dir}\n`);
      process.stdout.write(`  文件: ${r.files.join(", ")}\n`);
      process.stdout.write(`  ${r.note}\n`);
    }
  }
}
