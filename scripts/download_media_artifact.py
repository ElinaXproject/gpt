"""Download a single private GitHub Actions artifact safely by numeric artifact ID."""
from __future__ import annotations

import io
import os
import re
import urllib.error
import urllib.request
import zipfile
from pathlib import Path


class ArtifactError(RuntimeError):
    pass


def download_media_artifact(artifact_id: str, destination: Path, repository: str | None = None, token: str | None = None) -> tuple[Path, Path]:
    repository = repository or os.environ.get("GITHUB_REPOSITORY", "")
    token = token or os.environ.get("GITHUB_TOKEN", "")
    if not re.fullmatch(r"[0-9]+", str(artifact_id)):
        raise ArtifactError("invalid_artifact_id")
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repository):
        raise ArtifactError("invalid_repository")
    if not token:
        raise ArtifactError("github_token_missing")
    url = f"https://api.github.com/repos/{repository}/actions/artifacts/{artifact_id}/zip"
    request = urllib.request.Request(
        url,
        headers={"Authorization": "Bearer " + token, "Accept": "application/vnd.github+json"},
        method="GET",
    )
    try:
        with urllib.request.urlopen(request, timeout=90) as response:
            archive = response.read(500 * 1024 * 1024 + 1)
    except urllib.error.HTTPError as exc:
        raise ArtifactError(f"artifact_download_http_{exc.code}") from None
    except (urllib.error.URLError, TimeoutError, OSError):
        raise ArtifactError("artifact_download_network_error") from None
    if len(archive) > 500 * 1024 * 1024:
        raise ArtifactError("artifact_too_large")
    destination.mkdir(parents=True, exist_ok=True)
    try:
        with zipfile.ZipFile(io.BytesIO(archive)) as zipped:
            files = [info for info in zipped.infolist() if not info.is_dir()]
            if len(files) > 5:
                raise ArtifactError("artifact_file_count_exceeded")
            for info in files:
                name = Path(info.filename)
                if name.is_absolute() or ".." in name.parts:
                    raise ArtifactError("unsafe_artifact_path")
                if info.file_size > 300 * 1024 * 1024:
                    raise ArtifactError("artifact_member_too_large")
            manifest_info = next((item for item in files if Path(item.filename).name == "manifest.json"), None)
            media_info = next((item for item in files if Path(item.filename).suffix.lower() == ".mp4"), None)
            if not manifest_info or not media_info:
                raise ArtifactError("artifact_manifest_or_mp4_missing")
            manifest_path = destination / "manifest.json"
            media_path = destination / "media.mp4"
            manifest_path.write_bytes(zipped.read(manifest_info))
            media_path.write_bytes(zipped.read(media_info))
    except zipfile.BadZipFile:
        raise ArtifactError("artifact_zip_invalid") from None
    return manifest_path, media_path
