from datetime import datetime, timezone, timedelta
import unittest

from autored.core import (
    ContentPackage,
    JobStatus,
    MonthlyQuota,
    PROFILES,
    create_job,
    is_retryable_error,
    make_idempotency_key,
)


class AutoRedCoreTests(unittest.TestCase):
    def package(self, profile="tiktok_pieknemedia", **overrides):
        values = {
            "content_id": "content-001",
            "profile_key": profile,
            "title": "Test title",
            "description": "Test description",
            "hashtags": ("#test", "#autored"),
            "media_sha256": "a" * 64,
            "media_mime": "image/jpeg",
            "media_bytes": 12345,
            "source_urls": ("https://example.org/source",),
            "rights_reference": "original-or-licensed",
            "ai_disclosure_required": True,
            "ai_disclosure_set": True,
        }
        values.update(overrides)
        return ContentPackage(**values)

    def test_three_target_profiles_are_registered(self):
        self.assertEqual(
            {"@ocenionona6", "@pieknemedia", "@MemoryAgent-r3"},
            {profile.handle for profile in PROFILES.values()},
        )

    def test_valid_package_passes(self):
        self.assertEqual([], self.package().validate())

    def test_missing_ai_disclosure_blocks_package(self):
        package = self.package(ai_disclosure_set=False)
        self.assertIn("missing_ai_disclosure", package.validate())

    def test_missing_rights_reference_blocks_package(self):
        package = self.package(rights_reference="")
        self.assertIn("missing_rights_reference", package.validate())

    def test_idempotency_key_is_stable_for_same_job(self):
        scheduled = datetime(2026, 11, 14, 9, tzinfo=timezone.utc)
        package = self.package()
        self.assertEqual(
            make_idempotency_key(package, scheduled),
            make_idempotency_key(package, scheduled),
        )

    def test_profile_or_schedule_changes_idempotency_key(self):
        scheduled = datetime(2026, 11, 14, 9, tzinfo=timezone.utc)
        package = self.package()
        other_profile = self.package(profile="tiktok_ocenionona6")
        later = scheduled + timedelta(hours=1)
        self.assertNotEqual(
            make_idempotency_key(package, scheduled),
            make_idempotency_key(other_profile, scheduled),
        )
        self.assertNotEqual(
            make_idempotency_key(package, scheduled),
            make_idempotency_key(package, later),
        )

    def test_duplicate_job_is_rejected(self):
        scheduled = datetime(2026, 11, 14, 9, tzinfo=timezone.utc)
        package = self.package()
        job = create_job(package, scheduled)
        with self.assertRaisesRegex(ValueError, "duplicate_publication_job"):
            create_job(package, scheduled, existing_keys=(job.idempotency_key,))

    def test_naive_datetime_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "timezone_aware"):
            make_idempotency_key(self.package(), datetime(2026, 11, 14, 9))

    def test_state_machine_rejects_skipping_validation(self):
        job = create_job(self.package(), datetime(2026, 11, 14, 9, tzinfo=timezone.utc))
        with self.assertRaisesRegex(ValueError, "invalid_transition"):
            job.transition(JobStatus.PUBLISHING)

    def test_valid_state_machine_and_attempt_count(self):
        job = create_job(self.package(), datetime(2026, 11, 14, 9, tzinfo=timezone.utc))
        job.transition(JobStatus.READY, "validation_passed")
        job.transition(JobStatus.PUBLISHING, "adapter_started")
        self.assertEqual(1, job.attempts)
        job.transition(JobStatus.PUBLISHED, "platform_confirmed")
        self.assertEqual(JobStatus.PUBLISHED, job.status)

    def test_monthly_quota_never_exceeds_limit(self):
        quota = MonthlyQuota(limit=2)
        self.assertTrue(quota.reserve())
        self.assertTrue(quota.reserve())
        self.assertFalse(quota.reserve())
        self.assertEqual(0, quota.remaining)

    def test_retry_classification_is_conservative(self):
        self.assertTrue(is_retryable_error("network_timeout"))
        self.assertTrue(is_retryable_error("http_error", 429))
        self.assertTrue(is_retryable_error("http_error", 503))
        self.assertFalse(is_retryable_error("invalid_media", 400))
        self.assertFalse(is_retryable_error("permission_denied", 403))


if __name__ == "__main__":
    unittest.main()
