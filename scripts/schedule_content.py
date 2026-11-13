#!/usr/bin/env python3
"""Create an idempotent D1 publication job after encrypted media artifact upload."""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from autored.d1_client import D1Client, D1Error


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--provider", choices=("tiktok_direct", "youtube_direct"), required=True)
    parser.add_argument("--artifact-id", required=True)
    args = parser.parse_args()
    try:
        if not re.fullmatch(r"[0-9]+", args.artifact_id):
            raise ValueError("artifact_id_invalid")
        manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
        if not isinstance(manifest, dict):
            raise ValueError("manifest_invalid")
        required = {"content_id", "profile_id", "scheduled_at", "idempotency_key", "media_sha256", "media_bytes", "media_mime"}
        if required - set(manifest):
            raise ValueError("manifest_fields_missing")
        reservation = D1Client().reserve_job(
            content_id=str(manifest["content_id"]),
            profile_id=str(manifest["profile_id"]),
            scheduled_at=str(manifest["scheduled_at"]),
            idempotency_key=str(manifest["idempotency_key"]),
            provider=args.provider,
            media_artifact_id=args.artifact_id,
        )
    except (OSError, json.JSONDecodeError, ValueError, D1Error) as exc:
        code = getattr(exc, "code", str(exc))
        print(json.dumps({"status": "blocked", "error": str(code)[:120]}, ensure_ascii=False))
        return 2
    print(json.dumps({
        "status": "queued",
        "job_id": reservation["job_id"],
        "content_id": manifest["content_id"],
        "provider": args.provider,
        "artifact_id": args.artifact_id,
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
