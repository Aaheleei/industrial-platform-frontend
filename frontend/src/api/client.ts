/**
 * API Client Module
 * Handles all communication with the backend /predict endpoint
 */

import type { BackendResponse, PredictRequest } from '../types';

const API_BASE_URL = 'http://localhost:8000';
const PREDICT_ENDPOINT = `${API_BASE_URL}/predict`;

/**
 * Call the /predict endpoint
 */
export async function predictAnomaly(sensorValue: number): Promise<BackendResponse> {
  const request: PredictRequest = { value: sensorValue };

  try {
    const response = await fetch(PREDICT_ENDPOINT, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(request),
    });

    if (!response.ok) {
      throw new Error(`API error: ${response.status} ${response.statusText}`);
    }

    const data = await response.json();
    return data as BackendResponse;
  } catch (error) {
    console.error('Predict API error:', error);
    throw error;
  }
}

/**
 * Check if API is available
 */
export async function checkAPIHealth(): Promise<boolean> {
  try {
    const response = await fetch(`${API_BASE_URL}/docs`, { method: 'HEAD' });
    return response.ok;
  } catch {
    return false;
  }
}
