#!/usr/bin/env python3
"""Validate and schedule one AUTORED IDEA package through Publora.

This pipeline never calls publishNow. It creates a draft, uploads one media
asset, and schedules only after every local compliance gate passes.
"""
from __future__ import annotations

import argparse
import json
import mimetypes
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from publora_client import PubloraClient, PubloraError, stable_idempotency_key
from autored.d1_client import D1Client, D1Error


PROFILES = {
    "tiktok_pieknemedia": {"platform": "tiktok", "handle": "@pieknemedia"},
    "tiktok_ocenionona6": {"platform": "tiktok", "handle": "@ocenionona6"},
    "youtube_memoryagent": {"platform": "youtube", "handle": "@MemoryAgent-r3c"},
}


def validate_manifest(item: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    profile_id = item.get("profile_id")
    if profile_id not in PROFILES:
        raise PubloraError("unknown_target_profile")
    profile = PROFILES[profile_id]
    if item.get("platform") != profile["platform"]:
        raise PubloraError("profile_platform_mismatch")
    if item.get("handle", "").casefold() != profile["handle"].casefold():
        raise PubloraError("profile_handle_mismatch")
    for field in ("content_id", "content", "media_path", "rights_reference"):
        if not isinstance(item.get(field), str) or not item[field].strip():
            raise PubloraError("missing_" + field)
    if item.get("safety_review_status") != "passed":
        raise PubloraError("safety_review_not_passed")
    if item.get("ai_disclosure_required") and (
        not item.get("ai_disclosure_set") or item.get("ai_generated") is not True
    ):
        raise PubloraError("missing_ai_disclosure")
    if not isinstance(item.get("ai_generated"), bool):
        raise PubloraError("ai_generated_flag_required")
    if item.get("music_required"):
        if not item.get("music_license_reference") or not item.get("music_embedded"):
            raise PubloraError("licensed_music_not_embedded")
    scheduled_text = item.get("scheduled_time")
    if not isinstance(scheduled_text, str):
        raise PubloraError("scheduled_time_required")
    try:
        scheduled_time = datetime.fromisoformat(scheduled_text.replace("Z", "+00:00"))
    except ValueError:
        raise PubloraError("invalid_scheduled_time") from None
    if scheduled_time.tzinfo is None:
        raise PubloraError("schedule_must_be_timezone_aware")

    media_path = Path(item["media_path"])
    if not media_path.is_file():
        raise PubloraError("media_file_missing")
    mime = item.get("media_mime", "")
    detected_mime = mimetypes.guess_type(media_path.name)[0]
    if (
        not isinstance(mime, str)
        or not (mime.startswith("video/") or mime.startswith("image/"))
        or detected_mime != mime
    ):
        raise PubloraError("unsupported_media_type")
    if profile["platform"] == "tiktok" and len(item["content"].encode("utf-16-le")) // 2 > 2200:
        raise PubloraError("tiktok_caption_too_long")
    if profile["platform"] == "youtube" and len(item["content"]) > 5000:
        raise PubloraError("youtube_description_too_long")

    settings: dict[str, Any]
    if profile["platform"] == "tiktok":
        settings = {"tiktok": {"aiGenerated": item["ai_generated"]}}
        if mime.startswith("image/"):
            settings["tiktok"]["autoAddMusic"] = True
        else:
            if not item.get("music_license_reference") or not item.get("music_embedded"):
                raise PubloraError("tiktok_video_music_missing")
    else:
        title = item.get("title")
        privacy = item.get("privacy")
        made_for_kids = item.get("made_for_kids")
        if not isinstance(title, str) or not title.strip() or len(title) > 100:
            raise PubloraError("youtube_title_invalid")
        if privacy not in {"private", "unlisted", "public"}:
            raise PubloraError("youtube_privacy_invalid")
        if not isinstance(made_for_kids, bool):
            raise PubloraError("youtube_made_for_kids_declaration_required")
        if not mime.startswith("video/"):
            raise PubloraError("youtube_video_required")
        settings = {"youtube": {
            "privacy": privacy,
            "title": title,
            "madeForKids": made_for_kids,
            "aiGenerated": item["ai_generated"],
        }}
        tags = item.get("tags", [])
        if tags:
            if not isinstance(tags, list) or not all(isinstance(tag, str) for tag in tags):
                raise PubloraError("youtube_tags_invalid")
            if sum(len(tag) for tag in tags) + max(0, len(tags) - 1) > 500:
                raise PubloraError("youtube_tags_too_long")
            settings["youtube"]["tags"] = tags
    return profile, {"scheduled_time": scheduled_time, "platform_settings": settings, "media_path": media_path}


def process_manifest(client: Any, item: dict[str, Any], job_store: Any | None = None) -> dict[str, Any]:
    profile, validated = validate_manifest(item)
    connection = client.resolve_connection(profile["platform"], profile["handle"])
    client.check_schedule_quota(profile["platform"], validated["scheduled_time"])

    create_key = stable_idempotency_key(item["content_id"], item["profile_id"], "create")
    try:
        post_group_id = client.create_draft(
            item["content"],
            connection["platformId"],
            idempotency_key=create_key,
            platform_settings=validated["platform_settings"],
        )
    except PubloraError as exc:
        if exc.code != "network_outcome_unknown":
            raise
        # Repeating the identical request with the same key replays the original
        # response if Publora already created the draft.
        post_group_id = client.create_draft(
            item["content"],
            connection["platformId"],
            idempotency_key=create_key,
            platform_settings=validated["platform_settings"],
        )

    client.upload_media(post_group_id, validated["media_path"])
    schedule_key = stable_idempotency_key(item["content_id"], item["profile_id"], "schedule")
    try:
        scheduled = client.schedule_draft(
            post_group_id,
            validated["scheduled_time"],
            idempotency_key=schedule_key,
        )
    except PubloraError as exc:
        if exc.code != "network_outcome_unknown":
            raise
        current = client.get_post(post_group_id)
        group = current.get("postGroup", current)
        actual_time = group.get("scheduledTime") or group.get("scheduledAt") or group.get("scheduled_at")
        expected_time = validated["scheduled_time"].astimezone(timezone.utc)
        try:
            parsed_actual = datetime.fromisoformat(str(actual_time).replace("Z", "+00:00"))
        except (TypeError, ValueError):
            parsed_actual = None
        matches_time = (
            parsed_actual is not None
            and parsed_actual.tzinfo is not None
            and abs((parsed_actual.astimezone(timezone.utc) - expected_time).total_seconds()) <= 60
        )
        if group.get("status") == "scheduled" and matches_time:
            scheduled = current
        else:
            # Never blindly repeat a schedule update after an unknown outcome.
            raise PubloraError("schedule_outcome_unknown_requires_reconciliation") from None

    job_record = None
    if job_store is not None:
        try:
            job_record = job_store.record_scheduled(
                content_id=item["content_id"],
                profile_id=item["profile_id"],
                scheduled_at=validated["scheduled_time"].astimezone(timezone.utc).isoformat(),
                idempotency_key=schedule_key,
                provider_post_group_id=post_group_id,
            )
        except D1Error as exc:
            raise PubloraError("d1_job_record_failed:" + exc.code) from None

    return {
        "status": "scheduled",
        "post_group_id": post_group_id,
        "job_record": job_record,
        "platform_id": connection["platformId"],
        "scheduled_time": validated["scheduled_time"].astimezone(timezone.utc).isoformat(),
        "provider_response": scheduled,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    args = parser.parse_args()
    try:
        item = json.loads(args.manifest.read_text(encoding="utf-8"))
        result = process_manifest(PubloraClient(), item, D1Client())
    except (OSError, json.JSONDecodeError):
        print(json.dumps({"status": "blocked", "error": "manifest_read_failed"}))
        return 2
    except D1Error as exc:
        print(json.dumps({"status": "blocked", "error": exc.code}))
        return 2
    except PubloraError as exc:
        print(json.dumps({"status": "blocked", "error": exc.code, "http_status": exc.status}))
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
