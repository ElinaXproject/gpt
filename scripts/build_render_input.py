#!/usr/bin/env python3
"""Convert an approved D1 draft's structured script into the local FFmpeg renderer input."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from autored.d1_client import D1Client, D1Error


PROFILE_RENDER_SETTINGS = {
    "tiktok_pieknemedia": {"theme": "humor", "platform": "tiktok", "cta": "Obserwuj po więcej humoru"},
    "tiktok_ocenionona6": {"theme": "education", "platform": "tiktok", "cta": "Obserwuj po więcej wiedzy"},
    "youtube_memoryagent": {"theme": "tech", "platform": "youtube", "cta": "Subskrybuj Memory Agent"},
}


def build_render_input(d1: D1Client, content_id: str, profile_id: str) -> dict:
    settings = PROFILE_RENDER_SETTINGS.get(profile_id)
    if not settings:
        raise ValueError("unsupported_render_profile")
    item = d1.get_content_item_for_render(content_id, profile_id)
    script_data = item["script_data"]
    voiceover = str(script_data.get("voiceover_text") or "").strip()
    title = str(item.get("title") or "").strip()
    if not title or not voiceover:
        raise ValueError("render_input_missing_title_or_voiceover")
    return {
        "title": title,
        "script": voiceover,
        "cta": settings["cta"],
        "theme": settings["theme"],
        "platform": settings["platform"],
        "format": "video",
        "music_required": settings["platform"] == "tiktok",
        "content_id": content_id,
        "profile_id": profile_id,
        "visual_direction": str(script_data.get("visual_direction") or ""),
        "target_duration_seconds": script_data.get("duration_seconds"),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--content-id", required=True)
    parser.add_argument("--profile-id", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        render_input = build_render_input(D1Client(), args.content_id, args.profile_id)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(render_input, ensure_ascii=False, indent=2), encoding="utf-8")
    except (OSError, ValueError, D1Error) as exc:
        code = getattr(exc, "code", str(exc))
        print(json.dumps({"status": "blocked", "error": str(code)[:120]}, ensure_ascii=False))
        return 2
    print(json.dumps({"status": "render_input_created", "output": str(args.output), "content_id": args.content_id}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
