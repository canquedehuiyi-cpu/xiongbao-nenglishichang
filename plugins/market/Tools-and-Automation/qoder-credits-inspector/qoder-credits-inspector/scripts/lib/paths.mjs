// paths.mjs — 定位转录、会话与输出路径；提供原子写入。
//
// 平台事实：本机无 qodercli；两个客户端并存，各写一套转录：
//   桌面端：~/.qoder-cn/projects/<slug>/<sessionId>.jsonl              带 message.usage 真值
//   IDE 端：~/.qoder-cn/projects/<slug>/transcript/<sessionId>.jsonl   无 usage（报告数值全 0）
// slug 两代规则不同且不稳定，**不要靠它反推路径**（实测）：
//   桌面端把非字母数字逐个换 '-'：D:\Project\MES\Server → D--Project-MES-Server
//   IDE 端只换路径分隔符、保留 '.' 与中文：
//     D:\Project\MES\Server                         → D-Project-MES-Server
//     C:\Users\ocean.cui\Desktop\QoderCredits截析V2 → c-Users-ocean.cui-Desktop-QoderCredits截析V2
//     （盘符大小写还不稳定）
// 插件期由 Stop 钩子的 stdin 直接给出 transcript_path，无需推导 slug；本模块主要用于
// dev/CLI 的自动发现与输出定位，一律按「遍历全部 slug + 探两层目录」兼容两代布局。

import os from 'node:os';
import path from 'node:path';
import fs from 'node:fs';

export function qoderHome() {
  return process.env.QODER_HOME || path.join(os.homedir(), '.qoder-cn');
}

export function projectsDir() {
  return path.join(qoderHome(), 'projects');
}

/** 把工作目录转换为 Qoder 项目 slug。
 *  ⚠ 全仓无调用，保留仅作历史参考：IDE 端 slug 规则与它不一致（保留 '.' 与中文、盘符
 *  大小写不稳定），用它反推会找不到转录。发现转录一律走 findTranscriptForSession 的遍历。 */
export function slugFromCwd(cwd) {
  return String(cwd || '').replace(/[^A-Za-z0-9]/g, '-');
}

/** 一个项目 slug 目录下可能存放富转录的位置：目录本身（旧布局）+ transcript\ 子目录（新布局）。
 *  只下探一层，故 <sessionId>\subagents\agent-*.jsonl 不会被误当成主转录。 */
function transcriptDirs(slugDir) {
  const dirs = [slugDir];
  const nested = path.join(slugDir, 'transcript');
  try {
    if (fs.statSync(nested).isDirectory()) dirs.push(nested);
  } catch {
    /* 无 transcript\ 子目录（旧布局），只扫 slug 目录本身 */
  }
  return dirs;
}

/** 按 sessionId 在所有项目下查找富转录（兼容两代布局）。 */
export function findTranscriptForSession(sessionId) {
  if (!sessionId) return null;
  const root = projectsDir();
  if (!fs.existsSync(root)) return null;
  for (const slug of fs.readdirSync(root)) {
    for (const dir of transcriptDirs(path.join(root, slug))) {
      const p = path.join(dir, `${sessionId}.jsonl`);
      if (fs.existsSync(p)) return p;
    }
  }
  return null;
}

/** 返回最近修改的富转录（dev/CLI 的“当前会话”启发式）。 */
export function findLatestTranscript() {
  const root = projectsDir();
  if (!fs.existsSync(root)) return null;
  let best = null;
  let bestM = -1;
  for (const slug of fs.readdirSync(root)) {
    const dir = path.join(root, slug);
    let st;
    try {
      st = fs.statSync(dir);
    } catch {
      continue;
    }
    if (!st.isDirectory()) continue;
    for (const tdir of transcriptDirs(dir)) {
      let names;
      try {
        names = fs.readdirSync(tdir);
      } catch {
        continue;
      }
      for (const fn of names) {
        if (!fn.endsWith('.jsonl')) continue;
        const p = path.join(tdir, fn);
        try {
          const m = fs.statSync(p).mtimeMs;
          if (m > bestM) {
            bestM = m;
            best = p;
          }
        } catch {
          /* 忽略不可读文件 */
        }
      }
    }
  }
  return best;
}

/** 报告输出目录（默认落在工作目录下的 .qoder-credits/）。 */
export function defaultOutDir(cwd) {
  return path.join(cwd || process.cwd(), '.qoder-credits');
}

export function reportJsonPath(outDir) {
  return path.join(outDir, 'report.json');
}

export function canvasPath(outDir, base = 'session-tokens') {
  return path.join(outDir, `${base}.canvas.tsx`);
}

/** 官方 UI 真值回填文件路径：<outDir>\overrides\<sessionId>.json。
 *  IDE 端转录不含 usage，本地算不出 Credits；把官方 UI 的数字写进这个文件，
 *  报告就会多出「官方 UI 真值（手工录入）」一段，并与本地推导值并列对账。 */
export function overridePath(outDir, sessionId) {
  return path.join(outDir, 'overrides', `${sessionId}.json`);
}

/** 把会话标题清洗为安全的文件名片段：保留中文，仅替换 Windows 非法字符，剔除零宽字符，折叠空白，限长 40。
 *  零宽字符必须剔：新布局转录无 custom-title，标题回退到首条用户提问正文，而提问里常带
 *  U+200B（实测产出过以 U+200B 开头的文件名，导致按名读产物失败）。 */
function sanitizeTitle(title) {
  if (!title) return '';
  return String(title)
    .replace(/[\u200B-\u200D\u2060\uFEFF]/g, '')
    .replace(/[\\/:*?"<>|]/g, '_')
    .replace(/[\r\n\t]+/g, ' ')
    .replace(/\s+/g, ' ')
    .trim()
    .slice(0, 40)
    .replace(/[.\s]+$/, '');
}

/** 会话产物文件名基座：<标题>__<id 前 8 位>；无标题回退 session-<id 前 8 位>。
 *  标题取自转录 custom-title，与前端会话列表显示一致，便于对应；短 id 保证唯一。 */
export function sessionFileBase(sessionId, title) {
  const id = String(sessionId || '').trim();
  const shortId = id ? id.slice(0, 8) : 'current';
  const t = sanitizeTitle(title);
  return t ? `${t}__${shortId}` : `session-${shortId}`;
}

/** 确保目录存在。 */
export function ensureDir(dir) {
  fs.mkdirSync(dir, { recursive: true });
  return dir;
}

/** 原子写入：先写 .tmp 再 rename，避免刷新时读到半截文件。
 *  注：Windows 上 renameSync 不会覆盖已存在目标，故先移除旧文件（刷新所需）。 */
export function atomicWriteFile(filePath, text) {
  ensureDir(path.dirname(filePath));
  const tmp = `${filePath}.tmp`;
  fs.writeFileSync(tmp, text, 'utf8');
  try {
    fs.rmSync(filePath, { force: true });
  } catch {
    /* 旧文件不存在或不可删，忽略；rename 失败时向上报错 */
  }
  fs.renameSync(tmp, filePath);
  return filePath;
}
