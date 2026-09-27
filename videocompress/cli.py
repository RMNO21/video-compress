"""
Command-Line Interface (CLI) for Video-Compress v2.0.
Supports encode (Mode 1), play (Mode 2), install-plugin, and benchmark.
"""
import argparse
import sys
import os
import subprocess
import time
import numpy as np

from .modes.encoder import VideoEncoder
from .modes.player import VideoPlayer
from .core.filter import SelectiveMeanReconstructor, DirectionalEdgeReconstructor
from .core.checkerboard import CheckerboardMaskGenerator
from .core.hw_accel import HardwareEngine


def run_benchmark(input_path: str = None) -> None:
    """Runs performance benchmarks comparing baseline vs. vectorized filters."""
    print("\n========================================================")
    print("       VIDEO-COMPRESS ALGORITHMIC BENCHMARK SUITE       ")
    print("========================================================")

    best_enc, codec, accel = HardwareEngine.select_best_encoder("av1")
    print(f"Hardware Status:  {accel}")
    print(f"Detected Encoder: {best_enc} ({codec})")

    resolutions = [
        ("720p (HD)", 720, 1280),
        ("1080p (Full HD)", 1080, 1920),
    ]

    for name, h, w in resolutions:
        print(f"\n--- Testing Resolution: {name} ({w}x{h}) ---")
        img = np.random.randint(0, 255, (h, w, 3), dtype=np.uint8)
        mask = CheckerboardMaskGenerator.get_mask(h, w)

        # 1. Baseline np.roll simulation
        t0 = time.time()
        img_f = img.astype(np.float32)
        up = np.roll(img_f, -1, axis=0)
        down = np.roll(img_f, 1, axis=0)
        left = np.roll(img_f, -1, axis=1)
        right = np.roll(img_f, 1, axis=1)
        mean_all = (up + down + left + right) / 4.0
        t_base = (time.time() - t0) * 1000

        # 2. Vectorized Selective Mean (Fast)
        sm_fast = SelectiveMeanReconstructor(mode="fast")
        t0 = time.time()
        for _ in range(3):
            _ = sm_fast.reconstruct(img, 0, mask=mask)
        t_sm_fast = ((time.time() - t0) / 3.0) * 1000

        # 3. Directional Edge-Preserving Filter
        dir_filter = DirectionalEdgeReconstructor(threshold=10)
        t0 = time.time()
        for _ in range(3):
            _ = dir_filter.reconstruct(img, 0, mask=mask)
        t_dir = ((time.time() - t0) / 3.0) * 1000

        print(f"  Baseline (np.roll):              {t_base:.2f} ms ({1000/t_base:.1f} FPS)")
        print(f"  Vectorized Selective Mean:       {t_sm_fast:.2f} ms ({1000/t_sm_fast:.1f} FPS) -> [{t_base/t_sm_fast:.1f}x Faster]")
        print(f"  Adaptive Directional Filter:     {t_dir:.2f} ms ({1000/t_dir:.1f} FPS)")

    print("\nBenchmark completed.\n")


def install_plugin() -> None:
    """Launches the MPV plugin installer."""
    pkg_dir = os.path.dirname(os.path.abspath(__file__))
    repo_dir = os.path.dirname(pkg_dir)
    ps_installer = os.path.join(repo_dir, "plugins", "mpv", "install_mpv_plugin.ps1")
    if os.path.exists(ps_installer):
        subprocess.run(["powershell.exe", "-ExecutionPolicy", "Bypass", "-File", ps_installer])
    else:
        print("[ERROR] Plugin installer script not found.")


def interactive_menu() -> None:
    """Presents an interactive menu when invoked without CLI arguments."""
    while True:
        print("\n" + "=" * 55)
        print("          🗜️  VIDEO-COMPRESS (v2.0.0)  🗜️          ")
        print("=" * 55)
        best_enc, _, accel = HardwareEngine.select_best_encoder("av1")
        print(f"Hardware Accel: {accel} [{best_enc}]")
        print("-" * 55)
        print("Select operational mode:")
        print("  [1] Encode & Prepare Video (Mode 1: Transform)")
        print("  [2] Real-time Interactive Player (Mode 2: Playback)")
        print("  [3] Install MPV / Player Plugin (GPU Shader)")
        print("  [4] Run Algorithmic Benchmarks")
        print("  [5] Exit")
        print("=" * 55)

        choice = input("Enter choice (1-5): ").strip()

        if choice == "1":
            path = input("Enter input video path: ").strip('"').strip("'")
            if not os.path.exists(path):
                print(f"[ERROR] File not found: {path}")
                continue
            encoder = VideoEncoder(codec="av1", preset="balanced", filter_type="directional")
            encoder.encode(path)

        elif choice == "2":
            path = input("Enter video path to play: ").strip('"').strip("'")
            if not os.path.exists(path):
                print(f"[ERROR] File not found: {path}")
                continue
            player = VideoPlayer(filter_type="directional")
            player.play(path)

        elif choice == "3":
            install_plugin()

        elif choice == "4":
            run_benchmark()

        elif choice in ("5", "q", "exit"):
            print("Exiting Video-Compress. Goodbye!")
            sys.exit(0)
        else:
            print("Invalid option. Please enter 1 to 5.")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Video-Compress: High-Performance Spatial-Temporal Compression, Playback & Plugin Suite.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Mode 1: Encode video with hardware AV1/HEVC
  python -m videocompress encode input.mp4 -o output.mp4 --codec av1 --crf 24

  # Mode 2: Real-time playback with on-the-fly reconstruction
  python -m videocompress play compressed.mp4

  # Install MPV / RMN-Player GPU shader plugin
  python -m videocompress install-plugin

  # Run benchmark
  python -m videocompress benchmark
        """,
    )

    subparsers = parser.add_subparsers(dest="command", help="Operational mode")

    # Encode subparser
    enc_parser = subparsers.add_parser("encode", help="Mode 1: Transform and compress video")
    enc_parser.add_argument("input", help="Path to input video file")
    enc_parser.add_argument("-o", "--output", help="Path to output video file")
    enc_parser.add_argument("--codec", default="av1", choices=["av1", "hevc", "h264"], help="Target video codec")
    enc_parser.add_argument("--preset", default="balanced", choices=["ultra_fast", "balanced", "max_compression"], help="Compression preset")
    enc_parser.add_argument("--filter", default="directional", choices=["directional", "selective_mean"], help="Reconstruction filter")
    enc_parser.add_argument("--crf", type=int, default=24, help="Constant Rate Factor (18-32)")
    enc_parser.add_argument("--scale", type=float, default=1.0, help="Downscale factor (e.g. 0.75)")

    # Play subparser
    play_parser = subparsers.add_parser("play", help="Mode 2: Real-time interactive playback")
    play_parser.add_argument("input", help="Path to video file to play")
    play_parser.add_argument("--fps", type=float, help="Target playback frame rate")
    play_parser.add_argument("--filter", default="directional", choices=["directional", "selective_mean"], help="Filter algorithm")

    # Install plugin subparser
    subparsers.add_parser("install-plugin", help="Install MPV / RMN-Player GPU shader plugin")

    # Benchmark subparser
    subparsers.add_parser("benchmark", help="Run algorithmic performance benchmarks")

    args = parser.parse_args()

    if not args.command:
        interactive_menu()
        return

    if args.command == "encode":
        encoder = VideoEncoder(
            codec=args.codec,
            preset=args.preset,
            filter_type=args.filter,
            crf=args.crf,
            scale=args.scale,
        )
        encoder.encode(args.input, args.output)
    elif args.command == "play":
        player = VideoPlayer(filter_type=args.filter)
        player.play(args.input, target_fps=args.fps)
    elif args.command == "install-plugin":
        install_plugin()
    elif args.command == "benchmark":
        run_benchmark()


if __name__ == "__main__":
    main()
