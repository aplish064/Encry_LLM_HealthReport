# Shuffle Pipeline Animation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Animate the existing Shuffle Privacy Protection panel as a four-stage privacy pipeline that plays once and then settles into a subtle idle loop.

**Architecture:** Keep the implementation frontend-only. `frontend/assets/js/app.js` will generate richer privacy panel markup and manage the `is-playing` to `is-idle` transition; `frontend/assets/css/styles.css` will define all stage-specific motion, responsive layout, idle animations, and reduced-motion behavior.

**Tech Stack:** Vanilla JavaScript, static HTML, CSS keyframe animations, existing FastAPI response shape.

---

## File Structure

- Modify: `frontend/assets/js/app.js`
  - Replace the current `renderPrivacyProtection(privacy)` implementation with a version that renders the four-stage conveyor markup.
  - Add a module-level timer handle so repeated renders clear the prior idle-transition timer.
  - Keep fallback behavior for missing or disabled privacy data.

- Modify: `frontend/assets/css/styles.css`
  - Extend the existing privacy/shuffle style block.
  - Add stage-specific animation classes for raw profile, candidate pool, shuffle chamber, mask chips, protected output, and pipeline step highlighting.
  - Add `prefers-reduced-motion: reduce` behavior.
  - Add responsive rules so the privacy mixer stacks cleanly on narrow screens.

- Do not modify backend files.
- Do not add dependencies.
- Do not commit automatically; this repository's `AGENTS.md` explicitly says not to commit automatically.

## Task 1: Render Four-Stage Conveyor Markup And State

**Files:**
- Modify: `frontend/assets/js/app.js`

- [ ] **Step 1: Locate the existing privacy renderer**

Run:

```bash
rg -n "function renderPrivacyProtection|privacyPanel|mixerToken|shuffleChamber|protectedOutputCard" frontend/assets/js/app.js
```

Expected:

```text
frontend/assets/js/app.js:<line>:function renderPrivacyProtection(privacy) {
```

- [ ] **Step 2: Add the privacy animation timer handle**

In `frontend/assets/js/app.js`, near the top-level helpers and before `renderPrivacyProtection`, add:

```javascript
let privacyAnimationTimer = null;
```

This handle prevents older animation timers from switching a freshly rendered privacy panel into idle mode at the wrong time.

- [ ] **Step 3: Replace `renderPrivacyProtection(privacy)` with the staged renderer**

Replace the full existing `renderPrivacyProtection(privacy)` function in `frontend/assets/js/app.js` with:

```javascript
function renderPrivacyProtection(privacy) {
  const panel = $("privacyPanel");
  if (!panel) return;

  if (privacyAnimationTimer) {
    clearTimeout(privacyAnimationTimer);
    privacyAnimationTimer = null;
  }

  panel.classList.remove("is-playing", "is-idle");

  if (!privacy || !privacy.enabled) {
    panel.innerHTML = '<div class="hint">隐私保护数据暂不可用。</div>';
    return;
  }

  const defaultPipeline = [
    { label: "候选池", detail: "根据加密推理结果生成相似的合成候选。" },
    { label: "混洗", detail: "随机打乱候选顺序，切断直接对应关系。" },
    { label: "关联掩蔽", detail: "只暴露摘要候选，不暴露原始模型输出。" },
    { label: "受保护输出", detail: "从混洗候选中选择最终报告来源。" },
  ];
  const pipeline = Array.isArray(privacy.pipeline) && privacy.pipeline.length
    ? privacy.pipeline
    : defaultPipeline;

  const poolSize = Math.min(Number(privacy.pool_size || privacy.metrics?.pool_size || 10), 10);
  const selectedLabel = safeText(privacy.selected_label, "Protected Output");
  const summary = safeText(
    privacy.summary,
    "Final report selected from shuffled synthetic candidates."
  );

  const poolTokens = Array.from({ length: poolSize }, (_, index) => {
    return `<div class="mixerToken" style="--i:${index}; --slot:${((index * 7) % 10) + 1}">C${index + 1}</div>`;
  }).join("");

  const chamberTokens = Array.from({ length: Math.min(poolSize, 4) }, (_, index) => {
    const label = `C${((index * 3 + 1) % poolSize) + 1}`;
    return `<div class="shuffleToken shuffleToken${index + 1}">${label}</div>`;
  }).join("");

  const pipelineHtml = pipeline.slice(0, 4).map((stage, index) => {
    const stageClass = ["stage-raw", "stage-pool", "stage-shuffle", "stage-output"][index] || "stage-output";
    return `
      <div class="privacyStage ${stageClass}" style="--stage-index:${index}">
        <div class="privacyStageIndex">${index + 1}</div>
        <div>
          <div class="privacyStageTitle">${escHtml(stage.label)}</div>
          <div class="privacyStageDetail">${escHtml(stage.detail || "")}</div>
        </div>
      </div>
    `;
  }).join("");

  panel.innerHTML = `
    <div class="privacySummary">
      <strong>隐私混洗流水线已启动。</strong>
      ${escHtml(summary)}
    </div>
    <div class="privacyMixer" aria-label="Shuffle privacy pipeline">
      <div class="mixerColumn mixerRaw">
        <div class="mixerLabel">1. 原始加密推理摘要</div>
        <div class="rawResultCard rawProfileCard">
          <strong>Raw encrypted profile</strong>
          <div class="rawProfileBars" aria-hidden="true">
            <span style="--w:88%"></span>
            <span style="--w:67%"></span>
            <span style="--w:74%"></span>
          </div>
          <span class="profileLockChip">locked inference summary</span>
        </div>
      </div>
      <div class="mixerArrow arrowToPool" aria-hidden="true">→</div>
      <div class="mixerColumn mixerPool">
        <div class="mixerLabel">2. 合成候选池</div>
        <div class="mixerTokenGrid">${poolTokens}</div>
      </div>
      <div class="mixerArrow arrowToShuffle" aria-hidden="true">→</div>
      <div class="mixerColumn mixerShuffle">
        <div class="mixerLabel">3. 混洗与关联掩蔽</div>
        <div class="shuffleChamber">
          ${chamberTokens}
          <div class="shuffleLine"></div>
          <div class="shuffleLine"></div>
          <div class="shuffleLine"></div>
        </div>
        <div class="maskChipRow">
          <span class="maskChip">summary only</span>
          <span class="maskChip">reduced linkage</span>
        </div>
      </div>
      <div class="mixerArrow arrowToOutput" aria-hidden="true">→</div>
      <div class="mixerColumn mixerProtected">
        <div class="mixerLabel">4. 受保护输出</div>
        <div class="protectedOutputCard">${escHtml(selectedLabel)}</div>
      </div>
    </div>
    <div class="privacyPipeline">${pipelineHtml}</div>
  `;

  window.requestAnimationFrame(() => {
    panel.classList.add("is-playing");
  });

  privacyAnimationTimer = window.setTimeout(() => {
    if (!panel.isConnected) return;
    panel.classList.remove("is-playing");
    panel.classList.add("is-idle");
    privacyAnimationTimer = null;
  }, 7600);
}
```

- [ ] **Step 4: Run a syntax check by loading the file in Node**

Run:

```bash
node --check frontend/assets/js/app.js
```

Expected:

```text
```

`node --check` prints no output and exits with code `0` when the JavaScript is syntactically valid.

- [ ] **Step 5: Verify the old fallback text still exists**

Run:

```bash
rg -n "隐私保护数据暂不可用|privacyAnimationTimer|is-playing|is-idle|rawProfileCard|shuffleToken" frontend/assets/js/app.js
```

Expected:

```text
frontend/assets/js/app.js:<line>:let privacyAnimationTimer = null;
frontend/assets/js/app.js:<line>:panel.classList.remove("is-playing", "is-idle");
frontend/assets/js/app.js:<line>:panel.innerHTML = '<div class="hint">隐私保护数据暂不可用。</div>';
frontend/assets/js/app.js:<line>:<div class="rawResultCard rawProfileCard">
frontend/assets/js/app.js:<line>:return `<div class="shuffleToken shuffleToken${index + 1}">${label}</div>`;
```

## Task 2: Add Stage-Specific Privacy Animation CSS

**Files:**
- Modify: `frontend/assets/css/styles.css`

- [ ] **Step 1: Locate the existing privacy CSS block**

Run:

```bash
rg -n "\\.privacyMixer|\\.mixerToken|\\.shuffleChamber|\\.privacyStage|@keyframes tokenShuffle|@keyframes shuffleSweep|@keyframes protectedPulse" frontend/assets/css/styles.css
```

Expected:

```text
frontend/assets/css/styles.css:<line>:.privacyMixer {
frontend/assets/css/styles.css:<line>:.mixerToken {
frontend/assets/css/styles.css:<line>:.shuffleChamber {
frontend/assets/css/styles.css:<line>:.privacyStage {
frontend/assets/css/styles.css:<line>:@keyframes tokenShuffle {
frontend/assets/css/styles.css:<line>:@keyframes shuffleSweep {
frontend/assets/css/styles.css:<line>:@keyframes protectedPulse {
```

- [ ] **Step 2: Replace the privacy mixer animation CSS block**

In `frontend/assets/css/styles.css`, replace the existing privacy/shuffle block from the second `.privacyPanel {` near the report CSS through `@keyframes protectedPulse` with this CSS:

```css
.privacyPanel {
  display: grid;
  gap: 10px;
  margin-top: 0;
  color: var(--muted);
  font-size: 13px;
}

.privacyCandidateGrid {
  display: grid;
  grid-template-columns: 1fr;
  gap: 8px;
}

.privacyMixer {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto minmax(0, 1.12fr) auto minmax(0, 1fr) auto minmax(0, 1fr);
  align-items: stretch;
  gap: 8px;
  padding: 14px;
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  background: linear-gradient(180deg, #ffffff, #f8fbff);
}

.mixerColumn {
  position: relative;
  min-width: 0;
  display: grid;
  gap: 7px;
  align-content: start;
  padding: 9px;
  border: 1px solid transparent;
  border-radius: var(--radius-md);
}

.privacyPanel.is-playing .mixerColumn::before,
.privacyPanel.is-playing .privacyStage::before {
  content: "";
  position: absolute;
  inset: 0;
  border: 2px solid transparent;
  border-radius: inherit;
  pointer-events: none;
  animation: privacyStageFrame 7600ms ease-out 1;
}

.privacyPanel.is-playing .mixerRaw::before,
.privacyPanel.is-playing .privacyStage.stage-raw::before {
  animation-delay: 0ms;
}

.privacyPanel.is-playing .mixerPool::before,
.privacyPanel.is-playing .privacyStage.stage-pool::before {
  animation-delay: 1200ms;
}

.privacyPanel.is-playing .mixerShuffle::before,
.privacyPanel.is-playing .privacyStage.stage-shuffle::before {
  animation-delay: 2800ms;
}

.privacyPanel.is-playing .mixerProtected::before,
.privacyPanel.is-playing .privacyStage.stage-output::before {
  animation-delay: 6200ms;
}

.mixerLabel {
  color: var(--muted);
  font-size: 11px;
  font-weight: 900;
}

.rawResultCard,
.protectedOutputCard {
  min-height: 58px;
  padding: 9px;
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  background: #ffffff;
  font-size: 11px;
  line-height: 1.35;
}

.rawResultCard strong,
.rawResultCard span {
  display: block;
}

.rawResultCard span {
  margin-top: 5px;
  color: var(--muted);
}

.rawProfileCard {
  display: grid;
  gap: 7px;
}

.rawProfileBars {
  display: grid;
  gap: 5px;
}

.rawProfileBars span {
  display: block;
  width: var(--w);
  height: 7px;
  border-radius: 999px;
  background: #d8e1ef;
}

.privacyPanel.is-playing .rawProfileBars span {
  animation: rawProfileGlow 1200ms ease-out 1;
}

.profileLockChip {
  display: inline-flex;
  width: fit-content;
  padding: 4px 7px;
  border-radius: 999px;
  background: #eef2ff;
  color: #3730a3;
  font-size: 10px;
  font-weight: 900;
}

.mixerArrow {
  position: relative;
  display: flex;
  align-items: center;
  color: var(--muted);
  font-weight: 900;
}

.privacyPanel.is-playing .mixerArrow::after {
  content: "";
  position: absolute;
  left: 50%;
  top: calc(50% + 15px);
  width: 24px;
  height: 2px;
  border-radius: 999px;
  transform: translateX(-50%);
  background: #cbd5e1;
  animation: privacyArrowPulse 7600ms ease-out 1;
}

.privacyPanel.is-playing .arrowToPool::after { animation-delay: 900ms; }
.privacyPanel.is-playing .arrowToShuffle::after { animation-delay: 2600ms; }
.privacyPanel.is-playing .arrowToOutput::after { animation-delay: 5400ms; }

.mixerTokenGrid {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 4px;
}

.mixerToken {
  min-height: 30px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 6px;
  background: #eaf2ff;
  color: #1d4ed8;
  font-size: 10px;
  font-weight: 900;
}

.privacyPanel.is-playing .mixerToken {
  opacity: 0;
  animation: tokenReveal 460ms ease forwards;
  animation-delay: calc(1200ms + var(--i) * 90ms);
}

.privacyPanel.is-idle .mixerToken {
  animation: tokenIdleFloat 2600ms ease-in-out infinite;
  animation-delay: calc(var(--i) * 90ms);
}

.shuffleChamber {
  position: relative;
  min-height: 72px;
  overflow: hidden;
  border: 1px dashed rgba(37, 99, 235, 0.35);
  border-radius: var(--radius-md);
  background: rgba(37, 99, 235, 0.06);
}

.shuffleToken {
  position: absolute;
  z-index: 2;
  width: 28px;
  height: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 7px;
  background: #2563eb;
  color: #ffffff;
  font-size: 9px;
  font-weight: 900;
}

.shuffleToken1 { left: 12%; top: 14px; --mix-x: 66px; --mix-y: 30px; }
.shuffleToken2 { left: 38%; top: 43px; --mix-x: -30px; --mix-y: -28px; }
.shuffleToken3 { left: 64%; top: 16px; --mix-x: -52px; --mix-y: 32px; }
.shuffleToken4 { left: 74%; top: 45px; --mix-x: -64px; --mix-y: -20px; }

.privacyPanel.is-playing .shuffleToken {
  opacity: 0;
  animation: shuffleTokenMix 2500ms ease-in-out forwards;
  animation-delay: 2800ms;
}

.privacyPanel.is-idle .shuffleToken {
  animation: shuffleTokenIdle 3400ms ease-in-out infinite;
}

.shuffleLine {
  position: absolute;
  left: -35%;
  width: 60%;
  height: 2px;
  border-radius: 999px;
  background: linear-gradient(90deg, transparent, rgba(37, 99, 235, 0.8), transparent);
}

.privacyPanel.is-playing .shuffleLine {
  animation: shuffleSweep 1200ms ease-in-out 3;
}

.privacyPanel.is-idle .shuffleLine {
  animation: shuffleSweep 2600ms ease-in-out infinite;
}

.shuffleLine:nth-of-type(1) { top: 18px; animation-delay: 3100ms; }
.shuffleLine:nth-of-type(2) { top: 34px; animation-delay: 3350ms; }
.shuffleLine:nth-of-type(3) { top: 50px; animation-delay: 3600ms; }

.maskChipRow {
  display: flex;
  flex-wrap: wrap;
  gap: 5px;
}

.maskChip {
  padding: 4px 7px;
  border-radius: 999px;
  background: #f1f5f9;
  color: #64748b;
  font-size: 10px;
  font-weight: 900;
}

.privacyPanel.is-playing .maskChip {
  opacity: 0;
  animation: tokenReveal 420ms ease forwards;
  animation-delay: 5200ms;
}

.protectedOutputCard {
  display: flex;
  align-items: center;
  justify-content: center;
  border-color: rgba(31, 157, 85, 0.35);
  background: rgba(31, 157, 85, 0.08);
  color: #15803d;
  font-weight: 900;
}

.privacyPanel.is-playing .protectedOutputCard {
  opacity: 0;
  animation: protectedArrive 760ms ease forwards, protectedPulse 1200ms ease-in-out 1;
  animation-delay: 6400ms, 6900ms;
}

.privacyPanel.is-idle .protectedOutputCard {
  animation: protectedPulse 2300ms ease-in-out infinite;
}

.privacyPipeline {
  display: grid;
  gap: 8px;
}

.privacyStage {
  position: relative;
  display: grid;
  grid-template-columns: 26px minmax(0, 1fr);
  gap: 8px;
  padding: 12px;
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  background: #ffffff;
}

.privacyPanel.is-idle .privacyStage.stage-output {
  border-color: rgba(31, 157, 85, 0.35);
  background: rgba(31, 157, 85, 0.08);
}

.privacyStageIndex {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  border-radius: 999px;
  background: #eaf0f8;
  color: var(--muted);
  font-size: 11px;
  font-weight: 900;
}

.privacyPanel.is-idle .privacyStage.stage-output .privacyStageIndex {
  background: #15803d;
  color: #ffffff;
}

.privacyStageTitle {
  font-size: 13px;
  font-weight: 900;
  color: var(--text);
  line-height: 1.25;
}

.privacyStageDetail {
  margin-top: 3px;
  font-size: 12px;
  line-height: 1.35;
  color: var(--muted);
}

@keyframes privacyStageFrame {
  0%, 12%, 100% { border-color: transparent; }
  4%, 9% { border-color: rgba(37, 99, 235, 0.65); }
}

@keyframes rawProfileGlow {
  0% { background: #d8e1ef; }
  48% { background: #6366f1; }
  100% { background: #d8e1ef; }
}

@keyframes privacyArrowPulse {
  0%, 9%, 100% { background: #cbd5e1; }
  3%, 6% { background: #2563eb; }
}

@keyframes tokenReveal {
  from { opacity: 0; transform: translateY(8px) scale(0.94); }
  to { opacity: 1; transform: translateY(0) scale(1); }
}

@keyframes tokenIdleFloat {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(-2px); }
}

@keyframes shuffleTokenMix {
  0% { opacity: 0; transform: translate(0, 8px) rotate(0deg); }
  12% { opacity: 1; }
  45% { transform: translate(var(--mix-x), var(--mix-y)) rotate(30deg); }
  76% { transform: translate(calc(var(--mix-x) * -0.35), calc(var(--mix-y) * 0.5)) rotate(-20deg); }
  100% { opacity: 1; transform: translate(0, 0) rotate(0deg); }
}

@keyframes shuffleTokenIdle {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(-3px); }
}

@keyframes shuffleSweep {
  from { transform: translateX(0); opacity: 0.2; }
  45% { opacity: 1; }
  to { transform: translateX(230%); opacity: 0.2; }
}

@keyframes protectedArrive {
  from { opacity: 0; transform: translateX(-8px) scale(0.96); }
  to { opacity: 1; transform: translateX(0) scale(1); }
}

@keyframes protectedPulse {
  0%, 100% { box-shadow: 0 0 0 0 rgba(31, 157, 85, 0.14); }
  50% { box-shadow: 0 0 0 5px rgba(31, 157, 85, 0.07); }
}
```

- [ ] **Step 3: Add responsive and reduced-motion rules after the keyframes**

Still in `frontend/assets/css/styles.css`, add this CSS immediately after the new `@keyframes protectedPulse` block:

```css
@media (max-width: 980px) {
  .privacyMixer {
    grid-template-columns: 1fr;
  }

  .mixerArrow {
    min-height: 18px;
    justify-content: center;
  }

  .privacyPanel.is-playing .mixerArrow::after {
    top: 50%;
    transform: translateX(-50%) rotate(90deg);
  }

  .shuffleToken1 { --mix-x: 38px; --mix-y: 24px; }
  .shuffleToken2 { --mix-x: -24px; --mix-y: -22px; }
  .shuffleToken3 { --mix-x: -36px; --mix-y: 24px; }
  .shuffleToken4 { --mix-x: -42px; --mix-y: -18px; }
}

@media (prefers-reduced-motion: reduce) {
  .privacyPanel.is-playing .mixerColumn::before,
  .privacyPanel.is-playing .privacyStage::before,
  .privacyPanel.is-playing .rawProfileBars span,
  .privacyPanel.is-playing .mixerArrow::after,
  .privacyPanel.is-playing .mixerToken,
  .privacyPanel.is-idle .mixerToken,
  .privacyPanel.is-playing .shuffleToken,
  .privacyPanel.is-idle .shuffleToken,
  .privacyPanel.is-playing .shuffleLine,
  .privacyPanel.is-idle .shuffleLine,
  .privacyPanel.is-playing .maskChip,
  .privacyPanel.is-playing .protectedOutputCard,
  .privacyPanel.is-idle .protectedOutputCard {
    animation: none !important;
    opacity: 1 !important;
    transform: none !important;
  }
}
```

- [ ] **Step 4: Check for duplicate old keyframes**

Run:

```bash
rg -n "@keyframes tokenShuffle|@keyframes linkageReduce|@keyframes privacyStageFrame|@keyframes shuffleTokenMix" frontend/assets/css/styles.css
```

Expected:

```text
frontend/assets/css/styles.css:<line>:@keyframes privacyStageFrame {
frontend/assets/css/styles.css:<line>:@keyframes shuffleTokenMix {
```

There should be no remaining `@keyframes tokenShuffle` or `@keyframes linkageReduce` if the old block was fully replaced.

- [ ] **Step 5: Verify the CSS selectors exist**

Run:

```bash
rg -n "rawProfileCard|rawProfileBars|profileLockChip|shuffleToken|maskChipRow|maskChip|is-playing|is-idle|prefers-reduced-motion" frontend/assets/css/styles.css
```

Expected:

```text
frontend/assets/css/styles.css:<line>:.rawProfileCard {
frontend/assets/css/styles.css:<line>:.rawProfileBars {
frontend/assets/css/styles.css:<line>:.profileLockChip {
frontend/assets/css/styles.css:<line>:.privacyPanel.is-playing .shuffleToken {
frontend/assets/css/styles.css:<line>:.maskChipRow {
frontend/assets/css/styles.css:<line>:.maskChip {
frontend/assets/css/styles.css:<line>:@media (prefers-reduced-motion: reduce) {
```

## Task 3: Verify Behavior In The Existing App

**Files:**
- No source edits expected unless verification exposes a defect in Task 1 or Task 2.

- [ ] **Step 1: Run backend unit tests**

Run:

```bash
venv/bin/python -m unittest discover -s backend/tests
```

Expected:

```text
Ran 8 tests

OK
```

Matplotlib warnings about `tight_layout` are acceptable if the tests pass.

- [ ] **Step 2: Check port availability**

Run:

```bash
ss -ltnp | rg ":8082|:8001" || true
```

Expected if ports are free:

```text
```

If either port is already in use, choose the next allowed backend port from `8083` or `8084`, and update `frontend/assets/js/app.js` `API_BASE` only if the backend port changes.

- [ ] **Step 3: Start backend on the approved port**

Run:

```bash
cd backend && ../venv/bin/python -m uvicorn app:app --host 127.0.0.1 --port 8082
```

Expected:

```text
Uvicorn running on http://127.0.0.1:8082
```

Keep this process running until frontend verification is complete.

- [ ] **Step 4: Start frontend on the approved port**

Run in a second shell:

```bash
cd frontend && python -m http.server 8001
```

Expected:

```text
Serving HTTP on 0.0.0.0 port 8001
```

- [ ] **Step 5: Browser smoke test**

Open:

```text
http://127.0.0.1:8001
```

Expected manual observations:

- modality cards load
- selecting any modality enables `Run Analysis`
- clicking `Run Analysis` advances to the model stage and then privacy stage
- `Shuffle Privacy Protection` shows the four-column conveyor
- the first-run sequence plays through raw profile, pool, shuffle/mask, and protected output
- after roughly 8 seconds, motion becomes lower intensity
- the report still renders after the privacy stage
- model cluster and report layout remain unchanged

- [ ] **Step 6: Console smoke test**

In the browser console, confirm:

```text
no uncaught ReferenceError
no uncaught TypeError
```

Network requests to `/api/dispatch`, `/api/privacy_shuffle`, and `/api/report` should return HTTP `200`.

- [ ] **Step 7: Narrow viewport check**

Resize the browser to a narrow width around `390px`.

Expected manual observations:

- privacy mixer stacks vertically or remains readable without horizontal overflow
- tokens stay inside their cards
- text does not overlap adjacent content
- arrows do not cover labels or cards

- [ ] **Step 8: Reduced-motion check**

Temporarily emulate reduced motion in browser devtools, or add the CSS media override in devtools:

```css
* {
  animation-duration: 0.001ms !important;
  animation-iteration-count: 1 !important;
}
```

Expected manual observations:

- privacy panel still shows all four stages
- candidate tokens, mask chips, and protected output are visible
- panel remains understandable without motion

- [ ] **Step 9: Stop local servers**

Stop the backend and frontend processes with `Ctrl+C`.

Expected:

```text
backend process exited
frontend process exited
```

## Task 4: Final Review

**Files:**
- Review: `frontend/assets/js/app.js`
- Review: `frontend/assets/css/styles.css`
- Review: `docs/superpowers/specs/2026-05-03-shuffle-pipeline-animation-design.md`

- [ ] **Step 1: Confirm source diff is limited to approved frontend files**

Run:

```bash
git diff -- frontend/assets/js/app.js frontend/assets/css/styles.css
```

Expected:

```text
diff --git a/frontend/assets/js/app.js b/frontend/assets/js/app.js
diff --git a/frontend/assets/css/styles.css b/frontend/assets/css/styles.css
```

The diff should show only privacy renderer and privacy CSS changes.

- [ ] **Step 2: Confirm no backend API changes**

Run:

```bash
git diff -- backend
```

Expected:

```text
```

No backend diff should appear.

- [ ] **Step 3: Confirm implementation matches the approved spec**

Run:

```bash
rg -n "Raw encrypted profile|合成候选池|混洗与关联掩蔽|受保护输出|prefers-reduced-motion|privacyAnimationTimer" frontend/assets/js/app.js frontend/assets/css/styles.css
```

Expected:

```text
frontend/assets/js/app.js:<line>:let privacyAnimationTimer = null;
frontend/assets/js/app.js:<line>:Raw encrypted profile
frontend/assets/js/app.js:<line>:2. 合成候选池
frontend/assets/js/app.js:<line>:3. 混洗与关联掩蔽
frontend/assets/js/app.js:<line>:4. 受保护输出
frontend/assets/css/styles.css:<line>:@media (prefers-reduced-motion: reduce) {
```

- [ ] **Step 4: Prepare final implementation summary**

Use this summary shape:

```text
Implemented the shuffle privacy animation inside the existing privacy panel only. The panel now renders a four-stage conveyor for raw encrypted profile, synthetic candidate pool, shuffle/linkage mask, and protected output. The first render plays a staged sequence, then switches to a quieter idle state. Reduced-motion and narrow viewport behavior are covered.

Verified with:
- node --check frontend/assets/js/app.js
- venv/bin/python -m unittest discover -s backend/tests
- manual frontend/backend smoke test on 8082/8001
```

If any verification command could not be run, state that explicitly in the final implementation summary.

## Self-Review

Spec coverage:

- Linear conveyor pipeline: covered in Task 1 and Task 2.
- Animation stays inside shuffle panel: covered by file structure and Task 4 diff checks.
- Each stage has matching animation: covered by raw profile, pool, shuffle/mask, and protected output CSS in Task 2.
- First-run sequence then idle loop: covered by `privacyAnimationTimer`, `is-playing`, and `is-idle` in Task 1.
- Reduced motion: covered in Task 2.
- Responsive behavior: covered in Task 2 and Task 3.
- No backend/API changes: covered in Task 4.

Placeholder scan:

- This plan intentionally contains no unresolved placeholder markers or unspecified implementation steps.

Project constraints:

- The plan does not require automatic commits.
- The plan does not add dependencies.
- The plan does not require backend changes.
