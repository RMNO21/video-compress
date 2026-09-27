"""
Hardware Acceleration Engine for Video-Compress.
Detects available GPU encoders (Intel Arc QSV, NVIDIA NVENC, AMD AMF, CPU SVT-AV1/x265)
and builds optimal low-latency, high-efficiency FFmpeg command lines.
"""
import shutil
import subprocess
from typing import Dict, List, Optional, Tuple


class HardwareEngine:
    """
    Auto-detects GPU hardware capabilities and constructs optimized encoder pipelines.
    """

    SUPPORTED_CODECS = {
        "av1": ["av1_qsv", "av1_nvenc", "av1_amf", "libsvtav1"],
        "hevc": ["hevc_qsv", "hevc_nvenc", "hevc_amf", "libx265"],
        "h264": ["h264_qsv", "h264_nvenc", "h264_amf", "libx264"],
    }

    _detected_encoders: Optional[List[str]] = None
    _ffmpeg_path: Optional[str] = None

    @classmethod
    def get_ffmpeg_path(cls) -> str:
        if cls._ffmpeg_path is None:
            found = shutil.which("ffmpeg") or r"C:\msys64\mingw64\bin\ffmpeg.exe"
            cls._ffmpeg_path = found
        return cls._ffmpeg_path

    @classmethod
    def get_available_encoders(cls) -> List[str]:
        """Queries FFmpeg to discover all compiled and active video encoders."""
        if cls._detected_encoders is not None:
            return cls._detected_encoders

        ffmpeg_bin = cls.get_ffmpeg_path()
        try:
            res = subprocess.run(
                [ffmpeg_bin, "-encoders"],
                capture_output=True,
                text=True,
                check=True,
            )
            cls._detected_encoders = [
                line.split()[1]
                for line in res.stdout.splitlines()
                if line.strip().startswith("V") and len(line.split()) >= 2
            ]
        except Exception:
            cls._detected_encoders = ["libx264"]

        return cls._detected_encoders

    @classmethod
    def select_best_encoder(cls, preferred_codec: str = "av1") -> Tuple[str, str, str]:
        """
        Selects the highest performing encoder available for the system.
        Returns:
            (encoder_name, codec_format, acceleration_type)
        """
        available = cls.get_available_encoders()
        candidates = cls.SUPPORTED_CODECS.get(preferred_codec, [])

        for enc in candidates:
            if enc in available:
                if "qsv" in enc:
                    return enc, preferred_codec, "Intel Arc QSV (Hardware)"
                elif "nvenc" in enc:
                    return enc, preferred_codec, "NVIDIA NVENC (Hardware)"
                elif "amf" in enc:
                    return enc, preferred_codec, "AMD AMF (Hardware)"
                elif "svt" in enc or "x26" in enc:
                    return enc, preferred_codec, "Multi-Threaded CPU (Software)"

        # Fallback to H.264
        return "libx264", "h264", "Standard CPU (libx264)"

    @classmethod
    def build_encoding_args(
        cls,
        encoder: str,
        crf: int = 24,
        preset: str = "balanced",
    ) -> List[str]:
        """
        Generates finely-tuned parameters for the selected encoder.
        """
        args = ["-c:v", encoder]

        if "qsv" in encoder:
            # Intel Arc QuickSync Video parameters
            qsv_preset = "faster" if preset == "ultra_fast" else "medium"
            args.extend([
                "-preset", qsv_preset,
                "-global_quality", str(crf),
                "-look_ahead", "1",
                "-look_ahead_depth", "40",
            ])
        elif "nvenc" in encoder:
            # NVIDIA NVENC parameters
            nv_preset = "p4" if preset == "ultra_fast" else "p6"
            args.extend([
                "-preset", nv_preset,
                "-cq", str(crf),
                "-spatial-aq", "1",
                "-temporal-aq", "1",
            ])
        elif "amf" in encoder:
            # AMD AMF parameters
            args.extend([
                "-usage", "transcoding",
                "-rc", "cqp",
                "-qp_p", str(crf),
                "-qp_i", str(crf),
            ])
        elif "svtav1" in encoder:
            # Scalable Video Technology AV1
            svt_preset = "8" if preset == "ultra_fast" else "6"
            args.extend([
                "-preset", svt_preset,
                "-crf", str(crf),
                "-svtav1-params", "tune=0:fast-decode=1",
            ])
        else:
            # libx265 / libx264
            x_preset = "veryfast" if preset == "ultra_fast" else "medium"
            args.extend([
                "-preset", x_preset,
                "-crf", str(crf),
            ])

        return args
