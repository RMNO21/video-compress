# 🗜️ Video-Compress

<p align="center">
  <b>Smart Temporal & Spatial Video Compression Algorithm using Alternating Checkerboard Reconstruction</b>
  <br/>
  <i>Developed by <a href="https://github.com/RMNO21">RMNO21</a></i>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.8%2B-blue?style=for-the-badge&logo=python&logoColor=white" alt="Python 3.8+" />
  <img src="https://img.shields.io/badge/OpenCV-Computer%20Vision-5C3EE8?style=for-the-badge&logo=opencv&logoColor=white" alt="OpenCV" />
  <img src="https://img.shields.io/badge/NumPy-Vectorized%20Ops-013243?style=for-the-badge&logo=numpy&logoColor=white" alt="NumPy" />
  <a href="https://github.com/RMNO21/video-compress/stargazers"><img src="https://img.shields.io/github/stars/RMNO21/video-compress?style=for-the-badge&color=24292e" alt="Stars" /></a>
  <img src="https://img.shields.io/badge/License-MIT-green?style=for-the-badge" alt="License" />
</p>

---

## 💡 Overview

**Video-Compress** is an experimental computer vision and spatial-temporal compression pipeline. Instead of standard lossy quantization, it leverages an alternating checkerboard pixel decimation technique combined with a 4-neighbor **Selective Mean Filter** to reconstruct high-frequency details with minimal perceptual loss.

### 🧠 How the Algorithm Works:

1. **Checkerboard Decimation**: Each frame is divided into a 2D checkerboard grid of even and odd coordinates.
2. **Temporal Interlacing**: Odd and even pixel sub-grids alternate across successive frames at target frame rates (30+ FPS), taking advantage of human visual persistence (temporal blending).
3. **Selective Mean Edge Reconstruction**: To eliminate halos and blur around sharp edges, the algorithm analyzes the 4 cardinal neighbors (Up, Down, Left, Right), automatically identifies and discards the highest-variance outlier neighbor, and computes the spatial average of the remaining 3 closest pixels.

---

## ✨ Key Features

- ⚡ **High-Speed Vectorized Processing**: Fully vectorized with NumPy matrix rolling and masking operations.
- 🎯 **Edge-Preserving Selective Mean**: Eliminates artifacting and ghosting around high-contrast edges.
- 🔄 **Temporal Alternation**: Preserves motion fidelity without full-frame data duplication.
- 📦 **Minimal Dependencies**: Requires only standard `opencv-python` and `numpy`.

---

## 🚀 Quick Start

### 1. Prerequisites & Installation

Clone the repository and install the dependencies:

```bash
git clone https://github.com/RMNO21/video-compress.git
cd video-compress
pip install opencv-python numpy
```

### 2. Run the Compression Script

```bash
python pixel.py
```

When prompted, enter the full path to your source video file:
```text
Video File Path: "C:\path\to\your\video.mp4"
```

The script will process each frame with a live progress indicator and save the reconstructed output as `processed_pixel_video.mp4` in the same directory.

---

## 📊 Pipeline Comparison

| Step | Technique | Visual Effect |
| :--- | :--- | :--- |
| **Stage 1** | Checkerboard Decimation | Reduces per-frame pixel payload |
| **Stage 2** | 4-Neighbor Outlier Rejection | Discards boundary noise |
| **Stage 3** | Tri-Neighbor Interpolation | Reconstructs missing pixel coordinates |
| **Stage 4** | Temporal Frame Alternation | Leverages persistence of vision |

---

## ⭐ Support the Project

If you find this computer vision experiment interesting, please consider giving it a **Star** ⭐!  
Contributions, optimizations, and PRs are always welcome.

---

## 📜 License

MIT License © [RMNO21](https://github.com/RMNO21)
