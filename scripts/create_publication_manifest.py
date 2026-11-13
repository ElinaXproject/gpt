#!/usr/bin/env python3
"""Build a provider-specific publication manifest from a fully reviewed D1 content item."""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Any

from autored.d1_client import D1Client, D1Error
from autored.media_validation import MediaValidationError, sha256_file, validate_tiktok_video, validate_youtube_video


def _scheduled_at(value: str) -> str:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        raise ValueError("scheduled_at_invalid") from None
    if parsed.tzinfo is None:
        raise ValueError("scheduled_at_timezone_missing")
    return parsed.isoformat(timespec="seconds")


def _hashtags(item: dict[str, Any]) -> list[str]:
    try:
        values = json.loads(str(item.get("hashtags_json") or "[]"))
    except json.JSONDecodeError:
        raise ValueError("hashtags_invalid_json") from None
    if not isinstance(values, list) or any(not isinstance(value, str) for value in values):
        raise ValueError("hashtags_invalid")
    result = []
    for value in values:
        tag = value.strip().lstrip("#")
        if tag and tag not in result:
            result.append(tag)
    return result[:30]


def build_manifest(
    *,
    d1: D1Client,
    content_id: str,
    profile_id: str,
    provider: str,
    media_path: Path,
    scheduled_at: str,
    privacy_level: str = "SELF_ONLY",
    made_for_kids: bool | None = None,
) -> dict[str, Any]:
    if provider not in {"tiktok_direct", "youtube_direct"}:
        raise ValueError("unsupported_native_provider")
    scheduled = _scheduled_at(scheduled_at)
    item = d1.get_publishable_content(content_id, profile_id, provider)
    if not media_path.is_file():
        raise MediaValidationError("file_missing_or_empty")
    digest = sha256_file(media_path)
    size = media_path.stat().st_size
    if digest != item.get("media_sha256") or size != item.get("media_bytes"):
        raise D1Error("media_metadata_mismatch")
    if item.get("media_mime") != "video/mp4":
        raise D1Error("media_mime_invalid")
    hashtags = _hashtags(item)
    title = str(item.get("title") or "").strip()
    description = str(item.get("description") or "").strip()
    ai_generated = bool(item.get("ai_disclosure_required") == 1 or item.get("ai_disclosure_set") == 1)
    idempotency_key = hashlib.sha256(
        f"{content_id}|{profile_id}|{provider}|{scheduled}".encode("utf-8")
    ).hexdigest()

    if provider == "tiktok_direct":
        if privacy_level not in {
            "SELF_ONLY", "PUBLIC_TO_EVERYONE", "MUTUAL_FOLLOW_FRIENDS", "FOLLOWER_OF_CREATOR"
        }:
            raise ValueError("tiktok_privacy_level_invalid")
        media = validate_tiktok_video(media_path)
        caption = description
        if hashtags:
            caption = (caption + "\n" + " ".join("#" + tag for tag in hashtags)).strip()
        if not caption or len(caption) > 2200:
            raise ValueError("tiktok_caption_length_invalid")
        return {
            "content_id": content_id,
            "profile_id": profile_id,
            "scheduled_at": scheduled,
            "idempotency_key": idempotency_key,
            "caption": caption,
            "duration_seconds": int(media["duration_seconds"] + 0.999),
            "privacy_level": privacy_level,
            "music_embedded": item.get("music_embedded") == 1,
            "music_license_reference": str(item.get("music_license_reference") or ""),
            "ai_generated": ai_generated,
            "media_sha256": digest,
            "media_bytes": size,
            "media_mime": "video/mp4",
        }

    if made_for_kids is None:
        raise ValueError("youtube_audience_classification_required")
    if not title or len(title) > 100 or len(description) > 5000:
        raise ValueError("youtube_metadata_length_invalid")
    media = validate_youtube_video(media_path, format_type="longform")
    format_type = "short" if media["height"] > media["width"] and media["duration_seconds"] <= 180 else "longform"
    if format_type == "short":
        validate_youtube_video(media_path, format_type="short")
    return {
        "content_id": content_id,
        "profile_id": profile_id,
        "scheduled_at": scheduled,
        "idempotency_key": idempotency_key,
        "title": title,
        "description": description,
        "tags": hashtags,
        "made_for_kids": made_for_kids,
        "ai_generated": ai_generated,
        "media_sha256": digest,
        "media_bytes": size,
        "media_mime": "video/mp4",
        "format_type": format_type,
        "category_id": "28",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--content-id", required=True)
    parser.add_argument("--profile-id", required=True)
    parser.add_argument("--provider", choices=("tiktok_direct", "youtube_direct"), required=True)
    parser.add_argument("--media", type=Path, required=True)
    parser.add_argument("--scheduled-at", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--privacy-level", default="SELF_ONLY")
    parser.add_argument("--audience-classification", choices=("made_for_kids", "not_made_for_kids"))
    args = parser.parse_args()
    try:
        manifest = build_manifest(
            d1=D1Client(),
            content_id=args.content_id,
            profile_id=args.profile_id,
            provider=args.provider,
            media_path=args.media,
            scheduled_at=args.scheduled_at,
            privacy_level=args.privacy_level,
            made_for_kids=None if args.audience_classification is None else args.audience_classification == "made_for_kids",
        )
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    except (OSError, ValueError, D1Error, MediaValidationError) as exc:
        code = getattr(exc, "code", str(exc))
        print(json.dumps({"status": "blocked", "error": str(code)[:120]}, ensure_ascii=False))
        return 2
    print(json.dumps({"status": "manifest_created", "output": str(args.output), "content_id": args.content_id}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
