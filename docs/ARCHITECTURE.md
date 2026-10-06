# Video Compression Architecture

## 1. Pipeline Overview
Automated batch video transcode pipeline utilizing FFmpeg with perceptually optimized Constant Rate Factor (CRF) scaling.

## 2. Encoding Flow
- **Phase 1**: Source probe via `ffprobe` to determine codec, container, bitrate, and audio streams.
- **Phase 2**: Hardware acceleration detection (NVENC / QSV / AMF fallback to software libx264/libx265).
- **Phase 3**: Two-pass audio normalization (EBU R128 loudness target).
- **Phase 4**: Atomic transcode write and temporary cache eviction.
