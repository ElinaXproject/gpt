"""Native YouTube Data API uploader with OAuth refresh and resumable upload."""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


YOUTUBE_API = "https://www.googleapis.com/youtube/v3"
YOUTUBE_UPLOAD_API = "https://www.googleapis.com/upload/youtube/v3/videos"
OAUTH_TOKEN_URL = "https://oauth2.googleapis.com/token"
EXPECTED_MEMORY_AGENT_CHANNEL_ID = "UCOE1EX9WZGDesaJNYIEhj7g"


class YouTubeError(RuntimeError):
    def __init__(self, code: str, status: int | None = None):
        self.code = code
        self.status = status
        super().__init__("youtube_" + code + (f"_http_{status}" if status else ""))


class YouTubeUploader:
    def __init__(
        self,
        client_id: str | None = None,
        client_secret: str | None = None,
        refresh_token: str | None = None,
        expected_channel_id: str = EXPECTED_MEMORY_AGENT_CHANNEL_ID,
        opener=None,
    ):
        self.client_id = client_id or os.environ.get("YOUTUBE_CLIENT_ID", "")
        self.client_secret = client_secret or os.environ.get("YOUTUBE_CLIENT_SECRET", "")
        self.refresh_token = refresh_token or os.environ.get("YOUTUBE_REFRESH_TOKEN", "")
        self.expected_channel_id = expected_channel_id
        self.opener = opener or urllib.request.urlopen
        if not all((self.client_id, self.client_secret, self.refresh_token)):
            raise YouTubeError("oauth_credentials_missing")

    def _open(self, request: urllib.request.Request, timeout: int = 60):
        try:
            return self.opener(request, timeout=timeout)
        except urllib.error.HTTPError as exc:
            raise YouTubeError("provider_rejected", exc.code) from None
        except (urllib.error.URLError, TimeoutError, OSError):
            raise YouTubeError("network_outcome_unknown") from None

    def refresh_access_token(self) -> str:
        body = urllib.parse.urlencode({
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "refresh_token": self.refresh_token,
            "grant_type": "refresh_token",
        }).encode("utf-8")
        request = urllib.request.Request(
            OAUTH_TOKEN_URL,
            data=body,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            method="POST",
        )
        with self._open(request, timeout=30) as response:
            raw = response.read()
            status = getattr(response, "status", 200)
        if not 200 <= status < 300:
            raise YouTubeError("oauth_refresh_failed", status)
        try:
            payload = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            raise YouTubeError("oauth_invalid_json") from None
        token = payload.get("access_token")
        if not isinstance(token, str) or not token:
            raise YouTubeError("oauth_access_token_missing")
        return token

    def verify_channel(self, access_token: str) -> dict[str, Any]:
        query = urllib.parse.urlencode({"part": "id,snippet", "mine": "true"})
        request = urllib.request.Request(
            f"{YOUTUBE_API}/channels?{query}",
            headers={"Authorization": "Bearer " + access_token, "Accept": "application/json"},
            method="GET",
        )
        with self._open(request, timeout=30) as response:
            raw = response.read()
            status = getattr(response, "status", 200)
        if not 200 <= status < 300:
            raise YouTubeError("channel_verification_failed", status)
        try:
            payload = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            raise YouTubeError("channel_response_invalid_json") from None
        items = payload.get("items", [])
        if len(items) != 1 or items[0].get("id") != self.expected_channel_id:
            raise YouTubeError("youtube_channel_id_mismatch")
        return items[0]

    @staticmethod
    def _validate_metadata(metadata: dict[str, Any], media_path: Path) -> tuple[datetime, dict[str, Any]]:
        title = metadata.get("title")
        description = metadata.get("description", "")
        tags = metadata.get("tags", [])
        made_for_kids = metadata.get("made_for_kids")
        scheduled_time = metadata.get("scheduled_time")
        if not isinstance(title, str) or not title.strip() or len(title) > 100:
            raise YouTubeError("invalid_title")
        if not isinstance(description, str) or len(description) > 5000:
            raise YouTubeError("invalid_description")
        if not isinstance(tags, list) or not all(isinstance(tag, str) and tag for tag in tags):
            raise YouTubeError("invalid_tags")
        if sum(len(tag) + (2 if " " in tag else 0) for tag in tags) + max(0, len(tags) - 1) > 500:
            raise YouTubeError("tags_too_long")
        if not isinstance(made_for_kids, bool):
            raise YouTubeError("made_for_kids_declaration_required")
        if not media_path.is_file():
            raise YouTubeError("media_file_missing")
        if media_path.stat().st_size <= 0 or media_path.stat().st_size > 200 * 1024 * 1024:
            raise YouTubeError("media_size_out_of_project_bounds")
        if not isinstance(scheduled_time, str):
            raise YouTubeError("scheduled_time_required")
        try:
            scheduled = datetime.fromisoformat(scheduled_time.replace("Z", "+00:00"))
        except ValueError:
            raise YouTubeError("invalid_scheduled_time") from None
        if scheduled.tzinfo is None or scheduled <= datetime.now(timezone.utc):
            raise YouTubeError("scheduled_time_must_be_future_and_timezone_aware")
        if metadata.get("privacy", "public") != "public":
            raise YouTubeError("scheduled_publication_requires_public_target")
        status: dict[str, Any] = {
            "privacyStatus": "private",
            "publishAt": scheduled.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
            "selfDeclaredMadeForKids": made_for_kids,
        }
        if metadata.get("ai_generated") is True:
            status["containsSyntheticMedia"] = True
        snippet = {
            "title": title,
            "description": description,
            "tags": tags,
            "categoryId": str(metadata.get("category_id", "28")),
            "defaultLanguage": "pl",
        }
        return scheduled, {"snippet": snippet, "status": status}

    def upload_and_schedule(self, metadata: dict[str, Any], media_path: Path) -> dict[str, Any]:
        scheduled, body = self._validate_metadata(metadata, media_path)
        access_token = self.refresh_access_token()
        channel = self.verify_channel(access_token)
        size = media_path.stat().st_size
        mime_type = "video/mp4"
        query = urllib.parse.urlencode({"uploadType": "resumable", "part": "snippet,status"})
        request = urllib.request.Request(
            f"{YOUTUBE_UPLOAD_API}?{query}",
            data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
            headers={
                "Authorization": "Bearer " + access_token,
                "Content-Type": "application/json; charset=UTF-8",
                "X-Upload-Content-Type": mime_type,
                "X-Upload-Content-Length": str(size),
            },
            method="POST",
        )
        with self._open(request, timeout=30) as response:
            status = getattr(response, "status", 200)
            upload_url = response.headers.get("Location")
            response.read()
        if status not in {200, 201} or not upload_url:
            raise YouTubeError("resumable_session_not_created", status)
        parsed = urllib.parse.urlparse(upload_url)
        if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
            raise YouTubeError("unsafe_resumable_upload_url")

        data = media_path.read_bytes()
        upload_request = urllib.request.Request(
            upload_url,
            data=data,
            headers={
                "Authorization": "Bearer " + access_token,
                "Content-Type": mime_type,
                "Content-Length": str(size),
                "Content-Range": f"bytes 0-{size - 1}/{size}",
            },
            method="PUT",
        )
        try:
            with self._open(upload_request, timeout=180) as response:
                upload_status = getattr(response, "status", 200)
                raw = response.read()
        except YouTubeError as exc:
            if exc.code == "network_outcome_unknown":
                raise YouTubeError("upload_outcome_unknown_manual_reconciliation_required") from None
            raise
        if upload_status == 308:
            raise YouTubeError("upload_incomplete_resume_required", upload_status)
        if upload_status not in {200, 201}:
            raise YouTubeError("upload_failed", upload_status)
        try:
            uploaded = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            raise YouTubeError("upload_response_invalid_json") from None
        video_id = uploaded.get("id")
        if not isinstance(video_id, str) or not video_id:
            raise YouTubeError("video_id_missing")
        return {
            "status": "scheduled",
            "video_id": video_id,
            "channel_id": channel["id"],
            "scheduled_time": scheduled.astimezone(timezone.utc).isoformat(),
            "privacy_status": uploaded.get("status", {}).get("privacyStatus", "private"),
        }
