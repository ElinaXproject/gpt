#!/usr/bin/env python3
"""Persist a human safety-review checklist for one AUTORED IDEA content item."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from autored.d1_client import D1Client, D1Error


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--content-id", required=True)
    parser.add_argument("--profile-id", required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    try:
        report = json.loads(args.report.read_text(encoding="utf-8"))
        status, reference = D1Client().record_safety_review(
            content_id=args.content_id,
            profile_id=args.profile_id,
            reviewer=str(report.get("reviewer") or ""),
            reviewed_at=str(report.get("reviewed_at") or ""),
            decision=str(report.get("decision") or ""),
            checks=report.get("checks") if isinstance(report.get("checks"), dict) else {},
            notes=str(report.get("notes") or ""),
        )
    except (OSError, json.JSONDecodeError, D1Error, TypeError, ValueError) as exc:
        code = getattr(exc, "code", type(exc).__name__)
        print(json.dumps({"status": "blocked", "error": str(code)[:120]}, ensure_ascii=False))
        return 2
    print(json.dumps({
        "status": status,
        "content_id": args.content_id,
        "safety_review_reference": reference,
    }, ensure_ascii=False))
    return 0 if status == "passed" else 2


if __name__ == "__main__":
    raise SystemExit(main())
