import io
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from download_media_artifact import ArtifactError, download_media_artifact


class DownloadMediaArtifactTests(unittest.TestCase):
    def response(self, payload):
        class FakeResponse:
            status = 200
            def read(self, _limit=-1):
                return payload
            def __enter__(self):
                return self
            def __exit__(self, *args):
                return False
        return FakeResponse()

    def outer_archive(self, name, data):
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w") as archive:
            archive.writestr(name, data)
        return buffer.getvalue()

    def test_plain_manifest_and_video_artifact_is_rejected(self):
        payload = self.outer_archive("manifest.json", b"{}")
        with patch("download_media_artifact.urllib.request.urlopen", return_value=self.response(payload)):
            with tempfile.TemporaryDirectory() as tmp:
                with self.assertRaisesRegex(ArtifactError, "encrypted_artifact_must_contain_one_file|unencrypted_or_unsafe_artifact_rejected"):
                    download_media_artifact("123", Path(tmp), repository="owner/repo", token="token", age_identity="AGE-SECRET-KEY-TEST")

    def test_missing_decryption_identity_fails_before_network(self):
        with patch("download_media_artifact.urllib.request.urlopen") as request:
            with tempfile.TemporaryDirectory() as tmp:
                with self.assertRaisesRegex(ArtifactError, "artifact_decryption_identity_missing"):
                    download_media_artifact("123", Path(tmp), repository="owner/repo", token="token", age_identity="")
            request.assert_not_called()

    def test_encrypted_bundle_is_decrypted_and_extracted(self):
        inner = io.BytesIO()
        with zipfile.ZipFile(inner, "w") as bundle:
            bundle.writestr("manifest.json", b'{"content_id":"c1"}')
            bundle.writestr("media.mp4", b"video")
        outer = self.outer_archive("media_bundle.zip.age", b"ciphertext")
        def fake_age(args, **kwargs):
            output = Path(args[args.index("--output") + 1])
            output.write_bytes(inner.getvalue())
            return SimpleNamespace(returncode=0)
        with patch("download_media_artifact.urllib.request.urlopen", return_value=self.response(outer)):
            with patch("download_media_artifact.subprocess.run", side_effect=fake_age):
                with tempfile.TemporaryDirectory() as tmp:
                    manifest, media = download_media_artifact(
                        "123", Path(tmp), repository="owner/repo", token="token",
                        age_identity="AGE-SECRET-KEY-TEST"
                    )
                    self.assertEqual('{"content_id":"c1"}', manifest.read_text(encoding="utf-8"))
                    self.assertEqual(b"video", media.read_bytes())
                    self.assertFalse((Path(tmp) / "media_bundle.zip.age").exists())
                    self.assertFalse((Path(tmp) / "media_bundle.zip").exists())
                    self.assertEqual(["manifest.json", "media.mp4"], sorted(p.name for p in Path(tmp).iterdir()))


if __name__ == "__main__":
    unittest.main()
