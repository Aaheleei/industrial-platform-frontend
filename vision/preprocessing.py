"""
Vision preprocessing: image normalization, quality factor extraction.
"""

import numpy as np
import cv2
from typing import Tuple, Dict
from PIL import Image


def resize_and_normalize(image: np.ndarray, target_size: int = 224) -> np.ndarray:
    """
    Resize image to target size and normalize to [0, 1] range.

    Args:
        image: Input image (H, W) or (H, W, C)
        target_size: Target dimension (square)

    Returns:
        Normalized image of shape (target_size, target_size, 3) or (target_size, target_size)
    """
    if len(image.shape) == 2:
        # Grayscale: convert to 3-channel
        image = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
    elif image.shape[2] == 4:
        # RGBA: drop alpha
        image = cv2.cvtColor(image, cv2.COLOR_RGBA2BGR)

    # Resize
    resized = cv2.resize(image, (target_size, target_size), interpolation=cv2.INTER_AREA)

    # Normalize to [0, 1]
    if resized.dtype == np.uint8:
        resized = resized.astype(np.float32) / 255.0
    else:
        resized = np.clip(resized, 0, 1).astype(np.float32)

    return resized


def compute_blur_factor(image: np.ndarray, blur_ref: float = 100.0) -> float:
    """
    Compute blur factor using Laplacian variance.
    Higher variance = sharper image = higher blur_factor.

    Args:
        image: Grayscale or RGB image in [0, 1]
        blur_ref: Reference Laplacian variance for normalization

    Returns:
        blur_factor in [0, 1]
    """
    if len(image.shape) == 3:
        # Convert to grayscale
        gray = cv2.cvtColor((image * 255).astype(np.uint8), cv2.COLOR_BGR2GRAY).astype(np.float32) / 255.0
    else:
        gray = image

    laplacian = cv2.Laplacian((gray * 255).astype(np.uint8), cv2.CV_64F)
    variance = np.var(laplacian)

    # Normalize: clamp to [0, 1]
    factor = min(variance / blur_ref, 1.0)
    return max(factor, 0.0)


def compute_exposure_factor(image: np.ndarray, exposure_range: Tuple[float, float] = (50, 200)) -> float:
    """
    Compute exposure factor based on mean pixel brightness.
    Range: [low_bound, high_bound] in 8-bit space. Optimal is center.

    Args:
        image: RGB or grayscale image in [0, 1]
        exposure_range: (low_bound, high_bound) in 0-255 space

    Returns:
        exposure_factor in [0, 1]
    """
    if len(image.shape) == 3:
        # Convert to grayscale
        gray = cv2.cvtColor((image * 255).astype(np.uint8), cv2.COLOR_BGR2GRAY)
    else:
        gray = (image * 255).astype(np.uint8)

    mean_pixel = np.mean(gray)
    low, high = exposure_range
    midpoint = (low + high) / 2.0
    range_span = (high - low) / 2.0

    # Distance from midpoint, normalized by range
    distance = abs(mean_pixel - midpoint) / range_span
    factor = max(1.0 - distance, 0.0)
    return factor


def compute_illumination_uniformity(image: np.ndarray, illumination_threshold: float = 30.0) -> float:
    """
    Compute illumination uniformity using spatial std of grayscale.
    Lower std = more uniform = higher factor.

    Args:
        image: RGB or grayscale image in [0, 1]
        illumination_threshold: Std threshold above which factor drops to 0

    Returns:
        illumination_factor in [0, 1]
    """
    if len(image.shape) == 3:
        gray = cv2.cvtColor((image * 255).astype(np.uint8), cv2.COLOR_BGR2GRAY).astype(np.float32) / 255.0
    else:
        gray = image

    spatial_std = np.std(gray)
    factor = max(1.0 - (spatial_std * 255 / illumination_threshold), 0.0)
    return min(factor, 1.0)


def estimate_vision_quality(image: np.ndarray, config: Dict) -> Dict[str, float]:
    """
    Estimate vision quality factors from image properties alone.

    Args:
        image: Input image (H, W) or (H, W, C), values in [0, 1]
        config: Quality config dict with vision keys

    Returns:
        Dict with 'quality' (float in [0,1]) and 'factors' (dict of named factors)
    """
    vision_config = config.get("vision", {})
    blur_ref = vision_config.get("blur_ref", 100.0)
    exposure_range = tuple(vision_config.get("exposure_range", [50, 200]))
    illumination_threshold = vision_config.get("illumination_threshold", 30.0)

    blur = compute_blur_factor(image, blur_ref)
    exposure = compute_exposure_factor(image, exposure_range)
    illumination = compute_illumination_uniformity(image, illumination_threshold)

    factors = {
        "blur": blur,
        "exposure": exposure,
        "illumination": illumination,
    }

    # Aggregate by mean
    quality = np.mean(list(factors.values()))

    return {"quality": quality, "factors": factors}
