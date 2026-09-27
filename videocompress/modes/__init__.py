"""
Operational modes: Encoder (preparation) and Player (real-time playback).
"""
from .encoder import VideoEncoder
from .player import VideoPlayer

__all__ = ["VideoEncoder", "VideoPlayer"]
