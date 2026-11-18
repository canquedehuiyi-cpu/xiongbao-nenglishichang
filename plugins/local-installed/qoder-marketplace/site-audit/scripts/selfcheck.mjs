#!/usr/bin/env node
/**
 * 出包前的隐私闸门：selfcheck.mjs。
 *
 * 为什么存在：这套工具用来审别人的站，它自己的包里绝不能夹带审查者自己的数据。
 * 这种泄露靠自觉防不住，所以做成一条退出码：不过就不准出包。
 *
 * 第一版实现有个讽刺的缺陷：列 ZIP 目录用了 PATH 上的 `tar`，而 Git Bash 的 tar 是
 * GNU tar、读不了 zip → 目录清单为 null → 「../」越界、绝对路径、混入 .git 等结构检查
 * **全部静默跳过，却照样打印「结构合规」**。现在所有结构判定都从「真正解出来的树」推导，
 * 解不出来就硬失败，并额外用 --expect-tree 做「打包↔解包」往返校验。
 *
 * 命中时只报「文件名 + 命中项编号」，绝不回显内容——回显本身就是二次泄露。
 */

import {
  existsSync, readFileSync, readdirSync, statSync, lstatSync,
  mkdtempSync, rmSync, openSync, readSync, closeSync,
} from 'node:fs';
import { join, resolve, relative, sep } from 'node:path';
import { tmpdir } from 'node:os';
import { spawnSync } from 'node:child_process';
import { parseArgs, EXIT, usage } from './lib/tools.mjs';
import { safeRun } from './lib/harness.mjs';
import { scanTree } from './lib/scan.mjs';

const SCRIPT = 'selfcheck.mjs';
const USAGE =
  'audit selfcheck (--zip <path> | --dir <path>) [--forbidden <file>] [--expect-tree <dir>]' +
  ' [--max-bytes 8000000]';

/** 本地 bsdtar 能读 zip；Git Bash 的 GNU tar 不能，所以逐个试并校验解包结果。 */
function tarCandidates() {
  // 不写字面盘符路径（也会被自己的隐私闸门按「本机路径痕迹」拦下），
  // 而且读 SystemRoot 本来就更正确：Windows 目录未必在 C 盘。
  const out = ['bsdtar', 'tar'];
  if (process.platform === 'win32' && process.env.SystemRoot) {
    out.unshift(join(process.env.SystemRoot, 'System32', 'tar.exe'));
  }
  return out;
}

/**
 * 直接读中央目录里的**原始条目名**，不经过任何解包器。
 *
 * 为什么必须自己解析：解包器宽容。bsdtar 会把 `bin\audit.mjs` 里的反斜杠当普通字符或顺手规范化，
 * 于是「用 Windows 分隔符存名字」这种包在自检里一切正常，而严格按 ZIP 规范（APPNOTE 要求条目名用 `/`）
 * 解析的提交侧会判「包含非法包内路径，路径必须位于包根目录内」。这正是上一轮踩的坑：
 * Compress-Archive 兜底出的包，条目名全是反斜杠，而我们的结构检查是拿解出来的树做的，看不见。
 */
export function zipEntryNames(zipPath) {
  let buf;
  try {
    buf = readFileSync(zipPath);
  } catch (e) {
    return { names: [], error: '读不到文件：' + (e.code || e.message) };
  }
  let eocd = -1;
  const floor = Math.max(0, buf.length - 66000);
  for (let i = buf.length - 22; i >= floor; i--) {
    if (buf.length >= i + 22 && buf.readUInt32LE(i) === 0x06054b50) { eocd = i; break; }
  }
  if (eocd < 0) return { names: [], error: '找不到中央目录结束记录（EOCD）——不是标准 ZIP' };
  const count = buf.readUInt16LE(eocd + 10);
  const cdSize = buf.readUInt32LE(eocd + 12);
  let off = buf.readUInt32LE(eocd + 16);
  if (count === 0xffff || cdSize === 0xffffffff) return { names: [], error: 'ZIP64 包：本闸门不解析，请改用别的形态出包' };
  if (off + cdSize > buf.length) return { names: [], error: '中央目录越界（表头长度与实际文件不符）' };
  const names = [];
  for (let n = 0; n < count; n++) {
    if (off + 46 > buf.length || buf.readUInt32LE(off) !== 0x02014b50) {
      return { names, error: '中央目录第 ' + (n + 1) + '/' + count + ' 条签名不对（表被截断或损坏）' };
    }
    const nameLen = buf.readUInt16LE(off + 28);
    const extraLen = buf.readUInt16LE(off + 30);
    const commentLen = buf.readUInt16LE(off + 32);
    names.push(buf.toString('utf8', off + 46, off + 46 + nameLen));
    off += 46 + nameLen + extraLen + commentLen;
  }
  return { names, error: null };
}

/** 原始条目名层面的路径合法性——提交侧的判据，比解包后的树更严。 */
export function rawPathProblems(names) {
  const bad = [];
  for (const n of names) {
    if (!n) bad.push('(空条目名)');
    else if (n.includes('\\')) bad.push(n);
    else if (n.startsWith('/')) bad.push(n);
    else if (/^[A-Za-z]:/.test(n)) bad.push(n);
    else if (n === '.' || n === './' || n.startsWith('./')) bad.push(n);
    else if (/(^|\/)\.\.(\/|$)/.test(n)) bad.push(n);
  }
  return bad;
}

function isZipFile(path) {
  const buf = Buffer.alloc(4);
  let fd;
  try {
    fd = openSync(path, 'r');
    if (readSync(fd, buf, 0, 4, 0) !== 4) return false;
    // PK\003\004 —— 空包（创建失败）与「名字叫 .zip 的 tar」都会在这里被抓住
    return buf[0] === 0x50 && buf[1] === 0x4b && buf[2] === 0x03 && buf[3] === 0x04;
  } catch {
    return false;
  } finally {
    if (fd !== undefined) closeSync(fd);
  }
}

function listFiles(dir, out = [], base = dir) {
  let names = [];
  try {
    names = readdirSync(dir);
  } catch {
    return out;
  }
  for (const n of names) {
    const full = join(dir, n);
    const st = lstatSync(full);
    if (st.isSymbolicLink()) out.push({ rel: relative(base, full).split(sep).join('/'), symlink: true, size: 0 });
    else if (st.isDirectory()) listFiles(full, out, base);
    else out.push({ rel: relative(base, full).split(sep).join('/'), symlink: false, size: st.size });
  }
  return out;
}

function extract(zipPath, dst) {
  const attempts = [];
  for (const t of tarCandidates()) {
    attempts.push(() => spawnSync(t, ['-xf', zipPath, '-C', dst], { encoding: 'utf8', timeout: 120000 }));
  }
  attempts.push(() =>
    spawnSync('powershell.exe', [
      '-NoProfile', '-Command',
      `Expand-Archive -LiteralPath '${zipPath.replace(/'/g, '')}' -DestinationPath '${dst.replace(/'/g, '')}' -Force`,
    ], { encoding: 'utf8', timeout: 120000 })
  );
  for (const a of attempts) {
    try {
      const r = a();
      if (r.status === 0 && listFiles(dst).length > 0) return { ok: true };
    } catch {
      /* 换下一种解法 */
    }
  }
  return { ok: false };
}

/** 从解出来的树推导结构结论；每项检查是否真跑过都记进 coverage。 */
function structuralChecks(files, opts, rootDir) {
  const problems = [];
  const coverage = [];
  const rels = files.map((f) => f.rel);
  const maxBytes = Number(opts.maxBytes) || 8_000_000;
  const total = files.reduce((n, f) => n + f.size, 0);

  coverage.push('解包文件数>0');
  if (rels.some((r) => r.startsWith('../') || r.includes('/../'))) {
    problems.push('存在 ../ 越界路径条目（解包会写到目标目录之外）');
  }
  coverage.push('../ 越界');
  if (rels.some((r) => /^([A-Za-z]:[/\\]|[\\/])/.test(r))) problems.push('存在绝对路径条目');
  coverage.push('绝对路径');
  if (files.some((f) => f.symlink)) problems.push('存在符号链接条目（解包时可指向任意位置）');
  coverage.push('符号链接');
  if (rels.some((r) => /(^|\/)(\.git|node_modules)(\/|$)/.test(r))) problems.push('包里带了 .git 或 node_modules');
  coverage.push('.git/node_modules 混入');
  const hasManifest = rels.some((r) => r === '.qoder-plugin/plugin.json' || r.endsWith('/.qoder-plugin/plugin.json'));
  const hasSkill = rels.some((r) => r === 'SKILL.md' || r.endsWith('/SKILL.md'));
  if (!hasManifest && !hasSkill) problems.push('包里既没有 .qoder-plugin/plugin.json 也没有 SKILL.md，装了也不会被识别');
  /*
   * 提交侧在**压缩包根**上找清单：根目录必须直接有 plugin.json（Plugin 形态）或 SKILL.md（Skill 形态）。
   * 只把清单藏在 .qoder-plugin/ 里、或者整棵树被裹进一层同名目录，本地安装照样能装，
   * 上传时却报「缺少 manifest 或 SKILL.md」——这个坑是实测撞出来的，不是推理出来的。
   */
  const rootManifest = rels.filter((r) => /^(plugin\.json|SKILL\.md)$/i.test(r));
  if (!rootManifest.length) {
    const nested = rels.filter((r) => /(^|[/\\])(plugin\.json|SKILL\.md)$/i.test(r));
    problems.push(`压缩包根目录没有 plugin.json 也没有 SKILL.md（清单在 ${nested.slice(0, 2).join('、') || '任何地方都没有'}）——提交侧只认压缩包根上的这一份，会报「缺少 manifest 或 SKILL.md」`);
  }
  const dupManifests = rels.filter((r) => /(^|[/\\])plugin\.json$/i.test(r));
  if (dupManifests.length > 1) {
    let first = null;
    let drift = null;
    for (const r of dupManifests) {
      try {
        const t = readFileSync(join(rootDir || '.', r), 'utf8');
        if (first == null) first = t;
        else if (first !== t) drift = r;
      } catch { /* 读不到就不据此下结论 */ }
    }
    if (drift) problems.push(`多份 plugin.json 内容不一致（${dupManifests.join('、')}），漂移的那份：${drift}`);
  }
  coverage.push('压缩包根有清单/SKILL.md 且多份清单不漂移');
  coverage.push('清单存在性');
  if (total > maxBytes) problems.push(`解包后 ${total} 字节超上限 ${maxBytes}`);
  coverage.push('体积上限');
  // 图标与展示文案由使用者自己决定（本轮要求：displayName / description / logo 不进包）。
  // 这条查的是漂移：清单里没有 logo 引用，包里却躺着一份图标资源。
  const manifestRel = rels.filter((r) => r.endsWith('.qoder-plugin/plugin.json'));
  let manifestText = '';
  for (const r of manifestRel) {
    try {
      manifestText += readFileSync(join(rootDir || ".", r), 'utf8');
    } catch { /* 读不到就不据此下结论 */ }
  }
  const assetFiles = rels.filter((r) => /(^|[/\\])(assets|icons?)[/\\]|\.(svg|png|ico|jpe?g)$/i.test(r));
  // 没有清单（Skill 形态）时更严：没有任何东西能引用图标，所以包里一个都不该带。
  // 早先这条只在「有清单且清单不含 logo」时生效，于是 Skill 形态搬进图标照样放行——M24 就是这么幸存的。
  if (assetFiles.length && (!manifestRel.length || !manifestText.includes('"logo"'))) {
    problems.push(`包里带了 ${assetFiles.length} 个图标/图片资源（例：${assetFiles[0]}），但${manifestRel.length ? '清单里没有 logo 引用' : '这个形态根本没有清单可以引用它'}——图标应由使用者自己提供，不该混进包里`);
  }
  coverage.push('图标资源与清单一致');

  return { problems, coverage };
}

/** 往返校验：装上去的东西必须等于你打包时暂存的东西。 */
function compareTrees(zipFiles, expectDir) {
  const want = listFiles(expectDir);
  const a = new Map(zipFiles.map((f) => [f.rel, f.size]));
  const b = new Map(want.map((f) => [f.rel, f.size]));
  const missing = [...b.keys()].filter((k) => !a.has(k));
  const extra = [...a.keys()].filter((k) => !b.has(k));
  const differ = [...a.keys()].filter((k) => b.has(k) && a.get(k) !== b.get(k));
  return { missing, extra, differ, wantCount: b.size, gotCount: a.size };
}

export function inspectPackage(zipPath, opts = {}) {
  const report = { ok: false, problems: [], hits: [], coverage: [], fileCount: 0, roundtrip: null };
  if (!existsSync(zipPath)) {
    report.problems.push(`ZIP 不存在: ${zipPath}`);
    return report;
  }
  if (!isZipFile(zipPath)) {
    report.problems.push('文件不是合法 ZIP（缺 PK\\x03\\x04 魔数）——打包器产出了别的东西，不能出包');
    return report;
  }
  /* 先按提交侧的眼光看这个包：直接解析中央目录的原始条目名。 */
  const raw = zipEntryNames(zipPath);
  if (raw.error) {
    report.problems.push('原始中央目录读不出来：' + raw.error + '——连条目名都验不了，不能出包');
    return report;
  }
  const badNames = rawPathProblems(raw.names);
  if (badNames.length) {
    report.problems.push(`压缩包里有 ${badNames.length} 条非法包内路径（例：${badNames[0]}）——条目名必须用 / 分隔且落在包根之内；解包器会宽容地读它，提交侧不会`);
  }
  const rootFiles = raw.names.filter((n) => n && !n.includes('/') && !n.endsWith('/'));
  if (!rootFiles.some((n) => /^(plugin\.json|SKILL\.md)$/i.test(n))) {
    report.problems.push(`压缩包根上没有 plugin.json 也没有 SKILL.md（根级文件只有：${rootFiles.slice(0, 4).join('、') || '（无）'}）——提交侧只认这一层`);
  }
  const rawCoverage = ['原始条目名合法（/ 分隔·不越界·根上有清单）', '中央目录可解析（含 ZIP64 拒绝）'];
  const tmp = mkdtempSync(join(tmpdir(), 'site-audit-selfcheck-'));
  try {
    const ex = extract(zipPath, tmp);
    if (!ex.ok) {
      report.problems.push('无法解包（bsdtar 与 Expand-Archive 都失败或解出 0 个文件）——无法完成内容扫描，不能出包');
      return report;
    }
    const files = listFiles(tmp);
    report.fileCount = files.length;
    if (!files.length) {
      report.problems.push('解包结果为空目录：解包器「成功」但什么都没放出来，这种包等于没扫');
      return report;
    }
    const { problems, coverage } = structuralChecks(files, opts, tmp);
    report.problems.push(...problems);
    report.coverage = coverage;
    report.coverage.push(...rawCoverage);
    const scan = scanTree(tmp, opts.forbidden || []);
    report.hits = scan.hits;
    report.scanCoverage = scan.coverage;
    // 有盲区就不许报 CLEAN：哨兵词只要落在第 4001 个文件、或落在一个「只按文件名判过」的
    // 二进制里，这次扫描给出的就是「零命中」这个假结论。
    if (scan.coverage.gaps.length) report.problems.push(`隐私扫描有盲区：${scan.coverage.gaps.join('；')}`);
    report.coverage.push(`隐私扫描内容解析 ${scan.coverage.walked - scan.coverage.contentNotRead}/${scan.coverage.walked} 文件`);
    if (opts.expectTree) {
      const rt = compareTrees(files, resolve(opts.expectTree));
      report.roundtrip = { wantCount: rt.wantCount, gotCount: rt.gotCount, missing: rt.missing.length, extra: rt.extra.length, differ: rt.differ.length };
      if (rt.missing.length) report.problems.push(`往返校验：暂存树里有 ${rt.missing.length} 个文件没进包（例：${rt.missing.slice(0, 3).join(', ')}）`);
      if (rt.extra.length) report.problems.push(`往返校验：包里多出 ${rt.extra.length} 个暂存树里没有的文件（例：${rt.extra.slice(0, 3).join(', ')}）`);
      if (rt.differ.length) report.problems.push(`往返校验：${rt.differ.length} 个文件大小与暂存树不一致`);
      report.coverage.push('打包↔解包往返');
    } else {
      report.coverage.push('往返未做（缺 --expect-tree）');
    }
    report.ok = !report.problems.length && !report.hits.length;
    return report;
  } finally {
    rmSync(tmp, { recursive: true, force: true });
  }
}

function printVerdict(label, report, hits) {
  console.log('');
  console.log('='.repeat(66));
  if (hits.length || report.problems.length) {
    console.log(`selfcheck ${label} → BLOCKED (exit 1)`);
    console.log('='.repeat(66));
    console.log(`解包 ${report.fileCount} 个文件：内容命中 ${hits.length} 处、结构问题 ${report.problems.length} 处。`);
    const uniq = new Map();
    for (const h of hits) if (!uniq.has(`${h.file}::${h.ref}`)) uniq.set(`${h.file}::${h.ref}`, h);
    console.log('按「文件 + 命中项编号」列出（不回显内容，避免二次泄露）：');
    for (const h of [...uniq.values()].slice(0, 60)) console.log(`  ${h.file}  ←  ${h.ref}`);
    for (const p of report.problems) console.log(`  [结构] ${p}`);
    console.log('');
    console.log('不允许出包。把上述内容移出产物，或挪到不进 ZIP 的本机文件里。');
    return EXIT.FINDINGS;
  }
  console.log(`selfcheck ${label} → CLEAN (exit 0)`);
  console.log('='.repeat(66));
  console.log(`解包 ${report.fileCount || report.scannedFiles || 0} 个文件：无词表命中、无凭据形态、无本机路径痕迹。`);
  console.log(`结构检查实际覆盖：${report.coverage.length ? report.coverage.join('、') : '（目录扫描模式，无 ZIP 结构检查）'}`);
  if (!report.coverage.includes('打包↔解包往返') && report.coverage.length) {
    console.log('!! 未做往返校验：解包器与打包器不兼容时会「成功地产出空包」。发布请带 --expect-tree。');
  }
  return EXIT.CLEAN;
}

async function main(argv) {
  let opts;
  try {
    opts = parseArgs(argv, {
      value: ['zip', 'forbidden', 'dir', 'expect-tree', 'max-bytes', 'max-entries'],
    }).opts;
  } catch (e) {
    return usage(SCRIPT, USAGE, e.message);
  }
  const words = [];
  if (opts.forbidden) {
    if (!existsSync(resolve(opts.forbidden))) return usage(SCRIPT, USAGE, `词表不存在: ${opts.forbidden}`);
    words.push(...readFileSync(resolve(opts.forbidden), 'utf8').split(/\r?\n/));
  } else {
    console.log('提示：未给 --forbidden 词表，闸门只跑通用凭据/路径形态检查，无法保证不含特定身份数据。');
  }

  if (opts.zip) {
    const report = inspectPackage(resolve(opts.zip), {
      forbidden: words,
      expectTree: opts['expect-tree'] || opts.expectTree,
      maxBytes: opts['max-bytes'] || opts.maxBytes,
    });
    return printVerdict(opts.zip, report, report.hits);
  }

  if (opts.dir) {
    const root = resolve(opts.dir);
    if (!existsSync(root)) return usage(SCRIPT, USAGE, `目录不存在: ${root}`);
    const { hits, files, coverage } = scanTree(root, words);
    const rc = { ok: !hits.length, problems: [], coverage: [], fileCount: files.length };
    // 目录模式（审自己的源码树）不因盲区直接 BLOCK：树里本来就可能有自己的构建产物。
    // 但必须把盲区打印出来——否则「零命中」会被读成「全都扫过了」。
    if (coverage.gaps.length) console.log(`注意：目录扫描有盲区 —— ${coverage.gaps.join('；')}`);
    return printVerdict(opts.dir, rc, hits);
  }

  return usage(SCRIPT, USAGE, '需要 --zip 或 --dir');
}

if (process.argv[1] && process.argv[1].replace(/\\/g, '/').endsWith('scripts/selfcheck.mjs')) {
  process.exitCode = await safeRun(SCRIPT, USAGE, main, process.argv.slice(2));
}
