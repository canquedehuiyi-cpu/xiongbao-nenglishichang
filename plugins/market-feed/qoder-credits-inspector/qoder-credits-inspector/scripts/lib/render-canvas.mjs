// render-canvas.mjs — 把报告数据注入 Canvas 模板，产出可被宿主渲染的 .canvas.tsx。
//
// 模板 (scripts/canvas/report.canvas.tsx.tpl) 内含唯一注入行：
//   const REPORT = null as unknown as Report;
// 渲染按“整行替换”把该行重写为真实报告 JSON 字面量：
//   const REPORT = {"schemaVersion":2,...} as unknown as Report;

import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { canvasPath, atomicWriteFile, sessionFileBase } from './paths.mjs';

const HERE = path.dirname(fileURLToPath(import.meta.url));
export const TEMPLATE_PATH = path.join(HERE, '..', 'canvas', 'report.canvas.tsx.tpl');

/** 用报告数据渲染模板，返回最终 .canvas.tsx 文本。
 *  采用整行替换：定位以 "const REPORT =" 开头的代码行并整体重写，
 *  避免注释里出现的同名串被误替换（String.replace 只换首个匹配）。 */
export function renderCanvasFromTemplate(template, report) {
  if (typeof template !== 'string') throw new Error('模板内容为空');
  const json = JSON.stringify(report);
  const lines = template.split('\n');
  let replaced = false;
  const out = lines.map((line) => {
    const t = line.trimStart();
    if (!replaced && t.startsWith('const REPORT =')) {
      replaced = true;
      const indent = line.slice(0, line.length - t.length);
      return `${indent}const REPORT = ${json} as unknown as Report;`;
    }
    return line;
  });
  if (!replaced) throw new Error('模板缺少注入点：未找到以 "const REPORT =" 开头的行');
  return out.join('\n');
}

/** 渲染结果的轻量完整性校验（打包/交付前的自检）。 */
export function assertRenderedCanvas(tsx) {
  const problems = [];
  if (!tsx.includes('from "qoder/canvas"')) problems.push('缺少 qoder/canvas 导入');
  if (!tsx.includes('ReportShell')) problems.push('缺少 ReportShell 根组件');
  if (tsx.includes('const REPORT = null')) problems.push('注入点未被替换');
  if (!tsx.includes('const REPORT = {')) problems.push('未注入报告数据');
  return problems;
}

/** 读取模板、注入数据、原子写出每会话 .canvas.tsx；返回输出路径（无模板则 null）。 */
export function renderCanvasToFile(report, outDir, base) {
  if (!fs.existsSync(TEMPLATE_PATH)) return null;
  const tpl = fs.readFileSync(TEMPLATE_PATH, 'utf8');
  const tsx = renderCanvasFromTemplate(tpl, report);
  const b = base || sessionFileBase(report?.session?.id, report?.session?.title);
  return atomicWriteFile(canvasPath(outDir, b), tsx);
}
