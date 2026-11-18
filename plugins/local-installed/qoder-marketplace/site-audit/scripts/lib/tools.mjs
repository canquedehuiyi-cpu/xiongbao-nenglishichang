/**
 * 共享工具：argv 解析、外部命令解析（跨 Windows/Linux）、脱敏、哈希、退出码。
 * 只用 Node 内置模块，零依赖——脚本必须能在没有 node_modules 的全新克隆里跑。
 * 本文件不得有任何副作用，不得读写文件。
 */

import { existsSync } from 'node:fs';
import { execFileSync } from 'node:child_process';
import { createHash } from 'node:crypto';
import { dirname, join } from 'node:path';

/* ---------------- 退出码（有承重作用，不可改动） ---------------- */
export const EXIT = {
  CLEAN: 0,      // 跑完且无发现
  FINDINGS: 1,   // 跑完，存在 >=P2 的发现
  PARTIAL: 2,    // 只跑了一部分：存在 not-run
  UNUSABLE: 3,   // 缺能力，本脚本区间内一项都没跑
  USAGE: 4,      // argv/env 错误
};

/** 由一组 finding 推导退出码。not-run 优先于 pass/fail——「跑不了」绝不能被读成「通过」。 */
export function exitCodeFor(findings) {
  // 「这一轮什么都没判出来」不能等于 0。三个特例按重要性排：
  // 1) 一行都没有 → 3；2) 全是 not-run → 3（旧实现这里因为 every([])===true 也返回 3，
  //    但一旦脚本记了一行 pass 当兜底就退回 0，等于「没查但绿了」）；
  // 3) 有 not-run 但也有判定 → 2。
  if (findings.length === 0) return EXIT.UNUSABLE;
  const notRun = findings.filter((f) => f.verdict === 'not-run').length;
  const judged = findings.filter((f) => f.verdict === 'pass' || f.verdict === 'fail').length;
  if (!judged) return EXIT.UNUSABLE;
  if (notRun) return EXIT.PARTIAL;
  if (findings.some((f) => f.verdict === 'fail' && /^(P1|P2)$/.test(f.severity || ''))) {
    return EXIT.FINDINGS;
  }
  return EXIT.CLEAN;
}

/* ---------------- argv ---------------- */

/**
 * 极简 flag 解析：`--key value` / `--key=<value>` / `--flag`（布尔）。
 * kebab-case 与 camelCase 两个键都会写入——否则 `--probe-links` 会变成
 * `opts['probe-links']` 而调用方读 `opts.probeLinks` 永远是 undefined，
 * 整项检查静默失效（这个 bug 真实发生过，且没有任何报错）。
 * @param {string[]} argv 不含 node 与脚本路径
 * @param {{value?: string[], bool?: string[], positional?: boolean}} spec
 */
export function parseArgs(argv, spec = {}) {
  const valueKeys = new Set(spec.value || []);
  const boolKeys = new Set(spec.bool || []);
  const opts = {};
  const positional = [];
  const put = (key, val) => {
    opts[key] = val;
    if (key.includes('-')) {
      opts[key.replace(/-([a-z])/g, (_m, c) => c.toUpperCase())] = val;
    }
  };
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (!a.startsWith('--')) {
      positional.push(a);
      continue;
    }
    let key = a.slice(2);
    let val;
    const eq = key.indexOf('=');
    if (eq >= 0) {
      val = key.slice(eq + 1);
      key = key.slice(0, eq);
    }
    if (boolKeys.has(key)) {
      put(key, val === undefined ? true : val !== 'false');
    } else if (valueKeys.has(key)) {
      if (val === undefined) {
        const next = argv[i + 1];
        if (next === undefined || next.startsWith('--')) {
          throw new Error(`--${key} 需要取值`);
        }
        val = next;
        i++;
      }
      put(key, val);
    } else {
      throw new Error(`未知参数 --${key}`);
    }
  }
  if (!spec.positional) return { opts, positional: positional[0] };
  return { opts, positional };
}

/* ---------------- 外部命令解析 ---------------- */

/**
 * 找到可用的 npm 入口。Windows 上 execFileSync('npm.cmd') 会抛 EPERM/EINVAL，
 * 因此统一折成 `node <npm-cli.js>`；实在找不到才退回 shell。
 * @param {{env?: NodeJS.Process, platform?: string}} [ctx]
 * @returns {{cmd:string, prefix:string[], shell:boolean, how:string}|null}
 */
export function resolveNpm(ctx = {}) {
  const env = ctx.env || process.env;
  const platform = ctx.platform || process.platform;

  const execpath = env.npm_execpath;
  if (execpath && existsSync(execpath)) {
    return { cmd: process.execPath, prefix: [execpath], shell: false, how: 'npm_execpath' };
  }

  const nodeDir = dirname(process.execPath);
  const candidates =
    platform === 'win32'
      ? [
          join(nodeDir, 'node_modules', 'npm', 'bin', 'npm-cli.js'),
          join(nodeDir, '..', 'node_modules', 'npm', 'bin', 'npm-cli.js'),
        ]
      : [
          join(nodeDir, 'node_modules', 'npm', 'bin', 'npm-cli.js'),
          '/usr/lib/node_modules/npm/bin/npm-cli.js',
          '/usr/local/lib/node_modules/npm/bin/npm-cli.js',
          '/opt/homebrew/lib/node_modules/npm/bin/npm-cli.js',
        ];
  for (const c of candidates) {
    if (existsSync(c)) return { cmd: process.execPath, prefix: [c], shell: false, how: 'known-path' };
  }

  const locator = platform === 'win32' ? 'where' : 'which';
  try {
    const out = execFileSync(locator, [platform === 'win32' ? 'npm.cmd' : 'npm'], {
      encoding: 'utf8',
      stdio: ['ignore', 'pipe', 'ignore'],
    });
    const found = out.split(/\r?\n/).map((s) => s.trim()).filter(Boolean)[0];
    if (found) {
      const sibling = join(dirname(found), 'node_modules', 'npm', 'bin', 'npm-cli.js');
      if (existsSync(sibling)) {
        return { cmd: process.execPath, prefix: [sibling], shell: false, how: 'locator-sibling' };
      }
      if (/\.(cmd|bat|ps1)$/i.test(found)) {
        return { cmd: found, prefix: [], shell: true, how: 'locator-shell' };
      }
      return { cmd: found, prefix: [], shell: false, how: 'locator-bin' };
    }
  } catch {
    /* 没找到，继续走兜底 */
  }
  return platform === 'win32'
    ? { cmd: 'npm', prefix: [], shell: true, how: 'fallback-shell' }
    : { cmd: 'npm', prefix: [], shell: false, how: 'fallback-path' };
}

/**
 * 在 PATH 里找一个可执行文件（不经过 shell）。
 * @param {string} name
 */
export function resolveBin(name) {
  const platform = process.platform;
  if (platform === 'win32') {
    try {
      const out = execFileSync('where', [name], {
        encoding: 'utf8',
        stdio: ['ignore', 'pipe', 'ignore'],
      });
      const hit = out
        .split(/\r?\n/)
        .map((s) => s.trim())
        .filter((s) => s && !/\.ps1$/i.test(s))[0];
      return hit || null;
    } catch {
      return null;
    }
  }
  try {
    execFileSync('which', [name], { stdio: ['ignore', 'ignore', 'ignore'] });
    return name;
  } catch {
    return null;
  }
}

/**
 * argv 形式执行外部命令，绝不拼 shell 字符串。捕获一切失败，返回结构化结果——
 * 调用方必须显式处理 ok:false，这是「门禁 fail-open」的对称面。
 * @param {string} cmd
 * @param {string[]} args
 * @param {{cwd?:string, timeout?:number, maxBuffer?:number, shell?:boolean, input?:string}} [opt]
 */
/** 只保留跑外部命令必需的环境变量（用于「别把使用者的登录态交给被调程序」）。 */
export function minimalEnv(extra = {}) {
  const keep = {};
  for (const k of ['PATH', 'HOME', 'USERPROFILE', 'SystemRoot', 'systemroot', 'TEMP', 'TMP', 'LANG', 'LC_ALL', 'USER', 'USERNAME', 'SHELL', 'NODE_PATH', 'ComSpec', 'PATHEXT']) {
    if (process.env[k] !== undefined) keep[k] = process.env[k];
  }
  return { ...keep, ...extra };
}

export function run(cmd, args, opt = {}) {
  try {
    const stdout = execFileSync(cmd, args, {
      cwd: opt.cwd,
      encoding: 'utf8',
      timeout: opt.timeout ?? 120000,
      maxBuffer: opt.maxBuffer ?? 32 * 1024 * 1024,
      shell: opt.shell || false,
      stdio: ['pipe', 'pipe', 'pipe'],
      input: opt.input,
      // 被审项目里读到的配置不该影响我们自己的判断：调用方可显式覆盖（如 GIT_CONFIG_NOSYSTEM）
      // cleanEnv：只带上运行必需的几个变量。用于「不希望把使用者的登录态交给被调用程序」的场合
      // （例如 ci-hygiene 用 gh 查分支保护：不带 GH_TOKEN/GITHUB_TOKEN，就不会把使用者的令牌
      //   发到一个由被审仓库 origin 决定的查询地址上）。
      env: opt.cleanEnv ? minimalEnv(opt.env || {}) : opt.env ? { ...process.env, ...opt.env } : undefined,
    });
    return { ok: true, code: 0, stdout: stdout || '', stderr: '' };
  } catch (e) {
    return {
      ok: false,
      code: typeof e.status === 'number' ? e.status : -1,
      stdout: typeof e.stdout === 'string' ? e.stdout : '',
      stderr: typeof e.stderr === 'string' ? e.stderr : String(e.message || e),
      error: e,
    };
  }
}

/* ---------------- 脱敏与标识 ---------------- */

/** 凭据形态：只用于替换，永不用于回显匹配内容。 */
const SECRET_SHAPES = [
  /\bgh[pousr]_[0-9A-Za-z]{20,}\b/g,
  /\bgithub_pat_[0-9A-Za-z_]{20,}\b/g,
  /\bAKIA[0-9A-Z]{16}\b/g,
  /\bsk-[A-Za-z0-9_-]{20,}\b/g,
  /\bxox[baprs]-[0-9a-zA-Z-]{10,}\b/g,
  /\bAIza[0-9A-Za-z_-]{35}\b/g,
  /-----BEGIN (?:RSA |EC |DSA |OPENSSH |PGP )?PRIVATE KEY-----/g,
  /\bBearer\s+[A-Za-z0-9._~+\/-]{16,}/gi,
];

const PATH_SHAPES = [
  // 子进程 stdout、npm 报错 JSON、被审页面文本都可能带审查者本机路径；实测 SEC-2
  // 曾把 ~/.ssh 的文件名与密钥正文前缀原样写进账本。
  // 盘符规则必须要求前面不是单词字符——`https:/` 里的 `s:/` 也是「字母+冒号+斜杠」，
  // 同一个坑今晚踩过三次（PIPE-5、SEC-3、这里）。用捕获组留住前缀，只替换路径本身。
  // 反向斜杠必须一起支持：Windows 上子进程输出的是「盘符:反斜杠」形态的家目录，
  // 而字符类 [\/] 只认正斜杠——第 3 轮实测安装者的用户名与家目录照样进账本。
  /(^|[^\w/])([A-Za-z]:[\\/][^\s"'`,;()<>|]{1,200})/g,
  /(^|[^\w/])((?:\/Users|\/home|\/root|\/mnt\/wsl[0-9]?)[\/][\w.\-]{1,40}(?:\/[\w.\-]{1,60}){0,8})/g,
  /(^|\s)(~\/[\w.\-]{1,60}(?:\/[\w.\-]{1,60}){0,8})/g,
  /(^|[^\w/])(\/mnt\/[a-z]\/[\w.\-]{1,60}(?:\/[\w.\-]{1,60}){0,6})/g,
  // UNC：\\fileserver\share\… ——公司网络盘的常见形态
  /(^|[^\w\\])(\\\\[^\s"'`,;()<>|]{1,200})/g,
];

const URL_CRED = /\/\/[^\s/@]{1,64}:[^\s/@]{1,64}@/g;

const PII_SHAPES = [
  /[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}/g,
  // 手机号与国际号码。刻意不用「任意 9 位以上数字」——那会把 epoch 毫秒、
  // 字节数、行号一起吞掉，脱敏过度同样是缺陷（证据变得无法复核）。
  /\b1[3-9]\d{9}\b/g,
  /\+\d{1,3}[-\s]\(?\d{2,4}\)?[-\s]?\d{3,4}[-\s]?\d{3,4}/g,
  /\b\d{17}[\dXx]\b/g,
];

/**
 * 写盘/打印前统一过一遍：凭据与 PII 形态替换 + 截断。
 * 命中凭据时只保留 pattern 名（由调用方决定），这里连名字都不留——避免日志二次泄露。
 * @param {string} text
 * @param {number} [max]
 */
export function redact(text, max = 200) {
  let out = String(text == null ? '' : text).replace(/\s+/g, ' ').trim();
  let touched = false;
  // URL 内嵌凭据先脱掉，否则 --url https://user:pw@host 会一路进账本
  if (URL_CRED.test(out)) { touched = true; out = out.replace(URL_CRED, '//[REDACTED]@'); }
  URL_CRED.lastIndex = 0;
  for (const re of SECRET_SHAPES) {
    if (re.test(out)) touched = true;
    out = out.replace(re, '[REDACTED]');
    re.lastIndex = 0;
  }
  for (const re of PII_SHAPES) {
    if (re.test(out)) touched = true;
    out = out.replace(re, '[REDACTED]');
    re.lastIndex = 0;
  }
  for (const re of PATH_SHAPES) {
    if (re.test(out)) touched = true;
    out = out.replace(re, '$1[PATH]');
    re.lastIndex = 0;
  }
  if (out.length > max) out = out.slice(0, max - 1) + '…';
  return { text: out, touched };
}

/** 账本里对第三方站点只记哈希，人类报告里才给全文。 */
export function targetHash(url) {
  return createHash('sha256').update(String(url || '')).digest('hex').slice(0, 12);
}

export function hostOf(url) {
  try {
    return new URL(url).host;
  } catch {
    return '';
  }
}

export const nowIso = () => new Date().toISOString();

export function runId(round, ts = Date.now()) {
  return `r${round}-${createHash('sha1').update(String(ts)).digest('hex').slice(0, 8)}`;
}

/**
 * 「这条 npm script 要跑的程序在这台机器上根本不存在吗？」
 *
 * 为什么不靠读报错文本判：中文 Windows 上 cmd 的输出是 GBK 的，落到 utf8 里是乱码
 * （实测：`'notatool' 锟斤拷...`），任何语言的字面匹配都不会稳定命中。
 * 所以改成**先看要跑什么**：取脚本命令的第一个可执行程序名（跳过 `FOO=1 cmd` 这样的前置赋值
 * 与 `&&`/`||`/`;` 之后的第二段），再看它能不能在 PATH 或副本的 node_modules/.bin 里解析到。
 * 解析不到就是「环境跑不动」，与项目有没有缺陷无关。
 * @param {string} cmdLine package.json 里的脚本内容
 * @param {string[]} binDirs 额外的可执行目录（通常是副本里的 node_modules/.bin）
 * @returns {{program:string, missing:boolean}}
 */
export function missingProgram(cmdLine, binDirs = []) {
  const first = String(cmdLine || '').split(/&&|\|\||;/)[0].trim();
  if (!first) return { program: '', missing: false };
  const tokens = [];
  for (let raw of first.split(/\s+/)) {
    let tk = raw.replace(/^["']|["']$/g, '');
    raw = tk;
    if (/^[\w.-]+=$/.test(tk) || /^[\w.-]+=.+/.test(tk)) continue; // 前置环境变量赋值
    if (tk === 'npx') {
      // `npx astro build` / `pnpm -w build`：真正的程序在后面那个非 flag 词上
      continue;
    }
    if (tk.startsWith('-')) continue;
    tokens.push(tk);
    break;
  }
  const program = tokens[0] || '';
  if (!program) return { program: '', missing: false };
  // npm / pnpm / yarn 是「跑脚本的壳」，不是缺失的程序：能走到这一步说明 npm 本身在，
  // 把它们当程序去 PATH 里找会误判成「工具链缺失」，从而把真的门禁红灯降级成 not-run。
  if (/^(npm|pnpm|yarn|corepack|turbo|lerna)$/.test(program)) return { program, missing: !resolveBin(program) };
  const base = program.split(/[\\/]/).pop();
  const exts = process.platform === 'win32' ? ['', '.cmd', '.exe', '.bat'] : [''];
  for (const dir of binDirs) {
    for (const ext of exts) {
      try {
        if (existsSync(join(dir, base + ext))) return { program, missing: false };
      } catch { /* 路径不可达就当没找到 */ }
    }
  }
  return { program, missing: !resolveBin(base) };
}

/**
 * 「这条命令在这台机器上根本跑不起来」的文本判据（补充手段，不作为唯一依据）：
 * 模块缺失类信息在 npm/node 侧是英文的，比较稳定。
 */
export const UNRUNNABLE_RE = /Cannot find module|ERR_MODULE_NOT_FOUND|MODULE_NOT_FOUND|cannot find package|command not found|not recognized as an internal or external command|could not determine executable to run/i;

/* ---------------- 输出 ---------------- */

const BADGE = {
  [EXIT.CLEAN]: 'PASS     ',
  [EXIT.FINDINGS]: 'FINDINGS   ',
  [EXIT.PARTIAL]: 'PARTIAL    ',
  [EXIT.UNUSABLE]: 'NOT-RUN    ',
  [EXIT.USAGE]: 'USAGE-ERROR',
};

/**
 * 收尾打印。exit 2/3 与 0 必须视觉强区分——这是整套东西的核心不变量。
 * @returns {number} 建议的 process exitCode
 */
export function finish(script, findings, extra = {}) {
  const code = exitCodeFor(findings);
  const fails = findings.filter((f) => f.verdict === 'fail');
  const skipped = findings.filter((f) => f.verdict === 'not-run');
  const pass = findings.filter((f) => f.verdict === 'pass');
  const line = '='.repeat(66);
  console.log('');
  console.log(line);
  console.log(`${script}  →  ${BADGE[code]}  (exit ${code})`);
  console.log(
    `${line}`
  );
  console.log(`fail ${String(fails.length).padStart(3)}   pass ${String(pass.length).padStart(3)}   not-run ${String(skipped.length).padStart(3)}`);
  for (const f of fails) {
    console.log(`  [${f.severity}/${f.level}] ${f.id} — ${f.title}`);
    if (f.locator && f.locator.file) console.log(`      at ${f.locator.file}${f.locator.line ? ':' + f.locator.line : ''}`);
    if (f.locator && f.locator.url) console.log(`      at ${f.locator.url}`);
    if (f.repro) console.log(`      repro: ${f.repro}`);
  }
  for (const f of skipped) {
    console.log(`  [SKIP] ${f.id} — ${f.reason || f.title}`);
    if (f.unblockCommand) console.log(`      unblock: ${f.unblockCommand}`);
  }
  if (extra.note) console.log(`note: ${extra.note}`);
  if (code === EXIT.PARTIAL || code === EXIT.UNUSABLE) {
    console.log('!! 本脚本未完整执行：以上 SKIP 不等于「通过」，也不等于「无问题」。');
  }
  console.log(line);
  return code;
}

/** 参数/环境错误：exit 4，并打印用法。 */
export function usage(script, usageLine, message) {
  console.error(`${script}: ${message || '参数错误'}`);
  console.error(`用法: ${usageLine}`);
  return EXIT.USAGE;
}
