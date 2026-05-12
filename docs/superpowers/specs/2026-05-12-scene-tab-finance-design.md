# Scene Tab Finance Design

## Goal

Add a top-level scene switch to the existing privacy-preserving multimodal workflow so the demo can run in both Healthcare and Finance domains.

The existing Healthcare flow must keep its current stages and default behavior. Finance should reuse the same staged workflow while replacing the domain-specific data panel, local encoder panel, LLM prompt, and generated report.

## Approved Direction

Use a global header tab:

- Healthcare
- Finance

The active tab represents the dashboard's current scene. It is not just a filter inside the data panel.

Use a shared workflow controlled by a `scenario` parameter instead of copying the workflow:

- `healthcare` remains the default when no scenario is provided.
- `finance` activates finance data cards, finance local encoders, finance prompt text, finance privacy buckets, and finance report content.

## Data Placement

Move the prepared finance CSV out of the zip archive for runtime use:

- Source archive: `dataset/archive.zip`
- Source file in archive: `synthetic_personal_finance_dataset.csv`
- Runtime file: `test_data/synthetic_personal_finance_dataset.csv`

The archive can remain as the original packaged data source. Backend runtime code should read from `test_data/synthetic_personal_finance_dataset.csv`.

Expected dataset shape:

- Rows: 32,424
- Columns: 20
- Required fields:
  - `user_id`
  - `age`
  - `gender`
  - `education_level`
  - `employment_status`
  - `job_title`
  - `monthly_income_usd`
  - `monthly_expenses_usd`
  - `savings_usd`
  - `has_loan`
  - `loan_type`
  - `loan_amount_usd`
  - `loan_term_months`
  - `monthly_emi_usd`
  - `loan_interest_rate_pct`
  - `debt_to_income_ratio`
  - `credit_score`
  - `savings_to_income_ratio`
  - `region`
  - `record_date`

## Frontend Behavior

Add scene tabs in the workflow header near the product title and primary action. The selected scene is stored in the existing frontend controller, for example `ModalitySelector.currentScenario`.

All scene-sensitive requests should include the selected scenario:

- `/api/modalities?scenario=finance`
- `/api/modality_thumbnail?scenario=finance&modality=income`
- `/api/dispatch?scenario=finance&selected_modalities=income,expenses,loan`
- `/api/privacy_shuffle?session_id=...`
- `/api/report?session_id=...&llm_provider=qwen`

`privacy_shuffle` and `report` can infer the scenario from the staged session after `dispatch`, so they do not need a separate scenario parameter.

When the user switches scene:

- Clear selected cards.
- Reload modality cards for the selected scene.
- Reset model cluster to the selected scene's inactive encoders.
- Reset result table, privacy panel, report panel, progress, and status pills.
- Keep the same LLM provider selector behavior.

Healthcare labels should remain unchanged by default. Finance labels should replace domain-specific text:

- Step 1: Select Financial Data
- Step 2: Financial Data Encoders
- Step 3: Shuffle
- Step 4: Send to LLM
- Step 5: Report
- Report panel: Protected Financial Risk Report

## Finance Data Cards

Finance uses the same multi-select card model as Healthcare. Initial cards:

- Income
  - Fields: `monthly_income_usd`
  - Purpose: earning capacity and affordability baseline
- Expenses
  - Fields: `monthly_expenses_usd`
  - Purpose: monthly spending burden
- Savings
  - Fields: `savings_usd`, `savings_to_income_ratio`
  - Purpose: liquidity and resilience
- Loan
  - Fields: `has_loan`, `loan_type`, `loan_amount_usd`, `loan_term_months`, `monthly_emi_usd`, `loan_interest_rate_pct`
  - Purpose: repayment pressure and debt terms
- Credit
  - Fields: `credit_score`, `debt_to_income_ratio`
  - Purpose: credit risk and leverage
- Profile
  - Fields: `age`, `employment_status`, `job_title`, `region`, `record_date`
  - Purpose: contextual explanation, not direct identity exposure

The frontend cards should use the existing card layout. Financial cards can show compact textual/statistical previews instead of image thumbnails. If the existing card component requires a visual area, use small chart-like summaries such as bars, mini tables, or numeric tiles generated from the selected finance record.

## Finance Local Encoders

Finance local encoder cards:

- Income Capacity
  - Model id: `income_capacity`
  - Input: Income
  - Tool: `secure_income_toolbox`
- Expense Burden
  - Model id: `expense_burden`
  - Input: Expenses
  - Tool: `secure_expense_toolbox`
- Savings Resilience
  - Model id: `savings_resilience`
  - Input: Savings
  - Tool: `secure_savings_toolbox`
- Loan Stress
  - Model id: `loan_stress`
  - Input: Loan
  - Tool: `secure_loan_toolbox`
- Credit Risk
  - Model id: `credit_risk`
  - Input: Credit
  - Tool: `secure_credit_toolbox`
- Profile Context
  - Model id: `profile_context`
  - Input: Profile
  - Tool: `secure_profile_toolbox`

Scores should be deterministic and field-derived for the selected record, not random constants. Suggested metrics:

- Income Capacity: income percentile or normalized earning capacity
- Expense Burden: monthly expenses divided by monthly income
- Savings Resilience: savings-to-income ratio and savings buffer
- Loan Stress: EMI-to-income ratio, interest rate, loan amount, and loan term
- Credit Risk: credit score and debt-to-income ratio
- Profile Context: employment and profile context as explanatory status

All ratio calculations must guard against zero or missing income.

## Backend Scenario Layer

Introduce a lightweight scenario layer in `backend/app.py`.

The layer should provide, per scenario:

- modality definitions
- local model definitions
- step1 builder
- step2 builder
- structured report builder
- LLM prompt builder
- privacy summary adapter

Healthcare can initially wrap the current hardcoded behavior. Finance adds new builders while sharing the staged endpoint structure.

Endpoint defaults:

- `/api/modalities` defaults to Healthcare.
- `/api/modality_thumbnail` defaults to Healthcare.
- `/api/dispatch` defaults to Healthcare.
- `/api/cycle` defaults to Healthcare if retained for compatibility.

The staged session stored in `_STAGED_SESSIONS` should include `scenario`, so later privacy and report calls know which domain builder to use.

## Finance Report Shape

Finance should reuse the existing dynamic report JSON shape where practical, with domain metadata added:

- `domain`: `finance`
- `score_label`: `Financial resilience`
- `overall`: `Stable`, `Watch`, or `Attention`
- `summary.title`: `Financial Risk Summary`
- `summary.health_index`: keep as a compatibility numeric score for the existing frontend renderer
- `recommendations`: finance-specific recommendations

Finance report sections:

- Integrated Financial Risk
- Cashflow Balance
- Savings Resilience
- Loan Affordability
- Credit Standing
- Profile Context

The frontend can render existing section cards and charts while changing labels based on `domain` and `score_label`.

## Finance Prompt

The Finance LLM prompt must not use healthcare language such as clinical, patient, health monitoring, fall probability, diagnosis, or medical advice.

Prompt role:

> You are a privacy-preserving personal finance risk analysis expert.

The external LLM should receive only bucketed or summarized values:

- income band
- expense burden bucket
- savings resilience bucket
- credit score bucket
- debt-to-income bucket
- loan stress bucket
- selected finance model statuses
- high-level recommendations context

The prompt should ask for a concise and cautious financial risk conclusion, not personalized legal, tax, investment, or lending advice.

## Privacy Shuffle Adaptation

The existing synthetic database shuffle concept should remain:

- Create a real inference record.
- Generate synthetic peer records around it.
- Shuffle the real record into the synthetic database.
- Send only a bucketed protected summary to the non-trusted LLM.

For Finance, the privacy summary should replace health-specific axes and labels:

- Risk buckets: `low`, `attention`, `elevated`
- Scatter x-axis: debt or loan stress percentile
- Scatter y-axis: savings resilience percentile
- Protected summary fields:
  - financial resilience bucket
  - loan stress bucket
  - credit standing bucket
  - cashflow burden bucket

No raw `user_id`, exact income, exact savings, exact loan amount, exact EMI, or exact credit score should be sent to the LLM prompt.

## Error Handling

Finance scenario should handle:

- Missing `test_data/synthetic_personal_finance_dataset.csv`
  - `/api/modalities?scenario=finance` may still return card definitions.
  - `/api/dispatch?scenario=finance` should return a clear data-file-missing error.
- Missing CSV fields
  - Return a clear error naming the missing required fields.
- Empty selected modalities
  - Keep the same frontend prevention and backend fallback behavior as Healthcare.
- Zero or invalid income
  - Avoid division by zero.
  - Return conservative buckets and status labels.
- Unknown scenario
  - Return a clear unsupported-scenario error for explicit unknown values.
  - Use Healthcare only when the scenario parameter is omitted.

## Test Plan

Backend contract tests:

- `/api/modalities?scenario=healthcare` returns the existing Healthcare card set.
- `/api/modalities?scenario=finance` returns the six Finance cards.
- `/api/dispatch?scenario=finance&selected_modalities=income,credit,loan` returns Finance session data, Finance models, and Finance results.
- `/api/privacy_shuffle?session_id=<finance-session>` returns a Finance-compatible protected privacy summary.
- `/api/report?session_id=<finance-session>` returns a report with `domain: finance`.
- Healthcare staged endpoints still pass existing contract tests.

Data validation tests:

- `test_data/synthetic_personal_finance_dataset.csv` exists.
- It has 32,424 rows and 20 columns after extraction.
- All required fields are present.

Frontend manual validation:

- Healthcare tab keeps the existing flow and labels.
- Finance tab shows Finance cards and Finance encoders.
- Switching tabs clears selected cards and stale results.
- Finance run completes through dispatch, shuffle, LLM selection, and report.
- Report title, score label, section titles, prompt preview, and recommendations use Finance language.

## Change Scope

Expected implementation files:

- `test_data/synthetic_personal_finance_dataset.csv`
- `backend/app.py`
- `backend/privacy_shuffle.py`
- `frontend/index.html`
- `frontend/assets/js/modality-selector.js`
- `frontend/assets/js/modalityCards.js`
- `frontend/assets/js/app.js`
- `frontend/assets/css/styles.css` or `frontend/assets/css/enhancement.css`

Do not add one-click startup scripts. Do not change ports. Do not commit automatically.

## Non-Goals

- Do not train real financial models.
- Do not replace the CKKS/shuffle demonstration pipeline.
- Do not duplicate the entire frontend workflow.
- Do not remove or refactor the existing Healthcare demo beyond what is necessary for scenario routing.
- Do not send raw finance records to the LLM.
