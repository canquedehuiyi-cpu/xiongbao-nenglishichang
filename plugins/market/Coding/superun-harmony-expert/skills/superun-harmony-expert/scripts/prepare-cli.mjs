#!/usr/bin/env node
// 跨系统运行准备，由 scripts/sync-runtime.mjs 生成到各专家，勿直接修改生成文件。@author xiuyu.yi
import { promises as fs, constants } from 'node:fs';
import path from 'node:path';
import os from 'node:os';
import { createHash } from 'node:crypto';
import { execFile } from 'node:child_process';
import { promisify } from 'node:util';
import { fileURLToPath } from 'node:url';
import { createRequire } from 'node:module';

const profile = {
  "cacheName": "superun-harmony-expert",
  "specs": {
    "superun-ai": {
      "package": "superun-ai-cli",
      "major": 22,
      "versionArgs": [
        "version"
      ],
      "help": [
        {
          "args": [
            "chat",
            "create"
          ],
          "options": [
            "--no-wait",
            "--input"
          ]
        },
        {
          "args": [
            "chat",
            "send"
          ],
          "options": [
            "--no-wait",
            "--input"
          ]
        },
        {
          "args": [
            "chat",
            "wait"
          ],
          "options": [
            "--message-id",
            "--timeout"
          ]
        },
        {
          "args": [
            "chat",
            "state"
          ],
          "options": [
            "--message-id"
          ]
        },
        {
          "args": [
            "chat",
            "interaction",
            "reply"
          ],
          "options": [
            "--input",
            "--no-wait"
          ]
        },
        {
          "args": [
            "chat",
            "style",
            "list"
          ],
          "options": []
        },
        {
          "args": [
            "chat",
            "style",
            "select"
          ],
          "options": [
            "--no-wait"
          ]
        },
        {
          "args": [
            "chat",
            "publish",
            "status"
          ],
          "options": [
            "--for-launch"
          ]
        },
        {
          "args": [
            "session",
            "list"
          ],
          "options": [
            "--scope",
            "--limit",
            "--keyword"
          ]
        },
        {
          "args": [
            "app",
            "consult",
            "start"
          ],
          "options": [
            "--platform",
            "--source-message-id",
            "--retry-failed"
          ]
        },
        {
          "args": [
            "app",
            "consult",
            "status"
          ],
          "options": [
            "--platform",
            "--wait",
            "--timeout"
          ]
        },
        {
          "args": [
            "app",
            "consult",
            "send"
          ],
          "options": [
            "--platform",
            "--input"
          ]
        },
        {
          "args": [
            "app",
            "plan",
            "get"
          ],
          "options": [
            "--platform"
          ]
        },
        {
          "args": [
            "app",
            "plan",
            "execute"
          ],
          "options": [
            "--platform",
            "--plan-fingerprint"
          ]
        },
        {
          "args": [
            "app",
            "plan",
            "wait"
          ],
          "options": [
            "--platform",
            "--timeout"
          ]
        },
        {
          "args": [
            "app",
            "config",
            "get"
          ],
          "options": [
            "--platform"
          ]
        },
        {
          "args": [
            "app",
            "config",
            "set"
          ],
          "options": [
            "--platform",
            "--input"
          ]
        },
        {
          "args": [
            "app",
            "prepare"
          ],
          "options": [
            "--platform",
            "--build-type"
          ]
        },
        {
          "args": [
            "app",
            "build"
          ],
          "options": [
            "--platform",
            "--build-type",
            "--version-bump",
            "--acknowledge-store-upload"
          ]
        },
        {
          "args": [
            "app",
            "wait"
          ],
          "options": [
            "--platform",
            "--timeout"
          ]
        },
        {
          "args": [
            "app",
            "install"
          ],
          "options": [
            "--platform"
          ]
        },
        {
          "args": [
            "app",
            "history",
            "list"
          ],
          "options": [
            "--platform",
            "--limit"
          ]
        },
        {
          "args": [
            "app",
            "history",
            "get"
          ],
          "options": [
            "--platform"
          ]
        },
        {
          "args": [
            "app",
            "filing",
            "get"
          ],
          "options": [
            "--platform"
          ]
        },
        {
          "args": [
            "auth",
            "status"
          ],
          "options": []
        },
        {
          "args": [
            "auth",
            "login"
          ],
          "options": []
        },
        {
          "args": [
            "chat",
            "publish",
            "prepare"
          ],
          "options": []
        },
        {
          "args": [
            "chat",
            "publish",
            "deploy"
          ],
          "options": [
            "--source-message-id",
            "--quote-id",
            "--acknowledge-cloud-fee",
            "--acknowledge-site-publication",
            "--for-launch"
          ]
        },
        {
          "args": [
            "chat",
            "publish",
            "start"
          ],
          "options": [
            "--for-launch",
            "--acknowledge-cloud-fee"
          ]
        },
        {
          "args": [
            "chat",
            "publish",
            "visibility"
          ],
          "options": [
            "--source-message-id"
          ]
        },
        {
          "args": [
            "app",
            "guidance"
          ],
          "options": [
            "--platform",
            "--build-type"
          ]
        },
        {
          "args": [
            "app",
            "account",
            "connect"
          ],
          "options": [
            "--platform",
            "--service-account-file"
          ]
        },
        {
          "args": [
            "app",
            "devices",
            "list"
          ],
          "options": [
            "--platform"
          ]
        },
        {
          "args": [
            "app",
            "devices",
            "register"
          ],
          "options": [
            "--platform",
            "--input"
          ]
        },
        {
          "args": [
            "app",
            "devices",
            "select"
          ],
          "options": [
            "--platform",
            "--input"
          ]
        },
        {
          "args": [
            "app",
            "upload",
            "status"
          ],
          "options": [
            "--platform"
          ]
        },
        {
          "args": [
            "app",
            "upload",
            "retry"
          ],
          "options": [
            "--platform"
          ]
        }
      ],
      "requiredCapabilities": [
        "app-publishing-flow-v1"
      ]
    }
  }
};
const execute = promisify(execFile);
const versionPattern = /^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:-([0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?(?:\+[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?$/;
const fail = code => Object.assign(new Error(code), { code });
const projectToolPath = p => /(?:^|[/\\])(?:node_modules|\.git)(?:[/\\]|$)/i.test(p);
export const environmentValue = (env, name) => env[name] ?? Object.entries(env).find(([key]) => key.toUpperCase() === name.toUpperCase())?.[1];
function versionParts(version) {
  const match = typeof version === 'string' && version.match(versionPattern);
  if (!match || match[4]?.split('.').some(part => /^0\d+$/.test(part))) throw fail('CLI_VERSION_UNREADABLE');
  return { core: match.slice(1, 4).map(Number), pre: match[4]?.split('.') ?? [] };
}
export function compareVersions(left, right) {
  const a = versionParts(left), b = versionParts(right);
  for (let i = 0; i < 3; i++) if (a.core[i] !== b.core[i]) return a.core[i] > b.core[i] ? 1 : -1;
  if (!a.pre.length || !b.pre.length) return a.pre.length ? -1 : b.pre.length ? 1 : 0;
  for (let i = 0; i < Math.max(a.pre.length, b.pre.length); i++) {
    const x = a.pre[i], y = b.pre[i];
    if (x === y) continue;
    if (x === undefined) return -1;
    if (y === undefined) return 1;
    const nx = /^\d+$/.test(x), ny = /^\d+$/.test(y);
    if (nx && ny) return Number(x) > Number(y) ? 1 : -1;
    if (nx !== ny) return nx ? -1 : 1;
    return x > y ? 1 : -1;
  }
  return 0;
}
export function readVersion(output) {
  const text = output.trim();
  let value;
  if (text.startsWith('{')) {
    let wire;
    try { wire = JSON.parse(text); } catch { throw fail('CLI_VERSION_UNREADABLE'); }
    if (wire.ok === false) throw fail('CLI_VERSION_UNREADABLE');
    value = wire.data?.version ?? wire.version;
  } else value = text.replace(/^v/, '');
  versionParts(value);
  return value;
}
async function runDefault(file, args, env, timeout = 30_000) {
  try { return (await execute(file, args, { env, cwd: os.homedir(), timeout, maxBuffer: 1024 * 1024, windowsHide: true })).stdout.trim(); }
  catch { throw fail('COMMAND_FAILED'); } // npm 原始输出可能含凭据，不向外透出。
}

export async function prepare({ mode = 'ensure', target = 'all', env = process.env, nodePath = process.execPath,
  platform = process.platform, run = runDefault, files = fs, resolve, npmScript, semver: suppliedSemver } = {}) {
  const specs = profile.specs;
  if (!['ensure','check','update'].includes(mode) || (target !== 'all' && !Object.hasOwn(specs, target))) throw fail('INVALID_ARGUMENT');
  const windows = platform === 'win32', paths = windows ? path.win32 : path.posix;
  const normalize = file => windows ? paths.resolve(file).toLowerCase() : paths.resolve(file);
  // Git Bash/Cygwin 的环境路径不能原样交给 Windows npm。
  const nativePath = value => {
    const match = windows && typeof value === 'string' && value.match(/^\/(?:cygdrive\/)?([a-z])(?:\/(.*))?$/i);
    return match ? paths.join(match[1].toUpperCase() + ':\\', match[2] ?? '') : value;
  };
  const clean = {};
  for (const key of ['HOME','USERPROFILE','APPDATA','LOCALAPPDATA','SystemRoot','WINDIR','COMSPEC','TMP','TEMP','TMPDIR','LANG','LC_ALL','HTTP_PROXY','HTTPS_PROXY','NO_PROXY','http_proxy','https_proxy','no_proxy','NODE_EXTRA_CA_CERTS','SSL_CERT_FILE','SSL_CERT_DIR','ELECTRON_RUN_AS_NODE']) {
    const value = windows ? environmentValue(env, key) : env[key];
    if (value) clean[key] = value;
  }
  // 独立专家的缓存策略在主入口实现，直接运行 mjs 与 Shell 启动器保持一致。
  const configuredPrefix = nativePath(environmentValue(env, 'npm_config_prefix'));
  const cache = nativePath(environmentValue(env, 'XDG_CACHE_HOME')) || paths.join(environmentValue(env, windows ? 'USERPROFILE' : 'HOME') || os.homedir(), '.cache');
  const prefixOverride = profile.cacheName ? paths.join(cache, 'superun-ai-cli', 'experts', profile.cacheName) : configuredPrefix;
  if (prefixOverride) clean.npm_config_prefix = clean.NPM_CONFIG_PREFIX = prefixOverride;
  const cacheOverride = nativePath(environmentValue(env, 'npm_config_cache'));
  if (cacheOverride) clean.npm_config_cache = cacheOverride;
  clean.PATH = [...(prefixOverride ? [windows ? prefixOverride : paths.join(prefixOverride, 'bin')] : []), paths.dirname(nodePath),
    ...(environmentValue(env, 'PATH') || '').split(paths.delimiter).filter(p => paths.isAbsolute(p) && !projectToolPath(p))].join(paths.delimiter);
  clean.npm_config_userconfig = platform === process.platform ? os.devNull : windows ? '\\\\.\\nul' : '/dev/null';
  clean.npm_config_globalconfig = paths.join(clean.npm_config_userconfig, 'superun-empty-npmrc');
  const nodeVersion = await run(nodePath, ['--version'], clean);
  if (!versionPattern.test(nodeVersion.replace(/^v/, ''))) throw fail('NODE_VERSION_UNREADABLE');
  const selected = target === 'all' ? Object.keys(specs) : [target];
  const results = [];
  async function windowsEntry(prefix, command) {
    try {
      const root = paths.join(prefix, 'node_modules', specs[command].package);
      const metadata = JSON.parse(await files.readFile(paths.join(root, 'package.json'), 'utf8'));
      const bin = typeof metadata.bin === 'string' ? metadata.bin : metadata.bin?.[command];
      if (metadata.name !== specs[command].package || typeof bin !== 'string' || paths.isAbsolute(bin)) throw fail('CUSTOM_CLI_BINDING');
      const entry = paths.resolve(root, bin);
      if (!normalize(entry).startsWith(normalize(root) + paths.sep)) throw fail('CUSTOM_CLI_BINDING');
      await files.access(entry, constants.R_OK);
      return entry;
    } catch { throw fail('CUSTOM_CLI_BINDING'); }
  }
  const resolveCommand = resolve ?? (async (command, environment) => {
    const directories = profile.cacheName ? [windows ? prefixOverride : paths.join(prefixOverride, 'bin')] : environment.PATH.split(paths.delimiter);
    for (const dir of directories) {
      if (!paths.isAbsolute(dir) || projectToolPath(dir)) continue;
      const file = paths.join(dir, command + (windows ? '.cmd' : ''));
      try { await files.access(file, constants.X_OK); } catch { continue; }
      return windows ? windowsEntry(dir, command) : file;
    }
    return null;
  });
  let npm;
  async function npmBinding() {
    if (npm) return npm;
    let script = npmScript;
    const candidates = [paths.dirname(nodePath), ...clean.PATH.split(paths.delimiter)].flatMap(dir =>
      [paths.join(dir, 'node_modules', 'npm', 'bin', 'npm-cli.js'), paths.join(dir, 'npm')]);
    for (const candidate of candidates) {
      if (script) break;
      const resolved = await files.realpath(candidate).catch(() => null);
      if (resolved && paths.basename(resolved) === 'npm-cli.js') script = resolved;
    }
    if (!script) throw fail('NPM_REQUIRED');
    const flags = ['--global', '--registry=https://registry.npmjs.org'];
    const prefix = prefixOverride || await run(nodePath, [script, 'prefix', ...flags], clean);
    if (!paths.isAbsolute(prefix) || /[\r\n]/.test(prefix) || projectToolPath(prefix)) throw fail('INVALID_GLOBAL_PREFIX');
    npm = { script, flags, prefix, bin: windows ? prefix : paths.join(prefix, 'bin') };
    return npm;
  }
  for (const command of selected) {
    const spec = specs[command];
    let executable = null, version = null, latestVersion = null, requiredNode = null;
    const runCli = (file, args) => run(windows || /\.(?:mjs|cjs|js)$/i.test(file) ? nodePath : file,
      windows || /\.(?:mjs|cjs|js)$/i.test(file) ? [file, ...args] : args, clean);
    const cliVersion = async file => readVersion(await runCli(file, spec.versionArgs));
    try {
      executable = await resolveCommand(command, clean);
      const binding = await npmBinding();
      let metadata;
      try { metadata = JSON.parse(await run(nodePath, [binding.script, 'view', spec.package + '@latest', 'name', 'version', 'dist.integrity', 'engines.node', '--json', ...binding.flags], clean)); }
      catch { throw fail('NPM_METADATA_QUERY_FAILED'); }
      if (metadata.name !== spec.package || typeof metadata.version !== 'string' || !versionPattern.test(metadata.version) || typeof metadata['dist.integrity'] !== 'string') throw fail('INVALID_PACKAGE_METADATA');
      versionParts(metadata.version);
      latestVersion = metadata.version;
      requiredNode = metadata['engines.node'] ?? metadata.engines?.node ?? `>=${spec.major ?? 22}`;
      let semver = suppliedSemver;
      try { semver ??= createRequire(binding.script)('semver'); } catch { throw fail('NPM_SEMVER_UNAVAILABLE'); }
      if (typeof requiredNode !== 'string' || !semver.validRange(requiredNode)) throw fail('INVALID_PACKAGE_METADATA');
      if (!semver.satisfies(nodeVersion, requiredNode)) throw fail('NODE_VERSION_UNSUPPORTED');
      if (executable) version = await cliVersion(executable);
      const ready = async action => {
        const required = spec.requiredCapabilities ?? [];
        if (required.length) {
          let wire;
          try { wire = JSON.parse(await runCli(executable, spec.versionArgs)); } catch { throw fail('CLI_CAPABILITY_MISSING'); }
          if (wire?.schemaVersion !== '1' || wire.ok !== true || wire.data?.version !== version || !Array.isArray(wire.data.capabilities)
              || required.some(capability => !wire.data.capabilities.includes(capability))) throw fail('CLI_CAPABILITY_MISSING');
        }
        for (const check of spec.help ?? []) {
          const valid = text => text.includes(`Usage: ${command} ${check.args.join(' ')}`) && (check.options ?? []).every(option => text.includes(option));
          let help;
          try { help = await runCli(executable, [...check.args, '--help']); } catch { throw fail('CLI_CAPABILITY_MISSING'); }
          if (!valid(help)) {
            try { help = await runCli(executable, [...check.args.slice(0, -1), 'help', check.args.at(-1)]); } catch { throw fail('CLI_CAPABILITY_MISSING'); }
            if (!valid(help)) throw fail('CLI_CAPABILITY_MISSING');
          }
        }
        return { command, package: spec.package, status: 'READY', path: executable, version, latestVersion, requiredNode, action,
          verifiedCapabilities: required, verifiedCommands: (spec.help ?? []).map(check => check.args.join(' ')) };
      };
      const current = () => executable && compareVersions(version, latestVersion) >= 0;
      if (current()) { results.push(await ready(compareVersions(version, latestVersion) === 0 ? 'current' : 'newer')); continue; }
      if (mode === 'check') { results.push({ command, package: spec.package, status: executable ? 'OUTDATED' : 'MISSING', path: executable, version, latestVersion, action: 'none' }); continue; }
      const expectedPath = () => windows ? windowsEntry(binding.bin, command) : paths.join(binding.bin, command);
      const selectedEnvironment = { ...clean, PATH: binding.bin };
      const packageRoot = paths.join(binding.prefix, ...(windows ? [] : ['lib']), 'node_modules', spec.package);
      const inSelectedPrefix = file => windows ? normalize(file).startsWith(normalize(packageRoot) + paths.sep)
        : normalize(file) === normalize(paths.join(binding.bin, command));
      // 宿主 npm 与 PATH 可属于不同安装。只更新宿主选定前缀，不覆盖另一套 CLI。
      if (executable && !inSelectedPrefix(executable)) {
        executable = await resolveCommand(command, selectedEnvironment);
        version = executable ? await cliVersion(executable) : null;
        if (current()) { results.push(await ready('reused')); continue; }
      }
      const checkOwnership = async () => {
        if (!executable) return;
        const root = paths.join(await files.realpath(binding.prefix), ...(windows ? [] : ['lib']), 'node_modules', spec.package);
        if (normalize(executable) !== normalize(await expectedPath()) || !normalize(await files.realpath(executable)).startsWith(normalize(root) + paths.sep)) throw fail('CUSTOM_CLI_BINDING');
      };
      await checkOwnership();
      // npm 选定的全局目录在首次安装时可能尚不存在，沿原前缀创建即可。
      await files.mkdir(binding.prefix, { recursive: true, mode: 0o700 }).catch(() => { throw fail('GLOBAL_PREFIX_NOT_WRITABLE'); });
      await files.access(binding.prefix, constants.W_OK).catch(() => { throw fail('GLOBAL_PREFIX_NOT_WRITABLE'); });
      const lockPath = paths.join(windows ? environmentValue(env, 'TEMP') || os.tmpdir() : os.tmpdir(), 'superun-kit-prepare-' + createHash('sha256').update(normalize(binding.prefix)).digest('hex').slice(0, 20));
      await files.mkdir(lockPath, { mode: 0o700 }).catch(() => { throw fail('PREPARATION_BUSY'); });
      try {
        executable = await resolveCommand(command, selectedEnvironment);
        version = executable ? await cliVersion(executable) : null;
        if (current()) { results.push(await ready('reused')); continue; }
        await checkOwnership();
        const before = executable;
        try { await run(nodePath, [binding.script, 'install', spec.package + '@' + latestVersion, '--ignore-scripts', '--no-audit', '--no-fund', ...binding.flags], clean, 120_000); }
        catch { throw fail('CLI_INSTALL_FAILED'); }
        executable = await resolveCommand(command, { ...clean, PATH: binding.bin + paths.delimiter + clean.PATH });
        if (!executable || normalize(executable) !== normalize(await expectedPath())) throw fail('CLI_NOT_FOUND_AFTER_INSTALL');
        version = await cliVersion(executable);
        if (version !== latestVersion) throw fail('CLI_VERSION_MISMATCH');
        results.push(await ready(before ? 'updated' : 'installed'));
      } finally { await files.rmdir(lockPath); }
    } catch (error) {
      const code = typeof error.code === 'string' && /^[A-Z_]+$/.test(error.code) ? error.code : 'PREPARATION_FAILED';
      results.push({ command, package: spec.package, status: 'FAILED', path: executable, version, latestVersion, requiredNode, code });
    }
  }
  return { schemaVersion: 1, ok: results.every(result => result.status === 'READY'), nodePath, nodeVersion, results };
}
export function hookOutput(result) {
  return { hookSpecificOutput: { hookEventName: 'SessionStart', additionalContext:
    'superun CLI 准备结果：' + JSON.stringify(result) + '\n仅沿 READY 回执的 nodePath 和 path 执行原任务；Windows 使用 nodePath 执行 JavaScript path。失败时保留原任务并处理真实缺口。环境准备不登录；登录沿 CLI 原流程完成。' } };
}
if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const args = process.argv.slice(2), hook = args.includes('--hook');
  let result;
  try {
    if (args.filter(arg => ['--ensure','--check','--update'].includes(arg)).length > 1 || args.some(arg => arg.startsWith('--') && !['--hook','--ensure','--check','--update'].includes(arg)) || args.filter(arg => !arg.startsWith('--')).length > 1) throw fail('INVALID_ARGUMENT');
    result = await prepare({ mode: args.includes('--update') ? 'update' : args.includes('--check') ? 'check' : 'ensure', target: args.find(arg => !arg.startsWith('--')) ?? 'all' });
  } catch (error) { result = { schemaVersion: 1, ok: false, code: error.code && /^[A-Z_]+$/.test(error.code) ? error.code : 'PREPARATION_FAILED', results: [] }; }
  console.log(JSON.stringify(hook ? hookOutput(result) : result));
  if (!hook && !result.ok) process.exitCode = 1;
}
