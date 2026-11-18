import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';

const DEFAULT_WINDOW = 200000;

export function projectsRoot() {
  return path.join(os.homedir(), '.qoder-cn', 'projects');
}

export function findTranscript({ transcript, session } = {}) {
  if (transcript && fs.existsSync(transcript)) return transcript;
  const root = projectsRoot();
  if (!fs.existsSync(root)) return null;
  if (session) {
    for (const slug of fs.readdirSync(root)) {
      const p = path.join(root, slug, `${session}.jsonl`);
      if (fs.existsSync(p)) return p;
    }
    return null;
  }
  let best = null;
  let bestM = 0;
  for (const slug of fs.readdirSync(root)) {
    const dir = path.join(root, slug);
    if (!fs.statSync(dir).isDirectory()) continue;
    for (const f of fs.readdirSync(dir)) {
      if (!f.endsWith('.jsonl')) continue;
      const p = path.join(dir, f);
      const m = fs.statSync(p).mtimeMs;
      if (m > bestM) { bestM = m; best = p; }
    }
  }
  return best;
}

// 粗估：CJK 一字约一 token，其余按 4 字符一 token；仅供占比参考
export function estTokens(text) {
  if (!text) return 0;
  const cjk = (text.match(/[一-鿿　-〿＀-￯]/g) || []).length;
  return cjk + Math.ceil((text.length - cjk) / 4);
}

function blockText(content) {
  if (typeof content === 'string') return content;
  if (Array.isArray(content)) {
    return content.map(b => (b && b.type === 'text' ? b.text || '' : '')).join('');
  }
  return '';
}

export function compute(transcriptPath, { window } = {}) {
  const lines = fs.readFileSync(transcriptPath, 'utf8').split('\n');
  let contextWindow = window || null;
  let model = null;
  let title = null;
  let userTurns = 0;
  let toolCalls = 0;
  let roundTrips = 0;
  let credits = 0;
  let originalCredits = 0;
  let billed = 0;
  let peakRatio = 0;
  let lastRatio = 0;
  let firstTs = null;
  let lastTs = null;
  let lastUserTs = null;
  const byTool = {};
  const byFile = {};
  const toolUseById = {};
  const billedEvents = [];

  for (const line of lines) {
    if (!line.trim()) continue;
    let o;
    try { o = JSON.parse(line); } catch { continue; }
    const ts = typeof o.timestamp === 'number' ? o.timestamp
      : typeof o.timestamp === 'string' ? Date.parse(o.timestamp) : null;
    if (Number.isFinite(ts)) {
      if (firstTs === null || ts < firstTs) firstTs = ts;
      if (lastTs === null || ts > lastTs) lastTs = ts;
    }
    if (o.type === 'runtime-config') {
      if (o.model) model = o.model;
      if (!contextWindow && o.contextWindow) contextWindow = o.contextWindow;
      continue;
    }
    if (o.isSidechain === true) continue;
    const content = o.message && o.message.content;

    if (o.type === 'user') {
      const text = blockText(content);
      const isToolResultOnly = Array.isArray(content) && content.length > 0 &&
        content.every(b => b && b.type === 'tool_result');
      if (text.trim() && !isToolResultOnly) {
        userTurns++;
        if (Number.isFinite(ts)) lastUserTs = ts;
        if (!title) title = text.trim().replace(/\s+/g, ' ').slice(0, 40);
      }
      if (Array.isArray(content)) {
        for (const b of content) {
          if (!b || b.type !== 'tool_result') continue;
          const meta = toolUseById[b.tool_use_id];
          const tokens = estTokens(blockText(b.content));
          if (meta) {
            const t = (byTool[meta.name] ||= { calls: 0, resultTokens: 0 });
            t.resultTokens += tokens;
            if (meta.path) {
              const f = (byFile[meta.path] ||= { reads: 0, estTokens: 0, tool: meta.name });
              f.reads++;
              f.estTokens += tokens;
            }
          }
        }
      }
      continue;
    }

    if (o.type !== 'assistant') continue;
    if (Array.isArray(content)) {
      for (const b of content) {
        if (!b || b.type !== 'tool_use') continue;
        toolCalls++;
        const t = (byTool[b.name] ||= { calls: 0, resultTokens: 0 });
        t.calls++;
        const p = (b.input && (b.input.file_path || b.input.path)) || null;
        toolUseById[b.id] = { name: b.name, path: p };
      }
    }
    const u = o.message && o.message.usage;
    if (u && (u.billable === true || u.context_usage_ratio > 0 || u.credits > 0)) {
      roundTrips++;
      credits += u.credits || 0;
      originalCredits += u.original_credits || 0;
      const ratio = u.context_usage_ratio || 0;
      if (ratio > 0) {
        billed += ratio * (contextWindow || DEFAULT_WINDOW);
        if (ratio > peakRatio) peakRatio = ratio;
        lastRatio = ratio;
      }
      billedEvents.push({ ts: Number.isFinite(ts) ? ts : null, credits: u.credits || 0, ratio });
    }
  }

  // 本轮 = 最近一条文本用户消息之后的计费事件
  let turnCredits = 0;
  let turnRoundTrips = 0;
  let turnPeakRatio = 0;
  if (lastUserTs !== null) {
    for (const e of billedEvents) {
      if (e.ts === null || e.ts < lastUserTs) continue;
      turnRoundTrips++;
      turnCredits += e.credits;
      if (e.ratio > turnPeakRatio) turnPeakRatio = e.ratio;
    }
  }

  const win = contextWindow || DEFAULT_WINDOW;
  const net = Math.round(lastRatio * win);
  return {
    transcript: transcriptPath,
    session: { id: path.basename(transcriptPath, '.jsonl'), title, model },
    context: {
      contextWindow: win,
      windowSource: contextWindow ? 'runtime-config' : 'fallback',
      netContextTokens: net,
      peakRatio,
      amplification: net > 0 ? billed / net : null,
    },
    totals: {
      credits: Math.round(credits * 1000) / 1000,
      originalCredits: Math.round(originalCredits * 1000) / 1000,
      billedInputTokens: Math.round(billed),
      roundTrips,
      userTurns,
      toolCalls,
      durationMs: firstTs !== null && lastTs !== null && lastTs >= firstTs ? lastTs - firstTs : null,
      turnDurationMs: lastUserTs !== null && lastTs !== null && lastTs >= lastUserTs ? lastTs - lastUserTs : null,
      turnCredits: Math.round(turnCredits * 1000) / 1000,
      turnRoundTrips,
      turnPeakRatio,
    },
    byTool: Object.entries(byTool).map(([tool, v]) => ({ tool, ...v }))
      .sort((a, b) => b.resultTokens - a.resultTokens),
    byFile: Object.entries(byFile).map(([file, v]) => ({ file, ...v }))
      .sort((a, b) => b.estTokens - a.estTokens),
  };
}

export function fmtDuration(ms) {
  if (ms === null || ms === undefined || !Number.isFinite(ms) || ms < 0) return null;
  const s = Math.floor(ms / 1000);
  if (s < 60) return `${s}秒`;
  const min = Math.floor(s / 60);
  const d = Math.floor(min / 1440);
  const h = Math.floor((min % 1440) / 60);
  const m = min % 60;
  if (d > 0) return `${d}天${h}小时`;
  if (h > 0) return m ? `${h}小时${m}分钟` : `${h}小时`;
  return `${m}分钟`;
}

export function fmtClock(ms) {
  if (ms === null || ms === undefined || !Number.isFinite(ms) || ms < 0) return null;
  const s = Math.floor(ms / 1000);
  const h = Math.floor(s / 3600);
  const m = Math.floor((s % 3600) / 60);
  const sec = s % 60;
  if (h > 0) return `${h}h ${m}m`;
  if (m > 0) return `${m}m ${sec}s`;
  return `${sec}s`;
}

function fmt(n) { return n.toLocaleString('en-US'); }

function human(r) {
  const t = r.totals;
  const c = r.context;
  const out = [];
  out.push(`会话：${r.session.title || '(无标题)'}（${r.session.id.slice(0, 8)}）`);
  out.push(`模型：${r.session.model || '—'}｜窗口：${fmt(c.contextWindow)}（${c.windowSource === 'fallback' ? '回退估算' : 'runtime-config'}）`);
  if (t.roundTrips > 0) {
    out.push(`Credits：${t.credits}（measured，${t.roundTrips} 笔往返）`);
    out.push(`计费输入：≈${fmt(t.billedInputTokens)} tokens｜净上下文：${fmt(c.netContextTokens)}｜峰值：${(c.peakRatio * 100).toFixed(1)}%｜放大：${c.amplification ? c.amplification.toFixed(1) : '—'}×`);
  } else {
    out.push('Credits：不可用（转录无 usage，非「没花钱」）');
  }
  const dur = fmtDuration(t.turnDurationMs);
  const span = fmtDuration(t.durationMs);
  out.push(`对话 ${t.userTurns} 轮｜工具调用 ${t.toolCalls} 次${dur ? `｜本轮耗时 ${dur}` : ''}${span ? `｜整场 ${span}` : ''}`);
  if (r.byTool.length) {
    out.push('工具：' + r.byTool.map(x => `${x.tool} ${x.calls}次/返回≈${fmt(x.resultTokens)}tok`).join('；'));
  }
  if (r.byFile.length) {
    out.push('文件榜（估算）：');
    for (const f of r.byFile.slice(0, 5)) out.push(`  ≈${fmt(f.estTokens)} tok / 读${f.reads}次 ${f.file}`);
  }
  return out.join('\n');
}

const argv = process.argv.slice(2);
if (argv.length && process.argv[1] && process.argv[1].endsWith('engine.mjs')) {
  const get = (k) => { const i = argv.indexOf(k); return i >= 0 ? argv[i + 1] : null; };
  const transcript = findTranscript({ transcript: get('--transcript'), session: get('--session') });
  if (!transcript) { console.error('未找到转录'); process.exit(1); }
  const window = get('--window') ? Number(get('--window')) : undefined;
  const r = compute(transcript, { window });
  console.log(argv.includes('--json') ? JSON.stringify(r, null, 2) : human(r));
}