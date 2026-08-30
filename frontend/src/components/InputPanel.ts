/**
 * InputPanel Component
 * Handles user inputs for inference: asset selection and telemetry values
 */

export function InputPanel() {
  return `
    <section class="input-panel" role="region" aria-label="Inference input controls">
      <div class="panel-content">
        <h2>Inference Input</h2>

        <div class="input-group">
          <label for="assetId">Asset</label>
          <select
            id="assetId"
            class="input-field"
            aria-label="Select industrial asset for analysis"
            aria-describedby="asset-help"
          >
            <option value="motor-07">Motor-07</option>
            <option value="motor-08">Motor-08</option>
            <option value="motor-09">Motor-09</option>
          </select>
          <small id="asset-help" style="opacity: 0.7; font-size: 12px;">Choose the equipment to analyze</small>
        </div>

        <div class="modality-section">
          <h3>Telemetry</h3>
          <div class="input-group">
            <label for="sensorValue">Sensor Value (°C)</label>
            <input
              type="number"
              id="sensorValue"
              class="input-field"
              placeholder="Enter sensor value..."
              step="0.1"
              value="42.5"
              aria-label="Telemetry sensor value in degrees Celsius"
              aria-describedby="sensor-help"
              aria-required="true"
            />
            <small id="sensor-help" style="opacity: 0.7; font-size: 12px;">Enter a numeric value (example: 42.5)</small>
          </div>
        </div>

        <button
          id="runInferenceBtn"
          class="btn btn-primary"
          aria-label="Run anomaly detection inference"
          aria-busy="false"
        >
          Run Inference
        </button>
      </div>
    </section>
  `;
}

/**
 * Get the sensor value from input
 */
export function getSensorValue(): number {
  const input = document.querySelector('#sensorValue') as HTMLInputElement;
  return parseFloat(input.value);
}

/**
 * Get the asset ID from input
 */
export function getAssetId(): string {
  const select = document.querySelector('#assetId') as HTMLSelectElement;
  return select.value;
}

/**
 * Set loading state on the run button
 */
export function setRunButtonLoading(isLoading: boolean) {
  const btn = document.querySelector('#runInferenceBtn') as HTMLButtonElement;
  if (isLoading) {
    btn.disabled = true;
    btn.textContent = 'Running...';
  } else {
    btn.disabled = false;
    btn.textContent = 'Run Inference';
  }
}
