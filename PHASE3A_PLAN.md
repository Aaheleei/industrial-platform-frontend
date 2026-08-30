# Phase 3a: Visual Polish - Implementation Plan

**Status:** IN PROGRESS 🟡  
**Started:** 2026-08-30 09:22 UTC  
**Target:** Complete by end of today

---

## Overview

Phase 3a focuses on **visual refinement, accessibility, and edge case handling** without needing new data. Uses current backend with synthetic responses.

**Deliverables:**
1. ✅ Animation easing curves (smooth, professional)
2. ✅ Dark mode styling (test on multiple browsers)
3. ✅ Loading skeleton states (visual feedback)
4. ✅ Responsive testing (mobile 320px → desktop 2560px)
5. ✅ Accessibility baseline (ARIA, keyboard nav)
6. ✅ Error state UI (network, validation)
7. ✅ Edge case handling (empty modalities, degraded quality)

---

## Task Breakdown

### Task 1: Animation Easing Refinement
**Goal:** Make animations feel professional, not robotic

**Current state:**
```css
@keyframes stageActivate {
  from {
    opacity: 0;
    transform: translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}
```

**Improvements needed:**
- Add `ease-out` timing function (faster start, slower end)
- Fine-tune duration (maybe 400ms instead of 300ms)
- Stagger connector animations slightly behind stages
- Add hover states for interactive elements

**Files to update:**
- `frontend/src/styles/components.css` — Keyframes section

**Estimated time:** 30 minutes

---

### Task 2: Dark Mode Support
**Goal:** Test and refine dark mode appearance

**Current state:**
- Dark mode CSS already in place
- Uses `@media (prefers-color-scheme: dark)`
- Theme variables defined (`--bg`, `--text`, `--border`, etc.)

**Testing needed:**
- [ ] Open DevTools → Rendering tab → emulate `prefers-color-scheme: dark`
- [ ] Check contrast ratios (should be ≥4.5:1 for text)
- [ ] Verify all colors readable (especially pipeline stages)
- [ ] Test on Safari, Chrome, Firefox

**Files to check:**
- `frontend/src/style.css` — Global styles
- `frontend/src/styles/components.css` — Component colors

**Estimated time:** 45 minutes

---

### Task 3: Loading Skeleton States
**Goal:** Show visual feedback while backend responds

**Current state:**
- Button shows "Loading..." text
- No visual skeleton of pipeline

**Improvements:**
- Add skeleton loaders for pipeline stages
- Pulse animation for skeleton (subtle, not distracting)
- Skeleton disappears → real data fades in
- Feels faster to user

**Implementation:**
```html
<!-- Skeleton stage (shown while loading) -->
<div class="pipeline-stage skeleton">
  <div class="skeleton-node"></div>
  <div class="skeleton-details">
    <div class="skeleton-line short"></div>
    <div class="skeleton-line"></div>
  </div>
</div>
```

```css
@keyframes skeleton-pulse {
  0%, 100% { opacity: 0.6; }
  50% { opacity: 1; }
}

.skeleton {
  animation: skeleton-pulse 1.5s ease-in-out infinite;
}
```

**Files to update:**
- `frontend/src/components/PipelineVisualization.ts` — Add skeleton HTML
- `frontend/src/styles/components.css` — Add skeleton keyframes

**Estimated time:** 1 hour

---

### Task 4: Responsive Testing
**Goal:** Verify layout works across all device sizes

**Breakpoints to test:**
```css
/* Mobile (320px - 640px) */
@media (max-width: 768px) { }

/* Tablet (641px - 1024px) */
@media (max-width: 1024px) { }

/* Desktop (1025px - 1440px) */
@media (max-width: 1440px) { }

/* Large Desktop (1441px+) */
/* Default styles */
```

**Manual testing checklist:**
- [ ] 320px (iPhone SE) — single column, readable
- [ ] 480px (iPhone 12) — still single column
- [ ] 768px (iPad) — maybe 2 columns?
- [ ] 1024px (iPad Pro) — 2-3 columns
- [ ] 1440px (laptop) — full 3 columns
- [ ] 2560px (4K monitor) — still readable, not stretched

**Tools to use:**
- DevTools device emulation
- Real devices if available
- BrowserStack for multiple browsers

**Files to verify:**
- `frontend/src/styles/components.css` — Media queries

**Estimated time:** 1.5 hours

---

### Task 5: Accessibility Baseline
**Goal:** Make dashboard usable without mouse

**ARIA Labels to add:**
```html
<!-- Pipeline stages -->
<div class="pipeline-stage" 
     role="presentation" 
     aria-label="Stage 1: Inputs">
  
<!-- Input field -->
<input 
  type="number"
  id="sensorInput"
  aria-label="Sensor telemetry value"
  aria-required="true"
  aria-describedby="sensor-help"
/>

<!-- Button -->
<button 
  id="runInferenceBtn"
  aria-label="Run anomaly inference"
  aria-busy="false"
>
  Run Inference
</button>

<!-- Explanation panel -->
<section 
  role="region" 
  aria-label="Inference explanation"
>
  ...
</section>
```

**Keyboard navigation:**
- Tab through: Sensor input → Run button → Feedback buttons
- Enter to submit form
- Escape to cancel feedback

**Screen reader testing:**
- Use NVDA (Windows) or VoiceOver (Mac)
- Read through: Header → Input → Pipeline → Explanation
- Verify announce pipeline stage completion

**Files to update:**
- `frontend/src/components/InputPanel.ts` — Add ARIA to inputs
- `frontend/src/components/PipelineVisualization.ts` — Add ARIA to stages
- `frontend/src/components/ExplanationPanel.ts` — Add role region
- `frontend/src/components/FeedbackPanel.ts` — Add ARIA to buttons

**Estimated time:** 1 hour

---

### Task 6: Error State UI
**Goal:** Handle edge cases gracefully

**Scenarios to test:**
1. Backend unreachable (connection refused)
2. Invalid sensor input (non-numeric, NaN)
3. Backend returns error (500 status)
4. Network timeout (slow response)
5. Empty response from backend

**Error messages to improve:**
```
Current: "Failed to run inference: Error..."
Better:  "⚠️ Backend Connection Failed
         Make sure http://localhost:8000 is running.
         Tip: Run 'python backend/main.py' in another terminal."
```

**Visual improvements:**
- Show error in red banner (not just alert())
- Display for 5 seconds then auto-dismiss
- Option to retry without re-entering data
- Log full error to console for debugging

**Files to update:**
- `frontend/src/main.ts` — Enhanced error handling
- `frontend/src/styles/components.css` — Error banner styling

**Estimated time:** 45 minutes

---

### Task 7: Edge Case Handling
**Goal:** Test boundary conditions

**Edge cases:**
1. **Quality = 0** — Show "0%" without breaking
2. **Quality = 1** — Show "100%" correctly
3. **Very large sensor value** (1000+) — Format without overflow
4. **Very small sensor value** (0.001) — Display precision
5. **All stages missing data** — Show "—" consistently
6. **Contradictory predictions** — Handle disagreement

**Test script:**
```bash
# Test with edge values
for val in 0 0.001 1 999 1000; do
  curl -X POST http://localhost:8000/predict \
    -H "Content-Type: application/json" \
    -d "{\"value\": $val}"
done
```

**Verification:**
- [ ] All values display without console errors
- [ ] Layout doesn't break with edge values
- [ ] Number animations handle extremes smoothly
- [ ] Explanation text makes sense for all inputs

**Files to check:**
- `frontend/src/components/PipelineVisualization.ts` — Value formatting
- `frontend/src/components/ExplanationPanel.ts` — Text generation

**Estimated time:** 1 hour

---

## Implementation Order

1. **Animation Easing** (30 min) — Quick win, immediate visual improvement
2. **Dark Mode** (45 min) — Testing, no major changes needed
3. **Loading Skeletons** (1 hour) — Mid-complexity, good UX
4. **Accessibility** (1 hour) — Parallel work, important for usability
5. **Error Handling** (45 min) — Edge case improvements
6. **Responsive Testing** (1.5 hours) — Final verification across devices
7. **Edge Cases** (1 hour) — Boundary testing

**Total estimated time:** ~6.5 hours

---

## Quality Checklist - Phase 3a

- [ ] Animation easing looks professional
- [ ] Dark mode tested on 3+ browsers
- [ ] Loading skeletons show during API call
- [ ] Layout works on 320px, 768px, 1440px, 2560px
- [ ] Keyboard navigation works (Tab, Enter, Escape)
- [ ] ARIA labels present on all interactive elements
- [ ] Screen reader announces pipeline stages
- [ ] Error messages actionable and clear
- [ ] Edge values (0, 1, 999) handled gracefully
- [ ] No console errors or warnings
- [ ] All animations smooth (60fps)
- [ ] Color contrast ≥4.5:1 for text
- [ ] TypeScript compiles clean
- [ ] E2E tests still pass (7/7)

---

## After Phase 3a: ML Core Integration (Phase 3b)

Once Phase 3a is complete:

1. **Update backend/main.py** to call `ml_core.run_inference()`
2. **Use synthetic data generators** from ml_core/
3. **Test multimodal response:**
   - Stages 3-5 should populate
   - Quality varies based on synthetic noise
   - Weights show modality balance
4. **Verify pipeline displays all 6 stages**
5. **Run degradation scenarios:**
   - Clean data → all modalities visible
   - Telemetry noise → lower weight
   - Missing modality → renormalized weights

---

## Success Criteria

**Phase 3a complete when:**
- ✅ Visual polish done (animations, dark mode, skeletons)
- ✅ Accessibility baseline met (ARIA, keyboard nav)
- ✅ Error handling improved
- ✅ Responsive across all devices
- ✅ Edge cases handled gracefully
- ✅ All tests passing (7/7 + new edge case tests)
- ✅ No console errors or warnings
- ✅ Ready for Phase 3b (ML core integration)

---

## Notes

- **No new data needed** — Uses current backend
- **No backend changes** — Only frontend polish
- **Can work in parallel** — Start multiple tasks at once
- **Use real devices** — Emulation is good, real testing is better
- **Don't over-animate** — Professional = restrained, not flashy

---

**Ready to start?**

Next step: Begin with Task 1 (Animation Easing) while you work on Tasks 2-3 in parallel.
