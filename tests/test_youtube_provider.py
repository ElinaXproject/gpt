import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from autored.providers.youtube import (
    EXPECTED_MEMORY_AGENT_CHANNEL_ID,
    YouTubeError,
    YouTubeUploader,
)


class FakeResponse:
    def __init__(self, payload=None, status=200, headers=None):
        self.payload = payload or {}
        self.status = status
        self.headers = headers or {}

    def read(self):
        return json.dumps(self.payload).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


class YouTubeUploaderTests(unittest.TestCase):
    def metadata(self):
        scheduled = datetime.now(timezone.utc) + timedelta(hours=2)
        return {
            "title": "Test title",
            "description": "A short description for a test upload.",
            "tags": ["AI", "technology"],
            "made_for_kids": False,
            "ai_generated": True,
            "privacy": "public",
            "scheduled_time": scheduled.isoformat(),
        }

    def test_public_upload_is_blocked_until_api_audit(self):
        calls = []
        def opener(request, timeout=60):
            calls.append(request)
            return FakeResponse()
        with tempfile.TemporaryDirectory() as tmp:
            media = Path(tmp) / "test.mp4"
            media.write_bytes(b"video")
            client = YouTubeUploader(
                client_id="id", client_secret="secret", refresh_token="refresh",
                api_audited=False, opener=opener
            )
            with self.assertRaisesRegex(YouTubeError, "youtube_api_audit_required_for_public"):
                client.upload_and_schedule(self.metadata(), media)
        self.assertEqual([], calls)

    def test_upload_verifies_channel_and_scheduled_private_state(self):
        metadata = self.metadata()
        scheduled = datetime.fromisoformat(metadata["scheduled_time"])
        expected_publish_at = scheduled.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
        responses = [
            FakeResponse({"access_token": "access-token"}),
            FakeResponse({"items": [{"id": EXPECTED_MEMORY_AGENT_CHANNEL_ID}]}),
            FakeResponse({}, status=200, headers={"Location": "https://www.googleapis.com/upload/youtube/v3/videos?upload_id=1"}),
            FakeResponse({
                "id": "video-123",
                "status": {"privacyStatus": "private", "publishAt": expected_publish_at}
            }, status=200),
        ]
        captured = []
        def opener(request, timeout=60):
            captured.append(request)
            return responses.pop(0)
        with tempfile.TemporaryDirectory() as tmp:
            media = Path(tmp) / "test.mp4"
            media.write_bytes(b"video-bytes")
            client = YouTubeUploader(
                client_id="id", client_secret="secret", refresh_token="refresh",
                api_audited=True, opener=opener
            )
            result = client.upload_and_schedule(metadata, media)
        self.assertEqual("scheduled", result["status"])
        self.assertEqual("video-123", result["video_id"])
        self.assertEqual(EXPECTED_MEMORY_AGENT_CHANNEL_ID, result["channel_id"])
        self.assertEqual(4, len(captured))
        upload_body = json.loads(captured[2].data.decode("utf-8"))
        self.assertTrue(upload_body["status"]["containsSyntheticMedia"])
        self.assertEqual("private", upload_body["status"]["privacyStatus"])
        self.assertEqual("PUT", captured[3].get_method())
        self.assertIn("content-range", {name.lower() for name, _value in captured[3].header_items()})

    def test_untrusted_resumable_upload_host_is_rejected(self):
        metadata = self.metadata()
        responses = [
            FakeResponse({"access_token": "access-token"}),
            FakeResponse({"items": [{"id": EXPECTED_MEMORY_AGENT_CHANNEL_ID}]}),
            FakeResponse({}, status=200, headers={"Location": "https://attacker.example/session/1"}),
        ]
        def opener(request, timeout=60):
            return responses.pop(0)
        with tempfile.TemporaryDirectory() as tmp:
            media = Path(tmp) / "test.mp4"
            media.write_bytes(b"video-bytes")
            client = YouTubeUploader(
                client_id="id", client_secret="secret", refresh_token="refresh",
                api_audited=True, opener=opener
            )
            with self.assertRaisesRegex(YouTubeError, "unsafe_resumable_upload_url"):
                client.upload_and_schedule(metadata, media)

    def test_wrong_channel_id_blocks_before_upload(self):
        responses = [
            FakeResponse({"access_token": "access-token"}),
            FakeResponse({"items": [{"id": "wrong-channel"}]}),
        ]
        def opener(request, timeout=60):
            return responses.pop(0)
        with tempfile.TemporaryDirectory() as tmp:
            media = Path(tmp) / "test.mp4"
            media.write_bytes(b"video")
            client = YouTubeUploader(
                client_id="id", client_secret="secret", refresh_token="refresh",
                api_audited=True, opener=opener
            )
            with self.assertRaisesRegex(YouTubeError, "youtube_channel_id_mismatch"):
                client.upload_and_schedule(self.metadata(), media)

    def test_missing_made_for_kids_declaration_is_blocked(self):
        with tempfile.TemporaryDirectory() as tmp:
            media = Path(tmp) / "test.mp4"
            media.write_bytes(b"video")
            metadata = self.metadata()
            metadata.pop("made_for_kids")
            client = YouTubeUploader(
                client_id="id", client_secret="secret", refresh_token="refresh",
                api_audited=True, opener=lambda *_args, **_kwargs: FakeResponse()
            )
            with self.assertRaisesRegex(YouTubeError, "made_for_kids_declaration_required"):
                client.upload_and_schedule(metadata, media)


if __name__ == "__main__":
    unittest.main()
