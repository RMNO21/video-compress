"""
High-efficiency video transform & compression engine.
Integrates checkerboard decimation with GPU hardware-accelerated encoding (AV1, HEVC, H.264).
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
from ..core.hw_accel import HardwareEngine


class VideoEncoder:
    """
    Transforms and prepares source videos for storage and high-speed streaming.
    Supports hardware-accelerated AV1, HEVC, and H.264 encoding with audio multiplexing.
    """

    def __init__(
        self,
        codec: str = "av1",
        preset: str = "balanced",
        filter_type: str = "directional",
        crf: int = 24,
        scale: float = 1.0,
    ):
        self.codec = codec
        self.preset = preset
        self.filter_type = filter_type
        self.crf = crf
        self.scale = scale

        if filter_type == "directional":
            self.reconstructor = DirectionalEdgeReconstructor(threshold=10)
        else:
            self.reconstructor = SelectiveMeanReconstructor(mode="fast")

        # Discover hardware encoder
        self.encoder_name, self.actual_codec, self.accel_type = HardwareEngine.select_best_encoder(self.codec)

    def encode(
        self,
        input_path: str,
        output_path: Optional[str] = None,
        progress_callback: Optional[Callable[[int, int, float], None]] = None,
    ) -> str:
        """
        Compresses and prepares the input video.
        """
        if not os.path.exists(input_path):
            raise FileNotFoundError(f"Input file not found: {input_path}")

        if output_path is None:
            base, _ = os.path.splitext(input_path)
            output_path = f"{base}_compressed_{self.actual_codec}.mp4"

        cap = cv2.VideoCapture(input_path)
        if not cap.isOpened():
            raise RuntimeError(f"Could not open video file: {input_path}")

        orig_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        orig_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

        out_w = int(orig_w * self.scale)
        out_h = int(orig_h * self.scale)
        out_w = out_w if out_w % 2 == 0 else out_w - 1
        out_h = out_h if out_h % 2 == 0 else out_h - 1

        mask = CheckerboardMaskGenerator.get_mask(out_h, out_w)
        temp_video_path = output_path + ".temp.mp4"
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        writer = cv2.VideoWriter(temp_video_path, fourcc, fps, (out_w, out_h))

        print(f"\n========================================================")
        print(f"      🗜️  VIDEO-COMPRESS v2.0 - HARDWARE ENGINE         ")
        print(f"========================================================")
        print(f"Input Video:      {input_path}")
        print(f"Source Specs:     {orig_w}x{orig_h} @ {fps:.2f} FPS ({total_frames} frames)")
        print(f"Target Specs:     {out_w}x{out_h} (Scale: {self.scale:.2f})")
        print(f"Hardware Accel:   {self.accel_type}")
        print(f"Codec & Encoder:  {self.actual_codec.upper()} via [{self.encoder_name}]")
        print(f"Reconstruction:   {self.filter_type} filter")
        print(f"Output Target:    {output_path}")
        print(f"========================================================\n")

        start_time = time.time()
        frame_idx = 0

        try:
            while True:
                ret, frame = cap.read()
                if not ret:
                    break

                if (out_w != orig_w) or (out_h != orig_h):
                    frame = cv2.resize(frame, (out_w, out_h), interpolation=cv2.INTER_AREA)

                # Step 1: Spatial-temporal decimation
                decimated, _ = apply_checkerboard_decimation(frame, frame_idx, mask=mask)

                # Step 2: Edge-preserving reconstruction to maximize codec intra-frame correlation
                processed = self.reconstructor.reconstruct(decimated, frame_idx, mask=mask)
                writer.write(processed)

                frame_idx += 1
                elapsed = time.time() - start_time
                current_fps = frame_idx / elapsed if elapsed > 0 else 0

                if frame_idx % 15 == 0 or frame_idx == total_frames:
                    pct = (frame_idx / total_frames * 100) if total_frames > 0 else 0
                    eta_sec = (total_frames - frame_idx) / current_fps if current_fps > 0 else 0
                    print(
                        f"\rProcessing: [{frame_idx}/{total_frames}] {pct:.1f}% | "
                        f"Speed: {current_fps:.1f} FPS | ETA: {eta_sec:.1f}s",
                        end="",
                        flush=True,
                    )
                    if progress_callback:
                        progress_callback(frame_idx, total_frames, current_fps)

        finally:
            cap.release()
            writer.release()

        print("\n\nMuxing audio & encoding with Hardware Accelerated FFmpeg...")
        ffmpeg_bin = HardwareEngine.get_ffmpeg_path()

        enc_args = HardwareEngine.build_encoding_args(self.encoder_name, crf=self.crf, preset=self.preset)

        cmd = [
            ffmpeg_bin,
            "-y",
            "-i", temp_video_path,
            "-i", input_path,
            "-map", "0:v:0",
            "-map", "1:a:0?",
        ] + enc_args + [
            "-c:a", "libopus" if "libopus" in HardwareEngine.get_available_encoders() else "aac",
            "-b:a", "128k",
            "-movflags", "+faststart",
            output_path,
        ]

        try:
            res = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True, check=True)
            if os.path.exists(temp_video_path):
                os.remove(temp_video_path)
        except subprocess.CalledProcessError as e:
            # Fallback to libx264 if hardware encoder had driver constraint
            print(f"[WARN] Hardware encoder {self.encoder_name} reported: {e.stderr[:100]}... Falling back to libx264.")
            fallback_cmd = [
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
                output_path,
            ]
            subprocess.run(fallback_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            if os.path.exists(temp_video_path):
                os.remove(temp_video_path)

        orig_size_mb = os.path.getsize(input_path) / (1024 * 1024)
        comp_size_mb = os.path.getsize(output_path) / (1024 * 1024)
        ratio = (1.0 - (comp_size_mb / orig_size_mb)) * 100 if orig_size_mb > 0 else 0.0

        print(f"\n========================================================")
        print(f"             ✨ COMPRESSION COMPLETE ✨                 ")
        print(f"========================================================")
        print(f"Original Size:    {orig_size_mb:.2f} MB")
        print(f"Compressed Size:  {comp_size_mb:.2f} MB")
        print(f"Total Storage Saved: {ratio:.1f}%")
        print(f"Output File:      {output_path}")
        print(f"========================================================\n")

        return output_path
