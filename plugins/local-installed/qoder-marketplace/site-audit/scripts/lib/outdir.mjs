/**
 * --out 位置约束。
 *
 * 为什么单列：账本目录若与被审项目互相包含，被审项目（它的脚本会被执行）就能
 * 读改写自己的审查结论，甚至在插件源码树里留下副本——下一个 ZIP 就被污染了。
 * 对抗审查实测：`--out <repo>/audit-out` 与 `--out <插件>/scripts` 当时都被接受。
 */

import { resolve, dirname, sep } from 'node:path';
import { fileURLToPath } from 'node:url';

const contains = (child, parent) => {
  const c = resolve(child).split(sep).join('/');
  const p = resolve(parent).split(sep).join('/');
  return c === p || c.startsWith(p + '/');
};

/**
 * @param {{out:string, repo?:string}} opts
 * @param {string} scriptName
 * @param {string} moduleUrl import.meta.url，用于定位插件自身根目录
 */
export function outDirProblems(opts, moduleUrl) {
  const out = resolve(opts.out);
  const bad = [];
  if (opts.repo && (contains(out, resolve(opts.repo)) || contains(resolve(opts.repo), out))) {
    bad.push('账本目录与被审项目互相包含：结论会被写进被审项目，或被其执行的脚本读改写');
  }
  const pluginRoot = resolve(dirname(fileURLToPath(moduleUrl)), '..', '..');
  if (contains(out, pluginRoot)) bad.push('账本目录在插件自身源码树内：副本与结论会污染下一个 ZIP');
  if (contains(out, dirname(process.execPath))) bad.push('账本目录在 node 安装目录内');
  return bad;
}
