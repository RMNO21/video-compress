"""
Interactive Real-Time Video Player with on-the-fly reconstruction filter.
Features interactive controls, A/B visual comparison, timeline scrub, and HUD.
"""
import os
import sys
import time
from typing import Optional
import cv2
import numpy as np

from ..core.checkerboard import CheckerboardMaskGenerator
from ..core.filter import DirectionalEdgeReconstructor, SelectiveMeanReconstructor


class VideoPlayer:
    """
    High-performance video playback engine with real-time reconstruction filter.
    """

    def __init__(self, filter_type: str = "directional"):
        self.filter_type = filter_type
        if filter_type == "directional":
            self.reconstructor = DirectionalEdgeReconstructor(threshold=10)
        else:
            self.reconstructor = SelectiveMeanReconstructor(mode="fast")

        self.reconstruct_active = True
        self.is_paused = False
        self.show_hud = True

    def play(self, video_path: str, target_fps: Optional[float] = None) -> None:
        """
        Launches the interactive real-time video player.
        """
        if not os.path.exists(video_path):
            raise FileNotFoundError(f"Video file not found: {video_path}")

        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise RuntimeError(f"Could not open video file: {video_path}")

        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        native_fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        fps = target_fps if target_fps else native_fps
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        frame_delay = 1.0 / fps

        window_name = f"Video-Compress Player: {os.path.basename(video_path)}"
        cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
        cv2.resizeWindow(window_name, min(1280, width), min(720, height))

        mask = CheckerboardMaskGenerator.get_mask(height, width)

        print("\n==================================================")
        print("  VIDEO-COMPRESS INTERACTIVE REAL-TIME PLAYER     ")
        print("==================================================")
        print("Keyboard Controls:")
        print("  [SPACE]      : Pause / Resume")
        print("  [R]          : Toggle Real-time Reconstruction ON/OFF (A/B Test)")
        print("  [H]          : Toggle On-Screen Display HUD")
        print("  [LEFT/RIGHT] : Seek Backward / Forward 5 seconds")
        print("  [S]          : Save Comparison Screenshot")
        print("  [F]          : Toggle Fullscreen")
        print("  [Q] / [ESC]  : Exit Player")
        print("==================================================\n")

        fps_history = []
        is_fullscreen = False

        while True:
            t_start = time.time()

            if not self.is_paused:
                ret, frame = cap.read()
                if not ret:
                    # Loop video or break
                    print("\n[INFO] End of stream reached. Looping...")
                    cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    continue

                curr_frame_idx = int(cap.get(cv2.CAP_PROP_POS_FRAMES))

                # Apply on-the-fly reconstruction if enabled
                if self.reconstruct_active:
                    display_frame = self.reconstructor.reconstruct(frame, curr_frame_idx, mask=mask)
                else:
                    display_frame = frame.copy()
            else:
                curr_frame_idx = int(cap.get(cv2.CAP_PROP_POS_FRAMES))

            # Measure real FPS
            t_render = time.time() - t_start
            actual_fps = 1.0 / t_render if t_render > 0 else fps
            fps_history.append(actual_fps)
            if len(fps_history) > 20:
                fps_history.pop(0)
            avg_fps = sum(fps_history) / len(fps_history)

            # Draw HUD
            render_img = display_frame.copy()
            if self.show_hud:
                self._draw_hud(render_img, curr_frame_idx, total_frames, fps, avg_fps, width, height)

            cv2.imshow(window_name, render_img)

            # Frame rate timing control
            wait_time = max(1, int((frame_delay - t_render) * 1000)) if not self.is_paused else 30
            key = cv2.waitKey(wait_time) & 0xFF

            if key in (ord("q"), ord("Q"), 27):  # Q or ESC
                break
            elif key == ord(" "):  # Space
                self.is_paused = not self.is_paused
            elif key in (ord("r"), ord("R")):  # R
                self.reconstruct_active = not self.reconstruct_active
                status = "ENABLED" if self.reconstruct_active else "BYPASSED (RAW)"
                print(f"[HUD] Real-time Reconstruction: {status}")
            elif key in (ord("h"), ord("H")):  # H
                self.show_hud = not self.show_hud
            elif key in (ord("f"), ord("F")):  # F
                is_fullscreen = not is_fullscreen
                prop = cv2.WINDOW_FULLSCREEN if is_fullscreen else cv2.WINDOW_NORMAL
                cv2.setWindowProperty(window_name, cv2.WND_PROP_FULLSCREEN, prop)
            elif key in (ord("s"), ord("S")):  # S
                save_dir = os.path.dirname(video_path)
                snapshot_path = os.path.join(save_dir, f"snapshot_frame_{curr_frame_idx}.png")
                cv2.imwrite(snapshot_path, display_frame)
                print(f"[SNAPSHOT] Saved frame {curr_frame_idx} to: {snapshot_path}")
            elif key == 81 or key == 2424832:  # Left arrow
                new_pos = max(0, curr_frame_idx - int(fps * 5))
                cap.set(cv2.CAP_PROP_POS_FRAMES, new_pos)
            elif key == 83 or key == 2555904:  # Right arrow
                new_pos = min(total_frames - 1, curr_frame_idx + int(fps * 5))
                cap.set(cv2.CAP_PROP_POS_FRAMES, new_pos)

        cap.release()
        cv2.destroyAllWindows()

    def _draw_hud(
        self,
        img: np.ndarray,
        curr_frame: int,
        total_frames: int,
        target_fps: float,
        actual_fps: float,
        w: int,
        h: int,
    ) -> None:
        """Draws a clean, non-intrusive HUD overlay."""
        # Top banner
        status_text = "RECONSTRUCTION: ACTIVE (ON-THE-FLY)" if self.reconstruct_active else "RECONSTRUCTION: BYPASS (RAW INPUT)"
        status_color = (0, 230, 115) if self.reconstruct_active else (50, 150, 255)

        overlay = img.copy()
        cv2.rectangle(overlay, (15, 15), (420, 105), (20, 20, 20), -1)
        cv2.addWeighted(overlay, 0.75, img, 0.25, 0, img)

        cv2.putText(img, status_text, (25, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.52, status_color, 2)

        fps_text = f"FPS: {actual_fps:.1f} / {target_fps:.0f} | Res: {w}x{h}"
        cv2.putText(img, fps_text, (25, 65), cv2.FONT_HERSHEY_SIMPLEX, 0.48, (220, 220, 220), 1)

        pct = (curr_frame / total_frames * 100) if total_frames > 0 else 0
        state = "PAUSED" if self.is_paused else "PLAYING"
        progress_text = f"Frame: {curr_frame}/{total_frames} ({pct:.1f}%) | [{state}]"
        cv2.putText(img, progress_text, (25, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.48, (180, 180, 180), 1)

    @classmethod
    def play_isolated_mpv(cls, video_path: str) -> None:
        """
        Launches an isolated MPV playback instance with the Video-Compress GPU shader.
        Uses --no-config so it NEVER alters or interferes with the host system's player.
        """
        import shutil
        import subprocess

        mpv_bin = shutil.which("mpv") or r"C:\Users\User\AppData\Local\RMN-Player\mpv.com"
        if not os.path.exists(mpv_bin) and not shutil.which("mpv"):
            print("[ERROR] MPV binary not found. Falling back to built-in OpenCV player.")
            player = cls()
            player.play(video_path)
            return

        pkg_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        shader_file = os.path.join(pkg_dir, "plugins", "mpv", "video_compress_reconstruct.hook")
        script_file = os.path.join(pkg_dir, "plugins", "mpv", "video_compress.lua")

        cmd = [
            mpv_bin,
            "--no-config",
            f"--scripts={script_file}",
            f"--glsl-shaders={shader_file}",
            video_path,
        ]
        print(f"[PLAYER] Launching isolated MPV runner (0% interference with system player)...")
        subprocess.run(cmd)

