/**
 * 「什么东西进包」与「隐私闸门扫什么」必须是同一份规则。
 *
 * 这份规则分两级，是踩过坑之后定下来的：
 *  - ROOT 级：只在树的根层排除。开发期目录（打包输出、打包脚本本身、临时副本）不该进包，
 *    但**按名字全局排除会误伤同名子目录**——夹具自己的 `fixtures/synthetic-site/tools/`
 *    （渲染器与构建器）曾被一起排掉，装上去能力就是残的；这个 bug 只有解包后跑自检才会暴露。
 *  - ANY 级：任意层都排除（依赖、版本库、工具自身的运行痕迹）。
 *
 * 隐私扫描与打包共用这一份，是为了堵住另一种错法：闸门扫的东西比包里的多或少，
 * 于是「闸门通过」和「包是干净的」变成两件事。
 */

/** 只在根层排除的目录（开发期产物与工具）。 */
export const SKIP_ROOT = new Set(['dist-packages', 'tools', '.site-audit', '.work', '.sa-tmp', 'assets']);

/** 任意层排除的目录（只作用于**打包**；隐私扫描不看这些名字，见 scan.mjs）。 */
export const SKIP_ANY = new Set(['node_modules', '.git', '.site-audit', 'dist']);

/** 任意层排除的文件（本机词表与本地覆盖项，永不进包）。 */
export const SKIP_FILES = new Set(['forbidden.local.txt', 'forbidden.txt']);

/** 某个目录名在该深度是否应被跳过。 */
export function skipDir(name, depth) {
  if (SKIP_ANY.has(name)) return true;
  if (depth === 0 && SKIP_ROOT.has(name)) return true;
  return false;
}
