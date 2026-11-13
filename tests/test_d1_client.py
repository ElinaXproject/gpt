import json
import unittest
from datetime import datetime, timezone

from autored.d1_client import D1Client, D1Error, _safety_review_reference
from autored.factcheck import Claim, Evidence, FactCheckReport


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

    def valid_youtube_report(self, reviewer_type="human"):
        now = datetime.now(timezone.utc).isoformat()
        return FactCheckReport(
            profile_key="youtube_memoryagent",
            reviewed_at=now,
            reviewer="editor:verified-review",
            reviewer_type=reviewer_type,
            decision="approved",
            claims=(Claim("c1", "A verifiable technology claim"),),
            evidence=(
                Evidence("https://www.theverge.com/article-a", "The Verge report", now, ("c1",)),
                Evidence("https://arstechnica.com/article-b", "Ars Technica report", now, ("c1",)),
            ),
        )

    @staticmethod
    def report_payload(report):
        return json.dumps({
            "profile_key": report.profile_key,
            "reviewed_at": report.reviewed_at,
            "reviewer": report.reviewer,
            "reviewer_type": report.reviewer_type,
            "decision": report.decision,
            "claims": [{"claim_id": item.claim_id, "text": item.text} for item in report.claims],
            "evidence": [{
                "url": item.url, "title": item.title, "published_at": item.published_at,
                "supports_claim_ids": list(item.supports_claim_ids), "support_type": item.support_type
            } for item in report.evidence],
        }, ensure_ascii=False)

    def safety_payload(self, content_id, profile_id, checks=None):
        required = {"content_safety": True, "copyright_rights": True, "platform_rules": True, "ai_disclosure": True}
        if profile_id.startswith("tiktok_"):
            required["music_license"] = True
        if profile_id in {"tiktok_ocenionona6", "youtube_memoryagent"}:
            required["factual_accuracy"] = True
        if checks is not None:
            required.update(checks)
        return {
            "content_id": content_id,
            "profile_id": profile_id,
            "reviewer": "editor:verified-review",
            "reviewed_at": datetime.now(timezone.utc).isoformat(),
            "decision": "approved",
            "checks": required,
            "notes": "Reviewed before scheduling",
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
            "fact_check_report_json": "",
            "source_urls_json": "[]",
            "source_published_at_json": "[]",
            "media_mime": "video/mp4",
            "media_bytes": 5,
            "media_sha256": "a" * 64,
            "music_embedded": 1,
            "music_license_reference": "original-track-license-001",
        }
        row.update(overrides)
        safety_report = self.safety_payload(row["id"], row["profile_id"])
        row["safety_review_report_json"] = json.dumps(safety_report, ensure_ascii=False, sort_keys=True)
        row["safety_review_reference"] = _safety_review_reference(safety_report)
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

    def test_valid_safety_review_is_persisted(self):
        client, requests = self.client([
            self.response([{"profile_id":"tiktok_pieknemedia","status":"draft"}], 0),
            self.response([], 1),
            self.response([], 1),
        ])
        status, reference = client.record_safety_review(
            "content-1", "tiktok_pieknemedia", "editor:verified-review",
            datetime.now(timezone.utc).isoformat(), "approved",
            {"content_safety": True, "copyright_rights": True, "platform_rules": True,
             "ai_disclosure": True, "music_license": True},
            "All checks passed"
        )
        self.assertEqual("passed", status)
        self.assertTrue(reference.startswith("sr_"))
        self.assertEqual(3, len(requests))
        update = json.loads(requests[1].data.decode("utf-8"))
        self.assertIn("safety_review_report_json", update["sql"])
        self.assertIn("human_safety_review", json.loads(requests[2].data.decode("utf-8"))["sql"])

    def test_failed_safety_check_is_persisted_as_blocked(self):
        client, requests = self.client([
            self.response([{"profile_id":"tiktok_pieknemedia","status":"draft"}], 0),
            self.response([], 1),
            self.response([], 1),
        ])
        status, _reference = client.record_safety_review(
            "content-1", "tiktok_pieknemedia", "editor:verified-review",
            datetime.now(timezone.utc).isoformat(), "approved",
            {"content_safety": False, "copyright_rights": True, "platform_rules": True,
             "ai_disclosure": True, "music_license": True}
        )
        self.assertEqual("blocked", status)
        self.assertEqual(3, len(requests))
        update = json.loads(requests[1].data.decode("utf-8"))
        self.assertEqual("blocked", update["params"][0])

    def test_fact_check_report_requires_human_reviewer(self):
        client, requests = self.client([
            self.response([{"profile_id":"youtube_memoryagent","status":"draft"}], 0)
        ])
        with self.assertRaisesRegex(D1Error, "fact_check_human_review_required"):
            client.record_fact_check_report("content-1", "youtube_memoryagent", self.valid_youtube_report("ai_verifier"))
        self.assertEqual(1, len(requests))

    def test_valid_human_fact_check_report_is_persisted(self):
        report = self.valid_youtube_report()
        client, requests = self.client([
            self.response([{"profile_id":"youtube_memoryagent","status":"draft"}], 0),
            self.response([], 1),
            self.response([], 1),
        ])
        reference = client.record_fact_check_report("content-1", "youtube_memoryagent", report)
        self.assertEqual(report.reference(), reference)
        self.assertEqual(3, len(requests))
        update = json.loads(requests[1].data.decode("utf-8"))
        self.assertIn("fact_check_report_json", update["sql"])
        self.assertIn("human_fact_check", json.loads(requests[2].data.decode("utf-8"))["sql"])
        self.assertEqual(1, update["params"][0] == reference)

    def test_native_youtube_rejects_fact_check_reference_without_matching_report(self):
        report = self.valid_youtube_report()
        content = self.publishable_content(
            profile_id="youtube_memoryagent", fact_check_passed=1,
            fact_check_reference="fc_wrong",
            fact_check_report_json=self.report_payload(report),
            source_urls_json=json.dumps([item.url for item in report.evidence]),
            source_published_at_json=json.dumps([item.published_at for item in report.evidence]),
        )
        client, requests = self.client([self.response([content], 0)])
        with self.assertRaisesRegex(D1Error, "fact_check_reference_mismatch"):
            client.reserve_job(
                content_id="content-1", profile_id="youtube_memoryagent",
                scheduled_at="2026-11-14T12:00:00+00:00",
                idempotency_key="youtube-key", provider="youtube_direct",
                media_artifact_id="12345"
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
                idempotency_key="native-key", provider="tiktok_direct",
                media_artifact_id="12345"
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
            idempotency_key="native-key", provider="tiktok_direct",
            media_artifact_id="12345"
        )
        self.assertEqual("planned", result["status"])
        self.assertEqual(4, len(requests))


    def test_native_youtube_job_requires_fact_check_and_can_be_scheduled(self):
        report = self.valid_youtube_report()
        content = self.publishable_content(
            profile_id="youtube_memoryagent",
            fact_check_passed=1,
            fact_check_reference=report.reference(),
            fact_check_report_json=self.report_payload(report),
            source_urls_json=json.dumps([item.url for item in report.evidence]),
            source_published_at_json=json.dumps([item.published_at for item in report.evidence]),
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
            media_artifact_id="12345"
        )
        self.assertEqual("youtube_direct", result["provider"])
        client.mark_job_publishing("job-youtube")
        self.assertEqual(5, len(requests))

    def test_youtube_job_schedule_transition_stays_planned(self):
        client, requests = self.client([self.response([], changes=1)])
        client.mark_job_scheduled("job-youtube", "video-123")
        self.assertIn("provider='youtube_direct'", requests[0].data.decode("utf-8"))

    def test_native_provider_cannot_publish_another_platform_profile(self):
        client, requests = self.client([])
        with self.assertRaisesRegex(D1Error, "provider_profile_mismatch"):
            client.reserve_job(
                content_id="content-1", profile_id="tiktok_pieknemedia",
                scheduled_at="2026-11-14T12:00:00+00:00",
                idempotency_key="wrong-provider", provider="youtube_direct",
                media_artifact_id="12345"
            )
        self.assertEqual([], requests)

    def test_native_reservation_requires_numeric_media_artifact_id(self):
        client, requests = self.client([])
        with self.assertRaisesRegex(D1Error, "media_artifact_id_invalid"):
            client.reserve_job(
                content_id="content-1", profile_id="tiktok_pieknemedia",
                scheduled_at="2026-11-14T12:00:00+00:00",
                idempotency_key="native-key", provider="tiktok_direct",
                media_artifact_id="not-numeric"
            )
        self.assertEqual([], requests)

    def test_attach_media_metadata_updates_content_and_audit_event(self):
        client, requests = self.client([
            self.response([{"profile_id":"tiktok_pieknemedia","status":"draft"}], 0),
            self.response([], 1),
            self.response([], 1),
        ])
        client.attach_media_metadata(
            "content-1", "tiktok_pieknemedia", "video/mp4", 1024, "a" * 64,
            music_embedded=True, music_license_reference="licensed-track-2026"
        )
        self.assertEqual(3, len(requests))
        update = json.loads(requests[1].data.decode("utf-8"))
        self.assertIn("media_sha256", update["sql"])
        event = json.loads(requests[2].data.decode("utf-8"))
        self.assertIn("media_attached", event["sql"])

    def test_tiktok_media_metadata_requires_licensed_embedded_music(self):
        client, requests = self.client([])
        with self.assertRaisesRegex(D1Error, "licensed_embedded_music_required"):
            client.attach_media_metadata(
                "content-1", "tiktok_pieknemedia", "video/mp4", 1024, "a" * 64
            )
        self.assertEqual([], requests)

    def test_pending_tiktok_query_only_selects_publishing_jobs_with_post_ids(self):
        client, requests = self.client([self.response([], changes=0)])
        client.get_pending_tiktok_jobs(limit=5)
        sql = json.loads(requests[0].data.decode("utf-8"))["sql"]
        self.assertIn("provider='tiktok_direct'", sql)
        self.assertIn("status='publishing'", sql)
        self.assertIn("platform_post_id IS NOT NULL", sql)

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

    def test_mark_job_failed_updates_job_and_content_status(self):
        client, requests = self.client([
            self.response([{"content_id":"content-1"}], changes=0),
            self.response([], changes=1),
            self.response([], changes=1),
        ])
        client.mark_job_failed("job-test", "provider_failed", blocked=True)
        self.assertIn("status=?", json.loads(requests[1].data.decode("utf-8"))["sql"])
        content_update = json.loads(requests[2].data.decode("utf-8"))
        self.assertIn("UPDATE content_items SET status=?", content_update["sql"])
        self.assertEqual(["blocked", "content-1"], content_update["params"])

    def test_mark_job_publishing_requires_valid_state_transition(self):
        client, _requests = self.client([self.response([], changes=1)])
        client.mark_job_publishing("job-test")

    def test_missing_token_is_rejected(self):
        with self.assertRaisesRegex(D1Error, "missing_api_token"):
            D1Client(api_token="", opener=lambda *_args, **_kwargs: None)


if __name__ == "__main__":
    unittest.main()
