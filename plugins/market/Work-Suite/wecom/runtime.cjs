// Shared by the Unix and Windows entrypoints. No business arguments go through a shell.
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { spawnSync } = require('node:child_process');

const isWindows = process.platform === 'win32';
const installRoot = path.resolve(
  process.env.WECOM_CLI_INSTALL_ROOT || path.join(os.homedir(), '.local/share/qoder/wecom-cli'),
);
const managedEntry = path.join(installRoot, 'node_modules/@wecom/cli/bin/wecom.js');
const pathDirs = (process.env.PATH || '').split(path.delimiter).filter(Boolean);

function runtimeFile(candidate) {
  try {
    const file = fs.realpathSync(candidate);
    if (!fs.statSync(file).isFile() || file === fs.realpathSync(__filename)) return null;
    const fd = fs.openSync(file, 'r');
    const head = Buffer.alloc(256);
    try {
      fs.readSync(fd, head, 0, head.length, 0);
    } finally {
      fs.closeSync(fd);
    }
    // Skip aliases to this plugin and wrappers from other installed copies.
    if (head.toString().includes('wecom-qoder-entrypoint')) return null;
    if (/\.(cmd|bat)$/i.test(file)) {
      // Resolve npm's Windows shim to JavaScript; never interpolate CLI JSON into cmd.exe.
      return runtimeFile(path.join(path.dirname(file), 'node_modules/@wecom/cli/bin/wecom.js'));
    }
    const javascript = /\.[cm]?js$/i.test(file);
    fs.accessSync(file, javascript || isWindows ? fs.constants.R_OK : fs.constants.X_OK);
    return { file, command: javascript ? process.execPath : file, prefix: javascript ? [file] : [] };
  } catch {
    return null;
  }
}

function resolveRuntime() {
  const override = process.env.WECOM_CLI_RUNTIME_EXECUTABLE;
  if (override) {
    const runtime = runtimeFile(override);
    if (!runtime) throw new Error('WECOM_CLI_RUNTIME_EXECUTABLE does not point to a usable CLI runtime.');
    return runtime;
  }
  // A deliberate plugin install/upgrade must take effect even when PATH has an old CLI.
  const names = isWindows ? ['wecom-cli.exe', 'wecom-cli.cmd'] : ['wecom-cli'];
  const dirs = [
    path.join(os.homedir(), '.qoder/bin'),
    path.join(os.homedir(), '.qoder-cn/bin'),
    ...pathDirs,
    path.join(os.homedir(), '.local/bin'),
  ];
  for (const candidate of [managedEntry, ...dirs.flatMap((dir) => names.map((name) => path.join(dir, name)))]) {
    const runtime = runtimeFile(candidate);
    if (runtime) return runtime;
  }
  throw new Error('wecom-cli runtime is missing. Run wecom-cli-install, then retry.');
}

function run(runtime, args, options = {}) {
  const result = spawnSync(runtime.command, [...runtime.prefix, ...args], {
    stdio: 'inherit',
    ...options,
  });
  if (result.error) throw result.error;
  if (result.signal) process.kill(process.pid, result.signal);
  return result;
}

function npmRuntime() {
  const candidates = [
    path.join(path.dirname(process.execPath), 'node_modules/npm/bin/npm-cli.js'),
    ...pathDirs.flatMap((dir) => [
      path.join(dir, 'node_modules/npm/bin/npm-cli.js'),
      path.join(dir, 'npm'),
    ]),
  ];
  for (const candidate of candidates) {
    try {
      const file = fs.realpathSync(candidate);
      if (fs.statSync(file).isFile() && /npm-cli\.js$/.test(file)) {
        return { command: process.execPath, prefix: [file] };
      }
    } catch {
      // Continue looking in the remaining Node/npm installations.
    }
  }
  throw new Error('npm was not found. Install Node.js 18+ with npm, then retry.');
}

function install() {
  if (process.env.WECOM_CLI_RUNTIME_EXECUTABLE) {
    throw new Error('WECOM_CLI_RUNTIME_EXECUTABLE is set. Update that runtime or unset the override before installing.');
  }
  const { cliVersion } = require('./runtime-version.json');
  const result = run(npmRuntime(), [
    'install', '--prefix', installRoot, '--no-audit', '--no-fund', '--omit=dev',
    '--include=optional', '--ignore-scripts', '--save-exact', `@wecom/cli@${cliVersion}`,
  ]);
  if (result.status !== 0) return result.status || 1;
  const runtime = runtimeFile(managedEntry);
  if (!runtime) throw new Error('npm completed but @wecom/cli/bin/wecom.js is missing.');
  const check = run(runtime, ['--version'], { stdio: 'pipe', encoding: 'utf8' });
  if (check.status !== 0 || !check.stdout.includes(cliVersion)) {
    throw new Error(`Installed CLI failed version verification: ${check.stderr || check.stdout}`);
  }
  process.stdout.write(check.stdout);
  return 0;
}

const mode = process.argv[2];
try {
  if (Number(process.versions.node.split('.')[0]) < 18) throw new Error('Node.js 18+ is required.');
  if (mode === 'install') {
    process.exitCode = install();
  } else if (mode === 'check') {
    console.log(resolveRuntime().file);
  } else if (mode === 'run') {
    process.exitCode = run(resolveRuntime(), process.argv.slice(3)).status || 0;
  } else {
    throw new Error('Expected run, check, or install.');
  }
} catch (error) {
  console.error(error.message);
  process.exitCode = mode === 'run' || mode === 'check' ? 127 : 1;
}
