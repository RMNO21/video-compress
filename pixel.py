"""
Backward-compatibility entrypoint for Video-Compress.
Redirects to the high-performance vectorized core engine.
"""
import sys
import os
import cv2

# Ensure local package is in sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from videocompress.core.filter import SelectiveMeanReconstructor
from videocompress.core.checkerboard import CheckerboardMaskGenerator, apply_checkerboard_decimation


def process_video():
    video_path = input("Video File Path: ").strip('"').strip("'")
    if not os.path.exists(video_path):
        print(f"Error: Video file not found: {video_path}")
        return

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print("Error: Could not open video stream.")
        return

    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    save_dir = os.path.dirname(video_path)
    output_path = os.path.join(save_dir, "processed_pixel_video.mp4")

    # Use modern mp4v / avc1
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

    mask = CheckerboardMaskGenerator.get_mask(height, width)
    reconstructor = SelectiveMeanReconstructor(mode="fast")

    print(f"\nProcessing {total_frames} frames with high-speed vectorized engine...")
    frame_count = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        # Reconstruct on the fly with outlier rejection
        reconstructed = reconstructor.reconstruct(frame, frame_count, mask=mask)
        out.write(reconstructed)

        frame_count += 1
        if frame_count % 15 == 0 or frame_count == total_frames:
            pct = (frame_count / total_frames * 100) if total_frames > 0 else 0
            print(f"Progress: {frame_count}/{total_frames} frames ({pct:.1f}%)", end="\r")

    cap.release()
    out.release()
    print(f"\n[DONE] High-performance reconstructed video saved to: {output_path}")


if __name__ == "__main__":
    process_video()