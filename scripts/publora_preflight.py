#!/usr/bin/env python3
"""Read-only Publora preflight for AUTORED IDEA. Never creates or publishes posts."""
from __future__ import annotations

import json
import os
import sys
from typing import Any

from publora_client import PubloraClient, PubloraError
from publora_pipeline import PROFILES
from autored.d1_client import D1Client, D1Error


EXPECTED_YOUTUBE_PLATFORM_ID = "youtube-UCOE1EX9WZGDesaJNYIEhj7g"


def run_preflight(client: Any, d1_client: Any | None = None) -> dict[str, Any]:
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
            healthy = connection.get("connectionStatus") == "active" and connection.get("tokenStatus") in {"valid", "active", "ok"}
            results.append({
                "profile_id": profile_id,
                "status": "ready" if healthy else "blocked",
                "reason": None if healthy else "provider_connection_not_verified",
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
    account_result = {"status": "not_checked"}
    try:
        context = client.account_context()
        allowed = context.get("allowedPlatforms")
        expected_platforms = {"tiktok", "youtube"}
        unsupported = sorted(expected_platforms - set(allowed or [])) if isinstance(allowed, list) else []
        features = context.get("features", {})
        account_result = {
            "status": "ready" if not unsupported and features.get("publishing") is True and features.get("apiAccess") is True else "blocked",
            "plan": context.get("plan", {}).get("name"),
            "monthly_posts_remaining": context.get("quotas", {}).get("monthlyPosts", {}).get("remaining"),
            "scheduled_slots_remaining": context.get("quotas", {}).get("scheduledPosts", {}).get("remaining"),
            "connections_remaining": context.get("quotas", {}).get("connections", {}).get("remaining"),
            "max_scheduled_date": context.get("quotas", {}).get("scheduleHorizon", {}).get("maxScheduledDate"),
            "unsupported_platforms": unsupported,
        }
    except PubloraError as exc:
        account_result = {"status": "blocked", "reason": exc.code}
    d1_result = {"status": "not_checked"}
    if d1_client is not None:
        try:
            rows = d1_client.query("SELECT handle FROM profiles WHERE enabled=1", []).get("results", [])
            actual = {row.get("handle") for row in rows}
            expected = {profile["handle"] for profile in PROFILES.values()}
            missing = sorted(expected - actual)
            d1_result = {
                "status": "ready" if not missing else "incomplete",
                "expected_profiles": len(expected),
                "found_profiles": len(actual & expected),
                "missing_profiles": missing,
            }
        except D1Error as exc:
            d1_result = {"status": "blocked", "reason": exc.code}
    all_ready = ready == len(PROFILES) and account_result["status"] == "ready" and d1_result["status"] == "ready"
    return {
        "status": "ready" if all_ready else "incomplete",
        "publora_account": account_result,
        "ready_profiles": ready,
        "total_profiles": len(PROFILES),
        "d1_database": d1_result,
        "publishing_performed": False,
        "profiles": results,
    }


def main() -> int:
    missing_secrets = [
        name for name in ("PUBLORA_API_KEY", "CLOUDFLARE_API_TOKEN")
        if not os.environ.get(name)
    ]
    if missing_secrets:
        print(json.dumps({
            "status": "blocked",
            "reason": "required_secrets_missing",
            "missing": missing_secrets,
            "publishing_performed": False,
        }, indent=2))
        return 2
    try:
        result = run_preflight(PubloraClient(), D1Client())
    except (PubloraError, D1Error) as exc:
        print(json.dumps({"status": "blocked", "reason": exc.code, "publishing_performed": False}))
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "ready" else 1


if __name__ == "__main__":
    raise SystemExit(main())
