/**
 * 最小 ZIP 写入器（零依赖，只用 node:zlib / node:fs）。
 *
 * 为什么要自己写：出包原先靠外部工具（bsdtar，失败就回落 PowerShell 的 Compress-Archive），
 * 而 Compress-Archive 把条目名存成 `bin\audit.mjs` 这种反斜杠分隔——ZIP 规范（APPNOTE 4.4.17）
 * 要求条目名一律用 `/`。宽容的解包器照样能解开，严格按规范解析的提交侧会判
 * 「包含非法包内路径，路径必须位于包根目录内」。依赖 PATH 上恰好有哪个 tar，
 * 等于把包的合法性交给环境；自己写就只有一条路径，Windows / Linux / Git Bash 产出完全一致。
 *
 * 只支持 deflate 存储普通文件：不加密、不 ZIP64、不放目录条目（解包器按路径自己建目录）。
 */

import { readFileSync, writeFileSync, readdirSync, statSync } from 'node:fs';
import { join, sep } from 'node:path';
import { deflateRawSync } from 'node:zlib';

const CRC_TABLE = (() => {
  const t = new Int32Array(256);
  for (let i = 0; i < 256; i++) {
    let c = i;
    for (let k = 0; k < 8; k++) c = c & 1 ? 0xedb88320 ^ (c >>> 1) : c >>> 1;
    t[i] = c;
  }
  return t;
})();

function crc32(buf) {
  let c = 0xffffffff;
  for (let i = 0; i < buf.length; i++) c = CRC_TABLE[(c ^ buf[i]) & 0xff] ^ (c >>> 8);
  return (c ^ 0xffffffff) >>> 0;
}

function dosDateTime(d = new Date()) {
  const y = Math.max(1980, d.getFullYear());
  const date = ((y - 1980) << 9) | ((d.getMonth() + 1) << 5) | d.getDate();
  const time = (d.getHours() << 11) | (d.getMinutes() << 5) | (Math.floor(d.getSeconds() / 2));
  return { time, date };
}

/** 条目名必须是相对路径 + `/` 分隔；任何越界或反斜杠都在这里硬拒，不让它进包。 */
function safeName(name) {
  const raw = String(name);
  // 反斜杠要先拒：Windows 上它正是路径分隔符，先转换再检查会变成"悄悄规范化"，
  // 于是同一份代码在 Windows 出合法包、在 Linux 抛错——那种差异最难查。
  if (raw.includes('\\')) throw new Error('条目名含反斜杠（ZIP 规范要求 / 分隔）：' + raw);
  const n = raw.split(sep).join('/').replace(/^\.\/+/, '').replace(/^\/+/, '');
  if (!n) throw new Error('空的条目名');
  if (n === '.' || n === '..' || /(^|\/)\.\.(\/|$)/.test(n)) throw new Error('条目名越界：' + n);
  if (/^[A-Za-z]:/.test(n)) throw new Error('条目名含盘符：' + n);
  return n;
}

/**
 * @param {string} outPath 目标 zip 路径
 * @param {Array<{name: string, data: Buffer|string}>} entries
 */
export function writeZip(outPath, entries) {
  const { time, date } = dosDateTime();
  const locals = [];
  const centrals = [];
  let offset = 0;
  for (const e of entries) {
    const name = safeName(e.name);
    const nameBuf = Buffer.from(name, 'utf8');
    const raw = Buffer.isBuffer(e.data) ? e.data : Buffer.from(String(e.data), 'utf8');
    const deflated = deflateRawSync(raw, { level: 9 });
    const useDeflate = deflated.length < raw.length;
    const body = useDeflate ? deflated : raw;
    const method = useDeflate ? 8 : 0;
    const crc = crc32(raw);

    const lh = Buffer.alloc(30);
    lh.writeUInt32LE(0x04034b50, 0);
    lh.writeUInt16LE(20, 4);
    lh.writeUInt16LE(0, 6);
    lh.writeUInt16LE(method, 8);
    lh.writeUInt16LE(time, 10);
    lh.writeUInt16LE(date, 12);
    lh.writeUInt32LE(crc, 14);
    lh.writeUInt32LE(body.length, 18);
    lh.writeUInt32LE(raw.length, 22);
    lh.writeUInt16LE(nameBuf.length, 26);
    lh.writeUInt16LE(0, 28);
    locals.push(lh, nameBuf, body);

    const ch = Buffer.alloc(46);
    ch.writeUInt32LE(0x02014b50, 0);
    ch.writeUInt16LE(20, 4);
    ch.writeUInt16LE(20, 6);
    ch.writeUInt16LE(0, 8);
    ch.writeUInt16LE(method, 10);
    ch.writeUInt16LE(time, 12);
    ch.writeUInt16LE(date, 14);
    ch.writeUInt32LE(crc, 16);
    ch.writeUInt32LE(body.length, 20);
    ch.writeUInt32LE(raw.length, 24);
    ch.writeUInt16LE(nameBuf.length, 28);
    ch.writeUInt16LE(0, 30);
    ch.writeUInt16LE(0, 32);
    ch.writeUInt16LE(0, 34);
    ch.writeUInt16LE(0, 36);
    ch.writeUInt32LE(0o644 << 16, 38);
    ch.writeUInt32LE(offset, 42);
    centrals.push(ch, nameBuf);

    offset += lh.length + nameBuf.length + body.length;
  }
  const cd = Buffer.concat(centrals);
  const eocd = Buffer.alloc(22);
  eocd.writeUInt32LE(0x06054b50, 0);
  eocd.writeUInt16LE(0, 4);
  eocd.writeUInt16LE(0, 6);
  eocd.writeUInt16LE(entries.length, 8);
  eocd.writeUInt16LE(entries.length, 10);
  eocd.writeUInt32LE(cd.length, 12);
  eocd.writeUInt32LE(offset, 16);
  eocd.writeUInt16LE(0, 20);
  writeFileSync(outPath, Buffer.concat([Buffer.concat(locals), cd, eocd]));
  return { entries: entries.length, bytes: offset + cd.length + 22 };
}

/** 把一棵目录树打成 zip（条目名 = 相对 srcDir 的路径，`/` 分隔）。 */
export function zipDir(outPath, srcDir, { skip = () => false } = {}) {
  const entries = [];
  const walk = (dir, rel) => {
    for (const name of readdirSync(dir)) {
      const full = join(dir, name);
      const r = rel ? rel + '/' + name : name;
      if (skip(r, full)) continue;
      const st = statSync(full);
      if (st.isDirectory()) walk(full, r);
      else if (st.isFile()) entries.push({ name: r, data: readFileSync(full) });
    }
  };
  walk(srcDir, '');
  return writeZip(outPath, entries);
}
