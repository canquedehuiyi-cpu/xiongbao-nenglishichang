/**
 * 凭据扫描器。缺陷 F2：唯一的 GitHub 类规则只匹配旧版 `tk_live_<32>`，
 * 而本仓库 README 让人去创建的是新版 `tkv2_<22>_<59>`。
 * 缺陷 F2b：命中时把匹配片段的前 12 字符打到 stdout——日志二次泄露。
 *
 * 用法：node tools/scan-secrets.js [目录] [--emit-snippet]
 */

import { readFileSync, readdirSync, statSync } from 'node:fs';
import { join, dirname, relative } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = join(dirname(fileURLToPath(import.meta.url)), '..');
const target = process.argv[2] && !process.argv[2].startsWith('--') ? process.argv[2] : root;
const emitSnippet = process.argv.includes('--emit-snippet');

const PATTERNS = [
  { name: 'Service token', re: /\btk_live_[0-9A-Za-z]{32}\b/g },
  { name: 'AWS Access Key', re: /\bAKIA[0-9A-Z]{16}\b/g },
  { name: 'Private Key', re: /-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----/g },
  {
    name: 'Generic assignment',
    re: /(?:api[_-]?key|secret|token|password)\s*[:=]\s*['"]?[A-Za-z0-9_-]{16,}/gi,
    contentExempt: true,
  },
];

const EXCLUDE = new Set(['node_modules', '.git', 'dist']);
const SKIP_CONTENT = ['src' + '/' + 'posts'];

function walk(dir, base, out = []) {
  for (const name of readdirSync(dir)) {
    if (EXCLUDE.has(name)) continue;
    const full = join(dir, name);
    const st = statSync(full);
    if (st.isDirectory()) walk(full, base, out);
    else out.push(relative(base, full).split('\\').join('/'));
  }
  return out;
}

const hits = [];
for (const rel of walk(target, root)) {
  const text = readFileSync(join(root, rel), 'utf8');
  const inContent = SKIP_CONTENT.some((p) => rel.startsWith(p));
  for (const { name, re, contentExempt } of PATTERNS) {
    if (contentExempt && inContent) continue;
    re.lastIndex = 0;
    for (const m of text.matchAll(re)) {
      const line = text.slice(0, m.index).split('\n').length;
      hits.push({ rel, line, name, snippet: emitSnippet ? m[0].slice(0, 12) : '' });
      break;
    }
  }
}

if (hits.length) {
  console.error(`凭据扫描命中 ${hits.length} 处：`);
  for (const h of hits) {
    console.error(`  ${h.rel}:${h.line} — ${h.name}${h.snippet ? ' [' + h.snippet + '…]' : ''}`);
  }
  process.exit(1);
}
console.log('凭据扫描通过：未命中任何模式。');
