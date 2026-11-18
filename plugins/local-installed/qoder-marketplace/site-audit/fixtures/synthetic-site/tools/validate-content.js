/**
 * 内容校验器。它检查的是「来源行行尾有没有日期」，
 * 而 README 的契约是「多来源时每段各自带日期」——两者不等价，这就是缺陷 F1 的另一半：
 * 门禁绿，契约破。
 */

import { readFileSync, readdirSync } from 'node:fs';
import { join, dirname, basename } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = join(dirname(fileURLToPath(import.meta.url)), '..');
const src = join(root, 'src', 'posts');

const TAIL_DATE = /[（(][^（）()]*\d[^（）()]*[）)]\s*$/;
const ANY_URL = /\]\((https?:\/\/[^)\s]+)\)/g;

const errors = [];
const files = readdirSync(src).filter((f) => f.endsWith('.md')).sort();
for (const f of files) {
  const text = readFileSync(join(src, f), 'utf8');
  const lines = text.split(/\r?\n/);
  let current = null;
  let seenItem = false;
  lines.forEach((raw, i) => {
    const t = raw.trim();
    if (t.startsWith('### ')) {
      seenItem = true;
      current = { title: t.slice(4), line: i + 1 };
    } else if (/^来源[：:]/.test(t) && current) {
      const body = t.replace(/^来源[：:]/, '').trim();
      const links = [...body.matchAll(ANY_URL)];
      if (!links.length) {
        errors.push(`${f}:${i + 1} 来源行没有任何链接：${current.title}`);
      } else if (!TAIL_DATE.test(body)) {
        errors.push(`${f}:${i + 1} 来源行末尾缺日期标注：${current.title}`);
      }
      current.hasSource = true;
    } else if (t.startsWith('## ')) {
      current = null;
    }
  });
  if (!seenItem) errors.push(`${f} 没有任何条目`);
  for (const line of lines) {
    if (/"/.test(line)) errors.push(`${f} 出现 ASCII 直引号`);
  }
}

if (errors.length) {
  console.error(`内容校验失败：${errors.length} 处`);
  for (const e of errors) console.error('  - ' + e);
  process.exit(3);
}
console.log(`内容校验通过：${files.length} 篇全部合规。`);
