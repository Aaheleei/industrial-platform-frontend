"""
Configuration loader and utilities.
"""

import yaml
from typing import Dict, Any
from pathlib import Path


def load_config(config_path: str = "configs/config.yaml") -> Dict[str, Any]:
    """Load YAML config file."""
    with open(config_path, "r") as f:
        config = yaml.safe_load(f)
    return config


def get_config_value(config: Dict[str, Any], key_path: str, default=None) -> Any:
    """
    Get a nested config value by dot-separated path.
    E.g., get_config_value(config, "trust.epsilon") returns config["trust"]["epsilon"]
    """
    keys = key_path.split(".")
    val = config
    for key in keys:
        if isinstance(val, dict) and key in val:
            val = val[key]
        else:
            return default
    return val
