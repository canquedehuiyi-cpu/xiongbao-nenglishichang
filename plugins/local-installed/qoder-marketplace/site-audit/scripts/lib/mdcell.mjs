/**
 * 报告单元格中和器。
 *
 * 为什么需要：报告的表格单元格里塞的是「被审站点/仓库的文本」（页面可见文字、响应头值、
 * 子进程输出）。只转义竖线不够——反引号仍能开代码块、方括号仍能造链接，长 URL 会把行撑爆。
 * 报告是给人和模型读的**摘要**，宁可损失一点格式，也不让被审对象决定报告的排版；
 * 完整原文始终在 findings.jsonl 里。
 */
const BS = String.fromCharCode(92);

export function neutralizeCell(value, max = 220) {
  return String(value == null ? '' : value)
    .replace(new RegExp(BS + 'r?' + BS + 'n', 'g'), ' ')
    .replace(/\|/g, '!')
    .replace(/`/g, "'")
    .replace(/\[/g, '(')
    .replace(/\]/g, ')')
    .replace(/https?:\/\/\S+/g, (u) => u.slice(0, 40) + '…')
    .slice(0, max);
}
