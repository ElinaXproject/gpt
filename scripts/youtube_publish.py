#!/usr/bin/env python3
"""Upload and schedule one verified YouTube video for the exact Memory Agent channel."""
from __future__ import annotations

import argparse
import hashlib
import json
import mimetypes
from datetime import datetime
from pathlib import Path
from typing import Any

from autored.d1_client import D1Client, D1Error
from autored.media_validation import MediaValidationError, sha256_file, validate_youtube_video
from autored.providers.youtube import EXPECTED_MEMORY_AGENT_CHANNEL_ID, YouTubeError, YouTubeUploader


PROFILE_ID = "youtube_memoryagent"
EXPECTED_HANDLE = "@MemoryAgent-r3c"


def load_manifest(path: Path) -> dict[str, Any]:
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        raise ValueError("manifest_unreadable") from None
    required = {
        "content_id", "profile_id", "scheduled_at", "idempotency_key", "title",
        "description", "tags", "made_for_kids", "ai_generated", "media_sha256",
        "media_bytes", "media_mime", "format_type"
    }
    if not isinstance(manifest, dict) or required - set(manifest):
        raise ValueError("manifest_fields_missing")
    if manifest["profile_id"] != PROFILE_ID:
        raise ValueError("youtube_profile_mismatch")
    if not isinstance(manifest["made_for_kids"], bool) or not isinstance(manifest["ai_generated"], bool):
        raise ValueError("manifest_boolean_invalid")
    try:
        scheduled = datetime.fromisoformat(str(manifest["scheduled_at"]).replace("Z", "+00:00"))
    except ValueError:
        raise ValueError("scheduled_at_invalid") from None
    if scheduled.tzinfo is None:
        raise ValueError("scheduled_at_timezone_missing")
    if manifest["format_type"] not in {"short", "longform"}:
        raise ValueError("format_type_invalid")
    manifest["_scheduled_datetime"] = scheduled
    return manifest


def validate_media_against_d1(d1: D1Client, manifest: dict[str, Any], media_path: Path) -> dict[str, Any]:
    rows = d1.query(
        "SELECT media_sha256, media_bytes, media_mime FROM content_items WHERE id=? AND profile_id=?",
        [manifest["content_id"], PROFILE_ID],
    ).get("results", [])
    if len(rows) != 1:
        raise D1Error("content_media_record_not_found")
    row = rows[0]
    digest = sha256_file(media_path)
    size = media_path.stat().st_size
    mime = mimetypes.guess_type(media_path.name)[0] or "application/octet-stream"
    if digest != row.get("media_sha256") or digest != manifest["media_sha256"]:
        raise D1Error("media_sha256_mismatch")
    if size != row.get("media_bytes") or size != manifest["media_bytes"]:
        raise D1Error("media_size_mismatch")
    if mime != row.get("media_mime") or mime != manifest["media_mime"]:
        raise D1Error("media_mime_mismatch")
    return validate_youtube_video(media_path, format_type=manifest["format_type"])


def run(manifest_path: Path, media_path: Path) -> dict[str, Any]:
    manifest = load_manifest(manifest_path)
    d1 = D1Client()
    validate_media_against_d1(d1, manifest, media_path)
    reservation = d1.reserve_job(
        content_id=manifest["content_id"],
        profile_id=PROFILE_ID,
        scheduled_at=manifest["scheduled_at"],
        idempotency_key=manifest["idempotency_key"],
        provider="youtube_direct",
        media_artifact_id=manifest.get("media_artifact_id"),
    )
    job_id = reservation["job_id"]
    d1.mark_job_publishing(job_id)
    try:
        uploader = YouTubeUploader()
        result = uploader.upload_and_schedule({
            "title": manifest["title"],
            "description": manifest["description"],
            "tags": manifest["tags"],
            "made_for_kids": manifest["made_for_kids"],
            "ai_generated": manifest["ai_generated"],
            "privacy": "public",
            "scheduled_time": manifest["scheduled_at"],
            "category_id": manifest.get("category_id", "28"),
        }, media_path)
    except YouTubeError as exc:
        d1.mark_job_failed(job_id, exc.code, blocked=True)
        raise
    d1.mark_job_scheduled(job_id, result["video_id"])
    return {"job_id": job_id, "channel_handle": EXPECTED_HANDLE, "channel_id": EXPECTED_MEMORY_AGENT_CHANNEL_ID, **result}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--media", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = run(args.manifest, args.media)
    except (ValueError, D1Error, MediaValidationError, YouTubeError) as exc:
        code = getattr(exc, "code", str(exc))
        print(json.dumps({"status": "blocked", "error": str(code)[:120]}, ensure_ascii=False))
        return 2
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
