# Synthetic Database Privacy Refactor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the current candidate-report shuffle with a synthetic database workflow where fake data records hide the true homomorphic inference record, and only a bucketed summary is sent to the non-trusted LLM.

**Architecture:** The backend keeps the precise real inference result for dashboard rendering, generates valid fake data records from constrained distributions, inserts the real record into an anonymous database, shuffles it, and uses a hidden token to recover the real record. The LLM receives only a bucketed, generalized summary; the report UI keeps the current structured charts and precise dashboard report.

**Tech Stack:** Python/FastAPI backend, standard `random` data generation, existing `unittest` backend tests, static HTML/CSS/JavaScript frontend, Playwright browser checks in `temp/`.

---

## Design Boundary

The privacy flow should be:

```text
raw_results + raw_report
  -> build_real_data_record()
  -> generate_synthetic_database()
  -> insert_real_record()
  -> shuffle_anonymous_database()
  -> select_real_record_with_hidden_token()
  -> build_protected_llm_summary()
  -> call_zhipu_llm(protected_llm_summary)
  -> return dashboard report + privacy visualization payload
```

The report page keeps the current version: charts, metric cards, risk probability, activity mix, radar, and vitals still come from the real structured backend report. The LLM is a non-trusted external party and must only receive bucketed or generalized real-record summary fields.

Remove these concepts from the privacy visualization and API naming:

- Candidate report
- Quality gate
- Door rejection
- Pass/fail generated reports
- Random report selection

Use these concepts instead:

- Anonymous data record
- Synthetic database
- Constraint-based generator
- Real record hidden insertion
- Shuffle and linkage masking
- Hidden selection token
- Bucketed summary for non-trusted LLM

---

## File Structure

- Modify: `backend/privacy_shuffle.py`
  - Own synthetic database generation, anonymous database shuffling, hidden real-record selection, display previews, and bucketed LLM summary construction.

- Modify: `backend/app.py`
  - Replace candidate-report privacy flow in `_build_privacy_and_report()` and `/api/cycle`.
  - Keep `step3.report` as the current precise dashboard report.
  - Send only bucketed summary data into `call_zhipu_llm()`.

- Modify: `backend/tests/test_privacy_shuffle.py`
  - Add tests for real record construction, synthetic database generation, hidden insertion, shuffled selection, preview redaction, and bucketed summary.

- Modify: `backend/tests/test_app_contract.py`
  - Update API contract from `synthetic_shuffle`/candidate reports to `synthetic_database_shuffle`/anonymous database records.
  - Verify existing report shape is preserved.

- Modify: `frontend/assets/js/app.js`
  - Update privacy panel rendering to use anonymous data records and bucketed LLM summary.
  - Remove quality-gate rendering and candidate-report wording.

- Modify: `frontend/assets/css/styles.css`
  - Remove or neutralize quality-gate-specific visuals.
  - Add minimal styling for synthetic database generator, anonymous records, hidden selection, and LLM summary.

- Modify: `frontend/index.html`
  - Bump cache versions for modified frontend assets.

- Modify: `temp/check_privacy_animation_layout.py`
  - Update string checks and version checks for the new privacy flow.

- Modify: `temp/check_privacy_animation_browser.js`
  - Update animation sequence assertions for synthetic database flow.

- Modify: `temp/check_privacy_responsive_layout.js`
  - Update mock payload and layout selectors for anonymous data records.

- Modify or replace: `temp/check_privacy_selected_candidate.js`
  - Rename behavior mentally to selected anonymous record; verify selected display follows `selected_record_label` or `selected_record_index`.

---

## Task 1: Backend Unit Tests For Synthetic Database Primitives

**Files:**
- Modify: `backend/tests/test_privacy_shuffle.py`
- Modify: `backend/privacy_shuffle.py`

- [ ] **Step 1: Write failing tests for real record construction**

Add tests to `backend/tests/test_privacy_shuffle.py`:

```python
def test_build_real_data_record_keeps_precise_backend_values(self):
    record = build_real_data_record(self.raw_results, self.raw_report)

    self.assertEqual(record["kind"], "real")
    self.assertEqual(record["model_outputs"][0]["score"], 75.5)
    self.assertEqual(record["derived_metrics"]["fall_probability"], 0.41)
    self.assertEqual(record["derived_metrics"]["heart_rate"], 76)
    self.assertEqual(record["derived_metrics"]["blood_pressure"], 142)
    self.assertIn("activity_mix", record["derived_metrics"])
```

- [ ] **Step 2: Run the test and verify it fails**

Run:

```bash
source venv/bin/activate && python -m unittest backend.tests.test_privacy_shuffle.PrivacyShuffleTests.test_build_real_data_record_keeps_precise_backend_values
```

Expected: fail because `build_real_data_record` is not defined or not imported.

- [ ] **Step 3: Implement `build_real_data_record()`**

In `backend/privacy_shuffle.py`, add:

```python
def build_real_data_record(raw_results: List[Dict[str, Any]], raw_report: Dict[str, Any]) -> Dict[str, Any]:
    metrics_by_name = {metric.get("name"): metric for metric in raw_report.get("metrics", [])}
    charts = raw_report.get("charts", {})
    return {
        "kind": "real",
        "label": "Real Record",
        "risk_bucket": str(raw_report.get("fall_risk", {}).get("level", "moderate")).lower(),
        "overall": raw_report.get("overall", "Watch"),
        "model_outputs": copy.deepcopy(raw_results),
        "derived_metrics": {
            "fall_probability": raw_report.get("fall_risk", {}).get("probability"),
            "heart_rate": metrics_by_name.get("Heart Rate", {}).get("value"),
            "respiratory_rate": metrics_by_name.get("Respiratory Rate", {}).get("value"),
            "blood_pressure": metrics_by_name.get("Blood Pressure", {}).get("value"),
            "spo2": metrics_by_name.get("SpO2", {}).get("value"),
            "sleep_efficiency": metrics_by_name.get("Sleep Efficiency", {}).get("value"),
            "cadence": metrics_by_name.get("Cadence", {}).get("value"),
            "activity_mix": copy.deepcopy(charts.get("activity_mix", {})),
            "radar": copy.deepcopy(charts.get("radar", {})),
            "vitals": copy.deepcopy(charts.get("vitals", {})),
        },
    }
```

- [ ] **Step 4: Run the test and verify it passes**

Run the same command as Step 2.

Expected: `OK`.

---

## Task 2: Generate Valid Synthetic Data Records

**Files:**
- Modify: `backend/tests/test_privacy_shuffle.py`
- Modify: `backend/privacy_shuffle.py`

- [ ] **Step 1: Write failing tests for constrained fake records**

Add tests:

```python
def test_generate_synthetic_database_returns_valid_fake_records(self):
    rng = random.Random(123)
    real_record = build_real_data_record(self.raw_results, self.raw_report)

    records = generate_synthetic_database(real_record, database_size=8, rng=rng)

    self.assertEqual(len(records), 8)
    self.assertTrue(all(record["kind"] == "synthetic" for record in records))
    for record in records:
        metrics = record["derived_metrics"]
        self.assertGreaterEqual(metrics["heart_rate"], 45)
        self.assertLessEqual(metrics["heart_rate"], 130)
        self.assertGreaterEqual(metrics["respiratory_rate"], 8)
        self.assertLessEqual(metrics["respiratory_rate"], 30)
        self.assertGreaterEqual(metrics["blood_pressure"], 90)
        self.assertLessEqual(metrics["blood_pressure"], 180)
        self.assertGreaterEqual(metrics["fall_probability"], 0.05)
        self.assertLessEqual(metrics["fall_probability"], 0.95)
        self.assertAlmostEqual(sum(metrics["activity_mix"]["values"]), 1.0, places=3)
```

- [ ] **Step 2: Run the test and verify it fails**

Run:

```bash
source venv/bin/activate && python -m unittest backend.tests.test_privacy_shuffle.PrivacyShuffleTests.test_generate_synthetic_database_returns_valid_fake_records
```

Expected: fail because `generate_synthetic_database` is not defined or not imported.

- [ ] **Step 3: Implement constrained fake record generation**

Add helper functions to `backend/privacy_shuffle.py`:

```python
def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _sample_activity_mix(rng: random.Random) -> Dict[str, Any]:
    labels = ["Walk", "Stand", "Sit", "Sleep"]
    raw = [rng.uniform(0.1, 0.4) for _ in labels]
    total = sum(raw)
    return {"labels": labels, "values": [round(value / total, 4) for value in raw]}


def _status_for_score(score: float) -> str:
    if score >= 85:
        return "good"
    if score >= 65:
        return "normal"
    if score >= 45:
        return "attention"
    return "low"
```

Add:

```python
def generate_synthetic_database(
    real_record: Dict[str, Any],
    database_size: int,
    rng: random.Random,
) -> List[Dict[str, Any]]:
    records = []
    real_metrics = real_record.get("derived_metrics", {})
    real_outputs = real_record.get("model_outputs", [])
    for index in range(database_size):
        fall_probability = round(_clamp(float(real_metrics.get("fall_probability") or 0.25) + rng.uniform(-0.12, 0.12), 0.05, 0.95), 2)
        heart_rate = round(_clamp(float(real_metrics.get("heart_rate") or 76) + rng.uniform(-12, 12), 45, 130))
        respiratory_rate = round(_clamp(float(real_metrics.get("respiratory_rate") or 16) + rng.uniform(-4, 4), 8, 30))
        blood_pressure = round(_clamp(float(real_metrics.get("blood_pressure") or 125) + rng.uniform(-18, 18), 90, 180))
        sleep_efficiency = round(_clamp(float(real_metrics.get("sleep_efficiency") or 82) + rng.uniform(-15, 10), 40, 98))
        cadence = round(_clamp(float(real_metrics.get("cadence") or 92) + rng.uniform(-12, 12), 55, 130))
        model_outputs = []
        for output in real_outputs:
            score = output.get("score")
            if isinstance(score, (int, float)):
                synthetic_score = round(_clamp(float(score) + rng.uniform(-9, 9), 0, 10000), 2)
            else:
                synthetic_score = score
            model_outputs.append({
                **copy.deepcopy(output),
                "score": synthetic_score,
                "status": _status_for_score(float(synthetic_score)) if isinstance(synthetic_score, (int, float)) and float(synthetic_score) <= 100 else output.get("status", "normal"),
            })
        records.append({
            "kind": "synthetic",
            "label": f"Synthetic Record {index + 1}",
            "risk_bucket": "low" if fall_probability < 0.3 else "attention" if fall_probability < 0.6 else "elevated",
            "overall": real_record.get("overall", "Watch"),
            "model_outputs": model_outputs,
            "derived_metrics": {
                "fall_probability": fall_probability,
                "heart_rate": heart_rate,
                "respiratory_rate": respiratory_rate,
                "blood_pressure": blood_pressure,
                "spo2": round(_clamp(float(real_metrics.get("spo2") or 97) + rng.uniform(-2, 2), 90, 100)),
                "sleep_efficiency": sleep_efficiency,
                "cadence": cadence,
                "activity_mix": _sample_activity_mix(rng),
                "radar": copy.deepcopy(real_metrics.get("radar", {})),
                "vitals": copy.deepcopy(real_metrics.get("vitals", {})),
            },
        })
    return records
```

- [ ] **Step 4: Run the test and verify it passes**

Run the same command as Step 2.

Expected: `OK`.

---

## Task 3: Insert, Shuffle, And Select The Real Record With A Hidden Token

**Files:**
- Modify: `backend/tests/test_privacy_shuffle.py`
- Modify: `backend/privacy_shuffle.py`

- [ ] **Step 1: Write failing tests for hidden selection**

Add:

```python
def test_build_anonymous_database_hides_real_record_but_selects_it_by_token(self):
    rng = random.Random(7)
    real_record = build_real_data_record(self.raw_results, self.raw_report)
    fake_records = generate_synthetic_database(real_record, database_size=8, rng=rng)

    bundle = build_anonymous_database(real_record, fake_records, rng=random.Random(7))

    self.assertEqual(bundle["selected_record"]["kind"], "real")
    self.assertEqual(bundle["selected_record_label"], bundle["shuffle_order_preview"][bundle["selected_record_index"]])
    self.assertEqual(len(bundle["anonymous_database"]), 9)
    for preview in bundle["anonymous_database_preview"]:
        self.assertNotIn("kind", preview)
        self.assertNotIn("is_real", preview)
        self.assertTrue(preview["label"].startswith("匿名记录"))
```

- [ ] **Step 2: Run the test and verify it fails**

Run:

```bash
source venv/bin/activate && python -m unittest backend.tests.test_privacy_shuffle.PrivacyShuffleTests.test_build_anonymous_database_hides_real_record_but_selects_it_by_token
```

Expected: fail because `build_anonymous_database` is not defined or not imported.

- [ ] **Step 3: Implement anonymous database bundle**

Add:

```python
def _preview_record(record: Dict[str, Any], label: str) -> Dict[str, Any]:
    metrics = record.get("derived_metrics", {})
    outputs = record.get("model_outputs", [])
    normal_count = sum(1 for output in outputs if str(output.get("status", "")).lower() in {"normal", "good"})
    return {
        "label": label,
        "risk_bucket": record.get("risk_bucket", "attention"),
        "status_mix": "normal dominant" if normal_count >= max(1, len(outputs) // 2) else "watch mixed",
        "metric_shape": "balanced" if float(metrics.get("fall_probability") or 0.5) < 0.35 else "attention",
    }


def build_anonymous_database(
    real_record: Dict[str, Any],
    synthetic_records: List[Dict[str, Any]],
    rng: random.Random,
) -> Dict[str, Any]:
    real_token = f"real-{rng.randrange(10**9)}"
    tagged_real = copy.deepcopy(real_record)
    tagged_real["_selection_token"] = real_token
    combined = [copy.deepcopy(record) for record in synthetic_records] + [tagged_real]
    rng.shuffle(combined)
    anonymous_database = []
    selected_record = None
    selected_record_index = 0
    for index, record in enumerate(combined):
        anonymous_label = f"匿名记录 {index + 1:02d}"
        record_copy = copy.deepcopy(record)
        record_copy["_anonymous_label"] = anonymous_label
        anonymous_database.append(record_copy)
        if record_copy.get("_selection_token") == real_token:
            selected_record = record_copy
            selected_record_index = index
    if selected_record is None:
        raise ValueError("real record token was not found after shuffling")
    preview = [_preview_record(record, record.get("_anonymous_label", f"匿名记录 {index + 1:02d}")) for index, record in enumerate(anonymous_database[:6])]
    return {
        "anonymous_database": anonymous_database,
        "anonymous_database_preview": preview,
        "shuffle_order_preview": [record.get("_anonymous_label", f"匿名记录 {index + 1:02d}") for index, record in enumerate(anonymous_database[:6])],
        "selected_record": selected_record,
        "selected_record_label": selected_record.get("_anonymous_label", "匿名记录"),
        "selected_record_index": selected_record_index,
    }
```

- [ ] **Step 4: Run the test and verify it passes**

Run the same command as Step 2.

Expected: `OK`.

---

## Task 4: Build Bucketed Summary For The Non-Trusted LLM

**Files:**
- Modify: `backend/tests/test_privacy_shuffle.py`
- Modify: `backend/privacy_shuffle.py`

- [ ] **Step 1: Write failing tests for bucketed LLM summary**

Add:

```python
def test_build_protected_llm_summary_uses_buckets_not_precise_values(self):
    real_record = build_real_data_record(self.raw_results, self.raw_report)
    real_record["_anonymous_label"] = "匿名记录 07"

    summary = build_protected_llm_summary(real_record)

    self.assertEqual(summary["record"], "匿名记录 07")
    self.assertEqual(summary["risk_profile"]["fall_probability_bucket"], "40-45%")
    self.assertEqual(summary["metrics"]["blood_pressure"], "elevated")
    self.assertEqual(summary["metrics"]["heart_rate"], "normal range")
    self.assertEqual(summary["model_results"][0]["score_bucket"], "75-80")
    self.assertNotIn("75.5", str(summary))
    self.assertNotIn("142.0", str(summary))
```

- [ ] **Step 2: Run the test and verify it fails**

Run:

```bash
source venv/bin/activate && python -m unittest backend.tests.test_privacy_shuffle.PrivacyShuffleTests.test_build_protected_llm_summary_uses_buckets_not_precise_values
```

Expected: fail because `build_protected_llm_summary` is not defined or not imported.

- [ ] **Step 3: Implement bucket helpers and summary builder**

Add:

```python
def _bucket_percent(value: Any, width: int = 5) -> str:
    if not isinstance(value, (int, float)):
        return "unknown"
    percent = int(round(float(value) * 100))
    low = (percent // width) * width
    return f"{low}-{low + width}%"


def _bucket_number(value: Any, width: int = 5) -> str:
    if not isinstance(value, (int, float)):
        return "unknown"
    low = int(float(value) // width) * width
    return f"{low}-{low + width}"


def _metric_bucket(name: str, value: Any) -> str:
    if not isinstance(value, (int, float)):
        return "unknown"
    if name == "blood_pressure":
        if value >= 140:
            return "elevated"
        if value >= 120:
            return "slightly elevated"
        return "normal range"
    if name == "sleep_efficiency":
        if value >= 85:
            return "good"
        if value >= 70:
            return "attention"
        return "low"
    if name == "spo2":
        return "normal range" if value >= 95 else "attention"
    return "normal range"


def build_protected_llm_summary(record: Dict[str, Any]) -> Dict[str, Any]:
    metrics = record.get("derived_metrics", {})
    return {
        "record": record.get("_anonymous_label", "匿名记录"),
        "risk_profile": {
            "overall": record.get("overall", "Watch"),
            "fall_risk": record.get("risk_bucket", "attention"),
            "fall_probability_bucket": _bucket_percent(metrics.get("fall_probability")),
        },
        "model_results": [
            {
                "task": output.get("model"),
                "input": output.get("input_modality"),
                "status": output.get("status"),
                "score_bucket": _bucket_number(output.get("score")),
            }
            for output in record.get("model_outputs", [])
        ],
        "metrics": {
            "heart_rate": _metric_bucket("heart_rate", metrics.get("heart_rate")),
            "blood_pressure": _metric_bucket("blood_pressure", metrics.get("blood_pressure")),
            "sleep_efficiency": _metric_bucket("sleep_efficiency", metrics.get("sleep_efficiency")),
            "spo2": _metric_bucket("spo2", metrics.get("spo2")),
            "activity_mix": "bucketed distribution",
        },
    }
```

- [ ] **Step 4: Run the test and verify it passes**

Run the same command as Step 2.

Expected: `OK`.

---

## Task 5: Wire The New Backend Flow Into App Endpoints

**Files:**
- Modify: `backend/app.py`
- Modify: `backend/tests/test_app_contract.py`

- [ ] **Step 1: Write failing API contract assertions**

Update `test_cycle_returns_privacy_protection_block` in `backend/tests/test_app_contract.py` to assert:

```python
self.assertEqual(privacy.get("method"), "synthetic_database_shuffle")
self.assertIsInstance(privacy.get("anonymous_database_preview"), list)
self.assertGreaterEqual(len(privacy.get("anonymous_database_preview", [])), 3)
self.assertIsInstance(privacy.get("shuffle_order_preview"), list)
self.assertIsInstance(privacy.get("selected_record_label"), str)
self.assertIsInstance(privacy.get("selected_record_index"), int)
self.assertIn(privacy.get("selected_record_label"), privacy.get("shuffle_order_preview", []))
self.assertEqual(privacy.get("llm_summary_mode"), "bucketed_non_trusted")
self.assertIsInstance(privacy.get("protected_llm_summary_preview"), dict)
```

Keep the existing assertions that `step3.report` exists and `step3.results` remains a list.

- [ ] **Step 2: Run the contract test and verify it fails**

Run:

```bash
source venv/bin/activate && python -m unittest backend.tests.test_app_contract.AppContractTests.test_cycle_returns_privacy_protection_block
```

Expected: fail because the endpoint still returns `synthetic_shuffle` or old field names.

- [ ] **Step 3: Update imports in `backend/app.py`**

Replace candidate-report imports with:

```python
from privacy_shuffle import (
    build_anonymous_database,
    build_display_candidates,
    build_protected_llm_summary,
    build_real_data_record,
    derive_privacy_profile,
    generate_synthetic_database,
)
```

Keep `build_display_candidates` only if report-side compatibility still needs it during the transition; remove it after tests pass if unused.

- [ ] **Step 4: Update `_build_privacy_and_report()`**

Replace the candidate-pool block with:

```python
raw_report = build_health_report(raw_results, uwb_for_report, imu_for_report, csi_for_report)
rng = random.Random(session["seed"])
real_record = build_real_data_record(raw_results, raw_report)
synthetic_records = generate_synthetic_database(real_record, database_size=11, rng=rng)
anonymous_bundle = build_anonymous_database(real_record, synthetic_records, rng=rng)
selected_record = anonymous_bundle["selected_record"]
protected_llm_summary = build_protected_llm_summary(selected_record)
report = raw_report
```

Build the prompt from `protected_llm_summary`, not precise `report` fields:

```python
prompt = (
    "你是一个健康监测分析专家。外部大模型只能看到分桶后的隐私保护摘要。"
    f"记录: {protected_llm_summary['record']}; "
    f"整体状态: {protected_llm_summary['risk_profile']['overall']}; "
    f"跌倒风险桶: {protected_llm_summary['risk_profile']['fall_probability_bucket']}; "
    f"指标摘要: {protected_llm_summary['metrics']}; "
    f"模型摘要: {protected_llm_summary['model_results'][:3]}。"
    "请生成简洁、谨慎的健康结论，不要声称看到了精确原始数值。"
)
```

Return:

```python
"step3": {
    "time_sec": time.time() - step_start,
    "results": raw_results,
    "report_conclusion": report_conclusion,
    "report": report,
},
"privacy_protection": {
    "enabled": True,
    "method": "synthetic_database_shuffle",
    "database_size": len(anonymous_bundle["anonymous_database"]),
    "anonymous_database_preview": anonymous_bundle["anonymous_database_preview"],
    "shuffle_order_preview": anonymous_bundle["shuffle_order_preview"],
    "selected_record_label": anonymous_bundle["selected_record_label"],
    "selected_record_index": anonymous_bundle["selected_record_index"],
    "llm_summary_mode": "bucketed_non_trusted",
    "protected_llm_summary_preview": protected_llm_summary,
    "generation_policy": {
        "distribution": "risk-bucket conditioned",
        "constraints": [
            "physiological range",
            "cross-model consistency",
            "activity mix normalization",
        ],
    },
    "summary": "Synthetic database masks the real inference record before a bucketed summary is sent to the non-trusted LLM.",
}
```

- [ ] **Step 5: Update `/api/cycle` with the same flow**

In the step 3 block of `/api/cycle`, use the same real-record, synthetic database, anonymous bundle, and bucketed LLM summary flow. Keep `report = raw_report` for dashboard rendering.

- [ ] **Step 6: Run backend tests**

Run:

```bash
source venv/bin/activate && python -m unittest backend.tests.test_privacy_shuffle backend.tests.test_app_contract
```

Expected: all tests pass.

---

## Task 6: Update Frontend Privacy Panel To Anonymous Database Flow

**Files:**
- Modify: `frontend/assets/js/app.js`
- Modify: `frontend/assets/css/styles.css`
- Modify: `frontend/index.html`

- [ ] **Step 1: Update frontend mock payloads in temp checks first**

Use this shape in browser checks:

```js
const privacyData = {
  enabled: true,
  method: "synthetic_database_shuffle",
  database_size: 12,
  anonymous_database_preview: [
    { label: "匿名记录 01", risk_bucket: "low", status_mix: "normal dominant", metric_shape: "balanced" },
    { label: "匿名记录 02", risk_bucket: "attention", status_mix: "normal dominant", metric_shape: "attention" },
    { label: "匿名记录 03", risk_bucket: "low", status_mix: "watch mixed", metric_shape: "balanced" },
    { label: "匿名记录 04", risk_bucket: "low", status_mix: "normal dominant", metric_shape: "balanced" },
  ],
  shuffle_order_preview: ["匿名记录 04", "匿名记录 01", "匿名记录 03", "匿名记录 02"],
  selected_record_label: "匿名记录 03",
  selected_record_index: 2,
  llm_summary_mode: "bucketed_non_trusted",
  protected_llm_summary_preview: {
    risk_profile: { overall: "Watch", fall_probability_bucket: "20-25%" },
    metrics: { blood_pressure: "slightly elevated", sleep_efficiency: "good" },
  },
};
```

- [ ] **Step 2: Run browser checks and confirm they fail**

Run:

```bash
node temp/check_privacy_selected_candidate.js
```

Expected: fail because frontend still expects candidate report fields.

- [ ] **Step 3: Update `renderPrivacyProtection()` data extraction**

In `frontend/assets/js/app.js`, replace `display_candidates`, `selected_source_label`, and `protected_output` dependencies with:

```js
const databaseRecords = Array.isArray(privacy.anonymous_database_preview)
  ? privacy.anonymous_database_preview.slice(0, 6)
  : [];
const shuffleOrderPreview = Array.isArray(privacy.shuffle_order_preview)
  ? privacy.shuffle_order_preview.filter(Boolean).slice(0, 6)
  : [];
const selectedRecordText = safeText(privacy.selected_record_label, "");
const selectedOrderIndexRaw = Number(privacy.selected_record_index);
const matchedSelectedIndex = selectedRecordText
  ? shuffleOrderPreview.findIndex((label) => safeText(label) === selectedRecordText)
  : -1;
const selectedOrderIndex = Number.isInteger(selectedOrderIndexRaw)
  && selectedOrderIndexRaw >= 0
  && selectedOrderIndexRaw < shuffleOrderPreview.length
    ? selectedOrderIndexRaw
    : (matchedSelectedIndex >= 0 ? matchedSelectedIndex : 0);
const protectedSummary = privacy.protected_llm_summary_preview || {};
```

- [ ] **Step 4: Replace privacy animation labels**

Use these stage labels:

```text
1. 同态模型数据结果
2. 约束分布生成伪造数据库
3. 真实记录匿名混入并混洗
4. 分桶摘要进入非可信 LLM
```

Ensure these strings no longer appear in `app.js`:

```text
质量门
门外拦截
不符合要求
符合要求
候选报告
随机报告
```

- [ ] **Step 5: Update CSS class usage**

Either remove quality-gate-specific sections or leave the CSS unused. Add only the minimal classes needed for:

```css
.syntheticGeneratorStage
.anonymousDatabaseGrid
.anonymousRecordCard
.hiddenSelectionCard
.bucketedSummaryCard
```

Keep responsive constraints already added for `.privacyMixer`, `.mixerColumn`, and `.privacyStageOverlay`.

- [ ] **Step 6: Bump cache versions**

In `frontend/index.html`, bump:

```html
<link rel="stylesheet" href="./assets/css/styles.css?v=33"/>
<script src="./assets/js/app.js?v=41"></script>
```

- [ ] **Step 7: Run frontend static checks**

Run:

```bash
node --check frontend/assets/js/app.js
source venv/bin/activate && python temp/check_privacy_animation_layout.py
```

Expected: both pass after updating layout check version assertions and string expectations.

---

## Task 7: Update Browser Regression Checks

**Files:**
- Modify: `temp/check_privacy_animation_browser.js`
- Modify: `temp/check_privacy_responsive_layout.js`
- Modify: `temp/check_privacy_selected_candidate.js`
- Modify: `temp/check_privacy_animation_layout.py`

- [ ] **Step 1: Update selected-record browser check**

Change the selected check to assert:

```js
if (selected.some((group) => group.selectedIndex !== 2 || !group.selectedText.includes("匿名记录 03"))) {
  throw new Error(`selected record does not match backend hidden selection: ${JSON.stringify(selected)}`);
}
```

- [ ] **Step 2: Update animation sequence check**

Replace quality-gate assertions with sequence assertions:

```text
early: homomorphic data stage visible; synthetic generator hidden
middle: synthetic database visible; hidden selection not yet visible
late: shuffle and hidden selection visible
complete: static mixer contains all four steps
```

- [ ] **Step 3: Update responsive layout check**

Keep the existing viewport cases. Assert:

```js
const parts = {
  raw: box(".mixerRaw"),
  pool: box(".mixerPool"),
  shuffle: box(".mixerShuffle"),
  protected: box(".mixerProtected"),
};
```

Continue checking `mixerContainsEveryStep`, `mixerOverflow`, and `panelOverflow`.

- [ ] **Step 4: Run browser checks**

Run:

```bash
node temp/check_privacy_selected_candidate.js
node temp/check_privacy_responsive_layout.js
node temp/check_privacy_animation_browser.js
```

Expected: all pass.

---

## Task 8: Restart Backend And Verify Live App

**Files:**
- No source edits.

- [ ] **Step 1: Check ports**

Run:

```bash
ss -ltnp | rg ':(8001|8082)\b' || true
```

Expected: frontend on `8001`, backend on `8082`; if backend is an old process, restart it.

- [ ] **Step 2: Restart backend if needed**

Run:

```bash
kill <old-uvicorn-pid>
cd backend && source ../venv/bin/activate && uvicorn app:app --host 127.0.0.1 --port 8082
```

Expected: `Uvicorn running on http://127.0.0.1:8082`.

- [ ] **Step 3: Verify health and asset versions**

Run:

```bash
curl -s http://127.0.0.1:8082/api/health
curl -s http://127.0.0.1:8001/ | rg 'styles.css\?v=33|app.js\?v=41'
```

Expected: backend health JSON and both frontend asset versions.

- [ ] **Step 4: Verify live API privacy payload**

Run:

```bash
curl -s 'http://127.0.0.1:8082/api/cycle' | node -e 'let s=""; process.stdin.on("data", d => s += d); process.stdin.on("end", () => { const data = JSON.parse(s); const p = data.privacy_protection || {}; console.log(JSON.stringify({method:p.method,database_size:p.database_size,selected_record_label:p.selected_record_label,shuffle_order_preview:p.shuffle_order_preview,llm_summary_mode:p.llm_summary_mode}, null, 2)); });'
```

Expected:

```json
{
  "method": "synthetic_database_shuffle",
  "database_size": 12,
  "selected_record_label": "匿名记录 ...",
  "shuffle_order_preview": ["匿名记录 ..."],
  "llm_summary_mode": "bucketed_non_trusted"
}
```

---

## Final Verification

Run all of these before claiming completion:

```bash
source venv/bin/activate && python -m unittest backend.tests.test_privacy_shuffle backend.tests.test_app_contract
node --check frontend/assets/js/app.js
source venv/bin/activate && python temp/check_privacy_animation_layout.py
node temp/check_privacy_selected_candidate.js
node temp/check_privacy_responsive_layout.js
node temp/check_privacy_animation_browser.js
curl -s http://127.0.0.1:8082/api/health
curl -s http://127.0.0.1:8001/ | rg 'styles.css\?v=33|app.js\?v=41'
```

Expected:

- Backend unit and contract tests pass.
- Frontend JS syntax check passes.
- Static privacy layout check passes.
- Browser selected-record, responsive layout, and animation checks pass.
- Backend health endpoint responds.
- Frontend HTML references the new asset versions.

---

## Notes

- Do not expose `kind`, `is_real`, `_selection_token`, or exact real-record internals in `privacy_protection` payloads.
- Do not let the LLM prompt include precise score or metric values.
- Keep the current report UI and structured report data intact.
- Do not add startup scripts.
- Do not auto-commit.

---

## Approved Follow-up: 100-Record Distribution And Token Lookup Visualization

**Decision Date:** 2026-05-05

The privacy panel should not primarily display a handful of anonymous record cards. The approved direction is:

```text
real homomorphic inference record
  -> backend creates hidden token: H(session_seed, real_id, nonce)
  -> generate 100 valid synthetic records
  -> insert the real record into the synthetic database
  -> show the 100-record database as a distribution, not as individual cards
  -> shuffle anonymous IDs
  -> backend calls token_map[token] to recover the target record
  -> send only the bucketed summary to the non-trusted LLM
```

The visualization should combine two ideas:

- **Distribution masking:** show the fake database as a statistical distribution with risk buckets and a target point hidden inside the distribution.
- **Backend token lookup:** show token generation, token binding, shuffle mapping, and backend lookup as an internal backend process. The token must not look visible to the frontend or the non-trusted LLM.

The backend payload should evolve from previewing a few anonymous rows to returning distribution metadata:

```json
{
  "database_size": 101,
  "synthetic_record_count": 100,
  "distribution_summary": {
    "risk_buckets": [
      {"bucket": "low", "count": 34, "ratio": 0.34},
      {"bucket": "attention", "count": 51, "ratio": 0.51},
      {"bucket": "elevated", "count": 16, "ratio": 0.16}
    ],
    "scatter_points": [
      {"x": 0.42, "y": 0.62, "bucket": "attention", "target": false}
    ],
    "target_point": {
      "x": 0.56,
      "y": 0.41,
      "bucket": "attention",
      "label": "target hidden in distribution"
    }
  },
  "token_flow": {
    "token_label": "hidden backend token",
    "generation": "H(session_seed, real_id, nonce)",
    "binding": "token bound to real homomorphic inference record",
    "lookup": "real_record = token_map[token]",
    "visibility": "backend_only"
  }
}
```

The frontend privacy animation should become:

1. **同态模型数据结果 + 令牌生成**
   - Show model result buckets.
   - Show backend-only token generation as a small internal backend strip.

2. **100 份伪造数据库分布**
   - Show histogram / density bars for risk buckets.
   - Show scatter distribution; target point is hidden inside the distribution.
   - Do not show 100 individual cards.

3. **混洗映射与 token 查表**
   - Show anonymous IDs such as `anon_21`, `anon_04`, `anon_58`.
   - Show backend lookup `real_record = token_map[token]`.
   - Make clear `token_map` does not leave the backend.

4. **分桶摘要进入非可信 LLM**
   - Show only bucketed fields.
   - Keep the current report UI backed by the precise structured backend report.

Additional tests should assert:

- `generate_synthetic_database(..., database_size=100)` creates 100 synthetic records.
- Anonymous database size is 101 after inserting the real record.
- Distribution summary bucket counts add up to 101.
- Scatter points do not expose `kind`, `is_real`, `_selection_token`, or exact raw values.
- `target_point` exists and matches the selected record label without exposing the token.
- `token_flow.visibility` is `backend_only`.
- Frontend no longer uses anonymous record cards as the main visual.
