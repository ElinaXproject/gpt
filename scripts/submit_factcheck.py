#!/usr/bin/env python3
"""Validate and persist a human-reviewed fact-check report for one content item."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from autored.d1_client import D1Client, D1Error
from autored.factcheck import Claim, Evidence, FactCheckReport


def load_report(path: Path) -> FactCheckReport:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return FactCheckReport(
        profile_key=str(payload["profile_key"]),
        reviewed_at=str(payload["reviewed_at"]),
        reviewer=str(payload["reviewer"]),
        reviewer_type=str(payload["reviewer_type"]),
        decision=str(payload["decision"]),
        claims=tuple(Claim(str(item["claim_id"]), str(item["text"])) for item in payload["claims"]),
        evidence=tuple(
            Evidence(
                url=str(item["url"]),
                title=str(item["title"]),
                published_at=str(item["published_at"]),
                supports_claim_ids=tuple(str(value) for value in item["supports_claim_ids"]),
                support_type=str(item.get("support_type", "direct")),
            )
            for item in payload["evidence"]
        ),
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--content-id", required=True)
    parser.add_argument("--profile-id", required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    try:
        report = load_report(args.report)
        reference = D1Client().record_fact_check_report(args.content_id, args.profile_id, report)
    except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError, D1Error) as exc:
        code = getattr(exc, "code", type(exc).__name__)
        print(json.dumps({"status": "blocked", "error": str(code)[:120]}, ensure_ascii=False))
        return 2
    print(json.dumps({"status": "approved", "content_id": args.content_id, "fact_check_reference": reference}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
