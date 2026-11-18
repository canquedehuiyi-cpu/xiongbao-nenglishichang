/**
 * 可单测的纯规则函数。
 *
 * 为什么单独成模块：各检测脚本文件末尾都有 `process.exitCode = await main(...)`，
 * 一旦被 import 就会真的跑一整轮——所以「想单测某个判定逻辑」只能把逻辑挪到这种
 * 无副作用的模块里。新加判定逻辑时，凡是需要被 selftest 直接断言的，都放这里。
 */

/**
 * .gitignore 规则 → 安全正则。
 * gitignore 允许 `[`、`(`、`+`、`?` 作为字面量；不先转义就 new RegExp 会抛 SyntaxError，
 * 曾经让整个 gates.mjs 崩掉、7 行 SEC 结论一行都写不进账本（而 exit 1 看起来像「有发现」）。
 * @param {string} pattern
 * @returns {{ok:boolean, re?:RegExp, error?:string}}
 */
export function gitignoreToRegExp(pattern) {
  const p = String(pattern == null ? '' : pattern).trim();
  if (!p) return { ok: false, error: '空规则' };
  try {
    const dirOnly = p.endsWith('/');
    const body = p
      .replace(/^\/+/, '')
      .replace(/\/+$/, '')
      .replace(/[.+?^${}()|[\]\\]/g, '\\$&') // 先转义全部正则元字符（含 `[`）
      .replace(/\\\*\\\*/g, '@@') // 上一步把 * 也转义了，这里还原两级通配
      .replace(/\\\*/g, '[^/]*')
      .replace(/@@/g, '.*');
    if (!body) return { ok: false, error: '去锚定后为空' };
    return { ok: true, re: new RegExp('(^|/)' + body + (dirOnly ? '($|/)' : '($|[./])')) };
  } catch (e) {
    return { ok: false, error: String(e.message || e).slice(0, 60) };
  }
}

/**
 * 判断某个 URL 是否仍在本次运行绑定的主机上（`--pages` 可以传绝对 URL 或 `//host/`，
 * 不校验就等于开了一个跨主机后门，绕过单主机红线）。
 * @returns {{ok:boolean, host:string, reason:string}}
 */
export function sameHostAs(candidates, base) {
  let baseHost = '';
  try {
    baseHost = new URL(base).host;
  } catch {
    return { ok: false, host: '', reason: `基准 URL 无法解析: ${base}` };
  }
  for (const c of [].concat(candidates)) {
    let h = '';
    try {
      h = new URL(c, base).host;
    } catch {
      return { ok: false, host: '', reason: `路径无法解析，已拒绝: ${String(c).slice(0, 60)}` };
    }
    if (h !== baseHost) return { ok: false, host: h, reason: `越界主机：${h}（本次只授权 ${baseHost}）` };
  }
  return { ok: true, host: baseHost, reason: '' };
}

/** 解出颜色：支持 3/4/6/8 位十六进制、rgb()/rgba()（含 % 与斜杠语法）。 */
export function parseColor(text) {
  const t = String(text || '').trim();
  let m = /^#([0-9a-fA-F]{3,8})$/.exec(t);
  if (m) {
    let h = m[1];
    if (h.length === 4) h = h.slice(0, 3).split('').map((c) => c + c).join('');
    if (h.length === 8) h = h.slice(0, 6);
    if (h.length === 3) h = h.split('').map((c) => c + c).join('');
    if (h.length !== 6) return null;
    return [0, 2, 4].map((i) => parseInt(h.slice(i, i + 2), 16));
  }
  m = /^rgba?\(([^)]+)\)$/.exec(t);
  if (m) {
    const parts = m[1].trim().split(/[\s,/]+/).filter(Boolean);
    if (parts.length < 3) return null;
    const rgb = [];
    for (let i = 0; i < 3; i++) {
      const v = parts[i];
      const n = v.endsWith('%') ? (parseFloat(v) / 100) * 255 : parseFloat(v);
      if (!Number.isFinite(n)) return null;
      rgb.push(Math.max(0, Math.min(255, Math.round(n))));
    }
    return rgb;
  }
  return null;
}

/** WCAG 2.1 相对亮度与对比度。 */
export function contrastRatio(fg, bg) {
  const a = parseColor(fg);
  const b = parseColor(bg);
  if (!a || !b) return null;
  const lum = (rgb) => {
    const [r, g, bl] = rgb.map((v) => {
      const s = Math.max(0, Math.min(255, v)) / 255;
      return s <= 0.03928 ? s / 12.92 : ((s + 0.055) / 1.055) ** 2.4;
    });
    return 0.2126 * r + 0.7152 * g + 0.0722 * bl;
  };
  const l1 = lum(a);
  const l2 = lum(b);
  return (Math.max(l1, l2) + 0.05) / (Math.min(l1, l2) + 0.05);
}

/**
 * 粗粒度 YAML 扫描：只取 CI 加固判定用得上的两类信息——
 * `permissions` 块的键值，和 `run:` 的实际脚本体（含 `|` / `>` 块标量）。
 *
 * 为什么不用正则一把梭：`run: |` 之后的脚本体在**后续行**里，
 * 只看 `run:` 那一行会把多行的 `${{ }}` 插值全部漏掉（本轮自审实测：
 * 一个把 issue 标题插进 run 的工作流被判成「无插值」）。这不是省事的问题，
 * 是漏报会写成通过的问题。
 * @param {string} text 工作流原文
 * @returns {{permissions: Array<{job:string|null, inline:string, keys:object, line:number}>, runs: Array<{job:string|null, code:string, line:number}>}}
 */
export function scanWorkflowYaml(text) {
  const lines = String(text).split(/\r?\n/);
  const permissions = [];
  const runs = [];
  let section = null;
  let job = null;
  const indentOf = (l) => (l.match(/^[ \t]*/)[0] || '').replace(/\t/g, '  ').length;
  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    if (!line.trim() || /^\s*#/.test(line)) continue;
    const ind = indentOf(line);
    const km = /^\s*("?[\w.-]+"?)\s*:\s*(.*)$/.exec(line.replace(/^\s*-\s+/, (s) => ' '.repeat(s.length)));
    if (!km) continue;
    const key = km[1].replace(/^"|"$/g, '');
    if (ind === 0) { section = key; job = null; }
    else if (section === 'jobs' && ind === 2) job = key;
    const value = km[2].trim();
    if (key === 'permissions') {
      const keys = {};
      if (value === '' || /^[|>]/.test(value)) {
        for (let j = i + 1; j < lines.length; j++) {
          if (!lines[j].trim() || /^\s*#/.test(lines[j])) continue;
          if (indentOf(lines[j]) <= ind) break;
          const m2 = /^\s*("?[\w.-]+"?)\s*:\s*(.*)$/.exec(lines[j]);
          if (m2) keys[m2[1].replace(/^"|"$/g, '').toLowerCase()] = m2[2].trim().replace(/^["']|["']$/g, '');
        }
      }
      permissions.push({ job, inline: value, keys, line: i + 1 });
    }
    if (key === 'run') {
      const body = [];
      if (value === '' || /^[|>][-+\d]*$/.test(value)) {
        for (let j = i + 1; j < lines.length; j++) {
          if (!lines[j].trim()) { body.push(''); continue; }
          if (indentOf(lines[j]) <= ind) break;
          body.push(lines[j]);
        }
      } else {
        body.push(value);
        // 折叠式多行（run: cmd1 && 续行）也带进来，插值可能就在续行上
        for (let j = i + 1; j < lines.length; j++) {
          if (!lines[j].trim() || /^\s*\w+\s*:/ .test(lines[j])) break;
          if (indentOf(lines[j]) <= ind) break;
          body.push(lines[j]);
        }
      }
      runs.push({ job, code: body.join('\n'), line: i + 1 });
    }
  }
  return { permissions, runs };
}

/** 权限块里所有被授予写能力的 scope（`write-all` 记成 '*'）。 */
export function writeScopes(perms) {
  const out = [];
  for (const p of perms || []) {
    const inline = String(p.inline || '').trim();
    const low = inline.toLowerCase();
    if (low === 'write-all') out.push({ job: p.job, scope: '*', level: 'write-all' });
    else if (/^\{\s*\}$/.test(low)) out.push({ job: p.job, scope: '{}', level: 'none' });
    else if (low.startsWith('{')) {
      // 流式写法 `permissions: {contents: write-all, id-token: write}`：
      // 只认块状缩进的话，这一行会一个键都读不出来，于是 write-all 大摇大摆地过检
      const body = low.replace(/^\{/, '').replace(/\}\s*$/, '');
      for (const pair of body.split(',')) {
        const m = /^\s*["']?([\w.-]+)["']?\s*:\s*["']?([\w.-]+)["']?\s*$/.exec(pair);
        if (m && (m[2] === 'write' || m[2] === 'admin' || m[2] === 'write-all')) out.push({ job: p.job, scope: m[1], level: m[2] });
      }
      if (!out.filter((x) => x.job === p.job).length) out.push({ job: p.job, scope: '?', level: 'unparsed-flow-mapping' });
    }
    for (const [k, v] of Object.entries(p.keys || {})) {
      const level = String(v).toLowerCase();
      if (level === 'write' || level === 'admin' || level === 'write-all') out.push({ job: p.job, scope: k, level });
    }
  }
  return out;
}

/**
 * 哪些上下文是「不可信输入」：即使提交者没有仓库写权限也能左右的字段。
 * issue/PR 的标题与正文、评论、review 意见、discussion、repository_dispatch 的
 * client_payload——把这些插进 run: 就是让外部贡献者直接在 runner 上执行脚本。
 */
const UNTRUSTED_CTX = /github\.event\.(?:issue|pull_request|comment|discussion|review|review_comment|client_payload)\b|github\.event\.(?:head_?commit|commits)\b|github\.event\.workflow_run\.(?:head_branch|display_title)\b/gi;

/** run 体里出现的上下文插值，按「是否不可信」分开返回。 */
export function runInterpolations(runs) {
  const untrusted = [];
  const other = [];
  for (const r of runs || []) {
    const code = String(r.code || '');
    for (const m of code.matchAll(/\$\{\{([\s\S]*?)\}\}/g)) {
      const expr = m[1].trim();
      UNTRUSTED_CTX.lastIndex = 0;
      const hit = UNTRUSTED_CTX.exec(expr);
      if (hit) untrusted.push({ job: r.job, line: r.line, expr: expr.slice(0, 80), why: hit[0] });
      else other.push({ job: r.job, line: r.line, expr: expr.slice(0, 80) });
    }
    UNTRUSTED_CTX.lastIndex = 0;
  }
  return { untrusted, other };
}

/**
 * git 配置里「下次任意 git 操作就会执行命令」的键。
 *
 * 为什么单列：这些键不会让仓库看起来可疑——它们只是把「打开这个仓库」变成执行入口。
 * 克隆一个带 `ext::` 远端或 `!cmd` 凭据助手的仓库，再跑一次 `git status` / `git diff`，
 * 命令就在审查机上执行了。审查者读的是被审项目的 .git/config，属于「不可信输入驱动的副作用」。
 * @param {string} text .git/config 原文
 * @returns {Array<{k:string, why:string, exec:boolean, line:number}>}
 */
export function gitConfigRisks(text) {
  const out = [];
  let section = '';
  let sub = '';
  const lines = String(text).split(/\r?\n/);
  for (let i = 0; i < lines.length; i++) {
    const raw = lines[i].trim();
    if (!raw || raw.startsWith('#') || raw.startsWith(';')) continue;
    const sm = /^\[([^\]"]+)(?:\s+"([^"]*)")?\]$/.exec(raw);
    if (sm) {
      section = sm[1].trim().toLowerCase();
      sub = sm[2] || '';
      continue;
    }
    const km = /^([\w.-]+)\s*=\s*(.*)$/.exec(raw);
    if (!km) continue;
    const key = km[1].toLowerCase();
    const value = km[2].trim().replace(/^"|"$/g, '');
    const at = `${section}${sub ? ` "${sub}"` : ''}.${key}`;
    const push = (k, why, exec) => out.push({ k, why: `${at}: ${why}`, exec, line: i + 1 });
    if (/^ext::/i.test(value)) push('ext-remote', '远端用 ext:: 包装器，git 会执行后面的命令', true);
    else if (key === 'helper' && section === 'credential' && value.includes('!')) push('credential-helper-exec', '凭据助手以 ! 开头，等于让配置里的 shell 命令处理凭据', true);
    else if ((key === 'smudge' || key === 'clean') && section === 'filter' && (value.includes('!') || /^ext::/i.test(value))) push('filter-cmd', `自定义 filter.${key} 会在 checkout/加签时执行命令`, true);
    else if (key === 'textconv' && section === 'diff' && (value.includes('!') || value.startsWith('/'))) push('textconv', 'textconv 会在 git diff/展示文件时执行外部程序', true);
    else if (key === 'fsmonitor' && section === 'core' && value && value !== 'false') push('fsmonitor', 'core.fsmonitor 会启动外部进程', true);
    else if (key === 'hookspath' && section === 'core') {
      const v = value.replace(/\\/g, '/');
      if (v && !/(^|\/)\.git\/hooks$/.test(v)) push('hooksPath', `core.hooksPath 指向 ${v}：钩子可以来自工作树任意位置，随克隆一起进来`, true);
    } else if (section === 'alias' && value.startsWith('!')) push('alias-exec', 'alias 以 ! 开头，git <别名> 会执行 shell 命令', true);
    else if (key === 'path' && (section === 'include' || section.startsWith('includeif'))) push('include', '配置从别处再拉一段：被拉进来的文件可以放上面这些可执行键', true);
    else if (key === 'url' && /\/\/[^@/\s:]+:[^@\s/]+@/.test(value)) push('embedded', '远端 URL 里内嵌了凭据形态的串', false);
    else if (key === 'insteadof') push('insteadOf', '改写远端地址，可把发往 GitHub 的流量指到别处', false);
  }
  return out;
}
