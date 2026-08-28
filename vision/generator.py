"""
Vision image generator: structured synthetic defects for anomaly detection.

Normal: procedural texture (perlin-like noise or checkerboard patterns)
Anomalous: same base + injected defect (scratch, dark patch, geometric distortion)
"""

import numpy as np
from typing import Tuple


def generate_base_texture(size: int = 480, seed: int = None, texture_type: str = "checkerboard") -> np.ndarray:
    """
    Generate a base texture (normal condition).

    Args:
        size: Image dimension (square)
        seed: Random seed
        texture_type: "checkerboard", "gradients", or "noise"

    Returns:
        RGB image in [0, 1] of shape (size, size, 3)
    """
    if seed is not None:
        np.random.seed(seed)

    if texture_type == "checkerboard":
        # Checkerboard pattern
        grid_size = 40
        pattern = np.zeros((size, size))
        for i in range(0, size, grid_size):
            for j in range(0, size, grid_size):
                if ((i // grid_size) + (j // grid_size)) % 2 == 0:
                    pattern[i:i+grid_size, j:j+grid_size] = 1.0
        image = np.stack([pattern] * 3, axis=-1)

    elif texture_type == "gradients":
        # Linear gradients
        x = np.linspace(0, 1, size)
        y = np.linspace(0, 1, size)
        xx, yy = np.meshgrid(x, y)
        r_channel = xx
        g_channel = yy
        b_channel = 0.5 * (xx + yy)
        image = np.stack([r_channel, g_channel, b_channel], axis=-1)

    else:  # noise (structured)
        # Structured noise: low-frequency component (more realistic)
        base = np.random.rand(size, size, 3)
        # Blur to create structure
        from scipy.ndimage import gaussian_filter
        image = np.array([gaussian_filter(base[:, :, i], sigma=10) for i in range(3)])
        image = np.transpose(image, (1, 2, 0))
        image = (image - image.min()) / (image.max() - image.min() + 1e-6)

    return np.clip(image, 0, 1).astype(np.float32)


def inject_defect(image: np.ndarray, defect_type: str = "scratch", intensity: float = 0.8) -> np.ndarray:
    """
    Inject a synthetic defect into an image.

    Args:
        image: Base texture image in [0, 1]
        defect_type: "scratch", "dark_patch", "distortion", or "blur"
        intensity: How strong the defect is [0, 1]

    Returns:
        Image with injected defect
    """
    image = image.copy()
    h, w = image.shape[:2]

    if defect_type == "scratch":
        # Draw a thick line scratch across image (HIGH CONTRAST)
        y1, y2 = np.random.randint(0, h, 2)
        x1, x2 = np.random.randint(0, w, 2)

        # Create thick line with high contrast
        line_points = np.linspace([y1, x1], [y2, x2], 200, dtype=int)
        thickness = max(3, int(15 * intensity))
        for pt in line_points:
            y, x = pt[0] % h, pt[1] % w
            image[max(0, y-thickness):min(h, y+thickness),
                  max(0, x-thickness):min(w, x+thickness)] = 0.1  # Dark line

    elif defect_type == "dark_patch":
        # Larger, darker rectangular patch
        patch_h = int(h * 0.15 * (0.7 + intensity * 0.3))
        patch_w = int(w * 0.15 * (0.7 + intensity * 0.3))
        y = np.random.randint(0, max(1, h - patch_h))
        x = np.random.randint(0, max(1, w - patch_w))

        image[y:y+patch_h, x:x+patch_w] = 0.15  # Very dark patch

    elif defect_type == "bright_blob":
        # Bright overexposed blob
        blob_h = int(h * 0.12)
        blob_w = int(w * 0.12)
        y = np.random.randint(0, max(1, h - blob_h))
        x = np.random.randint(0, max(1, w - blob_w))

        # Create circular bright region
        yy, xx = np.ogrid[:blob_h, :blob_w]
        mask = (yy - blob_h//2)**2 + (xx - blob_w//2)**2 <= (blob_h//2)**2
        image[y:y+blob_h, x:x+blob_w][mask] = 0.95  # Bright blob

    elif defect_type == "distortion":
        # More severe geometric distortion
        from scipy import ndimage
        yy, xx = np.mgrid[:h, :w]

        # Radial distortion center
        cy, cx = h // 2 + np.random.randint(-h//6, h//6), w // 2 + np.random.randint(-w//6, w//6)

        # Compute stronger distortion
        dist = np.sqrt((yy - cy)**2 + (xx - cx)**2)
        factor = 1 + intensity * 0.25 * np.sin(dist / 15)  # Stronger effect

        for c in range(3):
            image[:, :, c] = ndimage.map_coordinates(image[:, :, c],
                                                      [yy / factor, xx / factor],
                                                      order=1, mode='reflect')

    elif defect_type == "blur":
        # Blur a region (focus issue) - larger and more obvious
        from scipy.ndimage import gaussian_filter
        blur_h = int(h * 0.25)
        blur_w = int(w * 0.25)
        y = np.random.randint(0, max(1, h - blur_h))
        x = np.random.randint(0, max(1, w - blur_w))

        blurred_region = gaussian_filter(image[y:y+blur_h, x:x+blur_w], sigma=15*intensity)
        image[y:y+blur_h, x:x+blur_w] = blurred_region

    return np.clip(image, 0, 1).astype(np.float32)


def generate_vision_image(condition: str = "normal", seed: int = None, size: int = 480) -> np.ndarray:
    """
    Generate a synthetic vision image (normal or anomalous).

    Args:
        condition: "normal" or "anomalous"
        seed: Random seed for reproducibility
        size: Image size (square)

    Returns:
        RGB image of shape (size, size, 3) in [0, 1]
    """
    if seed is not None:
        np.random.seed(seed)

    # Choose texture type
    texture_type = np.random.choice(["checkerboard", "gradients", "noise"])

    # Generate base
    image = generate_base_texture(size, seed, texture_type)

    # Inject defect if anomalous
    if condition == "anomalous":
        defect_type = np.random.choice(["scratch", "dark_patch", "bright_blob", "distortion", "blur"])
        intensity = np.random.uniform(0.7, 1.0)  # Stronger intensity
        image = inject_defect(image, defect_type, intensity)

    return image
