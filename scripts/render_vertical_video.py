#!/usr/bin/env python3
"""Render a vertical 9:16 video using local Polish Piper TTS and FFmpeg.

No paid API or unlicensed music is required. A supplied music file is accepted
only when an explicit license reference is provided.
"""
from __future__ import annotations

import argparse
import json
import math
import re
import shutil
import subprocess
import sys
import textwrap
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


WIDTH = 1080
HEIGHT = 1920
FPS = 30
VOICE = "pl_PL-darkman-medium"
FONT = "/usr/share/fonts/truetype/noto/NotoSans-Bold.ttf"


def run(command: list[str]) -> str:
    completed = subprocess.run(command, check=True, text=True, capture_output=True)
    return completed.stdout.strip()


def write_gradient(path: Path) -> None:
    """Create a lightweight PPM background using only the Python standard library."""
    data = bytearray()
    for y in range(HEIGHT):
        vy = y / max(1, HEIGHT - 1)
        for x in range(WIDTH):
            vx = x / max(1, WIDTH - 1)
            glow = max(0.0, 1.0 - math.sqrt(((vx - 0.78) / 0.72) ** 2 + ((vy - 0.18) / 0.45) ** 2))
            r = int(7 + 10 * (1 - vy) + 10 * glow)
            g = int(12 + 18 * (1 - vy) + 24 * glow)
            b = int(31 + 42 * (1 - vy) + 55 * glow)
            data.extend((min(r, 255), min(g, 255), min(b, 255)))
    path.write_bytes(f"P6\n{WIDTH} {HEIGHT}\n255\n".encode("ascii") + data)


def srt_time(seconds: float) -> str:
    millis = max(0, round(seconds * 1000))
    hours, remainder = divmod(millis, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    secs, millis = divmod(remainder, 1000)
    return f"{hours:02}:{minutes:02}:{secs:02},{millis:03}"


def make_captions(script: str, duration: float, path: Path) -> list[tuple[str, float, float]]:
    sentences = [part.strip() for part in re.split(r"(?<=[.!?])\s+", script) if part.strip()]
    if not sentences:
        raise ValueError("script_has_no_caption_sentences")
    weights = [max(1, len(sentence.split())) for sentence in sentences]
    total_weight = sum(weights)
    usable = max(1.0, duration - 0.4)
    cursor = 0.0
    rows = []
    segments = []
    for index, (sentence, weight) in enumerate(zip(sentences, weights), start=1):
        span = usable * weight / total_weight
        start = cursor
        end = min(duration, cursor + span)
        rows.append(f"{index}\n{srt_time(start)} --> {srt_time(end)}\n{sentence}\n")
        segments.append((sentence, start, end))
        cursor = end
    path.write_text("\n".join(rows), encoding="utf-8")
    return segments


def make_text_overlay(
    text: str,
    path: Path,
    font_path: str,
    font_size: int,
    wrap_width: int,
    padding: int = 26,
) -> None:
    font = ImageFont.truetype(font_path, font_size)
    wrapped = textwrap.fill(text, width=wrap_width)
    probe = Image.new("RGBA", (8, 8), (0, 0, 0, 0))
    draw = ImageDraw.Draw(probe)
    bbox = draw.multiline_textbbox((0, 0), wrapped, font=font, spacing=14, align="center")
    width = math.ceil(bbox[2] - bbox[0]) + padding * 2
    height = math.ceil(bbox[3] - bbox[1]) + padding * 2
    canvas = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)
    draw.rounded_rectangle(
        (0, 0, width - 1, height - 1),
        radius=22,
        fill=(0, 0, 0, 178),
    )
    draw.multiline_text(
        (padding - bbox[0], padding - bbox[1]),
        wrapped,
        font=font,
        fill=(255, 255, 255, 255),
        spacing=14,
        align="center",
    )
    canvas.save(path, format="PNG")


def probe_duration(path: Path) -> float:
    value = run([
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", str(path)
    ])
    return float(value)


def render(args: argparse.Namespace) -> dict:
    for tool in ("ffmpeg", "ffprobe"):
        if not shutil.which(tool):
            raise RuntimeError(f"missing_tool:{tool}")

    source = json.loads(args.input.read_text(encoding="utf-8"))
    title = str(source.get("title", "")).strip()
    script = str(source.get("script", "")).strip()
    cta = str(source.get("cta", "")).strip()
    if not title or not script or not cta:
        raise ValueError("input_requires_title_script_cta")

    music_license_ref = args.music_license_ref or str(source.get("music_license_ref", "")).strip()
    music_required = bool(source.get("music_required", False)) or (
        source.get("platform") == "tiktok" and source.get("format") == "video"
    )
    if music_required and not args.music:
        raise ValueError("licensed_music_required")
    if args.music:
        if not args.music.is_file():
            raise FileNotFoundError(args.music)
        if not music_license_ref:
            raise ValueError("music_license_reference_required")

    workdir = args.output.parent
    workdir.mkdir(parents=True, exist_ok=True)
    voice_dir = args.voice_dir.resolve()
    voice_dir.mkdir(parents=True, exist_ok=True)
    narration = workdir / "narration.wav"
    captions_srt = workdir / "captions.srt"
    background = workdir / "background.ppm"

    if args.background:
        if not args.background.is_file():
            raise FileNotFoundError(args.background)
        background = args.background.resolve()
    else:
        write_gradient(background)

    run([
        sys.executable, "-m", "piper", "-m", args.voice,
        "--data-dir", str(voice_dir), "-f", str(narration), "--", script
    ])
    duration = probe_duration(narration)
    if duration < 5 or duration > 90:
        raise ValueError(f"narration_duration_out_of_range:{duration:.2f}")
    segments = make_captions(script, duration, captions_srt)

    title_overlay = workdir / "title.png"
    cta_overlay = workdir / "cta.png"
    make_text_overlay(title, title_overlay, FONT, 58, 24)
    make_text_overlay(cta, cta_overlay, FONT, 40, 28)

    caption_overlays: list[tuple[Path, float, float]] = []
    for index, (sentence, start, end) in enumerate(segments, start=1):
        caption_path = workdir / f"caption_{index:02}.png"
        make_text_overlay(sentence, caption_path, FONT, 48, 28)
        caption_overlays.append((caption_path, start, end))

    command = [
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
        "-loop", "1", "-framerate", str(FPS), "-i", str(background),
        "-i", str(narration),
    ]
    if args.music:
        command += ["-stream_loop", "-1", "-i", str(args.music)]

    overlay_paths = [title_overlay] + [item[0] for item in caption_overlays] + [cta_overlay]
    for overlay_path in overlay_paths:
        command += ["-loop", "1", "-framerate", str(FPS), "-i", str(overlay_path)]

    overlay_input_index = 3 if args.music else 2
    filters = [
        f"[0:v]scale={WIDTH}:{HEIGHT}:force_original_aspect_ratio=increase,"
        f"crop={WIDTH}:{HEIGHT},"
        f"zoompan=z='min(zoom+0.00035,1.06)':d=1:s={WIDTH}x{HEIGHT}:fps={FPS}[base0]"
    ]
    current = "base0"

    filters.append(f"[{overlay_input_index}:v]format=rgba[title]")
    filters.append(f"[{current}][title]overlay=(W-w)/2:125:shortest=1[base1]")
    current = "base1"
    overlay_input_index += 1

    for index, (caption_path, start, end) in enumerate(caption_overlays, start=1):
        label = f"caption{index}"
        next_base = f"base{index + 1}"
        filters.append(f"[{overlay_input_index}:v]format=rgba[{label}]")
        filters.append(
            f"[{current}][{label}]overlay=(W-w)/2:(H-h)/2:"
            f"enable='between(t\\,{start:.3f}\\,{end:.3f})':shortest=1[{next_base}]"
        )
        current = next_base
        overlay_input_index += 1

    filters.append(f"[{overlay_input_index}:v]format=rgba[cta]")
    filters.append(f"[{current}][cta]overlay=(W-w)/2:H-h-230:shortest=1[v]")

    if args.music:
        filters.extend([
            "[1:a]loudnorm=I=-16:TP=-1.5:LRA=11[voice]",
            "[2:a]volume=0.10[music]",
            "[voice][music]amix=inputs=2:duration=first:dropout_transition=2,"
            "aresample=48000,aformat=channel_layouts=stereo[a]",
        ])
    else:
        filters.append(
            "[1:a]loudnorm=I=-16:TP=-1.5:LRA=11,aresample=48000,"
            "aformat=channel_layouts=stereo[a]"
        )

    command += [
        "-filter_complex", ";".join(filters),
        "-map", "[v]", "-map", "[a]",
        "-t", f"{duration:.3f}", "-r", str(FPS),
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "21",
        "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k",
        "-ar", "48000", "-ac", "2", "-movflags", "+faststart",
        str(args.output)
    ]
    run(command)

    streams = json.loads(run([
        "ffprobe", "-v", "error", "-show_entries",
        "stream=codec_type,codec_name,width,height,sample_rate,channels",
        "-of", "json", str(args.output)
    ]))
    video = next((s for s in streams.get("streams", []) if s.get("codec_type") == "video"), {})
    audio = next((s for s in streams.get("streams", []) if s.get("codec_type") == "audio"), {})
    if (video.get("width"), video.get("height"), video.get("codec_name")) != (WIDTH, HEIGHT, "h264"):
        raise RuntimeError("video_output_validation_failed")
    if audio.get("codec_name") != "aac" or audio.get("sample_rate") != "48000" or audio.get("channels") != 2:
        raise RuntimeError("audio_output_validation_failed")

    return {
        "output": str(args.output),
        "duration_seconds": round(probe_duration(args.output), 2),
        "width": video["width"],
        "height": video["height"],
        "video_codec": video["codec_name"],
        "audio_codec": audio["codec_name"],
        "sample_rate": audio["sample_rate"],
        "channels": audio["channels"],
        "voice": args.voice,
        "music_included": bool(args.music),
        "music_license_ref": music_license_ref if args.music else None,
        "file_bytes": args.output.stat().st_size,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--voice", default=VOICE)
    parser.add_argument("--voice-dir", type=Path, default=Path("voices"))
    parser.add_argument("--background", type=Path)
    parser.add_argument("--music", type=Path)
    parser.add_argument("--music-license-ref", default="")
    args = parser.parse_args()
    print(json.dumps(render(args), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
