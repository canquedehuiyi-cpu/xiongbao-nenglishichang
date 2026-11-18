/* credit-watch 看板前端逻辑：读取本机数据集，派生指标、图表、账号明细与 CSV 导出。 */

const DATA_URL = "./data/credits.json";
const SERIES_COLORS = ["#2f5d56", "#9a7b2a", "#4d5f80"];
const BOM = "\ufeff";
const IS_DAY = /^\d{4}-\d{2}-\d{2}$/;
const STORE = { range: "credit-watch.range" };

const $ = (sel, root = document) => root.querySelector(sel);
const $$ = (sel, root = document) => [...root.querySelectorAll(sel)];

const num = new Intl.NumberFormat("zh-CN");
const fmt = (n) => num.format(Math.round(n));
const day = (d) => `${d.getUTCFullYear()}-${String(d.getUTCMonth() + 1).padStart(2, "0")}-${String(d.getUTCDate()).padStart(2, "0")}`;
const parseDay = (s) => new Date(`${s}T00:00:00Z`);
const cn = (s) => (IS_DAY.test(String(s || "")) ? `${Number(s.slice(5, 7))}月${Number(s.slice(8, 10))}日` : "—");
const short = (s) => (IS_DAY.test(String(s || "")) ? s.slice(5) : "—");
const diffDays = (a, b) => Math.round((parseDay(b) - parseDay(a)) / 86400000);
const addDay = (s, n) => day(new Date(parseDay(s).getTime() + n * 86400000));
const el = (tag, cls, text) => {
  const node = document.createElement(tag);
  if (cls) node.className = cls;
  if (text !== undefined) node.textContent = text;
  return node;
};
const loadRange = () => {
  try {
    const v = Number(localStorage.getItem(STORE.range));
    return [7, 14, 30].includes(v) ? v : 14;
  } catch {
    return 14;
  }
};

/* 本地服务在 index.html 里注入的令牌；线上发布的包里没有这段，因此前端据此区分能力。 */
const LOCAL = window.__CW_LOCAL__ || null;

let viewSpan = 14;
const state = { data: null, range: loadRange(), q: "" };

/* ---------------- 数据派生 ---------------- */

function latestPerAccount() {
  const map = new Map();
  for (const row of state.data.history) {
    const prev = map.get(row.label);
    if (!prev || row.ts > prev.ts) map.set(row.label, row);
  }
  return map;
}

function buildModel() {
  const { history, meta, accounts } = state.data;
  const endDay = meta.windowEnd;
  // 数据不足所选区间时按实际有的天数收口，否则刚装好的看板会铺一屏空轴。
  const available = Math.max(1, diffDays(meta.windowStart, meta.windowEnd) + 1);
  const span = Math.min(state.range, available);
  const clamped = span < state.range;
  viewSpan = span;
  const startDay = addDay(endDay, -(span - 1));
  const prevEnd = addDay(startDay, -1);
  const prevStart = addDay(prevEnd, -(span - 1));

  const days = [];
  for (let i = 0; i < span; i += 1) days.push(addDay(startDay, i));

  const inRange = history.filter((r) => r.day >= startDay && r.day <= endDay);
  const labels = accounts.map((a) => a.label);
  const color = new Map(labels.map((l, i) => [l, SERIES_COLORS[i % SERIES_COLORS.length]]));

  const perDay = days.map((d) => {
    const rows = inRange.filter((r) => r.day === d);
    const by = new Map(rows.map((r) => [r.label, r]));
    return {
      day: d,
      by,
      parts: labels.map((l) => (by.has(l) ? by.get(l).consumed : null)),
      total: rows.reduce((s, r) => s + r.consumed, 0),
      captured: rows.length,
    };
  });

  const capturedDays = perDay.filter((d) => d.captured > 0).length || 1;
  const consumedTotal = inRange.reduce((s, r) => s + r.consumed, 0);
  const avgBurn = consumedTotal / capturedDays;

  const last7 = days.slice(-7);
  const burn7 = inRange.filter((r) => r.day >= last7[0]).reduce((s, r) => s + r.consumed, 0);
  const captured7 = perDay.filter((d) => d.captured > 0 && d.day >= last7[0]).length || 1;
  const avgBurn7 = burn7 / captured7;

  const latest = latestPerAccount();
  const snapshot = labels.map((l) => ({ label: l, ...(latest.get(l) || { totalRemaining: 0, day: null }) }));
  const currentRemaining = snapshot.reduce((s, r) => s + r.totalRemaining, 0);

  const prevRows = history.filter((r) => r.day >= prevStart && r.day <= prevEnd);
  const prevDays = [...new Set(prevRows.map((r) => r.day))];
  const hasPrev = prevRows.length > 0;
  const prevAvgBurn = hasPrev ? prevRows.reduce((s, r) => s + r.consumed, 0) / prevDays.length : null;
  const prevSnapshot = new Map();
  for (const r of prevRows) {
    const p = prevSnapshot.get(r.label);
    if (!p || r.ts > p.ts) prevSnapshot.set(r.label, r);
  }
  const prevRemaining = [...prevSnapshot.values()].reduce((s, r) => s + r.totalRemaining, 0);

  // 采集新鲜度不依赖任何人为阈值，只看每个号最近一次采集离区间末日多远。
  const freshList = labels.map((l) => {
    const r = latest.get(l);
    return { label: l, day: r && r.day ? r.day : null, days: r && r.day ? diffDays(r.day, endDay) : null };
  });
  const knownDays = freshList.map((f) => f.days).filter((d) => d !== null);
  const freshness = {
    list: freshList,
    today: freshList.filter((f) => f.days === 0).length,
    oldest: knownDays.length ? Math.max(...knownDays) : null,
    missing: freshList.filter((f) => f.days === null).length,
  };
  const runway = avgBurn7 > 0 ? currentRemaining / avgBurn7 : null;

  /* 今日签到状态。判定全在数据层（scripts/reward-window.mjs），页面只照实说；
     这里只回答一个时区问题：这份数据还是不是今天那一轮的——拿它写的下一轮开窗时刻
     和当前时刻比一下就行，不把 0 点口径在前端再实现一遍。 */
  const rewardInfo = meta.reward || null;
  const roundOver = !!(rewardInfo && rewardInfo.nextWindowOpenAt && Date.now() >= Date.parse(rewardInfo.nextWindowOpenAt));
  const rewardRows = labels.map((l) => {
    const acc = accounts.find((a) => a.label === l);
    const r = acc ? acc.reward : null;
    // 演示数据是一份冻结的旧快照，本来就与今天无关，不拿"跨轮"去覆盖它要演示的三种状态
    const status = !rewardInfo || !r ? "none" : roundOver && !meta.demo ? "stale" : r.status;
    return { label: l, status, raw: r };
  });
  const reward = {
    info: rewardInfo,
    roundOver,
    rows: rewardRows,
    pending: rewardRows.filter((x) => x.status === "unclaimed").map((x) => x.label),
    done: rewardRows.filter((x) => x.status === "claimed").map((x) => x.label),
    unclear: rewardRows.filter((x) => ["unknown", "stale", "none"].includes(x.status)).map((x) => x.label),
  };

  const perAccountRunway = labels.map((l) => {
    const rows = inRange.filter((r) => r.label === l);
    const burn = rows.reduce((s, r) => s + r.consumed, 0) / (new Set(rows.map((r) => r.day)).size || 1);
    const last = latest.get(l);
    return {
      label: l,
      color: color.get(l),
      burn,
      remaining: last ? last.totalRemaining : 0,
      days: burn > 0 && last ? last.totalRemaining / burn : Infinity,
      account: accounts.find((a) => a.label === l),
      latest: last,
    };
  });

  // 逐日"已知总剩余"：未采集的号沿用最后一次结果，避免把缺口画成零消耗。
  const remainingByDay = days.map((d) => {
    let sum = 0;
    for (const l of labels) {
      let last = null;
      for (const r of history) {
        if (r.label === l && r.day <= d && (!last || r.ts > last.ts)) last = r;
      }
      sum += last ? last.totalRemaining : 0;
    }
    return sum;
  });

  return {
    labels,
    color,
    endDay,
    startDay,
    span,
    clamped,
    prevStart,
    prevEnd,
    hasPrev,
    perDay,
    inRange,
    consumedTotal,
    avgBurn,
    prevAvgBurn,
    prevRemaining,
    currentRemaining,
    remainingByDay,
    freshness,
    reward,
    runway,
    snapshot,
    perAccountRunway,
    capturedDays,
  };
}

/* ---------------- 指标卡 ---------------- */

function sparkline(svg, values, opts = {}) {
  svg.textContent = "";
  const clean = values.filter((v) => v !== null && Number.isFinite(v));
  if (clean.length < 2) return;
  const w = 120;
  const h = 28;
  const max = Math.max(...clean);
  const min = Math.min(...clean);
  const range = max - min || 1;
  const pts = values.map((v, i) => {
    const x = (i / (values.length - 1)) * w;
    const y = v === null ? h : h - 3 - ((v - min) / range) * (h - 6);
    return [x, y];
  });
  const line = pts.map(([x, y], i) => `${i ? "L" : "M"}${x.toFixed(1)} ${y.toFixed(1)}`).join(" ");
  const area = document.createElementNS("http://www.w3.org/2000/svg", "path");
  area.setAttribute("class", "spark-fill");
  area.setAttribute("d", `${line} L${w} ${h} L0 ${h} Z`);
  const path = document.createElementNS("http://www.w3.org/2000/svg", "path");
  path.setAttribute("class", "spark-line");
  path.setAttribute("d", line);
  const dot = document.createElementNS("http://www.w3.org/2000/svg", "circle");
  dot.setAttribute("class", "spark-dot");
  dot.setAttribute("r", "2");
  const last = pts[pts.length - 1];
  dot.setAttribute("cx", String(last[0]));
  dot.setAttribute("cy", String(last[1]));
  svg.append(area, path, dot);
  if (opts.label) svg.setAttribute("aria-label", `${opts.label}，共 ${values.length} 个数据点`);
}

function setKpi(id, { value, unit, note, delta, arrow = "flat", tone = "flat", dirWord }) {
  const card = $(`#${id}`);
  $("[data-value]", card).textContent = value;
  if (unit) $("[data-unit]", card).textContent = unit;
  $("[data-note]", card).textContent = note || "";
  const d = $("[data-delta]", card);
  if (!delta) {
    d.textContent = "无对比数据";
    d.dataset.dir = "flat";
    d.removeAttribute("title");
    return;
  }
  d.textContent = `${arrow === "down" ? "▼" : arrow === "up" ? "▲" : "—"} ${delta}`;
  d.dataset.dir = tone;
  d.title = `${dirWord || ""}（对比上一周期 ${viewSpan} 天）`;
}

function renderKpis(m) {
  const remUp = m.currentRemaining >= m.prevRemaining;
  setKpi("kpi-remaining", {
    value: fmt(m.currentRemaining),
    note: `${m.snapshot.length} 个号的最近一次采集结果合计`,
    delta: m.hasPrev ? `${fmt(Math.abs(m.currentRemaining - m.prevRemaining))} credits` : null,
    arrow: remUp ? "up" : "down",
    tone: remUp ? "up" : "down",
    dirWord: remUp ? "较上一周期增加" : "较上一周期减少",
  });
  sparkline($("#kpi-remaining .spark"), m.remainingByDay, { label: "总剩余走势" });

  const burnUp = m.avgBurn > m.prevAvgBurn;
  setKpi("kpi-burn", {
    value: fmt(m.avgBurn),
    unit: "credits / 天",
    note: `区间内消耗 ${fmt(m.consumedTotal)}，按 ${m.capturedDays} 个有采集记录的天折算`,
    delta: m.prevAvgBurn === null ? null : `${fmt(Math.abs(m.avgBurn - m.prevAvgBurn))} / 天`,
    arrow: burnUp ? "up" : "down",
    tone: burnUp ? "down" : "up",
    dirWord: burnUp ? "消耗比上一周期快" : "消耗比上一周期慢",
  });
  sparkline($("#kpi-burn .spark"), m.perDay.map((d) => d.total), { label: "每日消耗走势" });

  const tightest = [...m.perAccountRunway].sort((a, b) => a.days - b.days)[0];
  const tightText = (a) => (a.days === Infinity ? "按当前速率本周期内不会见底" : a.days < 1 ? "不足 1 天见底" : `约 ${a.days.toFixed(1)} 天见底`);
  setKpi("kpi-runway", {
    value: m.runway === null ? "—" : m.runway < 1 ? "< 1" : m.runway.toFixed(1),
    unit: "天",
    note: m.runway === null ? "区间内没采集到消耗，暂时估不出见底时间" : `最紧的是${tightest.label}：${tightText(tightest)}`,
    delta: null,
  });
  const meter = $("#kpi-runway [data-meter]");
  meter.textContent = "";
  for (const a of m.perAccountRunway) {
    const li = el("li");
    const pct = a.days === Infinity ? 100 : Math.max(4, Math.min(100, (a.days / viewSpan) * 100));
    const bar = el("span", "meter");
    const fill = el("i");
    fill.style.width = `${pct.toFixed(0)}%`;
    fill.style.background = a.color;
    bar.append(fill);
    li.append(
      el("span", null, a.label),
      bar,
      el("b", null, a.days === Infinity ? "周期内充足" : `${a.days.toFixed(1)} 天`),
    );
    meter.append(li);
  }

  const f = m.freshness;
  const stale = [...f.list].sort((a, b) => (b.days ?? -1) - (a.days ?? -1))[0];
  setKpi("kpi-fresh", {
    value: String(f.today),
    unit: `/ ${f.list.length} 个号今日采过`,
    note: f.missing
      ? `${f.missing} 个号在数据集里没有任何记录：在它那一行点「登录窗口」登进去，再刷新余量数据`
      : f.oldest === 0
        ? "全部账号今天都采到过"
        : `最旧的是 ${stale.label}：${stale.days} 天前（${short(stale.day)}）`,
    delta: null,
  });
  const dots = $("#kpi-fresh [data-dots]");
  dots.textContent = "";
  for (const a of f.list) {
    const level = a.days === null ? "out" : a.days === 0 ? "ok" : a.days === 1 ? "watch" : "alert";
    const li = el("li");
    const d = el("span", "dot");
    d.dataset.level = level;
    li.append(d, el("span", null, `${a.label} ${a.days === null ? "无记录" : a.days === 0 ? "今日" : `${a.days} 天前`}`));
    dots.append(li);
  }
}

/* ---------------- 面积图 ---------------- */

function niceScale(max) {
  if (!Number.isFinite(max) || max < 25) return { top: 100, step: 25 };
  const exp = Math.floor(Math.log10(max));
  const base = 10 ** exp;
  const step = [1, 2, 2.5, 5, 10].map((k) => k * base).find((s) => max / s <= 4) || 10 * base;
  return { top: Math.ceil(max / step) * step, step };
}

function renderArea(m) {
  const svg = $("#area-chart");
  const width = Math.max(360, svg.clientWidth || 640);
  const height = 232;
  const pad = { t: 10, r: 10, b: 26, l: 44 };
  svg.setAttribute("viewBox", `0 0 ${width} ${height}`);
  svg.setAttribute("preserveAspectRatio", "xMidYMid meet");
  const title = svg.querySelector("title");
  svg.textContent = "";
  svg.append(title);

  const plotW = width - pad.l - pad.r;
  const plotH = height - pad.t - pad.b;
  const maxStack = Math.max(1, ...m.perDay.map((d) => d.total));
  const { top, step } = niceScale(maxStack);
  const x = (i) => pad.l + (m.perDay.length === 1 ? plotW / 2 : (i / (m.perDay.length - 1)) * plotW);
  const y = (v) => pad.t + plotH - (v / top) * plotH;

  for (let v = 0; v <= top + 1e-6; v += step) {
    const line = document.createElementNS("http://www.w3.org/2000/svg", "line");
    line.setAttribute("class", "grid-line");
    line.setAttribute("x1", String(pad.l));
    line.setAttribute("x2", String(width - pad.r));
    line.setAttribute("y1", String(y(v)));
    line.setAttribute("y2", String(y(v)));
    svg.append(line);
    const text = document.createElementNS("http://www.w3.org/2000/svg", "text");
    text.setAttribute("class", "axis-text");
    text.setAttribute("x", String(pad.l - 8));
    text.setAttribute("y", String(y(v) + 3.5));
    text.setAttribute("text-anchor", "end");
    text.textContent = v >= 1000 ? `${(v / 1000).toFixed(v % 1000 ? 1 : 0)}k` : String(v);
    svg.append(text);
  }

  const gapDays = m.perDay.filter((d) => d.captured < m.labels.length);
  const band = (d) => {
    const i = m.perDay.indexOf(d);
    const w = plotW / Math.max(1, m.perDay.length - 1);
    const r = document.createElementNS("http://www.w3.org/2000/svg", "rect");
    r.setAttribute("class", "gap-band");
    r.setAttribute("x", String(Math.max(pad.l, x(i) - w / 2)));
    r.setAttribute("y", String(pad.t));
    r.setAttribute("width", String(Math.min(w, pad.l + plotW - Math.max(pad.l, x(i) - w / 2))));
    r.setAttribute("height", String(plotH));
    svg.append(r);
  };
  gapDays.forEach(band);

  const running = m.perDay.map(() => 0);
  m.labels.forEach((label, si) => {
    const upper = [];
    const base = [];
    m.perDay.forEach((d, i) => {
      const v = d.parts[si];
      base.push(v === null ? null : running[i]);
      if (v !== null) running[i] += v;
      upper.push(v === null ? null : running[i]);
    });
    const line = (arr) => {
      let str = "";
      let open = false;
      arr.forEach((v, i) => {
        if (v === null) {
          open = false;
          return;
        }
        str += `${open ? "L" : "M"}${x(i).toFixed(1)} ${y(v).toFixed(1)} `;
        open = true;
      });
      return str.trim();
    };
    const forward = [];
    const backward = [];
    m.perDay.forEach((d, i) => {
      if (d.parts[si] === null) return;
      forward.push(`${x(i).toFixed(1)},${y(upper[i]).toFixed(1)}`);
      backward.unshift(`${x(i).toFixed(1)},${y(base[i]).toFixed(1)}`);
    });
    const areaPath = document.createElementNS("http://www.w3.org/2000/svg", "path");
    areaPath.setAttribute("fill", m.color.get(label));
    areaPath.setAttribute("fill-opacity", "0.16");
    if (forward.length) areaPath.setAttribute("d", `M${forward.join(" L")} L${backward.join(" L")} Z`);
    const linePath = document.createElementNS("http://www.w3.org/2000/svg", "path");
    linePath.setAttribute("class", "series");
    linePath.setAttribute("fill", "none");
    linePath.setAttribute("stroke", m.color.get(label));
    linePath.setAttribute("d", line(upper));
    svg.append(areaPath, linePath);
  });

  const cursor = document.createElementNS("http://www.w3.org/2000/svg", "line");
  cursor.setAttribute("class", "cursor");
  cursor.setAttribute("y1", String(pad.t));
  cursor.setAttribute("y2", String(pad.t + plotH));
  svg.append(cursor);

  const readout = $("#trend-readout");
  const clear = () => {
    readout.textContent = "";
    cursor.setAttribute("x1", "-9");
    cursor.setAttribute("x2", "-9");
  };
  clear();

  const minGap = 48;
  const labelStep = Math.max(1, Math.ceil(m.perDay.length / 8));
  const drawn = [];
  let lastLabelX = -Infinity;
  const drawLabel = (i, replaceLast) => {
    if (replaceLast && drawn.length > 1) {
      const prev = drawn.pop();
      prev.remove();
      lastLabelX = drawn.length ? x(Number(drawn[drawn.length - 1].dataset.i)) : -Infinity;
    }
    const d = m.perDay[i];
    const text = document.createElementNS("http://www.w3.org/2000/svg", "text");
    text.setAttribute("class", "axis-text");
    text.setAttribute("x", String(x(i)));
    text.setAttribute("y", String(pad.t + plotH + 16));
    text.setAttribute("text-anchor", i === 0 ? "start" : i === m.perDay.length - 1 ? "end" : "middle");
    text.dataset.i = String(i);
    text.textContent = short(d.day);
    svg.append(text);
    drawn.push(text);
    lastLabelX = x(i);
  };
  for (let i = 0; i < m.perDay.length; i += labelStep) {
    if (x(i) - lastLabelX >= minGap || drawn.length === 0) drawLabel(i);
  }
  const lastIdx = m.perDay.length - 1;
  if (drawn.length && lastIdx % labelStep !== 0) {
    drawLabel(lastIdx, x(lastIdx) - lastLabelX < minGap && drawn.length > 1);
  }
  m.perDay.forEach((d, i) => {
    const w = plotW / Math.max(1, m.perDay.length);
    const hit = document.createElementNS("http://www.w3.org/2000/svg", "rect");
    hit.setAttribute("class", "hit");
    hit.setAttribute("x", String(x(i) - w / 2));
    hit.setAttribute("y", String(pad.t));
    hit.setAttribute("width", String(w));
    hit.setAttribute("height", String(plotH));
    const show = () => {
      cursor.setAttribute("x1", String(x(i)));
      cursor.setAttribute("x2", String(x(i)));
      if (!d.captured) {
        readout.textContent = `${cn(d.day)} · 当日无采集记录`;
        return;
      }
      const parts = m.labels.map((l, si) => (d.parts[si] === null ? null : `${l} ${fmt(d.parts[si])}`)).filter(Boolean);
      const miss = m.labels.filter((_, si) => d.parts[si] === null);
      readout.textContent = `${cn(d.day)} · 合计 ${fmt(d.total)} · ${parts.join(" / ")}${miss.length ? ` · ${miss.join("、")} 未采集` : ""}`;
    };
    hit.addEventListener("pointerenter", show);
    hit.addEventListener("pointermove", show);
    svg.append(hit);
  });
  svg.addEventListener("pointerleave", clear);

  const legend = $("#area-legend");
  legend.textContent = "";
  m.labels.forEach((l, si) => {
    const sum = m.perDay.reduce((s, d) => s + (d.parts[si] || 0), 0);
    const li = el("li");
    const sw = el("span", "swatch");
    sw.style.background = m.color.get(l);
    li.append(sw, el("span", null, l), el("b", null, `${fmt(sum)} credits`));
    legend.append(li);
  });
  if (gapDays.length) {
    const li = el("li");
    const sw = el("span", "swatch");
    sw.style.background = "rgba(133,136,143,0.3)";
    li.append(sw, el("span", null, `未采集日 ${gapDays.length} 天（灰带）`));
    legend.append(li);
  }
  $("#area-note").textContent = `纵轴上限 ${fmt(top)} credits，每格 ${fmt(step)}；缺口不代表零消耗，只代表当天没有该号的采集记录。`;
}

/* ---------------- 环图 ---------------- */

function renderDonut(m) {
  const svg = $("#donut");
  const title = svg.querySelector("title");
  svg.textContent = "";
  svg.append(title);
  const cx = 90;
  const cy = 90;
  const rOuter = 72;
  const rInner = 48;
  const total = m.currentRemaining;

  const arc = (start, end, r1, r2) => {
    const p = (a, r) => [cx + r * Math.cos(a), cy + r * Math.sin(a)];
    const large = end - start > Math.PI ? 1 : 0;
    const [x1, y1] = p(start, r2);
    const [x2, y2] = p(end, r2);
    const [x3, y3] = p(end, r1);
    const [x4, y4] = p(start, r1);
    return `M${x1} ${y1} A${r2} ${r2} 0 ${large} 1 ${x2} ${y2} L${x3} ${y3} A${r1} ${r1} 0 ${large} 0 ${x4} ${y4} Z`;
  };

  if (total <= 0) {
    const ring = document.createElementNS("http://www.w3.org/2000/svg", "circle");
    ring.setAttribute("cx", String(cx));
    ring.setAttribute("cy", String(cy));
    ring.setAttribute("r", String((rOuter + rInner) / 2));
    ring.setAttribute("fill", "none");
    ring.setAttribute("stroke", "#d2d1c9");
    ring.setAttribute("stroke-width", String(rOuter - rInner));
    svg.append(ring);
  } else {
    let angle = -Math.PI / 2;
    for (const a of m.perAccountRunway) {
      const value = Math.max(0, a.remaining);
      const slice = (value / total) * Math.PI * 2;
      if (slice <= 0) continue;
      const path = document.createElementNS("http://www.w3.org/2000/svg", "path");
      path.setAttribute("class", "seg");
      path.setAttribute("d", arc(angle, angle + slice - 0.012, rInner, rOuter));
      path.setAttribute("fill", a.color);
      const t = document.createElementNS("http://www.w3.org/2000/svg", "title");
      t.textContent = `${a.label}：${fmt(value)} credits（占 ${((value / total) * 100).toFixed(1)}%）`;
      path.append(t);
      svg.append(path);
      angle += slice;
    }
  }

  const centerValue = document.createElementNS("http://www.w3.org/2000/svg", "text");
  centerValue.setAttribute("class", "center-value");
  centerValue.setAttribute("x", String(cx));
  centerValue.setAttribute("y", String(cy + 2));
  centerValue.setAttribute("text-anchor", "middle");
  centerValue.textContent = total >= 10000 ? `${(total / 1000).toFixed(1)}k` : fmt(total);
  const centerLabel = document.createElementNS("http://www.w3.org/2000/svg", "text");
  centerLabel.setAttribute("class", "center-label");
  centerLabel.setAttribute("x", String(cx));
  centerLabel.setAttribute("y", String(cy + 18));
  centerLabel.setAttribute("text-anchor", "middle");
  centerLabel.textContent = "剩余 credits";
  svg.append(centerValue, centerLabel);

  const legend = $("#donut-legend");
  legend.textContent = "";
  for (const a of m.perAccountRunway) {
    const value = a.remaining;
    const li = el("li");
    const sw = el("span", "swatch");
    sw.style.background = a.color;
    const name = el("span", "dl-name");
    const refresh = a.latest ? a.latest.nextRefresh : a.account.earliestExpiry;
    name.append(el("b", null, a.label), el("small", null, `${a.account.planTier} · ${short(refresh)} 刷新`));
    const val = el("span", "dl-val");
    val.append(el("span", null, fmt(value)), el("small", null, total ? `${((value / total) * 100).toFixed(1)}%` : "—"));
    li.append(sw, name, val);
    legend.append(li);
  }
}

/* ---------------- 搜索命中高亮 ---------------- */

function highlight(node, text, q) {
  if (!q) {
    node.textContent = text;
    return;
  }
  const lower = text.toLowerCase();
  const needle = q.toLowerCase();
  let from = 0;
  let at = lower.indexOf(needle, from);
  if (at === -1) {
    node.textContent = text;
    return;
  }
  while (at !== -1) {
    node.append(text.slice(from, at));
    const mark = el("mark", null, text.slice(at, at + needle.length));
    node.append(mark);
    from = at + needle.length;
    at = lower.indexOf(needle, from);
  }
  node.append(text.slice(from));
}

/* ---------------- 账号表 ---------------- */

/* 每号一个"打开登录窗口"：只有本机服务在跑时才存在，且必须打到该号实测过的端口，
   不然会把 A 号的窗口当成 B 号开。 */
function canOpenProfile() {
  return !!(LOCAL && LOCAL.token && state.data && !state.data.meta.demo);
}

/* 资源包来源：接口给的是内部码，页面上只说人话；认不出来的码也不把码摆出去。 */
function packSource(src) {
  const s = String(src || "").trim();
  if (!s) return "未标注来源";
  if (!s.startsWith("RESOURCE_PACKAGE_SOURCE_")) return s; // 演示数据用的本来就是中文标签
  if (s.includes("BONUS")) return "活动赠送";
  if (s.includes("PURCHASE") || s.includes("BUY") || s.includes("PAY")) return "加购资源包";
  if (s.includes("TRIAL")) return "试用赠送";
  return "其他资源包";
}

/* 今日签到徽标。注意：这里**没有按钮**——签到入口只在 Qoder 桌面端右上角的浮窗里，
   页面开出的浏览器窗口里没这个东西，放一个"去领取"就是骗人。只做状态告知。 */
function rewardBadge(row) {
  const r = row.raw;
  const mk = (text, cls, title) => {
    const b = el("span", `rw-badge ${cls}`, text);
    if (title) b.title = title;
    return b;
  };
  if (!r || row.status === "none") {
    return mk("—", "rw-none", "判断不了：这个号的采集记录里没有资源包明细");
  }
  const round = cn(r.window);
  if (row.status === "stale") {
    return mk("无法判断", "rw-unknown", `数据是 ${round} 那一轮的，今天已翻篇。重新采集后才能判断。`);
  }
  if (row.status === "claimed") {
    const e = r.evidence || {};
    const detail = e.expires
      ? `依据：一个 ${cn(e.expires)} 到期的活动资源包（现在还剩 ${fmt(e.remaining || 0)}）。签来的包会被用掉，所以看到期日不看余额。`
      : "依据：今天到期日的那个活动资源包。";
    return mk(r.uncertain ? "疑似已签" : "已签", r.uncertain ? "rw-doubt" : "rw-yes", `${round} 那一轮已签。${detail}`);
  }
  if (row.status === "unclaimed") {
    return mk("未签", "rw-no", `${round} 这一轮还没找到签到生成的资源包。签到只能去 Qoder 桌面端右上角的浮窗点，看板代不了；点「刷新余量数据」后重新采集才能更新。`);
  }
  return mk("无法判断", "rw-unknown", r.reason || "数据不够判断今天这一轮");
}

function renderTable(m) {
  const tbody = $("#account-table tbody");
  const q = state.q.trim();
  const needle = q.toLowerCase();
  const openable = canOpenProfile();
  $("#account-table").dataset.openable = String(openable);
  tbody.textContent = "";
  let shown = 0;
  for (const a of m.perAccountRunway) {
    const hay = `${a.label} ${a.account.accountName} ${a.account.planTier}`.toLowerCase();
    if (needle && !hay.includes(needle)) continue;
    shown += 1;
    const tr = el("tr");
    const name = el("th");
    name.scope = "row";
    const cell = el("span", "acct-cell");
    const sw = el("span", "swatch");
    sw.style.background = a.color;
    const txt = el("span");
    const label = el("b");
    highlight(label, a.label, q);
    txt.append(label, el("small", null, a.account.accountName || "—"));
    cell.append(sw, txt);
    name.append(cell);

    const tier = el("td", null, a.account.planTier.replace("PRO_PLUS", "PRO+"));
    const quota = el("td", "num", fmt(a.account.planQuota));
    const rem = el("td", "num", fmt(a.remaining));
    const meterTd = el("td");
    const bar = el("div", "row-meter");
    const fill = el("i");
    const ratio = Math.max(0.02, Math.min(1, a.remaining / a.account.planQuota));
    fill.style.width = `${(ratio * 100).toFixed(1)}%`;
    fill.style.background = a.color;
    bar.append(fill);
    meterTd.append(bar, el("small", "muted", ` ${((a.remaining / a.account.planQuota) * 100).toFixed(0)}%`));

    const burn = el("td", "num", `${fmt(a.burn)}`);
    const expiry = el("td", null, short(a.latest ? a.latest.earliestExpiry : a.account.earliestExpiry));
    const rewardRow = m.reward.rows.find((x) => x.label === a.label) || { label: a.label, status: "none", raw: null };
    const rw = el("td", "col-reward");
    rw.append(rewardBadge(rewardRow));
    const refresh = el("td", null, short(a.latest ? a.latest.nextRefresh : "—"));
    const cap = el("td");
    if (a.latest) {
      const stale = diffDays(a.latest.day, m.endDay);
      cap.append(el("span", stale >= 1 ? "stale" : "", `${short(a.latest.day)}`), el("small", "muted", stale >= 1 ? ` · ${stale} 天前` : " · 今日"));
    } else {
      cap.append(el("span", "stale", "无记录"));
    }
    const act = el("td", "col-act");
    if (openable) {
      const btn = el("button", "btn btn-mini", "登录窗口");
      btn.type = "button";
      btn.dataset.job = "/api/profiles";
      btn.dataset.port = String(a.account.debugPort || "");
      btn.dataset.label = a.label;
      btn.title = `单独打开「${a.label}」的登录窗口，在里面登录该号`;
      if (!a.account.debugPort || jobRunning) btn.disabled = true;
      act.append(btn);
    } else {
      act.append(el("span", "muted", "—"));
    }
    tr.append(name, tier, quota, rem, meterTd, burn, expiry, rw, refresh, cap, act);
    tbody.append(tr);
    // 资源包明细：每个号下面按包分行（各自到期不同）；旧数据无 packs 则不渲染
    for (const pk of (a.account && Array.isArray(a.account.packs) ? a.account.packs : [])) {
      const exp = pk.expires && pk.expires !== "—" ? pk.expires : null;
      const daysLeft = exp ? diffDays(m.endDay, exp) : null;
      const pr = el("tr", "pack-row");
      const td = el("td", "pack-cell");
      td.colSpan = 11;
      const line = el("span", "pack-line");
      line.append(
        el("span", "pack-tag", "资源包"),
        el("span", "pack-src", packSource(pk.source)),
        el("b", null, `${fmt(pk.remaining || 0)} credits`),
        el("span", "muted", ` 到期 ${exp ? short(exp) : "—"}`),
      );
      if (daysLeft !== null && daysLeft <= 14) line.append(el("span", "pack-soon", daysLeft < 0 ? "已过期" : `剩 ${daysLeft} 天`));
      td.append(line);
      pr.append(td);
      tbody.append(pr);
    }
  }
  $("#accounts-empty").hidden = shown > 0;
  $("#accounts-empty").textContent = needle
    ? `没有匹配「${q}」的账号。`
    : "数据集里还没有账号记录。";
  $("#search-hint").textContent = needle
    ? `在 ${m.labels.length} 个账号里筛出 ${shown} 个。`
    : "搜索按标签或账号名称筛下面那张账号表；指标与图表始终覆盖全部账号。";
}

/* 账号表上方一句话：今天还差哪几个号。只报状态，不给动作——桌面端才能签到。 */
function renderRewardNote(m) {
  const box = $("#reward-note");
  if (!box) return;
  const { info, rows, pending, done, unclear, roundOver } = m.reward;
  const isDemo = !!(state.data.meta && state.data.meta.demo);
  if (!info || !rows.length) {
    box.hidden = true;
    box.textContent = "";
    return;
  }
  const parts = [];
  if (isDemo) parts.push("演示数据");
  const round = `${cn(info.window)} 这一轮`;
  if (roundOver && !isDemo) {
    parts.push(`${round}的签到状态已经过期（数据是上一轮的），重新采集后才能判断`);
  } else if (pending.length) {
    parts.push(`${round}还有 ${pending.length} 个号没签到：${pending.join("、")}`);
  } else if (!unclear.length && done.length) {
    parts.push(`${round} ${done.length} 个号都签过了`);
  }
  if (unclear.length && !(roundOver && !isDemo)) parts.push(`另有 ${unclear.length} 个号判断不了：${unclear.join("、")}`);
  parts.push("签到只能在 Qoder 桌面端右上角的浮窗点，看板只显示状态、不代领");
  box.textContent = parts.join(" · ");
  box.dataset.state = pending.length || (roundOver && !isDemo) ? "pending" : "quiet";
  box.hidden = false;
}

/* ---------------- CSV ---------------- */

function csvCell(v) {
  const s = v === null || v === undefined ? "" : String(v);
  return /[",\n\r]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
}

function exportCsv(m) {
  const cols = ["ts", "day", "label", "accountName", "planTier", "planQuota", "planRemaining", "packRemaining", "totalRemaining", "consumed", "refilled", "nextRefresh", "earliestExpiry", "via"];
  const lines = [cols.join(",")];
  const rows = state.data.history.filter((r) => r.day >= m.startDay && r.day <= m.endDay);
  for (const r of rows) lines.push(cols.map((c) => csvCell(r[c])).join(","));
  const blob = new Blob([`${BOM}${lines.join("\r\n")}\r\n`], { type: "text/csv;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const a = el("a");
  a.href = url;
  a.download = `credit-watch_${m.span}d_${m.startDay}_${m.endDay}.csv`;
  document.body.append(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 4000);
  announce(`已导出 ${rows.length} 行（${m.startDay} 至 ${m.endDay}）`);
}

/* ---------------- 其他渲染 ---------------- */

let announceTimer = 0;

/* 弹窗用原生 dialog：ESC 与关闭按钮是浏览器自带的，这里只补"点背景关闭"和焦点归还。 */
function wireDialog(openSel, dlgSel) {
  const opener = $(openSel);
  const dlg = $(dlgSel);
  if (!opener || !dlg) return;
  opener.addEventListener("click", () => {
    dlg.dataset.opener = openSel;
    if (typeof dlg.showModal === "function") dlg.showModal();
    else dlg.setAttribute("open", "");
    const first = $("input:not([disabled]), button:not([value])", dlg);
    if (first) first.focus();
  });
  dlg.addEventListener("click", (e) => {
    if (e.target === dlg) dlg.close();
  });
  dlg.addEventListener("close", () => {
    const back = $(dlg.dataset.opener || "#");
    if (back) back.focus();
    if (dlg.id === "settings-dialog") markSettingsDirty();
  });
}

function announce(text) {
  $("#live-region").textContent = text;
  clearTimeout(announceTimer);
  announceTimer = setTimeout(() => {
    $("#live-region").textContent = "";
  }, 4000);
}

/* 看板 / 设置 两个视图互斥切换：主区只显其一，侧标常驻。 */
function showView(name) {
  const settings = name === "settings";
  const topbar = $(".topbar");
  const main = $("#main");
  if (topbar) topbar.hidden = settings;
  if (main) main.hidden = settings;
  const sv = $("#view-settings");
  if (sv) sv.hidden = !settings;
  if (settings) syncSettingsForm();
  try { window.scrollTo(0, 0); } catch { /* 忽略 */ }
}

function renderChrome(m) {
  const { meta } = state.data;
  $("#side-accounts").textContent = `${m.snapshot.length} 个号`;
  $("#side-latest").textContent = m.freshness.oldest === null ? "—"
    : m.freshness.oldest === 0 ? "今日" : `${m.freshness.oldest} 天前`;
  $("#demo-flag").hidden = !meta.demo;
  const demoNote = $("#foot-demo-note");
  demoNote.hidden = !meta.demo;
  demoNote.textContent = meta.demo
    ? "现在画的是随插件分发的演示数据，跟你的用量无关。在 Qoder 里执行 /credit-start 或直接点「刷新余量数据」，就会换成你本机的真实采集结果。"
    : "";
  const stale = m.perAccountRunway.filter((a) => a.latest && diffDays(a.latest.day, m.endDay) >= 1);
  $("#data-stamp").textContent =
    `${meta.demo ? "本地演示数据" : "本机采集数据"} · 截止 ${m.endDay} · 共 ${state.data.history.length} 条采集记录`;
  const hour = new Date().getHours();
  const hello = hour < 6 ? "凌晨好" : hour < 12 ? "早上好" : hour < 18 ? "下午好" : "晚上好";
  $("h1#greeting-title").textContent = meta.viewer ? `${hello}，${meta.viewer}` : hello;
  $("#greeting-sub").textContent =
    `${m.span} 天区间（${m.startDay} 至 ${m.endDay}）· 合计剩余 ${fmt(m.currentRemaining)} credits · ` +
    `${m.freshness.today}/${m.freshness.list.length} 个号今日采过` +
    `${stale.length ? ` · ${stale.map((a) => `${a.label}已 ${diffDays(a.latest.day, m.endDay)} 天未采集`).join("、")}` : ""}`;
  $("#range-note").textContent =
    `${m.clamped ? `本机记录只有 ${m.span} 天，已收口（可选 ${state.range} 天）· ` : ""}窗口对比基线：${m.hasPrev ? `${m.prevStart} 至 ${m.prevEnd}` : "该区间之前没有采集记录"}`;

  const age = diffDays(m.endDay, day(new Date(Date.now() + 8 * 3600 * 1000)));
  const ageText = age <= 0 ? "今日" : `${age} 天前`;
  const ver = meta.pluginVersion ? `插件 v${meta.pluginVersion}` : "版本未知";
  $("#side-version").textContent = ver;
  $("#log-version").textContent = meta.pluginVersion || "未知";
  const note = $("#refresh-note");
  note.textContent =
    (LOCAL ? "已连上本机服务，按钮可直接触发采集与改配置 · " : "未连接本机服务，当前仅可浏览；用 bin/serve-dashboard.cmd 打开后可直接触发采集与改配置 · ") +
    `数据截止 ${m.endDay}（${ageText}）· ${state.data.history.length} 条采集记录`;
  note.dataset.stale = String(meta.demo || age >= 1);
}

function render() {
  const m = buildModel();
  renderChrome(m);
  renderKpis(m);
  renderArea(m);
  renderDonut(m);
  renderTable(m);
  renderRewardNote(m);
}

/* ---------------- 本机动作（只有本地服务在跑时才存在） ---------------- */

let pollTimer = 0;
// 动作按钮不再是一张固定名单：账号表里每号一个，随数据重画。凡是带 data-job 的都算。
const jobButtons = () => $$("[data-job]");
const BUSY_LABEL = {
  "/api/refresh": "采集中…",
  "/api/rebuild": "重算中…",
  "/api/profiles": "正在打开窗口…",
};
const JOB_DONE = {
  refresh: "采集完成，看板已更新",
  rebuild: "数据已按现有记录重算",
  profiles: "登录窗口已打开，登录完成后回来点刷新余量数据",
  settings: "设置已保存，看板已按新配置重算",
};

function setBusy(btn, on, label) {
  if (!btn) return;
  if (on) {
    if (!btn.dataset.idleLabel) btn.dataset.idleLabel = btn.textContent;
    btn.dataset.busy = "1";
    btn.setAttribute("aria-busy", "true");
    btn.textContent = label || "处理中…";
    btn.disabled = true;
    return;
  }
  delete btn.dataset.busy;
  btn.removeAttribute("aria-busy");
  if (btn.dataset.idleLabel) btn.textContent = btn.dataset.idleLabel;
  btn.disabled = false;
}

let jobRunning = false;

function releaseJobs() {
  jobRunning = false;
  for (const b of jobButtons()) if (b.dataset.busy) setBusy(b, false);
  // 重画表格会造出没有 busy 痕迹的新按钮，这里统一解除"别人被按住"的状态
  for (const b of jobButtons()) b.disabled = b.dataset.job === "/api/profiles" && !b.dataset.port;
}

function holdOthers(keep) {
  for (const other of jobButtons()) {
    if (other !== keep) other.disabled = !!keep;
  }
}

/* 状态固定只占一行加一条细 bar：进度文字再长也只截断，不会把上面那排按钮顶得上下跳。 */
function renderStatus(s) {
  const text = $("#job-text");
  const line = $("#job-status");
  const bar = $("#job-bar");
  const fill = $("#job-fill");
  if (!s || (s.phase === "idle" && !s.running)) {
    text.textContent = "";
    $("#job-count").textContent = "";
    line.dataset.tone = "idle";
    bar.dataset.run = "none";
    fill.style.width = "0%";
    return;
  }
  const last = [...(s.lines || [])].reverse().find((l) => l && l.trim()) || "";
  const full = s.error || last || (s.running ? "处理中…" : s.phase === "done" ? "完成" : "");
  text.textContent = full;
  text.title = full;
  $("#job-count").textContent = s.total > 1 ? `${s.done}/${s.total}` : s.running ? "…" : "";
  line.dataset.tone = s.error ? "err" : s.running ? "busy" : s.phase === "done" ? "ok" : "idle";
  if (s.error) {
    bar.dataset.run = "none";
  } else if (s.running) {
    bar.dataset.run = s.total ? "count" : "indeterminate";
    if (s.total) fill.style.width = `${Math.min(100, Math.round((s.done / s.total) * 100))}%`;
  } else {
    bar.dataset.run = "count";
    fill.style.width = "100%";
  }
}

async function reload() {
  try {
    const res = await fetch(DATA_URL, { cache: "no-store" });
    if (!res.ok) return;
    const json = await res.json();
    if (json && Array.isArray(json.history) && json.meta) {
      state.data = json;
      render();
      syncSettingsForm();
    }
  } catch {
    /* 数据文件还没写出来，下一轮再取 */
  }
}

async function pollStatus() {
  let s = null;
  try {
    const res = await fetch("/api/refresh/status", { headers: { "x-cw-token": LOCAL.token }, cache: "no-store" });
    s = await res.json();
  } catch {
    clearInterval(pollTimer);
    releaseJobs();
    renderStatus({ phase: "failed", running: false, lines: [], error: "本机服务已关闭" });
    announce("本机服务已关闭，无法继续跟踪进度");
    return;
  }
  renderStatus(s);
  if (s.running) return;
  clearInterval(pollTimer);
  releaseJobs();
  if (s.phase === "done") {
    await reload();
    announce(JOB_DONE[s.kind] || "操作完成");
  } else if (s.error) {
    announce(`失败：${s.error}`);
  }
}

const STALE_TOKEN = "本机服务已重启，页面里的令牌过期了——刷新一下页面再点。";

async function startJob(path, btn, body) {
  const idle = btn.dataset.idleLabel || btn.textContent;
  jobRunning = true;
  setBusy(btn, true, BUSY_LABEL[path] || `${idle}…`);
  holdOthers(btn);
  renderStatus({ running: true, kind: null, phase: "running", done: 0, total: 0, lines: [`已触发：${idle}`] });
  try {
    const res = await fetch(path, {
      method: "POST",
      headers: { "content-type": "application/json", "x-cw-token": LOCAL.token },
      body: JSON.stringify(body || {}),
    });
    clearInterval(pollTimer);
    if (res.status === 409) {
      const out = await res.json().catch(() => null);
      setBusy(btn, false);
      holdOthers(null);
      if (out && out.job) renderStatus(out.job);
      announce("已经有一轮在跑，请等它结束");
      pollTimer = setInterval(pollStatus, 700);
      return;
    }
    if (res.status === 401) throw new Error(STALE_TOKEN);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    pollTimer = setInterval(pollStatus, 700);
  } catch (e) {
    releaseJobs();
    const msg = e?.message === STALE_TOKEN ? STALE_TOKEN : `触发失败：${e?.message || e}`;
    renderStatus({ running: false, phase: "failed", lines: [], error: msg });
    announce(msg);
  }
}

/* ---------------- 账号设置 ---------------- */

let settingsBase = null;

function settingsSnapshot() {
  const portInput = $("#set-port");
  return {
    port: portInput ? portInput.value : "",
    accounts: $$("#settings-accounts tbody tr").map((tr) => ({
      label: tr.dataset.label,
      newLabel: $("input[data-field='label']", tr).value,
      accountName: $("input[data-field='name']", tr).value,
    })),
  };
}

function fillSettingsFields() {
  const { accounts } = state.data;
  const tbody = $("#settings-accounts tbody");
  const focusId = document.activeElement && document.activeElement.id;
  tbody.textContent = "";
  for (const [i, a] of (accounts || []).entries()) {
    const tr = el("tr");
    tr.dataset.label = a.label;

    const who = el("th");
    who.scope = "row";
    const sw = el("span", "swatch");
    sw.style.background = SERIES_COLORS[i % SERIES_COLORS.length];
    const cell = el("span", "acct-cell");
    cell.append(sw, el("b", null, a.label));
    who.append(cell);

    const mk = (field, id, value, max, name) => {
      const inp = el("input");
      inp.type = "text";
      inp.maxLength = max;
      inp.dataset.field = field;
      inp.id = id;
      inp.value = value;
      inp.setAttribute("aria-label", name);
      const td = el("td");
      td.append(inp);
      return td;
    };

    tr.append(
      who,
      mk("label", `set-label-${i}`, a.label, 24, "标签"),
      mk("name", `set-name-${i}`, a.accountName || "", 40, "账号名称"),
      el("td", "muted", `${String(a.planTier || "—").replace("PRO_PLUS", "PRO+")} · 最近采集 ${short(a.lastDay) || "—"}`),
    );
    tbody.append(tr);
  }
  if (focusId) {
    const back = document.getElementById(focusId);
    if (back) back.focus();
  }
}

function syncSettingsForm() {
  const local = !!(LOCAL && LOCAL.token);
  const demo = !!(state.data && state.data.meta.demo);
  const canWrite = local && !demo;
  $("#settings-form").hidden = !canWrite;
  $("#settings-off").hidden = local;
  $("#settings-demo").hidden = !(local && demo);
  // 新增账号向导不依赖看板数据，演示数据下照样能用（它写的是你自己的名单）
  $("#register-box").hidden = !local;
  if (!canWrite || !state.data) return;
  $("#port-current").textContent = LOCAL.port ? String(LOCAL.port) : "—";
  const portInput = $("#set-port");
  if (portInput) portInput.value = LOCAL.port ? String(LOCAL.port) : "";
  fillSettingsFields();
  settingsBase = JSON.stringify(settingsSnapshot());
  markSettingsDirty();
}

function markSettingsDirty() {
  if (!settingsBase) return;
  const dirty = JSON.stringify(settingsSnapshot()) !== settingsBase;
  $("#revert-settings").disabled = !dirty;
  const state1 = $("#settings-state");
  if (dirty && state1.textContent !== "有未保存的修改") {
    state1.textContent = "有未保存的修改";
    state1.dataset.tone = "busy";
  } else if (!dirty && state1.textContent === "有未保存的修改") {
    state1.textContent = "";
    state1.dataset.tone = "";
  }
}

async function submitSettings(e) {
  e.preventDefault();
  const btn = $("#save-settings");
  const out1 = $("#settings-state");
  setBusy(btn, true, "保存中…");
  out1.textContent = "写入配置并重算中…";
  out1.dataset.tone = "busy";
  try {
    const res = await fetch("/api/settings", {
      method: "POST",
      headers: { "content-type": "application/json", "x-cw-token": LOCAL.token },
      body: JSON.stringify(settingsSnapshot()),
    });
    const out = await res.json().catch(() => null);
    if (!res.ok) {
      // 401 几乎都是服务重启后旧标签页里的令牌过期，不是他打错了字
      const msg = res.status === 401
        ? STALE_TOKEN
        : (out && out.errors && out.errors.join("；")) || `HTTP ${res.status}`;
      out1.textContent = `没有保存：${msg}`;
      out1.dataset.tone = "err";
      announce(`设置保存失败：${msg}`);
      return;
    }
    if (!out || !out.changes || !out.changes.length) {
      out1.textContent = "没有需要保存的改动";
      out1.dataset.tone = "";
      return;
    }
    const saved = `已保存：${out.changes.join("；")}`;
    out1.textContent = out.rebuildError ? `${saved}，但看板重算失败：${out.rebuildError}` : saved;
    out1.dataset.tone = out.rebuildError ? "err" : "ok";
    announce(out.rebuildError ? `设置已保存，但重算失败：${out.rebuildError}` : `设置已保存（${out.changes.join("；")}），看板已重算`);
    await reload();
    settingsBase = JSON.stringify(settingsSnapshot());
    markSettingsDirty();
  } catch (err) {
    out1.textContent = `保存失败：${err?.message || err}`;
    out1.dataset.tone = "err";
  } finally {
    setBusy(btn, false);
  }
}

/* ---------------- 新增账号向导 ---------------- */

function settingsNote(text, tone) {
  const out = $("#settings-state");
  out.textContent = text;
  out.dataset.tone = tone || "";
  if (text) announce(text);
}

/* 三个向导接口都是"跑完才回应"，所以用按钮自己的 loading 态，不占采集那条进度行。 */
async function callRegister(path, body, btn, busyLabel) {
  setBusy(btn, true, busyLabel);
  try {
    const res = await fetch(path, {
      method: "POST",
      headers: { "content-type": "application/json", "x-cw-token": LOCAL.token },
      body: JSON.stringify(body || {}),
    });
    const out = await res.json().catch(() => null);
    if (res.status === 409) {
      settingsNote("已经有一轮在跑（采集或重算），等它结束再点。", "err");
      return null;
    }
    if (!res.ok) {
      const msg = res.status === 401 ? STALE_TOKEN : (out && out.errors && out.errors.join("；")) || `HTTP ${res.status}`;
      settingsNote(`没成功：${msg}`, "err");
      return null;
    }
    return out;
  } catch (e) {
    settingsNote(`没成功：${e?.message || e}`, "err");
    return null;
  } finally {
    setBusy(btn, false);
  }
}

async function openRegisterWindow() {
  const out = await callRegister("/api/register/open", {}, $("#reg-open"), "开窗口中…");
  if (!out) return;
  settingsNote("干净窗口已打开：在里面登录要新增的那个号，登好之后点「读一下待登记的号」。", "ok");
}

function renderRegisterList(sessions, waiting) {
  const ul = $("#register-list");
  ul.textContent = "";
  const fresh = sessions.filter((s) => !s.registered);
  if (!sessions.length) {
    ul.hidden = true;
    settingsNote(waiting && waiting.length
      ? `有 ${waiting.length} 个窗口开着但还没登录：在那个窗口里登录，再回来点「读一下」。`
      : "一个窗口都没读到。先点「开一个新号窗口」，在里面把号登录上。", "err");
    return;
  }
  for (const s of sessions) {
    const li = el("li");
    const who = el("span", "reg-who");
    who.append(
      el("b", null, s.registered ? s.label : (s.name || "（没拿到登录名）")),
      el("small", "muted", ` ${String(s.tier || "—").replace("PRO_PLUS", "PRO+")}${s.registered ? " · 已在名单" : ""}`),
    );
    li.append(who);
    if (!s.registered) {
      const inp = el("input");
      inp.type = "text";
      inp.maxLength = 24;
      inp.placeholder = "起个标签，如“公司号”";
      inp.dataset.port = String(s.port);
      const btn = el("button", "btn btn-primary", "登记");
      btn.type = "button";
      btn.dataset.port = String(s.port);
      li.append(inp, btn);
    }
    ul.append(li);
  }
  ul.hidden = false;
  const also = waiting && waiting.length ? `另有 ${waiting.length} 个窗口开着但还没登录。` : "";
  settingsNote(fresh.length
    ? `读到 ${fresh.length} 个还没登记的号：填个标签再点「登记」。${also}`
    : `读到的号都已经在名单里了。${also || "要再加一个，就换个号在上一步的窗口里登录。"}`, fresh.length ? "ok" : "");
}

async function scanRegister() {
  const out = await callRegister("/api/register/scan", {}, $("#reg-scan"), "读取中…");
  if (out) renderRegisterList(out.sessions || [], out.waiting || []);
}

async function commitRegister(btn) {
  const li = btn.closest("li");
  const inp = $("input[data-port]", li);
  const label = (inp.value || "").trim();
  if (!label) {
    settingsNote("先给这个号起个标签。", "err");
    inp.focus();
    return;
  }
  const out = await callRegister("/api/register/commit", { items: [{ port: Number(btn.dataset.port), label }] }, btn, "登记中…");
  if (!out) return;
  if (!out.added || !out.added.length) {
    settingsNote("没有需要登记的改动。", "");
    return;
  }
  settingsNote(out.rebuildError
    ? `已登记 ${out.added.join("、")}，但验证采集失败：${out.rebuildError}`
    : `已登记 ${out.added.join("、")}，并顺手采到一次余量——它已经和别的号一样出现在名单里了。`, out.rebuildError ? "err" : "ok");
  li.remove();
  await reload();
}

/* ---------------- 交互装配 ---------------- */

function wire() {
  $$('input[name="range"]').forEach((r) =>
    r.addEventListener("change", () => {
      state.range = Number(r.value);
      try {
        localStorage.setItem(STORE.range, r.value);
      } catch {
        /* 隐私模式写不进去也不影响本次切换 */
      }
      render();
      announce(`时间范围切换为 ${state.range} 天`);
    }),
  );

  const input = $("#q");
  let timer = 0;
  input.addEventListener("input", () => {
    state.q = input.value;
    $("#search-clear").hidden = !input.value;
    clearTimeout(timer);
    timer = setTimeout(render, 120);
  });
  $("#search-form").addEventListener("submit", (e) => e.preventDefault());
  $("#search-clear").addEventListener("click", () => {
    input.value = "";
    state.q = "";
    $("#search-clear").hidden = true;
    input.focus();
    render();
  });

  $("#export-csv").addEventListener("click", () => exportCsv(buildModel()));

  if (LOCAL && LOCAL.token) {
    $$(".actions-row [data-job]").forEach((b) => { b.hidden = false; });
    // 账号表里的按钮随数据重画，逐个绑不住：动作统一在 document 上代管
    document.addEventListener("click", (e) => {
      const b = e.target.closest("[data-job]");
      if (!b || b.disabled) return;
      startJob(b.dataset.job, b, b.dataset.port ? { port: Number(b.dataset.port) } : {});
    });
    $("#settings-form").addEventListener("submit", submitSettings);
    $("#settings-form").addEventListener("input", markSettingsDirty);
    $("#revert-settings").addEventListener("click", () => {
      if (!settingsBase) return;
      const base = JSON.parse(settingsBase);
      const portInput = $("#set-port");
      if (portInput && base.port !== undefined) portInput.value = base.port;
      for (const item of base.accounts) {
        const tr = $$("#settings-accounts tbody tr").find((x) => x.dataset.label === item.label);
        if (!tr) continue;
        $("input[data-field='label']", tr).value = item.newLabel;
        $("input[data-field='name']", tr).value = item.accountName;
      }
      markSettingsDirty();
      announce("已还原未保存的修改");
    });
    $("#reg-open").addEventListener("click", openRegisterWindow);
    $("#reg-scan").addEventListener("click", scanRegister);
    // 待登记列表随扫描重画，按钮挂容器上代管
    $("#register-list").addEventListener("click", (e) => {
      const b = e.target.closest("button[data-port]");
      if (b && !b.disabled) commitRegister(b);
    });
  }

  // 看板 / 设置 视图切换（两个入口：顶部动作区与侧标）
  for (const sel of ["#open-settings", "#open-settings-side"]) {
    const b = $(sel);
    if (b) b.addEventListener("click", () => showView("settings"));
  }
  const back = $("#back-dashboard");
  if (back) back.addEventListener("click", () => showView("dashboard"));

  wireDialog("#open-guide", "#guide-dialog");
  wireDialog("#open-log", "#log-dialog");

  const nav = $("#primary-nav");
  const toggle = $("#nav-toggle");
  toggle.addEventListener("click", () => {
    const open = $("#appbar").dataset.open === "true";
    $("#appbar").dataset.open = String(!open);
    toggle.setAttribute("aria-expanded", String(!open));
  });
  nav.addEventListener("click", (e) => {
    if (!e.target.closest("a[data-nav]")) return;
    showView("dashboard");
    $("#appbar").dataset.open = "false";
    toggle.setAttribute("aria-expanded", "false");
  });

  const links = $$("[data-nav]");
  links.forEach((l, i) => l.setAttribute("aria-current", String(i === 0)));
  const sections = links.map((l) => document.getElementById(l.getAttribute("href").slice(1))).filter(Boolean);
  const spy = new IntersectionObserver(
    (entries) => {
      const visible = entries.filter((en) => en.isIntersecting).sort((a, b) => a.boundingClientRect.top - b.boundingClientRect.top);
      if (!visible.length) return;
      const id = `#${visible[0].target.id}`;
      links.forEach((l) => l.setAttribute("aria-current", String(l.getAttribute("href") === id)));
    },
    { rootMargin: "-110px 0px -60% 0px", threshold: 0 },
  );
  sections.forEach((s) => spy.observe(s));

  let raf = 0;
  const onResize = () => {
    cancelAnimationFrame(raf);
    raf = requestAnimationFrame(() => renderArea(buildModel()));
  };
  window.addEventListener("resize", onResize);
}

async function boot() {
  let json = null;
  try {
    const res = await fetch(DATA_URL, { cache: "no-store" });
    if (res.ok) {
      const parsed = await res.json();
      if (parsed && Array.isArray(parsed.history) && parsed.meta) json = parsed;
    }
  } catch {
    /* 文件读不到，走下面的错误态 */
  }
  if (!json) {
    $("#load-error").hidden = false;
    $("#data-stamp").textContent = "没有可用数据集";
    return;
  }
  state.data = json;
  $$('input[name="range"]').forEach((r) => {
    r.checked = Number(r.value) === state.range;
  });
  wire();
  render();
  syncSettingsForm();
}

boot();
