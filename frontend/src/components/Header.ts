/**
 * Header Component
 * Displays system title, status, and system health indicators
 */

export function Header() {
  const now = new Date().toLocaleTimeString();

  return `
    <header class="header">
      <div class="header-content">
        <div class="header-title">
          <h1>Industrial Anomaly Intelligence</h1>
          <p class="header-subtitle">Trust-Calibrated Multimodal Monitoring</p>
        </div>

        <div class="header-status">
          <div class="status-item">
            <span class="status-indicator online"></span>
            <span class="status-label">System Online</span>
          </div>
          <div class="status-item">
            <span class="status-indicator ready"></span>
            <span class="status-label">Model Ready</span>
          </div>
          <div class="status-item">
            <span class="status-indicator ready"></span>
            <span class="status-label">API Ready</span>
          </div>
          <div class="status-time">${now}</div>
        </div>
      </div>
    </header>
  `;
}
