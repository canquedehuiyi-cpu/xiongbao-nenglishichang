/**
 * 隐私扫描核心：凭据形态、本机路径痕迹、哨兵词表。
 * 单独成模块，是为了让 selftest 能复用同一份规则——
 * 「出包闸门」和「验证出包闸门的测试」绝不能各拿一套标准。
 */

import { readFileSync, readdirSync, statSync } from 'node:fs';
import { join, relative, sep } from 'node:path';
import { skipDir, SKIP_FILES } from './packrules.mjs';

export const SECRET_SHAPES = [
  ['secret-01', /\bgh[pousr]_[0-9A-Za-z]{20,}\b/],
  ['secret-02', /\bgithub_pat_[0-9A-Za-z]{20,}_[0-9A-Za-z]{20,}\b/],
  ['secret-03', /\bAKIA[0-9A-Z]{16}\b/],
  ['secret-04', /\bsk-[A-Za-z0-9_-]{24,}\b/],
  ['secret-05', /\bxox[baprs]-[0-9a-zA-Z-]{10,}\b/],
  ['secret-06', /\bAIza[0-9A-Za-z_-]{35}\b/],
  ['secret-07', /-----BEGIN (?:RSA |EC |DSA |OPENSSH |PGP )?PRIVATE KEY-----/],
  ['secret-08', /\bnpm_[A-Za-z0-9]{36}\b/],
];

/** 环境/路径痕迹：任何一条命中都说明包是从某台具体机器直接拷出来的。 */
export const TRACE = [
  ['trace-01', /(?:^|[^\w/])[A-Za-z]:[\\/](?!path\b)[\w.\- ]{2,}/m],
  ['trace-02', /\/Users\/(?!example|user)[\w.-]{2,}/],
  ['trace-03', /\/home\/(?!example|user)[\w.-]{2,}/],
  ['trace-04', /[\w.+-]+@(?:gmail|outlook|qq|163|126|icloud|protonmail|foxmail)\.(?:com|cn|net)/i],
  ['trace-05', /(?:\.qoder-cn|\.qoder)[\\/](?:memory|projects|plans|session-env|logs)[\\/]/],
];

// 排除规则来自 packrules：闸门扫的必须正好是进包的东西。注意 nested dist 不再被跳过——

export function walkFiles(dir, out = [], limit = 4000, st = { truncated: false, unreadable: 0 }, depth = 0, skip = null) {
  let entries = [];
  try {
    entries = readdirSync(dir);
  } catch {
    st.unreadable++;
    return out;
  }
  for (const n of entries) {
    if (out.length >= limit) {
      st.truncated = true;
      return out;
    }
    const full = join(dir, n);
    let s;
    try {
      s = statSync(full);
    } catch {
      st.unreadable++;
      continue;
    }
    if (s.isDirectory()) {
      if (!skip || !skip(n, depth)) walkFiles(full, out, limit, st, depth + 1, skip);
    } else if (!SKIP_FILES.has(n)) out.push(full);
  }
  return out;
}

/**
 * 扫一棵树。
 *
 * 第一版按扩展名白名单挑文件，于是 `.jsonl`、`.svg`、`.env` 和无扩展名文件全都不扫——
 * 而这正是泄露最容易藏身的地方。现在改成：**除二进制外全扫，且文件名本身也参与匹配**
 * （一个叫 `acme-corp-notes.md` 的文件，内容干净也照样是泄露）。
 *
 * @param {string} root 要扫的目录
 * @param {string[]} forbidden 哨兵词（一行一个，# 开头忽略）
 */
/**
 * 扫一棵树。**默认不排除任何目录名**：包里只要有一个叫 dist/ 或 node_modules/ 的目录，
 * 按名字跳过就等于给它开了免检——而闸门要回答的问题是「这个包里有没有你的数据」，
 * 跟那个目录叫什么无关。需要跳过开发期目录的调用方（例如扫插件自己的源码树）显式传 skip。
 * @param {string} root
 * @param {string[]} forbidden
 * @param {{skip?:(name:string,depth:number)=>boolean}} [opt]
 */
export function scanTree(root, forbidden = [], opt = {}) {
  const hits = [];
  const walkState = { truncated: false, unreadable: 0 };
  const files = walkFiles(root, [], 4000, walkState, 0, opt.skip || null);
  const words = forbidden.map((w) => String(w).trim()).filter((w) => w && !w.startsWith('#'));
  const matchName = (rel) => {
    for (let i = 0; i < words.length; i++) if (rel.includes(words[i])) hits.push({ file: rel, kind: 'forbidden', ref: `forbidden-line-${i + 1}`, where: 'filename' });
    for (const [kind, re] of SECRET_SHAPES) if (re.test(rel)) hits.push({ file: rel, kind, ref: kind, where: 'filename' });
    for (const [kind, re] of TRACE) if (re.test(rel)) hits.push({ file: rel, kind, ref: kind, where: 'filename' });
  };
  const notRead = [];
  for (const f of files) {
    const rel = relative(root, f).split(sep).join('/');
    matchName(rel);
    let buf = null;
    try {
      if (statSync(f).size > 4_000_000) { notRead.push({ file: rel, why: 'over-4MB' }); continue; }
      buf = readFileSync(f);
    } catch {
      notRead.push({ file: rel, why: 'unreadable' });
      continue;
    }
    if (buf.includes(0)) { notRead.push({ file: rel, why: 'binary' }); continue; } // 二进制：只按文件名判，不解析内容
    const text = buf.toString('utf8');
    for (let i = 0; i < words.length; i++) {
      if (text.includes(words[i])) hits.push({ file: rel, kind: 'forbidden', ref: `forbidden-line-${i + 1}` });
    }
    for (const [kind, re] of SECRET_SHAPES) if (re.test(text)) hits.push({ file: rel, kind, ref: kind });
    // 夹具里刻意放了带占位绝对路径的缺陷样本（PIPE-2/PIPE-5 的靶子），那是作者写的合成内容、
    // 不是从某台机器拷出来的痕迹。豁免范围收窄到**具体那几个文件所在目录**，
    // 并且哨兵词与凭据形态在夹具里照样判——真实数据混进夹具仍然会被拦下。
    const isFixtureProp = /(^|\/)fixtures\/synthetic-site\/(tools|src)\//.test(rel);
    if (!isFixtureProp) for (const [kind, re] of TRACE) if (re.test(text)) hits.push({ file: rel, kind, ref: kind });
  }
  // 覆盖度必须被调用方看见：只按文件名判过、内容从未读过的文件，等于没扫。
  return {
    hits,
    files: files.map((f) => relative(root, f).split(sep).join('/')),
    coverage: {
      walked: files.length,
      truncated: walkState.truncated,
      unreadableDirs: walkState.unreadable,
      contentNotRead: notRead.length,
      notRead: notRead.slice(0, 8),
      gaps: [
        walkState.truncated ? `文件数触顶（上限 4000），后面的文件一个都没看` : '',
        walkState.unreadableDirs ? `${walkState.unreadableDirs} 个目录/文件读不了` : '',
        notRead.length ? `${notRead.length} 个文件只按文件名判过、内容未解析` : '',
      ].filter(Boolean),
    },
  };
}
