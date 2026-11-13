"""TikTok Content Posting API Direct Post adapter.

Requires an owner-authorized OAuth token with video.publish scope.
Unaudited apps are restricted to SELF_ONLY; public posting is hard-blocked.
"""
from __future__ import annotations

import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Protocol


TIKTOK_API = "https://open.tiktokapis.com"
TIKTOK_TOKEN_URL = TIKTOK_API + "/v2/oauth/token/"
CREATOR_INFO_URL = TIKTOK_API + "/v2/post/publish/creator_info/query/"
VIDEO_INIT_URL = TIKTOK_API + "/v2/post/publish/video/init/"
STATUS_URL = TIKTOK_API + "/v2/post/publish/status/fetch/"
MIN_CHUNK_SIZE = 5 * 1024 * 1024
CHUNK_SIZE = 10 * 1024 * 1024
MAX_CHUNK_SIZE = 64 * 1024 * 1024
MAX_FINAL_CHUNK_SIZE = 128 * 1024 * 1024
MAX_VIDEO_SIZE = 4 * 1024 * 1024 * 1024


class TokenStore(Protocol):
    def get_refresh_token(self, profile_id: str) -> str: ...
    def save_refresh_token(self, profile_id: str, refresh_token: str) -> None: ...


class TikTokError(RuntimeError):
    def __init__(self, code: str, status: int | None = None):
        self.code = code
        self.status = status
        super().__init__("tiktok_" + code + (f"_http_{status}" if status else ""))


class TikTokDirectPublisher:
    def __init__(
        self,
        *,
        client_key: str | None = None,
        client_secret: str | None = None,
        profile_id: str,
        expected_username: str,
        token_store: TokenStore,
        app_audited: bool | None = None,
        opener=None,
        sleep=time.sleep,
    ):
        self.client_key = client_key or os.environ.get("TIKTOK_CLIENT_KEY", "")
        self.client_secret = client_secret or os.environ.get("TIKTOK_CLIENT_SECRET", "")
        self.profile_id = profile_id
        self.expected_username = expected_username.lstrip("@").casefold()
        self.token_store = token_store
        self.app_audited = app_audited if app_audited is not None else os.environ.get("TIKTOK_APP_AUDITED", "").lower() == "true"
        self.opener = opener or urllib.request.urlopen
        self.sleep = sleep
        if not self.client_key or not self.client_secret:
            raise TikTokError("oauth_client_credentials_missing")

    def _open(self, request: urllib.request.Request, timeout: int = 60):
        try:
            return self.opener(request, timeout=timeout)
        except urllib.error.HTTPError as exc:
            raise TikTokError("provider_rejected", exc.code) from None
        except (urllib.error.URLError, TimeoutError, OSError):
            raise TikTokError("network_outcome_unknown") from None

    def _json_request(self, url: str, token: str, body: dict[str, Any]) -> dict[str, Any]:
        request = urllib.request.Request(
            url,
            data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
            headers={
                "Authorization": "Bearer " + token,
                "Content-Type": "application/json; charset=UTF-8",
                "Accept": "application/json",
            },
            method="POST",
        )
        with self._open(request, timeout=45) as response:
            status = getattr(response, "status", 200)
            raw = response.read()
        if not 200 <= status < 300:
            raise TikTokError("api_request_failed", status)
        try:
            payload = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            raise TikTokError("invalid_json_response") from None
        error = payload.get("error", {})
        if error and error.get("code") not in {None, "ok"}:
            raise TikTokError(str(error.get("code")))
        return payload.get("data", payload)

    def refresh_access_token(self) -> str:
        refresh_token = self.token_store.get_refresh_token(self.profile_id)
        if not refresh_token:
            raise TikTokError("refresh_token_missing")
        body = urllib.parse.urlencode({
            "client_key": self.client_key,
            "client_secret": self.client_secret,
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
        }).encode("utf-8")
        request = urllib.request.Request(
            TIKTOK_TOKEN_URL,
            data=body,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            method="POST",
        )
        with self._open(request, timeout=30) as response:
            status = getattr(response, "status", 200)
            raw = response.read()
        if not 200 <= status < 300:
            raise TikTokError("oauth_refresh_failed", status)
        try:
            payload = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            raise TikTokError("oauth_invalid_json") from None
        if payload.get("error"):
            raise TikTokError(str(payload.get("error")))
        access_token = payload.get("access_token")
        if not isinstance(access_token, str) or not access_token:
            raise TikTokError("access_token_missing")
        rotated = payload.get("refresh_token")
        if isinstance(rotated, str) and rotated and rotated != refresh_token:
            self.token_store.save_refresh_token(self.profile_id, rotated)
        return access_token

    def get_creator_info(self, access_token: str) -> dict[str, Any]:
        return self._json_request(CREATOR_INFO_URL, access_token, {})

    def get_publish_status(self, publish_id: str) -> str:
        if not isinstance(publish_id, str) or not publish_id:
            raise TikTokError("publish_id_missing")
        access_token = self.refresh_access_token()
        payload = self._json_request(STATUS_URL, access_token, {"publish_id": publish_id})
        status = payload.get("status")
        if not isinstance(status, str) or not status:
            raise TikTokError("publish_status_missing")
        return status

    def _validate_creator(self, creator: dict[str, Any], privacy_level: str, duration_seconds: int) -> None:
        username = str(creator.get("creator_username", "")).lstrip("@").casefold()
        if username != self.expected_username:
            raise TikTokError("creator_account_mismatch")
        options = creator.get("privacy_level_options", [])
        if privacy_level not in options:
            raise TikTokError("privacy_level_not_available")
        if not self.app_audited and privacy_level != "SELF_ONLY":
            raise TikTokError("unaudited_app_public_post_blocked")
        max_duration = creator.get("max_video_post_duration_sec")
        if isinstance(max_duration, (int, float)) and duration_seconds > max_duration:
            raise TikTokError("video_duration_exceeds_creator_limit")

    def publish_video(
        self,
        *,
        media_path: Path,
        title: str,
        privacy_level: str = "PUBLIC_TO_EVERYONE",
        duration_seconds: int,
        scheduled_at,
        music_embedded: bool,
        music_license_reference: str,
        ai_generated: bool = True,
        disable_comment: bool = False,
        disable_duet: bool = False,
        disable_stitch: bool = False,
        poll_attempts: int = 6,
    ) -> dict[str, Any]:
        if not media_path.is_file():
            raise TikTokError("media_file_missing")
        size = media_path.stat().st_size
        if size < 1 or size > MAX_VIDEO_SIZE:
            raise TikTokError("media_size_out_of_bounds")
        if not isinstance(title, str) or not title.strip() or len(title) > 2200:
            raise TikTokError("invalid_caption")
        if not isinstance(duration_seconds, int) or duration_seconds < 1 or duration_seconds > 600:
            raise TikTokError("invalid_duration")
        if not hasattr(scheduled_at, "tzinfo") or scheduled_at.tzinfo is None:
            raise TikTokError("scheduled_time_must_be_timezone_aware")
        if scheduled_at.timestamp() > time.time():
            raise TikTokError("publication_not_due")
        if music_embedded is not True or not isinstance(music_license_reference, str) or not music_license_reference.strip():
            raise TikTokError("licensed_embedded_music_required")

        access_token = self.refresh_access_token()
        creator = self.get_creator_info(access_token)
        self._validate_creator(creator, privacy_level, duration_seconds)

        if size <= MAX_CHUNK_SIZE:
            chunk_size = size
            total_chunks = 1
        else:
            chunk_size = CHUNK_SIZE
            total_chunks = size // chunk_size
            final_chunk_size = size - chunk_size * (total_chunks - 1)
            if (
                total_chunks < 2
                or total_chunks > 1000
                or final_chunk_size < MIN_CHUNK_SIZE
                or final_chunk_size > MAX_FINAL_CHUNK_SIZE
            ):
                raise TikTokError("invalid_chunk_plan")
        init_data = self._json_request(VIDEO_INIT_URL, access_token, {
            "post_info": {
                "title": title,
                "privacy_level": privacy_level,
                "disable_comment": disable_comment,
                "disable_duet": disable_duet,
                "disable_stitch": disable_stitch,
                "is_aigc": ai_generated,
            },
            "source_info": {
                "source": "FILE_UPLOAD",
                "video_size": size,
                "chunk_size": chunk_size,
                "total_chunk_count": total_chunks,
            },
        })
        publish_id = init_data.get("publish_id")
        upload_url = init_data.get("upload_url")
        if not isinstance(publish_id, str) or not publish_id or not isinstance(upload_url, str):
            raise TikTokError("upload_session_missing")
        parsed = urllib.parse.urlparse(upload_url)
        allowed_upload_host = bool(
            parsed.hostname
            and (
                parsed.hostname == "open-upload.tiktokapis.com"
                or re.fullmatch(r"upload(?:\.[a-z0-9-]+)?\.tiktokapis\.com", parsed.hostname)
            )
        )
        if (
            parsed.scheme != "https"
            or not allowed_upload_host
            or parsed.username
            or parsed.password
            or parsed.port not in (None, 443)
            or parsed.fragment
        ):
            raise TikTokError("unsafe_upload_url")

        with media_path.open("rb") as media:
            start = 0
            for chunk_index in range(total_chunks):
                current_chunk_size = size - start if chunk_index == total_chunks - 1 else chunk_size
                chunk = media.read(current_chunk_size)
                if len(chunk) != current_chunk_size:
                    raise TikTokError("media_read_failed")
                end = start + len(chunk) - 1
                request = urllib.request.Request(
                    upload_url,
                    data=chunk,
                    headers={
                        "Content-Type": "video/mp4",
                        "Content-Length": str(len(chunk)),
                        "Content-Range": f"bytes {start}-{end}/{size}",
                    },
                    method="PUT",
                )
                with self._open(request, timeout=180) as response:
                    status = getattr(response, "status", 200)
                    response.read()
                expected_status = 201 if chunk_index == total_chunks - 1 else 206
                if status != expected_status:
                    raise TikTokError("chunk_upload_unexpected_status", status)
                start = end + 1
            if start != size:
                raise TikTokError("chunk_upload_incomplete")

        for attempt in range(poll_attempts):
            status_data = self._json_request(STATUS_URL, access_token, {"publish_id": publish_id})
            state = status_data.get("status")
            if state == "PUBLISH_COMPLETE":
                return {"status": "published", "publish_id": publish_id, "creator_username": creator.get("creator_username")}
            if state == "FAILED":
                raise TikTokError("publish_failed")
            if attempt < poll_attempts - 1:
                self.sleep(2)
        return {"status": "pending", "publish_id": publish_id, "creator_username": creator.get("creator_username")}
