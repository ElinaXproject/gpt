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

    def test_connection(self, platform_id):
        return {"status": "ok"}


class PubloraPreflightTests(unittest.TestCase):
    def test_all_exact_connections_pass(self):
        result = run_preflight(FakeClient())
        self.assertEqual("ready", result["status"])
        self.assertEqual(3, result["ready_profiles"])
        self.assertFalse(result["publishing_performed"])

    def test_missing_tiktok_account_is_reported(self):
        result = run_preflight(FakeClient(missing={"tiktok_ocenionona6"}))
        self.assertEqual("incomplete", result["status"])
        missing = next(x for x in result["profiles"] if x["profile_id"] == "tiktok_ocenionona6")
        self.assertEqual("target_connection_not_unique", missing["reason"])

    def test_wrong_youtube_channel_id_is_blocked(self):
        result = run_preflight(FakeClient(youtube_id="youtube-UCRmmEQysOmUbs8mpZEOgtLw"))
        youtube = next(x for x in result["profiles"] if x["profile_id"] == "youtube_memoryagent")
        self.assertEqual("youtube_channel_id_mismatch", youtube["reason"])
        self.assertEqual("incomplete", result["status"])


if __name__ == "__main__":
    unittest.main()
