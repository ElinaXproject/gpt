"""Minimal Cloudflare D1 REST client for publication job reconciliation."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import os
import urllib.error
import urllib.request
from datetime import datetime, timezone
from typing import Any

from .factcheck import Claim, Evidence, FactCheckReport


ACCOUNT_ID = os.environ.get("CLOUDFLARE_ACCOUNT_ID", "6a685fc3e19dd4a1cd85c3fe6711d73b")
DATABASE_ID = os.environ.get("D1_DATABASE_ID", "5162eab4-2364-4481-95c1-50fdc3070d3e")
API_ROOT = "https://api.cloudflare.com/client/v4"


class D1Error(RuntimeError):
    def __init__(self, code: str):
        self.code = code
        super().__init__("d1_" + code)


def _allowed_research_domains() -> set[str]:
    config_path = Path(__file__).resolve().parents[1] / "config" / "research_feeds.json"
    try:
        feeds = json.loads(config_path.read_text(encoding="utf-8"))
        return {
            str(domain).lower().removeprefix("www.")
            for feed in feeds
            for domain in feed.get("allowed_domains", [])
        }
    except (OSError, json.JSONDecodeError, TypeError):
        raise D1Error("research_domain_allowlist_unavailable") from None


def _safety_review_reference(payload: dict[str, Any]) -> str:
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return "sr_" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _validate_safety_review_payload(payload: dict[str, Any], content_id: str, profile_id: str) -> list[str]:
    errors: list[str] = []
    if payload.get("content_id") != content_id or payload.get("profile_id") != profile_id:
        errors.append("safety_review_content_mapping_invalid")
    if payload.get("decision") != "approved":
        errors.append("safety_review_not_approved")
    if not str(payload.get("reviewer") or "").strip():
        errors.append("safety_review_reviewer_missing")
    try:
        reviewed_at = datetime.fromisoformat(str(payload.get("reviewed_at") or "").replace("Z", "+00:00"))
        if reviewed_at.tzinfo is None:
            errors.append("safety_review_timezone_missing")
        elif (reviewed_at.astimezone(timezone.utc) - datetime.now(timezone.utc)).total_seconds() > 300:
            errors.append("safety_review_timestamp_in_future")
    except (TypeError, ValueError):
        errors.append("safety_review_timestamp_invalid")
    required = {"content_safety", "copyright_rights", "platform_rules", "ai_disclosure"}
    if profile_id.startswith("tiktok_"):
        required.add("music_license")
    if profile_id in {"tiktok_ocenionona6", "youtube_memoryagent"}:
        required.add("factual_accuracy")
    checks = payload.get("checks")
    if not isinstance(checks, dict):
        errors.append("safety_review_checks_missing")
    else:
        for key in required:
            if checks.get(key) is not True:
                errors.append("safety_review_check_failed:" + key)
    return sorted(set(errors))


def _fact_check_report_from_json(raw: str) -> FactCheckReport:
    try:
        payload = json.loads(raw)
        claims = tuple(
            Claim(str(item["claim_id"]), str(item["text"]))
            for item in payload["claims"]
        )
        evidence = tuple(
            Evidence(
                url=str(item["url"]),
                title=str(item["title"]),
                published_at=str(item["published_at"]),
                supports_claim_ids=tuple(str(value) for value in item["supports_claim_ids"]),
                support_type=str(item.get("support_type", "direct")),
            )
            for item in payload["evidence"]
        )
        return FactCheckReport(
            profile_key=str(payload["profile_key"]),
            reviewed_at=str(payload["reviewed_at"]),
            reviewer=str(payload["reviewer"]),
            reviewer_type=str(payload["reviewer_type"]),
            decision=str(payload["decision"]),
            claims=claims,
            evidence=evidence,
        )
    except (KeyError, TypeError, ValueError, json.JSONDecodeError):
        raise D1Error("fact_check_report_invalid_json") from None


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

    def record_safety_review(
        self,
        content_id: str,
        profile_id: str,
        reviewer: str,
        reviewed_at: str,
        decision: str,
        checks: dict[str, Any],
        notes: str = "",
    ) -> tuple[str, str]:
        rows = self.query(
            "SELECT profile_id, status FROM content_items WHERE id=?",
            [content_id],
        ).get("results", [])
        if len(rows) != 1:
            raise D1Error("content_item_not_found")
        if rows[0].get("profile_id") != profile_id:
            raise D1Error("content_profile_mismatch")
        payload = {
            "content_id": content_id,
            "profile_id": profile_id,
            "reviewer": str(reviewer),
            "reviewed_at": str(reviewed_at),
            "decision": str(decision),
            "checks": checks if isinstance(checks, dict) else {},
            "notes": str(notes)[:1000],
        }
        errors = _validate_safety_review_payload(payload, content_id, profile_id)
        status = "passed" if not errors else "blocked"
        reference = _safety_review_reference(payload)
        result = self.query(
            "UPDATE content_items SET safety_review_status=?, safety_review_reference=?, "
            "safety_review_report_json=?, updated_at=CURRENT_TIMESTAMP "
            "WHERE id=? AND profile_id=? AND status IN ('idea','draft','ready')",
            [
                status,
                reference,
                json.dumps(payload, ensure_ascii=False, sort_keys=True),
                content_id,
                profile_id,
            ],
        )
        if (result.get("meta") or {}).get("changes", 0) != 1:
            raise D1Error("safety_review_persist_rejected")
        return status, reference

    def record_fact_check_report(self, content_id: str, profile_id: str, report: FactCheckReport) -> str:
        rows = self.query(
            "SELECT profile_id, status FROM content_items WHERE id=?",
            [content_id],
        ).get("results", [])
        if len(rows) != 1:
            raise D1Error("content_item_not_found")
        if rows[0].get("profile_id") != profile_id or report.profile_key != profile_id:
            raise D1Error("content_profile_mismatch")
        if report.reviewer_type != "human":
            raise D1Error("fact_check_human_review_required")
        errors = report.validate(_allowed_research_domains())
        if errors:
            raise D1Error("fact_check_report_invalid:" + ",".join(errors)[:80])
        reference = report.reference()
        payload = {
            "profile_key": report.profile_key,
            "reviewed_at": report.reviewed_at,
            "reviewer": report.reviewer,
            "reviewer_type": report.reviewer_type,
            "decision": report.decision,
            "claims": [{"claim_id": claim.claim_id, "text": claim.text} for claim in report.claims],
            "evidence": [
                {
                    "url": item.url,
                    "title": item.title,
                    "published_at": item.published_at,
                    "supports_claim_ids": list(item.supports_claim_ids),
                    "support_type": item.support_type,
                }
                for item in report.evidence
            ],
        }
        evidence_urls = [item.url for item in report.evidence]
        evidence_dates = [item.published_at for item in report.evidence]
        result = self.query(
            "UPDATE content_items SET fact_check_passed=1, fact_check_reference=?, fact_check_report_json=?, "
            "source_urls_json=?, source_published_at_json=?, updated_at=CURRENT_TIMESTAMP "
            "WHERE id=? AND profile_id=? AND status IN ('draft','ready','scheduled')",
            [
                reference,
                json.dumps(payload, ensure_ascii=False, sort_keys=True),
                json.dumps(evidence_urls, ensure_ascii=False),
                json.dumps(evidence_dates, ensure_ascii=False),
                content_id,
                profile_id,
            ],
        )
        if (result.get("meta") or {}).get("changes", 0) != 1:
            raise D1Error("fact_check_report_persist_rejected")
        return reference

    def _validate_content_for_publish(self, content_id: str, profile_id: str, provider: str) -> dict[str, Any]:
        row = self.query(
            "SELECT id, profile_id, status, safety_review_status, rights_reference, "
            "ai_disclosure_required, ai_disclosure_set, fact_check_passed, fact_check_reference, "
            "fact_check_report_json, source_urls_json, source_published_at_json, "
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
        try:
            safety_report = json.loads(str(item.get("safety_review_report_json") or ""))
        except json.JSONDecodeError:
            raise D1Error("safety_review_report_invalid") from None
        if not isinstance(safety_report, dict):
            raise D1Error("safety_review_report_invalid")
        safety_errors = _validate_safety_review_payload(safety_report, content_id, profile_id)
        if safety_errors:
            raise D1Error("safety_review_report_invalid:" + ",".join(safety_errors)[:80])
        if _safety_review_reference(safety_report) != item.get("safety_review_reference"):
            raise D1Error("safety_review_reference_mismatch")
        if not str(item.get("rights_reference") or "").strip():
            raise D1Error("rights_reference_missing")
        if item.get("ai_disclosure_required") == 1 and item.get("ai_disclosure_set") != 1:
            raise D1Error("ai_disclosure_missing")
        if profile_id in {"tiktok_ocenionona6", "youtube_memoryagent"}:
            if item.get("fact_check_passed") != 1 or not str(item.get("fact_check_reference") or "").strip():
                raise D1Error("fact_check_not_passed")
            report = _fact_check_report_from_json(str(item.get("fact_check_report_json") or ""))
            if report.profile_key != profile_id or report.reviewer_type != "human":
                raise D1Error("fact_check_human_review_required")
            errors = report.validate(_allowed_research_domains())
            if errors:
                raise D1Error("fact_check_report_invalid:" + ",".join(errors)[:80])
            if report.reference() != item.get("fact_check_reference"):
                raise D1Error("fact_check_reference_mismatch")
            try:
                stored_urls = json.loads(str(item.get("source_urls_json") or "[]"))
                stored_dates = json.loads(str(item.get("source_published_at_json") or "[]"))
            except json.JSONDecodeError:
                raise D1Error("fact_check_source_metadata_invalid") from None
            if stored_urls != [source.url for source in report.evidence]:
                raise D1Error("fact_check_source_urls_mismatch")
            if stored_dates != [source.published_at for source in report.evidence]:
                raise D1Error("fact_check_source_dates_mismatch")
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

    def mark_job_scheduled(self, job_id: str, provider_post_id: str) -> None:
        result = self.query(
            "UPDATE publication_jobs SET status='planned', platform_post_id=?, updated_at=CURRENT_TIMESTAMP "
            "WHERE id=? AND status='publishing' AND provider='youtube_direct'",
            [provider_post_id, job_id],
        )
        if (result.get("meta") or {}).get("changes", 0) != 1:
            raise D1Error("job_schedule_transition_rejected")

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
        rows = self.query(
            "SELECT content_id FROM publication_jobs WHERE id=?",
            [job_id],
        ).get("results", [])
        if len(rows) != 1:
            raise D1Error("job_not_found")
        result = self.query(
            "UPDATE publication_jobs SET status=?, last_error_code=?, updated_at=CURRENT_TIMESTAMP WHERE id=?",
            [status, safe_code, job_id],
        )
        if (result.get("meta") or {}).get("changes", 0) != 1:
            raise D1Error("job_failure_transition_rejected")
        self.query(
            "UPDATE content_items SET status=?, updated_at=CURRENT_TIMESTAMP "
            "WHERE id=? AND status IN ('idea','draft','ready','scheduled')",
            [status, rows[0]["content_id"]],
        )

    def get_due_jobs(self, now_utc: str, limit: int = 20) -> list[dict[str, Any]]:
        if not 1 <= limit <= 100:
            raise D1Error("invalid_due_job_limit")
        return self.query(
            "SELECT id, content_id, profile_id, scheduled_at, idempotency_key, provider, media_artifact_id, status "
            "FROM publication_jobs WHERE provider='tiktok_direct' AND status IN ('planned','ready','retry_wait') AND scheduled_at<=? "
            "ORDER BY scheduled_at LIMIT ?",
            [now_utc, limit],
        ).get("results", [])


    def get_pending_tiktok_jobs(self, limit: int = 20) -> list[dict[str, Any]]:
        if not 1 <= limit <= 100:
            raise D1Error("invalid_pending_job_limit")
        return self.query(
            "SELECT id, content_id, profile_id, platform_post_id, status "
            "FROM publication_jobs WHERE provider='tiktok_direct' AND status='publishing' "
            "AND platform_post_id IS NOT NULL ORDER BY updated_at LIMIT ?",
            [limit],
        ).get("results", [])

    def get_youtube_jobs_to_schedule(self, now_utc: str, horizon_hours: int = 168, limit: int = 20) -> list[dict[str, Any]]:
        if not 1 <= limit <= 100 or not 1 <= horizon_hours <= 168:
            raise D1Error("invalid_youtube_schedule_query")
        rows = self.query(
            "SELECT id, content_id, profile_id, scheduled_at, idempotency_key, provider, media_artifact_id, status "
            "FROM publication_jobs WHERE provider='youtube_direct' AND status IN ('planned','ready','retry_wait') "
            "AND platform_post_id IS NULL AND scheduled_at>? "
            "AND scheduled_at<=datetime(?, '+' || ? || ' hours') "
            "ORDER BY scheduled_at LIMIT ?",
            [now_utc, now_utc, horizon_hours, limit],
        ).get("results", [])
        return rows
