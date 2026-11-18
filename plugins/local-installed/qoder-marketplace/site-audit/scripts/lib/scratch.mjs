/**
 * 输出目录与被禁访问路径。
 *
 * 存在理由：这是一套「审查别人」的工具，它必须结构上无法去翻使用者的私有区
 * （模型记忆目录、凭据文件、IDE 配置）。审查目标里出现这些路径也是泄露。
 * 所有脚本在把 --out/--repo/--dist 交给文件系统之前都必须过 assertReadablePath()。
 */

import { existsSync, mkdirSync, realpathSync } from 'node:fs';
import { homedir } from 'node:os';
import { join, resolve, sep } from 'node:path';

const HOME = homedir();
const IS_WIN = process.platform === 'win32';

export class PathDenied extends Error {}

/**
 * 目录名黑名单：按**路径分段**匹配。
 * 旧实现拿整条路径去 test 一个 `$` 锚定的正则，于是 `/\.ssh$/` 只挡住 `.ssh` 本身、
 * 放过了 `.ssh/id_rsa`，而 `/^\.[\\/]claude$/` 根本不可能命中完整路径。两个都是真 bug。
 *
 * 这里只放**凭据类**目录名。像 memory/plans/logs 这种词在正常仓库里也会出现
 * （`src/memory/`、`docs/plans/`），一律拦会误伤审查对象，所以它们走下面的
 * DENY_DIR_CHAINS（必须挂在 .qoder/.qoder-cn 之下才拦）。
 */
const DENY_DIR_NAMES = new Set([
  '.ssh', '.gnupg', '.aws', '.azure', '.kube', '.docker', '.npm', '.claude', '.cursor',
]);

/** 文件名黑名单（含私钥与凭据缓存的常见名字）。 */
const DENY_FILE_NAMES = new Set([
  '.netrc', '_netrc', 'npmrc', '.npmrc', 'git-credentials', '.git-credentials',
  // 浏览器 profile 里的会话与口令库：形状固定，直接按文件名拦
  'cookies.sqlite', 'key3.db', 'key4.db', 'logins.json', 'web data', 'local state',
  'id_rsa', 'id_ed25519', 'id_ecdsa', 'id_dsa',
]);

/** 需要「父目录 + 子目录」同时命中才算的链（避免把任何叫 gh 的目录都拦掉）。 */
const DENY_DIR_CHAINS = [
  ['.config', 'gh'], ['.config', 'git'], ['.config', 'gcloud'], ['.config', 'npm'],
  ['.qoder', 'memory'], ['.qoder-cn', 'memory'],
  ['.qoder', 'projects'], ['.qoder-cn', 'projects'],
  ['.qoder', 'plans'], ['.qoder-cn', 'plans'],
  ['.qoder', 'logs'], ['.qoder-cn', 'logs'],
  ['.qoder', 'session-env'], ['.qoder-cn', 'session-env'],
  // 浏览器 profile / 钥匙串：这些目录里的东西一旦被复制进 --out，
  // 账本目录就成了二次泄露源，而 --out 是要给人看、给人转的。
  ['appdata', 'local', 'google', 'chrome', 'user data'],
  ['appdata', 'local', 'microsoft', 'edge', 'user data'],
  ['appdata', 'roaming', 'mozilla', 'firefox'],
  ['library', 'application support', 'google', 'chrome'],
  ['library', 'application support', 'firefox'],
  ['library', 'keychains'],
  ['.mozilla', 'firefox'],
];

/** 使用者主目录下的敏感绝对前缀（含 settings.json 这类单文件）。 */
const DENY_PATHS = [
  join(HOME, '.qoder-cn', 'settings.json'),
  join(HOME, '.qoder', 'settings.json'),
  join(HOME, '.qoder-cn', 'mcp-router.json'),
  join(HOME, '.qoder', 'mcp-router.json'),
];

function real(p) {
  try {
    return realpathSync(p);
  } catch {
    return resolve(p);
  }
}

/** Windows 文件系统大小写不敏感：全大写的 .SSH 与小写的 .ssh 是同一个目录，比较前先统一小写。 */
function normPath(p) {
  const s = p.split(sep).join('/');
  return IS_WIN ? s.toLowerCase() : s;
}

/**
 * @param {string} p
 * @param {{purpose?: string}} [opt]
 * @returns {string} 解析后的绝对路径
 */
export function assertReadablePath(p, opt = {}) {
  const abs = resolve(p);
  const r = real(abs);
  const norm = normPath(r);
  const segs = norm.split('/').filter(Boolean);
  const why = (rule) =>
    `拒绝访问 ${abs}${opt.purpose ? `（用途: ${opt.purpose}）` : ''}：命中私有区规则「${rule}」。` +
    `本工具的任何检查都不得读取它，也不得把它复制进账本目录。`;

  for (const denied of DENY_PATHS) {
    const dn = normPath(real(denied));
    if (norm === dn || norm.startsWith(dn + '/')) throw new PathDenied(why(denied));
  }
  for (const seg of segs) {
    if (DENY_DIR_NAMES.has(seg)) throw new PathDenied(why('目录名 ' + seg));
  }
  const base = segs[segs.length - 1] || '';
  if (DENY_FILE_NAMES.has(base)) throw new PathDenied(why('文件名 ' + base));
  for (const chain of DENY_DIR_CHAINS) {
    for (let i = 0; i + chain.length <= segs.length; i++) {
      if (chain.every((c, k) => segs[i + k] === c)) throw new PathDenied(why(chain.join('/')));
    }
  }
  // UNC（\\host\share）与 8.3 短名（memo~1）都能绕过按段比较，单独挡
  if (r.startsWith('\\\\')) throw new PathDenied(why('UNC 路径'));
  if (/~\d/.test(r)) throw new PathDenied(why('8.3 短名路径'));
  return abs;
}


/**
 * 输出根目录。默认 <cwd>/.site-audit/<round>——永远在被审对象的工作区里，
 * 不写到用户主目录、不写到对方仓库之外。
 */
export function ensureOut(dir) {
  const abs = resolve(dir);
  assertReadablePath(abs, { purpose: '输出目录' });
  if (!existsSync(abs)) mkdirSync(abs, { recursive: true });
  return abs;
}

export const homePlaceholder = (p) => (p || '').split(HOME).join('~');
