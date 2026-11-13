import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from create_publication_manifest import build_manifest


class FakeD1:
    def __init__(self, item):
        self.item = item

    def get_publishable_content(self, content_id, profile_id, provider):
        self.asserted = (content_id, profile_id, provider)
        return self.item


class CreatePublicationManifestTests(unittest.TestCase):
    def make_item(self, media):
        return {
            "title": "Technology explainer",
            "description": "A concise explainer.",
            "hashtags_json": json.dumps(["#AI", "technology"]),
            "ai_disclosure_required": 1,
            "ai_disclosure_set": 1,
            "media_mime": "video/mp4",
            "media_bytes": media.stat().st_size,
            "media_sha256": hashlib.sha256(media.read_bytes()).hexdigest(),
            "music_embedded": 1,
            "music_license_reference": "licensed-original-track",
        }

    def test_tiktok_manifest_defaults_to_private_and_binds_licensed_audio(self):
        with tempfile.TemporaryDirectory() as tmp:
            media = Path(tmp) / "clip.mp4"
            media.write_bytes(b"video-bytes")
            with patch("create_publication_manifest.validate_tiktok_video", return_value={"duration_seconds": 20.2}):
                manifest = build_manifest(
                    d1=FakeD1(self.make_item(media)),
                    content_id="content-1",
                    profile_id="tiktok_pieknemedia",
                    provider="tiktok_direct",
                    media_path=media,
                    scheduled_at="2026-11-14T12:00:00Z",
                )
        self.assertEqual("SELF_ONLY", manifest["privacy_level"])
        self.assertTrue(manifest["music_embedded"])
        self.assertEqual("licensed-original-track", manifest["music_license_reference"])
        self.assertEqual(21, manifest["duration_seconds"])
        self.assertIn("#AI", manifest["caption"])

    def test_youtube_manifest_requires_explicit_audience_classification(self):
        with tempfile.TemporaryDirectory() as tmp:
            media = Path(tmp) / "clip.mp4"
            media.write_bytes(b"video-bytes")
            with patch("create_publication_manifest.validate_youtube_video", return_value={"width":1080,"height":1920,"duration_seconds":120}):
                with self.assertRaisesRegex(ValueError, "youtube_audience_classification_required"):
                    build_manifest(
                        d1=FakeD1(self.make_item(media)),
                        content_id="content-1",
                        profile_id="youtube_memoryagent",
                        provider="youtube_direct",
                        media_path=media,
                        scheduled_at="2026-11-14T12:00:00Z",
                    )

    def test_youtube_manifest_marks_vertical_short_and_carries_disclosure(self):
        with tempfile.TemporaryDirectory() as tmp:
            media = Path(tmp) / "clip.mp4"
            media.write_bytes(b"video-bytes")
            with patch("create_publication_manifest.validate_youtube_video", return_value={"width":1080,"height":1920,"duration_seconds":120}):
                manifest = build_manifest(
                    d1=FakeD1(self.make_item(media)),
                    content_id="content-1",
                    profile_id="youtube_memoryagent",
                    provider="youtube_direct",
                    media_path=media,
                    scheduled_at="2026-11-14T12:00:00Z",
                    made_for_kids=False,
                )
        self.assertEqual("short", manifest["format_type"])
        self.assertTrue(manifest["ai_generated"])
        self.assertFalse(manifest["made_for_kids"])
        self.assertEqual(["AI", "technology"], manifest["tags"])


if __name__ == "__main__":
    unittest.main()
