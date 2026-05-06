# Shuffle Privacy Protection Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

## Goal

Implement a real shuffle-based privacy protection layer between encrypted inference and the final health report.

The final displayed report must not directly expose the raw target-user Step 3 output.
Instead:

1. backend computes the raw outcome internally
2. backend derives a coarse privacy profile
3. backend generates a synthetic candidate pool
4. backend shuffles the pool and selects one protected candidate
5. frontend shows a distinct `Shuffle Privacy Protection` stage
6. frontend renders the final report from the protected candidate only

## Guardrails

- Preserve the current visual language and report widgets.
- Do not replace the current report layout with a new design system.
- Keep `backend/app.py` as the canonical backend entrypoint.
- Keep `backend/simple_app.py` compatible by continuing to point at `backend/app.py`.
- Do not automatically commit; repository guidance forbids automatic commits.
- Respect the current dirty worktree in frontend files and make surgical edits only.

## File Map

### Backend

- `backend/app.py`
  - Keep route wiring, current API surface, and final payload assembly.
  - Add the new `privacy_protection` response block.
  - Route final displayed `step3.results`, `step3.report`, and `step3.report_conclusion` through the protected candidate.

- `backend/privacy_shuffle.py`
  - New focused module for privacy-profile derivation, synthetic candidate generation, shuffle, protected selection, and frontend-facing summary cards.
  - Keeps `app.py` from growing further and isolates the novelty logic.

- `backend/tests/test_app_contract.py`
  - Extend the current contract tests to cover the new `privacy_protection` block and protected Step 3 behavior.

- `backend/tests/test_privacy_shuffle.py`
  - New focused unit tests for `privacy_shuffle.py`.

### Frontend

- `frontend/index.html`
  - Change the visible flow from 3 cards to 4 cards.
  - Add a dedicated Step 3 card for `Shuffle Privacy Protection`.
  - Renumber the current report card to Step 4.

- `frontend/assets/js/app.js`
  - Add `renderPrivacyProtection()` for the new Step 3 card.
  - Keep `renderHealthReport()` as the Step 4 renderer.
  - Add a small helper to safely render privacy candidate chips/cards from backend metadata.

- `frontend/assets/js/modality-selector.js`
  - Update orchestration so Step 3 pill/status is filled from `privacy_protection`.
  - Move the current report completion status to Step 4.
  - Call `renderPrivacyProtection()` before `renderHealthReport()`.

- `frontend/assets/css/styles.css`
  - Update the grid layout for the 4-step flow.
  - Add compact card styles for the privacy stage.
  - Keep the current report card spacious.

- `frontend/assets/css/enhancement.css`
  - Add only delta styles if the existing base stylesheet is already crowded.

## Test Strategy

- Use `unittest`, not `pytest`; `pytest` is not installed in the project venv.
- Patch out external LLM calls in backend tests.
- Verify both API contract and privacy-helper logic.
- Verify the final live API with `uvicorn app:app --host 127.0.0.1 --port 8082`.

## Tasks

### Phase 1: Lock the New Backend Contract With Failing Tests

- [ ] **Step 1: Extend the API contract test file with a failing privacy-stage test**

Edit `backend/tests/test_app_contract.py` and add this test method inside `AppContractTests`:

```python
    async def test_cycle_returns_privacy_protection_block(self):
        response = await self.client.get(
            "/api/cycle",
            params={"selected_modalities": "depth,uwb,imu,csi,rgb"},
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        privacy = payload.get("privacy_protection")

        self.assertIsInstance(privacy, dict)
        self.assertTrue(privacy.get("enabled"))
        self.assertEqual(privacy.get("method"), "synthetic_shuffle")
        self.assertEqual(privacy.get("pool_size"), 10)
        self.assertIsInstance(privacy.get("display_candidates"), list)
        self.assertGreaterEqual(len(privacy.get("display_candidates", [])), 3)
        self.assertLessEqual(len(privacy.get("display_candidates", [])), 5)
        self.assertIsInstance(privacy.get("summary"), str)
```

- [ ] **Step 2: Extend the API contract test file with a failing protected-report test**

In the same file, add:

```python
    async def test_cycle_routes_display_report_through_protected_output(self):
        response = await self.client.get(
            "/api/cycle",
            params={"selected_modalities": "depth,uwb,imu,csi,rgb"},
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        privacy = payload["privacy_protection"]
        report = payload["step3"]["report"]
        results = payload["step3"]["results"]

        self.assertEqual(privacy["selected_label"], "Protected Output")
        self.assertIsInstance(report.get("overall"), str)
        self.assertIsInstance(report.get("metrics"), list)
        self.assertIsInstance(results, list)
        self.assertEqual(len(results), 5)
```

- [ ] **Step 3: Run the contract tests to capture the red state**

Run:

```bash
source /home/hkustgz/Us/Encry_LLM_HealthReport/venv/bin/activate
cd /home/hkustgz/Us/Encry_LLM_HealthReport
python -m unittest backend.tests.test_app_contract -v
```

Expected:

- current contract tests still pass
- new privacy-stage tests fail because `privacy_protection` is not returned yet

### Phase 2: Add a Focused Backend Privacy Module

- [ ] **Step 4: Create a failing unit-test file for privacy shuffle helpers**

Create `backend/tests/test_privacy_shuffle.py` with:

```python
import random
import unittest

from backend.privacy_shuffle import (
    build_display_candidates,
    derive_privacy_profile,
    generate_synthetic_candidate_pool,
    select_protected_candidate,
)


class PrivacyShuffleTests(unittest.TestCase):
    def setUp(self):
        self.raw_results = [
            {"model": "ECG Arrhythmia", "model_id": "ecg", "input_modality": "WiFi CSI", "tool": "secure_ecg_toolbox", "score": 75.5, "status": "normal"},
            {"model": "Blood Pressure", "model_id": "bp", "input_modality": "UWB Radar", "tool": "secure_bp_toolbox", "score": 142.0, "status": "elevated"},
            {"model": "Sleep Staging", "model_id": "sleep", "input_modality": "Depth Camera", "tool": "secure_sleep_toolbox", "score": 68.0, "status": "low"},
            {"model": "Metabolic Score", "model_id": "metabolic", "input_modality": "IMU Sensor", "tool": "secure_metabolic_toolbox", "score": 52.0, "status": "normal"},
            {"model": "Risk Assessment", "model_id": "risk", "input_modality": "RGB Camera", "tool": "secure_risk_toolbox", "score": 0.41, "status": "moderate"},
        ]
        self.raw_report = {
            "overall": "Watch",
            "fall_risk": {
                "level": "Moderate",
                "probability": 0.41,
                "drivers": ["BP elevated", "Sleep reduced"],
            },
            "metrics": [
                {"name": "Heart Rate", "value": 76, "unit": "bpm", "ref": "60-100", "status": "normal"},
                {"name": "Respiratory Rate", "value": 17, "unit": "rpm", "ref": "12-20", "status": "normal"},
                {"name": "Blood Pressure", "value": 142, "unit": "mmHg", "ref": "<120", "status": "high"},
                {"name": "SpO2", "value": 97, "unit": "%", "ref": "95-100", "status": "normal"},
                {"name": "Sleep Efficiency", "value": 68, "unit": "%", "ref": ">85", "status": "low"},
                {"name": "Cadence", "value": 91, "unit": "spm", "ref": "90-120", "status": "normal"},
            ],
            "recommendations": ["Reduce sodium intake", "Improve sleep hygiene"],
            "narrative": "Overall status: Watch.",
            "charts": {
                "activity_mix": {"labels": ["Walk", "Stand", "Sit", "Sleep"], "values": [0.21, 0.18, 0.24, 0.37]},
                "radar": {"labels": ["Cardio", "BP", "Sleep", "Metabolic", "Recovery", "Safety"], "values": [68, 54, 51, 62, 58, 60]},
                "vitals": {"labels": ["HR", "RR", "BP", "SpO2"], "values": [76, 17, 142, 97], "refs": [80, 16, 120, 98]},
                "sparklines": {},
            },
            "disclaimer": "Demo output only — not for medical use.",
        }

    def test_derive_privacy_profile_returns_bucketed_fields(self):
        profile = derive_privacy_profile(self.raw_results, self.raw_report)
        self.assertEqual(profile["overall"], "Watch")
        self.assertEqual(profile["risk_level"], "Moderate")
        self.assertIn("metric_buckets", profile)

    def test_generate_candidate_pool_returns_requested_size(self):
        rng = random.Random(42)
        profile = derive_privacy_profile(self.raw_results, self.raw_report)
        pool = generate_synthetic_candidate_pool(profile, self.raw_results, self.raw_report, pool_size=10, rng=rng)
        self.assertEqual(len(pool), 10)

    def test_select_protected_candidate_returns_single_candidate_after_shuffle(self):
        rng = random.Random(42)
        profile = derive_privacy_profile(self.raw_results, self.raw_report)
        pool = generate_synthetic_candidate_pool(profile, self.raw_results, self.raw_report, pool_size=10, rng=rng)
        protected = select_protected_candidate(pool, rng=rng)
        self.assertIn("results", protected)
        self.assertIn("report", protected)

    def test_build_display_candidates_limits_frontend_exposure(self):
        rng = random.Random(42)
        profile = derive_privacy_profile(self.raw_results, self.raw_report)
        pool = generate_synthetic_candidate_pool(profile, self.raw_results, self.raw_report, pool_size=10, rng=rng)
        cards = build_display_candidates(pool, limit=4)
        self.assertEqual(len(cards), 4)
        self.assertIn("metric_summary", cards[0])
        self.assertNotIn("results", cards[0])


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 5: Run the new helper tests to verify the missing module fails**

Run:

```bash
source /home/hkustgz/Us/Encry_LLM_HealthReport/venv/bin/activate
cd /home/hkustgz/Us/Encry_LLM_HealthReport
python -m unittest backend.tests.test_privacy_shuffle -v
```

Expected:

- import failure because `backend/privacy_shuffle.py` does not exist yet

- [ ] **Step 6: Create `backend/privacy_shuffle.py` with the minimal helper API**

Create `backend/privacy_shuffle.py` with this starting structure:

```python
import copy
import random
from typing import Any, Dict, List


def derive_privacy_profile(raw_results: List[Dict[str, Any]], raw_report: Dict[str, Any]) -> Dict[str, Any]:
    metric_buckets = []
    for metric in raw_report.get("metrics", []):
        metric_buckets.append(
            {
                "name": metric.get("name"),
                "status": metric.get("status"),
                "unit": metric.get("unit"),
            }
        )

    return {
        "overall": raw_report.get("overall", "Watch"),
        "risk_level": raw_report.get("fall_risk", {}).get("level", "Moderate"),
        "metric_buckets": metric_buckets,
    }


def _jitter_numeric(value: Any, rng: random.Random, spread: float) -> Any:
    if not isinstance(value, (int, float)):
        return value
    return round(float(value) + rng.uniform(-spread, spread), 1)


def _mutate_results(raw_results: List[Dict[str, Any]], rng: random.Random) -> List[Dict[str, Any]]:
    mutated = copy.deepcopy(raw_results)
    for row in mutated:
        row["score"] = _jitter_numeric(row.get("score"), rng, 6.0)
    return mutated


def _mutate_report(raw_report: Dict[str, Any], rng: random.Random) -> Dict[str, Any]:
    report = copy.deepcopy(raw_report)
    for metric in report.get("metrics", []):
        metric["value"] = _jitter_numeric(metric.get("value"), rng, 5.0)
    if "fall_risk" in report and "probability" in report["fall_risk"]:
        report["fall_risk"]["probability"] = max(
            0.05,
            min(0.95, _jitter_numeric(report["fall_risk"]["probability"], rng, 0.08)),
        )
    return report


def generate_synthetic_candidate_pool(
    profile: Dict[str, Any],
    raw_results: List[Dict[str, Any]],
    raw_report: Dict[str, Any],
    pool_size: int,
    rng: random.Random,
) -> List[Dict[str, Any]]:
    pool = []
    for idx in range(pool_size):
        pool.append(
            {
                "label": f"Candidate {idx + 1}",
                "profile": profile,
                "results": _mutate_results(raw_results, rng),
                "report": _mutate_report(raw_report, rng),
            }
        )
    return pool


def select_protected_candidate(pool: List[Dict[str, Any]], rng: random.Random) -> Dict[str, Any]:
    shuffled = list(pool)
    rng.shuffle(shuffled)
    selected = copy.deepcopy(shuffled[0])
    selected["label"] = "Protected Output"
    return selected


def build_display_candidates(pool: List[Dict[str, Any]], limit: int = 4) -> List[Dict[str, Any]]:
    cards = []
    for candidate in pool[:limit]:
        report = candidate["report"]
        fall_risk = report.get("fall_risk", {})
        metric_summary = []
        for metric in report.get("metrics", []):
            status = str(metric.get("status", "")).lower()
            if status in {"low", "elevated", "high", "moderate"}:
                metric_summary.append(f"{metric.get('name')} {status}")
            if len(metric_summary) == 3:
                break
        cards.append(
            {
                "label": candidate["label"],
                "overall": report.get("overall", "Watch"),
                "risk_level": fall_risk.get("level", "Moderate"),
                "metric_summary": metric_summary or ["Protected summary"],
            }
        )
    return cards
```

- [ ] **Step 7: Run the helper unit tests to verify the privacy module turns green**

Run:

```bash
source /home/hkustgz/Us/Encry_LLM_HealthReport/venv/bin/activate
cd /home/hkustgz/Us/Encry_LLM_HealthReport
python -m unittest backend.tests.test_privacy_shuffle -v
```

Expected:

- all tests in `backend.tests.test_privacy_shuffle` pass

### Phase 3: Wire the Backend Route Through Protected Output

- [ ] **Step 8: Import the new privacy helpers into `backend/app.py`**

Add near the top of `backend/app.py`:

```python
import random

from privacy_shuffle import (
    build_display_candidates,
    derive_privacy_profile,
    generate_synthetic_candidate_pool,
    select_protected_candidate,
)
```

- [ ] **Step 9: Insert protected-selection logic after the raw report is built**

In `backend/app.py`, inside `run_cycle()`, replace the current direct-finalization path:

```python
        report = build_health_report(results, uwb_for_report, imu_for_report, csi_for_report)
```

with:

```python
        raw_results = results
        raw_report = build_health_report(results, uwb_for_report, imu_for_report, csi_for_report)
        rng = random.Random(int(start_time))
        profile = derive_privacy_profile(raw_results, raw_report)
        candidate_pool = generate_synthetic_candidate_pool(
            profile,
            raw_results,
            raw_report,
            pool_size=10,
            rng=rng,
        )
        protected_candidate = select_protected_candidate(candidate_pool, rng=rng)
        display_candidates = build_display_candidates(candidate_pool, limit=4)

        results = protected_candidate["results"]
        report = protected_candidate["report"]
```

- [ ] **Step 10: Add the new `privacy_protection` block to the response payload**

In the final `return` of `run_cycle()`, add:

```python
        "privacy_protection": {
            "enabled": True,
            "method": "synthetic_shuffle",
            "pool_size": 10,
            "display_candidates": display_candidates,
            "selected_label": "Protected Output",
            "summary": "Final report selected from shuffled synthetic candidates.",
        },
```

- [ ] **Step 11: Keep the LLM prompt routed through the protected report only**

Do not change the existing prompt structure, but confirm it reads from the post-selection `report` object, not `raw_report`.

The code around this section must look like:

```python
        activity_mix = report["charts"]["activity_mix"]
        radar_scores = report["charts"]["radar"]["values"]
        llm_prompt = f"""..."""
        report_conclusion = await call_zhipu_llm(llm_prompt)
```

and must not reference `raw_report` in the prompt.

- [ ] **Step 12: Run the contract tests again to verify the backend turns green**

Run:

```bash
source /home/hkustgz/Us/Encry_LLM_HealthReport/venv/bin/activate
cd /home/hkustgz/Us/Encry_LLM_HealthReport
python -m unittest backend.tests.test_app_contract backend.tests.test_privacy_shuffle -v
```

Expected:

- all contract tests pass
- all privacy helper tests pass

### Phase 4: Add the New Frontend Stage Without Breaking the Report UI

- [ ] **Step 13: Update `frontend/index.html` to expose a fourth card**

Change the step layout so the cards become:

```html
      <div class="card" id="stepUpload">
        <div class="cardHead">
          <div class="stepTag">1</div>
          <div class="cardTitle">选择数据模态</div>
          <div class="meta"><span class="pill" id="tUpload">—</span></div>
        </div>
      </div>

      <div class="card" id="stepProtect">
        <div class="cardHead">
          <div class="stepTag">3</div>
          <div class="cardTitle">Shuffle Privacy Protection</div>
          <div class="meta"><span class="pill" id="tProtect">—</span></div>
        </div>
        <div class="cardBody">
          <div class="subTitle">Synthetic candidate protection</div>
          <div class="privacyPanel" id="privacyPanel">Loading...</div>
        </div>
      </div>

      <div class="card" id="stepDispatch">
        <div class="cardHead">
          <div class="stepTag">2</div>
          <div class="cardTitle">DeepSeek Dispatch → Homomorphic Prediction Model Cluster</div>
          <div class="meta"><span class="pill" id="tDispatch">—</span></div>
        </div>
      </div>

      <div class="card" id="stepDecrypt">
        <div class="cardHead">
          <div class="stepTag">4</div>
          <div class="cardTitle">Protected Health Report</div>
          <div class="meta"><span class="pill" id="tDecrypt">—</span></div>
        </div>
      </div>
```

- [ ] **Step 14: Update the stylesheet grid for the 4-step layout**

In `frontend/assets/css/styles.css`, adjust the grid placement to:

```css
#stepUpload {
  grid-row: 1;
  grid-column: 1;
}

#stepProtect {
  grid-row: 1;
  grid-column: 2;
}

#stepDispatch {
  grid-row: 1 / 3;
  grid-column: 3;
  display: flex;
  flex-direction: column;
}

#stepDecrypt {
  grid-row: 2;
  grid-column: 1 / 3;
}
```

Then add compact privacy-stage styles:

```css
.privacyPanel {
  display: grid;
  gap: 10px;
}

.privacySummary {
  padding: 10px 12px;
  border: 1px solid var(--line);
  border-radius: 12px;
  background: linear-gradient(180deg, #ffffff, #fbfcff);
  color: var(--muted);
  font-size: 13px;
}

.privacyCandidateGrid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
}

.privacyCandidateCard {
  border: 1px solid var(--line);
  border-radius: 14px;
  padding: 10px;
  background: #fff;
}

.privacyChipRow {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 8px;
}
```

- [ ] **Step 15: Add a dedicated privacy-stage renderer in `frontend/assets/js/app.js`**

Add this function near `renderHealthReport()`:

```javascript
function renderPrivacyProtection(privacy) {
  const panel = $("privacyPanel");
  if (!panel) return;
  if (!privacy || !privacy.enabled) {
    panel.innerHTML = '<div class="hint">Privacy protection data unavailable.</div>';
    return;
  }

  const cards = (privacy.display_candidates || []).map((candidate) => {
    const chips = (candidate.metric_summary || [])
      .map((item) => `<span class="chip">${escHtml(item)}</span>`)
      .join("");

    return `
      <div class="privacyCandidateCard">
        <div class="reportCardHead">
          <div class="metricName">${escHtml(candidate.label || "Candidate")}</div>
          <div class="chip">${escHtml(candidate.risk_level || "Protected")}</div>
        </div>
        <div class="metricDetail">${escHtml(candidate.overall || "Watch")}</div>
        <div class="privacyChipRow">${chips}</div>
      </div>
    `;
  }).join("");

  panel.innerHTML = `
    <div class="privacySummary">
      <strong>Shuffle protection active.</strong>
      ${escHtml(privacy.summary || "")}
    </div>
    <div class="privacyCandidateGrid">${cards}</div>
    <div class="privacySummary">
      Selected output: ${escHtml(privacy.selected_label || "Protected Output")}
    </div>
  `;
}
```

- [ ] **Step 16: Update `modality-selector.js` to render the privacy stage before the report**

Inside `handleResults(data)`, insert:

```javascript
    const privacy = data.privacy_protection || {};
    if (typeof renderPrivacyProtection === "function") {
      renderPrivacyProtection(privacy);
      const tProtect = document.getElementById("tProtect");
      if (tProtect) {
        tProtect.className = "pill success";
        tProtect.textContent = privacy.enabled ? "Done" : "Unavailable";
      }
    }
```

Then keep the current report rendering below it, but treat it as Step 4.
Do not delete the existing `renderHealthReport(s3.report)` path.

- [ ] **Step 17: Update any user-facing report titles to reflect protected output**

In `modality-selector.js`, change the results title update block so it uses a protected framing:

```javascript
          resultsTitle.textContent = `Key results (${count} protected modalities: ${modalityNames})`;
```

Do not rename the report widgets themselves.

### Phase 5: Full Verification

- [ ] **Step 18: Run the backend test suite again after the frontend wiring changes**

Run:

```bash
source /home/hkustgz/Us/Encry_LLM_HealthReport/venv/bin/activate
cd /home/hkustgz/Us/Encry_LLM_HealthReport
python -m unittest backend.tests.test_app_contract backend.tests.test_privacy_shuffle -v
```

Expected:

- all backend tests still pass

- [ ] **Step 19: Start the backend and verify the live API shape**

Run:

```bash
source /home/hkustgz/Us/Encry_LLM_HealthReport/venv/bin/activate
cd /home/hkustgz/Us/Encry_LLM_HealthReport/backend
uvicorn app:app --host 127.0.0.1 --port 8082
```

In another shell:

```bash
python3 - <<'PY'
import json, urllib.request
with urllib.request.urlopen(
    "http://127.0.0.1:8082/api/cycle?selected_modalities=depth,uwb,imu,csi,rgb",
    timeout=120,
) as resp:
    data = json.load(resp)
print("privacy keys:", sorted(data["privacy_protection"].keys()))
print("candidate count:", len(data["privacy_protection"]["display_candidates"]))
print("selected:", data["privacy_protection"]["selected_label"])
print("results count:", len(data["step3"]["results"]))
print("report overall:", data["step3"]["report"]["overall"])
PY
```

Expected:

- `privacy_protection` block exists
- 3 to 5 display candidates are returned
- `selected_label` is present
- Step 3 results still return 5 protected rows for the selected modalities

- [ ] **Step 20: Start the frontend and visually verify the four-step flow**

Run:

```bash
cd /home/hkustgz/Us/Encry_LLM_HealthReport/frontend
python3 -m http.server 8001
```

Open:

```text
http://127.0.0.1:8001
```

Manual checks:

- card 1 still lets the user select modalities
- card 2 still shows dispatch and ciphertext preview
- card 3 shows synthetic candidate summaries and privacy explanation
- card 4 still shows the report cards, charts, recommendations, and conclusion
- report stage does not visibly expose a raw-target-only output path

## Notes for the Implementer

- No commit steps are included because repository guidance says not to commit automatically.
- Preserve existing frontend dirty changes where possible; patch around them instead of reformatting wholesale.
- Prefer adding `privacy_shuffle.py` over packing more helper logic into `app.py`.
- The first iteration can use deterministic jittered synthetic candidates; if the demo needs stronger novelty later, improve the candidate generator without changing the API contract.

## Self-Review

Spec coverage check:

- 4-stage frontend flow: covered in Steps 13, 14, 16, and 20
- independent `Shuffle Privacy Protection` stage: covered in Steps 13, 15, and 20
- whole final report protected, not just text: covered in Steps 9, 10, 11, and 19
- backend shuffle-based protection: covered in Steps 4 through 12
- medium-strength frontend explanation with candidate summaries: covered in Steps 10, 15, and 20

Placeholder scan:

- no `TODO` / `TBD`
- every changed file path is explicit
- every verification command is explicit

Type consistency check:

- backend response key is always `privacy_protection`
- frontend renderer name is always `renderPrivacyProtection`
- protected report continues to live under `step3.report`

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-05-02-shuffle-privacy-protection.md`.

Two execution options:

1. Subagent-Driven (recommended) - dispatch a fresh subagent per task, review between tasks
2. Inline Execution - execute tasks in this session with checkpoints
