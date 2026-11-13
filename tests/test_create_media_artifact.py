import hashlib
import json
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from create_media_artifact import MediaArtifactError, build_plain_bundle, create_encrypted_bundle


class CreateMediaArtifactTests(unittest.TestCase):
    def create_inputs(self, directory):
        media = directory / "clip.mp4"
        media.write_bytes(b"sample-video")
        manifest = directory / "manifest.json"
        manifest.write_text(json.dumps({
            "media_sha256": hashlib.sha256(b"sample-video").hexdigest(),
            "media_bytes": len(b"sample-video"),
            "media_mime": "video/mp4",
        }), encoding="utf-8")
        return manifest, media

    def test_plain_bundle_contains_only_manifest_and_media(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest, media = self.create_inputs(root)
            bundle = root / "plain.zip"
            result = build_plain_bundle(manifest, media, bundle)
            self.assertEqual(len(b"sample-video"), result["media_bytes"])
            with zipfile.ZipFile(bundle) as archive:
                self.assertEqual(["manifest.json", "media.mp4"], sorted(archive.namelist()))
                self.assertEqual(b"sample-video", archive.read("media.mp4"))

    def test_media_hash_mismatch_blocks_packaging(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest, media = self.create_inputs(root)
            manifest.write_text(json.dumps({
                "media_sha256": "0" * 64, "media_bytes": media.stat().st_size, "media_mime": "video/mp4"
            }), encoding="utf-8")
            with self.assertRaisesRegex(MediaArtifactError, "media_sha256_mismatch"):
                build_plain_bundle(manifest, media, root / "plain.zip")

    def test_encrypted_output_is_created_only_after_age_command(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest, media = self.create_inputs(root)
            output = root / "media_bundle.zip.age"
            def fake_age(args, **kwargs):
                self.assertIn("age1recipient", args)
                output.write_bytes(b"encrypted-payload")
                return SimpleNamespace(returncode=0)
            with patch("create_media_artifact.subprocess.run", side_effect=fake_age):
                result = create_encrypted_bundle(manifest, media, output, recipient="age1recipient")
            self.assertEqual("encrypted", "encrypted" if output.exists() else "")
            self.assertEqual(hashlib.sha256(b"encrypted-payload").hexdigest(), result["encrypted_sha256"])
            self.assertEqual(["manifest.json", "clip.mp4", "media_bundle.zip.age"], sorted(p.name for p in root.iterdir()))


if __name__ == "__main__":
    unittest.main()
