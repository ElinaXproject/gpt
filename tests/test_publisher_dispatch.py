import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from publisher_dispatch import run_dispatch


class FakeD1:
    def __init__(self, tiktok=None, youtube=None, pending=None):
        self.tiktok = tiktok or []
        self.youtube = youtube or []
        self.pending = pending or []
        self.failed = []
        self.published = []

    def get_pending_tiktok_jobs(self, limit=20):
        return self.pending[:limit]

    def get_due_jobs(self, now, limit=10):
        return self.tiktok[:limit]

    def get_youtube_jobs_to_schedule(self, now, horizon_hours=168, limit=10):
        return self.youtube[:limit]

    def mark_job_failed(self, job_id, error_code, blocked=False):
        self.failed.append((job_id, error_code, blocked))

    def mark_job_published(self, job_id, provider_post_id):
        self.published.append((job_id, provider_post_id))


def make_job(provider="tiktok_direct", profile="tiktok_pieknemedia"):
    return {
        "id": "job-1",
        "content_id": "content-1",
        "profile_id": profile,
        "scheduled_at": "2026-11-14T12:00:00Z",
        "idempotency_key": "idem-1",
        "provider": provider,
        "media_artifact_id": "12345",
        "status": "planned",
    }


class PublisherDispatchTests(unittest.TestCase):
    def artifact(self, manifest_data):
        def download(_artifact_id, destination):
            destination.mkdir(parents=True, exist_ok=True)
            manifest = destination / "manifest.json"
            media = destination / "media.mp4"
            manifest.write_text(json.dumps(manifest_data), encoding="utf-8")
            media.write_bytes(b"media")
            return manifest, media
        return download

    def test_dry_run_lists_candidates_without_downloading_or_mutating(self):
        d1 = FakeD1(tiktok=[make_job()])
        result = run_dispatch(d1=d1, now_utc="2026-11-14T12:00:00Z", dry_run=True)
        self.assertEqual("dry_run", result["status"])
        self.assertEqual(1, result["candidate_count"])
        self.assertEqual([], d1.failed)

    def test_missing_provider_credentials_skip_without_blocking_job(self):
        d1 = FakeD1(tiktok=[make_job()])
        result = run_dispatch(
            d1=d1, now_utc="2026-11-14T12:00:00Z", env={},
            downloader=lambda *_args: self.fail("must not download")
        )
        self.assertEqual(1, result["skipped"])
        self.assertEqual([], d1.failed)

    def test_manifest_mismatch_blocks_job_before_runner(self):
        d1 = FakeD1(tiktok=[make_job()])
        manifest = {
            "content_id": "wrong-content",
            "profile_id": "tiktok_pieknemedia",
            "scheduled_at": "2026-11-14T12:00:00Z",
            "idempotency_key": "idem-1",
            "caption": "Test", "duration_seconds": 20, "privacy_level": "SELF_ONLY",
            "music_embedded": True, "music_license_reference": "license",
            "ai_generated": True, "media_sha256": "0" * 64, "media_bytes": 5, "media_mime": "video/mp4"
        }
        result = run_dispatch(
            d1=d1, now_utc="2026-11-14T12:00:00Z",
            env={"TIKTOK_CLIENT_KEY":"key","TIKTOK_CLIENT_SECRET":"secret","AUTORED_TOKEN_ENCRYPTION_KEY":"key"},
            downloader=self.artifact(manifest),
            tiktok_runner=lambda *_args: self.fail("runner must not be called")
        )
        self.assertEqual(1, result["blocked"])
        self.assertEqual([("job-1", "media_manifest_job_mismatch", True)], d1.failed)

    def test_valid_tiktok_manifest_dispatches_once(self):
        d1 = FakeD1(tiktok=[make_job()])
        manifest = {
            "content_id": "content-1",
            "profile_id": "tiktok_pieknemedia",
            "scheduled_at": "2026-11-14T13:00:00+01:00",
            "idempotency_key": "idem-1",
            "caption": "Test", "duration_seconds": 20, "privacy_level": "SELF_ONLY",
            "music_embedded": True, "music_license_reference": "license",
            "ai_generated": True, "media_sha256": "0" * 64, "media_bytes": 5, "media_mime": "video/mp4"
        }
        called=[]
        result = run_dispatch(
            d1=d1, now_utc="2026-11-14T12:00:00Z",
            env={"TIKTOK_CLIENT_KEY":"key","TIKTOK_CLIENT_SECRET":"secret","AUTORED_TOKEN_ENCRYPTION_KEY":"key"},
            downloader=self.artifact(manifest),
            tiktok_runner=lambda manifest_path, media_path: called.append((manifest_path, media_path)) or {"status":"published"}
        )
        self.assertEqual(1, result["processed"])
        self.assertEqual(1, len(called))
        self.assertEqual([], d1.failed)

    def test_pending_tiktok_job_is_reconciled_as_published(self):
        pending = {"id":"job-pending","profile_id":"tiktok_pieknemedia","platform_post_id":"publish-1"}
        d1 = FakeD1(pending=[pending])
        result = run_dispatch(
            d1=d1, now_utc="2026-11-14T12:00:00Z",
            env={"TIKTOK_CLIENT_KEY":"key","TIKTOK_CLIENT_SECRET":"secret","AUTORED_TOKEN_ENCRYPTION_KEY":"key"},
            tiktok_status_checker=lambda _job, _d1: "PUBLISH_COMPLETE"
        )
        self.assertEqual(1, result["reconciled"])
        self.assertEqual([("job-pending", "publish-1")], d1.published)

    def test_pending_tiktok_failure_is_marked_failed(self):
        pending = {"id":"job-pending","profile_id":"tiktok_pieknemedia","platform_post_id":"publish-2"}
        d1 = FakeD1(pending=[pending])
        result = run_dispatch(
            d1=d1, now_utc="2026-11-14T12:00:00Z",
            env={"TIKTOK_CLIENT_KEY":"key","TIKTOK_CLIENT_SECRET":"secret","AUTORED_TOKEN_ENCRYPTION_KEY":"key"},
            tiktok_status_checker=lambda _job, _d1: "FAILED"
        )
        self.assertEqual(1, result["reconciled"])
        self.assertEqual([("job-pending", "tiktok_publish_failed", False)], d1.failed)

    def test_pending_tiktok_job_is_left_unchanged_while_processing(self):
        pending = {"id":"job-pending","profile_id":"tiktok_pieknemedia","platform_post_id":"publish-3"}
        d1 = FakeD1(pending=[pending])
        result = run_dispatch(
            d1=d1, now_utc="2026-11-14T12:00:00Z",
            env={"TIKTOK_CLIENT_KEY":"key","TIKTOK_CLIENT_SECRET":"secret","AUTORED_TOKEN_ENCRYPTION_KEY":"key"},
            tiktok_status_checker=lambda _job, _d1: "PROCESSING_UPLOAD"
        )
        self.assertEqual(1, result["pending"])
        self.assertEqual([], d1.failed)
        self.assertEqual([], d1.published)

    def test_youtube_future_job_uses_youtube_credentials_and_runner(self):
        job=make_job("youtube_direct","youtube_memoryagent")
        d1=FakeD1(youtube=[job])
        manifest = {
            "content_id": "content-1",
            "profile_id": "youtube_memoryagent",
            "scheduled_at": "2026-11-14T12:00:00Z",
            "idempotency_key": "idem-1",
            "title":"Test", "description":"Description", "tags":[],
            "made_for_kids":False, "ai_generated":True, "media_sha256":"0"*64,
            "media_bytes":5, "media_mime":"video/mp4", "format_type":"short"
        }
        called=[]
        result=run_dispatch(
            d1=d1, now_utc="2026-11-13T12:00:00Z",
            env={"YOUTUBE_CLIENT_ID":"id","YOUTUBE_CLIENT_SECRET":"secret","YOUTUBE_REFRESH_TOKEN":"refresh"},
            downloader=self.artifact(manifest),
            youtube_runner=lambda manifest_path, media_path: called.append(media_path) or {"status":"scheduled"}
        )
        self.assertEqual(1,result["processed"])
        self.assertEqual(1,len(called))


if __name__ == "__main__":
    unittest.main()
