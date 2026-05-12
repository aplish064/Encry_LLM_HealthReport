# Scene Tab Finance Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a header-level Healthcare / Finance scene switch that reuses the existing encrypted workflow while swapping data cards, local encoders, privacy prompt, and report content for Finance.

**Architecture:** Keep Healthcare as the default path and add a `scenario` parameter for scene-aware endpoints. Store the selected scenario in staged sessions so privacy shuffle and report generation can dispatch to the correct domain builders. Use standard-library CSV parsing for the Finance dataset and preserve the existing frontend workflow controller instead of duplicating the page.

**Tech Stack:** FastAPI, Python standard library `csv` / `zipfile`, NumPy, TenSEAL, vanilla JavaScript, existing CSS, `unittest` contract tests.

**Project Constraints:** Use the project venv for commands. Do not use port `8080`. Do not add startup scripts. Do not commit automatically; every task ends with a verification checkpoint instead of a commit.

---

## File Structure

- `test_data/synthetic_personal_finance_dataset.csv`
  - Runtime Finance dataset extracted from `dataset/archive.zip`.
- `backend/app.py`
  - Scenario routing, Finance modality config, Finance CSV loading, Finance step1/step2 builders, Finance report builder, Finance prompt builder, staged session scenario storage.
- `backend/privacy_shuffle.py`
  - Domain-aware real record and protected summary support for Finance while keeping existing Healthcare behavior.
- `backend/tests/test_app_contract.py`
  - Scenario endpoint contract tests and Finance CSV validation tests.
- `backend/tests/test_privacy_shuffle.py`
  - Finance protected summary tests.
- `frontend/index.html`
  - Header scene tabs and ids for scene-sensitive labels.
- `frontend/assets/js/modalityCards.js`
  - Finance card definitions and compact finance card rendering.
- `frontend/assets/js/modality-selector.js`
  - Current scenario state, tab event handling, scene-aware API calls, model cluster reset.
- `frontend/assets/js/app.js`
  - Domain-aware report labels and privacy wording.
- `frontend/assets/css/styles.css`
  - Header scene tab styling.

---

### Task 1: Extract Finance Dataset and Add Data Validation Test

**Files:**
- Create: `test_data/synthetic_personal_finance_dataset.csv`
- Modify: `backend/tests/test_app_contract.py`

- [ ] **Step 1: Write the failing dataset validation tests**

Append these tests to `backend/tests/test_app_contract.py` after `AppContractTests`:

```python
class FinanceDatasetTests(unittest.TestCase):
    def test_finance_dataset_exists_with_expected_shape(self):
        data_path = BACKEND_DIR.parent / "test_data" / "synthetic_personal_finance_dataset.csv"

        self.assertTrue(data_path.exists(), f"Missing finance dataset: {data_path}")

        with data_path.open("r", encoding="utf-8", newline="") as handle:
            header = handle.readline().strip().split(",")
            row_count = sum(1 for _ in handle)

        self.assertEqual(len(header), 20)
        self.assertEqual(row_count, 32424)

    def test_finance_dataset_contains_required_columns(self):
        data_path = BACKEND_DIR.parent / "test_data" / "synthetic_personal_finance_dataset.csv"
        required = {
            "user_id",
            "age",
            "gender",
            "education_level",
            "employment_status",
            "job_title",
            "monthly_income_usd",
            "monthly_expenses_usd",
            "savings_usd",
            "has_loan",
            "loan_type",
            "loan_amount_usd",
            "loan_term_months",
            "monthly_emi_usd",
            "loan_interest_rate_pct",
            "debt_to_income_ratio",
            "credit_score",
            "savings_to_income_ratio",
            "region",
            "record_date",
        }

        self.assertTrue(data_path.exists(), f"Missing finance dataset: {data_path}")
        with data_path.open("r", encoding="utf-8", newline="") as handle:
            header = set(handle.readline().strip().split(","))

        self.assertEqual(required - header, set())
```

- [ ] **Step 2: Run the tests to verify the first test fails before extraction**

Run:

```bash
cd /home/hkustgz/Us/Encry_LLM_HealthReport
source venv/bin/activate
python -m unittest backend.tests.test_app_contract.FinanceDatasetTests -v
```

Expected before extraction: failure with `Missing finance dataset`.

- [ ] **Step 3: Extract the CSV into `test_data/`**

Run:

```bash
cd /home/hkustgz/Us/Encry_LLM_HealthReport
unzip -p dataset/archive.zip synthetic_personal_finance_dataset.csv > test_data/synthetic_personal_finance_dataset.csv
```

- [ ] **Step 4: Verify dataset shape from the shell**

Run:

```bash
cd /home/hkustgz/Us/Encry_LLM_HealthReport
python - <<'PY'
from pathlib import Path
path = Path("test_data/synthetic_personal_finance_dataset.csv")
with path.open("r", encoding="utf-8", newline="") as handle:
    header = handle.readline().strip().split(",")
    rows = sum(1 for _ in handle)
print(f"columns={len(header)}")
print(f"rows={rows}")
print(",".join(header))
PY
```

Expected:

```text
columns=20
rows=32424
user_id,age,gender,education_level,employment_status,job_title,monthly_income_usd,monthly_expenses_usd,savings_usd,has_loan,loan_type,loan_amount_usd,loan_term_months,monthly_emi_usd,loan_interest_rate_pct,debt_to_income_ratio,credit_score,savings_to_income_ratio,region,record_date
```

- [ ] **Step 5: Run the dataset tests again**

Run:

```bash
cd /home/hkustgz/Us/Encry_LLM_HealthReport
source venv/bin/activate
python -m unittest backend.tests.test_app_contract.FinanceDatasetTests -v
```

Expected: both tests pass.

- [ ] **Step 6: Verification checkpoint**

Run:

```bash
cd /home/hkustgz/Us/Encry_LLM_HealthReport
git status --short test_data/synthetic_personal_finance_dataset.csv backend/tests/test_app_contract.py
```

Expected: the CSV is new or modified and `backend/tests/test_app_contract.py` is modified. Do not commit.

---

### Task 2: Add Backend Scenario Routing and Finance Modalities

**Files:**
- Modify: `backend/app.py`
- Modify: `backend/tests/test_app_contract.py`

- [ ] **Step 1: Write failing API contract tests for scenario modalities**

Append these methods inside `AppContractTests` in `backend/tests/test_app_contract.py`:

```python
    async def test_modalities_defaults_to_healthcare(self):
        response = await self.client.get("/api/modalities")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload.get("scenario"), "healthcare")
        modality_ids = [item["id"] for item in payload["modalities"]]
        self.assertIn("depth", modality_ids)
        self.assertIn("uwb", modality_ids)
        self.assertIn("blood", modality_ids)

    async def test_modalities_returns_finance_cards_for_finance_scenario(self):
        response = await self.client.get("/api/modalities", params={"scenario": "finance"})

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload.get("scenario"), "finance")
        self.assertEqual(
            [item["id"] for item in payload["modalities"]],
            ["income", "expenses", "savings", "loan", "credit", "profile"],
        )
        self.assertEqual(payload["modalities"][0]["name"], "Income")
        self.assertEqual(payload["modalities"][4]["name"], "Credit")

    async def test_modalities_rejects_unknown_explicit_scenario(self):
        response = await self.client.get("/api/modalities", params={"scenario": "unknown"})

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertIn("error", payload)
        self.assertIn("Unsupported scenario", payload["error"])
```

- [ ] **Step 2: Run tests and verify they fail**

Run:

```bash
cd /home/hkustgz/Us/Encry_LLM_HealthReport
source venv/bin/activate
python -m unittest backend.tests.test_app_contract.AppContractTests.test_modalities_defaults_to_healthcare backend.tests.test_app_contract.AppContractTests.test_modalities_returns_finance_cards_for_finance_scenario backend.tests.test_app_contract.AppContractTests.test_modalities_rejects_unknown_explicit_scenario -v
```

Expected: at least `scenario` assertions fail because `/api/modalities` is not scenario-aware yet.

- [ ] **Step 3: Add scenario constants to `backend/app.py`**

Insert near the existing modality/model constants:

```python
SUPPORTED_SCENARIOS = {"healthcare", "finance"}
DEFAULT_SCENARIO = "healthcare"

FINANCE_DATA_PATH = os.path.join(BASE_DIR, "test_data", "synthetic_personal_finance_dataset.csv")

FINANCE_REQUIRED_FIELDS = [
    "user_id",
    "age",
    "gender",
    "education_level",
    "employment_status",
    "job_title",
    "monthly_income_usd",
    "monthly_expenses_usd",
    "savings_usd",
    "has_loan",
    "loan_type",
    "loan_amount_usd",
    "loan_term_months",
    "monthly_emi_usd",
    "loan_interest_rate_pct",
    "debt_to_income_ratio",
    "credit_score",
    "savings_to_income_ratio",
    "region",
    "record_date",
]

FINANCE_MODALITIES = [
    {
        "id": "income",
        "name": "Income",
        "type": "finance",
        "data_type": "numeric",
        "description": "Monthly income and earning capacity baseline",
        "icon": "income",
        "fields": ["monthly_income_usd"],
    },
    {
        "id": "expenses",
        "name": "Expenses",
        "type": "finance",
        "data_type": "numeric",
        "description": "Monthly spending burden",
        "icon": "expenses",
        "fields": ["monthly_expenses_usd"],
    },
    {
        "id": "savings",
        "name": "Savings",
        "type": "finance",
        "data_type": "numeric",
        "description": "Savings buffer and liquidity resilience",
        "icon": "savings",
        "fields": ["savings_usd", "savings_to_income_ratio"],
    },
    {
        "id": "loan",
        "name": "Loan",
        "type": "finance",
        "data_type": "mixed",
        "description": "Loan balance, monthly payment, term, and interest pressure",
        "icon": "loan",
        "fields": [
            "has_loan",
            "loan_type",
            "loan_amount_usd",
            "loan_term_months",
            "monthly_emi_usd",
            "loan_interest_rate_pct",
        ],
    },
    {
        "id": "credit",
        "name": "Credit",
        "type": "finance",
        "data_type": "numeric",
        "description": "Credit score and debt-to-income leverage",
        "icon": "credit",
        "fields": ["credit_score", "debt_to_income_ratio"],
    },
    {
        "id": "profile",
        "name": "Profile",
        "type": "finance",
        "data_type": "categorical",
        "description": "Employment and regional context for explanation",
        "icon": "profile",
        "fields": ["age", "employment_status", "job_title", "region", "record_date"],
    },
]

FINANCE_CLUSTER_MODELS = [
    {"id": "income_capacity", "title": "Income Capacity", "subtitle": "Income percentile model"},
    {"id": "expense_burden", "title": "Expense Burden", "subtitle": "Cashflow burden model"},
    {"id": "savings_resilience", "title": "Savings Resilience", "subtitle": "Liquidity buffer model"},
    {"id": "loan_stress", "title": "Loan Stress", "subtitle": "Repayment pressure model"},
    {"id": "credit_risk", "title": "Credit Risk", "subtitle": "Credit and leverage model"},
    {"id": "profile_context", "title": "Profile Context", "subtitle": "Employment context model"},
]
```

- [ ] **Step 4: Add scenario normalization helpers to `backend/app.py`**

Insert after `normalize_modality_name`:

```python
def normalize_scenario(scenario: Optional[str]) -> str:
    if scenario is None or not str(scenario).strip():
        return DEFAULT_SCENARIO
    normalized = str(scenario).strip().lower()
    if normalized not in SUPPORTED_SCENARIOS:
        raise ValueError(f"Unsupported scenario: {scenario}")
    return normalized


def unsupported_scenario_payload(error: ValueError) -> Dict[str, str]:
    return {"error": str(error)}
```

- [ ] **Step 5: Update `/api/modalities` to accept scenario**

Change the function signature and first branch:

```python
@app.get("/api/modalities")
async def get_modalities(scenario: Optional[str] = None):
    """获取所有可用的模态配置，包括文件信息"""
    try:
        scenario_key = normalize_scenario(scenario)
    except ValueError as exc:
        return unsupported_scenario_payload(exc)

    if scenario_key == "finance":
        return {
            "scenario": "finance",
            "modalities": [dict(item) for item in FINANCE_MODALITIES],
        }

    try:
        config_path = os.path.join(BASE_DIR, "backend", "modality_config.json")
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)

        test_data_dir = os.path.join(BASE_DIR, "test_data")

        for modality in config.get("modalities", []):
            modality_id = modality["id"]
            file_info = get_modality_file_info(modality_id, test_data_dir)
            modality["files"] = file_info

        return {
            **config,
            "scenario": "healthcare",
        }
```

Also update the fallback return at the end of the same function:

```python
        return {
            **default_config,
            "scenario": "healthcare",
        }
```

- [ ] **Step 6: Run the scenario modality tests**

Run:

```bash
cd /home/hkustgz/Us/Encry_LLM_HealthReport
source venv/bin/activate
python -m unittest backend.tests.test_app_contract.AppContractTests.test_modalities_defaults_to_healthcare backend.tests.test_app_contract.AppContractTests.test_modalities_returns_finance_cards_for_finance_scenario backend.tests.test_app_contract.AppContractTests.test_modalities_rejects_unknown_explicit_scenario -v
```

Expected: all three tests pass.

- [ ] **Step 7: Verification checkpoint**

Run:

```bash
cd /home/hkustgz/Us/Encry_LLM_HealthReport
source venv/bin/activate
python -m unittest backend.tests.test_app_contract.AppContractTests.test_cycle_preserves_core_response_shape backend.tests.test_app_contract.AppContractTests.test_modalities_defaults_to_healthcare backend.tests.test_app_contract.AppContractTests.test_modalities_returns_finance_cards_for_finance_scenario -v
git status --short backend/app.py backend/tests/test_app_contract.py
```

Expected: tests pass; files are modified; no commit.

---

### Task 3: Add Finance CSV Loading, Dispatch, and Session Storage

**Files:**
- Modify: `backend/app.py`
- Modify: `backend/tests/test_app_contract.py`

- [ ] **Step 1: Write failing Finance dispatch tests**

Append these methods inside `AppContractTests`:

```python
    async def test_finance_dispatch_returns_finance_session_and_models(self):
        response = await self.client.get(
            "/api/dispatch",
            params={"scenario": "finance", "selected_modalities": "income,credit,loan"},
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload.get("scenario"), "finance")
        self.assertEqual(payload.get("data_source"), "synthetic_personal_finance_dataset.csv")
        self.assertIn("session_id", payload)
        self.assertEqual(payload["step1"]["enabled_modalities"], ["Income", "Credit", "Loan"])
        self.assertEqual(
            [item["id"] for item in payload["step2"]["cluster_models"]],
            ["income_capacity", "expense_burden", "savings_resilience", "loan_stress", "credit_risk", "profile_context"],
        )
        self.assertEqual(
            [item["model_id"] for item in payload["step2"]["assignments"]],
            ["income_capacity", "loan_stress", "credit_risk"],
        )
        self.assertEqual(
            [item["model_id"] for item in payload["raw_results"]],
            ["income_capacity", "loan_stress", "credit_risk"],
        )

    async def test_finance_dispatch_rejects_missing_finance_dataset_fields(self):
        with patch.object(self.backend, "load_finance_records", return_value=[{"user_id": "U1"}]):
            response = await self.client.get(
                "/api/dispatch",
                params={"scenario": "finance", "selected_modalities": "income"},
            )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertIn("error", payload)
        self.assertIn("Missing finance dataset fields", payload["error"])
```

- [ ] **Step 2: Run tests and verify they fail**

Run:

```bash
cd /home/hkustgz/Us/Encry_LLM_HealthReport
source venv/bin/activate
python -m unittest backend.tests.test_app_contract.AppContractTests.test_finance_dispatch_returns_finance_session_and_models backend.tests.test_app_contract.AppContractTests.test_finance_dispatch_rejects_missing_finance_dataset_fields -v
```

Expected: fail because `scenario=finance` dispatch is not implemented.

- [ ] **Step 3: Add Finance loading and validation helpers to `backend/app.py`**

Insert near the other data loading helpers:

```python
_FINANCE_DATA_CACHE: Optional[List[Dict[str, str]]] = None


def load_finance_records() -> List[Dict[str, str]]:
    global _FINANCE_DATA_CACHE
    if _FINANCE_DATA_CACHE is not None:
        return _FINANCE_DATA_CACHE
    if not os.path.exists(FINANCE_DATA_PATH):
        raise FileNotFoundError(f"Finance data file missing: {FINANCE_DATA_PATH}")
    import csv
    with open(FINANCE_DATA_PATH, "r", encoding="utf-8", newline="") as handle:
        records = list(csv.DictReader(handle))
    _FINANCE_DATA_CACHE = records
    return records


def validate_finance_records(records: List[Dict[str, str]]) -> None:
    if not records:
        raise ValueError("Finance dataset is empty")
    missing = [field for field in FINANCE_REQUIRED_FIELDS if field not in records[0]]
    if missing:
        raise ValueError(f"Missing finance dataset fields: {', '.join(missing)}")


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return default
    if np.isnan(parsed) or np.isinf(parsed):
        return default
    return parsed


def safe_ratio(numerator: Any, denominator: Any) -> float:
    den = safe_float(denominator)
    if abs(den) < 1e-9:
        return 0.0
    return safe_float(numerator) / den


def pick_finance_record(records: List[Dict[str, str]], seed: int) -> Dict[str, str]:
    validate_finance_records(records)
    index = seed % len(records)
    return records[index]
```

- [ ] **Step 4: Add Finance modality resolution helpers**

Insert near `_selected_flags`:

```python
FINANCE_MODALITY_BY_ID = {item["id"]: item for item in FINANCE_MODALITIES}
FINANCE_MODALITY_NAME_BY_ID = {item["id"]: item["name"] for item in FINANCE_MODALITIES}


def resolve_finance_modalities(selected_modalities: Optional[str]) -> List[str]:
    default_ids = [item["id"] for item in FINANCE_MODALITIES]
    if not selected_modalities:
        return default_ids
    resolved = []
    for raw_item in selected_modalities.split(","):
        item_id = raw_item.strip().lower()
        if item_id in FINANCE_MODALITY_BY_ID and item_id not in resolved:
            resolved.append(item_id)
    return resolved or default_ids
```

- [ ] **Step 5: Add Finance score helpers**

Insert before `_score_for_model`:

```python
def finance_status_from_risk(risk: float) -> str:
    if risk >= 0.70:
        return "attention"
    if risk >= 0.40:
        return "watch"
    return "stable"


def finance_score_for_model(model_id: str, record: Dict[str, str]) -> Dict[str, Any]:
    income = max(safe_float(record.get("monthly_income_usd")), 0.0)
    expenses = max(safe_float(record.get("monthly_expenses_usd")), 0.0)
    savings = max(safe_float(record.get("savings_usd")), 0.0)
    emi = max(safe_float(record.get("monthly_emi_usd")), 0.0)
    interest = max(safe_float(record.get("loan_interest_rate_pct")), 0.0)
    debt_to_income = max(safe_float(record.get("debt_to_income_ratio")), 0.0)
    credit_score = safe_float(record.get("credit_score"), 600.0)
    savings_to_income = max(safe_float(record.get("savings_to_income_ratio")), 0.0)

    expense_ratio = safe_ratio(expenses, income)
    emi_ratio = safe_ratio(emi, income)
    credit_risk = _clamp((680.0 - credit_score) / 380.0, 0.0, 1.0)

    if model_id == "income_capacity":
        score = _clamp(income / 8000.0, 0.0, 1.0) * 100
        return {"score": round(score, 2), "status": "stable" if score >= 45 else "watch"}
    if model_id == "expense_burden":
        risk = _clamp(expense_ratio, 0.0, 1.2)
        return {"score": round(risk * 100, 2), "status": finance_status_from_risk(risk)}
    if model_id == "savings_resilience":
        resilience = _clamp(min(savings_to_income / 6.0, savings / max(income, 1.0) / 12.0), 0.0, 1.0)
        return {"score": round(resilience * 100, 2), "status": "stable" if resilience >= 0.55 else "watch"}
    if model_id == "loan_stress":
        risk = _clamp(0.55 * emi_ratio + 0.30 * debt_to_income + 0.15 * (interest / 30.0), 0.0, 1.0)
        return {"score": round(risk * 100, 2), "status": finance_status_from_risk(risk)}
    if model_id == "credit_risk":
        risk = _clamp(0.65 * credit_risk + 0.35 * min(debt_to_income / 2.0, 1.0), 0.0, 1.0)
        return {"score": round(risk * 100, 2), "status": finance_status_from_risk(risk)}
    if model_id == "profile_context":
        employed = str(record.get("employment_status", "")).strip().lower() == "employed"
        score = 75.0 if employed else 55.0
        return {"score": score, "status": "stable" if employed else "watch"}
    return {"score": 50.0, "status": "watch"}
```

- [ ] **Step 6: Add Finance step builders**

Insert after `_build_step2`:

```python
def _finance_excerpt(record: Dict[str, str], fields: List[str]) -> str:
    parts = []
    for field in fields:
        value = record.get(field, "")
        parts.append(f"{field}={value}")
    return "; ".join(parts)


def _build_finance_step1(record: Dict[str, str], selected_ids: List[str]) -> Dict[str, Any]:
    step_start = time.time()
    modalities = {}
    for item_id in selected_ids:
        config = FINANCE_MODALITY_BY_ID[item_id]
        fields = config["fields"]
        modalities[config["name"]] = {
            "kind": "finance",
            "type": "finance",
            "shape": f"{len(fields)} fields",
            "fields": fields,
            "plaintext_excerpt": _finance_excerpt(record, fields),
            "preview": {field: record.get(field) for field in fields},
        }
    return {
        "time_sec": time.time() - step_start,
        "modalities": modalities,
        "enabled_modalities": [FINANCE_MODALITY_NAME_BY_ID[item_id] for item_id in selected_ids],
    }


def _build_finance_assignments(selected_ids: List[str]) -> List[Dict[str, str]]:
    pairs = [
        ("income", "income_capacity", "secure_income_toolbox"),
        ("expenses", "expense_burden", "secure_expense_toolbox"),
        ("savings", "savings_resilience", "secure_savings_toolbox"),
        ("loan", "loan_stress", "secure_loan_toolbox"),
        ("credit", "credit_risk", "secure_credit_toolbox"),
        ("profile", "profile_context", "secure_profile_toolbox"),
    ]
    return [
        {"input_modality": FINANCE_MODALITY_NAME_BY_ID[item_id], "model_id": model_id, "tool": tool}
        for item_id, model_id, tool in pairs
        if item_id in selected_ids
    ]


def _build_finance_step2(record: Dict[str, str], selected_ids: List[str]) -> Dict[str, Any]:
    step_start = time.time()
    features = np.array([
        safe_float(record.get("monthly_income_usd")),
        safe_float(record.get("monthly_expenses_usd")),
        safe_float(record.get("savings_usd")),
        safe_float(record.get("monthly_emi_usd")),
        safe_float(record.get("debt_to_income_ratio")),
        safe_float(record.get("credit_score")),
        safe_float(record.get("savings_to_income_ratio")),
        safe_float(record.get("loan_interest_rate_pct")),
    ], dtype=float)
    ctx = setup_context()
    enc_features = ts.ckks_vector(ctx, features.tolist())
    agg_bytes = enc_features.serialize()

    assignments = _build_finance_assignments(selected_ids)
    results = []
    for assignment in assignments:
        model_meta = next((item for item in FINANCE_CLUSTER_MODELS if item["id"] == assignment["model_id"]), None)
        scored = finance_score_for_model(assignment["model_id"], record)
        results.append({
            "model": model_meta["title"] if model_meta else assignment["model_id"],
            "model_id": assignment["model_id"],
            "input_modality": assignment["input_modality"],
            "tool": assignment["tool"],
            "score": scored["score"],
            "status": scored["status"],
        })

    return {
        "step2": {
            "time_sec": time.time() - step_start,
            "llm_time_sec": 0.0,
            "summary": ", ".join([f"{item['input_modality']}→{item['tool']}" for item in assignments]),
            "cluster_models": FINANCE_CLUSTER_MODELS,
            "assignments": assignments,
            "tool_times": [0.6 for _ in assignments],
            "aggregate_cipher_preview": bytes_preview(agg_bytes, 160),
        },
        "raw_results": results,
    }
```

- [ ] **Step 7: Update `/api/dispatch` to route Finance**

Modify the start of `run_dispatch`:

```python
@app.get("/api/dispatch")
async def run_dispatch(selected_modalities: Optional[str] = None, scenario: Optional[str] = None):
    start_time = time.time()
    session_seed = time.time_ns()
    try:
        scenario_key = normalize_scenario(scenario)
    except ValueError as exc:
        return unsupported_scenario_payload(exc)

    if scenario_key == "finance":
        try:
            records = load_finance_records()
            validate_finance_records(records)
            selected_ids = resolve_finance_modalities(selected_modalities)
            finance_record = pick_finance_record(records, session_seed)
            step1_data = _build_finance_step1(finance_record, selected_ids)
            step2_bundle = _build_finance_step2(finance_record, selected_ids)
        except Exception as exc:
            return {"error": str(exc)}

        session_id = uuid.uuid4().hex
        _STAGED_SESSIONS[session_id] = {
            "scenario": "finance",
            "seed": session_seed,
            "selected_modalities": selected_ids,
            "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "step1": step1_data,
            "step2": step2_bundle["step2"],
            "finance_record": finance_record,
            "series": {"uwb": None, "imu": None, "csi": None},
            "raw_results": step2_bundle["raw_results"],
        }
        return {
            "schema": "he-multimodal-dispatch/v1",
            "scenario": "finance",
            "session_id": session_id,
            "generated_at": _STAGED_SESSIONS[session_id]["generated_at"],
            "step1": step1_data,
            "step2": step2_bundle["step2"],
            "raw_results": step2_bundle["raw_results"],
            "data_source": "synthetic_personal_finance_dataset.csv",
            "llm_provider": "ZhipuAI",
        }
```

Keep the existing Healthcare body after this branch and add `"scenario": "healthcare"` to the Healthcare session and return payload.

- [ ] **Step 8: Run Finance dispatch tests**

Run:

```bash
cd /home/hkustgz/Us/Encry_LLM_HealthReport
source venv/bin/activate
python -m unittest backend.tests.test_app_contract.AppContractTests.test_finance_dispatch_returns_finance_session_and_models backend.tests.test_app_contract.AppContractTests.test_finance_dispatch_rejects_missing_finance_dataset_fields -v
```

Expected: both tests pass.

- [ ] **Step 9: Run existing Healthcare dispatch-stage tests**

Run:

```bash
cd /home/hkustgz/Us/Encry_LLM_HealthReport
source venv/bin/activate
python -m unittest backend.tests.test_app_contract.AppContractTests.test_privacy_shuffle_returns_plaintext_prompt_for_stage backend.tests.test_app_contract.AppContractTests.test_cycle_accepts_modality_ids_without_falling_back_to_all_modalities -v
```

Expected: both tests pass.

- [ ] **Step 10: Verification checkpoint**

Run:

```bash
cd /home/hkustgz/Us/Encry_LLM_HealthReport
git status --short backend/app.py backend/tests/test_app_contract.py
```

Expected: files modified; no commit.

---

### Task 4: Add Finance Privacy Summary, Prompt, and Report

**Files:**
- Modify: `backend/privacy_shuffle.py`
- Modify: `backend/app.py`
- Modify: `backend/tests/test_privacy_shuffle.py`
- Modify: `backend/tests/test_app_contract.py`

- [ ] **Step 1: Write failing Finance privacy unit test**

Append this test to `PrivacyShuffleTests` in `backend/tests/test_privacy_shuffle.py`:

```python
    def test_build_protected_llm_summary_supports_finance_buckets(self):
        real_record = {
            "kind": "real",
            "domain": "finance",
            "label": "Real Finance Record",
            "risk_bucket": "attention",
            "overall": "Watch",
            "_anonymous_label": "Synthetic Record 11",
            "model_outputs": [
                {"model": "Credit Risk", "model_id": "credit_risk", "score": 62.4, "status": "watch"},
                {"model": "Loan Stress", "model_id": "loan_stress", "score": 72.1, "status": "attention"},
            ],
            "derived_metrics": {
                "financial_resilience": 0.44,
                "cashflow_burden": 0.67,
                "loan_stress": 0.72,
                "credit_standing": 543,
                "debt_to_income": 1.4,
            },
        }

        summary = build_protected_llm_summary(real_record)

        self.assertEqual(summary["domain"], "finance")
        self.assertEqual(summary["record"], "Synthetic Record 11")
        self.assertEqual(summary["risk_profile"]["financial_resilience_bucket"], "40-45%")
        self.assertEqual(summary["metrics"]["loan_stress"], "70-75%")
        self.assertEqual(summary["metrics"]["credit_standing"], "500-550")
        self.assertNotIn("543", str(summary))
        self.assertNotIn("72.1", str(summary))
```

- [ ] **Step 2: Write failing Finance report endpoint test**

Append this method inside `AppContractTests`:

```python
    async def test_finance_report_uses_finance_domain_prompt_and_report(self):
        dispatch = await self.client.get(
            "/api/dispatch",
            params={"scenario": "finance", "selected_modalities": "income,expenses,savings,loan,credit"},
        )
        self.assertEqual(dispatch.status_code, 200)
        session_id = dispatch.json()["session_id"]

        response = await self.client.get(
            "/api/report",
            params={"session_id": session_id, "llm_provider": "zhipu"},
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload.get("scenario"), "finance")
        self.assertEqual(payload.get("data_source"), "synthetic_personal_finance_dataset.csv")
        report = payload["step3"]["report"]
        prompt = payload["step3"]["plaintext_prompt"]
        self.assertEqual(report.get("domain"), "finance")
        self.assertEqual(report.get("score_label"), "Financial resilience")
        self.assertIn("Financial Risk Summary", report["summary"]["title"])
        self.assertIn("personal finance risk analysis", prompt)
        self.assertNotIn("health", prompt.lower())
        self.assertNotIn("clinical", prompt.lower())
        self.assertNotIn("fall probability", prompt.lower())
```

- [ ] **Step 3: Run tests and verify they fail**

Run:

```bash
cd /home/hkustgz/Us/Encry_LLM_HealthReport
source venv/bin/activate
python -m unittest backend.tests.test_privacy_shuffle.PrivacyShuffleTests.test_build_protected_llm_summary_supports_finance_buckets backend.tests.test_app_contract.AppContractTests.test_finance_report_uses_finance_domain_prompt_and_report -v
```

Expected: fail because Finance protected summary/report path is missing.

- [ ] **Step 4: Add Finance summary support in `backend/privacy_shuffle.py`**

Modify `build_protected_llm_summary` so the first lines branch on domain:

```python
def build_protected_llm_summary(record: Dict[str, Any]) -> Dict[str, Any]:
    if record.get("domain") == "finance":
        metrics = record.get("derived_metrics", {})
        return {
            "domain": "finance",
            "record": record.get("_anonymous_label", record.get("label", "Synthetic Record")),
            "risk_profile": {
                "overall": record.get("overall", "Watch"),
                "financial_resilience_bucket": _bucket_percent(metrics.get("financial_resilience")),
                "risk_bucket": record.get("risk_bucket", "attention"),
            },
            "metrics": {
                "cashflow_burden": _bucket_percent(metrics.get("cashflow_burden")),
                "loan_stress": _bucket_percent(metrics.get("loan_stress")),
                "credit_standing": _bucket_number(metrics.get("credit_standing"), width=50),
                "debt_to_income": _bucket_number(metrics.get("debt_to_income"), width=1),
            },
            "model_results": [
                {
                    "model": output.get("model"),
                    "status": output.get("status"),
                    "score_bucket": _bucket_number(output.get("score")),
                }
                for output in record.get("model_outputs", [])
            ],
        }

    metrics = record.get("derived_metrics", {})
```

Leave the existing Healthcare return body after this branch.

- [ ] **Step 5: Add Finance real record and report builders in `backend/app.py`**

Insert after `_build_bucketed_llm_prompt`:

```python
def _bucket_label(value: float, low_label: str = "low", mid_label: str = "watch", high_label: str = "attention") -> str:
    if value >= 0.70:
        return high_label
    if value >= 0.40:
        return mid_label
    return low_label


def build_finance_report(raw_results: List[Dict[str, Any]], record: Dict[str, str], selected_modalities: List[str]) -> Dict[str, Any]:
    income = max(safe_float(record.get("monthly_income_usd")), 0.0)
    expenses = max(safe_float(record.get("monthly_expenses_usd")), 0.0)
    savings = max(safe_float(record.get("savings_usd")), 0.0)
    emi = max(safe_float(record.get("monthly_emi_usd")), 0.0)
    credit_score = safe_float(record.get("credit_score"), 600.0)
    debt_to_income = max(safe_float(record.get("debt_to_income_ratio")), 0.0)
    savings_to_income = max(safe_float(record.get("savings_to_income_ratio")), 0.0)
    expense_ratio = _clamp(safe_ratio(expenses, income), 0.0, 1.2)
    emi_ratio = _clamp(safe_ratio(emi, income), 0.0, 1.2)
    cashflow_burden = _clamp(expense_ratio, 0.0, 1.0)
    loan_stress = _clamp(0.65 * emi_ratio + 0.35 * min(debt_to_income / 2.0, 1.0), 0.0, 1.0)
    credit_risk = _clamp((680.0 - credit_score) / 380.0, 0.0, 1.0)
    savings_resilience = _clamp(min(savings_to_income / 6.0, savings / max(income, 1.0) / 12.0), 0.0, 1.0)
    risk = _clamp(0.35 * cashflow_burden + 0.30 * loan_stress + 0.25 * credit_risk + 0.10 * (1.0 - savings_resilience), 0.0, 1.0)
    resilience_index = 1.0 - risk

    if risk >= 0.70:
        overall = "Attention"
    elif risk >= 0.40:
        overall = "Watch"
    else:
        overall = "Stable"

    def metric(name: str, value: float, unit: str, ref: str, status: str, detail: str = "") -> Dict[str, Any]:
        return {"name": name, "value": float(value), "unit": unit, "ref": ref, "status": status, "detail": detail}

    metrics = [
        metric("Expense burden", cashflow_burden * 100, "%", "<70", _bucket_label(cashflow_burden, "stable", "watch", "attention")),
        metric("Savings resilience", savings_resilience * 100, "%", ">55", "stable" if savings_resilience >= 0.55 else "watch"),
        metric("Loan stress", loan_stress * 100, "%", "<40", _bucket_label(loan_stress, "stable", "watch", "attention")),
        metric("Credit standing", credit_score, "score", "670+", "stable" if credit_score >= 670 else "watch"),
        metric("Debt to income", debt_to_income, "ratio", "<0.40", _bucket_label(min(debt_to_income / 2.0, 1.0), "stable", "watch", "attention")),
    ]

    selected_names = [FINANCE_MODALITY_NAME_BY_ID[item_id].lower() for item_id in selected_modalities]
    sections = [
        {
            "id": "integrated_financial_risk",
            "title": "Integrated Financial Risk",
            "status": overall.lower(),
            "priority": 95,
            "source_modalities": selected_names,
            "chart_type": "radar",
            "chart": {
                "labels": ["Cashflow", "Savings", "Loan", "Credit", "Resilience"],
                "values": [
                    float(100 * (1.0 - cashflow_burden)),
                    float(100 * savings_resilience),
                    float(100 * (1.0 - loan_stress)),
                    float(100 * (1.0 - credit_risk)),
                    float(100 * resilience_index),
                ],
            },
            "metrics": [metric("Financial resilience", resilience_index * 100, "%", "70-100", "stable" if resilience_index >= 0.70 else "watch")],
            "insight": "Selected financial evidence is summarized into a protected resilience score.",
            "expanded": True,
        },
        {
            "id": "cashflow_balance",
            "title": "Cashflow Balance",
            "status": _bucket_label(cashflow_burden, "stable", "watch", "attention"),
            "priority": 80,
            "source_modalities": ["income", "expenses"],
            "chart_type": "reference_bars",
            "chart": {"labels": ["Income", "Expenses"], "values": [float(income), float(expenses)], "ranges": {"Expenses": [0, max(income * 0.7, 1.0)]}},
            "metrics": metrics[:1],
            "insight": "Monthly spending is compared with income capacity.",
            "expanded": True,
        },
        {
            "id": "loan_affordability",
            "title": "Loan Affordability",
            "status": _bucket_label(loan_stress, "stable", "watch", "attention"),
            "priority": 75,
            "source_modalities": ["loan", "credit"],
            "chart_type": "reference_bars",
            "chart": {"labels": ["EMI ratio", "DTI"], "values": [float(emi_ratio * 100), float(debt_to_income * 100)], "ranges": {"EMI ratio": [0, 35], "DTI": [0, 40]}},
            "metrics": metrics[2:5],
            "insight": "Repayment pressure is estimated from EMI, leverage, and credit context.",
            "expanded": True,
        },
    ]

    recos = [
        "Keep monthly fixed repayments within a conservative share of income.",
        "Build or preserve an emergency savings buffer before increasing discretionary spending.",
        "Review high-interest debt first when reducing repayment pressure.",
        "This demo report is not financial, tax, legal, investment, or lending advice.",
    ]
    if overall == "Attention":
        recos.insert(0, "Financial pressure appears elevated in this protected demo summary; prioritize cashflow stabilization.")
    elif overall == "Watch":
        recos.insert(0, "Financial resilience appears mixed; monitor spending and repayment ratios before taking on new debt.")

    return {
        "domain": "finance",
        "score_label": "Financial resilience",
        "overall": overall,
        "disclaimer": "Demo output only — not financial advice.",
        "fall_risk": {"probability": float(risk), "level": overall, "drivers": []},
        "summary": {
            "title": "Financial Risk Summary",
            "health_index": float(resilience_index),
            "overall": overall,
            "drivers": [item["name"] for item in metrics if item["status"] != "stable"][:4],
            "coverage": {"selected_modalities": selected_modalities, "available_theme_count": len(sections), "total_theme_count": 6},
        },
        "sections": sections,
        "compact_sections": [],
        "missing_signals": [],
        "metrics": metrics,
        "recommendations": recos,
        "narrative": f"Overall status: {overall}. Financial resilience estimate: {resilience_index:.2f}.",
        "charts": {"radar": sections[0]["chart"]},
    }
```

- [ ] **Step 6: Add Finance privacy bundle and prompt builders in `backend/app.py`**

Insert after `build_finance_report`:

```python
def _build_finance_real_data_record(raw_results: List[Dict[str, Any]], raw_report: Dict[str, Any], record: Dict[str, str]) -> Dict[str, Any]:
    metric_by_name = {item["name"]: item for item in raw_report.get("metrics", [])}
    return {
        "kind": "real",
        "domain": "finance",
        "label": "Real Finance Record",
        "risk_bucket": str(raw_report.get("overall", "Watch")).lower(),
        "overall": raw_report.get("overall", "Watch"),
        "model_outputs": copy.deepcopy(raw_results),
        "derived_metrics": {
            "financial_resilience": raw_report.get("summary", {}).get("health_index"),
            "cashflow_burden": safe_float(metric_by_name.get("Expense burden", {}).get("value")) / 100.0,
            "loan_stress": safe_float(metric_by_name.get("Loan stress", {}).get("value")) / 100.0,
            "credit_standing": safe_float(record.get("credit_score")),
            "debt_to_income": safe_float(record.get("debt_to_income_ratio")),
        },
    }


def _build_finance_privacy(raw_results: List[Dict[str, Any]], raw_report: Dict[str, Any], record: Dict[str, str], rng: random.Random) -> Dict[str, Any]:
    real_record = _build_finance_real_data_record(raw_results, raw_report, record)
    synthetic_records = generate_synthetic_database(real_record, database_size=100, rng=rng)
    anonymous_bundle = build_anonymous_database(real_record, synthetic_records, rng=rng)
    protected_llm_summary = build_protected_llm_summary(anonymous_bundle["selected_record"])
    distribution_summary = build_distribution_summary(anonymous_bundle)
    distribution_summary["axes"] = {
        "x": "loan_stress_percentile",
        "y": "savings_resilience_percentile",
        "x_source": "loan_stress",
        "y_source": "financial_resilience",
    }
    return {
        "protected_llm_summary": protected_llm_summary,
        "privacy_protection": {
            "enabled": True,
            "method": "synthetic_database_shuffle",
            "database_size": len(anonymous_bundle["anonymous_database"]),
            "synthetic_record_count": distribution_summary["synthetic_record_count"],
            "distribution_summary": {
                "risk_buckets": distribution_summary["risk_buckets"],
                "scatter_points": distribution_summary["scatter_points"],
                "target_point": distribution_summary["target_point"],
                "axes": distribution_summary["axes"],
            },
            "token_flow": distribution_summary["token_flow"],
            "anonymous_database_preview": anonymous_bundle["anonymous_database_preview"],
            "shuffle_order_preview": anonymous_bundle["shuffle_order_preview"],
            "selected_record_label": anonymous_bundle["selected_record_label"],
            "selected_record_index": anonymous_bundle["selected_record_index"],
            "llm_summary_mode": "bucketed_non_trusted",
            "protected_llm_summary_preview": protected_llm_summary,
            "generation_policy": {
                "distribution": "finance-risk-bucket conditioned",
                "constraints": ["bucketed finance metrics", "no raw user identifier", "no exact financial amounts"],
            },
            "summary": "Synthetic finance peers mask the real inference record before a bucketed summary is sent to the non-trusted LLM.",
        },
    }


def _build_finance_llm_prompt(protected_llm_summary: Dict[str, Any], raw_report: Dict[str, Any]) -> str:
    section_summary = _build_bucketed_section_prompt_summary(raw_report)
    return (
        "You are a privacy-preserving personal finance risk analysis expert. "
        "The external model can only see a bucketed privacy-preserving summary. "
        f"Record: {protected_llm_summary['record']}; "
        f"Overall status: {protected_llm_summary['risk_profile']['overall']}; "
        f"Financial resilience bucket: {protected_llm_summary['risk_profile']['financial_resilience_bucket']}; "
        f"Metric summary: {protected_llm_summary['metrics']}; "
        f"Section summary: {section_summary}; "
        f"Model summary: {protected_llm_summary['model_results'][:3]}. "
        "Generate a concise and cautious financial risk conclusion. "
        "Do not provide tax, legal, investment, or lending advice."
    )
```

Add `import copy` at the top of `backend/app.py`.

- [ ] **Step 7: Route `_build_privacy_prompt_payload` and `_build_privacy_and_report` by scenario**

At the top of `_build_privacy_prompt_payload`, add:

```python
    scenario = session.get("scenario", "healthcare")
    if scenario == "finance":
        raw_results = session["raw_results"]
        record = session["finance_record"]
        selected_ids = list(session.get("selected_modalities") or [])
        raw_report = build_finance_report(raw_results, record, selected_ids)
        rng = random.Random(session["seed"])
        privacy_bundle = _build_finance_privacy(raw_results, raw_report, record, rng)
        prompt = _build_finance_llm_prompt(privacy_bundle["protected_llm_summary"], raw_report)
        return {
            "raw_results": raw_results,
            "raw_report": raw_report,
            "privacy_bundle": privacy_bundle,
            "prompt": prompt,
        }
```

In `/api/report` return payload, include scenario and Finance data source:

```python
    scenario = session.get("scenario", "healthcare")
    return {
        "schema": "he-multimodal-report/v1",
        "scenario": scenario,
        "session_id": session_id,
        "generated_at": session["generated_at"],
        "step3": session["step3"],
        "privacy_protection": session["privacy_protection"],
        "data_source": "synthetic_personal_finance_dataset.csv" if scenario == "finance" else "UT_HAR dataset",
        "llm_provider": session.get("llm_provider", llm_provider_label(provider_key)),
    }
```

In `/api/privacy_shuffle` response, include `"scenario": session.get("scenario", "healthcare")`.

- [ ] **Step 8: Run Finance privacy/report tests**

Run:

```bash
cd /home/hkustgz/Us/Encry_LLM_HealthReport
source venv/bin/activate
python -m unittest backend.tests.test_privacy_shuffle.PrivacyShuffleTests.test_build_protected_llm_summary_supports_finance_buckets backend.tests.test_app_contract.AppContractTests.test_finance_report_uses_finance_domain_prompt_and_report -v
```

Expected: both tests pass.

- [ ] **Step 9: Run existing privacy tests to catch regressions**

Run:

```bash
cd /home/hkustgz/Us/Encry_LLM_HealthReport
source venv/bin/activate
python -m unittest backend.tests.test_privacy_shuffle backend.tests.test_app_contract.AppContractTests.test_cycle_keeps_precise_dashboard_report_and_results -v
```

Expected: all tests pass.

- [ ] **Step 10: Verification checkpoint**

Run:

```bash
cd /home/hkustgz/Us/Encry_LLM_HealthReport
git status --short backend/app.py backend/privacy_shuffle.py backend/tests/test_app_contract.py backend/tests/test_privacy_shuffle.py
```

Expected: files modified; no commit.

---

### Task 5: Add Frontend Scene Tabs and Finance Cards

**Files:**
- Modify: `frontend/index.html`
- Modify: `frontend/assets/js/modalityCards.js`
- Modify: `frontend/assets/js/modality-selector.js`
- Modify: `frontend/assets/css/styles.css`

- [ ] **Step 1: Add scene tabs to `frontend/index.html`**

Inside `<header class="workflow-header">`, after `.workflow-title`, insert:

```html
      <div class="scene-tabs" id="sceneTabs" role="tablist" aria-label="Analysis scene">
        <button class="scene-tab active" type="button" role="tab" aria-selected="true" data-scenario="healthcare">Healthcare</button>
        <button class="scene-tab" type="button" role="tab" aria-selected="false" data-scenario="finance">Finance</button>
      </div>
```

Add ids to scene-sensitive text:

```html
        <li class="step active" data-step="select"><span>1</span><b id="stepSelectLabel">Select Medical Data</b></li>
```

If wrapping step text in `<b>` disrupts styling, use a plain `<span id="stepSelectLabel" class="step-label">Select Medical Data</span>`.

Add ids to these elements:

```html
<h2 id="dataPanelTitle">Select Medical Data</h2>
<p id="dataPanelSubtitle">Choose multimodal data sources for encrypted health inference.</p>
<h2 id="modelPanelTitle">Multimodal Data Encoders</h2>
<p id="modelPanelSubtitle">Selected medical data are dispatched to specialized local encoders.</p>
<h2 id="reportPanelTitle">Protected Health Report</h2>
<p id="reportPanelSubtitle">Privacy-preserved clinical summary with status and recommendations.</p>
```

- [ ] **Step 2: Add tab styles to `frontend/assets/css/styles.css`**

Append:

```css
.scene-tabs {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 4px;
  border: 1px solid rgba(148, 163, 184, 0.35);
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.78);
}

.scene-tab {
  border: 0;
  border-radius: 6px;
  background: transparent;
  color: #475569;
  cursor: pointer;
  font: inherit;
  font-size: 13px;
  font-weight: 700;
  line-height: 1;
  padding: 9px 12px;
}

.scene-tab.active {
  background: #111827;
  color: #ffffff;
}

.scene-tab:focus-visible {
  outline: 2px solid #2563eb;
  outline-offset: 2px;
}
```

- [ ] **Step 3: Add Finance card config in `frontend/assets/js/modalityCards.js`**

Add Finance colors:

```javascript
  'Income': '#0f766e',
  'Expenses': '#b91c1c',
  'Savings': '#15803d',
  'Loan': '#7c3aed',
  'Credit': '#1d4ed8',
  'Profile': '#475569'
```

Add Finance entries to `MODALITY_CONFIG`:

```javascript
  'income': {
    id: 'income',
    name: 'Income',
    type: 'finance',
    icon: '$',
    description: 'Monthly income and earning capacity baseline',
    color: MODALITY_COLORS.Income
  },
  'expenses': {
    id: 'expenses',
    name: 'Expenses',
    type: 'finance',
    icon: '-',
    description: 'Monthly spending burden',
    color: MODALITY_COLORS.Expenses
  },
  'savings': {
    id: 'savings',
    name: 'Savings',
    type: 'finance',
    icon: '+',
    description: 'Savings buffer and liquidity resilience',
    color: MODALITY_COLORS.Savings
  },
  'loan': {
    id: 'loan',
    name: 'Loan',
    type: 'finance',
    icon: '%',
    description: 'Loan balance, payment, and interest pressure',
    color: MODALITY_COLORS.Loan
  },
  'credit': {
    id: 'credit',
    name: 'Credit',
    type: 'finance',
    icon: '#',
    description: 'Credit score and debt-to-income leverage',
    color: MODALITY_COLORS.Credit
  },
  'profile': {
    id: 'profile',
    name: 'Profile',
    type: 'finance',
    icon: 'i',
    description: 'Employment and regional context',
    color: MODALITY_COLORS.Profile
  },
```

In `createModalityCard(modalityKey, modalityData)`, add this before image/timeseries handling:

```javascript
  if (config.type === 'finance') {
    const preview = modalityData && modalityData.preview ? modalityData.preview : {};
    const previewRows = Object.entries(preview).slice(0, 3).map(([key, value]) => `
      <div class="finance-preview-row">
        <span>${key.replaceAll('_', ' ')}</span>
        <strong>${value === null || value === undefined || value === '' ? '-' : String(value)}</strong>
      </div>
    `).join('');
    visualContent = `
      <div class="card-visual">
        <div class="finance-card-preview" style="--finance-color:${config.color}">
          ${previewRows || `<div class="finance-preview-row"><span>Protected field group</span><strong>${config.name}</strong></div>`}
        </div>
      </div>
    `;
  } else if (uploaded) {
```

The existing current code starts with `if (uploaded)`. Change that block into a three-branch chain: first `if (config.type === 'finance')`, then `else if (uploaded)`, then the existing empty-upload `else`, preserving the current uploaded and empty upload branch bodies.

- [ ] **Step 4: Add Finance card CSS**

Append to `frontend/assets/css/styles.css`:

```css
.finance-card-preview {
  display: grid;
  gap: 7px;
  min-height: 130px;
  align-content: center;
  border-radius: 8px;
  background: linear-gradient(180deg, rgba(248, 250, 252, 0.96), rgba(241, 245, 249, 0.92));
  border: 1px solid rgba(148, 163, 184, 0.28);
  padding: 12px;
}

.finance-preview-row {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 8px;
  align-items: center;
  font-size: 11px;
  color: #64748b;
}

.finance-preview-row strong {
  color: var(--finance-color, #111827);
  font-size: 12px;
  max-width: 96px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
```

- [ ] **Step 5: Add scenario state and scene labels in `frontend/assets/js/modality-selector.js`**

In the constructor, add:

```javascript
    this.currentScenario = 'healthcare';
```

Add methods to the class:

```javascript
  getScenarioLabels() {
    if (this.currentScenario === 'finance') {
      return {
        selectStep: 'Select Financial Data',
        dataTitle: 'Select Financial Data',
        dataSubtitle: 'Choose financial field groups for encrypted risk inference.',
        modelTitle: 'Financial Data Encoders',
        modelSubtitle: 'Selected financial data are dispatched to specialized local encoders.',
        reportTitle: 'Protected Financial Risk Report',
        reportSubtitle: 'Privacy-preserved financial summary with status and recommendations.',
        emptyCluster: 'Select financial data, then run analysis to activate local encoders.',
        emptyResults: 'Select financial data and run analysis to populate results.',
        privacyEmpty: 'Select financial data and run analysis to open the anonymized shuffle flow.',
      };
    }
    return {
      selectStep: 'Select Medical Data',
      dataTitle: 'Select Medical Data',
      dataSubtitle: 'Choose multimodal data sources for encrypted health inference.',
      modelTitle: 'Multimodal Data Encoders',
      modelSubtitle: 'Selected medical data are dispatched to specialized local encoders.',
      reportTitle: 'Protected Health Report',
      reportSubtitle: 'Privacy-preserved clinical summary with status and recommendations.',
      emptyCluster: 'Select medical data, then run analysis to activate local encoders.',
      emptyResults: 'Select medical data and run analysis to populate results.',
      privacyEmpty: 'Select medical data and run analysis to open the anonymized shuffle flow.',
    };
  }

  applyScenarioLabels() {
    const labels = this.getScenarioLabels();
    const setText = (id, text) => {
      const el = document.getElementById(id);
      if (el) el.textContent = text;
    };
    setText('stepSelectLabel', labels.selectStep);
    setText('dataPanelTitle', labels.dataTitle);
    setText('dataPanelSubtitle', labels.dataSubtitle);
    setText('modelPanelTitle', labels.modelTitle);
    setText('modelPanelSubtitle', labels.modelSubtitle);
    setText('reportPanelTitle', labels.reportTitle);
    setText('reportPanelSubtitle', labels.reportSubtitle);
  }
```

- [ ] **Step 6: Make API requests scenario-aware**

In `loadModalities`, change the URL to:

```javascript
      const response = await this.fetchWithTimeout(`${apiBase}/api/modalities?scenario=${encodeURIComponent(this.currentScenario)}`, {
```

In `loadModalityThumbnails`, change the URL to:

```javascript
          `${apiBase}/api/modality_thumbnail?scenario=${encodeURIComponent(this.currentScenario)}&modality=${encodeURIComponent(modality.name)}`,
```

In `launchAnalysisWithRetry`, change the dispatch URL to:

```javascript
        `${apiBase}/api/dispatch?scenario=${encodeURIComponent(this.currentScenario)}&selected_modalities=${encodeURIComponent(selectedList)}`
```

- [ ] **Step 7: Add scene tab event handling**

In `attachEventListeners`, add:

```javascript
    document.querySelectorAll('.scene-tab[data-scenario]').forEach((button) => {
      button.addEventListener('click', () => {
        this.switchScenario(button.dataset.scenario);
      });
    });
```

Add this class method:

```javascript
  async switchScenario(nextScenario) {
    const normalized = String(nextScenario || 'healthcare').toLowerCase();
    if (normalized === this.currentScenario || this.isLoading) return;
    this.currentScenario = normalized;
    document.querySelectorAll('.scene-tab[data-scenario]').forEach((button) => {
      const active = button.dataset.scenario === normalized;
      button.classList.toggle('active', active);
      button.setAttribute('aria-selected', active ? 'true' : 'false');
    });
    this.selectedModalities.clear();
    this.modalityThumbnails = {};
    this.uploadedModalityImages = {};
    this.applyScenarioLabels();
    this.resetWorkflowForScenario();
    this.setLoadingState(true);
    try {
      await this.loadModalities();
      await this.loadModalityThumbnails();
      this.renderCards();
      this.updateSelectionUI();
      this.updateModelCluster();
    } catch (error) {
      console.error('Scenario switch failed:', error);
      this.showError(`Scenario switch failed: ${error.message}`);
    } finally {
      this.setLoadingState(false);
    }
  }
```

Add reset method:

```javascript
  resetWorkflowForScenario() {
    const labels = this.getScenarioLabels();
    const resultTable = document.querySelector('#resultTable tbody');
    if (resultTable) {
      resultTable.innerHTML = `<tr><td colspan="4" style="text-align:center; color: #9ca3af; padding: 20px;">${labels.emptyResults}</td></tr>`;
    }
    const privacyPanel = document.getElementById('privacyPanel');
    if (privacyPanel) privacyPanel.innerHTML = labels.privacyEmpty;
    const resultsTitle = document.getElementById('resultsTitle');
    if (resultsTitle) resultsTitle.textContent = 'Key results (waiting for analysis)';
    const recommendPanel = document.getElementById('recommendPanel');
    if (recommendPanel) recommendPanel.innerHTML = 'Recommendations will appear after analysis.';
    const conclusionPanel = document.getElementById('conclusionPanel');
    if (conclusionPanel) conclusionPanel.innerHTML = 'Report status will appear after analysis.';
    ['tUpload', 'tDispatch', 'tProtect', 'tDecrypt'].forEach((id) => {
      const pill = document.getElementById(id);
      if (pill) {
        pill.className = 'pill';
        pill.textContent = '—';
      }
    });
    if (typeof setWorkflowStep === 'function') setWorkflowStep('select');
  }
```

Call `this.applyScenarioLabels();` during `init()` before `loadModalities()`.

- [ ] **Step 8: Make model cluster scenario-aware**

At the top of `updateModelCluster`, replace the hardcoded `clusterModels` definition with:

```javascript
    const clusterModels = this.currentScenario === 'finance'
      ? [
          { id: 'income_capacity', title: 'Income Capacity', subtitle: 'Income percentile model', modalityId: 'income' },
          { id: 'expense_burden', title: 'Expense Burden', subtitle: 'Cashflow burden model', modalityId: 'expenses' },
          { id: 'savings_resilience', title: 'Savings Resilience', subtitle: 'Liquidity buffer model', modalityId: 'savings' },
          { id: 'loan_stress', title: 'Loan Stress', subtitle: 'Repayment pressure model', modalityId: 'loan' },
          { id: 'credit_risk', title: 'Credit Risk', subtitle: 'Credit and leverage model', modalityId: 'credit' },
          { id: 'profile_context', title: 'Profile Context', subtitle: 'Employment context model', modalityId: 'profile' }
        ]
      : [
          { id: 'sleep', title: 'Sleep Staging', subtitle: 'Depth-based Model', modalityId: 'depth' },
          { id: 'bp', title: 'Blood Pressure', subtitle: 'UWB Regression', modalityId: 'uwb' },
          { id: 'metabolic', title: 'Metabolic Score', subtitle: 'IMU Proxy', modalityId: 'imu' },
          { id: 'ecg', title: 'ECG Arrhythmia', subtitle: 'CSI Heart Pattern', modalityId: 'csi' },
          { id: 'risk', title: 'Risk Assessment', subtitle: 'RGB Triage', modalityId: 'rgb' },
          { id: 'action', title: 'Action Recognition', subtitle: 'Skeleton Model', modalityId: 'ntu' },
          { id: 'cardio', title: 'Cardiovascular', subtitle: 'Retina Analysis', modalityId: 'retina' },
          { id: 'lung', title: 'Lung Screening', subtitle: 'X-ray Analysis', modalityId: 'chest' },
          { id: 'cancer', title: 'Cancer Detection', subtitle: 'Pathology Model', modalityId: 'path' },
          { id: 'blood', title: 'Blood Analysis', subtitle: 'Hematology Model', modalityId: 'blood' }
        ];
```

- [ ] **Step 9: Verify frontend syntax with browser-free checks**

Run:

```bash
cd /home/hkustgz/Us/Encry_LLM_HealthReport
node --check frontend/assets/js/modalityCards.js
node --check frontend/assets/js/modality-selector.js
```

Expected: no syntax errors.

- [ ] **Step 10: Verification checkpoint**

Run:

```bash
cd /home/hkustgz/Us/Encry_LLM_HealthReport
git status --short frontend/index.html frontend/assets/js/modalityCards.js frontend/assets/js/modality-selector.js frontend/assets/css/styles.css
```

Expected: files modified; no commit.

---

### Task 6: Make Report and Privacy Rendering Domain-Aware

**Files:**
- Modify: `frontend/assets/js/app.js`
- Modify: `frontend/assets/js/modality-selector.js`

- [ ] **Step 1: Update `renderDynamicHealthReport` score label**

In `frontend/assets/js/app.js`, inside `renderDynamicHealthReport(report, plaintextPrompt)`, add:

```javascript
  const domain = report.domain || 'healthcare';
  const scoreLabel = report.score_label || (domain === 'finance' ? 'Financial resilience' : 'Health index');
```

Replace hardcoded `Health Index` labels in this function with `${escHtml(scoreLabel)}`. For example:

```javascript
            <div class="summaryLabel">${escHtml(scoreLabel)}</div>
```

If the existing markup uses a chart title, change it to:

```javascript
          <div class="chartTitle">${escHtml(scoreLabel)}</div>
```

- [ ] **Step 2: Update legacy report title fallback**

In `renderLegacyHealthReport`, add:

```javascript
  const scoreLabel = report.score_label || (report.domain === 'finance' ? 'Financial resilience' : 'Health index');
  const reportTitle = report.domain === 'finance' ? 'Protected Financial Risk Report' : 'Multimodal Health Report (demo)';
```

Replace:

```javascript
        <div class="reportTitle">Multimodal Health Report (demo)</div>
```

with:

```javascript
        <div class="reportTitle">${escHtml(reportTitle)}</div>
```

Replace any legacy visible `Health Index` text in that function with `${escHtml(scoreLabel)}`.

- [ ] **Step 3: Update privacy rendering language for Finance**

In `renderPrivacyProtection(privacy)`, add:

```javascript
  const protectedSummary = privacy.protected_llm_summary_preview || {};
  const domain = protectedSummary.domain || 'healthcare';
  const privacyMetricText = domain === 'finance'
    ? 'Model scores / financial buckets / risk profile'
    : 'Model scores / physiological metrics / risk profile';
```

Replace hardcoded:

```javascript
Model scores / physiological metrics / risk profile
```

with:

```javascript
${escHtml(privacyMetricText)}
```

- [ ] **Step 4: Update progress text for Finance**

In `launchAnalysisWithRetry` in `frontend/assets/js/modality-selector.js`, before progress messages that mention health, add:

```javascript
      const reportKind = this.currentScenario === 'finance' ? 'financial risk report' : 'health report';
```

Replace:

```javascript
      this.updateProgress(85, `Generating protected health report with ${llmLabel}...`);
```

with:

```javascript
      this.updateProgress(85, `Generating protected ${reportKind} with ${llmLabel}...`);
```

- [ ] **Step 5: Verify frontend syntax**

Run:

```bash
cd /home/hkustgz/Us/Encry_LLM_HealthReport
node --check frontend/assets/js/app.js
node --check frontend/assets/js/modality-selector.js
```

Expected: no syntax errors.

- [ ] **Step 6: Verification checkpoint**

Run:

```bash
cd /home/hkustgz/Us/Encry_LLM_HealthReport
git status --short frontend/assets/js/app.js frontend/assets/js/modality-selector.js
```

Expected: files modified; no commit.

---

### Task 7: End-to-End Verification

**Files:**
- No new files.
- Verify all touched files.

- [ ] **Step 1: Run backend unit and contract tests**

Run:

```bash
cd /home/hkustgz/Us/Encry_LLM_HealthReport
source venv/bin/activate
python -m unittest discover -s backend/tests -p 'test_*.py' -v
```

Expected: all tests pass.

- [ ] **Step 2: Run focused Finance endpoint smoke checks**

Run:

```bash
cd /home/hkustgz/Us/Encry_LLM_HealthReport
source venv/bin/activate
python - <<'PY'
import asyncio
import importlib.util
from pathlib import Path
import sys
import httpx

root = Path.cwd()
backend_dir = root / "backend"
sys.path.insert(0, str(backend_dir))
spec = importlib.util.spec_from_file_location("backend_app_module", backend_dir / "app.py")
backend = importlib.util.module_from_spec(spec)
spec.loader.exec_module(backend)

async def fake_llm(prompt, provider=None, max_tokens=1024):
    return "finance smoke conclusion"

async def main():
    backend.call_selected_llm = fake_llm
    transport = httpx.ASGITransport(app=backend.app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        modalities = await client.get("/api/modalities", params={"scenario": "finance"})
        print("modalities", modalities.status_code, [item["id"] for item in modalities.json()["modalities"]])
        dispatch = await client.get("/api/dispatch", params={"scenario": "finance", "selected_modalities": "income,credit,loan"})
        dispatch_payload = dispatch.json()
        print("dispatch", dispatch.status_code, dispatch_payload.get("scenario"), dispatch_payload.get("data_source"))
        privacy = await client.get("/api/privacy_shuffle", params={"session_id": dispatch_payload["session_id"]})
        print("privacy", privacy.status_code, privacy.json()["privacy_protection"]["protected_llm_summary_preview"]["domain"])
        report = await client.get("/api/report", params={"session_id": dispatch_payload["session_id"], "llm_provider": "zhipu"})
        report_payload = report.json()
        print("report", report.status_code, report_payload["step3"]["report"]["domain"], report_payload["step3"]["report"]["score_label"])

asyncio.run(main())
PY
```

Expected:

```text
modalities 200 ['income', 'expenses', 'savings', 'loan', 'credit', 'profile']
dispatch 200 finance synthetic_personal_finance_dataset.csv
privacy 200 finance
report 200 finance Financial resilience
```

- [ ] **Step 3: Run frontend syntax checks**

Run:

```bash
cd /home/hkustgz/Us/Encry_LLM_HealthReport
node --check frontend/assets/js/app.js
node --check frontend/assets/js/modalityCards.js
node --check frontend/assets/js/modality-selector.js
```

Expected: no syntax errors.

- [ ] **Step 4: Start backend on allowed port**

Run:

```bash
cd /home/hkustgz/Us/Encry_LLM_HealthReport
source venv/bin/activate
python - <<'PY'
import socket
for port in (8082, 8083, 8084):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        if sock.connect_ex(("127.0.0.1", port)) != 0:
            print(port)
            break
PY
```

Use the printed port. If it prints `8082`, run:

```bash
cd /home/hkustgz/Us/Encry_LLM_HealthReport/backend
source ../venv/bin/activate
uvicorn app:app --host 127.0.0.1 --port 8082
```

Expected: backend starts without import errors. Keep this session running for manual browser validation.

- [ ] **Step 5: Start frontend on preferred port**

In a second terminal:

```bash
cd /home/hkustgz/Us/Encry_LLM_HealthReport/frontend
python -m http.server 8001
```

Expected: frontend starts at `http://127.0.0.1:8001`.

- [ ] **Step 6: Manual browser validation**

Open:

```text
http://127.0.0.1:8001
```

Validate:

- Healthcare tab is active by default.
- Healthcare cards still load.
- Select Healthcare cards and run a short flow through dispatch, shuffle, LLM selection, and report.
- Click Finance.
- Finance cards are `Income`, `Expenses`, `Savings`, `Loan`, `Credit`, `Profile`.
- Model panel shows Finance encoders.
- Select `Income`, `Credit`, and `Loan`.
- Run analysis.
- Privacy panel uses financial bucket wording.
- Report title is `Protected Financial Risk Report`.
- Report score label is `Financial resilience`.
- Prompt/conclusion text avoids healthcare terms.

- [ ] **Step 7: Stop servers**

Stop the backend and frontend terminal processes with `Ctrl+C`.

- [ ] **Step 8: Final status checkpoint**

Run:

```bash
cd /home/hkustgz/Us/Encry_LLM_HealthReport
git status --short
```

Expected: only intentional files are modified or added. Do not commit unless the user explicitly asks.

---

## Self-Review Checklist

- Spec coverage:
  - Header tab: Task 5.
  - Runtime CSV in `test_data/`: Task 1.
  - Scenario parameter and default Healthcare behavior: Task 2 and Task 3.
  - Finance multi-select cards and encoders: Task 3 and Task 5.
  - Finance prompt and report: Task 4 and Task 6.
  - Finance privacy buckets: Task 4 and Task 6.
  - Error handling for missing fields and unknown scenario: Task 2 and Task 3.
  - Testing and manual validation: Task 7.
- Placeholder scan:
  - No `TBD`, `TODO`, `implement later`, or unbounded “add tests” instructions.
- Type consistency:
  - Scenario strings are `healthcare` and `finance`.
  - Finance modality ids are `income`, `expenses`, `savings`, `loan`, `credit`, `profile`.
  - Finance report domain is `finance`.
  - Compatibility score field remains `summary.health_index`; display label is `score_label`.
