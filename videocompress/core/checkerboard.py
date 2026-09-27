"""
Checkerboard mask generator and decimation routines.
"""
from typing import Tuple, Dict
import numpy as np


class CheckerboardMaskGenerator:
    """
    Cached, zero-allocation mask generator for alternating quincunx / checkerboard grids.
    """
    _cache: Dict[Tuple[int, int], np.ndarray] = {}

    @classmethod
    def get_mask(cls, height: int, width: int) -> np.ndarray:
        """
        Returns a boolean mask where True indicates (x + y) % 2 == 0.
        Uses in-memory caching to avoid allocating coordinate grids per frame.
        """
        key = (height, width)
        if key not in cls._cache:
            y, x = np.indices((height, width), dtype=np.int32)
            cls._cache[key] = ((x + y) % 2 == 0)
        return cls._cache[key]

    @classmethod
    def clear_cache(cls) -> None:
        """Clears cached coordinate grids."""
        cls._cache.clear()


def apply_checkerboard_decimation(frame: np.ndarray, frame_index: int, mask: np.ndarray = None) -> Tuple[np.ndarray, bool]:
    """
    Applies temporal checkerboard decimation.
    Even frames retain (x+y)%2==0 coordinates.
    Odd frames retain (x+y)%2==1 coordinates.

    Returns:
        (decimated_frame, is_even_parity)
    """
    h, w = frame.shape[:2]
    if mask is None:
        mask = CheckerboardMaskGenerator.get_mask(h, w)

    is_even = (frame_index % 2 == 0)
    valid_mask = mask if is_even else (~mask)

    decimated = np.zeros_like(frame)
    decimated[valid_mask] = frame[valid_mask]
    return decimated, is_even
