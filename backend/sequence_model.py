import numpy as np

class TimeSeriesAnomalyTracker:
    def __init__(self, window_size=5):
        self.window_size = window_size
        self.history = []

    def evaluate_trend(self, current_val):
        """
        Tracks a rolling window of telemetry values to detect slow upward/downward drifts 
        (e.g., temperature slowly increasing over time).
        """
        self.history.append(current_val)
        if len(self.history) > self.window_size:
            self.history.pop(0) # Keep only the latest N steps

        if len(self.history) < self.window_size:
            return 0.0, "Stabilizing history..."

        # Calculate slope or trend across the window
        trend = np.polyfit(range(len(self.history)), self.history, 1)[0]
        
        if trend > 0.5:
            return float(trend), "Warning: Parameter is steadily increasing over time."
        elif trend < -0.5:
            return float(trend), "Warning: Parameter is steadily decreasing over time."
        else:
            return float(trend), "Trend stable."