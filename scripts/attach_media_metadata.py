#!/usr/bin/env python3
"""Attach a rendered MP4's verified metadata to an existing D1 content item."""
from __future__ import annotations

import argparse
import json
import mimetypes
from pathlib import Path

from autored.d1_client import D1Client, D1Error
from autored.media_validation import sha256_file


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--content-id", required=True)
    parser.add_argument("--profile-id", required=True)
    parser.add_argument("--media", type=Path, required=True)
    parser.add_argument("--music-embedded", action="store_true")
    parser.add_argument("--music-license-reference", default="")
    args = parser.parse_args()
    try:
        if not args.media.is_file():
            raise ValueError("media_file_missing")
        mime = mimetypes.guess_type(args.media.name)[0] or "application/octet-stream"
        digest = sha256_file(args.media)
        size = args.media.stat().st_size
        D1Client().attach_media_metadata(
            content_id=args.content_id,
            profile_id=args.profile_id,
            media_mime=mime,
            media_bytes=size,
            media_sha256=digest,
            music_embedded=args.music_embedded,
            music_license_reference=args.music_license_reference,
        )
    except (OSError, ValueError, D1Error) as exc:
        code = getattr(exc, "code", str(exc))
        print(json.dumps({"status": "blocked", "error": str(code)[:120]}, ensure_ascii=False))
        return 2
    print(json.dumps({
        "status": "attached",
        "content_id": args.content_id,
        "media_mime": mime,
        "media_bytes": size,
        "media_sha256": digest,
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
