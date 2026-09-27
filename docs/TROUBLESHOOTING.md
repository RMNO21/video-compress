# 🛠️ Video-Compress Troubleshooting Guide

## 1. FFmpeg Not Detected
**Issue**: `RuntimeError: FFmpeg binary not found.`  
**Solution**:
- Ensure FFmpeg is installed and added to your system `PATH`.
- On Windows, install via `winget install Gyan.FFmpeg` or `choco install ffmpeg`.

## 2. Hardware Acceleration Fallback
**Issue**: Warning message indicating encoder fallback: `[WARN] Hardware encoder av1_qsv reported error... Falling back to libx264.`  
**Solution**:
- Verify GPU drivers are up to date (Intel Arc driver 32.0+ or NVIDIA driver 530+).
- Use `--codec hevc` or `--codec h264` if your GPU does not support AV1 hardware encoding.

## 3. MPV Plugin Not Triggering
**Issue**: Pressing `Ctrl + V` inside MPV does not display the OSD message.  
**Solution**:
- Run `python -m videocompress install-plugin` to verify scripts are placed into `%APPDATA%\mpv\scripts\` and shaders into `%APPDATA%\mpv\shaders\`.
- Check MPV log by launching MPV from terminal: `mpv --msg-level=all=v video.mp4`.
