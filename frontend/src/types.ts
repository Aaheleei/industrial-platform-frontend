/**
 * Shared TypeScript interfaces for the Industrial Anomaly Intelligence Dashboard
 */

/**
 * Backend response from /predict endpoint
 */
export interface BackendResponse {
  sensor_value: number;
  trend_score: number;
  trend_analysis: string;
  quality_estimation: number;
  rag_recommendation: string;
  status: string;

  // Multimodal inference results (stages 3-5)
  trust_gate?: number;
  fusion?: {
    raw_score: number;
    fused_score: number;
    disagreement: number;
  };
  calibration?: {
    raw_probability: number;
    calibrated_probability: number;
    temperature: number;
    ece: number;
  };
  modalities?: {
    vision: {
      prediction: number;
      quality: number;
      prior_trust: number;
      weight: number;
    };
    telemetry: {
      prediction: number;
      quality: number;
      prior_trust: number;
      weight: number;
    };
    history: {
      prediction: number;
      quality: number;
      prior_trust: number;
      weight: number;
    };
  };
}

/**
 * State for the inference process
 */
export interface InferenceState {
  assetId: string;
  sensorValue: number;
  isLoading: boolean;
  result: BackendResponse | null;
  error: string | null;
  activeStage: number; // 0-6, where 0 = idle
  animationComplete: boolean;
}

/**
 * Individual pipeline stage
 */
export interface PipelineStage {
  id: number;
  name: string;
  title: string;
  description: string;
  value?: number | string;
  factors?: Record<string, number>;
}

/**
 * Request body for /predict endpoint
 */
export interface PredictRequest {
  value: number;
}
