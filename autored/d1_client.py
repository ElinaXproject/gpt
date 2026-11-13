"""Minimal Cloudflare D1 REST client for publication job reconciliation."""
from __future__ import annotations

import hashlib
import json
import os
import urllib.error
import urllib.request
from datetime import datetime
from typing import Any


ACCOUNT_ID = os.environ.get("CLOUDFLARE_ACCOUNT_ID", "6a685fc3e19dd4a1cd85c3fe6711d73b")
DATABASE_ID = os.environ.get("D1_DATABASE_ID", "5162eab4-2364-4481-95c1-50fdc3070d3e")
API_ROOT = "https://api.cloudflare.com/client/v4"


class D1Error(RuntimeError):
    def __init__(self, code: str):
        self.code = code
        super().__init__("d1_" + code)


class D1Client:
    def __init__(self, api_token: str | None = None, opener=None):
        self.api_token = api_token or os.environ.get("CLOUDFLARE_API_TOKEN", "")
        if not self.api_token:
            raise D1Error("missing_api_token")
        self.opener = opener or urllib.request.urlopen

    def query(self, sql: str, params: list[Any] | None = None) -> dict[str, Any]:
        url = f"{API_ROOT}/accounts/{ACCOUNT_ID}/d1/database/{DATABASE_ID}/query"
        body = json.dumps({"sql": sql, "params": params or []}).encode("utf-8")
        request = urllib.request.Request(
            url,
            data=body,
            headers={
                "Authorization": "Bearer " + self.api_token,
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            method="POST",
        )
        try:
            with self.opener(request, timeout=30) as response:
                raw = response.read()
                status = getattr(response, "status", 200)
        except urllib.error.HTTPError as exc:
            raise D1Error("provider_rejected_http_" + str(exc.code)) from None
        except (urllib.error.URLError, TimeoutError, OSError):
            raise D1Error("network_outcome_unknown") from None
        if not 200 <= status < 300:
            raise D1Error("unexpected_http_status")
        try:
            payload = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            raise D1Error("invalid_json_response") from None
        if payload.get("success") is not True:
            raise D1Error("query_failed")
        result = payload.get("result")
        if not isinstance(result, list) or not result:
            raise D1Error("invalid_query_result")
        first = result[0]
        if first.get("success") is False:
            raise D1Error("statement_failed")
        return first

    def _validate_content_for_publish(self, content_id: str, profile_id: str, provider: str) -> dict[str, Any]:
        row = self.query(
            "SELECT id, profile_id, status, safety_review_status, rights_reference, "
            "ai_disclosure_required, ai_disclosure_set, fact_check_passed, fact_check_reference, "
            "music_embedded, music_license_reference FROM content_items WHERE id = ?",
            [content_id],
        ).get("results", [])
        if len(row) != 1:
            raise D1Error("content_item_not_found")
        item = row[0]
        if item.get("profile_id") != profile_id:
            raise D1Error("content_profile_mismatch")
        if item.get("status") not in {"draft", "ready", "scheduled"}:
            raise D1Error("content_status_not_publishable")
        if item.get("safety_review_status") != "passed":
            raise D1Error("safety_review_not_passed")
        if not str(item.get("rights_reference") or "").strip():
            raise D1Error("rights_reference_missing")
        if item.get("ai_disclosure_required") == 1 and item.get("ai_disclosure_set") != 1:
            raise D1Error("ai_disclosure_missing")
        if profile_id in {"tiktok_ocenionona6", "youtube_memoryagent"}:
            if item.get("fact_check_passed") != 1 or not str(item.get("fact_check_reference") or "").strip():
                raise D1Error("fact_check_not_passed")
        if provider == "tiktok_direct":
            if item.get("music_embedded") != 1 or not str(item.get("music_license_reference") or "").strip():
                raise D1Error("licensed_embedded_music_required")
        return item

    def record_scheduled(
        self,
        *,
        content_id: str,
        profile_id: str,
        scheduled_at: str,
        idempotency_key: str,
        provider_post_group_id: str,
    ) -> dict[str, Any]:
        self._validate_content_for_publish(content_id, profile_id, "publora")

        job_id = "job_" + hashlib.sha256(
            (content_id + "\0" + profile_id + "\0" + idempotency_key).encode("utf-8")
        ).hexdigest()[:40]
        self.query(
            "INSERT INTO publication_jobs "
            "(id, content_id, profile_id, scheduled_at, idempotency_key, status, attempts, platform_post_id, provider) "
            "VALUES (?, ?, ?, ?, ?, 'planned', 0, ?, 'publora') "
            "ON CONFLICT(idempotency_key) DO NOTHING",
            [job_id, content_id, profile_id, scheduled_at, idempotency_key, provider_post_group_id],
        )
        existing = self.query(
            "SELECT id, content_id, profile_id, status, provider, platform_post_id "
            "FROM publication_jobs WHERE idempotency_key=?",
            [idempotency_key],
        ).get("results", [])
        if len(existing) != 1:
            raise D1Error("job_record_not_confirmed")
        job = existing[0]
        if job.get("content_id") != content_id or job.get("profile_id") != profile_id or job.get("provider") != "publora":
            raise D1Error("idempotency_key_conflict")
        if job.get("status") == "published":
            raise D1Error("job_already_published")
        if job.get("status") == "publishing":
            raise D1Error("job_requires_reconciliation")
        if job.get("status") not in {"planned", "ready", "retry_wait"}:
            raise D1Error("job_not_reservable")
        if job.get("platform_post_id") not in {None, provider_post_group_id}:
            raise D1Error("provider_post_group_mismatch")
        self.query(
            "UPDATE publication_jobs SET platform_post_id=?, updated_at=CURRENT_TIMESTAMP WHERE id=?",
            [provider_post_group_id, job["id"]],
        )
        update = self.query(
            "UPDATE content_items SET status='scheduled', updated_at=CURRENT_TIMESTAMP "
            "WHERE id=? AND profile_id=? AND status IN ('idea','draft','ready','scheduled')",
            [content_id, profile_id],
        )
        return {
            "job_id": job_id,
            "job_status": "planned",
            "content_status": "scheduled",
            "content_rows_changed": (update.get("meta") or {}).get("changes", 0),
            "provider_post_group_id": provider_post_group_id,
        }


    def reserve_job(
        self,
        *,
        content_id: str,
        profile_id: str,
        scheduled_at: str,
        idempotency_key: str,
        provider: str,
        media_artifact_id: str | None = None,
    ) -> dict[str, Any]:
        if provider not in {"tiktok_direct", "youtube_direct"}:
            raise D1Error("unsupported_native_provider")
        if not idempotency_key:
            raise D1Error("missing_idempotency_key")
        self._validate_content_for_publish(content_id, profile_id, provider)
        try:
            parsed_schedule = datetime.fromisoformat(scheduled_at.replace("Z", "+00:00"))
        except (TypeError, ValueError):
            raise D1Error("invalid_scheduled_at") from None
        if parsed_schedule.tzinfo is None:
            raise D1Error("scheduled_at_missing_timezone")
        job_id = "job_" + hashlib.sha256(
            (content_id + "\0" + profile_id + "\0" + idempotency_key).encode("utf-8")
        ).hexdigest()[:40]
        self.query(
            "INSERT INTO publication_jobs "
            "(id, content_id, profile_id, scheduled_at, idempotency_key, status, attempts, provider, media_artifact_id) "
            "VALUES (?, ?, ?, ?, ?, 'planned', 0, ?, ?) "
            "ON CONFLICT(idempotency_key) DO NOTHING",
            [job_id, content_id, profile_id, scheduled_at, idempotency_key, provider, media_artifact_id],
        )
        rows = self.query(
            "SELECT id, content_id, profile_id, status, provider, platform_post_id "
            "FROM publication_jobs WHERE idempotency_key=?",
            [idempotency_key],
        ).get("results", [])
        if len(rows) != 1:
            raise D1Error("job_reservation_not_confirmed")
        job = rows[0]
        if job.get("content_id") != content_id or job.get("profile_id") != profile_id or job.get("provider") != provider:
            raise D1Error("idempotency_key_conflict")
        if job.get("status") == "published":
            raise D1Error("job_already_published")
        if job.get("status") == "publishing":
            raise D1Error("job_requires_reconciliation")
        if job.get("status") not in {"planned", "ready", "retry_wait"}:
            raise D1Error("job_not_reservable")
        self.query(
            "UPDATE content_items SET status='scheduled', updated_at=CURRENT_TIMESTAMP "
            "WHERE id=? AND profile_id=? AND status IN ('draft','ready','scheduled')",
            [content_id, profile_id],
        )
        return {"job_id": job["id"], "status": job["status"], "provider": provider}

    def mark_job_publishing(self, job_id: str) -> None:
        result = self.query(
            "UPDATE publication_jobs SET status='publishing', attempts=attempts+1, updated_at=CURRENT_TIMESTAMP "
            "WHERE id=? AND status IN ('planned','ready','retry_wait')",
            [job_id],
        )
        if (result.get("meta") or {}).get("changes", 0) != 1:
            raise D1Error("job_transition_to_publishing_rejected")

    def mark_job_pending(self, job_id: str, provider_post_id: str) -> None:
        result = self.query(
            "UPDATE publication_jobs SET status='publishing', platform_post_id=?, updated_at=CURRENT_TIMESTAMP "
            "WHERE id=? AND status='publishing'",
            [provider_post_id, job_id],
        )
        if (result.get("meta") or {}).get("changes", 0) != 1:
            raise D1Error("job_pending_update_rejected")

    def mark_job_published(self, job_id: str, provider_post_id: str, published_url: str | None = None) -> None:
        rows = self.query(
            "SELECT content_id FROM publication_jobs WHERE id=?",
            [job_id],
        ).get("results", [])
        if len(rows) != 1:
            raise D1Error("job_not_found")
        content_id = rows[0]["content_id"]
        result = self.query(
            "UPDATE publication_jobs SET status='published', platform_post_id=?, published_url=?, "
            "last_error_code=NULL, updated_at=CURRENT_TIMESTAMP WHERE id=? AND status='publishing'",
            [provider_post_id, published_url, job_id],
        )
        if (result.get("meta") or {}).get("changes", 0) != 1:
            raise D1Error("job_publish_transition_rejected")
        self.query(
            "UPDATE content_items SET status='published', updated_at=CURRENT_TIMESTAMP WHERE id=?",
            [content_id],
        )

    def mark_job_failed(self, job_id: str, error_code: str, blocked: bool = False) -> None:
        status = "blocked" if blocked else "failed"
        safe_code = str(error_code)[:120]
        self.query(
            "UPDATE publication_jobs SET status=?, last_error_code=?, updated_at=CURRENT_TIMESTAMP WHERE id=?",
            [status, safe_code, job_id],
        )

    def get_due_jobs(self, now_utc: str, limit: int = 20) -> list[dict[str, Any]]:
        if not 1 <= limit <= 100:
            raise D1Error("invalid_due_job_limit")
        return self.query(
            "SELECT id, content_id, profile_id, scheduled_at, idempotency_key, provider, media_artifact_id, status "
            "FROM publication_jobs WHERE status IN ('planned','ready','retry_wait') AND scheduled_at<=? "
            "ORDER BY scheduled_at LIMIT ?",
            [now_utc, limit],
        ).get("results", [])
