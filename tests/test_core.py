import pytest
import numpy as np
from videocompress.core.checkerboard import CheckerboardMaskGenerator, apply_checkerboard_decimation
from videocompress.core.filter import SelectiveMeanReconstructor, DirectionalEdgeReconstructor


def test_checkerboard_mask():
    mask = CheckerboardMaskGenerator.get_mask(100, 100)
    assert mask.shape == (100, 100)
    assert mask[0, 0] == True
    assert mask[0, 1] == False
    assert mask[1, 0] == False
    assert mask[1, 1] == True


def test_decimation():
    frame = np.ones((50, 50, 3), dtype=np.uint8) * 128
    decimated, is_even = apply_checkerboard_decimation(frame, 0)
    assert is_even == True
    # At (0,0), even frame retains pixel (128)
    assert np.all(decimated[0, 0] == 128)
    # At (0,1), even frame zeroes out pixel (0)
    assert np.all(decimated[0, 1] == 0)


def test_selective_mean_reconstruction():
    reconstructor = SelectiveMeanReconstructor(mode="fast")
    # Synthetic gradient frame
    frame = np.zeros((64, 64, 3), dtype=np.uint8)
    frame[:, :] = 100

    # Decimate frame 0
    decimated, _ = apply_checkerboard_decimation(frame, 0)

    # Reconstruct
    reconstructed = reconstructor.reconstruct(decimated, 0)
    assert reconstructed.shape == frame.shape
    # All interior pixels should be restored close to 100
    assert np.allclose(reconstructed[2:-2, 2:-2], 100, atol=2)


def test_directional_edge_reconstruction():
    reconstructor = DirectionalEdgeReconstructor(threshold=10)
    frame = np.zeros((40, 40, 3), dtype=np.uint8)
    frame[:20, :] = 50
    frame[20:, :] = 200

    decimated, _ = apply_checkerboard_decimation(frame, 0)
    reconstructed = reconstructor.reconstruct(decimated, 0)
    assert reconstructed.shape == frame.shape
    assert np.all(reconstructed[5, 5] == 50)
    assert np.all(reconstructed[35, 35] == 200)
