#!/usr/bin/env python3
"""Dispatch due TikTok jobs and future YouTube schedules from the D1 queue."""
from __future__ import annotations

import argparse
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from autored.d1_client import D1Client, D1Error
from autored.providers.tiktok import TikTokDirectPublisher
from autored.token_vault import D1EncryptedTokenStore
from download_media_artifact import ArtifactError, download_media_artifact
from tiktok_publish import PROFILES, load_manifest as load_tiktok_manifest, run as run_tiktok
from youtube_publish import load_manifest as load_youtube_manifest, run as run_youtube


def _parse_time(value: Any) -> datetime:
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        raise ValueError("scheduled_at_invalid") from None
    if parsed.tzinfo is None:
        raise ValueError("scheduled_at_timezone_missing")
    return parsed.astimezone(timezone.utc)


def _manifest_matches(job: dict[str, Any], manifest: dict[str, Any]) -> bool:
    return (
        manifest.get("content_id") == job.get("content_id")
        and manifest.get("profile_id") == job.get("profile_id")
        and manifest.get("idempotency_key") == job.get("idempotency_key")
        and _parse_time(manifest.get("scheduled_at")) == _parse_time(job.get("scheduled_at"))
    )


def _provider_ready(provider: str, env: dict[str, str]) -> bool:
    if provider == "tiktok_direct":
        return all(env.get(key) for key in (
            "TIKTOK_CLIENT_KEY", "TIKTOK_CLIENT_SECRET", "AUTORED_TOKEN_ENCRYPTION_KEY"
        ))
    if provider == "youtube_direct":
        return all(env.get(key) for key in (
            "YOUTUBE_CLIENT_ID", "YOUTUBE_CLIENT_SECRET", "YOUTUBE_REFRESH_TOKEN"
        ))
    return False


def _check_tiktok_status(job: dict[str, Any], d1: D1Client) -> str:
    profile_id = str(job.get("profile_id") or "")
    username = PROFILES.get(profile_id)
    if not username:
        raise ValueError("unknown_tiktok_profile")
    publisher = TikTokDirectPublisher(
        profile_id=profile_id,
        expected_username=username,
        token_store=D1EncryptedTokenStore(d1),
    )
    return publisher.get_publish_status(str(job.get("platform_post_id") or ""))


def _reconcile_pending_tiktok(
    job: dict[str, Any],
    *,
    d1: D1Client,
    env: dict[str, str],
    status_checker: Callable[[dict[str, Any], D1Client], str],
) -> dict[str, Any]:
    job_id = str(job.get("id") or "")
    if not _provider_ready("tiktok_direct", env):
        return {"job_id": job_id, "status": "skipped", "reason": "provider_credentials_not_configured"}
    try:
        provider_status = status_checker(job, d1)
        if provider_status == "PUBLISH_COMPLETE":
            d1.mark_job_published(job_id, str(job["platform_post_id"]))
            return {"job_id": job_id, "status": "published"}
        if provider_status == "FAILED":
            d1.mark_job_failed(job_id, "tiktok_publish_failed", blocked=False)
            return {"job_id": job_id, "status": "failed"}
        return {"job_id": job_id, "status": "pending", "provider_status": provider_status}
    except Exception as exc:
        code = getattr(exc, "code", type(exc).__name__)
        return {"job_id": job_id, "status": "error", "reason": str(code)[:120]}


def _dispatch_one(
    job: dict[str, Any],
    *,
    d1: D1Client,
    env: dict[str, str],
    downloader: Callable[..., tuple[Path, Path]],
    tiktok_runner: Callable[[Path, Path], dict[str, Any]],
    youtube_runner: Callable[[Path, Path], dict[str, Any]],
) -> dict[str, Any]:
    job_id = str(job.get("id") or "")
    provider = str(job.get("provider") or "")
    if not _provider_ready(provider, env):
        return {"job_id": job_id, "status": "skipped", "reason": "provider_credentials_not_configured"}
    artifact_id = str(job.get("media_artifact_id") or "")
    if not artifact_id.isdigit():
        d1.mark_job_failed(job_id, "media_artifact_id_missing_or_invalid", blocked=True)
        return {"job_id": job_id, "status": "blocked", "reason": "media_artifact_id_missing_or_invalid"}

    with tempfile.TemporaryDirectory(prefix="autored-publish-") as tmp:
        try:
            manifest_path, media_path = downloader(artifact_id, Path(tmp))
            if provider == "tiktok_direct":
                manifest = load_tiktok_manifest(manifest_path)
                runner = tiktok_runner
            elif provider == "youtube_direct":
                manifest = load_youtube_manifest(manifest_path)
                runner = youtube_runner
            else:
                d1.mark_job_failed(job_id, "unsupported_native_provider", blocked=True)
                return {"job_id": job_id, "status": "blocked", "reason": "unsupported_native_provider"}
            if not _manifest_matches(job, manifest):
                d1.mark_job_failed(job_id, "media_manifest_job_mismatch", blocked=True)
                return {"job_id": job_id, "status": "blocked", "reason": "media_manifest_job_mismatch"}
            result = runner(manifest_path, media_path)
            return {"job_id": job_id, "status": "processed", "provider": provider, "result": result}
        except (ArtifactError, ValueError, OSError, D1Error) as exc:
            code = getattr(exc, "code", type(exc).__name__)
            d1.mark_job_failed(job_id, str(code)[:120], blocked=True)
            return {"job_id": job_id, "status": "blocked", "reason": str(code)[:120]}
        except Exception as exc:
            # Provider runners persist their own failure state; expose only a bounded class/code.
            code = getattr(exc, "code", type(exc).__name__)
            return {"job_id": job_id, "status": "error", "reason": str(code)[:120]}


def run_dispatch(
    *,
    d1: D1Client | None = None,
    now_utc: str | None = None,
    limit: int = 10,
    dry_run: bool = False,
    env: dict[str, str] | None = None,
    downloader: Callable[..., tuple[Path, Path]] = download_media_artifact,
    tiktok_runner: Callable[[Path, Path], dict[str, Any]] = run_tiktok,
    youtube_runner: Callable[[Path, Path], dict[str, Any]] = run_youtube,
    tiktok_status_checker: Callable[[dict[str, Any], D1Client], str] = _check_tiktok_status,
) -> dict[str, Any]:
    client = d1 or D1Client()
    environment = dict(os.environ if env is None else env)
    now = now_utc or datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    pending_tiktok_jobs = client.get_pending_tiktok_jobs(limit=limit)
    tiktok_jobs = client.get_due_jobs(now, limit=limit)
    youtube_jobs = client.get_youtube_jobs_to_schedule(now, horizon_hours=168, limit=limit)
    candidates = [
        *[dict(job, provider="tiktok_direct") for job in tiktok_jobs],
        *[dict(job, provider="youtube_direct") for job in youtube_jobs],
    ]
    if dry_run:
        return {
            "status": "dry_run",
            "candidate_count": len(candidates),
            "pending_tiktok_count": len(pending_tiktok_jobs),
            "jobs": candidates,
            "pending_tiktok_jobs": pending_tiktok_jobs,
        }
    reconciliation = [
        _reconcile_pending_tiktok(
            job, d1=client, env=environment, status_checker=tiktok_status_checker
        )
        for job in pending_tiktok_jobs
    ]
    results = [
        _dispatch_one(
            job, d1=client, env=environment, downloader=downloader,
            tiktok_runner=tiktok_runner, youtube_runner=youtube_runner
        )
        for job in candidates
    ]
    return {
        "status": "completed",
        "candidate_count": len(candidates),
        "reconciled": sum(item["status"] in {"published", "failed"} for item in reconciliation),
        "pending": sum(item["status"] == "pending" for item in reconciliation),
        "reconciliation_errors": sum(item["status"] == "error" for item in reconciliation),
        "processed": sum(item["status"] == "processed" for item in results),
        "blocked": sum(item["status"] == "blocked" for item in results),
        "skipped": sum(item["status"] == "skipped" for item in results),
        "errors": sum(item["status"] == "error" for item in results),
        "jobs": results,
        "reconciliation": reconciliation,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    if not 1 <= args.limit <= 100:
        parser.error("--limit must be between 1 and 100")
    try:
        result = run_dispatch(limit=args.limit, dry_run=args.dry_run)
    except (D1Error, ValueError) as exc:
        code = getattr(exc, "code", str(exc))
        print(json.dumps({"status": "failed", "error": str(code)[:120]}, ensure_ascii=False))
        return 2
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result["status"] in {"completed", "dry_run"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
