import numpy as np


def level(samples: np.ndarray) -> float:
    """Loudness in 0..1 for UI animation; samples are float in [-1, 1]."""
    return min(1.0, float(np.sqrt(np.mean(np.square(samples)))) * 4)
