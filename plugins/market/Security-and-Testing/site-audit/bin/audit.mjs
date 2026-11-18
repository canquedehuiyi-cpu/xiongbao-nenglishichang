#!/usr/bin/env node
/**
 * 唯一 argv 入口。`audit <子命令> ...` 转发到 scripts/<子命令>.mjs，
 * 并把宿主退出码原样透出——退出码是这套工具的承重契约，不能在中间层被吃掉。
 */

import { existsSync } from 'node:fs';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const here = dirname(fileURLToPath(import.meta.url));
const root = dirname(here);
const scriptsDir = join(root, 'scripts');

const ALIAS = {
  l: 'ledger',
  ls: 'ledger',
  live: 'live-and-edge',
  contracts: 'content-contract',
};

const DESCRIPTION = `site-audit — 静态站点独立审查（零依赖，只用 Node 内置模块）

用法: node bin/audit.mjs <子命令> [参数...]

  probe             探测能力矩阵 → <out>/capabilities.json
  build-forensics   构建产物取证（BLD-*）
  live-and-edge     线上响应与边缘行为（LIVE-*, HDR-*）
  injection         注入面：载荷只打本地渲染器（INJ-*）
  content-contract  内容契约与漂移（CTX-*, DOC-1/3）
  pipeline-trust    发布链路信任边界（PIPE-*）
  gates             凭据扫描与依赖门禁（SEC-*）
  ci-hygiene        CI 与测试覆盖（CI-*）
  surface           元数据/可访问性/链接（SEO-*, A11Y-*, LNK-*）
  ledger            完备性闸门与报告：verify | report | merge | checklist | outstanding
  selfcheck         出包前隐私闸门：--zip <path>
  selftest          端到端验收：拿 fixtures/synthetic-site 跑完整一轮并断言结果

退出码: 0 通过 · 1 有 P1/P2 发现 · 2 部分未跑 · 3 完全没跑 · 4 用法错误
未跑 ≠ 通过。`;

function main(argv) {
  let sub = argv[0];
  if (!sub || sub === '-h' || sub === '--help' || sub === 'help') {
    console.log(DESCRIPTION);
    return sub ? 0 : 4;
  }
  sub = ALIAS[sub] || sub;
  if (sub === 'checklist') {
    argv = ['ledger', 'checklist', ...argv.slice(2)];
    sub = 'ledger';
  }
  const target = [join(scriptsDir, `${sub}.mjs`), join(here, `${sub}.mjs`)].find((p) => existsSync(p));
  if (!target) {
    console.error(`未知子命令: ${sub}`);
    console.error(DESCRIPTION);
    return 4;
  }
  const r = spawnSync(process.execPath, [target, ...argv.slice(1)], { stdio: 'inherit' });
  if (r.error) {
    console.error(`无法执行 ${sub}: ${r.error.message}`);
    return 4;
  }
  if (r.signal) {
    console.error(`${sub} 被信号终止: ${r.signal}`);
    return 4;
  }
  return typeof r.status === 'number' ? r.status : 4;
}

process.exitCode = main(process.argv.slice(2));
