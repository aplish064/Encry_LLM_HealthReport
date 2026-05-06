# Shuffle Privacy Protection Design

Date: 2026-05-02
Status: Draft
Scope: Frontend + backend design only, no implementation in this document

## Goal

Add a privacy-protection stage between encrypted inference and the final health report.

The final displayed report must not directly expose the target user's raw Step 3 outcome.
Instead, the system should generate a synthetic candidate pool, apply shuffle-based selection,
and display only a protected report derived from that shuffled synthetic pool.

## Why

The current demo protects transport and inference, but the final report layer still risks
revealing user-specific outcomes if raw results are sent directly into report rendering or an LLM.

This feature adds a visible and defensible privacy layer:

- backend: real protection logic
- frontend: clear explanation of the novelty

## Product Decisions

Confirmed with the user:

- The privacy feature must be visible on the frontend.
- The page should move from 3 major stages to 4.
- The new stage is a distinct `Shuffle Privacy Protection` step.
- The final two stages should stay visually compact.
- The whole Step 3 output must be protected, not just the final text.
- The privacy stage should use a medium-strength explanation:
  show candidate summaries and shuffle, but not reveal internal reversible mappings.

## Non-Goals

- Do not redesign the entire page layout.
- Do not change the visual language of the current demo.
- Do not expose the real user outcome in the privacy stage UI.
- Do not replace the existing report card/radar/vitals structure.

## User-Facing Flow

The main flow becomes:

1. Multimodal Data
2. Encrypted Inference
3. Shuffle Privacy Protection
4. Protected Health Report

The new Step 3 sits between inference and report generation.
Step 4 keeps the current report presentation style, but all displayed content comes from the
protected synthetic output rather than the raw user result.

## Frontend Design

### Step 3: Shuffle Privacy Protection

This stage should visually explain the protection method without disclosing sensitive internals.

Recommended content:

- `Target outcome received`
  - abstract status only, no raw numeric values
- `Synthetic candidate pool`
  - show 3 to 5 candidate cards
  - each card contains only coarse summaries
- `Shuffle applied`
  - a visible transition or animation cue
- `Protected selection`
  - indicate that one protected candidate was selected for final report rendering

### Candidate Card Content

Each candidate card should show only limited, non-reversible information such as:

- overall status: `Stable`, `Watch`, `Attention`
- fall risk level: `Low`, `Moderate`, `High`
- 2 or 3 metric summary tags:
  - `BP elevated`
  - `Sleep reduced`
  - `Recovery moderate`

Avoid:

- exact original user values
- side-by-side mapping to the target user
- ranking details that imply which candidate came from where

### Step 4: Protected Health Report

Keep the current report visual structure:

- overall badge
- fall risk
- result table
- domain scores
- vitals
- recommendations
- narrative / conclusion

But all of these must come from the selected synthetic protected output.

## Backend Design

### High-Level Pipeline

1. Produce real inference results internally.
2. Derive a coarse-grained privacy profile from the real results.
3. Generate `N` synthetic candidate reports consistent with that profile.
4. Shuffle the candidate pool.
5. Select one candidate as the protected displayed report.
6. Generate final conclusion text from the protected report only.

### Privacy Profile

The real result should be reduced to a coarse profile before synthetic generation.
Examples:

- overall bucket
- fall-risk bucket
- metric trend buckets
- domain-score tendency buckets

This avoids sending exact values into the synthetic report generator or LLM prompt.

### Synthetic Candidate Pool

Recommended initial value:

- pool size `N = 10`

Each candidate report should preserve distribution-level plausibility, but not exact identity.
Candidate generation can reuse the current deterministic demo structure, with bounded perturbation
and bucket-preserving variation.

### Shuffle and Selection

Selection must not always be "the first candidate".

Minimum design:

- generate the full pool
- shuffle the pool
- pick one candidate after shuffle

This is the first defensible version of the novelty.

## API Contract

Keep the existing report contract as stable as possible.

Continue returning:

- `step1`
- `step2`
- `step3.report`
- `step3.report_conclusion`

Add a new block for the frontend privacy stage:

```json
{
  "privacy_protection": {
    "enabled": true,
    "method": "synthetic_shuffle",
    "pool_size": 10,
    "display_candidates": [
      {
        "label": "Candidate A",
        "overall": "Watch",
        "risk_level": "Moderate",
        "metric_summary": ["BP elevated", "Sleep reduced"]
      }
    ],
    "selected_label": "Protected Output",
    "summary": "Final report selected from shuffled synthetic candidates."
  }
}
```

This block should be sufficient for the new Step 3 rendering layer.

## LLM Rule

The LLM must not receive raw final user results for the displayed report.

It may only receive:

- the selected protected candidate report
- or a coarse summary derived from the protected candidate

If no LLM key is configured, fallback text should still describe the protected output, not the raw user result.

## Acceptance Criteria

### Functional

- The page shows 4 stages instead of 3.
- Stage 3 is clearly labeled `Shuffle Privacy Protection`.
- Stage 3 visibly shows synthetic candidate summaries and a shuffle/protected-selection concept.
- The final displayed report is produced from protected synthetic output.
- The LLM prompt, if used, is based on protected output only.

### Safety

- Raw Step 3 values are not directly rendered as the final displayed report.
- The privacy-stage UI does not reveal reversible target-to-candidate mappings.
- Candidate display uses coarse summaries only.

### Compatibility

- Existing report layout in the final stage remains recognizable.
- Existing frontend report widgets can continue consuming the report object shape with minimal changes.

## Risks

### Risk 1: "Fake but obviously fake"

If synthetic candidates look too random, the privacy layer will weaken trust in the demo.

Mitigation:

- keep synthetic data bucket-consistent
- preserve plausible correlations across report fields

### Risk 2: "Privacy theater"

If only the text is protected but metrics and results remain raw, the feature becomes cosmetic.

Mitigation:

- protect the whole final report surface, not just `report_conclusion`

### Risk 3: "Over-explaining the algorithm"

If Step 3 reveals too much detail, the display could undermine the privacy story.

Mitigation:

- show only medium-detail candidate summaries
- do not expose raw mappings or exact candidate provenance

## Implementation Order

1. Backend: synthetic candidate pool, shuffle, protected selection
2. Backend: new `privacy_protection` response block
3. Backend: route final report and LLM prompt through protected output
4. Frontend: convert the flow from 3 stages to 4
5. Frontend: render the new Step 3 privacy stage
6. Frontend: keep Step 4 report visuals and feed them protected report data
7. Verification: confirm the final displayed report no longer directly mirrors raw internal results

## Recommendation

Proceed with a minimal but real implementation:

- true backend shuffle-based protection
- explicit frontend Step 3 visualization
- unchanged Step 4 report style

This is the smallest version that preserves the current demo while making the novelty legible.
