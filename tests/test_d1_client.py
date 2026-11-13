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

    def test_record_scheduled_creates_job_and_updates_content(self):
        client, requests = self.client([
            self.response([{"id": "content-1", "profile_id": "tiktok_pieknemedia", "status": "idea"}], 0),
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
        self.assertEqual(3, len(requests))
        self.assertTrue(result["job_id"].startswith("job_"))
        self.assertEqual("Bearer test-token", requests[0].get_header("Authorization"))

    def test_profile_mismatch_blocks_before_insert(self):
        client, requests = self.client([
            self.response([{"id": "content-1", "profile_id": "youtube_memoryagent", "status": "idea"}], 0)
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
            self.response([{"id": "content-1", "profile_id": "tiktok_pieknemedia", "status": "blocked"}], 0)
        ])
        with self.assertRaisesRegex(D1Error, "content_status_not_schedulable"):
            client.record_scheduled(
                content_id="content-1",
                profile_id="tiktok_pieknemedia",
                scheduled_at="2026-11-14T12:00:00+00:00",
                idempotency_key="schedule-key",
                provider_post_group_id="group-1",
            )
        self.assertEqual(1, len(requests))

    def test_missing_token_is_rejected(self):
        with self.assertRaisesRegex(D1Error, "missing_api_token"):
            D1Client(api_token="", opener=lambda *_args, **_kwargs: None)


if __name__ == "__main__":
    unittest.main()
