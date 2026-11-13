#!/usr/bin/env python3
"""Safe server-side Publora API client for AUTORED IDEA.

The client creates drafts first, uploads media, then schedules. It never
publishes immediately. API credentials are read only from PUBLORA_API_KEY.
"""
from __future__ import annotations

import hashlib
import json
import mimetypes
import os
import re
import urllib.error
import urllib.parse
import urllib.request
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable


API_ROOT = "https://api.publora.com/api/v1"


class PubloraError(RuntimeError):
    def __init__(self, code: str, status: int | None = None):
        self.code = code
        self.status = status
        super().__init__(f"publora_{code}" + (f"_http_{status}" if status else ""))


class PubloraClient:
    def __init__(self, api_key: str | None = None, opener: Callable[..., Any] | None = None):
        self.api_key = api_key or os.environ.get("PUBLORA_API_KEY", "")
        if not self.api_key:
            raise PubloraError("missing_api_key")
        self.opener = opener or urllib.request.urlopen

    def _request(
        self,
        method: str,
        path: str,
        body: dict[str, Any] | None = None,
        *,
        idempotency_key: str | None = None,
        content_type: str = "application/json",
    ) -> dict[str, Any]:
        headers = {"x-publora-key": self.api_key, "Accept": "application/json"}
        data = None
        if body is not None:
            headers["Content-Type"] = content_type
            data = json.dumps(body, ensure_ascii=False).encode("utf-8")
        if idempotency_key:
            headers["Idempotency-Key"] = idempotency_key
        request = urllib.request.Request(
            API_ROOT + path, data=data, headers=headers, method=method
        )
        try:
            with self.opener(request, timeout=30) as response:
                raw = response.read()
                status = getattr(response, "status", 200)
        except urllib.error.HTTPError as exc:
            try:
                payload = json.loads(exc.read().decode("utf-8"))
                code = str(payload.get("code") or payload.get("error") or "provider_rejected")
            except Exception:
                code = "provider_rejected"
            raise PubloraError(re.sub(r"[^a-zA-Z0-9_-]", "_", code)[:80], exc.code) from None
        except (urllib.error.URLError, TimeoutError, OSError):
            raise PubloraError("network_outcome_unknown") from None
        if not 200 <= status < 300:
            raise PubloraError("unexpected_http_status", status)
        try:
            result = json.loads(raw.decode("utf-8")) if raw else {}
        except (UnicodeDecodeError, json.JSONDecodeError):
            raise PubloraError("invalid_json_response", status) from None
        if result.get("success") is False:
            raise PubloraError(str(result.get("code") or "provider_rejected"), status)
        return result

    def account_context(self, scheduled_time: datetime | None = None) -> dict[str, Any]:
        path = "/account-context"
        if scheduled_time is not None:
            if scheduled_time.tzinfo is None:
                raise PubloraError("schedule_must_be_timezone_aware")
            query = urllib.parse.urlencode({
                "scheduledTime": scheduled_time.astimezone(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")
            })
            path += "?" + query
        result = self._request("GET", path)
        context = result.get("context")
        if not isinstance(context, dict):
            raise PubloraError("invalid_account_context")
        return context

    def check_schedule_quota(self, platform: str, scheduled_time: datetime) -> dict[str, Any]:
        context = self.account_context(scheduled_time)
        if context.get("features", {}).get("publishing") is not True:
            raise PubloraError("publishing_feature_unavailable")
        if context.get("features", {}).get("apiAccess") is not True:
            raise PubloraError("api_access_unavailable")
        allowed = context.get("allowedPlatforms")
        if isinstance(allowed, list) and platform not in allowed:
            raise PubloraError("platform_not_available_on_plan")
        quotas = context.get("quotas", {})
        monthly = quotas.get("monthlyPosts", {})
        scheduled = quotas.get("scheduledPosts", {})
        if monthly.get("remaining") is not None and monthly.get("remaining") < 1:
            raise PubloraError("monthly_post_quota_exhausted")
        if scheduled.get("remaining") is not None and scheduled.get("remaining") < 1:
            raise PubloraError("scheduled_queue_full")
        horizon = quotas.get("scheduleHorizon", {})
        max_date = horizon.get("maxScheduledDate")
        if max_date:
            try:
                max_dt = datetime.fromisoformat(max_date.replace("Z", "+00:00"))
            except (TypeError, ValueError):
                raise PubloraError("invalid_schedule_horizon_response") from None
            if scheduled_time.astimezone(timezone.utc) > max_dt.astimezone(timezone.utc):
                raise PubloraError("schedule_exceeds_provider_horizon")
        return context

    def list_connections(self) -> list[dict[str, Any]]:
        result = self._request("GET", "/platform-connections")
        connections = result.get("connections")
        if not isinstance(connections, list):
            raise PubloraError("invalid_connections_response")
        return connections

    @staticmethod
    def _normalize_handle(value: str | None) -> str:
        return (value or "").strip().lower().removeprefix("@")

    def resolve_connection(self, platform: str, handle: str) -> dict[str, Any]:
        expected = self._normalize_handle(handle)
        matches = [
            item for item in self.list_connections()
            if str(item.get("platformId", "")).startswith(platform.lower() + "-")
            and self._normalize_handle(item.get("username")) == expected
        ]
        if len(matches) != 1:
            raise PubloraError("target_connection_not_unique")
        connection = matches[0]
        if connection.get("connectionStatus") != "active":
            raise PubloraError("target_connection_not_active")
        if connection.get("tokenStatus") not in {"valid", "active", "ok"}:
            raise PubloraError("target_token_not_verified")
        return connection

    def create_draft(
        self,
        content: str,
        platform_id: str,
        *,
        idempotency_key: str,
        platform_settings: dict[str, Any] | None = None,
    ) -> str:
        if not content.strip():
            raise PubloraError("empty_post_content")
        if not idempotency_key.strip():
            raise PubloraError("missing_idempotency_key")
        body: dict[str, Any] = {"content": content, "platforms": [platform_id]}
        if platform_settings:
            body["platformSettings"] = platform_settings
        result = self._request(
            "POST", "/create-post", body, idempotency_key=idempotency_key
        )
        post_group_id = result.get("postGroupId")
        if not isinstance(post_group_id, str) or not post_group_id:
            raise PubloraError("missing_post_group_id")
        return post_group_id

    def upload_media(self, post_group_id: str, media_path: Path) -> dict[str, Any]:
        if not media_path.is_file():
            raise PubloraError("media_file_missing")
        mime_type = mimetypes.guess_type(media_path.name)[0] or "application/octet-stream"
        if not (mime_type.startswith("image/") or mime_type.startswith("video/")):
            raise PubloraError("unsupported_media_type")
        upload = self._request(
            "POST",
            "/get-upload-url",
            {
                "fileName": media_path.name,
                "contentType": mime_type,
                "postGroupId": post_group_id,
                "type": "image" if mime_type.startswith("image/") else "video",
            },
        )
        upload_url = upload.get("uploadUrl")
        if not isinstance(upload_url, str):
            raise PubloraError("missing_upload_url")
        parsed = urllib.parse.urlparse(upload_url)
        if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
            raise PubloraError("unsafe_upload_url")
        data = media_path.read_bytes()
        request = urllib.request.Request(
            upload_url,
            data=data,
            headers={"Content-Type": mime_type},
            method="PUT",
        )
        try:
            with self.opener(request, timeout=120) as response:
                status = getattr(response, "status", 200)
                response.read()
        except (urllib.error.URLError, TimeoutError, OSError):
            raise PubloraError("media_upload_outcome_unknown") from None
        if not 200 <= status < 300:
            raise PubloraError("media_upload_failed", status)
        media_id = upload.get("mediaId")
        if not isinstance(media_id, str) or not media_id:
            raise PubloraError("missing_media_id")
        self.complete_media(media_id)
        post = self.get_post(post_group_id)
        group = post.get("postGroup", post.get("post", post))
        media_items = group.get("media") if isinstance(group, dict) else None
        media_items = media_items if isinstance(media_items, list) else post.get("media", [])
        matching = [item for item in media_items if item.get("mediaId") == media_id]
        if len(matching) != 1 or matching[0].get("status") != "ready":
            raise PubloraError("uploaded_media_not_ready")
        return {"mediaId": media_id, "fileUrl": upload.get("fileUrl"), "status": "ready"}

    def complete_media(self, media_id: str, max_attempts: int = 3) -> dict[str, Any]:
        safe_id = urllib.parse.quote(media_id, safe="")
        for attempt in range(max_attempts):
            try:
                result = self._request("POST", f"/complete-media/{safe_id}")
            except PubloraError as exc:
                if exc.code == "MEDIA_VALIDATION_PENDING" and attempt < max_attempts - 1:
                    time.sleep(min(2 ** (attempt + 1), 8))
                    continue
                raise
            media_file = result.get("mediaFile", {})
            if media_file.get("status") == "ready":
                return media_file
            if media_file.get("status") == "failed":
                raise PubloraError("media_validation_failed")
            if result.get("retryable") is True and result.get("nextAction") == "WAIT_AND_RETRY_SAME_MEDIA" and attempt < max_attempts - 1:
                delay = result.get("retryAfterSec", 2)
                time.sleep(min(max(int(delay), 1), 10))
                continue
            raise PubloraError("media_not_ready")
        raise PubloraError("media_validation_timeout")

    def schedule_draft(
        self,
        post_group_id: str,
        scheduled_time: datetime,
        *,
        idempotency_key: str,
        now: datetime | None = None,
        max_days: int = 7,
    ) -> dict[str, Any]:
        if scheduled_time.tzinfo is None:
            raise PubloraError("schedule_must_be_timezone_aware")
        current = now or datetime.now(timezone.utc)
        target = scheduled_time.astimezone(timezone.utc)
        if target <= current.astimezone(timezone.utc):
            raise PubloraError("schedule_must_be_in_future")
        if target > current.astimezone(timezone.utc) + timedelta(days=max_days):
            raise PubloraError("schedule_exceeds_plan_horizon")
        safe_id = urllib.parse.quote(post_group_id, safe="")
        return self._request(
            "PUT",
            f"/update-post/{safe_id}",
            {"status": "scheduled", "scheduledTime": target.isoformat(timespec="milliseconds").replace("+00:00", "Z")},
            idempotency_key=idempotency_key,
        )

    def get_post(self, post_group_id: str) -> dict[str, Any]:
        safe_id = urllib.parse.quote(post_group_id, safe="")
        return self._request("GET", f"/get-post/{safe_id}")


def stable_idempotency_key(content_id: str, profile_id: str, operation: str) -> str:
    payload = "\0".join((content_id, profile_id, operation)).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()
