"""Media integrity checks before social-platform upload."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any, Callable


class MediaValidationError(RuntimeError):
    def __init__(self, code: str):
        self.code = code
        super().__init__("media_" + code)


def probe_media(path: Path, runner: Callable[..., Any] = subprocess.run) -> dict[str, Any]:
    if not path.is_file() or path.stat().st_size <= 0:
        raise MediaValidationError("file_missing_or_empty")
    try:
        result = runner(
            ["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", str(path)],
            check=True,
            capture_output=True,
            text=True,
            timeout=30,
        )
    except FileNotFoundError:
        raise MediaValidationError("ffprobe_unavailable") from None
    except subprocess.TimeoutExpired:
        raise MediaValidationError("probe_timeout") from None
    except subprocess.CalledProcessError:
        raise MediaValidationError("probe_failed") from None
    try:
        return json.loads(result.stdout)
    except (TypeError, json.JSONDecodeError):
        raise MediaValidationError("invalid_probe_json") from None


def validate_tiktok_video(path: Path, runner: Callable[..., Any] = subprocess.run) -> dict[str, Any]:
    probe = probe_media(path, runner)
    streams = probe.get("streams", [])
    video = next((item for item in streams if item.get("codec_type") == "video"), None)
    audio = next((item for item in streams if item.get("codec_type") == "audio"), None)
    if not video:
        raise MediaValidationError("video_stream_missing")
    if not audio:
        raise MediaValidationError("audio_stream_missing")
    width, height = video.get("width"), video.get("height")
    if not isinstance(width, int) or not isinstance(height, int) or width < 720 or height < 1280:
        raise MediaValidationError("resolution_below_minimum")
    ratio = width / height
    if not 0.54 <= ratio <= 0.60:
        raise MediaValidationError("vertical_aspect_ratio_required")
    if video.get("codec_name") != "h264":
        raise MediaValidationError("h264_required")
    if audio.get("codec_name") != "aac" or str(audio.get("sample_rate")) != "48000" or audio.get("channels") != 2:
        raise MediaValidationError("aac_48khz_stereo_required")
    try:
        duration = float(probe.get("format", {}).get("duration"))
    except (TypeError, ValueError):
        raise MediaValidationError("duration_missing") from None
    if not 5 <= duration <= 90:
        raise MediaValidationError("duration_out_of_tiktok_range")
    return {
        "width": width,
        "height": height,
        "duration_seconds": duration,
        "video_codec": "h264",
        "audio_codec": "aac",
        "sample_rate": 48000,
        "channels": 2,
    }


def validate_youtube_video(path: Path, runner: Callable[..., Any] = subprocess.run, format_type: str = "short") -> dict[str, Any]:
    probe = probe_media(path, runner)
    streams = probe.get("streams", [])
    video = next((item for item in streams if item.get("codec_type") == "video"), None)
    audio = next((item for item in streams if item.get("codec_type") == "audio"), None)
    if not video:
        raise MediaValidationError("video_stream_missing")
    if not audio:
        raise MediaValidationError("audio_stream_missing")
    width, height = video.get("width"), video.get("height")
    if not isinstance(width, int) or not isinstance(height, int) or min(width, height) < 720:
        raise MediaValidationError("resolution_below_minimum")
    ratio = width / height
    if not (0.54 <= ratio <= 0.60 or 1.70 <= ratio <= 1.80):
        raise MediaValidationError("unsupported_aspect_ratio")
    if video.get("codec_name") != "h264":
        raise MediaValidationError("h264_required")
    if audio.get("codec_name") != "aac" or str(audio.get("sample_rate")) != "48000" or audio.get("channels") != 2:
        raise MediaValidationError("aac_48khz_stereo_required")
    try:
        duration = float(probe.get("format", {}).get("duration"))
    except (TypeError, ValueError):
        raise MediaValidationError("duration_missing") from None
    maximum = 180 if format_type == "short" else 3600
    if not 5 <= duration <= maximum:
        raise MediaValidationError("duration_out_of_range")
    return {
        "width": width,
        "height": height,
        "duration_seconds": duration,
        "video_codec": "h264",
        "audio_codec": "aac",
        "sample_rate": 48000,
        "channels": 2,
        "format_type": format_type,
    }
