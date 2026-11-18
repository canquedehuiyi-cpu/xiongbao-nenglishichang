/**
 * 带上限、会自报覆盖度的目录遍历。
 *
 * 单独成模块是因为 tools.mjs 声明了「不得读写文件」，而这个必须读；
 * 也因为这套循环在三个脚本里各手写过一遍——三处都只数「收够几个文件」，
 * 不数「跳过了多少个」。450 页的产物扫 400 页，报出来是一句口气完整的
 * 「400 页零内联事件」，同时站点地图那边还反过来编出「50 个 URL 在产物中不存在」
 * 的假缺陷（第 3 轮实测）。上限本身是必要的（仓库可能很大），
 * 不可接受的是触顶之后仍按全量口径下结论。
 */

import { readdirSync, statSync } from 'node:fs';
import { join } from 'node:path';

const DEFAULT_SKIP = new Set(['node_modules', '.git', '.astro', 'coverage', '.site-audit']);

/** 只吞真正的文件系统错误；代码写错（ReferenceError 之类）必须冒出来，不能被记成「读不了」。 */
function isFsError(e) {
  return !!(e && typeof e.code === 'string' && /^(ENOENT|EACCES|EPERM|ENOTDIR|ELOOP|EBUSY|ENAMETOOLONG|EISDIR|ERR_)/.test(e.code));
}

/**
 * @param {string} dir
 * @param {{match?:(name:string,full:string)=>boolean, cap?:number, skipDirs?:Set<string>}} [opt]
 * @returns {{files:string[], truncated:boolean, unreadable:number, cap:number, errors:string[]}}
 */
export function walkLimited(dir, opt = {}) {
  const cap = Number(opt.cap) || 400;
  const match = opt.match || ((name) => name.endsWith('.html'));
  const skip = opt.skipDirs || DEFAULT_SKIP;
  const files = [];
  const errors = [];
  let truncated = false;
  let unreadable = 0;
  const walk = (d) => {
    let names;
    try {
      names = readdirSync(d);
    } catch (e) {
      if (!isFsError(e)) throw e;
      unreadable++;
      errors.push(String(e.code) + ' ' + d);
      return;
    }
    for (const n of names) {
      if (files.length >= cap) {
        truncated = true;
        return;
      }
      const full = join(d, n);
      let st = null;
      try {
        st = statSync(full);
      } catch (e) {
        if (!isFsError(e)) throw e;
        unreadable++;
        continue;
      }
      if (st.isDirectory()) {
        if (!skip.has(n)) walk(full);
      } else if (match(n, full)) files.push(full);
    }
  };
  walk(dir);
  return { files, truncated, unreadable, cap, errors };
}

/**
 * 一行覆盖度说明；扫全了且没有读不了的目录时返回空串。
 * 调用方把它拼进 title/evidence，或在触顶时改判 not-run——静默触顶等于假结论。
 */
export function walkCoverage(w) {
  if (!w) return '';
  const bits = [];
  if (w.truncated) bits.push(`文件数触顶 ${w.cap}，未扫完（结论只覆盖已扫到的 ${w.files.length} 个）`);
  if (w.unreadable) bits.push(`${w.unreadable} 个目录/文件读不了`);
  return bits.join('；');
}
