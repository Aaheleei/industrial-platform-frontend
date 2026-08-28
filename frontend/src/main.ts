import './style.css'

document.querySelector<HTMLDivElement>('#app')!.innerHTML = `
  <div style="padding: 2rem; font-family: Arial, sans-serif;">
    <h2>Industrial Anomaly Intelligence Dashboard</h2>
    <div style="margin-bottom: 1.5rem;">
      <input
        type="number"
        id="sensorValue"
        placeholder="Enter sensor value..."
        style="padding: 0.5rem; margin-right: 0.5rem; width: 200px;"
      />
      <button id="predictBtn" style="padding: 0.5rem 1rem; cursor: pointer;">Run Prediction</button>
    </div>

    <div id="resultBox" style="background: #f4f4f4; padding: 1rem; border-radius: 5px; maxWidth: 500px; display: none;">
      <h3>Analysis Results</h3>
      <p><strong>Sensor Value:</strong> <span id="resValue"></span></p>
      <p><strong>Trend Score:</strong> <span id="resTrend"></span></p>
      <p><strong>Trend Analysis:</strong> <span id="resAnalysis"></span></p>
      <p><strong>Quality Estimation:</strong> <span id="resQuality"></span></p>
      <p><strong>RAG Recommendation:</strong> <span id="resRag"></span></p>
      <p style="color: green;"><strong>Status:</strong> <span id="resStatus"></span></p>
    </div>
  </div>
`;

document.querySelector('#predictBtn')?.addEventListener('click', async () => {
  const inputEl = document.querySelector('#sensorValue') as HTMLInputElement;
  const value = parseFloat(inputEl.value);

  if (isNaN(value)) {
    alert('Please enter a valid number');
    return;
  }

  try {
    const response = await fetch('http://localhost:8000/predict', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ value }),
    });
    const data = await response.json();

    document.getElementById('resValue')!.innerText = data.sensor_value;
    document.getElementById('resTrend')!.innerText = data.trend_score;
    document.getElementById('resAnalysis')!.innerText = data.trend_analysis;
    document.getElementById('resQuality')!.innerText = data.quality_estimation;
    document.getElementById('resRag')!.innerText = data.rag_recommendation;
    document.getElementById('resStatus')!.innerText = data.status;

    document.getElementById('resultBox')!.style.display = 'block';
  } catch (err) {
    console.error('Error connecting to backend:', err);
    alert('Failed to connect to FastAPI backend on port 8000');
  }
});