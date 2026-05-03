// frontend/assets/js/app.js
const API_BASE = (window.API_BASE || "http://127.0.0.1:8082");

const $ = (id) => document.getElementById(id);

const WORKFLOW_PANEL_BY_STEP = {
  select: "stepUpload",
  model: "stepDispatch",
  privacy: "stepProtect",
  report: "stepDecrypt",
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
  const s = String(x);
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
  const w = 360, h = 140;
  const pad = 20;
  const barHeight = 40;
  const barY = 60;
  const barX = pad;
  const barWidth = w - 2 * pad;

  const pct = Math.round(p * 100);
  const fillWidth = barWidth * p;

  // Color based on risk level
  const barColor = p >= 0.7 ? "#ef4444" : (p >= 0.4 ? "#f97316" : "#22c55e");
  const barColorLight = p >= 0.7 ? "rgba(239, 68, 68, 0.15)" : (p >= 0.4 ? "rgba(249, 115, 22, 0.15)" : "rgba(34, 197, 94, 0.15)");

  // Risk level indicators
  const lowEnd = barX + barWidth * 0.4;
  const highStart = barX + barWidth * 0.7;

  return `
  <svg viewBox="0 0 ${w} ${h}" role="img" aria-label="Fall probability">
    <rect x="1" y="1" width="${w-2}" height="${h-2}" rx="12" fill="#ffffff" stroke="rgba(230,232,239,.8)"/>

    <!-- Risk zone backgrounds -->
    <rect x="${barX}" y="${barY}" width="${barWidth * 0.4}" height="${barHeight}" fill="rgba(34, 197, 94, 0.08)" rx="8"/>
    <rect x="${lowEnd}" y="${barY}" width="${barWidth * 0.3}" height="${barHeight}" fill="rgba(249, 115, 22, 0.08)"/>
    <rect x="${highStart}" y="${barY}" width="${barWidth * 0.3}" height="${barHeight}" fill="rgba(239, 68, 68, 0.08)" rx="8"/>

    <!-- Background bar -->
    <rect x="${barX}" y="${barY}" width="${barWidth}" height="${barHeight}" fill="rgba(15,23,42,.06)" stroke="rgba(15,23,42,.12)" stroke-width="1" rx="8"/>

    <!-- Progress fill -->
    <rect x="${barX}" y="${barY}" width="${fillWidth.toFixed(2)}" height="${barHeight}" fill="${barColor}" rx="8"/>

    <!-- Zone labels -->
    <text x="${barX + barWidth * 0.2}" y="${barY + barHeight + 18}" text-anchor="middle" font-size="10" font-weight="700" fill="#22c55e">Low</text>
    <text x="${barX + barWidth * 0.55}" y="${barY + barHeight + 18}" text-anchor="middle" font-size="10" font-weight="700" fill="#f97316">Moderate</text>
    <text x="${barX + barWidth * 0.85}" y="${barY + barHeight + 18}" text-anchor="middle" font-size="10" font-weight="700" fill="#ef4444">High</text>

    <!-- Percentage and label -->
    <text x="${w / 2}" y="35" text-anchor="middle" font-size="32" font-weight="900" fill="#0f172a">${pct}%</text>
    <text x="${w / 2}" y="50" text-anchor="middle" font-size="13" font-weight="700" fill="rgba(15,23,42,.6)">${escHtml(label || "")}</text>

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
  const items = labels.slice(0, values.length).map((lab, i) => {
    const pct = (100 * (values[i] / sum)).toFixed(0) + "%";
    return `<span class="legendItem"><span class="legendDot" style="background:${palette[i % palette.length]}"></span>${escHtml(lab)} <span class="mono">${pct}</span></span>`;
  }).join("");

  return `
  <div class="donutWrap">
    <svg width="${w}" height="${h}" viewBox="0 0 ${w} ${h}" aria-label="Donut chart">
      <circle cx="${cx}" cy="${cy}" r="${r}" fill="none" stroke="rgba(2,6,23,.08)" stroke-width="${stroke}"/>
      ${segs}
      <circle cx="${cx}" cy="${cy}" r="${r - stroke * 0.9}" fill="#fff"/>
      <text x="${cx}" y="${cy + 6}" font-size="14" text-anchor="middle" fill="#0f172a" font-weight="700">Activity</text>
    </svg>
    <div class="legend">${items}</div>
  </div>`;
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

function renderPrivacyProtection(privacy) {
  const panel = $("privacyPanel");
  if (!panel) return;
  if (!privacy || !privacy.enabled) {
    panel.innerHTML = '<div class="hint">隐私保护数据暂不可用。</div>';
    return;
  }

  const pipeline = [
    { label: "候选池", detail: "根据加密推理结果生成相似的合成候选。" },
    { label: "混洗", detail: "随机打乱候选顺序，切断直接对应关系。" },
    { label: "关联掩蔽", detail: "只暴露摘要候选，不暴露原始模型输出。" },
    { label: "受保护输出", detail: "从混洗候选中选择最终报告来源。" },
  ];
  const poolSize = Math.min(Number(privacy.pool_size || privacy.metrics?.pool_size || 10), 10);
  const tokens = Array.from({ length: poolSize }, (_, index) => {
    const slot = ((index * 7) % 10) + 1;
    return `<div class="mixerToken" style="--slot:${slot}; --delay:${700 + index * 130}ms">C${index + 1}</div>`;
  }).join("");

  const pipelineHtml = pipeline.map((stage, index) => `
    <div class="privacyStage ${index === pipeline.length - 1 ? "active" : ""}" style="--delay:${index * 1400}ms">
      <div class="privacyStageIndex">${index + 1}</div>
      <div>
        <div class="privacyStageTitle">${escHtml(stage.label)}</div>
        <div class="privacyStageDetail">${escHtml(stage.detail || "")}</div>
      </div>
    </div>
  `).join("");

  panel.innerHTML = `
    <div class="privacySummary">
      <strong>隐私混洗器已启动。</strong>
      原始推理结果不会直接进入报告，而是先混入合成候选池，再通过混洗和关联掩蔽生成受保护输出。
    </div>
    <div class="privacyMixer">
      <div class="mixerColumn mixerRaw">
        <div class="mixerLabel">原始加密推理摘要</div>
        <div class="rawResultCard">
          <strong>Raw profile</strong>
          <span>风险摘要 / 生理指标 / 模型评分</span>
        </div>
      </div>
      <div class="mixerArrow">→</div>
      <div class="mixerColumn mixerPool">
        <div class="mixerLabel">候选池</div>
        <div class="mixerTokenGrid">${tokens}</div>
      </div>
      <div class="mixerArrow">→</div>
      <div class="mixerColumn mixerShuffle">
        <div class="mixerLabel">混洗通道</div>
        <div class="shuffleChamber">
          <div class="shuffleLine"></div>
          <div class="shuffleLine"></div>
          <div class="shuffleLine"></div>
        </div>
      </div>
      <div class="mixerArrow">→</div>
      <div class="mixerColumn mixerProtected">
        <div class="mixerLabel">受保护输出</div>
        <div class="protectedOutputCard">Protected Output</div>
      </div>
    </div>
    <div class="privacyPipeline">${pipelineHtml}</div>
  `;
}

function renderHealthReport(report) {
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
  const fallP = Number(fall.probability ?? 0);
  const fallLevel = fall.level || "—";

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

    const activityMix = report.charts?.activity_mix || {};
  const vitals = report.charts?.vitals || {};
  const radar = report.charts?.radar || {};
  const narrative = report.narrative || "";

  const recos = (report.recommendations || []).map(x => `<li>${escHtml(x)}</li>`).join("");

  // Conclusion side (no recommendations here)
  panel.innerHTML = `
    <div class="reportTop">
      <div>
        <div class="reportTitle">Multimodal Health Report (demo)</div>
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
          <div class="chartTitle">Fall probability</div>
          <div class="svgBox">${svgGauge(fallP, `${fallLevel} risk`)}</div>
          <div class="chipRow">${chips}</div>
        </div>
        <div class="chartBox">
          <div class="chartTitle">Activity mix (7‑day aggregate)</div>
          <div class="svgBox">${svgDonut(activityMix, {w:360, h:170})}</div>
        </div>
      </div>

      <div class="chartRow">
        <div class="chartBox">
          <div class="chartTitle">Domain scores</div>
          <div class="svgBox">${svgRadar(radar)}</div>
        </div>
        <div class="chartBox">
          <div class="chartTitle">Vitals vs reference</div>
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
    const privacy = data.privacy_protection || {};
    renderPrivacyProtection(privacy);
    setPill("tProtect", privacy.enabled ? "protected" : "unavailable");

    // step 4
    const s3 = data.step3 || {};
    console.log("Step 3 data:", s3);
    console.log("Results array:", s3.results);

    // Always render results table first
    renderResults(s3.results || []);

    // Then render report if available
    if (s3.report) {
      renderHealthReport(s3.report);
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
    modelCluster.innerHTML = '<div style="grid-column: 1/-1; text-align: center; color: #9ca3af; padding: 40px;">Select modalities, then run analysis to activate model dispatch.</div>';
    console.log('✅ Step 2占位符已设置');
  }

  const resultTable = document.querySelector('#resultTable tbody');
  if (resultTable) {
    resultTable.innerHTML = '<tr><td colspan="4" style="text-align:center; color: #9ca3af; padding: 20px;">Select modalities and run analysis to populate results.</td></tr>';
    console.log('✅ Step 3占位符已设置');
  }

  const privacyPanel = document.getElementById('privacyPanel');
  if (privacyPanel) {
    privacyPanel.innerHTML = 'Select modalities and run analysis to generate protected candidates.';
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
