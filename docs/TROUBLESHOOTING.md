# Video-Compress Troubleshooting

## 1. NVENC Session Limit Error
- **Symptom**: `Cannot open video encoder: Function not implemented`.
- **Solution**: Consume driver patches for consumer GeForce GPUs or fallback to CPU encoding.

## 2. Audio Desynchronization
- **Cause**: Variable Frame Rate (VFR) in mobile phone recordings.
- **Solution**: Pass `-vsync cfr` to force constant frame rate output.
