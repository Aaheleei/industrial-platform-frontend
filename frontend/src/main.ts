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
    displayErrorBanner(error);
  } finally {
    setRunButtonLoading(false);
  }
}

/**
 * Display user-friendly error message
 */
function displayErrorBanner(error: unknown) {
  const errorContainer = document.querySelector('.main-content') as HTMLElement;
  if (!errorContainer) return;

  // Remove any existing error banner
  const existingBanner = errorContainer.querySelector('.error-banner');
  if (existingBanner) existingBanner.remove();

  let title = 'Inference Failed';
  let message = 'An unknown error occurred.';

  if (error instanceof TypeError && error.message.includes('fetch')) {
    title = 'Backend Connection Failed';
    message =
      'Cannot reach the backend API at http://localhost:8000.\n\n' +
      'Solution: Make sure the backend is running.\n' +
      'Run: python backend/main.py';
  } else if (error instanceof Error) {
    if (error.message.includes('400')) {
      title = 'Invalid Input';
      message = 'The sensor value is invalid. Please enter a number.';
    } else if (error.message.includes('500')) {
      title = 'Server Error';
      message =
        'The backend encountered an error.\n' +
        'Check the backend console for details.';
    } else {
      message = error.message;
    }
  }

  const banner = document.createElement('div');
  banner.className = 'error-banner';
  banner.innerHTML = `
    <strong>⚠️ ${title}</strong>
    <div>${message}</div>
  `;

  errorContainer.insertBefore(banner, errorContainer.firstChild);

  // Auto-dismiss after 6 seconds
  setTimeout(() => {
    banner.style.animation = 'slideUp 0.3s ease-out forwards';
    setTimeout(() => banner.remove(), 300);
  }, 6000);
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
