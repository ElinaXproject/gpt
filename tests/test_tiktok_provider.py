import json
import tempfile
import unittest
from pathlib import Path

from autored.providers.tiktok import TikTokDirectPublisher, TikTokError


class FakeResponse:
    def __init__(self, payload=None, status=200):
        self.payload = payload or {}
        self.status = status

    def read(self):
        return json.dumps(self.payload).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


class FakeTokenStore:
    def __init__(self, token="refresh-1"):
        self.token = token
        self.saved = []

    def get_refresh_token(self, profile_id):
        return self.token

    def save_refresh_token(self, profile_id, refresh_token):
        self.saved.append((profile_id, refresh_token))
        self.token = refresh_token


class TikTokDirectPublisherTests(unittest.TestCase):
    def publisher(self, responses, *, audited=False, username="pieknemedia", store=None, captured=None):
        queue = list(responses)
        captured = captured if captured is not None else []
        def opener(request, timeout=60):
            captured.append(request)
            return queue.pop(0)
        return TikTokDirectPublisher(
            client_key="client-key",
            client_secret="client-secret",
            profile_id="tiktok_pieknemedia",
            expected_username=username,
            token_store=store or FakeTokenStore(),
            app_audited=audited,
            opener=opener,
            sleep=lambda _seconds: None,
        ), captured

    def creator_info(self, username="pieknemedia"):
        return {"data": {
            "creator_username": username,
            "privacy_level_options": ["SELF_ONLY", "PUBLIC_TO_EVERYONE"],
            "max_video_post_duration_sec": 60
        }}

    def test_unaudited_app_cannot_publish_publicly(self):
        publisher, captured = self.publisher([
            FakeResponse({"access_token": "access", "refresh_token": "refresh-2"}),
            FakeResponse(self.creator_info()),
        ], audited=False)
        with tempfile.TemporaryDirectory() as tmp:
            media = Path(tmp) / "clip.mp4"
            media.write_bytes(b"video")
            with self.assertRaisesRegex(TikTokError, "unaudited_app_public_post_blocked"):
                publisher.publish_video(
                    media_path=media, title="Test", privacy_level="PUBLIC_TO_EVERYONE", duration_seconds=20
                )
        self.assertEqual(2, len(captured))

    def test_unaudited_app_can_only_use_supported_private_visibility(self):
        store = FakeTokenStore()
        responses = [
            FakeResponse({"access_token": "access", "refresh_token": "refresh-2"}),
            FakeResponse(self.creator_info()),
            FakeResponse({"data": {"publish_id": "publish-1", "upload_url": "https://upload.tiktok.test/session/1"}}),
            FakeResponse({}, status=201),
            FakeResponse({"data": {"status": "PUBLISH_COMPLETE"}}),
        ]
        publisher, captured = self.publisher(responses, audited=False, store=store)
        with tempfile.TemporaryDirectory() as tmp:
            media = Path(tmp) / "clip.mp4"
            media.write_bytes(b"video-bytes")
            result = publisher.publish_video(
                media_path=media, title="Test caption", privacy_level="SELF_ONLY", duration_seconds=20
            )
        self.assertEqual("published", result["status"])
        self.assertEqual("publish-1", result["publish_id"])
        self.assertEqual([("tiktok_pieknemedia", "refresh-2")], store.saved)
        self.assertIn("/video/init/", captured[2].full_url)
        upload_headers = {name.lower(): value for name, value in captured[3].header_items()}
        self.assertEqual("bytes 0-10/11", upload_headers["content-range"])

    def test_creator_account_mismatch_blocks_before_video_init(self):
        responses = [
            FakeResponse({"access_token": "access"}),
            FakeResponse(self.creator_info("other-account")),
        ]
        publisher, captured = self.publisher(responses, audited=True)
        with tempfile.TemporaryDirectory() as tmp:
            media = Path(tmp) / "clip.mp4"
            media.write_bytes(b"video")
            with self.assertRaisesRegex(TikTokError, "creator_account_mismatch"):
                publisher.publish_video(
                    media_path=media, title="Test", privacy_level="PUBLIC_TO_EVERYONE", duration_seconds=20
                )
        self.assertEqual(2, len(captured))

    def test_audited_app_can_publish_public_when_creator_allows_it(self):
        responses = [
            FakeResponse({"access_token": "access"}),
            FakeResponse(self.creator_info()),
            FakeResponse({"data": {"publish_id": "publish-2", "upload_url": "https://upload.tiktok.test/session/2"}}),
            FakeResponse({}, status=201),
            FakeResponse({"data": {"status": "PUBLISH_COMPLETE"}}),
        ]
        publisher, _ = self.publisher(responses, audited=True)
        with tempfile.TemporaryDirectory() as tmp:
            media = Path(tmp) / "clip.mp4"
            media.write_bytes(b"video")
            result = publisher.publish_video(
                media_path=media, title="Test", privacy_level="PUBLIC_TO_EVERYONE", duration_seconds=20
            )
        self.assertEqual("published", result["status"])

    def test_pending_publish_is_not_reported_as_complete(self):
        responses = [
            FakeResponse({"access_token": "access"}),
            FakeResponse(self.creator_info()),
            FakeResponse({"data": {"publish_id": "publish-3", "upload_url": "https://upload.tiktok.test/session/3"}}),
            FakeResponse({}, status=201),
            FakeResponse({"data": {"status": "PROCESSING_UPLOAD"}}),
            FakeResponse({"data": {"status": "PROCESSING_DOWNLOAD"}}),
        ]
        publisher, _ = self.publisher(responses, audited=True)
        with tempfile.TemporaryDirectory() as tmp:
            media = Path(tmp) / "clip.mp4"
            media.write_bytes(b"video")
            result = publisher.publish_video(
                media_path=media, title="Test", privacy_level="PUBLIC_TO_EVERYONE",
                duration_seconds=20, poll_attempts=2
            )
        self.assertEqual("pending", result["status"])


if __name__ == "__main__":
    unittest.main()
