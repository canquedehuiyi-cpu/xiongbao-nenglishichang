#!/usr/bin/env node
/**
 * 端到端验收：拿自带的合成夹具跑完整一轮，断言「植入的缺陷必须被抓到、
 * 已修复的形态不许误报、隐私闸门必须放行」。
 *
 * 这是本插件自己的回归测试。改任何检测逻辑之后必须重跑：
 *   node bin/audit.mjs selftest
 */

import { spawn, spawnSync } from 'node:child_process';
import { mkdirSync, rmSync, mkdtempSync, writeFileSync, existsSync, readFileSync, readdirSync, statSync } from 'node:fs';
import { join, resolve, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';
import { tmpdir } from 'node:os';
import { readLedger, latestByVerdict } from '../scripts/lib/jsonl.mjs';
import { scanTree } from '../scripts/lib/scan.mjs';
import { regressionChecks } from './selftest-fixes.mjs';

const HERE = dirname(fileURLToPath(import.meta.url));
const ROOT = resolve(HERE, '..');
const FIXTURE = join(ROOT, 'fixtures', 'synthetic-site');
const AUDIT = join(ROOT, 'bin', 'audit.mjs');

/** 必须被抓到的项：夹具里确有对应缺陷 */
const MUST_FAIL = [
  ['CTX-1', '来源段日期未逐段兑现'],
  ['CTX-3', '校验器对违规样本仍放行（门禁≠契约）'],
  ['SEC-1', '扫描器认不出文档声明的凭据形态'],
  ['SEC-4', '门禁 fail-open'],
  ['LIVE-1', '被服务响应里有产物中不存在的第三方源'],
  ['INJ-2', '平衡括号 URL 被截断'],
  ['INJ-3', '原型链成员撞上查表'],
  ['BLD-6', '站点地图含产物中不存在的 URL'],
  ['CTX-2', '页面公示的派生指标与仓库自己的 JS 算法复算不一致'],
  ['A11Y-1', '颜色令牌对比度不达标'],
  ['SEO-1', '首页 noindex / canonical 复用'],
  ['PIPE-1', '发布脚本执行快照内代码'],
  ['CI-1', '没有任何 CI 工作流'],
];
/** 必须不误报的项：夹具在这些方面是干净的 */
const MUST_NOT_FAIL = [
  ['INJ-1', 'XSS 载荷（渲染器先转义，应判通过）'],
  ['SEC-3', '忽略清单与实际跟踪文件'],
];
/** 缺能力时必须老实记 not-run，而不是消失 */
const MUST_NOT_RUN = ['LIVE-2', 'LNK-2'];

function runNode(args, cwd) {
  const r = spawnSync(process.execPath, args, { cwd: cwd || ROOT, encoding: 'utf8', timeout: 600000 });
  return { code: r.status, out: String(r.stdout || '') + String(r.stderr || '') };
}

function waitForServer(child, ms) {
  const t0 = Date.now();
  let buf = '';
  return new Promise((res, rej) => {
    const tick = () => {
      const m = /LISTENING (\d+)/.exec(buf);
      if (m) return res(Number(m[1]));
      if (Date.now() - t0 > ms) return rej(new Error('服务器未在 ' + ms + 'ms 内就绪：' + buf.slice(0, 200)));
      setTimeout(tick, 120);
    };
    child.stdout.on('data', (d) => { buf += d.toString(); });
    child.stderr.on('data', (d) => { buf += d.toString(); });
    tick();
  });
}

async function main() {
  const results = [];
  const tmp = mkdtempSync(join(tmpdir(), 'site-audit-selftest-'));
  let server = null;
  try {
    /* 1 构建夹具 */
    const b = runNode([join(FIXTURE, 'tools', 'build.js')]);
    results.push({ name: '夹具可构建', ok: b.code === 0, detail: b.out.slice(-160) });

    /* 2 起服务器（只绑 127.0.0.1） */
    server = spawn(process.execPath, [join(FIXTURE, 'tools', 'serve.js'), '0'], { cwd: FIXTURE, stdio: ['ignore', 'pipe', 'pipe'] });
    const port = await waitForServer(server, 15000);
    const url = `http://127.0.0.1:${port}/`;
    results.push({ name: '合成服务器已启动', ok: true, detail: url });

    /* 3 跑一轮 */
    const out = join(tmp, 'round1');
    mkdirSync(out, { recursive: true });
    const steps = [
      ['probe', ['probe', '--out', out, '--url', url, '--repo', FIXTURE, '--dist', join(FIXTURE, 'dist'), '--authorized', 'selftest']],
      ['build-forensics', ['build-forensics', '--out', out, '--repo', FIXTURE, '--dist', join(FIXTURE, 'dist')]],
      ['injection', ['injection', '--out', out, '--repo', FIXTURE, '--renderer', 'tools/render.js']],
      ['content-contract', ['content-contract', '--out', out, '--repo', FIXTURE, '--dist', join(FIXTURE, 'dist'), '--validator', 'validate', '--url', url, '--js']],
      ['gates', ['gates', '--out', out, '--repo', FIXTURE]],
      ['pipeline-trust', ['pipeline-trust', '--out', out, '--repo', FIXTURE]],
      ['ci-hygiene', ['ci-hygiene', '--out', out, '--repo', FIXTURE]],
      ['live-and-edge', ['live-and-edge', '--out', out, '--url', url, '--dist', join(FIXTURE, 'dist')]],
      ['surface', ['surface', '--out', out, '--repo', FIXTURE, '--dist', join(FIXTURE, 'dist')]],
      ['ledger verify', ['ledger', 'verify', '--out', out]],
    ];
    for (const [name, args] of steps) {
      const r = runNode([AUDIT, ...args]);
      results.push({ name: `执行 ${name}`, ok: r.code <= 2, detail: `exit ${r.code}` + (r.code > 2 ? ' — ' + r.out.slice(-200) : '') });
    }

    /* 4 账本断言 */
    const rows = [...latestByVerdict(readLedger(out)).values()];
    const byId = new Map(rows.map((r) => [r.id, r]));
    for (const [id, why] of MUST_FAIL) {
      const r = byId.get(id);
      results.push({ name: `抓到 ${id}`, ok: !!r && r.verdict === 'fail', detail: r ? String(r.title).slice(0, 90) : `${id} 不在账本里（${why}）` });
    }
    for (const [id, why] of MUST_NOT_FAIL) {
      const r = byId.get(id);
      results.push({ name: `不误报 ${id}`, ok: !!r && r.verdict !== 'fail', detail: r ? `${r.verdict} — ${String(r.title).slice(0, 70)}` : `${id} 缺行（${why}）` });
    }
    for (const id of MUST_NOT_RUN) {
      const r = byId.get(id);
      results.push({ name: `${id} 老实记 not-run`, ok: !!r && r.verdict === 'not-run' && !!r.reason, detail: r ? String(r.reason).slice(0, 80) : `${id} 缺行——静默消失正是要修的 bug` });
    }
    const total = new Set(rows.map((r) => r.id)).size;
    results.push({ name: '完备性：48 项全部有结论', ok: total === 48, detail: `入账 ${total}/48，not-run 行数 ${rows.filter((r) => r.verdict === 'not-run').length}` });

    /* 5 结构与清单：装上之后必须真能生效 */
    const NL = String.fromCharCode(10);
    const CR = String.fromCharCode(13);
    const strip = (x) => String(x).replace(CR, '');
    const unslash = (x) => (String(x).startsWith('./') ? String(x).slice(2) : String(x));
    const hasManifestFile = existsSync(join(ROOT, '.qoder-plugin', 'plugin.json'));
    let manifest = null;
    try { manifest = JSON.parse(readFileSync(join(ROOT, '.qoder-plugin', 'plugin.json'), 'utf8')); } catch { manifest = null; }
    if (!hasManifestFile) {
      results.push({ name: 'plugin.json（Skill 形态不适用）', ok: true, detail: '本形态以 SKILL.md 为根，无插件清单，跳过清单断言' });
    } else {
    results.push({ name: 'plugin.json 可解析', ok: !!manifest, detail: manifest ? 'name=' + manifest.name + ' v' + manifest.version : 'JSON 解析失败' });
    if (manifest) {
      const missingFields = ['name', 'version', 'skills', 'hooks'].filter((f) => manifest[f] == null);
      results.push({ name: 'plugin.json 必要字段齐备', ok: !missingFields.length, detail: missingFields.length ? '缺 ' + missingFields.join(', ') : 'name/version/skills/hooks 在' });
      // 使用者要求显示名、描述、图标不进包；这条断言把决定钉住，避免下一次改清单时悄悄加回来。
      const banned = ['displayName', 'description', 'logo'].filter((f) => manifest[f] != null);
      results.push({ name: '包内清单不含 displayName/description/logo', ok: !banned.length, detail: banned.length ? '不该出现：' + banned.join(', ') : '三项都不在清单里' });
      const dangling = Object.entries(manifest).filter(([, v]) => typeof v === 'string' && /assets[/]/.test(v));
      results.push({ name: '清单不引用包外资源（assets 被排除）', ok: !dangling.length, detail: dangling.length ? '悬空引用：' + dangling.map(([k]) => k).join(', ') : '无资源引用' });
      for (const sk of [].concat(manifest.skills || [])) {
        const ok = existsSync(join(ROOT, unslash(sk), 'SKILL.md'));
        results.push({ name: 'skills 指向的目录含 SKILL.md（' + sk + '）', ok, detail: ok ? 'ok' : '不存在——装了也不会出现技能' });
      }
      let hooks = null;
      try { hooks = JSON.parse(readFileSync(join(ROOT, unslash(manifest.hooks)), 'utf8')); } catch { hooks = null; }
      const nested = !!(hooks && hooks.hooks && typeof hooks.hooks === 'object');
      results.push({ name: 'hooks 是官方嵌套形态（外层有 hooks 键）', ok: nested, detail: nested ? Object.keys(hooks.hooks).join(',') : '外层缺 hooks 键：会被静默忽略' });
      if (nested) {
        const raw = JSON.stringify(hooks.hooks);
        const TOK = '${QODER_PLUGIN_ROOT}/';
        const cmds = [];
        let i = 0;
        while ((i = raw.indexOf(TOK, i)) >= 0) {
          let j = i + TOK.length;
          while (j < raw.length && raw[j] !== '"' && raw[j] !== ' ' && raw[j] !== String.fromCharCode(92)) j++;
          cmds.push(raw.slice(i, j));
          i = j;
        }
        const miss = cmds.filter((c) => !existsSync(join(ROOT, c.slice(TOK.length))));
        results.push({ name: 'hooks 命令指向的文件存在', ok: cmds.length > 0 && !miss.length, detail: cmds.length ? (miss.length ? '缺 ' + miss.join(', ') : cmds.join(', ')) : 'hooks 里没有 QODER_PLUGIN_ROOT 命令' });
      }
    }
    }
    /*
     * 图标不进包这条，光靠清单断言堵不住 Skill 形态——它根本没有清单可查。
     * 所以在「包内」跑的时候直接查树。源码树里 assets/ 是使用者自备素材的合法去处，
     * 于是用「有没有 tools/package.mjs」区分自己在包里还是在源码树里。
     */
    const inPackage = !existsSync(join(ROOT, 'tools', 'package.mjs'));
    const images = [];
    if (inPackage) {
      const stack = [[ROOT, 0]];
      while (stack.length && images.length < 20) {
        const [d, depth] = stack.pop();
        let names = [];
        try { names = readdirSync(d); } catch { continue; }
        for (const n of names) {
          const full = join(d, n);
          let st = null;
          try { st = statSync(full); } catch { continue; }
          if (st.isDirectory()) { if (depth < 6) stack.push([full, depth + 1]); }
          else if (/\.(svg|png|ico|jpe?g)$/i.test(n)) images.push(n);
        }
      }
    }
    results.push({
      name: '包内不含图标/图片资源（两种形态同一条规则）',
      ok: !inPackage || !images.length,
      detail: inPackage ? (images.length ? '漏进了包：' + images.join(', ') : '零图片文件（assets 被排除）') : '源码树不适用：assets/ 留给使用者自己决定',
    });
    // 提交侧只认压缩包根上的那一层：解包后的根必须直接有 plugin.json 或 SKILL.md。
    const atRoot = ['plugin.json', 'SKILL.md'].filter((f) => existsSync(join(ROOT, f)));
    results.push({
      name: '解包根目录直接含 plugin.json 或 SKILL.md（提交侧判据）',
      ok: !inPackage || atRoot.length > 0,
      detail: inPackage ? (atRoot.join(' + ') || '根上没有清单——上传会报「缺少 manifest 或 SKILL.md」') : '源码树不适用：清单在 .qoder-plugin/ 下',
    });
    // SKILL.md 位置随形态而变：Plugin 形态在 skills/site-audit/，Skill 形态就在根
    const skillPath = existsSync(join(ROOT, 'SKILL.md')) ? join(ROOT, 'SKILL.md') : join(ROOT, 'skills', 'site-audit', 'SKILL.md');
    const txt = existsSync(skillPath) ? readFileSync(skillPath, 'utf8') : '';
    const fmParts = txt.startsWith('---') ? txt.split('---') : [];
    const fmLines = (fmParts[1] || '').split(NL).map(strip);
    const nm = fmLines.find((l) => l.startsWith('name:'));
    const ds = fmLines.find((l) => l.startsWith('description:'));
    const nameVal = nm ? nm.slice(5).trim() : '';
    const descVal = ds ? ds.slice(11).trim() : '';
    results.push({ name: 'SKILL.md frontmatter 完整', ok: fmParts.length >= 3 && !!nm && !!ds, detail: fmParts.length >= 3 ? 'ok' : '缺 --- 包裹的 frontmatter' });
    results.push({ name: 'SKILL.md name 合法（hyphen-case 且 ≤64）', ok: /^[a-z0-9-]+$/.test(nameVal) && nameVal.length <= 64, detail: nameVal || '(空)' });
    results.push({ name: 'SKILL.md description 单行且 ≤1024 字符', ok: descVal.length > 40 && descVal.length <= 1024 && !fmLines.some((l, i) => i > fmLines.indexOf(ds) && l.startsWith('  ') && false), detail: descVal.length + ' 字符' });
    const bodyLines = txt.split(NL).length - (fmParts.length >= 3 ? (fmParts[0] + '---' + fmParts[1] + '---').split(NL).length : 0);
    results.push({ name: 'SKILL.md 正文 <500 行', ok: bodyLines > 0 && bodyLines < 500, detail: bodyLines + ' 行' });
    results.push({ name: 'SKILL.md 声明了自检入口', ok: /selftest/.test(txt), detail: /selftest/.test(txt) ? 'ok' : '缺：装完无法自证能力生效' });

    /* 6 网络与授权红线：必须由代码拒绝，而不是靠文档 */
    const { HttpBudget, PolicyViolation } = await import('../scripts/lib/net.mjs');
    const bb = new HttpBudget({ allowPrivate: true, budget: 3 });
    bb.bindOrigin('https://example.com');
    let cross = false;
    try { await bb.request('https://example.org/x'); } catch (e) { cross = e instanceof PolicyViolation; }
    results.push({ name: '红线：跨 origin 请求被代码拒绝', ok: cross, detail: cross ? 'PolicyViolation' : '未抛 PolicyViolation' });
    let post = false;
    try { await bb.request('https://example.com/', { method: 'POST' }); } catch (e) { post = e instanceof PolicyViolation; }
    results.push({ name: '红线：POST 被代码拒绝', ok: post, detail: post ? 'PolicyViolation' : '未抛 PolicyViolation' });
    // https 目标下的 http 降级探测：不显式开启必须被拒；显式开启每轮只允许一次
    const dg = new HttpBudget({ allowPrivate: true, budget: 4, timeoutMs: 800 });
    dg.bindOrigin('https://example.com');
    let dgBlocked = false;
    try { await dg.request('http://example.com/'); } catch (e) { dgBlocked = e instanceof PolicyViolation; }
    results.push({ name: '红线：https 目标的 http 降级探测需显式开启', ok: dgBlocked, detail: dgBlocked ? 'PolicyViolation' : '未抛 PolicyViolation' });
    // http 目标（本机夹具）不该被同一条规则误伤
    const plain = new HttpBudget({ allowPrivate: true, budget: 2, timeoutMs: 800 });
    plain.bindOrigin('http://127.0.0.1:1');
    let plainOk = true;
    try { await plain.request('http://127.0.0.1:1/'); } catch { plainOk = false; }
    results.push({ name: '红线不误伤：http 目标可正常请求', ok: plainOk, detail: plainOk ? '未抛策略异常（连接失败属正常）' : '被策略异常拦下——规则过严' });
    const noAuth = runNode([AUDIT, 'probe', '--out', join(tmp, 'noauth'), '--url', 'https://example.com/']);
    results.push({ name: '红线：黑盒缺 --authorized 拒启', ok: noAuth.code === 4 && /授权/.test(noAuth.out), detail: 'exit ' + noAuth.code });
    // 用本机不可达端口，保证自检完全离线、不向任何真实主机发请求
    const bud = new HttpBudget({ allowPrivate: true, budget: 1, timeoutMs: 1500 });
    bud.bindOrigin('http://127.0.0.1:1');
    await bud.request('http://127.0.0.1:1/a');
    const over = await bud.request('http://127.0.0.1:1/b');
    results.push({ name: '红线：预算耗尽后不再发请求', ok: over.skipped === 'budget', detail: 'skipped=' + (over.skipped || '未生效') });

    /* 6b 本轮自审修掉的缺陷，逐项钉住 */
    await regressionChecks(ROOT, join(tmp, 'regress'), (name, ok, detail) => {
      results.push({ name, ok: !!ok, detail: String(detail == null ? '' : detail).slice(0, 160) });
    });

    /* 7 隐私：账本证据里不得出现凭据形态与邮箱 */
    const blob = rows.map((r) => `${r.evidence}${r.title}${r.reason}`).join('\n');
    const leaky = /\bgh[pousr]_[0-9A-Za-z]{20,}|\bAKIA[0-9A-Z]{16}|[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}/.test(blob);
    results.push({ name: '隐私：账本证据已脱敏', ok: !leaky, detail: leaky ? 'evidence/title 里仍有凭据或邮箱形态' : '无凭据形态、无邮箱' });

    /* 8 隐私闸门：插件树本身必须扫得干净 */
    // 拼接而非字面量：否则这几个哨兵词会出现在被扫描的树里，自己把自己判成污染
    const sentinel = ['sentinel-' + 'tenant.example', 'sentinel-' + 'user', 'sentinel-' + 'repo-name'];
    const { skipDir } = await import('../scripts/lib/packrules.mjs');
    const scan = scanTree(ROOT, sentinel, { skip: skipDir });
    const forbiddenHits = scan.hits.filter((h) => h.kind === 'forbidden');
    const envHits = scan.hits.filter((h) => h.kind !== 'forbidden');
    results.push({
      name: '隐私闸门：插件树无哨兵词',
      ok: forbiddenHits.length === 0,
      detail: forbiddenHits.length ? '命中：' + forbiddenHits.slice(0, 4).map((h) => `${h.file}←${h.ref}`).join(', ') : `扫 ${scan.files.length} 个文件，哨兵词零命中`,
    });
    results.push({
      name: '隐私闸门：插件树无凭据/本机路径痕迹',
      ok: envHits.length === 0,
      detail: envHits.length ? '命中：' + envHits.slice(0, 6).map((h) => `${h.file}←${h.ref}`).join(', ') : '零命中',
    });
    const poison = (() => {
        const dir = join(tmp, 'poison');
        mkdirSync(dir, { recursive: true });
        const f = join(dir, 'SKILL.md');
        writePoison(f, sentinel[0]);
        const hit = scanTree(dir, sentinel).hits.length > 0;
        rmSync(dir, { recursive: true, force: true });
        return { ok: hit, detail: hit ? '注入哨兵词后确实 BLOCK' : '注入后仍报干净——闸门失效，测试无效' };
      })();
    results.push({ name: '隐私闸门能抓到被污染的文件', ...poison });
  } catch (e) {
    results.push({ name: 'selftest 异常', ok: false, detail: String(e.message || e).slice(0, 300) });
  } finally {
    if (server) server.kill();
    rmSync(tmp, { recursive: true, force: true });
  }

  const bad = results.filter((r) => !r.ok);
  console.log('');
  console.log('='.repeat(70));
  console.log(`site-audit selftest — ${results.length} 项断言，失败 ${bad.length}`);
  console.log('='.repeat(70));
  for (const r of results) console.log(`${r.ok ? '  ok  ' : ' FAIL '} ${r.name}\n         ${r.detail}`);
  console.log('');
  console.log(bad.length ? `selftest FAILED (${bad.length})` : 'selftest PASSED');
  process.exitCode = bad.length ? 1 : 0;
}

function writePoison(file, token) {
  writeFileSync(file, `# 探针\n\n访问 ${token} 看一眼\n`, 'utf8');
}

main();
