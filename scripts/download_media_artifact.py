"""Download and decrypt one age-encrypted GitHub Actions media artifact."""
from __future__ import annotations

import io
import os
import re
import subprocess
import tempfile
import urllib.error
import urllib.request
import zipfile
from pathlib import Path


class ArtifactError(RuntimeError):
    pass


def download_media_artifact(
    artifact_id: str,
    destination: Path,
    repository: str | None = None,
    token: str | None = None,
    age_identity: str | None = None,
) -> tuple[Path, Path]:
    repository = repository or os.environ.get("GITHUB_REPOSITORY", "")
    token = token or os.environ.get("GITHUB_TOKEN", "")
    age_identity = age_identity or os.environ.get("AUTORED_ARTIFACT_AGE_IDENTITY", "")
    if not re.fullmatch(r"[0-9]+", str(artifact_id)):
        raise ArtifactError("invalid_artifact_id")
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repository):
        raise ArtifactError("invalid_repository")
    if not token:
        raise ArtifactError("github_token_missing")
    if not age_identity.strip().startswith("AGE-SECRET-KEY-"):
        raise ArtifactError("artifact_decryption_identity_missing")
    url = f"https://api.github.com/repos/{repository}/actions/artifacts/{artifact_id}/zip"
    request = urllib.request.Request(
        url,
        headers={"Authorization": "Bearer " + token, "Accept": "application/vnd.github+json"},
        method="GET",
    )
    try:
        with urllib.request.urlopen(request, timeout=90) as response:
            archive_bytes = response.read(500 * 1024 * 1024 + 1)
    except urllib.error.HTTPError as exc:
        raise ArtifactError(f"artifact_download_http_{exc.code}") from None
    except (urllib.error.URLError, TimeoutError, OSError):
        raise ArtifactError("artifact_download_network_error") from None
    if len(archive_bytes) > 500 * 1024 * 1024:
        raise ArtifactError("artifact_too_large")

    destination.mkdir(parents=True, exist_ok=True)
    encrypted_path = destination / "media_bundle.zip.age"
    decrypted_path = destination / "media_bundle.zip"
    identity_path: Path | None = None
    try:
        try:
            with zipfile.ZipFile(io.BytesIO(archive_bytes)) as zipped:
                files = [info for info in zipped.infolist() if not info.is_dir()]
                if len(files) != 1:
                    raise ArtifactError("encrypted_artifact_must_contain_one_file")
                info = files[0]
                name = Path(info.filename)
                if name.is_absolute() or ".." in name.parts or name.name != "media_bundle.zip.age":
                    raise ArtifactError("unencrypted_or_unsafe_artifact_rejected")
                if info.file_size > 500 * 1024 * 1024:
                    raise ArtifactError("encrypted_artifact_member_too_large")
                encrypted_path.write_bytes(zipped.read(info))
        except zipfile.BadZipFile:
            raise ArtifactError("artifact_zip_invalid") from None

        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", prefix=".autored-age-identity-", dir=destination, delete=False
        ) as identity_file:
            identity_file.write(age_identity.strip() + "\n")
            identity_path = Path(identity_file.name)
        os.chmod(identity_path, 0o600)
        try:
            subprocess.run(
                ["age", "--decrypt", "--identity", str(identity_path), "--output", str(decrypted_path), str(encrypted_path)],
                check=True,
                capture_output=True,
                text=True,
                timeout=300,
            )
        except FileNotFoundError:
            raise ArtifactError("age_binary_unavailable") from None
        except subprocess.TimeoutExpired:
            raise ArtifactError("artifact_decryption_timeout") from None
        except subprocess.CalledProcessError:
            raise ArtifactError("artifact_decryption_failed") from None

        try:
            with zipfile.ZipFile(decrypted_path) as bundle:
                files = [info for info in bundle.infolist() if not info.is_dir()]
                if len(files) != 2:
                    raise ArtifactError("decrypted_bundle_file_count_invalid")
                by_name = {Path(info.filename).name: info for info in files}
                if set(by_name) != {"manifest.json", "media.mp4"}:
                    raise ArtifactError("decrypted_bundle_layout_invalid")
                if any(Path(info.filename).is_absolute() or ".." in Path(info.filename).parts for info in files):
                    raise ArtifactError("unsafe_decrypted_bundle_path")
                if by_name["manifest.json"].file_size > 1024 * 1024:
                    raise ArtifactError("manifest_too_large")
                if by_name["media.mp4"].file_size > 300 * 1024 * 1024:
                    raise ArtifactError("media_too_large_for_artifact_runner")
                manifest_path = destination / "manifest.json"
                media_path = destination / "media.mp4"
                manifest_path.write_bytes(bundle.read(by_name["manifest.json"]))
                media_path.write_bytes(bundle.read(by_name["media.mp4"]))
        except zipfile.BadZipFile:
            raise ArtifactError("decrypted_bundle_zip_invalid") from None
        return manifest_path, media_path
    finally:
        if identity_path is not None:
            identity_path.unlink(missing_ok=True)
        encrypted_path.unlink(missing_ok=True)
        decrypted_path.unlink(missing_ok=True)
