"""Minimal Cloudflare D1 REST client for publication job reconciliation."""
from __future__ import annotations

import hashlib
import json
import os
import urllib.error
import urllib.request
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

    def record_scheduled(
        self,
        *,
        content_id: str,
        profile_id: str,
        scheduled_at: str,
        idempotency_key: str,
        provider_post_group_id: str,
    ) -> dict[str, Any]:
        row = self.query(
            "SELECT id, profile_id, status FROM content_items WHERE id = ?",
            [content_id],
        ).get("results", [])
        if len(row) != 1:
            raise D1Error("content_item_not_found")
        item = row[0]
        if item.get("profile_id") != profile_id:
            raise D1Error("content_profile_mismatch")
        if item.get("status") not in {"idea", "draft", "ready", "scheduled"}:
            raise D1Error("content_status_not_schedulable")

        job_id = "job_" + hashlib.sha256(
            (content_id + "\0" + profile_id + "\0" + idempotency_key).encode("utf-8")
        ).hexdigest()[:40]
        self.query(
            "INSERT INTO publication_jobs "
            "(id, content_id, profile_id, scheduled_at, idempotency_key, status, attempts, platform_post_id) "
            "VALUES (?, ?, ?, ?, ?, 'planned', 0, ?) "
            "ON CONFLICT(idempotency_key) DO UPDATE SET "
            "scheduled_at=excluded.scheduled_at, status='planned', "
            "platform_post_id=excluded.platform_post_id, updated_at=CURRENT_TIMESTAMP",
            [job_id, content_id, profile_id, scheduled_at, idempotency_key, provider_post_group_id],
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
