/**
 * 依赖扫描器桩。
 *  - 没有 package-lock.json（= 从未 install 过）时，向 stdout 打印一段**合法 JSON 的错误响应**并 exit 1。
 *    这正是 audit-baseline.js 会误读成「0 条告警」的东西。
 *  - 有 lockfile 时，从 .audit-data.json 读合成告警数据（真实项目里这一步是 npm audit）。
 */

import { existsSync, readFileSync } from 'node:fs';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = join(dirname(fileURLToPath(import.meta.url)), '..');

if (!existsSync(join(root, 'package-lock.json'))) {
  process.stdout.write(JSON.stringify({ error: { code: 'ENOENT', message: '缺少 package-lock.json，无法确定已安装的依赖树' } }) + '\n');
  process.exit(1);
}

const advisories = JSON.parse(readFileSync(join(root, '.audit-data.json'), 'utf8'));
const vulnerabilities = {};
for (const a of advisories) {
  vulnerabilities[a.name] = vulnerabilities[a.name] || { severity: a.severity, via: [] };
  vulnerabilities[a.name].via.push(a.url);
  if (SEVERITY_RANK(a.severity) > SEVERITY_RANK(vulnerabilities[a.name].severity)) {
    vulnerabilities[a.name].severity = a.severity;
  }
}
process.stdout.write(JSON.stringify({ vulnerabilities }) + '\n');

function SEVERITY_RANK(s) {
  return { low: 1, moderate: 2, high: 3, critical: 4 }[String(s).toLowerCase()] || 0;
}
