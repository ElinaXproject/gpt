"""Structured, auditable fact-check report validation for AUTORED IDEA.

This validates evidence structure, freshness, source independence and explicit
review decisions. It does not claim to prove semantic truth automatically.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
from urllib.parse import urlparse

from .core import PROFILES


@dataclass(frozen=True)
class Claim:
    claim_id: str
    text: str


@dataclass(frozen=True)
class Evidence:
    url: str
    title: str
    published_at: str
    supports_claim_ids: tuple[str, ...]
    support_type: str = "direct"


@dataclass(frozen=True)
class FactCheckReport:
    profile_key: str
    reviewed_at: str
    reviewer: str
    reviewer_type: str
    decision: str
    claims: tuple[Claim, ...]
    evidence: tuple[Evidence, ...]

    def validate(self, allowed_domains: set[str]) -> list[str]:
        errors: list[str] = []
        if self.profile_key not in PROFILES:
            return ["unknown_profile"]
        try:
            reviewed = datetime.fromisoformat(self.reviewed_at.replace("Z", "+00:00"))
            if reviewed.tzinfo is None:
                errors.append("review_timestamp_missing_timezone")
        except (TypeError, ValueError):
            reviewed = None
            errors.append("invalid_review_timestamp")
        if not self.reviewer.strip():
            errors.append("missing_reviewer")
        if self.reviewer_type not in {"human", "ai_verifier"}:
            errors.append("invalid_reviewer_type")
        if self.decision != "approved":
            errors.append("fact_check_not_approved")
        if not self.claims:
            errors.append("missing_claims")

        claim_ids = [claim.claim_id for claim in self.claims]
        if any(not claim_id.strip() for claim_id in claim_ids) or len(set(claim_ids)) != len(claim_ids):
            errors.append("invalid_or_duplicate_claim_id")
        if any(not claim.text.strip() for claim in self.claims):
            errors.append("empty_claim_text")

        evidence_urls = [item.url for item in self.evidence]
        if len(set(evidence_urls)) != len(evidence_urls):
            errors.append("duplicate_evidence_url")
        now = reviewed.astimezone(timezone.utc) if reviewed and reviewed.tzinfo else datetime.now(timezone.utc)
        evidence_by_claim: dict[str, list[tuple[str, str]]] = {claim_id: [] for claim_id in claim_ids}

        for item in self.evidence:
            parsed_url = urlparse(item.url)
            domain = (parsed_url.hostname or "").lower().removeprefix("www.")
            if parsed_url.scheme != "https" or not domain or domain not in allowed_domains:
                errors.append("evidence_url_not_allowlisted")
                continue
            if item.support_type != "direct":
                errors.append("evidence_not_direct_support")
                continue
            try:
                published = datetime.fromisoformat(item.published_at.replace("Z", "+00:00"))
                if published.tzinfo is None:
                    errors.append("evidence_timestamp_missing_timezone")
                    continue
                age = (now - published.astimezone(timezone.utc)).total_seconds()
                if age < -300 or age > 72 * 60 * 60:
                    errors.append("evidence_outside_72h_window")
                    continue
            except (TypeError, ValueError):
                errors.append("invalid_evidence_timestamp")
                continue
            for claim_id in item.supports_claim_ids:
                if claim_id not in evidence_by_claim:
                    errors.append("evidence_references_unknown_claim")
                    continue
                evidence_by_claim[claim_id].append((domain, item.url))

        minimum_domains = 2 if self.profile_key == "youtube_memoryagent" else (
            1 if self.profile_key == "tiktok_ocenionona6" else 0
        )
        for claim_id, items in evidence_by_claim.items():
            distinct_domains = {domain for domain, _ in items}
            if len(distinct_domains) < minimum_domains:
                errors.append("insufficient_independent_evidence:" + claim_id)
        return sorted(set(errors))

    def reference(self) -> str:
        payload = {
            "profile_key": self.profile_key,
            "reviewed_at": self.reviewed_at,
            "reviewer": self.reviewer,
            "reviewer_type": self.reviewer_type,
            "decision": self.decision,
            "claims": [claim.__dict__ for claim in self.claims],
            "evidence": [
                {
                    "url": item.url,
                    "title": item.title,
                    "published_at": item.published_at,
                    "supports_claim_ids": list(item.supports_claim_ids),
                    "support_type": item.support_type,
                }
                for item in self.evidence
            ],
        }
        canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        return "fc_" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    def approved(self, allowed_domains: set[str]) -> bool:
        return not self.validate(allowed_domains)
