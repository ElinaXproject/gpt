#!/usr/bin/env python3
"""Package one media job and encrypt the complete bundle with age before upload."""
from __future__ import annotations

import argparse
import hashlib
import json
import mimetypes
import os
import subprocess
import tempfile
import zipfile
from pathlib import Path
from typing import Any


class MediaArtifactError(RuntimeError):
    pass


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_plain_bundle(manifest_path: Path, media_path: Path, output_zip: Path) -> dict[str, Any]:
    if not manifest_path.is_file() or not media_path.is_file():
        raise MediaArtifactError("manifest_or_media_missing")
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        raise MediaArtifactError("manifest_unreadable") from None
    if not isinstance(manifest, dict):
        raise MediaArtifactError("manifest_invalid")
    expected_hash = manifest.get("media_sha256")
    expected_size = manifest.get("media_bytes")
    expected_mime = manifest.get("media_mime")
    actual_hash = sha256_file(media_path)
    actual_size = media_path.stat().st_size
    actual_mime = mimetypes.guess_type(media_path.name)[0] or "application/octet-stream"
    if actual_hash != expected_hash:
        raise MediaArtifactError("media_sha256_mismatch")
    if actual_size != expected_size:
        raise MediaArtifactError("media_size_mismatch")
    if actual_mime != expected_mime:
        raise MediaArtifactError("media_mime_mismatch")
    if actual_mime != "video/mp4":
        raise MediaArtifactError("media_mime_not_mp4")
    output_zip.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output_zip, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=1) as archive:
        archive.write(manifest_path, "manifest.json")
        archive.write(media_path, "media.mp4")
    return {"media_sha256": actual_hash, "media_bytes": actual_size, "media_mime": actual_mime}


def create_encrypted_bundle(
    manifest_path: Path,
    media_path: Path,
    output_path: Path,
    recipient: str | None = None,
) -> dict[str, Any]:
    recipient = recipient or os.environ.get("AUTORED_ARTIFACT_AGE_RECIPIENT", "")
    if not isinstance(recipient, str) or not recipient.startswith("age1"):
        raise MediaArtifactError("age_recipient_missing_or_invalid")
    with tempfile.TemporaryDirectory(prefix="autored-media-bundle-") as tmp:
        plain_zip = Path(tmp) / "media_bundle.zip"
        details = build_plain_bundle(manifest_path, media_path, plain_zip)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        if output_path.exists():
            raise MediaArtifactError("encrypted_output_already_exists")
        try:
            subprocess.run(
                ["age", "--recipient", recipient, "--output", str(output_path), str(plain_zip)],
                check=True,
                capture_output=True,
                text=True,
                timeout=600,
            )
        except FileNotFoundError:
            output_path.unlink(missing_ok=True)
            raise MediaArtifactError("age_binary_unavailable") from None
        except subprocess.TimeoutExpired:
            output_path.unlink(missing_ok=True)
            raise MediaArtifactError("age_encryption_timeout") from None
        except subprocess.CalledProcessError:
            output_path.unlink(missing_ok=True)
            raise MediaArtifactError("age_encryption_failed") from None
    if not output_path.is_file() or output_path.stat().st_size <= 0:
        raise MediaArtifactError("encrypted_bundle_missing")
    details["encrypted_bytes"] = output_path.stat().st_size
    details["encrypted_sha256"] = sha256_file(output_path)
    details["output"] = str(output_path)
    return details


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--media", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = create_encrypted_bundle(args.manifest, args.media, args.output)
    except (MediaArtifactError, OSError) as exc:
        print(json.dumps({"status": "failed", "error": str(exc)[:120]}, ensure_ascii=False))
        return 2
    print(json.dumps({"status": "encrypted", **result}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
