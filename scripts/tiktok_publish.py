#!/usr/bin/env python3
"""Run one due TikTok Direct Post job after all D1 gates pass."""
from __future__ import annotations

import argparse
import hashlib
import json
import mimetypes
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from autored.d1_client import D1Client, D1Error
from autored.media_validation import MediaValidationError, sha256_file, validate_tiktok_video
from autored.providers.tiktok import TikTokDirectPublisher, TikTokError
from autored.token_vault import D1EncryptedTokenStore, TokenVaultError


PROFILES = {
    "tiktok_pieknemedia": "pieknemedia",
    "tiktok_ocenionona6": "ocenionona6",
}


def load_manifest(path: Path) -> dict[str, Any]:
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        raise ValueError("manifest_unreadable") from None
    required = {
        "content_id", "profile_id", "scheduled_at", "idempotency_key", "caption",
        "duration_seconds", "privacy_level", "music_embedded", "music_license_reference",
        "ai_generated", "media_sha256", "media_bytes", "media_mime"
    }
    if not isinstance(manifest, dict) or required - set(manifest):
        raise ValueError("manifest_fields_missing")
    if manifest["profile_id"] not in PROFILES:
        raise ValueError("unknown_tiktok_profile")
    if not isinstance(manifest["ai_generated"], bool) or not isinstance(manifest["music_embedded"], bool):
        raise ValueError("manifest_boolean_invalid")
    try:
        scheduled = datetime.fromisoformat(str(manifest["scheduled_at"]).replace("Z", "+00:00"))
    except ValueError:
        raise ValueError("scheduled_at_invalid") from None
    if scheduled.tzinfo is None:
        raise ValueError("scheduled_at_timezone_missing")
    manifest["_scheduled_datetime"] = scheduled
    return manifest


def validate_media_against_d1(d1: D1Client, manifest: dict[str, Any], media_path: Path) -> dict[str, Any]:
    rows = d1.query(
        "SELECT media_sha256, media_bytes, media_mime, music_embedded, music_license_reference "
        "FROM content_items WHERE id=? AND profile_id=?",
        [manifest["content_id"], manifest["profile_id"]],
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
    if row.get("music_embedded") != 1 or not row.get("music_license_reference"):
        raise D1Error("licensed_embedded_music_required")
    if manifest["music_embedded"] is not True or manifest["music_license_reference"] != row["music_license_reference"]:
        raise D1Error("music_metadata_mismatch")
    return validate_tiktok_video(media_path)


def run(manifest_path: Path, media_path: Path) -> dict[str, Any]:
    manifest = load_manifest(manifest_path)
    d1 = D1Client()
    validate_media_against_d1(d1, manifest, media_path)
    reservation = d1.reserve_job(
        content_id=manifest["content_id"],
        profile_id=manifest["profile_id"],
        scheduled_at=manifest["scheduled_at"],
        idempotency_key=manifest["idempotency_key"],
        provider="tiktok_direct",
        media_artifact_id=manifest.get("media_artifact_id"),
    )
    job_id = reservation["job_id"]
    d1.mark_job_publishing(job_id)
    try:
        publisher = TikTokDirectPublisher(
            profile_id=manifest["profile_id"],
            expected_username=PROFILES[manifest["profile_id"]],
            token_store=D1EncryptedTokenStore(d1),
        )
        result = publisher.publish_video(
            media_path=media_path,
            title=manifest["caption"],
            privacy_level=manifest["privacy_level"],
            duration_seconds=int(manifest["duration_seconds"]),
            scheduled_at=manifest["_scheduled_datetime"],
            music_embedded=manifest["music_embedded"],
            music_license_reference=manifest["music_license_reference"],
            ai_generated=manifest["ai_generated"],
        )
    except TikTokError as exc:
        d1.mark_job_failed(job_id, exc.code, blocked=exc.code in {
            "network_outcome_unknown", "upload_outcome_unknown", "publication_not_due",
            "unaudited_app_public_post_blocked"
        })
        raise
    except TokenVaultError as exc:
        d1.mark_job_failed(job_id, exc.code, blocked=True)
        raise
    if result["status"] == "published":
        d1.mark_job_published(job_id, result["publish_id"])
    else:
        d1.mark_job_pending(job_id, result["publish_id"])
    return {"job_id": job_id, **result}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--media", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = run(args.manifest, args.media)
    except (ValueError, D1Error, MediaValidationError, TikTokError, TokenVaultError) as exc:
        code = getattr(exc, "code", str(exc))
        print(json.dumps({"status": "blocked", "error": str(code)[:120]}, ensure_ascii=False))
        return 2
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
