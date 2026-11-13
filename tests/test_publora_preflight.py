import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from publora_preflight import run_preflight


class FakeClient:
    def __init__(self, youtube_id="youtube-UCOE1EX9WZGDesaJNYIEhj7g", missing=None):
        self.youtube_id = youtube_id
        self.missing = set(missing or [])

    def resolve_connection(self, platform, handle):
        profile = next(
            (key for key, value in {
                "tiktok_pieknemedia": ("tiktok", "@pieknemedia"),
                "tiktok_ocenionona6": ("tiktok", "@ocenionona6"),
                "youtube_memoryagent": ("youtube", "@MemoryAgent-r3c"),
            }.items() if value == (platform, handle)),
            None,
        )
        if profile in self.missing:
            from publora_client import PubloraError
            raise PubloraError("target_connection_not_unique")
        platform_id = self.youtube_id if profile == "youtube_memoryagent" else f"{platform}-{profile}"
        return {
            "platformId": platform_id,
            "connectionStatus": "active",
            "tokenStatus": "valid",
        }

    def account_context(self):
        return {
            "plan": {"name": "Starter"},
            "features": {"publishing": True, "apiAccess": True},
            "allowedPlatforms": ["tiktok", "youtube"],
            "quotas": {
                "monthlyPosts": {"remaining": 13},
                "scheduledPosts": {"remaining": 3},
                "connections": {"remaining": 2},
                "scheduleHorizon": {"maxScheduledDate": "2026-11-20T23:59:59.999Z"}
            }
        }


class FakeD1Client:
    def __init__(self, missing=None):
        self.missing = set(missing or [])

    def query(self, sql, params):
        handles = ["@pieknemedia", "@ocenionona6", "@MemoryAgent-r3c"]
        return {"results": [{"handle": handle} for handle in handles if handle not in self.missing]}


class PubloraPreflightTests(unittest.TestCase):
    def test_all_exact_connections_pass(self):
        result = run_preflight(FakeClient(), FakeD1Client())
        self.assertEqual("ready", result["status"])
        self.assertEqual(3, result["ready_profiles"])
        self.assertFalse(result["publishing_performed"])

    def test_missing_tiktok_account_is_reported(self):
        result = run_preflight(FakeClient(missing={"tiktok_ocenionona6"}), FakeD1Client())
        self.assertEqual("incomplete", result["status"])
        missing = next(x for x in result["profiles"] if x["profile_id"] == "tiktok_ocenionona6")
        self.assertEqual("target_connection_not_unique", missing["reason"])

    def test_wrong_youtube_channel_id_is_blocked(self):
        result = run_preflight(FakeClient(youtube_id="youtube-UCRmmEQysOmUbs8mpZEOgtLw"), FakeD1Client())
        youtube = next(x for x in result["profiles"] if x["profile_id"] == "youtube_memoryagent")
        self.assertEqual("youtube_channel_id_mismatch", youtube["reason"])
        self.assertEqual("incomplete", result["status"])


    def test_unsupported_provider_platform_blocks_preflight(self):
        client = FakeClient()
        client.account_context = lambda: {
            "plan": {"name": "Starter"},
            "features": {"publishing": True, "apiAccess": True},
            "allowedPlatforms": ["tiktok"],
            "quotas": {}
        }
        result = run_preflight(client, FakeD1Client())
        self.assertEqual("blocked", result["publora_account"]["status"])
        self.assertEqual(["youtube"], result["publora_account"]["unsupported_platforms"])

    def test_missing_d1_profile_mapping_blocks_preflight(self):
        result = run_preflight(FakeClient(), FakeD1Client(missing={"@MemoryAgent-r3c"}))
        self.assertEqual("incomplete", result["status"])
        self.assertEqual("incomplete", result["d1_database"]["status"])
        self.assertEqual(["@MemoryAgent-r3c"], result["d1_database"]["missing_profiles"])


if __name__ == "__main__":
    unittest.main()
