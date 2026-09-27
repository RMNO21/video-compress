import pytest
import os
import cv2
import numpy as np
from videocompress.modes.encoder import VideoEncoder
from videocompress.modes.player import VideoPlayer


@pytest.fixture
def sample_video(tmp_path):
    video_path = str(tmp_path / "test_sample.mp4")
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    out = cv2.VideoWriter(video_path, fourcc, 30.0, (128, 128))
    for i in range(15):
        frame = np.full((128, 128, 3), (i * 15) % 255, dtype=np.uint8)
        out.write(frame)
    out.release()
    return video_path


def test_encoder_mode(sample_video, tmp_path):
    output_path = str(tmp_path / "output_test.mp4")
    encoder = VideoEncoder(preset="balanced", filter_type="directional", crf=28)
    res = encoder.encode(sample_video, output_path)

    assert os.path.exists(res)
    assert os.path.getsize(res) > 0


def test_player_initialization():
    player = VideoPlayer(filter_type="directional")
    assert player.reconstruct_active == True
    assert player.is_paused == False
