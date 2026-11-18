#!/usr/bin/env node
/**
 * 注入面：INJ-1..3。
 *
 * 判据一律是「产物里是否出现了未被转义的危险构造」，而不是「有没有奇怪字符」——
 * 前者是真问题，后者会造出一堆自误报（第一轮就吃过 5 个假阳性）。
 * 载荷只打本地渲染器，绝不打线上。
 */

import { existsSync, readFileSync } from 'node:fs';
import { join, resolve, relative } from 'node:path';
import { pathToFileURL } from 'node:url';
import { parseArgs, makeFindingCtx, safeRun, guardPaths, usage, makeWorktree, cleanWorktrees } from './lib/harness.mjs';
import { readJsonIfExists } from './lib/jsonl.mjs';

const SCRIPT = 'injection.mjs';
const USAGE = 'audit injection --out <dir> --repo <dir> [--renderer <相对路径>]';

const RENDER_EXPORTS = ['renderInline', 'render', 'inline', 'mdInline', 'renderMarkdown'];
const SOURCE_EXPORTS = ['parseSources', 'splitSourceParts', 'parseSourceLine'];
const LOOKUP_EXPORTS = ['sectionClass', 'getSectionMeta', 'sectionMeta', 'iconFor', 'ICONS', 'SECTIONS', 'SECTION_CLASS'];

/**
 * 危险构造：必须处在「markup 位置」才算命中。
 * 转义会把 < > " 变成实体，但属性名文字仍留在正文里——
 * 若只看 ` onerror=` 就会把已经正确转义的输出判成漏洞（这里踩过一次，5 个假阳性）。
 */
const DANGEROUS = [
  { name: '未转义 <img>', re: /<img\b/i },
  { name: '未转义 <svg>', re: /<svg\b/i },
  { name: '未转义 <script>', re: /<script\b/i },
  { name: '真实标签上的内联事件属性', re: /<[a-z][^>]*?\son[a-z]+\s*=\s*["'`]?/i },
  { name: 'javascript: 协议（属性位）', re: /(?:href|src|action|xlink:href)\s*=\s*["']?\s*javascript:/i },
  { name: '未转义收尾引号逃逸出属性', re: /"\s+[a-z-]+\s*=\s*"[^"]*"\s*>/ },
  { name: '孤立 </strong>', re: /<\/strong>/ },
];

const XSS = [
  { name: 'IMG onerror', input: '<img src=x onerror=alert(1)>', how: '裸 HTML' },
  { name: 'SVG onload', input: '<svg onload=alert(1)>x</svg>', how: '裸 HTML' },
  { name: 'javascript: 链接', input: '[点我](javascript:alert(1))', how: 'markdown 链接协议' },
  { name: 'data: 链接', input: '[点我](data:text/html;base64,PHNjcmlwdD4=)', how: 'markdown 链接协议' },
  { name: '属性断裂', input: '[a](https://e.example/x" onmouseover="alert(1))', how: 'URL 里的引号' },
  { name: '尖括号实体', input: '&lt;script&gt;alert(1)&lt;/script&gt;', how: '已编码输入' },
  { name: '协议相对', input: '[a](//evil.example/x)', how: 'protocol-relative' },
];

const ORDER = [
  { name: '含一层平衡括号的 URL', input: '[百科](https://e.example/item_(消歧义))', expect: (h) => h.includes('item_(消歧义)') || 'href 少了收尾右括号，且正文留下裸括号' },
  { name: 'URL 里含星号', input: '[链接](https://e.example/a**b)', expect: (h) => !/<strong>/.test(h) && !/href="[^"]*<strong>/.test(h) || '粗体替换在链接之后跑，把 <strong> 写进了 href' },
  { name: '孤立的双星号词', input: '调用 **kwargs 时需注意', expect: (h) => !/<strong>/.test(h) || '非粗体星号对被错误配对' },
  { name: 'glob 模式', input: '匹配 src/**/*.ts 的文件', expect: (h) => (h.match(/<strong>/g) || []).length === 0 || 'glob 星号被当成粗体' },
  { name: '中文全角括号 URL', input: '[甲](https://e.example/条目（一）)', expect: (h) => /条目（一）/.test(h) || '全角括号形态的 URL 被截断' },
];

async function loadRenderer(repo, hint) {
  // 只要求「仓库内相对路径」：绝对路径、盘符、.. 分段都要拒
  const bad = hint && (/^[A-Za-z]:/.test(hint) || hint.startsWith('/') || hint.startsWith(String.fromCharCode(92)) || hint.split(/[\/]/).includes('..'));
  if (bad) {
    throw new Error('--renderer 必须是仓库内相对路径（不接受绝对路径或 ..），收到: ' + hint);
  }
  const tries = hint
    ? [hint]
    : ['tools/render.js', 'tools/render.mjs', 'src/lib/parser.ts', 'src/lib/parser.js', 'src/lib/render.ts', 'lib/render.js'];
  const errs = [];
  for (const t of tries) {
    const abs = join(repo, t);
    if (!existsSync(abs)) { errs.push(`${t}: 不存在`); continue; }
    try {
      const mod = await import(pathToFileURL(abs).href);
      return { file: t, mod };
    } catch (e) {
      // 「文件在但加载不了」和「没有这个文件」是两件完全不同的事，
      // 混成一条提示会让人对着一个根本不存在的路径反复调 --renderer。
      errs.push(`${t}: ${String(e.message || e).slice(0, 70)}`);
    }
  }
  return { file: null, errs };
}

async function main(argv) {
  let opts;
  try {
    opts = parseArgs(argv, { value: ['out', 'repo', 'renderer'] }).opts;
  } catch (e) {
    return usage(SCRIPT, USAGE, e.message);
  }
  guardPaths(opts, SCRIPT);
  if (!opts.out) return usage(SCRIPT, USAGE, '需要 --out');
  const capsDoc = readJsonIfExists(resolve(opts.out), 'capabilities.json');
  const ctx = makeFindingCtx(SCRIPT, opts, capsDoc);
  const { record } = ctx;
  const repo = opts.repo ? resolve(opts.repo) : null;
  if (!repo) {
    for (const id of ['INJ-1', 'INJ-2', 'INJ-3']) record({ id, verdict: 'not-run', reason: '需要 --repo：这一组要直接调用被审项目自己的渲染器' });
    return ctx.finish();
  }
  // 必须从 --out 的副本里 import：直接 import 被审项目代码会在真实树上执行
  // （对抗审查用 tools/render.js 在仓库里落了标记文件，实测成功），
  // 而 SKILL.md 的第二条硬规则写的就是「只在 --out 的副本里跑」。
  const execRepo = makeWorktree(opts.out, repo, 'inj-worktree');
  let loaded;
  try {
    loaded = await loadRenderer(execRepo, opts.renderer);
  } catch (e) {
    cleanWorktrees();
    return usage(SCRIPT, USAGE, e.message);
  }
  if (!loaded || !loaded.file) {
    const why = loaded && loaded.errs ? loaded.errs.join('；').slice(0, 200) : '候选清单为空';
    for (const id of ['INJ-1', 'INJ-2', 'INJ-3']) {
      record({ id, verdict: 'not-run', reason: `没能拿到渲染器（${why}）；用 --renderer <仓库内相对路径> 指明真正生成页面正文的那个文件` });
    }
    cleanWorktrees();
    return ctx.finish();
  }
  const rel = (f) => relative(repo, join(repo, f)).split('\\').join('/');
  const call = (names, args) => {
    // 被 import 的 CJS 模块，其 module.exports 挂在 default 上；只看命名空间会
    // 得出「这个渲染器没有 render 导出」的错误结论（第 3 轮实测）。
    const bag = { ...loaded.mod, ...(loaded.mod.default && typeof loaded.mod.default === 'object' ? loaded.mod.default : {}) };
    for (const n of names) {
      const fn = bag[n];
      if (typeof fn === 'function') {
        try {
          return { name: n, out: fn(...args) };
        } catch (e) {
          return { name: n, threw: String(e.message || e).slice(0, 80) };
        }
      }
      if (fn && typeof fn === 'object' && typeof args[0] === 'string' && n in fn) return { name: n, out: fn[args[0]] };
    }
    return { name: null, out: undefined };
  };

  const render = (text) => {
    const r = call(RENDER_EXPORTS, [text]);
    if (r.threw) throw new Error(`${r.name} 抛错：${r.threw}`);
    return typeof r.out === 'string' ? r.out : r.out && typeof r.out === 'object' ? String(r.out.__html ?? JSON.stringify(r.out)) : '';
  };

  /* ---------- INJ-1 XSS 载荷电池 ---------- */
  // 先证明「我给的文字真的经过了渲染器」。上一版把载荷塞进一个由渲染器自己生成的标记位置，
  // 于是一个不做该替换的渲染器（只导出 render(md)=md.replace(/^# (.+)$/, '<h1>$1</h1>') 那种）
  // 从头到尾没吃到载荷，输出里自然没有危险构造，INJ-1 就报「7 个载荷全部被转义」——假通过。
  // 回显探针不通时整组记 not-run：宁可少一项结论，也不要一项站不住的通过。
  const ECHO = 'site-audit-echo-probe-7f3a';
  const echoOut = (() => {
    try {
      return render('段落前缀 ' + ECHO + ' 后缀');
    } catch {
      return '';
    }
  })();
  // 转义过的形态也算抵达：`&lt;`/`&gt;` 之外本探针不用尖括号，实体编码只可能出现在引号上
  const echoSeen = String(echoOut).includes(ECHO);
  let fired = [];
  let broke = [];
  if (!echoSeen) {
    // 载荷根本没进渲染器：这时「产物里没有危险构造」是废话，不是结论
    for (const id of ['INJ-1', 'INJ-2', 'INJ-3']) {
      record({
        id,
        verdict: 'not-run',
        reason: `回显探针没能穿过 ${loaded.file}（输出里找不到探针字串）：这个导出不是真正渲染正文的那一层，报「已转义」会是假结论`,
        unblockCommand: '用 --renderer 指向真正生成页面正文的文件/导出（能把你给的文字渲染出来的那个）',
      });
    }
    cleanWorktrees();
    return ctx.finish();
  }
  for (const p of XSS) {
    let html = '';
    try {
      html = render(p.input);
    } catch (e) {
      broke.push({ name: p.name, err: String(e.message).slice(0, 60) });
      continue;
    }
    const hits = DANGEROUS.filter((d) => d.re.test(html)).map((d) => d.name);
    if (hits.length) fired.push({ name: p.name, how: p.how, hits, sample: html.slice(0, 120) });
  }
  record({
    id: 'INJ-1',
    verdict: fired.length || broke.length ? 'fail' : 'pass',
    severity: fired.length ? 'P1' : broke.length ? 'P2' : '-',
    title: fired.length
      ? `${fired.length}/${XSS.length} 个载荷以未转义形态穿过渲染器：${fired.map((f) => `${f.name}→${f.hits.join('+')}`).join('；')}`
      : broke.length
        ? `渲染器被载荷输入直接打崩：${broke.map((b) => b.name).join('、')}`
        : `${XSS.length} 个载荷全部被转义或拒绝（判据：产物里不出现未转义标签/事件属性/js: 协议）`,
    evidence: JSON.stringify(fired[0] || broke[0] || { payloads: XSS.length, renderer: rel(loaded.file) }).slice(0, 240),
    locator: { file: rel(loaded.file) },
    repro: `import ${rel(loaded.file)} 后逐个渲染 ${XSS.length} 个载荷，检查输出里是否出现未转义构造`,
  });

  /* ---------- INJ-2 替换顺序与正则形态 ---------- */
  const orderBad = [];
  for (const c of ORDER) {
    let html = '';
    try {
      html = render(c.input);
    } catch (e) {
      orderBad.push({ name: c.name, why: '抛错 ' + String(e.message).slice(0, 50) });
      continue;
    }
    const r = c.expect(html);
    if (r !== true) orderBad.push({ name: c.name, why: r, out: html.slice(0, 110) });
  }
  record({
    id: 'INJ-2',
    verdict: orderBad.length ? 'fail' : 'pass',
    severity: orderBad.some((o) => /href/.test(o.why || '')) ? 'P1' : orderBad.length ? 'P2' : '-',
    title: orderBad.length
      ? `${orderBad.length}/${ORDER.length} 个形态被渲染错：${orderBad.map((o) => `${o.name}（${o.why}）`).join('；')}`
      : `${ORDER.length} 个易错形态（平衡括号、URL 内星号、glob、孤立星号对、全角括号）全部正确`,
    evidence: JSON.stringify(orderBad[0] || { cases: ORDER.length }).slice(0, 240),
    locator: { file: rel(loaded.file) },
    nextAction: orderBad.length ? '让链接先占位、粗体用 CommonMark 的 flanking 规则；URL 正则改成深度计数而非字符类' : '',
  });

  /* ---------- INJ-3 原型链查表 ---------- */
  const protoBad = [];
  for (const key of ['constructor', '__proto__', 'toString', 'hasOwnProperty']) {
    const a = call(LOOKUP_EXPORTS, [key]);
    const v = a.out;
    if (a.name && (typeof v === 'function' || (v && typeof v === 'object'))) {
      protoBad.push({ key, via: a.name, type: typeof v, preview: String(v).slice(0, 40) });
    }
  }
  record({
    id: 'INJ-3',
    verdict: LOOKUP_EXPORTS.some((n) => loaded.mod[n]) ? (protoBad.length ? 'fail' : 'pass') : 'not-run',
    severity: protoBad.length ? 'P1' : '-',
    reason: protoBad.length ? '' : '渲染器模块没有导出查表函数（试过 ' + LOOKUP_EXPORTS.join('/') + '）',
    title: protoBad.length
      ? `不可信键直接查对象字面量会撞上原型成员：${protoBad.map((p) => `${p.key}→${p.type}`).join('、')}；若该值经 set:html/innerHTML 落进 DOM，即为脚本注入`
      : '板块/图标查表对原型成员安全（或不可达）',
    evidence: JSON.stringify(protoBad[0] || {}).slice(0, 200),
    locator: { file: rel(loaded.file) },
    nextAction: protoBad.length ? '改用 Object.hasOwn(obj, key) 判定后再取值，或把表换成 Map' : '',
  });

  const code = ctx.finish();
  cleanWorktrees();
  return code;
}

process.exitCode = await safeRun(SCRIPT, USAGE, main, process.argv.slice(2));
