#!/usr/bin/env node
// 只发现宿主已有工具，不安装或修改项目依赖。@author xiuyu.yi
import fs from 'node:fs/promises';
import path from 'node:path';
import os from 'node:os';
import { execFile } from 'node:child_process';
import { promisify } from 'node:util';
import { fileURLToPath } from 'node:url';
const exec = promisify(execFile);
// uxarts-agent resources/sandbox: e2b-template.ts and both Dockerfiles.
export const baseline = '10.33.0';
async function exists(file) { try { await fs.access(file); return true; } catch { return false; } }
export async function resolvePnpm({ project, env = process.env, nodePath = process.execPath, candidates } = {}) {
  const root = await fs.realpath(project);
  const pkg = JSON.parse(await fs.readFile(path.join(root, 'package.json'), 'utf8'));
  const declaration = pkg.packageManager || (pkg.devEngines?.packageManager?.name ?
    `${pkg.devEngines.packageManager.name}@${pkg.devEngines.packageManager.version || ''}` : '');
  if ((declaration && !declaration.startsWith('pnpm@')) || (!declaration && !await exists(path.join(root, 'pnpm-lock.yaml')))) return { status: 'NOT_APPLICABLE', declaration, project: root };
  const exact = declaration.match(/^pnpm@(\d+\.\d+\.\d+)(?:\+sha\d+\.[a-fA-F0-9]+)?$/)?.[1];
  if (declaration && !exact) return { status: 'PROJECT_VERSION_REQUIRED', declaration, project: root };
  const required = exact || baseline;
  const environment = { COREPACK_ENABLE_NETWORK: '0', COREPACK_ENABLE_AUTO_PIN: '0', COREPACK_ENABLE_PROJECT_SPEC: '0',
    npm_config_manage_package_manager_versions: 'false', NPM_CONFIG_MANAGE_PACKAGE_MANAGER_VERSIONS: 'false' };
  const windows = process.platform === 'win32';
  const searchPath = env.PATH ?? Object.entries(env).find(([key]) => key.toUpperCase() === 'PATH')?.[1] ?? '';
  const clean = Object.fromEntries(Object.entries(env).filter(([key]) => key.toUpperCase() !== 'PATH'));
  Object.assign(clean, environment, { PATH: [path.dirname(nodePath), searchPath].join(path.delimiter) });
  if (!candidates) {
    const home = env.HOME || env.USERPROFILE || os.homedir();
    const dirs = [path.dirname(nodePath), ...searchPath.split(path.delimiter), env.PNPM_HOME,
      ...(windows ? [env.APPDATA, env.LOCALAPPDATA && path.join(env.LOCALAPPDATA, 'pnpm')] : []),
      path.join(home, 'Library/pnpm'), path.join(home, '.local/share/pnpm'), path.join(home, '.local/bin'), '/opt/homebrew/bin', '/usr/local/bin'];
    const nvm = path.join(env.NVM_DIR || path.join(home, '.nvm'), 'versions/node');
    for (const entry of await fs.readdir(nvm, { withFileTypes: true }).catch(() => [])) if (entry.isDirectory()) dirs.push(path.join(nvm, entry.name, 'bin'));
    candidates = [...new Set(dirs.filter(d => d && path.isAbsolute(d) && !d.split(path.sep).includes('node_modules')))].flatMap(d => (windows ? ['pnpm.cmd', 'pnpm.exe', 'pnpm'] : ['pnpm']).map(file => path.join(d, file)));
    // Corepack shims may now select another major; reuse already cached releases directly.
    const cache = env.COREPACK_HOME || (windows && env.LOCALAPPDATA ? path.join(env.LOCALAPPDATA, 'node', 'corepack') : path.join(env.XDG_CACHE_HOME || path.join(home, '.cache'), 'node/corepack'));
    const pnpmCache = path.join(cache, 'v1/pnpm');
    const cached = (await fs.readdir(pnpmCache, { withFileTypes: true }).catch(() => []))
      .filter(entry => entry.isDirectory() && /^\d+\.\d+\.\d+$/.test(entry.name))
      .sort((a, b) => b.name.localeCompare(a.name, undefined, { numeric: true }));
    for (const entry of cached) candidates.push(path.join(pnpmCache, entry.name, 'bin/pnpm.cjs'));

  }
  const seen = new Set();
  for (const candidate of candidates) {
    let real = await fs.realpath(candidate).catch(() => null);
    if (real && /\.cmd$/i.test(real)) {
      // 不将批处理文件交给 execFile；读取已知包的 bin 声明定位真实 JS。
      const directory = path.dirname(real);
      real = null;
      for (const name of ['pnpm', 'corepack']) {
        try {
          const base = path.join(directory, 'node_modules', name);
          const metadata = JSON.parse(await fs.readFile(path.join(base, 'package.json'), 'utf8'));
          const bin = typeof metadata.bin === 'string' ? metadata.bin : metadata.bin?.pnpm;
          if (metadata.name !== name || typeof bin !== 'string' || path.isAbsolute(bin)) continue;
          const entry = path.resolve(base, bin);
          if (!entry.toLowerCase().startsWith(path.resolve(base).toLowerCase() + path.sep)) continue;
          await fs.access(entry); real = entry; break;
        } catch {}
      }
    }
    if (!real || seen.has(real)) continue;
    seen.add(real);
    const js = /\.(?:c?js|mjs)$/.test(real);
    const executable = js ? nodePath : real;
    const prefix = js ? [real] : [];
    const run = async args => (await exec(executable, [...prefix, ...args], { env: clean, cwd: root, timeout: 8000, maxBuffer: 131072, windowsHide: true })).stdout.trim();
    try {
      const version = await run(['--version']);
      if (!/^\d+\.\d+\.\d+$/.test(version)) continue;
      const [major, minor] = version.split('.').map(Number);
      if (exact ? version !== exact : major !== 10 || minor < 33) continue;
      const storePath = await run(['store', 'path']);
      if (!path.isAbsolute(storePath)) continue;
      return { status: 'READY', project: root, required, version, nodePath, command: [executable, ...prefix], storePath, environment };
    } catch { /* A missing cached Corepack version is not a reason to fetch latest. */ }
  }
  return { status: 'PNPM_REQUIRED', project: root, required, declaration,
    message: '未找到可复用版本；由宿主按 required 准备 pnpm 后重新检查，不安装 latest。' };
}
if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  try {
    if (process.argv.length !== 4 || process.argv[2] !== '--project') throw Error('Invalid arguments');
    console.log(JSON.stringify(await resolvePnpm({ project: process.argv[3] }), null, 2));
  } catch (error) {
    console.log(JSON.stringify({ status: 'FAILED', code: error.code || 'PNPM_DISCOVERY_FAILED' }));
    process.exitCode = 1;
  }
}
