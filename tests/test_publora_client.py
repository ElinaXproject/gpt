import json
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from scripts.publora_client import PubloraClient, PubloraError, stable_idempotency_key


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


class PubloraClientTests(unittest.TestCase):
    def client(self, payload):
        captured = []

        def opener(request, timeout=30):
            captured.append(request)
            return FakeResponse(payload)

        return PubloraClient(api_key="test-key", opener=opener), captured

    def test_resolves_exact_tiktok_handle_and_requires_active_connection(self):
        client, _ = self.client({
            "connections": [{
                "platformId": "tiktok-abc123",
                "username": "pieknemedia",
                "connectionStatus": "active",
                "tokenStatus": "valid"
            }]
        })
        self.assertEqual(
            "tiktok-abc123",
            client.resolve_connection("tiktok", "@pieknemedia")["platformId"]
        )

    def test_refuses_wrong_or_ambiguous_target(self):
        client, _ = self.client({"connections": []})
        with self.assertRaisesRegex(PubloraError, "target_connection_not_unique"):
            client.resolve_connection("tiktok", "@pieknemedia")

    def test_refuses_inactive_connection(self):
        client, _ = self.client({
            "connections": [{
                "platformId": "tiktok-abc123",
                "username": "pieknemedia",
                "connectionStatus": "reconnect_required",
                "tokenStatus": "valid"
            }]
        })
        with self.assertRaisesRegex(PubloraError, "target_connection_not_active"):
            client.resolve_connection("tiktok", "@pieknemedia")

    def test_create_draft_uses_idempotency_and_does_not_publish_now(self):
        client, captured = self.client({"success": True, "postGroupId": "group-1"})
        post_id = client.create_draft(
            "Test draft",
            "tiktok-abc123",
            idempotency_key="stable-key"
        )
        self.assertEqual("group-1", post_id)
        request = captured[0]
        self.assertEqual("POST", request.get_method())
        self.assertEqual("stable-key", request.get_header("Idempotency-key"))
        body = json.loads(request.data.decode("utf-8"))
        self.assertEqual(["tiktok-abc123"], body["platforms"])
        self.assertNotIn("publishNow", body)
        self.assertNotIn("scheduledTime", body)

    def test_schedule_requires_future_timezone_aware_time_and_free_horizon(self):
        client, _ = self.client({"success": True})
        now = datetime(2026, 11, 13, 12, tzinfo=timezone.utc)
        with self.assertRaisesRegex(PubloraError, "schedule_must_be_timezone_aware"):
            client.schedule_draft("group-1", datetime(2026, 11, 14, 12), idempotency_key="k", now=now)
        with self.assertRaisesRegex(PubloraError, "schedule_must_be_in_future"):
            client.schedule_draft("group-1", now, idempotency_key="k", now=now)
        with self.assertRaisesRegex(PubloraError, "schedule_exceeds_plan_horizon"):
            client.schedule_draft("group-1", now + timedelta(days=8), idempotency_key="k", now=now)

    def test_schedule_uses_utc_and_idempotency(self):
        client, captured = self.client({"success": True, "scheduledTime": "2026-11-14T12:00:00.000Z"})
        now = datetime(2026, 11, 13, 12, tzinfo=timezone.utc)
        client.schedule_draft(
            "group-1",
            now + timedelta(days=1),
            idempotency_key="schedule-key",
            now=now
        )
        request = captured[0]
        body = json.loads(request.data.decode("utf-8"))
        self.assertEqual("scheduled", body["status"])
        self.assertEqual("2026-11-14T12:00:00.000Z", body["scheduledTime"])
        self.assertEqual("schedule-key", request.get_header("Idempotency-key"))

    def test_stable_idempotency_key_is_deterministic_and_scoped(self):
        a = stable_idempotency_key("content-1", "profile-1", "create")
        self.assertEqual(a, stable_idempotency_key("content-1", "profile-1", "create"))
        self.assertNotEqual(a, stable_idempotency_key("content-1", "profile-2", "create"))

    def test_missing_api_key_is_rejected(self):
        with self.assertRaisesRegex(PubloraError, "missing_api_key"):
            PubloraClient(api_key="", opener=lambda *_args, **_kwargs: None)


if __name__ == "__main__":
    unittest.main()
