/**
 * ExplanationPanel Component
 * Displays why the system made its decision
 */

import type { BackendResponse } from '../types';

export function ExplanationPanel() {
  return `
    <section class="explanation-panel">
      <div class="panel-content">
        <h2>Decision Explanation</h2>

        <div id="explanationContent" class="explanation-content">
          <p class="placeholder">Run inference to see explanation</p>
        </div>
      </div>
    </section>
  `;
}

/**
 * Update explanation with backend response
 */
export function updateExplanation(response: BackendResponse) {
  const content = document.querySelector('#explanationContent');
  if (!content) return;

  let html = '<div class="explanation-list">';

  // Add trend analysis
  if (response.trend_analysis) {
    html += `<div class="explanation-item">
      <span class="explanation-icon">📈</span>
      <span class="explanation-text">${response.trend_analysis}</span>
    </div>`;
  }

  // Add quality explanation
  const qualityLevel =
    response.quality_estimation > 0.8
      ? 'High'
      : response.quality_estimation > 0.6
        ? 'Moderate'
        : 'Low';
  html += `<div class="explanation-item">
    <span class="explanation-icon">✓</span>
    <span class="explanation-text">Evidence quality: ${qualityLevel} (${(response.quality_estimation * 100).toFixed(0)}%)</span>
  </div>`;

  // Add RAG recommendation
  if (response.rag_recommendation) {
    html += `<div class="explanation-item recommendation">
      <span class="explanation-icon">💡</span>
      <span class="explanation-text"><strong>Recommendation:</strong> ${response.rag_recommendation}</span>
    </div>`;
  }

  html += '</div>';

  content.innerHTML = html;
}

/**
 * Clear explanation
 */
export function clearExplanation() {
  const content = document.querySelector('#explanationContent');
  if (content) {
    content.innerHTML = '<p class="placeholder">Run inference to see explanation</p>';
  }
}
