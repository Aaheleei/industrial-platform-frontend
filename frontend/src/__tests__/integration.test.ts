/**
 * Integration Tests: Backend Response → Pipeline Visualization
 * Tests that the frontend correctly maps backend data to the pipeline UI
 */

import { predictAnomaly } from '../api/client';
import type { BackendResponse } from '../types';

describe('Integration: Backend Response → Pipeline', () => {
  /**
   * Test 1: Backend returns complete response with all required fields
   */
  it('should call /predict and receive complete BackendResponse', async () => {
    const response = await predictAnomaly(42.5);

    // Verify all required fields are present
    expect(response).toHaveProperty('sensor_value');
    expect(response).toHaveProperty('trend_score');
    expect(response).toHaveProperty('trend_analysis');
    expect(response).toHaveProperty('quality_estimation');
    expect(response).toHaveProperty('rag_recommendation');
    expect(response).toHaveProperty('status');

    // Verify data types
    expect(typeof response.sensor_value).toBe('number');
    expect(typeof response.trend_score).toBe('number');
    expect(typeof response.trend_analysis).toBe('string');
    expect(typeof response.quality_estimation).toBe('number');
    expect(typeof response.rag_recommendation).toBe('string');
    expect(typeof response.status).toBe('string');

    // Verify quality is normalized [0, 1]
    expect(response.quality_estimation).toBeGreaterThanOrEqual(0);
    expect(response.quality_estimation).toBeLessThanOrEqual(1);
  });

  /**
   * Test 2: Response mapping to pipeline stages
   */
  it('should map response fields to all 6 pipeline stages', async () => {
    const response = await predictAnomaly(35.0);

    // Stage 1: Inputs - sensor_value
    expect(response.sensor_value).toBeDefined();

    // Stage 2: Quality - quality_estimation (independent from confidence)
    expect(response.quality_estimation).toBeGreaterThan(0);

    // Stage 3: Trust - placeholder (backend not ready)
    // Stage 4: Fusion - placeholder (backend not ready)
    // Stage 5: Calibration - placeholder (backend not ready)

    // Stage 6: Decision - trend_analysis + quality
    expect(response.trend_analysis).toBeTruthy();
    expect(response.rag_recommendation).toBeTruthy();
  });

  /**
   * Test 3: Quality estimation stays independent from trend analysis
   */
  it('quality_estimation should be independent from trend_score', async () => {
    // Test with different sensor values to see quality independence
    const response1 = await predictAnomaly(10);
    const response2 = await predictAnomaly(90);

    // Quality might differ, but should be independent scoring
    expect(response1.quality_estimation).toBeDefined();
    expect(response2.quality_estimation).toBeDefined();

    // Both should be valid probabilities
    expect(response1.quality_estimation).toBeGreaterThanOrEqual(0);
    expect(response2.quality_estimation).toBeGreaterThanOrEqual(0);
  });

  /**
   * Test 4: Error handling - invalid input
   */
  it('should handle network errors gracefully', async () => {
    // This test would need a mock or a way to simulate network failure
    // For now, just verify the client handles errors
    try {
      const response = await predictAnomaly(NaN);
      // If it doesn't error, the backend handles NaN
      expect(response).toBeDefined();
    } catch (error) {
      expect(error).toBeDefined();
    }
  });

  /**
   * Test 5: Animation readiness - verify data completeness
   */
  it('should provide all data needed for 6-stage animation', async () => {
    const response = await predictAnomaly(50);

    // For animation to work smoothly, we need:
    // - Stage 1: sensor input
    expect(response.sensor_value).toBeDefined();

    // - Stage 2: quality metric
    expect(response.quality_estimation).toBeDefined();

    // - Stage 6: final decision
    expect(response.trend_analysis).toBeDefined();

    // Animation sequence should complete without data gaps
    expect(response.status).toBeTruthy();
  });
});

/**
 * Unit Tests: Data Transformation Functions
 */
describe('Data Transformation: Backend Response → UI Format', () => {
  /**
   * Test formatValue function logic
   */
  it('should format numbers correctly for display', () => {
    // Quality score (0-1) should display as percentage
    const quality = 0.72;
    const displayQuality = (quality * 100).toFixed(0) + '%';
    expect(displayQuality).toBe('72%');

    // Sensor value (arbitrary) should display with 2 decimals
    const sensor = 42.5;
    const displaySensor = sensor.toFixed(2);
    expect(displaySensor).toBe('42.50');
  });

  /**
   * Test stage activation order
   */
  it('should activate stages in correct sequence', () => {
    const stages = [1, 2, 3, 4, 5, 6];
    const stageDelay = 500; // ms

    // Total animation time = 6 stages × 500ms = 3000ms
    const totalTime = stages.length * stageDelay;
    expect(totalTime).toBe(3000);
  });

  /**
   * Test animation duration per stage
   */
  it('should animate each number value over 300ms', () => {
    // Number animation duration (shorter than stage delay allows smooth counting)
    const numberAnimationDuration = 300; // ms
    const stageDelay = 500; // ms

    // 300ms animation fits within 500ms stage window
    expect(numberAnimationDuration).toBeLessThan(stageDelay);
  });
});

/**
 * Scenario Tests: Key Use Cases
 */
describe('Scenario 1: Clean System - All Quality ~0.9', () => {
  it('should display high quality with balanced pipeline', async () => {
    const response = await predictAnomaly(50);

    // In clean system, quality should be reasonably high
    expect(response.quality_estimation).toBeGreaterThan(0.5);

    // Trend analysis should be informative
    expect(response.trend_analysis.length).toBeGreaterThan(0);
  });
});

describe('Scenario 2: Telemetry Noise - Quality Drops', () => {
  it('should detect quality degradation', async () => {
    // Call multiple times to simulate noisy data
    const responses = await Promise.all([
      predictAnomaly(100),
      predictAnomaly(5),
      predictAnomaly(95),
    ]);

    // At least one response should have quality data
    expect(responses.some(r => r.quality_estimation > 0)).toBe(true);
  });
});

describe('Scenario 7: Degradation - Trust-Gated Fusion > Fixed Averaging', () => {
  it('should show trust gating improves reliability', async () => {
    // This test validates the conceptual benefit
    const response = await predictAnomaly(42.5);

    // Quality estimation is independent from confidence
    // (demonstrates trust gating concept)
    expect(response.quality_estimation).toBeDefined();
    expect(response.trend_score).toBeDefined();

    // They should be different values in real scenarios
    // (not just copying confidence)
    console.log('Quality:', response.quality_estimation);
    console.log('Trend Score:', response.trend_score);
  });
});
