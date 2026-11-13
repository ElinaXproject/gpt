import json
import unittest

from autored.d1_client import D1Client, D1Error


class FakeResponse:
    def __init__(self, payload, status=200):
        self.payload = payload
        self.status = status

    def read(self):
        return json.dumps(self.payload).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


class D1ClientTests(unittest.TestCase):
    def client(self, payloads):
        captured = []
        remaining = list(payloads)

        def opener(request, timeout=30):
            captured.append(request)
            return FakeResponse(remaining.pop(0))

        return D1Client(api_token="test-token", opener=opener), captured

    @staticmethod
    def response(results=None, changes=1):
        return {
            "success": True,
            "result": [{
                "success": True,
                "results": results or [],
                "meta": {"changes": changes}
            }]
        }

    def publishable_content(self, **overrides):
        row = {
            "id": "content-1",
            "profile_id": "tiktok_pieknemedia",
            "status": "ready",
            "safety_review_status": "passed",
            "rights_reference": "original-or-licensed",
            "ai_disclosure_required": 1,
            "ai_disclosure_set": 1,
            "fact_check_passed": 0,
            "fact_check_reference": "",
            "music_embedded": 1,
            "music_license_reference": "original-track-license-001",
        }
        row.update(overrides)
        return row

    def test_record_scheduled_creates_job_and_updates_content(self):
        client, requests = self.client([
            self.response([self.publishable_content()], 0),
            self.response([], 1),
            self.response([{"id":"job-test","content_id":"content-1","profile_id":"tiktok_pieknemedia","status":"planned","provider":"publora","platform_post_id":"publora-group-1"}], 0),
            self.response([], 1),
            self.response([], 1),
        ])
        result = client.record_scheduled(
            content_id="content-1",
            profile_id="tiktok_pieknemedia",
            scheduled_at="2026-11-14T12:00:00+00:00",
            idempotency_key="schedule-key",
            provider_post_group_id="publora-group-1",
        )
        self.assertEqual("planned", result["job_status"])
        self.assertEqual("scheduled", result["content_status"])
        self.assertEqual(5, len(requests))
        self.assertTrue(result["job_id"].startswith("job_"))
        self.assertEqual("Bearer test-token", requests[0].get_header("Authorization"))

    def test_profile_mismatch_blocks_before_insert(self):
        client, requests = self.client([
            self.response([self.publishable_content(profile_id="youtube_memoryagent")], 0)
        ])
        with self.assertRaisesRegex(D1Error, "content_profile_mismatch"):
            client.record_scheduled(
                content_id="content-1",
                profile_id="tiktok_pieknemedia",
                scheduled_at="2026-11-14T12:00:00+00:00",
                idempotency_key="schedule-key",
                provider_post_group_id="group-1",
            )
        self.assertEqual(1, len(requests))

    def test_unapproved_content_status_blocks_scheduling(self):
        client, requests = self.client([
            self.response([self.publishable_content(status="blocked")], 0)
        ])
        with self.assertRaisesRegex(D1Error, "content_status_not_publishable"):
            client.record_scheduled(
                content_id="content-1",
                profile_id="tiktok_pieknemedia",
                scheduled_at="2026-11-14T12:00:00+00:00",
                idempotency_key="schedule-key",
                provider_post_group_id="group-1",
            )
        self.assertEqual(1, len(requests))


    def test_safety_pending_content_blocks_schedule(self):
        client, requests = self.client([
            self.response([self.publishable_content(safety_review_status="pending")], 0)
        ])
        with self.assertRaisesRegex(D1Error, "safety_review_not_passed"):
            client.record_scheduled(
                content_id="content-1", profile_id="tiktok_pieknemedia",
                scheduled_at="2026-11-14T12:00:00+00:00",
                idempotency_key="schedule-key", provider_post_group_id="group-1"
            )
        self.assertEqual(1, len(requests))

    def test_research_profile_requires_fact_check_reference(self):
        client, requests = self.client([
            self.response([self.publishable_content(
                profile_id="youtube_memoryagent",
                fact_check_passed=0,
                fact_check_reference=""
            )], 0)
        ])
        with self.assertRaisesRegex(D1Error, "fact_check_not_passed"):
            client.record_scheduled(
                content_id="content-1", profile_id="youtube_memoryagent",
                scheduled_at="2026-11-14T12:00:00+00:00",
                idempotency_key="schedule-key", provider_post_group_id="group-1"
            )
        self.assertEqual(1, len(requests))

    def test_native_tiktok_job_requires_licensed_embedded_music(self):
        client, requests = self.client([
            self.response([self.publishable_content(music_embedded=0, music_license_reference="")], 0)
        ])
        with self.assertRaisesRegex(D1Error, "licensed_embedded_music_required"):
            client.reserve_job(
                content_id="content-1", profile_id="tiktok_pieknemedia",
                scheduled_at="2026-11-14T12:00:00+00:00",
                idempotency_key="native-key", provider="tiktok_direct"
            )
        self.assertEqual(1, len(requests))

    def test_native_tiktok_job_is_reserved_idempotently(self):
        client, requests = self.client([
            self.response([self.publishable_content()], 0),
            self.response([], 1),
            self.response([{"id":"job-test","content_id":"content-1","profile_id":"tiktok_pieknemedia","status":"planned","provider":"tiktok_direct","platform_post_id":None}], 0),
            self.response([], 1),
        ])
        result = client.reserve_job(
            content_id="content-1", profile_id="tiktok_pieknemedia",
            scheduled_at="2026-11-14T12:00:00+00:00",
            idempotency_key="native-key", provider="tiktok_direct"
        )
        self.assertEqual("planned", result["status"])
        self.assertEqual(4, len(requests))


    def test_native_youtube_job_requires_fact_check_and_can_be_scheduled(self):
        content = self.publishable_content(
            profile_id="youtube_memoryagent",
            fact_check_passed=1,
            fact_check_reference="factcheck:sha256:report-001",
            music_embedded=0,
            music_license_reference=""
        )
        client, requests = self.client([
            self.response([content], 0),
            self.response([], 1),
            self.response([{"id":"job-youtube","content_id":"content-1","profile_id":"youtube_memoryagent","status":"planned","provider":"youtube_direct","platform_post_id":None}], 0),
            self.response([], 1),
            self.response([], 1),
        ])
        result = client.reserve_job(
            content_id="content-1", profile_id="youtube_memoryagent",
            scheduled_at="2026-11-14T12:00:00+00:00",
            idempotency_key="youtube-key", provider="youtube_direct",
            media_artifact_id="artifact-123"
        )
        self.assertEqual("youtube_direct", result["provider"])
        client.mark_job_publishing("job-youtube")
        self.assertEqual(5, len(requests))

    def test_youtube_job_schedule_transition_stays_planned(self):
        client, requests = self.client([self.response([], changes=1)])
        client.mark_job_scheduled("job-youtube", "video-123")
        self.assertIn("provider='youtube_direct'", requests[0].data.decode("utf-8"))

    def test_due_job_query_does_not_reupload_scheduled_youtube_videos(self):
        client, requests = self.client([self.response([], changes=0)])
        client.get_due_jobs("2026-11-14T12:00:00Z", limit=10)
        sql = json.loads(requests[0].data.decode("utf-8"))["sql"]
        self.assertIn("provider='tiktok_direct'", sql)


    def test_youtube_scheduler_selects_only_unuploaded_future_jobs(self):
        client, requests = self.client([self.response([], changes=0)])
        client.get_youtube_jobs_to_schedule("2026-11-14T12:00:00Z", horizon_hours=168, limit=10)
        sql = json.loads(requests[0].data.decode("utf-8"))["sql"]
        self.assertIn("provider='youtube_direct'", sql)
        self.assertIn("platform_post_id IS NULL", sql)

    def test_mark_job_publishing_requires_valid_state_transition(self):
        client, _requests = self.client([self.response([], changes=1)])
        client.mark_job_publishing("job-test")

    def test_missing_token_is_rejected(self):
        with self.assertRaisesRegex(D1Error, "missing_api_token"):
            D1Client(api_token="", opener=lambda *_args, **_kwargs: None)


if __name__ == "__main__":
    unittest.main()
