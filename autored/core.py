"""Deterministic, provider-neutral core for AUTORED IDEA.

This module intentionally does not perform network requests or publish content.
Platform adapters must be implemented separately and tested against official APIs.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
import hashlib
import json
from typing import Iterable
from urllib.parse import urlparse


class Platform(str, Enum):
    TIKTOK = "tiktok"
    YOUTUBE = "youtube"


@dataclass(frozen=True)
class Profile:
    key: str
    platform: Platform
    handle: str
    timezone_name: str = "Europe/Warsaw"


PROFILES: dict[str, Profile] = {
    "tiktok_ocenionona6": Profile("tiktok_ocenionona6", Platform.TIKTOK, "@ocenionona6"),
    "tiktok_pieknemedia": Profile("tiktok_pieknemedia", Platform.TIKTOK, "@pieknemedia"),
    "youtube_memoryagent": Profile("youtube_memoryagent", Platform.YOUTUBE, "@MemoryAgent-r3c"),
}


class JobStatus(str, Enum):
    PLANNED = "planned"
    READY = "ready"
    PUBLISHING = "publishing"
    PUBLISHED = "published"
    RETRY_WAIT = "retry_wait"
    BLOCKED = "blocked"
    FAILED = "failed"


ALLOWED_TRANSITIONS: dict[JobStatus, set[JobStatus]] = {
    JobStatus.PLANNED: {JobStatus.READY, JobStatus.BLOCKED, JobStatus.FAILED},
    JobStatus.READY: {JobStatus.PUBLISHING, JobStatus.BLOCKED, JobStatus.FAILED},
    JobStatus.PUBLISHING: {
        JobStatus.PUBLISHED, JobStatus.RETRY_WAIT, JobStatus.BLOCKED, JobStatus.FAILED
    },
    JobStatus.RETRY_WAIT: {JobStatus.READY, JobStatus.BLOCKED, JobStatus.FAILED},
    JobStatus.PUBLISHED: set(),
    JobStatus.BLOCKED: {JobStatus.READY, JobStatus.FAILED},
    JobStatus.FAILED: set(),
}


@dataclass(frozen=True)
class ContentPackage:
    content_id: str
    profile_key: str
    title: str
    description: str
    hashtags: tuple[str, ...]
    media_sha256: str
    media_mime: str
    media_bytes: int
    source_urls: tuple[str, ...] = ()
    rights_reference: str = ""
    ai_disclosure_required: bool = False
    ai_disclosure_set: bool = False
    safety_review_passed: bool = False
    source_published_at: tuple[str, ...] = ()
    fact_check_passed: bool = False
    fact_check_reference: str = ""

    def validate(self) -> list[str]:
        errors: list[str] = []
        if self.profile_key not in PROFILES:
            errors.append("unknown_profile")
        if not self.content_id.strip():
            errors.append("missing_content_id")
        if not self.title.strip():
            errors.append("missing_title")
        if not self.description.strip():
            errors.append("missing_description")
        if self.media_bytes <= 0:
            errors.append("invalid_media_size")
        if len(self.media_sha256) != 64 or any(c not in "0123456789abcdef" for c in self.media_sha256.lower()):
            errors.append("invalid_media_sha256")
        if not self.media_mime.startswith(("image/", "video/")):
            errors.append("unsupported_media_mime")
        if not self.rights_reference.strip():
            errors.append("missing_rights_reference")
        if len(set(self.source_urls)) != len(self.source_urls):
            errors.append("duplicate_source_url")
        if any(urlparse(url).scheme != "https" or not urlparse(url).hostname for url in self.source_urls):
            errors.append("invalid_source_url")

        research_profiles = {"tiktok_ocenionona6": 1, "youtube_memoryagent": 2}
        minimum_sources = research_profiles.get(self.profile_key, 0)
        if len(self.source_urls) < minimum_sources:
            errors.append("insufficient_verified_sources")
        if minimum_sources and not self.fact_check_passed:
            errors.append("fact_check_not_passed")
        if minimum_sources and not self.fact_check_reference.strip():
            errors.append("missing_fact_check_reference")
        if self.profile_key == "youtube_memoryagent":
            source_domains = {urlparse(url).hostname.lower().removeprefix("www.") for url in self.source_urls if urlparse(url).hostname}
            if len(source_domains) < 2:
                errors.append("insufficient_independent_source_domains")
        if minimum_sources and len(self.source_published_at) != len(self.source_urls):
            errors.append("source_dates_mismatch")
        if minimum_sources and len(self.source_published_at) == len(self.source_urls):
            now = datetime.now(timezone.utc)
            for published_at in self.source_published_at:
                try:
                    parsed = datetime.fromisoformat(published_at.replace("Z", "+00:00"))
                    if parsed.tzinfo is None:
                        errors.append("source_date_missing_timezone")
                        continue
                    age_seconds = (now - parsed.astimezone(timezone.utc)).total_seconds()
                    if age_seconds < -300 or age_seconds > 72 * 60 * 60:
                        errors.append("source_outside_72h_window")
                except (TypeError, ValueError):
                    errors.append("invalid_source_date")
        if self.ai_disclosure_required and not self.ai_disclosure_set:
            errors.append("missing_ai_disclosure")
        if not self.safety_review_passed:
            errors.append("safety_review_not_passed")
        if any(not tag.startswith("#") for tag in self.hashtags):
            errors.append("invalid_hashtag")
        return errors


@dataclass
class PublicationJob:
    idempotency_key: str
    content_id: str
    profile_key: str
    scheduled_at: datetime
    status: JobStatus = JobStatus.PLANNED
    attempts: int = 0
    platform_post_id: str | None = None
    published_url: str | None = None
    last_error_code: str | None = None
    events: list[str] = field(default_factory=list)

    def transition(self, next_status: JobStatus, event: str = "") -> None:
        if next_status not in ALLOWED_TRANSITIONS[self.status]:
            raise ValueError(f"invalid_transition:{self.status.value}->{next_status.value}")
        self.status = next_status
        if event:
            self.events.append(event)
        if next_status == JobStatus.PUBLISHING:
            self.attempts += 1


def make_idempotency_key(
    package: ContentPackage, scheduled_at: datetime
) -> str:
    if scheduled_at.tzinfo is None:
        raise ValueError("scheduled_at_must_be_timezone_aware")
    canonical = {
        "content_id": package.content_id,
        "profile_key": package.profile_key,
        "platform": PROFILES.get(package.profile_key, Profile("", Platform.TIKTOK, "")).platform.value,
        "media_sha256": package.media_sha256.lower(),
        "scheduled_at": scheduled_at.astimezone(timezone.utc).isoformat(),
    }
    payload = json.dumps(canonical, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def create_job(
    package: ContentPackage,
    scheduled_at: datetime,
    existing_keys: Iterable[str] = (),
) -> PublicationJob:
    errors = package.validate()
    if errors:
        raise ValueError("invalid_content_package:" + ",".join(errors))
    key = make_idempotency_key(package, scheduled_at)
    if key in set(existing_keys):
        raise ValueError("duplicate_publication_job")
    return PublicationJob(
        idempotency_key=key,
        content_id=package.content_id,
        profile_key=package.profile_key,
        scheduled_at=scheduled_at,
    )


@dataclass
class MonthlyQuota:
    limit: int
    used: int = 0

    @property
    def remaining(self) -> int:
        return max(0, self.limit - self.used)

    def reserve(self, amount: int = 1) -> bool:
        if amount <= 0:
            raise ValueError("amount_must_be_positive")
        if self.used + amount > self.limit:
            return False
        self.used += amount
        return True


def is_retryable_error(code: str, http_status: int | None = None) -> bool:
    """Only transient transport/rate/server failures may be retried."""
    if code in {"network_timeout", "connection_reset", "temporary_unavailable"}:
        return True
    return http_status == 429 or (http_status is not None and 500 <= http_status <= 599)
