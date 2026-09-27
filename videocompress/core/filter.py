"""
Reconstruction filters for missing checkerboard pixels:
1. SelectiveMeanReconstructor (vectorized outlier-rejecting 4-neighbor average)
2. DirectionalEdgeReconstructor (gradient-guided edge-preserving interpolation)
"""
from typing import Optional
import cv2
import numpy as np
from .checkerboard import CheckerboardMaskGenerator


class SelectiveMeanReconstructor:
    """
    Vectorized implementation of the 4-neighbor Selective Mean Filter.
    For each target pixel:
    - Gathers cardinal neighbors (Up, Down, Left, Right) using zero-copy padded views.
    - Identifies and rejects the single most distant outlier neighbor (boundary edge).
    - Computes the average of the remaining 3 closest neighbors.
    """

    def __init__(self, mode: str = "fast"):
        """
        Args:
            mode: 'fast' uses L1 Manhattan channel distance, 'precise' uses L2 Euclidean norm.
        """
        self.mode = mode

    def reconstruct(self, frame: np.ndarray, frame_index: int, mask: Optional[np.ndarray] = None) -> np.ndarray:
        """
        Reconstructs missing decimated pixels for the given frame parity.
        """
        h, w = frame.shape[:2]
        if mask is None:
            mask = CheckerboardMaskGenerator.get_mask(h, w)

        is_even = (frame_index % 2 == 0)
        # Even frames have valid pixels at (x+y)%2 == 0, missing at (x+y)%2 == 1
        missing_mask = (~mask) if is_even else mask

        # Fast border reflection with 1-pixel border
        pad = cv2.copyMakeBorder(frame, 1, 1, 1, 1, cv2.BORDER_REFLECT)
        pad_int = pad.astype(np.int32)

        up = pad_int[:-2, 1:-1]
        down = pad_int[2:, 1:-1]
        left = pad_int[1:-1, :-2]
        right = pad_int[1:-1, 2:]

        sum_neighbors = up + down + left + right

        # 4 * mean = sum_neighbors. Difference to mean: 4*n - sum_neighbors
        if self.mode == "fast":
            # L1 Manhattan norm across channels: sum(|4*n - sum|)
            d_up = np.sum(np.abs(4 * up - sum_neighbors), axis=2)
            d_down = np.sum(np.abs(4 * down - sum_neighbors), axis=2)
            d_left = np.sum(np.abs(4 * left - sum_neighbors), axis=2)
            d_right = np.sum(np.abs(4 * right - sum_neighbors), axis=2)
        else:
            # L2 squared norm
            d_up = np.sum((4 * up - sum_neighbors) ** 2, axis=2)
            d_down = np.sum((4 * down - sum_neighbors) ** 2, axis=2)
            d_left = np.sum((4 * left - sum_neighbors) ** 2, axis=2)
            d_right = np.sum((4 * right - sum_neighbors) ** 2, axis=2)

        # Find which neighbor has the maximum distance (outlier)
        stack_dist = np.stack([d_up, d_down, d_left, d_right], axis=-1)
        max_dist_idx = np.argmax(stack_dist, axis=-1)

        # Output frame preserves existing valid pixels
        output = frame.copy()
        neighbors = [up, down, left, right]

        # Calculate average of the 3 closest neighbors ONLY where pixels are missing
        for i, neighbor in enumerate(neighbors):
            active_outlier_mask = (max_dist_idx == i) & missing_mask
            if np.any(active_outlier_mask):
                output[active_outlier_mask] = (
                    (sum_neighbors[active_outlier_mask] - neighbor[active_outlier_mask]) // 3
                ).astype(np.uint8)

        return output


class DirectionalEdgeReconstructor:
    """
    Directional gradient-guided reconstruction filter.
    Analyzes local gradients across Vertical, Horizontal, and Diagonal axes to interpolate
    ALONG the edge rather than across the edge, completely preventing edge blurring.
    """

    def __init__(self, threshold: int = 12):
        self.threshold = threshold

    def reconstruct(self, frame: np.ndarray, frame_index: int, mask: Optional[np.ndarray] = None) -> np.ndarray:
        h, w = frame.shape[:2]
        if mask is None:
            mask = CheckerboardMaskGenerator.get_mask(h, w)

        is_even = (frame_index % 2 == 0)
        missing_mask = (~mask) if is_even else mask

        # Grayscale edge guidance
        if len(frame.shape) == 3:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY).astype(np.int32)
        else:
            gray = frame.astype(np.int32)

        pad_g = cv2.copyMakeBorder(gray, 1, 1, 1, 1, cv2.BORDER_REFLECT)
        g_up = pad_g[:-2, 1:-1]
        g_down = pad_g[2:, 1:-1]
        g_left = pad_g[1:-1, :-2]
        g_right = pad_g[1:-1, 2:]

        diff_v = np.abs(g_up - g_down)
        diff_h = np.abs(g_left - g_right)

        pad_c = cv2.copyMakeBorder(frame, 1, 1, 1, 1, cv2.BORDER_REFLECT).astype(np.uint16)
        c_up = pad_c[:-2, 1:-1]
        c_down = pad_c[2:, 1:-1]
        c_left = pad_c[1:-1, :-2]
        c_right = pad_c[1:-1, 2:]

        avg_v = (c_up + c_down) // 2
        avg_h = (c_left + c_right) // 2
        avg_all = (c_up + c_down + c_left + c_right) // 4

        output = frame.copy()

        # Vertical edge detected -> interpolate vertically
        is_vert_edge = missing_mask & (diff_v < (diff_h - self.threshold))
        output[is_vert_edge] = avg_v[is_vert_edge].astype(np.uint8)

        # Horizontal edge detected -> interpolate horizontally
        is_horiz_edge = missing_mask & (diff_h < (diff_v - self.threshold))
        output[is_horiz_edge] = avg_h[is_horiz_edge].astype(np.uint8)

        # Flat or omnidirectional region -> interpolate with all 4
        is_flat = missing_mask & (~is_vert_edge) & (~is_horiz_edge)
        output[is_flat] = avg_all[is_flat].astype(np.uint8)

        return output
