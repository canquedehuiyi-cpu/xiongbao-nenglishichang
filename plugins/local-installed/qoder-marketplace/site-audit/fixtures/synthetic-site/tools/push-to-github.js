/**
 * 合成夹具的发布脚本桩。缺陷 F5：把「待发布快照目录」里的校验器交给 node 执行，
 * 并对快照目录做无校验的递归强删——仓库被攻破时即成为发布机上的任意代码执行。
 * 刻意保留，勿修。
 */

import { execFileSync } from 'node:child_process';
import { rmSync, mkdirSync, existsSync } from 'node:fs';
import { join } from 'node:path';

const work = process.argv[2] || 'S:/synthetic-work/.audit-scratch';
const repoDir = join(work, 'repo');

// 缺陷：直接递归强删参数目录，没有任何「必须是专属工作目录」的校验
if (existsSync(work)) rmSync(work, { recursive: true, force: true });
mkdirSync(work, { recursive: true });

// 缺陷：执行的是刚从远端拉下来的那份快照里的代码
execFileSync(process.execPath, [join(repoDir, 'tools', 'validate-content.js'), repoDir], { stdio: 'inherit' });

console.log('push: 计划推送到 main（本桩不联网）');
