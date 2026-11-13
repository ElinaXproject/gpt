import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from publora_client import PubloraError
from autored.d1_client import D1Error
from publora_pipeline import process_manifest, validate_manifest


class FakeClient:
    def __init__(self, schedule_error=None, post_status="scheduled"):
        self.calls = []
        self.schedule_error = schedule_error
        self.post_status = post_status

    def resolve_connection(self, platform, handle):
        self.calls.append(("resolve", platform, handle))
        return {"platformId": f"{platform}-connected", "connectionStatus": "active"}

    def test_connection(self, platform_id):
        self.calls.append(("test", platform_id))
        return {"status": "ok"}

    def create_draft(self, content, platform_id, *, idempotency_key, platform_settings=None):
        self.calls.append(("draft", content, platform_id, idempotency_key, platform_settings))
        return "group-1"

    def upload_media(self, post_group_id, media_path):
        self.calls.append(("upload", post_group_id, media_path))
        return {"mediaId": "media-1"}

    def schedule_draft(self, post_group_id, scheduled_time, *, idempotency_key):
        self.calls.append(("schedule", post_group_id, scheduled_time, idempotency_key))
        if self.schedule_error:
            raise self.schedule_error
        return {"status": "scheduled"}

    def get_post(self, post_group_id):
        self.calls.append(("get", post_group_id))
        return {"postGroup": {"status": self.post_status}}



class FakeJobStore:
    def __init__(self, error=None):
        self.error = error
        self.record = None

    def record_scheduled(self, **kwargs):
        if self.error:
            raise self.error
        self.record = kwargs
        return {"job_id": "job-test", "job_status": "planned"}


class PubloraPipelineTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.media = Path(self.temp.name) / "clip.mp4"
        self.media.write_bytes(b"test-video")
        self.base = {
            "content_id": "content-001",
            "profile_id": "tiktok_pieknemedia",
            "platform": "tiktok",
            "handle": "@pieknemedia",
            "content": "Test caption",
            "media_path": str(self.media),
            "media_mime": "video/mp4",
            "scheduled_time": (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat(),
            "rights_reference": "original-or-licensed",
            "safety_review_status": "passed",
            "ai_disclosure_required": True,
            "ai_disclosure_set": True,
            "ai_generated": True,
            "music_license_reference": "license-record-001",
            "music_embedded": True,
        }

    def tearDown(self):
        self.temp.cleanup()

    def test_tiktok_video_requires_embedded_licensed_music(self):
        item = dict(self.base, music_license_reference="", music_embedded=False)
        with self.assertRaisesRegex(PubloraError, "tiktok_video_music_missing"):
            validate_manifest(item)

    def test_tiktok_photo_enables_automatic_music(self):
        photo = Path(self.temp.name) / "photo.jpg"
        photo.write_bytes(b"test-image")
        item = dict(self.base, media_path=str(photo), media_mime="image/jpeg")
        item.pop("music_license_reference")
        item.pop("music_embedded")
        _, validated = validate_manifest(item)
        self.assertTrue(validated["platform_settings"]["tiktok"]["autoAddMusic"])

    def test_ai_disclosure_gate_blocks_missing_disclosure(self):
        item = dict(self.base, ai_disclosure_set=False)
        with self.assertRaisesRegex(PubloraError, "missing_ai_disclosure"):
            validate_manifest(item)

    def test_profile_handle_is_exact(self):
        item = dict(self.base, handle="@pieknemedia-extra")
        with self.assertRaisesRegex(PubloraError, "profile_handle_mismatch"):
            validate_manifest(item)

    def test_youtube_requires_explicit_audience_declaration_and_title(self):
        item = dict(
            self.base,
            profile_id="youtube_memoryagent",
            platform="youtube",
            handle="@MemoryAgent-r3c",
            title="Memory Agent test",
            privacy="private",
            media_mime="video/mp4",
            made_for_kids=None,
        )
        with self.assertRaisesRegex(PubloraError, "youtube_made_for_kids_declaration_required"):
            validate_manifest(item)

    def test_successful_pipeline_creates_draft_uploads_then_schedules(self):
        client = FakeClient()
        result = process_manifest(client, self.base)
        self.assertEqual("scheduled", result["status"])
        self.assertEqual(
            ["resolve", "test", "draft", "upload", "schedule"],
            [call[0] for call in client.calls]
        )
        settings = client.calls[2][4]
        self.assertTrue(settings["tiktok"]["aiGenerated"])


    def test_successful_schedule_is_persisted_to_d1_job_store(self):
        client = FakeClient()
        job_store = FakeJobStore()
        result = process_manifest(client, self.base, job_store)
        self.assertEqual("job-test", result["job_record"]["job_id"])
        self.assertEqual("content-001", job_store.record["content_id"])
        self.assertEqual("tiktok_pieknemedia", job_store.record["profile_id"])
        self.assertEqual("group-1", job_store.record["provider_post_group_id"])

    def test_d1_persistence_failure_blocks_success_result(self):
        client = FakeClient()
        job_store = FakeJobStore(error=D1Error("network_outcome_unknown"))
        with self.assertRaisesRegex(PubloraError, "d1_job_record_failed"):
            process_manifest(client, self.base, job_store)

    def test_unknown_schedule_outcome_is_reconciled_by_reading_post(self):
        client = FakeClient(schedule_error=PubloraError("network_outcome_unknown"), post_status="scheduled")
        result = process_manifest(client, self.base)
        self.assertEqual("scheduled", result["status"])
        self.assertEqual("get", client.calls[-1][0])

    def test_unknown_schedule_outcome_is_not_blindly_retried(self):
        client = FakeClient(schedule_error=PubloraError("network_outcome_unknown"), post_status="draft")
        with self.assertRaisesRegex(PubloraError, "schedule_outcome_unknown_requires_reconciliation"):
            process_manifest(client, self.base)
        self.assertEqual(1, sum(1 for call in client.calls if call[0] == "schedule"))


if __name__ == "__main__":
    unittest.main()
