/**
 * PipelineVisualization Component
 * Displays the animated inference pipeline with sequential stage activation
 */

import type { BackendResponse } from '../types';

export function PipelineVisualization() {
  return `
    <section class="pipeline-section">
      <div class="pipeline-container">
        <h2>Inference Pipeline</h2>

        <div class="pipeline-diagram">
          <!-- Stage 1: Inputs -->
          <div class="pipeline-stage" id="stage-1" data-stage="1">
            <div class="stage-node">
              <div class="stage-label">Inputs</div>
              <div class="stage-icon">📥</div>
            </div>
            <div class="stage-details">
              <div class="detail-row">
                <span class="detail-label">Telemetry:</span>
                <span class="detail-value" id="input-telemetry">—</span>
              </div>
            </div>
          </div>

          <!-- Connector 1→2 -->
          <div class="pipeline-connector" id="connector-1-2">
            <svg width="40" height="60" viewBox="0 0 40 60">
              <path d="M 20 0 Q 20 30, 20 60" stroke="currentColor" stroke-width="2" fill="none" stroke-dasharray="4,4" />
            </svg>
          </div>

          <!-- Stage 2: Quality -->
          <div class="pipeline-stage" id="stage-2" data-stage="2">
            <div class="stage-node">
              <div class="stage-label">Quality</div>
              <div class="stage-icon">✓</div>
            </div>
            <div class="stage-details">
              <div class="detail-row">
                <span class="detail-label">Quality:</span>
                <span class="detail-value" id="quality-score">—</span>
              </div>
              <div class="detail-info">
                <small>Independent from prediction confidence</small>
              </div>
            </div>
          </div>

          <!-- Connector 2→3 -->
          <div class="pipeline-connector" id="connector-2-3">
            <svg width="40" height="60" viewBox="0 0 40 60">
              <path d="M 20 0 Q 20 30, 20 60" stroke="currentColor" stroke-width="2" fill="none" stroke-dasharray="4,4" />
            </svg>
          </div>

          <!-- Stage 3: Trust -->
          <div class="pipeline-stage" id="stage-3" data-stage="3">
            <div class="stage-node">
              <div class="stage-label">Trust</div>
              <div class="stage-icon">🔒</div>
            </div>
            <div class="stage-details">
              <div class="detail-row">
                <span class="detail-label">Gate Value:</span>
                <span class="detail-value" id="trust-gate">—</span>
              </div>
            </div>
          </div>

          <!-- Connector 3→4 -->
          <div class="pipeline-connector" id="connector-3-4">
            <svg width="40" height="60" viewBox="0 0 40 60">
              <path d="M 20 0 Q 20 30, 20 60" stroke="currentColor" stroke-width="2" fill="none" stroke-dasharray="4,4" />
            </svg>
          </div>

          <!-- Stage 4: Fusion -->
          <div class="pipeline-stage" id="stage-4" data-stage="4">
            <div class="stage-node">
              <div class="stage-label">Fusion</div>
              <div class="stage-icon">⚡</div>
            </div>
            <div class="stage-details">
              <div class="detail-row">
                <span class="detail-label">Fused Score:</span>
                <span class="detail-value" id="fused-score">—</span>
              </div>
            </div>
          </div>

          <!-- Connector 4→5 -->
          <div class="pipeline-connector" id="connector-4-5">
            <svg width="40" height="60" viewBox="0 0 40 60">
              <path d="M 20 0 Q 20 30, 20 60" stroke="currentColor" stroke-width="2" fill="none" stroke-dasharray="4,4" />
            </svg>
          </div>

          <!-- Stage 5: Calibration -->
          <div class="pipeline-stage" id="stage-5" data-stage="5">
            <div class="stage-node">
              <div class="stage-label">Calibration</div>
              <div class="stage-icon">📊</div>
            </div>
            <div class="stage-details">
              <div class="detail-row">
                <span class="detail-label">Raw → Calibrated:</span>
                <span class="detail-value" id="calibration-values">— → —</span>
              </div>
            </div>
          </div>

          <!-- Connector 5→6 -->
          <div class="pipeline-connector" id="connector-5-6">
            <svg width="40" height="60" viewBox="0 0 40 60">
              <path d="M 20 0 Q 20 30, 20 60" stroke="currentColor" stroke-width="2" fill="none" stroke-dasharray="4,4" />
            </svg>
          </div>

          <!-- Stage 6: Decision -->
          <div class="pipeline-stage" id="stage-6" data-stage="6">
            <div class="stage-node decision-node">
              <div class="stage-label">Decision</div>
              <div class="stage-icon">🎯</div>
            </div>
            <div class="stage-details">
              <div class="detail-row">
                <span class="detail-label">Prediction:</span>
                <span class="detail-value" id="final-prediction">—</span>
              </div>
              <div class="detail-row">
                <span class="detail-label">Confidence:</span>
                <span class="detail-value" id="final-confidence">—</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  `;
}

/**
 * Format a number value for display with animation
 */
function formatValue(value: number | string): string {
  if (typeof value === 'string') return value;
  if (value < 1) return (value * 100).toFixed(0) + '%';
  return value.toFixed(2);
}

/**
 * Animate number from one value to another
 */
function animateNumberValue(
  element: HTMLElement,
  fromValue: number,
  toValue: number,
  duration: number = 400
) {
  const startTime = performance.now();

  function updateValue(currentTime: number) {
    const elapsed = currentTime - startTime;
    const progress = Math.min(elapsed / duration, 1);

    const currentValue = fromValue + (toValue - fromValue) * progress;
    element.textContent = formatValue(currentValue);

    if (progress < 1) {
      requestAnimationFrame(updateValue);
    }
  }

  requestAnimationFrame(updateValue);
}

/**
 * Update pipeline with backend response data
 */
export function updatePipelineWithResponse(response: BackendResponse) {
  // Stage 1: Inputs
  const inputTelemetry = document.querySelector('#input-telemetry');
  if (inputTelemetry) {
    animateNumberValue(inputTelemetry as HTMLElement, 0, response.sensor_value, 300);
  }

  // Stage 2: Quality
  const qualityScore = document.querySelector('#quality-score');
  if (qualityScore) {
    const qualityEl = qualityScore as HTMLElement;
    qualityEl.textContent = '0%';
    animateNumberValue(
      qualityEl,
      0,
      response.quality_estimation * 100,
      300
    );
  }

  // Stage 3: Trust (placeholder - backend not ready)
  const trustGate = document.querySelector('#trust-gate');
  if (trustGate) {
    trustGate.textContent = '—';
  }

  // Stage 4: Fusion (placeholder - backend not ready)
  const fusedScore = document.querySelector('#fused-score');
  if (fusedScore) {
    fusedScore.textContent = '—';
  }

  // Stage 5: Calibration (placeholder - backend not ready)
  const calibrationValues = document.querySelector('#calibration-values');
  if (calibrationValues) {
    calibrationValues.textContent = '— → —';
  }

  // Stage 6: Decision
  const finalPrediction = document.querySelector('#final-prediction');
  if (finalPrediction) {
    finalPrediction.textContent = response.trend_analysis || 'Analysis complete';
  }

  const finalConfidence = document.querySelector('#final-confidence');
  if (finalConfidence) {
    const confEl = finalConfidence as HTMLElement;
    confEl.textContent = '0%';
    animateNumberValue(
      confEl,
      0,
      response.quality_estimation * 100,
      300
    );
  }
}

/**
 * Activate stages sequentially with animation
 * Each stage takes 500ms (300ms animation + 200ms wait)
 */
export async function animatePipelineStages(): Promise<void> {
  const stages = [1, 2, 3, 4, 5, 6];
  const stageDelay = 500; // milliseconds between stage activations

  for (const stage of stages) {
    const stageEl = document.querySelector(`#stage-${stage}`);
    const connectorEl =
      stage < 6 ? document.querySelector(`#connector-${stage}-${stage + 1}`) : null;

    if (stageEl) {
      // Add active class to trigger CSS animation
      stageEl.classList.add('active');
      stageEl.classList.add('animating');

      // Wait for stage animation to complete before moving to next
      await new Promise(resolve => setTimeout(resolve, stageDelay));

      stageEl.classList.remove('animating');
    }

    // Activate connector after stage
    if (connectorEl) {
      connectorEl.classList.add('active');
    }
  }
}

/**
 * Reset pipeline visualization to initial state
 */
export function resetPipeline() {
  // Reset all stages
  document.querySelectorAll('.pipeline-stage').forEach(stage => {
    stage.classList.remove('active', 'animating');
  });

  // Reset all connectors
  document.querySelectorAll('.pipeline-connector').forEach(connector => {
    connector.classList.remove('active');
  });

  // Reset all values to dash
  document.querySelectorAll('[id^="input-"], [id$="-score"], [id$="-values"], [id^="final-"], [id^="trust-"], [id^="fused-"], [id^="calibration-"]').forEach(el => {
    if (el.classList.contains('detail-value')) {
      el.textContent = '—';
    }
  });
}
