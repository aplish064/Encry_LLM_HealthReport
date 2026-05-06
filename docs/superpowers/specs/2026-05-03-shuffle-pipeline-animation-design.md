# Shuffle Pipeline Animation Design

Date: 2026-05-03
Status: Approved for implementation
Scope: Frontend animation design for the existing `Shuffle Privacy Protection` panel only

## Goal

Improve the existing shuffle privacy panel so it clearly communicates a complete privacy
protection pipeline:

1. Raw encrypted inference profile
2. Synthetic candidate pool
3. Shuffle and linkage masking
4. Protected output

The animation should explain the method, not just add motion. The rest of the dashboard layout
must remain unchanged.

## Confirmed Product Decisions

Confirmed with the user:

- Use a linear conveyor-style pipeline.
- Keep all animation inside the current shuffle/privacy panel.
- Do not redesign or move the model cluster, report panel, page shell, or workflow header.
- Each pipeline step needs its own corresponding animation.
- On first render, play a complete staged explanation.
- After the first staged explanation, switch to a low-intensity idle loop.
- The design direction is based on option A from brainstorming, with clearer step-specific motion.

## Non-Goals

- Do not change backend privacy logic or API contracts.
- Do not add new frontend dependencies.
- Do not introduce Canvas or WebGL for this version.
- Do not rebuild the page layout.
- Do not change report rendering, model cluster rendering, or modality selection behavior.
- Do not add explanatory copy outside the shuffle privacy panel.

## Existing Context

The current frontend already renders the privacy stage through `renderPrivacyProtection(privacy)`
in `frontend/assets/js/app.js`.

The current panel structure includes:

- `privacySummary`
- `privacyMixer`
- `privacyPipeline`

The current mixer has four conceptual columns:

- raw encrypted inference summary
- candidate pool
- shuffle channel
- protected output

The current CSS in `frontend/assets/css/styles.css` already includes privacy-related classes such
as `mixerToken`, `shuffleChamber`, `shuffleLine`, `privacyStage`, and `protectedOutputCard`.
This animation design should build on those existing names and patterns where practical.

## Recommended Approach

Use a CSS-first implementation with a small amount of JavaScript state.

CSS should own the visual motion. JavaScript should only:

- generate the required stage markup
- add the initial playing state after rendering
- switch the panel to an idle state after the staged animation completes
- reset the sequence cleanly when a new analysis result renders

Recommended state classes:

- `privacyPanel is-playing`
- `privacyPanel is-idle`

The initial `is-playing` state runs the explanatory sequence. After approximately 7 to 8 seconds,
JavaScript switches the panel to `is-idle`, where only subtle looped motion remains.

## Panel Structure

Keep the overall privacy panel shape:

```text
privacySummary
privacyMixer
privacyPipeline
```

Enhance only the content inside `privacyMixer` and the active styling of `privacyPipeline`.

### Mixer Columns

The `privacyMixer` should remain a four-part linear flow:

```text
Raw encrypted profile -> Synthetic candidate pool -> Shuffle + linkage mask -> Protected output
```

### Raw Encrypted Profile

Purpose:

Show that the workflow starts from a compact encrypted inference summary, not from raw visible
health values.

Visual elements:

- a compact `Raw profile` card
- 3 or 4 horizontal summary bars
- a small locked/encrypted status chip

Animation:

- on first play, the raw card frame highlights
- summary bars briefly glow or sweep
- the encrypted status chip appears or brightens

Idle behavior:

- no continuous heavy motion
- optional very subtle glow only if it does not distract from the report

### Synthetic Candidate Pool

Purpose:

Show that multiple plausible synthetic candidates are generated before the final report is chosen.

Visual elements:

- 10 candidate tokens, matching the backend pool size when available
- labels such as `C1` through `C10`
- a compact grid that fits within the existing panel

Animation:

- candidate tokens reveal one by one
- tokens can scale or rise slightly as they appear
- the stage frame highlights while the pool is being generated

Idle behavior:

- light staggered floating or breathing motion
- no large movement that changes layout dimensions

### Shuffle And Linkage Mask

Purpose:

Show that candidates are randomized and that the direct raw-result-to-output link is obscured.

Visual elements:

- existing `shuffleChamber`
- 3 to 5 representative candidate tokens inside the chamber
- sweep lines inside the chamber
- optional small label or chip for `linkage masked`

Animation:

- representative tokens move across each other inside the chamber
- sweep lines pass through the chamber during the first-run sequence
- the stage frame highlights during the shuffle phase
- if a linkage chip is shown, it appears after the token mixing starts

Idle behavior:

- low-frequency sweep or token bobbing
- avoid continuous high-speed token movement

### Protected Output

Purpose:

Show that the report receives a protected candidate, not the raw inference profile.

Visual elements:

- `Protected Output` card
- compact chips such as `summary only` and `reduced linkage`

Animation:

- mask chips appear first
- protected output card slides or fades in
- final card pulses once to mark completion

Idle behavior:

- very subtle pulse on the protected output card
- no repeated attention-grabbing flash

## Animation Timeline

The first-run animation should play once in this order:

| Time | Stage | Behavior |
| --- | --- | --- |
| 0.0s-1.2s | Raw encrypted profile | profile card highlights; summary bars glow |
| 1.2s-2.8s | Synthetic candidate pool | candidate tokens appear one by one |
| 2.8s-5.2s | Shuffle and linkage mask | chamber tokens mix; sweep lines pass through |
| 5.2s-6.6s | Masking | `summary only` and `reduced linkage` chips appear |
| 6.6s-7.4s | Protected output | final protected output card appears and pulses |
| 7.4s+ | Idle | low-intensity loop begins |

The exact durations can be adjusted during implementation, but the total first-run sequence should
stay under 8 seconds so the UI does not feel blocked.

## Privacy Pipeline Step Cards

The existing `privacyPipeline` should remain visible as the textual explanation layer.

During first-run animation:

- each pipeline step should highlight in sync with its corresponding mixer stage
- only one step should be visually dominant at a time
- the final protected output step can remain active after the sequence completes

During idle:

- the final step can stay highlighted
- other steps should remain readable but visually quieter

## Responsive Behavior

Desktop:

- keep the existing horizontal conveyor layout
- preserve the current panel proportions
- prevent token animation from changing layout dimensions

Narrow screens:

- allow the mixer to stack vertically if the existing CSS already does so or if needed to avoid
  overflow
- arrows can rotate or become short vertical separators
- stage-specific animation should still run, but token travel distance should be reduced

The design must not cause text or tokens to overlap in mobile-width layouts.

## Accessibility And Motion Preference

Respect `prefers-reduced-motion: reduce`.

When reduced motion is enabled:

- skip the long first-run sequence
- render the final pipeline state immediately
- avoid continuous idle animation
- keep the same explanatory content visible

The panel should remain understandable without animation.

## Implementation Boundaries

Expected files:

- `frontend/assets/js/app.js`
- `frontend/assets/css/styles.css`

No backend files are expected to change.

No new dependencies are expected.

No new markdown files are expected beyond this explicitly approved design document.

## Data Use

Use existing `privacy_protection` response fields:

- `enabled`
- `pool_size`
- `metrics.pool_size`
- `display_candidates`
- `selected_label`
- `summary`
- `pipeline`

Candidate token count should derive from `pool_size`, capped at 10 as the current UI already does.
If privacy data is unavailable, keep the existing unavailable/fallback behavior.

## Error And Re-Render Behavior

When `renderPrivacyProtection(privacy)` is called repeatedly:

- the previous animation state should not leak into the new render
- pending timers should not create conflicting state changes if a new analysis starts quickly
- the panel should restart the first-run sequence for the new result

If the backend returns disabled or missing privacy data:

- render the existing unavailable hint
- do not start animation timers

## Testing And Verification

Manual verification:

- run the backend on port `8082`
- run the frontend on port `8001`
- select modalities and run analysis
- confirm the shuffle panel animates through the four stages once
- confirm the panel switches to a lower-intensity idle state
- confirm no other dashboard sections move or change layout
- confirm narrow viewport layout does not overflow or overlap

Automated or code-level checks:

- existing backend unit tests should still pass because API behavior is unchanged
- frontend should not throw console errors when privacy data is present
- frontend should not throw console errors when privacy data is missing or disabled

## Acceptance Criteria

- The shuffle privacy panel communicates a complete privacy pipeline.
- Each of the four stages has a distinct matching animation.
- The first-run animation completes and then transitions to a quieter idle state.
- The change is limited to the shuffle/privacy panel.
- Existing page layout and other workflow sections remain unchanged.
- No new third-party frontend dependencies are added.
- Reduced-motion users can still understand the panel without continuous animation.

## Recommendation

Implement the CSS + small JavaScript state version.

This gives enough control for a clear first-run explanation and a restrained idle loop while staying
consistent with the current vanilla frontend and existing privacy panel structure.
