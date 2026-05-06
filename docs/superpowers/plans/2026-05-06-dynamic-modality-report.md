# Dynamic Modality Report Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a modality-aware protected health report that renders visual health-theme sections, selected from the modalities the user chose.

**Architecture:** Add backend section-building helpers around the existing `build_health_report()` flow, preserving the current report fields for compatibility. Extend the frontend report renderer to prefer `report.summary`, `report.sections`, `report.compact_sections`, and `report.missing_signals`, with a fallback to the existing fixed chart layout.

**Tech Stack:** Python 3.8, FastAPI, unittest/httpx backend contract tests, vanilla JavaScript, inline SVG chart helpers, existing CSS in `frontend/assets/css/styles.css`.

---

## File Structure

- Modify `AGENTS.md`: already updated to allow brainstorming specs and implementation plans under `docs/superpowers/`.
- Modify `backend/app.py`: add selected-modality aware report section builders and pass selected modality IDs into report construction.
- Modify `backend/tests/test_app_contract.py`: add API contract coverage for dynamic report sections, missing signals, and fallback compatibility fields.
- Modify `frontend/assets/js/app.js`: add dynamic section renderers and chart helpers; keep old renderer as fallback.
- Modify `frontend/assets/js/modality-selector.js`: no major data-flow change expected; only adjust calls if `renderHealthReport()` needs selected modality context.
- Modify `frontend/assets/css/styles.css`: add styles for summary, missing signals, expanded section story cards, compact tiles, metric strips, and source tags.

Do not remove the existing fixed report fields in this implementation. They are migration compatibility fields and keep privacy shuffle helpers stable.

## Task 1: Backend Contract Tests for Dynamic Sections

**Files:**
- Modify: `backend/tests/test_app_contract.py`

- [ ] **Step 1: Add a focused test for single-modality section filtering**

Add this method to `AppContractTests`:

```python
    async def test_report_sections_follow_selected_modalities(self):
        response = await self.client.get(
            "/api/cycle",
            params={"selected_modalities": "imu"},
        )

        self.assertEqual(response.status_code, 200)
        report = response.json()["step3"]["report"]

        self.assertIn("summary", report)
        self.assertIn("sections", report)
        self.assertIn("missing_signals", report)
        self.assertIn("compact_sections", report)

        section_ids = {section["id"] for section in report["sections"]}
        compact_ids = {section["id"] for section in report["compact_sections"]}
        all_visible_ids = section_ids | compact_ids

        self.assertIn("mobility", all_visible_ids)
        self.assertIn("activity", all_visible_ids)
        self.assertNotIn("vitals", all_visible_ids)
        self.assertNotIn("sleep", all_visible_ids)
        self.assertNotIn("medical_screening", all_visible_ids)

        missing_ids = {item["theme_id"] for item in report["missing_signals"]}
        self.assertIn("vitals", missing_ids)
        self.assertIn("sleep", missing_ids)
        self.assertIn("medical_screening", missing_ids)
```

- [ ] **Step 2: Add a test for multi-modality expanded section count and source tags**

Add this method to `AppContractTests`:

```python
    async def test_report_expands_integrated_summary_and_top_three_sections(self):
        response = await self.client.get(
            "/api/cycle",
            params={"selected_modalities": "depth,uwb,imu,csi,rgb"},
        )

        self.assertEqual(response.status_code, 200)
        report = response.json()["step3"]["report"]

        self.assertEqual(report["summary"]["title"], "Integrated Summary")
        self.assertGreaterEqual(report["summary"]["health_index"], 0)
        self.assertLessEqual(report["summary"]["health_index"], 1)
        self.assertEqual(
            report["summary"]["coverage"]["selected_modalities"],
            ["depth", "uwb", "imu", "csi", "rgb"],
        )

        expanded_sections = [section for section in report["sections"] if section.get("expanded")]
        self.assertLessEqual(len(expanded_sections), 3)
        self.assertGreaterEqual(len(expanded_sections), 1)

        integrated = next(section for section in report["sections"] if section["id"] == "integrated_risk")
        self.assertEqual(integrated["chart_type"], "radar")
        self.assertGreaterEqual(len(integrated["source_modalities"]), 2)

        for section in report["sections"]:
            self.assertIsInstance(section["title"], str)
            self.assertIsInstance(section["source_modalities"], list)
            self.assertIsInstance(section["metrics"], list)
            self.assertIsInstance(section["insight"], str)
            self.assertIsInstance(section["chart"], dict)
```

- [ ] **Step 3: Verify the tests fail before implementation**

Run:

```bash
source venv/bin/activate && PYTHONPATH=. pytest backend/tests/test_app_contract.py::AppContractTests::test_report_sections_follow_selected_modalities backend/tests/test_app_contract.py::AppContractTests::test_report_expands_integrated_summary_and_top_three_sections -v
```

Expected: both tests fail because `summary`, `sections`, `missing_signals`, and `compact_sections` are not yet present in the report.

## Task 2: Backend Section Schema and Builders

**Files:**
- Modify: `backend/app.py`

- [ ] **Step 1: Change `build_health_report()` signature**

Update the function signature:

```python
def build_health_report(
    results: List[Dict],
    uwb_data: np.ndarray,
    imu_data: np.ndarray,
    csi_data: np.ndarray,
    seed: int = 42,
    selected_modalities: Optional[List[str]] = None,
) -> Dict[str, Any]:
```

Use the already imported `Optional` from `typing`. If it is not imported, add it to the existing typing import:

```python
from typing import Any, Dict, List, Optional
```

- [ ] **Step 2: Add local modality normalization inside `build_health_report()`**

Place this near the top of `build_health_report()` after the RNG setup:

```python
    selected_modality_ids = [
        str(item).strip().lower()
        for item in (selected_modalities or [])
        if str(item).strip()
    ]
```

- [ ] **Step 3: Add theme definitions inside `build_health_report()` after `metrics` are built**

Add:

```python
    theme_order = ["integrated_risk", "mobility", "vitals", "sleep", "activity", "medical_screening"]
    theme_definitions = {
        "mobility": {
            "title": "Mobility & Fall Stability",
            "modalities": ["imu", "uwb", "rgb", "ntu"],
            "chart_type": "stability",
        },
        "vitals": {
            "title": "Cardiorespiratory Vitals",
            "modalities": ["csi", "uwb"],
            "chart_type": "reference_bars",
        },
        "sleep": {
            "title": "Sleep & Recovery",
            "modalities": ["depth", "csi"],
            "chart_type": "recovery_bars",
        },
        "activity": {
            "title": "Activity Pattern",
            "modalities": ["imu", "uwb", "rgb", "ntu"],
            "chart_type": "stacked_mix",
        },
        "medical_screening": {
            "title": "Medical Image Screening",
            "modalities": ["retina", "chest", "path", "blood"],
            "chart_type": "risk_tiles",
        },
        "integrated_risk": {
            "title": "Integrated Risk Summary",
            "modalities": selected_modality_ids,
            "chart_type": "radar",
        },
    }
```

- [ ] **Step 4: Add helper functions inside `build_health_report()`**

Add these nested helpers after `theme_definitions`:

```python
    metric_by_name = {item["name"].lower(): item for item in metrics}

    def selected_sources(theme_id: str) -> List[str]:
        if theme_id == "integrated_risk":
            return selected_modality_ids if len(selected_modality_ids) >= 2 else []
        supported = theme_definitions[theme_id]["modalities"]
        return [item for item in selected_modality_ids if item in supported]

    def metric_pick(*names: str) -> List[Dict[str, Any]]:
        picked = []
        for name in names:
            metric_item = metric_by_name.get(name.lower())
            if metric_item:
                picked.append(metric_item)
        return picked

    def section_status(section_metrics: List[Dict[str, Any]], default_status: str = "stable") -> str:
        statuses = {str(item.get("status", "")).lower() for item in section_metrics}
        if "high" in statuses or "low" in statuses:
            return "attention"
        if "watch" in statuses or "moderate" in statuses:
            return "watch"
        return default_status

    def abnormality_score(section_metrics: List[Dict[str, Any]]) -> int:
        score = 0
        for item in section_metrics:
            status = str(item.get("status", "")).lower()
            if status in ("high", "low", "attention"):
                score += 30
            elif status in ("moderate", "watch"):
                score += 18
            elif status == "normal":
                score += 5
        return score
```

- [ ] **Step 5: Build dynamic sections**

Add this section-building block before the final `return`:

```python
    sections = []

    if len(selected_modality_ids) >= 2:
        sections.append({
            "id": "integrated_risk",
            "title": theme_definitions["integrated_risk"]["title"],
            "status": overall.lower(),
            "priority": 85 + min(10, len(selected_modality_ids)),
            "source_modalities": selected_sources("integrated_risk"),
            "chart_type": "radar",
            "chart": {"labels": radar_labels, "values": [float(x) for x in radar_values]},
            "metrics": [
                metric("Health index", health_index * 100, "%", "70-100", "normal" if health_index >= 0.7 else "low"),
                metric("Data coverage", len(selected_modality_ids), "modalities", "2+", "normal"),
            ],
            "insight": "Cross-modal evidence is summarized into a single protected health profile.",
        })

    mobility_metrics = metric_pick("Cadence")
    if selected_sources("mobility"):
        sections.append({
            "id": "mobility",
            "title": theme_definitions["mobility"]["title"],
            "status": "attention" if mobility_r > 0.55 else "stable",
            "priority": abnormality_score(mobility_metrics) + int(mobility_r * 60) + 20,
            "source_modalities": selected_sources("mobility"),
            "chart_type": "stability",
            "chart": {
                "score": float(1.0 - mobility_r),
                "trend": [float(x) for x in np.clip(np.linspace(1.0 - mobility_r * 0.7, 1.0 - mobility_r, 8), 0, 1).tolist()],
                "drift": float(uwb_drift),
                "gait_variability": float(gait_var),
            },
            "metrics": mobility_metrics + [
                metric("Movement drift", uwb_drift, "", "<0.08", "high" if uwb_drift > 0.08 else "normal"),
            ],
            "insight": "Movement stability is estimated from gait variability and radar motion drift.",
        })

    vitals_metrics = metric_pick("Heart rate", "Resp. rate", "Blood pressure", "SpO₂")
    if selected_sources("vitals"):
        sections.append({
            "id": "vitals",
            "title": theme_definitions["vitals"]["title"],
            "status": section_status(vitals_metrics),
            "priority": abnormality_score(vitals_metrics) + int(cardio_r * 30) + int(bp_r * 30),
            "source_modalities": selected_sources("vitals"),
            "chart_type": "reference_bars",
            "chart": {
                "labels": ["HR", "RR", "SBP", "SpO2"],
                "values": [float(hr_bpm if not np.isnan(hr_bpm) else 75.0), float(rr_bpm if not np.isnan(rr_bpm) else 16.0), float(sbp), float(spo2)],
                "ranges": {"HR": [60, 100], "RR": [12, 20], "SBP": [90, 120], "SpO2": [95, 100]},
            },
            "metrics": vitals_metrics[:4],
            "insight": "Cardiorespiratory proxies are compared against demo reference bands.",
        })

    sleep_metrics = metric_pick("Sleep efficiency", "Resp. rate")
    if selected_sources("sleep"):
        sections.append({
            "id": "sleep",
            "title": theme_definitions["sleep"]["title"],
            "status": "attention" if sleep_eff < 85 else "stable",
            "priority": abnormality_score(sleep_metrics) + int(sleep_r * 55),
            "source_modalities": selected_sources("sleep"),
            "chart_type": "recovery_bars",
            "chart": {
                "labels": ["Sleep efficiency", "Recovery", "Resp. regularity"],
                "values": [float(sleep_eff), float(100 * (1.0 - sleep_r)), float(100 * (1.0 - cardio_r * 0.4))],
            },
            "metrics": sleep_metrics,
            "insight": "Sleep and recovery are estimated from depth posture and respiratory rhythm signals.",
        })

    if selected_sources("activity"):
        sections.append({
            "id": "activity",
            "title": theme_definitions["activity"]["title"],
            "status": "stable",
            "priority": 35 + int((mix[0] + mix[1]) * 30),
            "source_modalities": selected_sources("activity"),
            "chart_type": "stacked_mix",
            "chart": {"labels": activity_labels, "values": [float(x) for x in mix.tolist()]},
            "metrics": [
                metric("Walk share", float(mix[0] * 100), "%", "demo mix", "normal"),
                metric("Rest share", float((mix[2] + mix[3]) * 100), "%", "demo mix", "normal"),
            ],
            "insight": "Activity mix summarizes the selected motion and visual behavior signals.",
        })

    medical_sources = selected_sources("medical_screening")
    if medical_sources:
        image_results = [item for item in results if str(item.get("model_id", "")).lower() in {"retina", "chest", "path", "blood"}]
        sections.append({
            "id": "medical_screening",
            "title": theme_definitions["medical_screening"]["title"],
            "status": "watch" if any(str(item.get("status", "")).lower() != "normal" for item in image_results) else "stable",
            "priority": 40 + 10 * len(image_results),
            "source_modalities": medical_sources,
            "chart_type": "risk_tiles",
            "chart": {
                "tiles": [
                    {"label": item.get("model", item.get("model_id", "Image")), "score": item.get("score"), "status": item.get("status", "normal")}
                    for item in image_results
                ],
            },
            "metrics": [
                metric("Image sources", len(medical_sources), "modalities", "1+", "normal"),
            ],
            "insight": "Medical imaging signals are summarized as demo screening tiles.",
        })
```

- [ ] **Step 6: Split expanded and compact sections**

Add this after the `sections` list is built:

```python
    order_index = {theme_id: index for index, theme_id in enumerate(theme_order)}
    sections.sort(key=lambda item: (-int(item.get("priority", 0)), order_index.get(item["id"], 99)))
    expanded_ids = {item["id"] for item in sections[:3]}
    expanded_sections = [{**item, "expanded": item["id"] in expanded_ids} for item in sections[:3]]
    compact_sections = [{**item, "expanded": False} for item in sections[3:]]
```

- [ ] **Step 7: Build missing signals**

Add:

```python
    missing_signals = []
    for theme_id in theme_order:
        if theme_id == "integrated_risk":
            if len(selected_modality_ids) < 2:
                missing_signals.append({
                    "theme_id": theme_id,
                    "title": theme_definitions[theme_id]["title"],
                    "missing_modalities": [],
                    "message": "Select at least two modalities to unlock integrated cross-modal risk summary.",
                })
            continue
        if selected_sources(theme_id):
            continue
        missing_signals.append({
            "theme_id": theme_id,
            "title": theme_definitions[theme_id]["title"],
            "missing_modalities": theme_definitions[theme_id]["modalities"],
            "message": f"Add {', '.join(theme_definitions[theme_id]['modalities'])} to unlock {theme_definitions[theme_id]['title']}.",
        })
```

- [ ] **Step 8: Extend the returned report dictionary**

In the final `return`, add these keys alongside existing fields:

```python
        "summary": {
            "title": "Integrated Summary",
            "health_index": float(health_index),
            "overall": overall,
            "drivers": drivers[:4],
            "coverage": {
                "selected_modalities": selected_modality_ids,
                "available_theme_count": len(sections),
                "total_theme_count": len(theme_order),
            },
        },
        "missing_signals": missing_signals,
        "sections": expanded_sections,
        "compact_sections": compact_sections,
```

- [ ] **Step 9: Pass selected modalities into report construction**

Find all calls to `build_health_report(...)` in `backend/app.py`.

For `_build_privacy_and_report(session)`, change:

```python
    raw_report = build_health_report(raw_results, uwb_for_report, imu_for_report, csi_for_report)
```

to:

```python
    raw_report = build_health_report(
        raw_results,
        uwb_for_report,
        imu_for_report,
        csi_for_report,
        selected_modalities=session.get("selected_modalities", []),
    )
```

For the `/api/cycle` path near the bottom of `backend/app.py`, pass the selected modality IDs already parsed in that function:

```python
        raw_report = build_health_report(
            raw_results,
            uwb_for_report,
            imu_for_report,
            csi_for_report,
            selected_modalities=selected_modality_ids,
        )
```

- [ ] **Step 10: Run backend contract tests**

Run:

```bash
source venv/bin/activate && PYTHONPATH=. pytest backend/tests/test_app_contract.py -v
```

Expected: all `AppContractTests` pass.

## Task 3: Keep Privacy Prompt Bucketed with Section Context

**Files:**
- Modify: `backend/app.py`
- Modify: `backend/tests/test_app_contract.py`

- [ ] **Step 1: Add a privacy prompt test**

Add this assertion block to `test_cycle_keeps_precise_dashboard_report_and_results` after `llm_prompt = self.llm_mock.call_args.args[0]`:

```python
        self.assertIn("Section summary", llm_prompt)
        self.assertIn("Mobility & Fall Stability", llm_prompt)
        self.assertNotIn(str(report["summary"]["health_index"]), llm_prompt)
```

- [ ] **Step 2: Verify the test fails**

Run:

```bash
source venv/bin/activate && PYTHONPATH=. pytest backend/tests/test_app_contract.py::AppContractTests::test_cycle_keeps_precise_dashboard_report_and_results -v
```

Expected: FAIL because `_build_bucketed_llm_prompt()` does not yet mention section summaries.

- [ ] **Step 3: Add a section summary helper**

Add this function before `_build_bucketed_llm_prompt()`:

```python
def _build_bucketed_section_prompt_summary(raw_report: Dict[str, Any]) -> List[Dict[str, Any]]:
    summaries = []
    for section in raw_report.get("sections", [])[:3]:
        summaries.append({
            "title": section.get("title"),
            "status": section.get("status"),
            "sources": section.get("source_modalities", []),
            "metric_names": [metric.get("name") for metric in section.get("metrics", [])[:4]],
        })
    return summaries
```

- [ ] **Step 4: Pass raw report into the prompt builder**

Change:

```python
def _build_bucketed_llm_prompt(protected_llm_summary: Dict[str, Any]) -> str:
```

to:

```python
def _build_bucketed_llm_prompt(protected_llm_summary: Dict[str, Any], raw_report: Optional[Dict[str, Any]] = None) -> str:
```

Inside the return string, add:

```python
        f"Section summary: {_build_bucketed_section_prompt_summary(raw_report or {})}; "
```

Change calls from:

```python
    prompt = _build_bucketed_llm_prompt(privacy_bundle["protected_llm_summary"])
```

to:

```python
    prompt = _build_bucketed_llm_prompt(privacy_bundle["protected_llm_summary"], raw_report)
```

Also update the `/api/cycle` call:

```python
        llm_prompt = _build_bucketed_llm_prompt(privacy_bundle["protected_llm_summary"], raw_report)
```

- [ ] **Step 5: Run backend tests**

Run:

```bash
source venv/bin/activate && PYTHONPATH=. pytest backend/tests -v
```

Expected: all backend tests pass.

## Task 4: Frontend Dynamic Report Rendering

**Files:**
- Modify: `frontend/assets/js/app.js`

- [ ] **Step 1: Preserve fallback renderer**

Rename the current `renderHealthReport(report, plaintextPrompt)` implementation to:

```javascript
function renderLegacyHealthReport(report, plaintextPrompt) {
  // existing function body goes here unchanged
}
```

Then create a new wrapper:

```javascript
function renderHealthReport(report, plaintextPrompt) {
  if (!report || !Array.isArray(report.sections)) {
    return renderLegacyHealthReport(report, plaintextPrompt);
  }
  return renderDynamicHealthReport(report, plaintextPrompt);
}
```

- [ ] **Step 2: Add small rendering utilities**

Add these functions before `renderDynamicHealthReport`:

```javascript
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
    : (Number.isFinite(Number(metric.value)) ? Number(metric.value).toFixed(Number(metric.value) % 1 === 0 ? 0 : 2) : escHtml(metric.value));
  const unit = metric?.unit ? `<span>${escHtml(metric.unit)}</span>` : "";
  return `
    <div class="miniMetric ${statusClass(metric?.status)}">
      <div class="miniMetricName">${escHtml(metric?.name || "")}</div>
      <div class="miniMetricValue">${value}${unit}</div>
      ${metric?.ref ? `<div class="miniMetricRef">${escHtml(metric.ref)}</div>` : ""}
    </div>
  `;
}
```

- [ ] **Step 3: Add chart router**

Add:

```javascript
function renderSectionChart(section) {
  const type = section?.chart_type;
  const chart = section?.chart || {};
  if (type === "reference_bars") return svgBarVitals(chart);
  if (type === "radar") return svgRadar(chart);
  if (type === "stacked_mix") return svgStackedMix(chart);
  if (type === "recovery_bars") return svgRecoveryBars(chart);
  if (type === "risk_tiles") return svgRiskTiles(chart);
  return svgStabilityChart(chart);
}
```

- [ ] **Step 4: Add new SVG helpers**

Add lightweight helpers after existing chart helpers:

```javascript
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
  const html = tiles.length ? tiles.map((tile) => `
    <div class="riskTile ${statusClass(tile.status)}">
      <span>${escHtml(tile.label || "Image")}</span>
      <strong>${tile.score === undefined || tile.score === null ? "—" : escHtml(String(tile.score))}</strong>
      <em>${escHtml(tile.status || "normal")}</em>
    </div>
  `).join("") : `<div class="riskTile muted"><span>No image signals</span><strong>—</strong><em>missing</em></div>`;
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
  return `
    <svg viewBox="0 0 360 150" role="img" aria-label="stability trend">
      <rect x="1" y="1" width="358" height="148" rx="12" fill="#fff" stroke="rgba(230,232,239,.9)"/>
      <rect x="18" y="34" width="${(324 * score).toFixed(1)}" height="18" rx="9" fill="${score >= 0.7 ? "#22c55e" : score >= 0.4 ? "#f97316" : "#ef4444"}"/>
      <rect x="18" y="34" width="324" height="18" rx="9" fill="none" stroke="rgba(15,23,42,.12)"/>
      <polyline points="${points}" fill="none" stroke="#0f172a" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/>
      <text x="18" y="26" font-size="12" font-weight="800" fill="#0f172a">Stability ${Math.round(score * 100)}%</text>
    </svg>
  `;
}
```

- [ ] **Step 5: Add dynamic renderer**

Add:

```javascript
function renderDynamicHealthReport(report, plaintextPrompt) {
  const panel = $("conclusionPanel");
  const recoPanel = $("recommendPanel");
  if (!panel) return;

  const summary = report.summary || {};
  const badge = statusBadge(summary.overall || report.overall);
  const expandedSections = Array.isArray(report.sections) ? report.sections : [];
  const compactSections = Array.isArray(report.compact_sections) ? report.compact_sections : [];
  const missingSignals = Array.isArray(report.missing_signals) ? report.missing_signals : [];
  const drivers = (summary.drivers || report.fall_risk?.drivers || []).map((item) => `<span class="chip">${escHtml(item)}</span>`).join("");

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
    <section class="storySection ${statusClass(section.status)}">
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
        <div class="compactSection ${statusClass(section.status)}">
          <div class="compactSectionHead">
            <strong>${escHtml(section.title || "")}</strong>
            <span>${(section.source_modalities || []).map((item) => escHtml(String(item).toUpperCase())).join(" + ")}</span>
          </div>
          <div class="compactChart">${renderSectionChart(section)}</div>
        </div>
      `).join("")}
    </div>
  ` : "";

  panel.innerHTML = `
    <div class="reportProtectionBanner">
      <span>Protected output</span>
      Structured report keeps true encoded inference results, while the narrative is generated from the bucketed summary.
    </div>
    <div class="dynamicReportTop">
      <section class="integratedSummary">
        <div class="summaryHead">
          <div>
            <div class="reportTitle">${escHtml(summary.title || "Integrated Summary")}</div>
            <div class="summaryScore">${Math.round(Number(summary.health_index || 0) * 100)}%</div>
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
```

- [ ] **Step 6: Run a syntax check**

Run:

```bash
node --check frontend/assets/js/app.js
```

Expected: no syntax errors.

## Task 5: Frontend Styling

**Files:**
- Modify: `frontend/assets/css/styles.css`

- [ ] **Step 1: Add layout styles**

Append these styles near the existing report styles:

```css
.dynamicReportTop {
  display: grid;
  grid-template-columns: minmax(0, 1.2fr) minmax(260px, .8fr);
  gap: 14px;
  margin-bottom: 14px;
}

.integratedSummary,
.missingSignals,
.storySection,
.compactSection {
  border: 1px solid rgba(226, 232, 240, .9);
  background: #fff;
  border-radius: 12px;
}

.integratedSummary {
  padding: 16px;
  background: #0f172a;
  color: #fff;
}

.summaryHead,
.storySectionHead,
.compactSectionHead {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.summaryScore {
  margin-top: 6px;
  font-size: 34px;
  line-height: 1;
  font-weight: 900;
}

.summaryTrack {
  height: 10px;
  overflow: hidden;
  border-radius: 999px;
  background: rgba(255, 255, 255, .16);
  margin: 14px 0 12px;
}

.summaryTrack i {
  display: block;
  height: 100%;
  border-radius: inherit;
  background: linear-gradient(90deg, #f97316, #22c55e);
}

.missingSignals {
  padding: 14px;
  background: #fff7ed;
  border-color: #fed7aa;
}

.missingTitle {
  color: #9a3412;
  font-size: 12px;
  font-weight: 900;
  letter-spacing: .08em;
  text-transform: uppercase;
}

.missingItem {
  display: grid;
  gap: 4px;
  margin-top: 10px;
  color: #7c2d12;
}

.missingItem span {
  font-size: 12px;
  line-height: 1.35;
}

.storySectionStack {
  display: grid;
  gap: 14px;
}

.storySection {
  padding: 14px;
}

.storySectionHead h3 {
  margin: 0;
  font-size: 16px;
}

.storySectionHead p {
  margin: 6px 0 0;
  color: #64748b;
  font-size: 13px;
  line-height: 1.45;
}

.sourceTags {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 6px;
}

.sourceTag {
  border-radius: 999px;
  background: #eef2ff;
  color: #3730a3;
  padding: 4px 8px;
  font-size: 11px;
  font-weight: 900;
}

.storySectionBody {
  display: grid;
  grid-template-columns: minmax(0, 1.35fr) minmax(180px, .65fr);
  gap: 12px;
  margin-top: 12px;
}

.storyChart {
  min-height: 170px;
}

.storyMetrics {
  display: grid;
  grid-template-columns: 1fr;
  gap: 8px;
}

.miniMetric {
  border: 1px solid #e2e8f0;
  background: #f8fafc;
  border-radius: 10px;
  padding: 9px;
}

.miniMetricName,
.miniMetricRef {
  color: #64748b;
  font-size: 11px;
  font-weight: 700;
}

.miniMetricValue {
  margin-top: 3px;
  color: #0f172a;
  font-size: 18px;
  font-weight: 900;
}

.miniMetricValue span {
  margin-left: 3px;
  font-size: 11px;
  color: #64748b;
}

.compactSectionGrid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
  margin-top: 14px;
}

.compactSection {
  padding: 12px;
}

.compactSectionHead strong {
  font-size: 13px;
}

.compactSectionHead span {
  color: #64748b;
  font-size: 11px;
  font-weight: 800;
}

.compactChart {
  margin-top: 10px;
  max-height: 90px;
  overflow: hidden;
}

.recoveryBars {
  display: grid;
  gap: 10px;
  padding: 14px;
  border: 1px solid #e2e8f0;
  background: #fff;
  border-radius: 12px;
}

.recoveryRow {
  display: grid;
  grid-template-columns: 120px 1fr 34px;
  gap: 10px;
  align-items: center;
  font-size: 12px;
  font-weight: 800;
}

.recoveryTrack {
  height: 10px;
  border-radius: 999px;
  background: #e2e8f0;
  overflow: hidden;
}

.recoveryTrack i {
  display: block;
  height: 100%;
  border-radius: inherit;
  background: linear-gradient(90deg, #06b6d4, #7c3aed);
}

.riskTileGrid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px;
}

.riskTile {
  border: 1px solid #e2e8f0;
  background: #f8fafc;
  border-radius: 10px;
  padding: 10px;
  display: grid;
  gap: 4px;
}

.riskTile strong {
  font-size: 18px;
}

.riskTile em {
  color: #64748b;
  font-size: 11px;
  font-style: normal;
  font-weight: 800;
}

@media (max-width: 920px) {
  .dynamicReportTop,
  .storySectionBody,
  .compactSectionGrid {
    grid-template-columns: 1fr;
  }

  .sourceTags {
    justify-content: flex-start;
  }
}
```

- [ ] **Step 2: Run frontend syntax check again**

Run:

```bash
node --check frontend/assets/js/app.js
```

Expected: no syntax errors.

## Task 6: End-to-End Verification

**Files:**
- Verify: `backend/app.py`
- Verify: `frontend/assets/js/app.js`
- Verify: `frontend/assets/css/styles.css`
- Verify: `backend/tests/test_app_contract.py`

- [ ] **Step 1: Run all backend tests**

Run:

```bash
source venv/bin/activate && PYTHONPATH=. pytest backend/tests -v
```

Expected: all backend tests pass.

- [ ] **Step 2: Run frontend syntax check**

Run:

```bash
node --check frontend/assets/js/app.js
```

Expected: no syntax errors.

- [ ] **Step 3: Start backend on an allowed port**

Check port:

```bash
python - <<'PY'
import socket
for port in [8082, 8083, 8084]:
    with socket.socket() as sock:
        try:
            sock.bind(("127.0.0.1", port))
        except OSError:
            continue
        print(port)
        break
PY
```

Expected: prints an available port such as `8082`.

Start backend using the printed port:

```bash
source venv/bin/activate && cd backend && uvicorn app:app --host 127.0.0.1 --port 8082
```

- [ ] **Step 4: Start frontend on the preferred port**

Check port:

```bash
python - <<'PY'
import socket
with socket.socket() as sock:
    sock.bind(("127.0.0.1", 8001))
print("8001")
PY
```

Expected: prints `8001`.

Start frontend:

```bash
cd frontend && python -m http.server 8001
```

- [ ] **Step 5: Manual browser verification**

Open:

```text
http://127.0.0.1:8001
```

Run these checks:

- Select only `IMU Sensor`; report shows `Mobility & Fall Stability` and `Activity Pattern`, plus missing signals for vitals, sleep, medical screening, and integrated risk.
- Select `Depth Camera`, `UWB Radar`, `IMU Sensor`, `WiFi CSI`, and `RGB Camera`; report shows `Integrated Summary` and no more than three expanded sections.
- Select medical image modalities; report includes `Medical Image Screening` with tile-style visuals.
- Check mobile-width browser view; story sections stack vertically and text stays inside cards.

- [ ] **Step 6: Check worktree before handoff**

Run:

```bash
git status --short
git diff --stat
```

Expected: changed files match this plan. Do not commit unless the user explicitly asks for a commit.

## Self-Review Checklist

- Spec coverage: The plan covers AGENTS rule update, backend dynamic schema, privacy prompt bucketing, frontend dynamic section rendering, styling, and verification.
- Placeholder scan: The plan contains concrete paths, commands, expected outputs, and code snippets. It avoids unresolved placeholder markers and unspecified "add handling" instructions.
- Type consistency: Backend keys are `summary`, `missing_signals`, `sections`, `compact_sections`, `source_modalities`, `chart_type`, `chart`, `metrics`, and `insight`; frontend code uses the same keys.
