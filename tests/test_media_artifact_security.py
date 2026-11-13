import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class MediaArtifactSecurityTests(unittest.TestCase):
    def test_reusable_action_uploads_only_age_encrypted_bundle(self):
        action = (ROOT / ".github" / "actions" / "package-and-schedule" / "action.yml").read_text(encoding="utf-8")
        self.assertIn("path: media_bundle.zip.age", action)
        self.assertIn("actions/upload-artifact@ea165f8d65b6e75b540449e92b4886f43607fa02", action)
        self.assertNotIn("path: manifest.json", action)
        self.assertNotIn("path: media.mp4", action)

    def test_publication_dispatcher_requires_age_identity(self):
        dispatcher = (ROOT / "scripts" / "publisher_dispatch.py").read_text(encoding="utf-8")
        self.assertIn("AUTORED_ARTIFACT_AGE_IDENTITY", dispatcher)
        downloader = (ROOT / "scripts" / "download_media_artifact.py").read_text(encoding="utf-8")
        self.assertIn("unencrypted_or_unsafe_artifact_rejected", downloader)
        self.assertIn("artifact_decryption_identity_missing", downloader)


if __name__ == "__main__":
    unittest.main()
