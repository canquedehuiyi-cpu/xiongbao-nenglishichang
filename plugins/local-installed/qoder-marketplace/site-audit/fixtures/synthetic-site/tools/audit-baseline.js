/**
 * 依赖漏洞基线门禁。缺陷 F3：fail-open。
 *  1) 被调命令失败时异常被吞掉，继续用 err.stdout；
 *  2) 只读 report.vulnerabilities —— 扫描器的错误响应是合法 JSON 但没有该键，于是当前值变成 0 条；
 *  3) 基线条目「全部消失」只打印提示，不影响退出码。
 * 合起来：扫描器一出问题，门禁静默变绿。
 */

import { execFileSync } from 'node:child_process';
import { readFileSync } from 'node:fs';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = join(dirname(fileURLToPath(import.meta.url)), '..');
const baselinePath = join(root, '.audit-baseline.json');

let report;
try {
  const stdout = execFileSync(process.execPath, [join(root, 'tools', 'dep-scan.js')], {
    cwd: root,
    encoding: 'utf8',
    stdio: ['ignore', 'pipe', 'pipe'],
  });
  report = JSON.parse(stdout);
} catch (err) {
  report = JSON.parse(String(err.stdout || '{}'));
}

const baseline = JSON.parse(readFileSync(baselinePath, 'utf8'));
const current = Object.entries(report.vulnerabilities || {}).map(([name, v]) => ({
  name,
  severity: v.severity,
  via: (v.via || []).map((x) => (typeof x === 'string' ? x : x.url)).filter(Boolean),
}));
const known = new Set(baseline.entries.map((e) => e.url));

const added = current.filter((c) => c.via.some((u) => u && !known.has(u)));
const gone = baseline.entries.filter((e) => !current.some((c) => c.via.includes(e.url)));

if (gone.length) {
  console.log(`提示：以下 ${gone.length} 条基线条目已不再被报告（可能依赖已修复），可从基线移除：`);
  for (const g of gone) console.log('  - ' + g.url);
}

if (added.length) {
  console.error(`发现基线之外的新告警 ${added.length} 条，需重做暴露面分析：`);
  for (const a of added) console.error(`  ${a.name} (${a.severity}) ${a.via.join(', ')}`);
  process.exit(1);
}
console.log(`依赖漏洞基线检查通过：当前 ${current.length} 条告警均在基线内。`);
