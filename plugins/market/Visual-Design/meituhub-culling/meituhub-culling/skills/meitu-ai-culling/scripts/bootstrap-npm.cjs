'use strict';
// Standalone Node-only bootstrap: no npm, curl, tar or global installation needed.
const fs = require('node:fs');
const path = require('node:path');
const { createHash } = require('node:crypto');
const { gunzipSync } = require('node:zlib');
const { spawnSync } = require('node:child_process');
const version = '10.9.2';
const url = `https://registry.npmjs.org/npm/-/npm-${version}.tgz`;
const integrity = 'iriPEPIkoMYUy3F6f3wwSZAU93E0Eg6cHwIR6jzzOXWSy+SD/rOODEs74cVONHKSx2obXtuUoyidVEhISrisgQ==';
const limit = 32 * 1024 * 1024;

function unpack(archive, destination) {
  if (createHash('sha512').update(archive).digest('base64') !== integrity) {
    throw new Error('npm archive integrity check failed');
  }
  const tar = gunzipSync(archive, { maxOutputLength: limit });
  let offset = 0;
  while (offset + 512 <= tar.length) {
    const header = tar.subarray(offset, offset + 512);
    if (header.every(byte => byte === 0)) return;
    const str = (start, length) => header.subarray(start, start + length).toString('utf8').split('\0')[0];
    const name = str(0, 100);
    const prefix = str(345, 155);
    const entry = prefix ? `${prefix}/${name}` : name;
    const size = parseInt(str(124, 12).trim(), 8);
    const checksum = parseInt(str(148, 8).trim(), 8);
    const sum = header.reduce((total, byte, index) => total + (index >= 148 && index < 156 ? 32 : byte), 0);
    if (checksum !== sum || !Number.isSafeInteger(size) || size < 0 || offset + 512 + size > tar.length) {
      throw new Error('Invalid npm archive header');
    }
    // npm's pinned archive contains regular files only; reject links and traversal.
    if (!entry.startsWith('package/') || /[\\:]/.test(entry) || entry.split('/').includes('..') ||
        ![0, 48, 53].includes(header[156])) throw new Error('Unsafe npm archive entry');
    const target = path.resolve(destination, entry.slice(8));
    if (!target.startsWith(destination + path.sep)) throw new Error('Unsafe npm archive path');
    if (header[156] === 53) fs.mkdirSync(target, { recursive: true });
    else {
      fs.mkdirSync(path.dirname(target), { recursive: true });
      fs.writeFileSync(target, tar.subarray(offset + 512, offset + 512 + size), { flag: 'wx', mode: 0o644 });
    }
    offset += 512 + Math.ceil(size / 512) * 512;
  }
  throw new Error('Truncated npm archive');
}

function usable(root) {
  try {
    const pkg = JSON.parse(fs.readFileSync(path.join(root, 'package.json'), 'utf8'));
    if (pkg.name !== 'npm' || pkg.version !== version) return false;
    const probe = spawnSync(process.execPath, [path.join(root, 'bin/npm-cli.js'), '--version'],
      { encoding: 'utf8', timeout: 10000, windowsHide: true });
    return probe.status === 0 && probe.stdout.trim() === version;
  } catch { return false; }
}

async function prepare(runtime) {
  const parent = path.join(runtime, 'tools');
  const root = path.join(parent, `npm-${version}`);
  if (usable(root)) return path.join(root, 'bin/npm-cli.js');
  fs.mkdirSync(parent, { recursive: true });
  const staging = fs.mkdtempSync(path.join(parent, 'npm-install-'));
  try {
    console.error('Preparing private npm runtime automatically...');
    const response = await fetch(url, { signal: AbortSignal.timeout(60000), redirect: 'error' });
    if (!response.ok) throw new Error(`npm download failed (HTTP ${response.status})`);
    const chunks = [];
    let size = 0;
    for await (const chunk of response.body) {
      size += chunk.length;
      if (size > limit) throw new Error('npm download exceeds size limit');
      chunks.push(Buffer.from(chunk));
    }
    unpack(Buffer.concat(chunks), staging);
    if (!usable(staging)) throw new Error('Private npm runtime validation failed');
    // The caller holds the shared qoder update lock throughout bootstrap/install.
    fs.rmSync(root, { recursive: true, force: true });
    fs.renameSync(staging, root);
    return path.join(root, 'bin/npm-cli.js');
  } finally {
    fs.rmSync(staging, { recursive: true, force: true });
  }
}

if (require.main === module) prepare(path.resolve(process.argv[2])).then(bin => console.log(bin)).catch(error => {
  console.error(`Automatic npm preparation failed: ${error.message}. Check access to registry.npmjs.org and retry setup.`);
  process.exitCode = 2;
});
module.exports = { unpack, prepare, version };
