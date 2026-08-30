/**
 * FeedbackPanel Component
 * Allows users to provide feedback on predictions
 */

export function FeedbackPanel() {
  return `
    <section class="feedback-panel">
      <div class="panel-content">
        <h2>Prediction Feedback</h2>

        <div class="feedback-section">
          <p class="feedback-prompt">Was this prediction correct?</p>
          <div class="feedback-buttons">
            <button id="feedbackCorrect" class="btn btn-secondary">
              ✓ Correct
            </button>
            <button id="feedbackIncorrect" class="btn btn-secondary">
              ✗ Incorrect
            </button>
          </div>
        </div>

        <div id="feedbackMessage" class="feedback-message" style="display: none;"></div>
      </div>
    </section>
  `;
}

/**
 * Setup feedback button handlers
 */
export function setupFeedbackHandlers(onFeedback: (correct: boolean) => void) {
  const correctBtn = document.querySelector('#feedbackCorrect') as HTMLButtonElement;
  const incorrectBtn = document.querySelector('#feedbackIncorrect') as HTMLButtonElement;

  correctBtn?.addEventListener('click', () => {
    onFeedback(true);
    showFeedbackMessage('Thank you! Feedback recorded.', 'success');
  });

  incorrectBtn?.addEventListener('click', () => {
    onFeedback(false);
    showFeedbackMessage('Thank you! Feedback recorded. Trust priors will be updated.', 'info');
  });
}

/**
 * Show feedback message
 */
function showFeedbackMessage(message: string, type: 'success' | 'info' | 'error') {
  const msgEl = document.querySelector('#feedbackMessage') as HTMLDivElement;
  if (!msgEl) return;

  msgEl.textContent = message;
  msgEl.className = `feedback-message feedback-${type}`;
  msgEl.style.display = 'block';

  // Hide after 3 seconds
  setTimeout(() => {
    msgEl.style.display = 'none';
  }, 3000);
}

/**
 * Reset feedback panel
 */
export function resetFeedback() {
  const msgEl = document.querySelector('#feedbackMessage') as HTMLDivElement;
  if (msgEl) {
    msgEl.style.display = 'none';
  }
}
