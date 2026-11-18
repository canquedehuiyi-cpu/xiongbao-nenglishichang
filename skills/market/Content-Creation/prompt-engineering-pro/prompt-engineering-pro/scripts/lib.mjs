#!/usr/bin/env node
// lib.mjs — 公共工具库（消除跨脚本重复：ROOT/clamp/ts/ensureDir + 安全边界工具）
// 用途: 被各引擎脚本 import，避免各脚本各自复制同一段工具代码
// v1.0.3 新增: safePath/safeDir/safeId/escapeRegExp/isMain
//   —— 修复 1.0.1 的路径穿越（--dir/--id/--cases/--cache-dir 等参数可写/读包外任意位置）、
//      正则注入与 Windows 主入口误判问题
import { existsSync, mkdirSync } from "node:fs";
import { join, dirname, resolve, sep } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
import { tmpdir } from "node:os";

// 项目根目录（脚本位于 scripts/ 下，故 ..）
export const ROOT = join(dirname(fileURLToPath(import.meta.url)), "..");

export function clamp(n, lo = 0, hi = 100) {
  return Math.max(lo, Math.min(hi, n));
}

export function ensureDir(dir) {
  if (!existsSync(dir)) mkdirSync(dir, { recursive: true });
}

// 格式化时间戳（YYYYMMDDHHMMSS，本地时间）
export function ts() {
  const d = new Date();
  return `${d.getFullYear()}${String(d.getMonth() + 1).padStart(2, "0")}${String(d.getDate()).padStart(2, "0")}${String(d.getHours()).padStart(2, "0")}${String(d.getMinutes()).padStart(2, "0")}${String(d.getSeconds()).padStart(2, "0")}`;
}

function underBase(target, base) {
  const b = resolve(base);
  return target === b || target.startsWith(b + sep);
}

/**
 * 路径安全边界（1.0.3 安全修复核心）：校验任意外部传入的路径参数。
 * 仅允许落在两处白名单内：
 *   1. 技能包根目录（ROOT）子树 —— 正常数据读写位置；
 *   2. 系统临时目录（os.tmpdir()）子树 —— 包内测试套件（validate/attack）注入临时目录用。
 * 其余位置（如系统目录、用户文档、其它盘符）一律抛错拒绝，绝不静默放行。
 * 相对路径以 ROOT 为基准解析，防止借 cwd 逃逸。
 * @param {string} p 外部传入的路径（文件目录均可）
 * @param {{allowTmp?: boolean}} [opts] allowTmp=false 时连临时目录也禁止（用于强约束场景）
 * @returns {string} 归一化后的绝对路径
 */
export function safePath(p, { allowTmp = true } = {}) {
  const target = resolve(ROOT, String(p));
  if (underBase(target, ROOT)) return target;
  if (allowTmp && underBase(target, tmpdir())) return target;
  throw new Error(`安全边界: 路径必须位于技能包内部或系统临时目录，拒绝外部路径: ${p}`);
}

/**
 * 目录参数安全封装：--dir / --cache-dir / --profile-dir 等。
 * 入参为空时返回默认目录；否则经 safePath 校验。
 * @param {string|undefined|null} dir 用户传入的目录参数
 * @param {string} fallback 默认目录（应位于 ROOT 内）
 * @returns {string} 安全目录绝对路径
 */
export function safeDir(dir, fallback) {
  if (dir === undefined || dir === null || dir === "") return resolve(fallback);
  return safePath(dir);
}

/**
 * ID 清洗：用于会进入文件名的用户可控片段（如 version-store 的 --id）。
 * 1.0.1 中 --id 含 "../../" 时可逃逸数据目录；清洗后仅保留安全文件名字符。
 * @param {string} raw 原始 id
 * @returns {string} 仅含 [A-Za-z0-9_.-] 的安全片段；清洗后为空则抛错
 */
export function safeId(raw) {
  const cleaned = String(raw ?? "")
    .replace(/[\\/]+/g, "")
    .replace(/\.\./g, "")
    .replace(/[^A-Za-z0-9_.-]/g, "_")
    .replace(/^\.+/, "")
    .slice(0, 120);
  if (!cleaned) throw new Error("安全边界: 非法的 id（清洗后为空）");
  return cleaned;
}

/**
 * 正则特殊字符转义：把字符串安全地拼入 new RegExp()。
 * 修复 matrix-check 等处的正则注入/ReDoS 隐患。
 * @param {string} s 任意字符串
 * @returns {string} 转义后可安全拼入正则的字符串
 */
export function escapeRegExp(s) {
  return String(s).replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

/**
 * 稳健的主入口判定（替代各脚本中 import.meta.url === new URL(file://argv[1]) 的脆弱写法）。
 * 修复 Windows 下含空格/中文/特殊字符路径时 CLI 静默不执行的问题：
 * 使用 pathToFileURL 正确处理编码与盘符，解析失败时保守返回 false。
 * @param {ImportMeta} importMeta 调用方的 import.meta
 * @returns {boolean} 当前模块是否作为主入口直接运行
 */
export function isMain(importMeta) {
  try {
    if (!process.argv[1]) return false;
    return importMeta.url === pathToFileURL(resolve(process.argv[1])).href;
  } catch {
    return false;
  }
}

/**
 * CLI 参数解析器工厂（消除 9 个脚本各自复制的同一段逻辑）。
 * 用法: const opt = makeOpt(process.argv.slice(2)); opt("dir") → "--dir" 后的值或 undefined。
 * @param {string[]} args 命令行参数数组（不含 node 与脚本路径）
 * @returns {(name: string) => string|undefined} 按 --<name> 取值的函数
 */
export function makeOpt(args) {
  return (name) => {
    const i = args.indexOf(`--${name}`);
    return i >= 0 ? args[i + 1] : undefined;
  };
}
