/**
 * Industrial Anomaly Intelligence Dashboard
 * Main application entry point
 */

import './style.css';
import {
  Header,
  InputPanel,
  PipelineVisualization,
  ExplanationPanel,
  FeedbackPanel,
  getSensorValue,
  setRunButtonLoading,
  updatePipelineWithResponse,
  animatePipelineStages,
  resetPipeline,
  updateExplanation,
  clearExplanation,
  setupFeedbackHandlers,
  resetFeedback,
} from './components';
import { predictAnomaly } from './api/client';
import type { BackendResponse } from './types';

/**
 * Initialize the application
 */
function initializeApp() {
  const app = document.querySelector('#app') as HTMLDivElement;
  if (!app) {
    console.error('App container not found');
    return;
  }

  // Build the dashboard layout
  app.innerHTML = `
    <div class="dashboard-container">
      ${Header()}

      <div class="main-content">
        ${InputPanel()}
        ${PipelineVisualization()}
        ${ExplanationPanel()}
        ${FeedbackPanel()}
      </div>
    </div>
  `;

  // Setup event handlers
  setupEventHandlers();
}

/**
 * Setup all event handlers
 */
function setupEventHandlers() {
  const runBtn = document.querySelector('#runInferenceBtn') as HTMLButtonElement;

  runBtn?.addEventListener('click', handleRunInference);

  // Setup feedback handlers
  setupFeedbackHandlers((correct: boolean) => {
    console.log('Feedback received:', correct ? 'Correct' : 'Incorrect');
    // TODO: Send feedback to backend when API supports it
  });
}

/**
 * Handle run inference button click
 */
async function handleRunInference() {
  const sensorValue = getSensorValue();

  if (isNaN(sensorValue)) {
    alert('Please enter a valid sensor value');
    return;
  }

  // Reset UI
  resetPipeline();
  clearExplanation();
  resetFeedback();

  // Set loading state
  setRunButtonLoading(true);

  try {
    // Call backend API
    const response = await predictAnomaly(sensorValue);

    // Update pipeline visualization with response data
    updatePipelineWithResponse(response);

    // Animate stages sequentially (500ms per stage)
    await animatePipelineStages();

    // Update explanation with backend insights
    updateExplanation(response);
  } catch (error) {
    console.error('Error during inference:', error);
    const errorMsg =
      error instanceof Error ? error.message : 'Unknown error occurred';
    alert(`Failed to run inference: ${errorMsg}\n\nMake sure the backend is running on port 8000.`);
  } finally {
    setRunButtonLoading(false);
  }
}

/**
 * Initialize app when DOM is ready
 */
document.addEventListener('DOMContentLoaded', initializeApp);

// Also try immediate initialization for fast loads
if (document.readyState === 'loading') {
  // DOM still loading
} else {
  // DOM already loaded
  initializeApp();
}
