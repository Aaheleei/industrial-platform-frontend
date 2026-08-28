"""
Integration test: Full inference pipeline end-to-end.
"""

import pytest
import numpy as np
from pathlib import Path
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).parent.parent))

from pipeline.inference import InferencePipeline
from telemetry.generator import generate_sample
from history.generator import generate_asset_history
from configs import load_config


class TestInferencePipeline:
    """Test full inference pipeline."""

    def test_pipeline_initialization(self):
        config_path = "configs/config.yaml"
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            pipeline = InferencePipeline(
                config_path=config_path,
                priors_store_path=f.name,
            )
            assert pipeline is not None

    def test_pipeline_clean_inference(self):
        """Test inference with all modalities present and good quality."""
        config_path = "configs/config.yaml"
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            pipeline = InferencePipeline(
                config_path=config_path,
                priors_store_path=f.name,
            )

            # Create synthetic inputs
            image = np.random.rand(480, 640, 3)
            sample = generate_sample(condition="normal", seed=42)
            history = generate_asset_history(asset_id="asset_001", seed=42)

            telemetry = {
                "channels": sample.channels,
                "timestamps": sample.timestamps,
            }

            result = pipeline.run_inference(image, telemetry, history, "asset_001")

            assert result.asset_id == "asset_001"
            assert "label" in result.prediction
            assert 0.0 <= result.prediction["calibrated_probability"] <= 1.0
            assert len(result.modalities) == 3
            assert result.uncertainty["cross_modal_disagreement"] >= 0.0

    def test_pipeline_output_structure(self):
        """Verify InferenceResult structure is correct."""
        config_path = "configs/config.yaml"
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            pipeline = InferencePipeline(
                config_path=config_path,
                priors_store_path=f.name,
            )

            image = np.random.rand(480, 640, 3)
            sample = generate_sample(condition="normal", seed=42)
            history = generate_asset_history(asset_id="asset_002", seed=42)

            telemetry = {
                "channels": sample.channels,
                "timestamps": sample.timestamps,
            }

            result = pipeline.run_inference(image, telemetry, history, "asset_002")

            # Check structure
            assert result.asset_id == "asset_002"

            # prediction dict
            assert "label" in result.prediction
            assert "raw_probability" in result.prediction
            assert "calibrated_probability" in result.prediction

            # modalities list
            assert len(result.modalities) == 3
            for mod in result.modalities:
                assert "name" in mod
                assert "prediction" in mod
                assert "quality" in mod
                assert "prior" in mod
                assert "weight" in mod

            # uncertainty dict
            assert "cross_modal_disagreement" in result.uncertainty

            # explanations dict
            assert "dominant_modality" in result.explanations
            assert "reason" in result.explanations

    def test_pipeline_weights_sum_to_one(self):
        """Verify fusion weights sum to 1."""
        config_path = "configs/config.yaml"
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            pipeline = InferencePipeline(
                config_path=config_path,
                priors_store_path=f.name,
            )

            image = np.random.rand(480, 640, 3)
            sample = generate_sample(condition="normal", seed=42)
            history = generate_asset_history(asset_id="asset_003", seed=42)

            telemetry = {
                "channels": sample.channels,
                "timestamps": sample.timestamps,
            }

            result = pipeline.run_inference(image, telemetry, history, "asset_003")

            weights = {mod["name"]: mod["weight"] for mod in result.modalities}
            weight_sum = sum(weights.values())
            assert abs(weight_sum - 1.0) < 1e-5


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
