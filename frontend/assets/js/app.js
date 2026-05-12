// frontend/assets/js/app.js
const API_BASE = (
  window.API_BASE ||
  (window.location.port === "8001"
    ? `${window.location.protocol}//${window.location.hostname}:8082`
    : "")
);
window.API_BASE = API_BASE;

const $ = (id) => document.getElementById(id);

const WORKFLOW_PANEL_BY_STEP = {
  select: "stepUpload",
  model: "stepDispatch",
  privacy: "stepProtect",
  report: "stepDecrypt",
  llm: "stepProtect",
};

function setWorkflowStep(stepName) {
  const activePanelId = WORKFLOW_PANEL_BY_STEP[stepName] || WORKFLOW_PANEL_BY_STEP.select;

  document.querySelectorAll(".step[data-step]").forEach((step) => {
    step.classList.remove("active");
    if (step.dataset.step === stepName) step.classList.add("active");
  });

  document.querySelectorAll(".workflow-panel").forEach((panel) => {
    panel.classList.remove("active-panel");
  });

  const activePanel = $(activePanelId);
  if (activePanel) activePanel.classList.add("active-panel");
}

function renderLlmPromptRoute() {
  return `
    <div class="llmPromptRoute" id="llmPromptRoute">
      <div class="llmRouteArrow" aria-hidden="true">
        <span class="llmRouteStem"></span>
        <span class="llmRouteArrowHead"></span>
      </div>
      <div class="llm-icon-group llmPromptIconGroup" id="llmIconGroup" role="group" aria-label="Target LLM">
        <button class="llm-icon-option" type="button" data-llm-provider="qwen" data-llm-label="Qwen" aria-pressed="false" title="Qwen">
          <img src="./assets/icons/qwen-color.svg" alt="Qwen"/>
        </button>
        <button class="llm-icon-option" type="button" data-llm-provider="deepseek" data-llm-label="DeepSeek Compatible" aria-pressed="false" title="DeepSeek Compatible">
          <img src="./assets/icons/deepseek-color.svg" alt="DeepSeek Compatible"/>
        </button>
        <button class="llm-icon-option" type="button" data-llm-provider="zhipu" data-llm-label="ZhipuAI" aria-pressed="false" title="ZhipuAI">
          <img src="./assets/icons/zhipu-color.svg" alt="ZhipuAI"/>
        </button>
        <button class="llm-icon-option" type="button" data-llm-provider="kimi" data-llm-label="Kimi" aria-pressed="false" title="Kimi">
          <img src="./assets/icons/kimi.svg" alt="Kimi"/>
        </button>
        <button class="llm-icon-option" type="button" data-llm-provider="minimax" data-llm-label="MiniMax" aria-pressed="false" title="MiniMax">
          <img src="./assets/icons/minimax-color.svg" alt="MiniMax"/>
        </button>
        <button class="llm-icon-option" type="button" data-llm-provider="doubao" data-llm-label="Doubao" aria-pressed="false" title="Doubao">
          <img src="./assets/icons/doubao-color.svg" alt="Doubao"/>
        </button>
        <button class="llm-icon-option active" type="button" data-llm-provider="xiaomi-mimo" data-llm-label="Xiaomi MiMo" aria-pressed="true" title="Xiaomi MiMo">
          <img src="./assets/icons/xiaomimimo.svg" alt="Xiaomi MiMo"/>
        </button>
      </div>
      <div class="route-meta" id="llmRouteMeta">Ready to send to Xiaomi MiMo after shuffle.</div>
      <button class="confirm-llm-btn" type="button" id="confirmLlmBtn" disabled>Confirm Xiaomi MiMo and generate report</button>
    </div>
  `;
}

function showSpinner(id, show) {
  const el = $(id);
  if (!el) return;
  el.style.display = show ? "flex" : "none";
}

function setPill(id, text) {
  const el = $(id);
  if (!el) return;
  el.textContent = text;
}

function safeText(x, fallback="—") {
  if (x === null || x === undefined) return fallback;
  const s = String(x).trim();
  return s.length ? s : fallback;
}

function fmtSec(sec) {
  if (sec === null || sec === undefined) return "—";
  return `${sec.toFixed(3)} s`;
}

function renderModalities(modalities) {
  const plainGrid = $("modalityPlainGrid");
  if (!plainGrid) return;
  plainGrid.innerHTML = "";

  // Plaintext data order
  const order = ["Depth", "UWB", "IMU", "CSI", "RGB"];

  const buildHead = (name, m, tagText) => {
    const head = document.createElement("div");
    head.className = "modHead";

    const title = document.createElement("div");
    title.className = "modName";
    title.textContent = name;

    const tag = document.createElement("div");
    tag.className = "modTag";
    tag.textContent = safeText(tagText);

    head.appendChild(title);
    head.appendChild(tag);
    return head;
  };

  for (const name of order) {
    const m = modalities[name] || modalities[name.toLowerCase()] || null;
    if (!m) continue;

    // --- plaintext tile ---
    const tile = document.createElement("div");
    tile.className = "modTile";
    tile.appendChild(buildHead(name, m, m.shape || m.kind || "preview"));

    const prev = document.createElement("div");
    prev.className = "modPreview";
    const img = document.createElement("img");
    img.alt = `${name} preview`;
    img.src = m.preview_png ? `data:image/png;base64,${m.preview_png}` : "";
    // Add special class for Depth to control size
    if (name === "Depth") {
      img.className = "depthImg";
    }
    prev.appendChild(img);
    tile.appendChild(prev);

    const txt = document.createElement("div");
    txt.className = "modText";
    txt.textContent = safeText(m.plaintext_excerpt);
    tile.appendChild(txt);
    plainGrid.appendChild(tile);
  }
}

function renderCluster(clusterModels, assignments) {
  const wrap = $("modelCluster");
  if (!wrap) return;
  wrap.innerHTML = "";

  const assignedSet = new Set((assignments || []).map(x => x.model_id));
  const byModel = {};
  for (const a of (assignments || [])) byModel[a.model_id] = a;

  for (const m of clusterModels || []) {
    const card = document.createElement("div");
    card.className = "modelCard " + (assignedSet.has(m.id) ? "active" : "inactive");

    const n = document.createElement("div");
    n.className = "modelName";
    n.textContent = m.title;

    const s = document.createElement("div");
    s.className = "modelSub";
    s.textContent = m.subtitle;

    card.appendChild(n);
    card.appendChild(s);

    if (assignedSet.has(m.id)) {
      const b = document.createElement("div");
      b.className = "modelBadge";
      const a = byModel[m.id];
      b.textContent = `${a.input_modality} → ${a.tool}`;
      card.appendChild(b);
    }

    wrap.appendChild(card);
  }
}

function renderResults(rows) {
  const table = $("resultTable");
  if (!table) {
    console.warn("resultTable element not found!");
    return;
  }
  const tbody = table.querySelector("tbody");
  if (!tbody) {
    console.warn("tbody not found in resultTable!");
    return;
  }
  tbody.innerHTML = "";

  console.log("renderResults called with rows:", rows);

  if (!rows || rows.length === 0) {
    const tr = document.createElement("tr");
    const td = document.createElement("td");
    td.colSpan = 4;
    td.textContent = "No results available";
    td.style.textAlign = "center";
    td.style.color = "var(--muted)";
    tr.appendChild(td);
    tbody.appendChild(tr);
    return;
  }

  for (const r of rows) {
    const tr = document.createElement("tr");

    const tdModel = document.createElement("td");
    tdModel.textContent = safeText(r.model);

    const tdInput = document.createElement("td");
    tdInput.textContent = safeText(r.input_modality);

    const tdScore = document.createElement("td");
    const scoreVal = (r.score === null || r.score === undefined) ? "—" : Number(r.score).toFixed(2);
    tdScore.textContent = scoreVal;

    const tdStatus = document.createElement("td");
    tdStatus.textContent = safeText(r.status);

    tr.appendChild(tdModel);
    tr.appendChild(tdInput);
    tr.appendChild(tdScore);
    tr.appendChild(tdStatus);

    tbody.appendChild(tr);
  }
}

// -----------------------------
// Report rendering (vanilla SVG)
// -----------------------------
function escHtml(s) {
  return String(s)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll("\"", "&quot;")
    .replaceAll("'", "&#39;");
}

function svgSpark(values, opts = {}) {
  const w = opts.w || 360;
  const h = opts.h || 120;
  const pad = opts.pad || 10;
  const v = (values || []).map(Number).filter(x => Number.isFinite(x));
  if (!v.length) return `<svg viewBox="0 0 ${w} ${h}"></svg>`;
  const min = Math.min(...v);
  const max = Math.max(...v);
  const dx = (w - 2 * pad) / Math.max(1, v.length - 1);
  const normY = (x) => {
    if (max - min < 1e-9) return h / 2;
    return pad + (h - 2 * pad) * (1 - (x - min) / (max - min));
  };
  let d = "";
  for (let i = 0; i < v.length; i++) {
    const x = pad + i * dx;
    const y = normY(v[i]);
    d += (i === 0 ? "M" : "L") + x.toFixed(2) + " " + y.toFixed(2) + " ";
  }
  // area fill
  const dArea = `${d}L ${pad + (v.length - 1) * dx} ${h - pad} L ${pad} ${h - pad} Z`;
  return `
  <svg viewBox="0 0 ${w} ${h}" role="img" aria-label="trend">
    <defs>
      <linearGradient id="g" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0%" stop-color="#0f172a" stop-opacity="0.18"/>
        <stop offset="100%" stop-color="#0f172a" stop-opacity="0.02"/>
      </linearGradient>
    </defs>
    <rect x="1" y="1" width="${w-2}" height="${h-2}" rx="12" fill="#fbfcff" stroke="rgba(230,232,239,.8)"/>
    <path d="${dArea}" fill="url(#g)"/>
    <path d="${d}" fill="none" stroke="#0f172a" stroke-width="2.4" stroke-linecap="round"/>
  </svg>`;
}

function svgGauge(prob, label) {
  const p = Math.max(0, Math.min(1, Number(prob)));
  const gaugeLabel = label || "Score";
  const w = 360, h = 140;
  const pad = 20;
  const barHeight = 40;
  const barY = 60;
  const barX = pad;
  const barWidth = w - 2 * pad;

  const pct = Math.round(p * 100);
  const fillWidth = barWidth * p;

  // Color based on health index level
  const barColor = p >= 0.7 ? "#22c55e" : (p >= 0.4 ? "#f97316" : "#ef4444");
  const barColorLight = p >= 0.7 ? "rgba(34, 197, 94, 0.15)" : (p >= 0.4 ? "rgba(249, 115, 22, 0.15)" : "rgba(239, 68, 68, 0.15)");

  // Health index indicators (three non-hierarchical bands)
  const lowEnd = barX + barWidth * 0.4;
  const highStart = barX + barWidth * 0.7;

  return `
  <svg viewBox="0 0 ${w} ${h}" role="img" aria-label="${escHtml(gaugeLabel)}">
    <rect x="1" y="1" width="${w-2}" height="${h-2}" rx="12" fill="#ffffff" stroke="rgba(230,232,239,.8)"/>

    <!-- Health-index band backgrounds -->
    <rect x="${barX}" y="${barY}" width="${barWidth * 0.4}" height="${barHeight}" fill="rgba(239, 68, 68, 0.08)" rx="8"/>
    <rect x="${lowEnd}" y="${barY}" width="${barWidth * 0.3}" height="${barHeight}" fill="rgba(249, 115, 22, 0.08)"/>
    <rect x="${highStart}" y="${barY}" width="${barWidth * 0.3}" height="${barHeight}" fill="rgba(34, 197, 94, 0.08)" rx="8"/>

    <!-- Background bar -->
    <rect x="${barX}" y="${barY}" width="${barWidth}" height="${barHeight}" fill="rgba(15,23,42,.06)" stroke="rgba(15,23,42,.12)" stroke-width="1" rx="8"/>

    <!-- Progress fill -->
    <rect x="${barX}" y="${barY}" width="${fillWidth.toFixed(2)}" height="${barHeight}" fill="${barColor}" rx="8"/>

    <!-- Zone labels -->
    <text x="${barX + barWidth * 0.2}" y="${barY + barHeight + 18}" text-anchor="middle" font-size="10" font-weight="700" fill="#ef4444">Zone 1</text>
    <text x="${barX + barWidth * 0.55}" y="${barY + barHeight + 18}" text-anchor="middle" font-size="10" font-weight="700" fill="#f97316">Zone 2</text>
    <text x="${barX + barWidth * 0.85}" y="${barY + barHeight + 18}" text-anchor="middle" font-size="10" font-weight="700" fill="#22c55e">Zone 3</text>

    <!-- Percentage and label -->
    <text x="${w / 2}" y="35" text-anchor="middle" font-size="32" font-weight="900" fill="#0f172a">${pct}%</text>
    <text x="${w / 2}" y="50" text-anchor="middle" font-size="13" font-weight="700" fill="rgba(15,23,42,.6)">${escHtml(gaugeLabel)}</text>

    <!-- Threshold lines -->
    <line x1="${lowEnd}" y1="${barY - 3}" x2="${lowEnd}" y2="${barY + barHeight + 3}" stroke="rgba(15,23,42,.2)" stroke-width="1.5" stroke-dasharray="3,3"/>
    <line x1="${highStart}" y1="${barY - 3}" x2="${highStart}" y2="${barY + barHeight + 3}" stroke="rgba(15,23,42,.2)" stroke-width="1.5" stroke-dasharray="3,3"/>
  </svg>`;
}

function svgBarVitals(payload) {
  const labels = payload?.labels || [];
  const values = payload?.values || [];
  const ranges = payload?.ranges || {};
  const w = 360, h = 180, pad = 16;
  const n = Math.max(1, labels.length);
  const gap = 10;
  const palette = ["#7c3aed", "#06b6d4", "#f97316", "#22c55e", "#ef4444", "#eab308"];
  const bw = (w - 2 * pad - (n - 1) * gap) / n;

  const norm = (lab, val) => {
    const r = ranges[lab] || null;
    if (!r) return 0.5;
    const lo = r[0], hi = r[1];
    const v = Number(val);
    if (!Number.isFinite(v) || hi - lo < 1e-9) return 0.5;
    // map [lo..hi] to [0.25..0.85], allow out-of-range
    const t = (v - lo) / (hi - lo);
    return Math.max(0.05, Math.min(0.95, 0.25 + 0.60 * t));
  };

  let bars = "";
  for (let i = 0; i < labels.length; i++) {
    const lab = labels[i];
    const v = values[i];
    const t = norm(lab, v);
    const x = pad + i * (bw + gap);
    const y0 = pad + 18;
    const h0 = h - y0 - pad - 18;
    const bh = h0 * t;
    const y = y0 + (h0 - bh);
    const r = ranges[lab] || null;
    const ref = r ? `${r[0]}–${r[1]}` : "";

    // reference band
    if (r) {
      const refLo = Math.max(0.05, Math.min(0.95, 0.25 + 0.60 * ((r[0] - r[0]) / (r[1] - r[0] || 1))));
      const refHi = Math.max(0.05, Math.min(0.95, 0.25 + 0.60 * ((r[1] - r[0]) / (r[1] - r[0] || 1))));
      const bandY = y0 + (h0 - h0 * refHi);
      const bandH = Math.max(4, h0 * (refHi - refLo));
      bars += `<rect x="${x.toFixed(2)}" y="${bandY.toFixed(2)}" width="${bw.toFixed(2)}" height="${bandH.toFixed(2)}" rx="8" fill="rgba(15,23,42,.06)"/>`;
    }

    bars += `
      <rect x="${x.toFixed(2)}" y="${y.toFixed(2)}" width="${bw.toFixed(2)}" height="${bh.toFixed(2)}" rx="10" fill="${palette[i % palette.length]}" fill-opacity="0.88"/>
      <text x="${(x + bw/2).toFixed(2)}" y="${(h - pad).toFixed(2)}" text-anchor="middle" font-size="10" font-weight="900" fill="rgba(15,23,42,.72)">${escHtml(lab)}</text>
      <text x="${(x + bw/2).toFixed(2)}" y="${(y - 6).toFixed(2)}" text-anchor="middle" font-size="10" font-weight="900" fill="${palette[i % palette.length]}">${Number.isFinite(Number(v)) ? Number(v).toFixed(0) : "—"}</text>
      ${ref ? `<text x="${(x + bw/2).toFixed(2)}" y="${(h - pad - 12).toFixed(2)}" text-anchor="middle" font-size="9" fill="rgba(15,23,42,.55)">${escHtml(ref)}</text>` : ""}
    `;
  }

  return `
  <svg viewBox="0 0 ${w} ${h}" role="img" aria-label="vitals">
    <rect x="1" y="1" width="${w-2}" height="${h-2}" rx="12" fill="#ffffff" stroke="rgba(230,232,239,.8)"/>
    ${bars}
  </svg>`;
}

function svgRadar(payload) {
  const labels = payload?.labels || [];
  const values = payload?.values || [];
  const w = 360, h = 260;
  const cx = 180, cy = 135;
  const r = 92;
  const n = Math.max(3, labels.length);
  const ang0 = -Math.PI / 2;

  const pt = (i, rr) => {
    const a = ang0 + i * (2 * Math.PI / n);
    return [cx + rr * Math.cos(a), cy + rr * Math.sin(a)];
  };

  // grid
  let grid = "";
  for (const k of [0.25, 0.5, 0.75, 1.0]) {
    let d = "";
    for (let i = 0; i < n; i++) {
      const [x, y] = pt(i, r * k);
      d += (i === 0 ? "M" : "L") + x.toFixed(2) + " " + y.toFixed(2) + " ";
    }
    d += "Z";
    grid += `<path d="${d}" fill="none" stroke="rgba(15,23,42,.10)"/>`;
  }

  // axes + labels
  let axes = "";
  for (let i = 0; i < n; i++) {
    const [x, y] = pt(i, r);
    axes += `<path d="M ${cx} ${cy} L ${x.toFixed(2)} ${y.toFixed(2)}" stroke="rgba(15,23,42,.10)"/>`;
    const [lx, ly] = pt(i, r + 20);
    axes += `<text x="${lx.toFixed(2)}" y="${ly.toFixed(2)}" text-anchor="middle" font-size="10" font-weight="900" fill="rgba(15,23,42,.72)">${escHtml(labels[i] || "")}</text>`;
  }

  // polygon
  let d = "";
  for (let i = 0; i < n; i++) {
    const v = Number(values[i] ?? 0);
    const t = Math.max(0, Math.min(100, v)) / 100;
    const [x, y] = pt(i, r * t);
    d += (i === 0 ? "M" : "L") + x.toFixed(2) + " " + y.toFixed(2) + " ";
  }
  d += "Z";

  return `
  <svg viewBox="0 0 ${w} ${h}" role="img" aria-label="radar">
    <rect x="1" y="1" width="${w-2}" height="${h-2}" rx="12" fill="#fbfcff" stroke="rgba(230,232,239,.8)"/>
    ${grid}
    ${axes}
    <path d="${d}" fill="rgba(124,58,237,.18)" stroke="#7c3aed" stroke-width="2"/>
  </svg>`;
}

function svgDonut(chart, opts = {}) {
  const labels = chart?.labels || [];
  const values = (chart?.values || []).map(x => Math.max(0, Number(x) || 0));
  const sum = values.reduce((a, b) => a + b, 0) || 1;

  const w = opts.w || 360;
  const h = opts.h || 160;
  const cx = w / 2;
  const cy = h / 2;
  const r = Math.min(w, h) * 0.38;
  const stroke = Math.max(14, r * 0.28);

  const palette = ["#7c3aed", "#06b6d4", "#f97316", "#22c55e", "#ef4444", "#eab308"];

  let a0 = -Math.PI / 2;
  let segs = "";
  for (let i = 0; i < values.length; i++) {
    const frac = values[i] / sum;
    const a1 = a0 + frac * Math.PI * 2;
    const x0 = cx + r * Math.cos(a0), y0 = cy + r * Math.sin(a0);
    const x1 = cx + r * Math.cos(a1), y1 = cy + r * Math.sin(a1);
    const large = (a1 - a0) > Math.PI ? 1 : 0;
    const d = `M ${x0.toFixed(2)} ${y0.toFixed(2)} A ${r.toFixed(2)} ${r.toFixed(2)} 0 ${large} 1 ${x1.toFixed(2)} ${y1.toFixed(2)}`;
    segs += `<path d="${d}" fill="none" stroke="${palette[i % palette.length]}" stroke-width="${stroke}" stroke-linecap="round"/>`;
    a0 = a1;
  }

  // Legend
  const legendY = h - 10;
  const legendEntries = labels.slice(0, values.length).map((lab, i) => {
    const pct = (100 * (values[i] / sum)).toFixed(0) + "%";
    return { label: lab, pct, color: palette[i % palette.length] };
  });
  const items = opts.compactLegend
    ? legendEntries.map((entry) => (
      `<span class="compactLegendItem"><span class="legendDot" style="background:${entry.color}"></span>${escHtml(entry.label)} <strong>${entry.pct}</strong></span>`
    )).join("")
    : legendEntries.map((entry) => (
      `<span class="legendItem"><span class="legendDot" style="background:${entry.color}"></span>${escHtml(entry.label)} <span class="mono">${entry.pct}</span></span>`
    )).join("");

  return `
  <div class="donutWrap">
    <svg width="${w}" height="${h}" viewBox="0 0 ${w} ${h}" aria-label="Donut chart">
      <circle cx="${cx}" cy="${cy}" r="${r}" fill="none" stroke="rgba(2,6,23,.08)" stroke-width="${stroke}"/>
      ${segs}
      <circle cx="${cx}" cy="${cy}" r="${r - stroke * 0.9}" fill="#fff"/>
      <text x="${cx}" y="${cy + 6}" font-size="14" text-anchor="middle" fill="#0f172a" font-weight="700">Activity</text>
    </svg>
    <div class="${opts.compactLegend ? "compactLegend" : "legend"}">${items}</div>
  </div>`;
}

function svgStackedMix(chart) {
  const labels = chart?.labels || [];
  const values = (chart?.values || []).map((value) => Math.max(0, Number(value) || 0));
  const sum = values.reduce((acc, value) => acc + value, 0) || 1;
  const palette = ["#7c3aed", "#06b6d4", "#f97316", "#22c55e", "#ef4444", "#eab308"];
  let x = 0;
  const segments = values.map((value, index) => {
    const width = (value / sum) * 100;
    const segment = `<rect x="${x}" y="42" width="${width}" height="34" rx="8" fill="${palette[index % palette.length]}"></rect>`;
    x += width;
    return segment;
  }).join("");
  const legend = labels.map((label, index) => `<span class="legendItem"><span class="legendDot" style="background:${palette[index % palette.length]}"></span>${escHtml(label)}</span>`).join("");
  return `<div class="sectionSvg"><svg viewBox="0 0 100 118" preserveAspectRatio="none">${segments}</svg><div class="legend">${legend}</div></div>`;
}

function svgRecoveryBars(chart) {
  const labels = chart?.labels || [];
  const values = chart?.values || [];
  const rows = labels.map((label, index) => {
    const value = Math.max(0, Math.min(100, Number(values[index]) || 0));
    return `
      <div class="recoveryRow">
        <span>${escHtml(label)}</span>
        <div class="recoveryTrack"><i style="width:${value}%"></i></div>
        <strong>${Math.round(value)}</strong>
      </div>
    `;
  }).join("");
  return `<div class="recoveryBars">${rows}</div>`;
}

function svgRiskTiles(chart) {
  const tiles = Array.isArray(chart?.tiles) ? chart.tiles : [];
  const html = tiles.length
    ? tiles.map((tile) => `
      <div class="riskTile ${statusClass(tile.status)}">
        <span>${escHtml(tile.label || "Image")}</span>
        <strong>${tile.score === undefined || tile.score === null ? "—" : escHtml(String(tile.score))}</strong>
        <em>${escHtml(tile.status || "normal")}</em>
      </div>
    `).join("")
    : `<div class="riskTile muted"><span>No image signals</span><strong>—</strong><em>missing</em></div>`;
  return `<div class="riskTileGrid">${html}</div>`;
}

function svgStabilityChart(chart) {
  const score = Math.max(0, Math.min(1, Number(chart?.score) || 0));
  const trend = Array.isArray(chart?.trend) ? chart.trend : [score, score, score];
  const points = trend.map((value, index) => {
    const x = 18 + index * (324 / Math.max(1, trend.length - 1));
    const y = 120 - Math.max(0, Math.min(1, Number(value) || 0)) * 86;
    return `${x.toFixed(1)},${y.toFixed(1)}`;
  }).join(" ");
  const color = score >= 0.7 ? "#22c55e" : score >= 0.4 ? "#f97316" : "#ef4444";
  return `
    <svg viewBox="0 0 360 150" role="img" aria-label="stability trend">
      <rect x="1" y="1" width="358" height="148" rx="12" fill="#fff" stroke="rgba(230,232,239,.9)"/>
      <rect x="18" y="34" width="${(324 * score).toFixed(1)}" height="18" rx="9" fill="${color}"/>
      <rect x="18" y="34" width="324" height="18" rx="9" fill="none" stroke="rgba(15,23,42,.12)"/>
      <polyline points="${points}" fill="none" stroke="#0f172a" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/>
      <text x="18" y="26" font-size="12" font-weight="800" fill="#0f172a">Stability ${Math.round(score * 100)}%</text>
    </svg>
  `;
}

function compactStabilityCard(chart) {
  const score = Math.max(0, Math.min(1, Number(chart?.score) || 0));
  const drift = Number(chart?.drift);
  const variability = Number(chart?.gait_variability);
  const extras = [
    Number.isFinite(drift) ? `Drift ${drift.toFixed(2)}` : "",
    Number.isFinite(variability) ? `Var ${variability.toFixed(2)}` : "",
  ].filter(Boolean).join(" · ");
  return `
    <div class="compactStability">
      <div class="compactStabilityScore">${Math.round(score * 100)}%</div>
      <div class="compactStabilityTrack"><i style="width:${Math.round(score * 100)}%"></i></div>
      ${extras ? `<div class="compactStabilityMeta">${escHtml(extras)}</div>` : ""}
    </div>
  `;
}

function statusClass(status) {
  const s = String(status || "").toLowerCase();
  if (s === "attention" || s === "high" || s === "low") return "attention";
  if (s === "watch" || s === "moderate") return "watch";
  return "stable";
}

function modalityTag(label) {
  return `<span class="sourceTag">${escHtml(String(label || "").toUpperCase())}</span>`;
}

function metricMiniCard(metric) {
  const value = metric?.value === null || metric?.value === undefined
    ? "—"
    : (Number.isFinite(Number(metric.value))
      ? Number(metric.value).toFixed(Number(metric.value) % 1 === 0 ? 0 : 2)
      : escHtml(metric.value));
  const unit = metric?.unit ? `<span>${escHtml(metric.unit)}</span>` : "";
  return `
    <div class="miniMetric ${statusClass(metric?.status)}">
      <div class="miniMetricName">${escHtml(metric?.name || "")}</div>
      <div class="miniMetricValue">${value}${unit}</div>
      ${metric?.ref ? `<div class="miniMetricRef">${escHtml(metric.ref)}</div>` : ""}
    </div>
  `;
}

function renderSectionChart(section, options = {}) {
  const type = section?.chart_type;
  const chart = section?.chart || {};
  if (options.compact && type === "stability") return compactStabilityCard(chart);
  if (type === "reference_bars") return svgBarVitals(chart);
  if (type === "radar") return svgRadar(chart);
  if (section?.id === "activity" || type === "donut") {
    const size = options.compact ? {w: 180, h: 180} : {w: 220, h: 120};
    return svgDonut(chart, {...size, compactLegend: options.compact});
  }
  if (type === "stacked_mix") return svgStackedMix(chart);
  if (type === "recovery_bars") return svgRecoveryBars(chart);
  if (type === "risk_tiles") return svgRiskTiles(chart);
  return svgStabilityChart(chart);
}

function statusBadge(overall) {
  const s = String(overall || "").toLowerCase();
  if (s === "attention") return { text: "Attention", dot: "#b91c1c" };
  if (s === "watch") return { text: "Watch", dot: "#a16207" };
  return { text: "Stable", dot: "#0f172a" };
}

// Store detailed analysis data
let detailedAnalysisData = {};

function setupAnalysisTabs() {
  const tabBtns = document.querySelectorAll('.tabBtn');
  tabBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      // Remove active class from all buttons
      tabBtns.forEach(b => b.classList.remove('active'));
      // Add active class to clicked button
      btn.classList.add('active');
      // Render the selected modality's analysis
      const modality = btn.getAttribute('data-tab');
      renderDetailedAnalysis(modality);
    });
  });
}

function renderDetailedAnalysis(modality) {
  const panel = $('analysisPanel');
  if (!panel) return;

  const mod = modality.toUpperCase();
  const data = detailedAnalysisData[mod];

  if (!data) {
    panel.innerHTML = '<div class="hint">No detailed analysis data available for this modality.</div>';
    return;
  }

  let html = '';

  // FFT spectrum chart
  if (data.fft_png) {
    html += `
      <div class="analysisChart">
        <div class="chartLabel">Frequency Spectrum Analysis (FFT)</div>
        <img src="data:image/png;base64,${data.fft_png}" alt="${mod} FFT">
      </div>
    `;
  }

  // Spectrogram (only for CSI)
  if (data.spectrogram_png) {
    html += `
      <div class="analysisChart">
        <div class="chartLabel">Time-Frequency Spectrogram</div>
        <img src="data:image/png;base64,${data.spectrogram_png}" alt="${mod} Spectrogram">
      </div>
    `;
  }

  if (!html) {
    html = '<div class="hint">No frequency analysis available for this modality.</div>';
  }

  panel.innerHTML = html;
}

let privacyAnimationTimer = null;
let privacyAnimationFrame = null;
let privacyAnimationRenderId = 0;

function renderPrivacyProtection(privacy) {
  const panel = $("privacyPanel");
  if (!panel) return;

  if (privacyAnimationFrame) {
    window.cancelAnimationFrame(privacyAnimationFrame);
    privacyAnimationFrame = null;
  }
  if (privacyAnimationTimer) {
    window.clearTimeout(privacyAnimationTimer);
    privacyAnimationTimer = null;
  }
  panel.classList.remove("is-playing", "is-idle", "is-complete", "step-by-step");

  if (!privacy || !privacy.enabled) {
    panel.innerHTML = '<div class="hint">Protected privacy data is unavailable.</div>';
    return;
  }

  const protectedSummary = privacy.protected_llm_summary_preview || {};
  const summaryMetrics = protectedSummary.metrics || {};
  const domain = protectedSummary.domain || "healthcare";
  const isFinanceDomain = domain === "finance";
  const privacyMetricText = isFinanceDomain
    ? "Model scores / financial buckets / risk profile"
    : "Model scores / physiological metrics / risk profile";
  const distributionSummary = privacy.distribution_summary || {};
  const valueHistogram = Array.isArray(distributionSummary.value_histogram)
    ? distributionSummary.value_histogram
    : [];
  const scatterPoints = Array.isArray(distributionSummary.scatter_points)
    ? distributionSummary.scatter_points
    : [];
  const targetPoint = distributionSummary.target_point || {};
  const tokenFlow = privacy.token_flow || distributionSummary.token_flow || {};
  const rawPoolSize = privacy.database_size ?? privacy.pool_size ?? 101;
  const parsedPoolSize = Number(rawPoolSize);
  const poolSize = Math.min(
    Number.isFinite(parsedPoolSize) ? Math.max(0, Math.floor(parsedPoolSize)) : 101,
    101
  );
  const numericBars = valueHistogram.length ? valueHistogram : [
    { start: 0.08, end: 0.18, count: 7 },
    { start: 0.18, end: 0.28, count: 13 },
    { start: 0.28, end: 0.38, count: 21 },
    { start: 0.38, end: 0.48, count: 26 },
    { start: 0.48, end: 0.58, count: 18 },
    { start: 0.58, end: 0.68, count: 9 },
    { start: 0.68, end: 0.78, count: 5 },
    { start: 0.78, end: 0.88, count: 2 },
  ];
  const maxBucketCount = Math.max(1, ...numericBars.map((bucket) => Number(bucket.count || 0)));
  const histogramBars = numericBars.map((bucket) => {
    const height = Math.max(14, Math.round((Number(bucket.count || 0) / maxBucketCount) * 70));
    const center = (Number(bucket.start || 0) + Number(bucket.end || 0)) / 2;
    const hue = Math.max(8, Math.min(140, Math.round(140 - center * 90)));
    const barColor = `hsl(${hue} 74% 46%)`;
    const rangeLabel = `${Math.round(Number(bucket.start || 0) * 100)}-${Math.round(Number(bucket.end || 0) * 100)}%`;
    return `
      <div class="distributionBar" style="--bar-h:${height}px; --bar-color:${barColor}">
        <span>${escHtml(bucket.count ?? "0")}</span>
        <em>${escHtml(rangeLabel)}</em>
      </div>
    `;
  }).join("");
  const scatterSource = scatterPoints.length ? scatterPoints : Array.from({ length: 28 }, (_, index) => ({
    x: 0.08 + ((index * 17) % 84) / 100,
    y: 0.25 + ((index * 23) % 55) / 100,
    bucket: index % 5 === 0 ? "elevated" : index % 2 === 0 ? "attention" : "low",
    target: false,
  }));
  const rawXs = scatterSource.map((point) => Number(point.x ?? 0.5));
  const rawYs = scatterSource.map((point) => Number(point.y ?? 0.5));
  const xMin = Math.min(...rawXs);
  const xMax = Math.max(...rawXs);
  const yMin = Math.min(...rawYs);
  const yMax = Math.max(...rawYs);
  const xSpan = Math.max(1e-4, xMax - xMin);
  const ySpan = Math.max(1e-4, yMax - yMin);

  const scatterDots = scatterSource.map((point, index) => {
    const rawX = Number(point.x ?? 0.5);
    const rawY = Number(point.y ?? 0.5);
    const xNorm = (rawX - xMin) / xSpan;
    const yNorm = (rawY - yMin) / ySpan;
    const jitterX = (((index * 37) % 11) - 5) * 0.003;
    const jitterY = (((index * 19) % 11) - 5) * 0.003;
    const x = Math.max(4, Math.min(96, (0.06 + (xNorm + jitterX) * 0.88) * 100));
    const y = Math.max(7, Math.min(93, 100 - (0.08 + (yNorm + jitterY) * 0.84) * 100));
    const isTarget = Boolean(point.target) || point.label === targetPoint.label;
    const dotColor = isTarget
      ? "#2563eb"
      : `hsl(${Math.max(10, Math.min(145, Math.round(145 - Number(point.x ?? 0.5) * 90)))} 70% 44%)`;
    return `<span class="distributionDot ${isTarget ? "targetDot" : ""}" style="--x:${x}%; --y:${y}%; --dot-color:${dotColor}; --i:${index}"></span>`;
  }).join("");
  const targetX = Math.max(3, Math.min(96, Number(targetPoint.x ?? 0.56) * 100));
  const targetY = Math.max(6, Math.min(92, 100 - Number(targetPoint.y ?? 0.41) * 100));
  const distributionVisual = `
    <div class="distributionPanel">
      <div class="distributionHead">
        <strong>Synthetic Database Distribution</strong>
        <span>${escHtml(String(privacy.synthetic_record_count || Math.max(0, poolSize - 1)))} fake + target</span>
      </div>
      <div class="distributionBars">${histogramBars}</div>
      <div class="distributionScatter" aria-label="synthetic database distribution">
        ${scatterDots}
        <span class="targetLocator" style="--x:${targetX}%; --y:${targetY}%">target hidden in distribution</span>
      </div>
    </div>
  `;

  const shuffleOrderPreview = Array.isArray(privacy.shuffle_order_preview)
    ? privacy.shuffle_order_preview.map((label) => safeText(label)).filter(Boolean).slice(0, 6)
    : [];
  const fallbackOrderLabels = Array.from({ length: 6 }, (_, index) => `Synthetic Record ${String(index + 1).padStart(2, "0")}`);
  const selectedRecordText = safeText(privacy.selected_record_label || targetPoint.label, "");
  const orderLabels = (shuffleOrderPreview.length ? shuffleOrderPreview : fallbackOrderLabels).slice(0, 6);
  const normalizedOrderLabels = orderLabels.map((label) => safeText(label));
  if (selectedRecordText && !normalizedOrderLabels.includes(selectedRecordText)) {
    normalizedOrderLabels[Math.max(0, normalizedOrderLabels.length - 1)] = selectedRecordText;
  }
  const selectedRecordTextSafe = safeText(selectedRecordText, orderLabels[0] || "Synthetic Record");
  const selectedOrderIndexRaw = Number(privacy.selected_record_index);
  const matchedSelectedIndex = normalizedOrderLabels.findIndex((label) => label === selectedRecordTextSafe);
  const clampedOrderIndex =
    Number.isInteger(selectedOrderIndexRaw) && selectedOrderIndexRaw >= 0 && normalizedOrderLabels.length
      ? Math.min(selectedOrderIndexRaw, normalizedOrderLabels.length - 1)
      : -1;
  const selectedOrderIndex = clampedOrderIndex >= 0
    ? clampedOrderIndex
    : (matchedSelectedIndex >= 0 ? matchedSelectedIndex : 0);
  const orderLabelsFinal = normalizedOrderLabels;
  const orderChips = orderLabelsFinal.map((label, orderIndex) => (
    `<span class="orderChip ${orderIndex === selectedOrderIndex ? "orderChipSelected" : ""}" style="--i:${orderIndex}">
      ${escHtml(label)}
    </span>`
  )).join("");
  const selectedRecordLabel = escHtml(safeText(
    privacy.selected_record_label,
    orderLabelsFinal[selectedOrderIndex] || orderLabelsFinal[0] || "Synthetic Record"
  ));
  const rawPrompt = safeText(privacy.plaintext_prompt || privacy.llm_prompt, "");
  const plaintextPromptHtml = rawPrompt
    ? `<details class="cipher-panel reportPromptPanel">
      <summary>Plaintext Prompt (sent to untrusted LLM)</summary>
      <pre class="v">${escHtml(rawPrompt)}</pre>
    </details>`
    : "";
  const llmPromptRouteHtml = renderLlmPromptRoute();
  const summaryBucketRows = isFinanceDomain
    ? [
        ["Cashflow Burden", summaryMetrics.cashflow_burden || "masked"],
        ["Loan Stress", summaryMetrics.loan_stress || "masked"],
      ]
    : [
        ["Blood Pressure", summaryMetrics.blood_pressure || "masked"],
        ["Sleep Efficiency", summaryMetrics.sleep_efficiency || "masked"],
      ];
  const summaryBucketHtml = summaryBucketRows.map(([label, value]) => (
    `<span>${escHtml(label)}: ${escHtml(value)}</span>`
  )).join("");
  const bucketedSummaryThumb = `
    <div class="bucketedSummaryCard protectedReportThumb">
      <div class="protectedReportHead">
        <strong>Bucketed Summary</strong>
      </div>
      <div class="protectedReportSource">
        <span>${selectedRecordLabel}</span>
      </div>
      <div class="protectedReportBars" aria-hidden="true">
        <span style="--w:84%"></span>
        <span style="--w:62%"></span>
        <span style="--w:72%"></span>
      </div>
      <div class="protectedReportMeta">
        ${summaryBucketHtml}
      </div>
    </div>
  `;

  const shuffleProcess = `
    <div class="shuffleProcess">
      <div class="shuffleProcessStep">
        <div class="shuffleOrder">${orderChips}</div>
      </div>
      <div class="processArrow">Token binding</div>
    </div>
  `;

  const linkageMethod = `
    <div class="linkageTrack">
      <span class="linkageNode rawNode">Raw</span>
      <span class="linkageBeam"></span>
      <span class="linkageNode outputNode">Output</span>
    </div>
    <div class="maskOverlay">
      <span>Shuffled order</span>
      <span>Direct linkage is masked</span>
    </div>
  `;

  panel.innerHTML = `
    <div class="privacyMixer" aria-label="Shuffle privacy pipeline">
      <div class="mixerColumn mixerRaw">
        <div class="mixerLabel">1. Encoded model outputs</div>
        <div class="rawResultCard rawProfileCard">
          <strong>Encoded Inference Output</strong>
          <div class="rawProfileMetaRow">
            <span>${escHtml(privacyMetricText)}</span>
            <div class="profileLockChip">Encoded profile</div>
          </div>
          <div class="rawProfileBars">
            <span style="--w:88%"></span>
            <span style="--w:67%"></span>
            <span style="--w:74%"></span>
          </div>
          <div class="backendTokenStrip">
            <span>backend token</span>
            <code>${escHtml(tokenFlow.generation || "H(session_seed, real_id, nonce)")}</code>
          </div>
        </div>
      </div>
      <div class="mixerArrow arrowToPool">→</div>
      <div class="mixerColumn mixerPool">
        <div class="mixerLabel">2. Generate synthetic database</div>
        <div class="syntheticDatabaseStack">
          ${distributionVisual}
        </div>
      </div>
      <div class="mixerArrow arrowToShuffle">→</div>
      <div class="mixerColumn mixerShuffle">
        <div class="mixerLabel">3. Real record anonymization and shuffle</div>
        <div class="selectionRule">
          <span>token_map</span>
          ${escHtml(tokenFlow.lookup || "real_record = token_map[token]")}
        </div>
        <div class="shuffleMethodStage">
          ${linkageMethod}
          ${shuffleProcess}
        </div>
      </div>
      <div class="mixerArrow arrowToOutput">→</div>
      <div class="mixerColumn mixerProtected">
        <div class="mixerLabel">4. Bucketed summary enters untrusted LLM</div>
        <div class="protectedOutputCard">
          ${plaintextPromptHtml}
          ${llmPromptRouteHtml}
          ${bucketedSummaryThumb}
        </div>
      </div>
    </div>
  `;
  panel.classList.add("step-by-step");
}

function renderLegacyHealthReport(report, plaintextPrompt) {
  const panel = $("conclusionPanel");
  const recoPanel = $("recommendPanel");
  if (!panel) return;
  if (!report) {
    panel.textContent = "—";
    if (recoPanel) recoPanel.textContent = "—";
    return;
  }

  const badge = statusBadge(report.overall);
  const fall = report.fall_risk || {};
  const healthIndex = 1 - Math.min(1, Math.max(0, Number(fall.probability ?? 0)));
  const scoreLabel = report.score_label || (report.domain === "finance" ? "Financial resilience" : "Health index");
  const isFinanceReport = report.domain === "finance";
  const reportTitle = isFinanceReport ? "Protected Financial Risk Report" : "Multimodal Health Report (demo)";

  const metrics = report.metrics || [];
  const chips = (fall.drivers || []).map(x => `<span class="chip">${escHtml(x)}</span>`).join("");

  const metricCards = metrics.map(m => {
    const v = (m.value === null || m.value === undefined) ? "—" : (Number.isFinite(Number(m.value)) ? Number(m.value).toFixed(0) : "—");
    const unit = m.unit ? `<span class="metricUnit">${escHtml(m.unit)}</span>` : "";
    const ref = m.ref ? `<div class="metricRef">Ref: ${escHtml(m.ref)}</div>` : "";
    const detail = m.detail ? `<div class="metricDetail">${escHtml(m.detail)}</div>` : "";
    return `
      <div class="reportCard">
        <div class="reportCardHead">
          <div>
            <div class="metricName">${escHtml(m.name || "")}</div>
            ${ref}
          </div>
          <div class="chip">${escHtml(String(m.status || "").toUpperCase())}</div>
        </div>
        <div class="metricValue">${v}${unit}</div>
        ${detail}
      </div>
    `;
  }).join("");

  const activityMix = isFinanceReport ? (report.charts?.cashflow || {}) : (report.charts?.activity_mix || {});
  const vitals = isFinanceReport ? (report.charts?.burden || {}) : (report.charts?.vitals || {});
  const radar = report.charts?.radar || {};
  const activityTitle = isFinanceReport ? "Cashflow snapshot" : "Activity mix (7-day aggregate)";
  const vitalsTitle = isFinanceReport ? "Risk factors vs reference" : "Vitals vs reference";
  const narrative = report.narrative || "";
  const recos = (report.recommendations || []).map(x => `<li>${escHtml(x)}</li>`).join("");

  // Conclusion side (no recommendations here)
  panel.innerHTML = `
    <div class="reportTop">
      <div>
        <div class="reportTitle">${escHtml(reportTitle)}</div>
        <div class="reportText">${escHtml(narrative)}</div>
      </div>
      <div class="badge">
        <span class="badgeDot" style="background:${badge.dot}"></span>
        <span>${escHtml(badge.text)}</span>
      </div>
    </div>

    <div class="chartGrid">
      <div class="chartRow">
          <div class="chartBox">
          <div class="chartTitle">${escHtml(scoreLabel)}</div>
          <div class="svgBox">${svgGauge(healthIndex, scoreLabel)}</div>
          <div class="chipRow">${chips}</div>
        </div>
        <div class="chartBox">
          <div class="chartTitle">${escHtml(activityTitle)}</div>
          <div class="svgBox">${svgDonut(activityMix, {w:360, h:170})}</div>
        </div>
      </div>

      <div class="chartRow">
        <div class="chartBox">
          <div class="chartTitle">Domain scores</div>
          <div class="svgBox">${svgRadar(radar)}</div>
        </div>
        <div class="chartBox">
          <div class="chartTitle">${escHtml(vitalsTitle)}</div>
          <div class="svgBox">${svgBarVitals(vitals)}</div>
        </div>
      </div>
    </div>

    <div class="reportGrid">${metricCards}</div>
  `;

  // Recommendations panel
  if (recoPanel) {
    recoPanel.innerHTML = `
      <ul class="list">${recos || `<li>${escHtml("—")}</li>`}</ul>
      <div class="disclaimer">${escHtml(report.disclaimer || "")}</div>
    `;
  }
}

function renderHealthReport(report, plaintextPrompt) {
  const hasDynamicReport = Boolean(
    report &&
    typeof report === "object" &&
    report.summary &&
    typeof report.summary === "object" &&
    !Array.isArray(report.summary) &&
    ((Array.isArray(report.sections) && report.sections.length > 0) ||
      Array.isArray(report.compact_sections) ||
      Array.isArray(report.missing_signals))
  );

  if (!hasDynamicReport) {
    return renderLegacyHealthReport(report, plaintextPrompt);
  }
  return renderDynamicHealthReport(report, plaintextPrompt);
}

function renderDynamicHealthReport(report, plaintextPrompt) {
  const panel = $("conclusionPanel");
  const recoPanel = $("recommendPanel");
  if (!panel) return;

  const summary = report?.summary || {};
  const domain = report.domain || "healthcare";
  const scoreLabel = report.score_label || (domain === "finance" ? "Financial resilience" : "Health index");
  const badge = statusBadge(summary.overall || report.overall);
  const expandedSections = Array.isArray(report.sections) ? report.sections : [];
  const compactSections = Array.isArray(report.compact_sections) ? report.compact_sections : [];
  const missingSignals = Array.isArray(report.missing_signals) ? report.missing_signals : [];
  const drivers = (summary.drivers || report.fall_risk?.drivers || []).map(item => `<span class="chip">${escHtml(item)}</span>`).join("");

  const missingHtml = missingSignals.length ? `
    <aside class="missingSignals">
      <div class="missingTitle">Missing signals</div>
      ${missingSignals.slice(0, 3).map((item) => `
        <div class="missingItem">
          <strong>${escHtml(item.title || "")}</strong>
          <span>${escHtml(item.message || "")}</span>
        </div>
      `).join("")}
    </aside>
  ` : "";

  const sectionHtml = expandedSections.map((section) => `
    <section class="storySection story-${escHtml(section.id || "section")} ${statusClass(section.status)}">
      <div class="storySectionHead">
        <div>
          <h3>${escHtml(section.title || "")}</h3>
          <p>${escHtml(section.insight || "")}</p>
        </div>
        <div class="sourceTags">${(section.source_modalities || []).map(modalityTag).join("")}</div>
      </div>
      <div class="storySectionBody">
        <div class="storyChart">${renderSectionChart(section)}</div>
        <div class="storyMetrics">${(section.metrics || []).slice(0, 4).map(metricMiniCard).join("")}</div>
      </div>
    </section>
  `).join("");

  const compactHtml = compactSections.length ? `
    <div class="compactSectionGrid">
      ${compactSections.map((section) => `
        <div class="compactSection compact-${escHtml(section.id || "section")} ${statusClass(section.status)}">
          <div class="compactSectionHead">
            <strong>${escHtml(section.title || "")}</strong>
            <span>${(section.source_modalities || []).map((item) => escHtml(String(item).toUpperCase())).join(" + ")}</span>
          </div>
          <div class="compactChart">${renderSectionChart(section, {compact: true})}</div>
        </div>
      `).join("")}
    </div>
  ` : "";

  panel.innerHTML = `
    <div class="dynamicReportTop">
      <section class="integratedSummary">
        <div class="summaryHead">
          <div>
            <div class="reportTitle">${escHtml(summary.title || "Integrated Summary")}</div>
            <div class="summaryScore">${Math.round(Number(summary.health_index || 0) * 100)}%</div>
            <div class="summaryScoreLabel">${escHtml(scoreLabel)}</div>
          </div>
          <div class="badge">
            <span class="badgeDot" style="background:${badge.dot}"></span>
            <span>${escHtml(badge.text)}</span>
          </div>
        </div>
        <div class="summaryTrack"><i style="width:${Math.max(0, Math.min(100, Number(summary.health_index || 0) * 100))}%"></i></div>
        <div class="chipRow">${drivers}</div>
      </section>
      ${missingHtml}
    </div>
    <div class="storySectionStack">${sectionHtml}</div>
    ${compactHtml}
  `;

  if (recoPanel) {
    const recos = (report.recommendations || []).map((item) => `<li>${escHtml(item)}</li>`).join("");
    recoPanel.innerHTML = `
      <ul class="list">${recos || `<li>${escHtml("—")}</li>`}</ul>
      <div class="disclaimer">${escHtml(report.disclaimer || "")}</div>
    `;
  }
}

let running = false;

async function runCycle() {
  if (running) return;
  running = true;

  showSpinner("spinUpload", true);
  showSpinner("spinDispatch", true);
  showSpinner("spinDecrypt", true);

  const t0 = performance.now();

  try {
    const res = await fetch(`${API_BASE}/api/cycle`, { method: "GET" });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();

    // step 1
    renderModalities(data.step1.modalities || {});
    setPill("tUpload", `refresh ${fmtSec(data.step1.time_sec)} | ${safeText(data.generated_at)}`);

    // Store detailed analysis data
    detailedAnalysisData = data.step1.modalities || {};
    // Render initial analysis (UWB by default)
    renderDetailedAnalysis('uwb');

    // step 2
    const s2 = data.step2 || {};
$("ctResPreview").textContent = safeText(s2.aggregate_cipher_preview);

    renderCluster(s2.cluster_models || [], s2.assignments || []);
    setPill("tDispatch", `dispatch+infer ${fmtSec(s2.time_sec)}`);

    // step 3
    const s3 = data.step3 || {};
    const privacy = {
      ...(data.privacy_protection || {}),
      plaintext_prompt: s3.plaintext_prompt || s3.llm_prompt,
    };
    renderPrivacyProtection(privacy);
    setPill("tProtect", privacy.enabled ? "protected" : "unavailable");

    // step 4
    console.log("Step 3 data:", s3);
    console.log("Results array:", s3.results);

    // Always render results table first
    renderResults(s3.results || []);

    // Then render report if available
    if (s3.report) {
      renderHealthReport(s3.report, s3.plaintext_prompt || s3.llm_prompt);
      if ($("conclusionPanel")) $("conclusionPanel").style.display = "block";
      if ($("recommendPanel")) $("recommendPanel").style.display = "block";
      if ($("reportText")) $("reportText").style.display = "none";
    } else {
      if ($("conclusionPanel")) $("conclusionPanel").style.display = "none";
      if ($("reportText")) {
        $("reportText").style.display = "block";
        $("reportText").textContent = safeText(s3.report_conclusion || s3.conclusion || "—");
      }
      if ($("recommendPanel")) {
        $("recommendPanel").style.display = "block";
        $("recommendPanel").textContent = "—";
      }
    }
    setPill("tDecrypt", `report ${fmtSec(s3.time_sec)}`);

  } catch (e) {
    console.error(e);
    setPill("tUpload", "error");
    setPill("tDispatch", "error");
    setPill("tProtect", "error");
    setPill("tDecrypt", "error");
    if ($("conclusionPanel")) {
      $("conclusionPanel").style.display = "block";
      $("conclusionPanel").innerHTML = `<div class="reportText">Error: ${escHtml(e.message)}</div>`;
    }
    if ($("recommendPanel")) {
      $("recommendPanel").style.display = "block";
      $("recommendPanel").textContent = "—";
    }
    if ($("reportText")) {
      $("reportText").style.display = "none";
      $("reportText").textContent = `Error: ${e.message}`;
    }
  } finally {
    showSpinner("spinUpload", false);
    showSpinner("spinDispatch", false);
    showSpinner("spinDecrypt", false);
    running = false;
  }

  const t1 = performance.now();
  const meta = $("cycleMeta");
  if (meta) meta.textContent = `Auto refresh: 10s | last cycle ${(t1 - t0).toFixed(0)} ms`;
}

window.addEventListener("DOMContentLoaded", () => {
  console.log('🟢 DOMContentLoaded事件触发');
  setWorkflowStep("select");
  setupAnalysisTabs();
  // 完全禁用自动刷新 - 只通过用户点击"开始分析"按钮触发
  // runCycle();
  // setInterval(runCycle, 10000000000);
  console.log('✅ 自动刷新已禁用，不会调用runCycle()');

  // 初始化模态选择器
  if (typeof ModalitySelector !== 'undefined') {
    console.log('🔵 开始初始化ModalitySelector');
    new ModalitySelector();
  } else {
    console.error('❌ ModalitySelector未定义，请检查modality-selector.js是否正确加载');
  }

  // 初始化时清空Step 2和Step 3的内容
  const modelCluster = document.getElementById('modelCluster');
  if (modelCluster) {
    modelCluster.innerHTML = '<div style="grid-column: 1/-1; text-align: center; color: #9ca3af; padding: 40px;">Select medical data, then run analysis to activate local encoders.</div>';
    console.log('✅ Step 2占位符已设置');
  }

  const resultTable = document.querySelector('#resultTable tbody');
  if (resultTable) {
    resultTable.innerHTML = '<tr><td colspan="4" style="text-align:center; color: #9ca3af; padding: 20px;">Select medical data and run analysis to populate results.</td></tr>';
    console.log('✅ Step 3占位符已设置');
  }

  const privacyPanel = document.getElementById('privacyPanel');
  if (privacyPanel) {
    privacyPanel.innerHTML = 'Select medical data and run analysis to open the anonymized shuffle flow.';
  }

  const resultsTitle = document.getElementById('resultsTitle');
  if (resultsTitle) {
    resultsTitle.textContent = 'Key results (waiting for analysis)';
  }

  const recommendPanel = document.getElementById('recommendPanel');
  if (recommendPanel) {
    recommendPanel.innerHTML = 'Recommendations will appear after analysis.';
  }

  const conclusionPanel = document.getElementById('conclusionPanel');
  if (conclusionPanel) {
    conclusionPanel.innerHTML = 'Report status will appear after analysis.';
  }

  console.log('✅ 页面初始化完成');
});
