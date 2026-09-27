"""
High-efficiency video transform & compression engine.
Combines checkerboard decimation with optimized video codec compression.
"""
import os
import sys
import time
import subprocess
import shutil
from typing import Optional, Callable
import cv2
import numpy as np

from ..core.checkerboard import CheckerboardMaskGenerator, apply_checkerboard_decimation
from ..core.filter import DirectionalEdgeReconstructor, SelectiveMeanReconstructor


class VideoEncoder:
    """
    Transforms and prepares source videos for storage and high-speed streaming.
    """

    def __init__(
        self,
        preset: str = "balanced",
        filter_type: str = "directional",
        crf: int = 24,
        scale: float = 1.0,
    ):
        self.preset = preset
        self.filter_type = filter_type
        self.crf = crf
        self.scale = scale

        if filter_type == "directional":
            self.reconstructor = DirectionalEdgeReconstructor(threshold=10)
        else:
            self.reconstructor = SelectiveMeanReconstructor(mode="fast")

    def encode(
        self,
        input_path: str,
        output_path: Optional[str] = None,
        progress_callback: Optional[Callable[[int, int, float], None]] = None,
    ) -> str:
        """
        Compresses and prepares the input video.

        Returns:
            Path to the processed output video.
        """
        if not os.path.exists(input_path):
            raise FileNotFoundError(f"Input file not found: {input_path}")

        if output_path is None:
            base, ext = os.path.splitext(input_path)
            output_path = f"{base}_compressed.mp4"

        cap = cv2.VideoCapture(input_path)
        if not cap.isOpened():
            raise RuntimeError(f"Could not open video file: {input_path}")

        orig_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        orig_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

        out_w = int(orig_w * self.scale)
        out_h = int(orig_h * self.scale)
        # Ensure dimensions are even numbers for encoders
        out_w = out_w if out_w % 2 == 0 else out_w - 1
        out_h = out_h if out_h % 2 == 0 else out_h - 1

        mask = CheckerboardMaskGenerator.get_mask(out_h, out_w)

        # Temporary video output before audio multiplexing
        temp_video_path = output_path + ".temp.mp4"
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        writer = cv2.VideoWriter(temp_video_path, fourcc, fps, (out_w, out_h))

        print(f"\n[ENCODE MODE] Starting Compression...")
        print(f"Input: {input_path} ({orig_w}x{orig_h} @ {fps:.2f} FPS | {total_frames} frames)")
        print(f"Output: {output_path} ({out_w}x{out_h} | Preset: {self.preset} | Filter: {self.filter_type})")

        start_time = time.time()
        frame_idx = 0

        try:
            while True:
                ret, frame = cap.read()
                if not ret:
                    break

                if (out_w != orig_w) or (out_h != orig_h):
                    frame = cv2.resize(frame, (out_w, out_h), interpolation=cv2.INTER_AREA)

                # Apply temporal alternating checkerboard decimation
                decimated, _ = apply_checkerboard_decimation(frame, frame_idx, mask=mask)

                # Pre-reconstruct with edge-preserving selective filter so codec compresses with maximum intra-prediction
                processed = self.reconstructor.reconstruct(decimated, frame_idx, mask=mask)
                writer.write(processed)

                frame_idx += 1
                elapsed = time.time() - start_time
                current_fps = frame_idx / elapsed if elapsed > 0 else 0

                if frame_idx % 15 == 0 or frame_idx == total_frames:
                    pct = (frame_idx / total_frames * 100) if total_frames > 0 else 0
                    eta_sec = (total_frames - frame_idx) / current_fps if current_fps > 0 else 0
                    print(
                        f"\rProgress: [{frame_idx}/{total_frames}] {pct:.1f}% | "
                        f"Speed: {current_fps:.1f} FPS | ETA: {eta_sec:.1f}s",
                        end="",
                        flush=True,
                    )
                    if progress_callback:
                        progress_callback(frame_idx, total_frames, current_fps)

        finally:
            cap.release()
            writer.release()

        print("\n\nMuxing and optimizing with FFmpeg...")
        ffmpeg_bin = shutil.which("ffmpeg") or r"C:\msys64\mingw64\bin\ffmpeg.exe"

        # Check if ffmpeg is available for audio copy and high-efficiency H.264/HEVC compression
        if os.path.exists(ffmpeg_bin) or shutil.which("ffmpeg"):
            cmd = [
                ffmpeg_bin,
                "-y",
                "-i", temp_video_path,
                "-i", input_path,
                "-map", "0:v:0",
                "-map", "1:a:0?",
                "-c:v", "libx264",
                "-preset", "faster",
                "-crf", str(self.crf),
                "-c:a", "aac",
                "-b:a", "128k",
                "-movflags", "+faststart",
                output_path,
            ]
            try:
                subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
                if os.path.exists(temp_video_path):
                    os.remove(temp_video_path)
            except Exception:
                # If ffmpeg failed or error, fallback to temp output
                if os.path.exists(output_path):
                    os.remove(output_path)
                os.rename(temp_video_path, output_path)
        else:
            if os.path.exists(output_path):
                os.remove(output_path)
            os.rename(temp_video_path, output_path)

        # File size statistics
        orig_size_mb = os.path.getsize(input_path) / (1024 * 1024)
        comp_size_mb = os.path.getsize(output_path) / (1024 * 1024)
        ratio = (1.0 - (comp_size_mb / orig_size_mb)) * 100 if orig_size_mb > 0 else 0.0

        print(f"[COMPLETE] Compression Successful!")
        print(f"Original Size:   {orig_size_mb:.2f} MB")
        print(f"Compressed Size: {comp_size_mb:.2f} MB")
        print(f"Space Saved:     {ratio:.1f}%")
        print(f"Saved to:        {output_path}\n")

        return output_path
