#!/usr/bin/env python3
"""Read-only Publora preflight for AUTORED IDEA. Never creates or publishes posts."""
from __future__ import annotations

import json
import os
import sys
from typing import Any

from publora_client import PubloraClient, PubloraError
from publora_pipeline import PROFILES


EXPECTED_YOUTUBE_PLATFORM_ID = "youtube-UCOE1EX9WZGDesaJNYIEhj7g"


def run_preflight(client: Any) -> dict[str, Any]:
    results = []
    for profile_id, profile in PROFILES.items():
        try:
            connection = client.resolve_connection(profile["platform"], profile["handle"])
            if profile_id == "youtube_memoryagent" and connection.get("platformId") != EXPECTED_YOUTUBE_PLATFORM_ID:
                results.append({
                    "profile_id": profile_id,
                    "status": "blocked",
                    "reason": "youtube_channel_id_mismatch",
                    "expected_platform_id": EXPECTED_YOUTUBE_PLATFORM_ID,
                    "actual_platform_id": connection.get("platformId"),
                })
                continue
            check = client.test_connection(connection["platformId"])
            healthy = check.get("status") in {"ok", "success"} or check.get("success") is True
            results.append({
                "profile_id": profile_id,
                "status": "ready" if healthy else "blocked",
                "reason": None if healthy else "provider_test_failed",
                "platform_id": connection["platformId"],
                "connection_status": connection.get("connectionStatus"),
                "token_status": connection.get("tokenStatus"),
            })
        except PubloraError as exc:
            results.append({
                "profile_id": profile_id,
                "status": "blocked",
                "reason": exc.code,
            })
    ready = sum(1 for item in results if item["status"] == "ready")
    return {
        "status": "ready" if ready == len(PROFILES) else "incomplete",
        "ready_profiles": ready,
        "total_profiles": len(PROFILES),
        "publishing_performed": False,
        "profiles": results,
    }


def main() -> int:
    if not os.environ.get("PUBLORA_API_KEY"):
        print(json.dumps({
            "status": "blocked",
            "reason": "PUBLORA_API_KEY_secret_missing",
            "publishing_performed": False,
        }, indent=2))
        return 2
    try:
        result = run_preflight(PubloraClient())
    except PubloraError as exc:
        print(json.dumps({"status": "blocked", "reason": exc.code, "publishing_performed": False}))
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "ready" else 1


if __name__ == "__main__":
    raise SystemExit(main())
