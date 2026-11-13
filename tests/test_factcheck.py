import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from autored.factcheck import Claim, Evidence, FactCheckReport


class FactCheckReportTests(unittest.TestCase):
    def setUp(self):
        now = datetime.now(timezone.utc).isoformat()
        self.report = FactCheckReport(
            profile_key="youtube_memoryagent",
            reviewed_at=now,
            reviewer="ai_verifier:independent-review",
            reviewer_type="ai_verifier",
            decision="approved",
            claims=(Claim("c1", "A specific factual claim"),),
            evidence=(
                Evidence("https://example.org/a", "Source A", now, ("c1",)),
                Evidence("https://example.net/b", "Source B", now, ("c1",)),
            ),
        )
        self.allowed = {"example.org", "example.net"}

    def test_two_independent_direct_sources_pass(self):
        self.assertEqual([], self.report.validate(self.allowed))
        self.assertTrue(self.report.approved(self.allowed))

    def test_same_domain_does_not_count_as_independent_sources(self):
        report = FactCheckReport(
            profile_key="youtube_memoryagent",
            reviewed_at=self.report.reviewed_at,
            reviewer="editor",
            reviewer_type="human",
            decision="approved",
            claims=self.report.claims,
            evidence=(
                Evidence("https://example.org/a", "Source A", self.report.reviewed_at, ("c1",)),
                Evidence("https://sub.example.org/b", "Source B", self.report.reviewed_at, ("c1",)),
            ),
        )
        self.assertIn("insufficient_independent_evidence:c1", report.validate({"example.org"}))

    def test_stale_evidence_is_rejected(self):
        old = (datetime.now(timezone.utc) - timedelta(days=4)).isoformat()
        evidence = tuple(
            Evidence(item.url, item.title, old, item.supports_claim_ids)
            for item in self.report.evidence
        )
        report = FactCheckReport(
            self.report.profile_key,
            self.report.reviewed_at,
            self.report.reviewer,
            self.report.reviewer_type,
            self.report.decision,
            self.report.claims,
            evidence,
        )
        self.assertIn("evidence_outside_72h_window", report.validate(self.allowed))

    def test_rejected_report_cannot_pass(self):
        report = FactCheckReport(
            self.report.profile_key,
            self.report.reviewed_at,
            self.report.reviewer,
            self.report.reviewer_type,
            "rejected",
            self.report.claims,
            self.report.evidence,
        )
        self.assertIn("fact_check_not_approved", report.validate(self.allowed))

    def test_non_allowlisted_source_is_rejected(self):
        evidence = (
            Evidence("https://attacker.example/a", "Source A", self.report.reviewed_at, ("c1",)),
            self.report.evidence[1],
        )
        report = FactCheckReport(
            self.report.profile_key,
            self.report.reviewed_at,
            self.report.reviewer,
            self.report.reviewer_type,
            self.report.decision,
            self.report.claims,
            evidence,
        )
        self.assertIn("evidence_url_not_allowlisted", report.validate(self.allowed))

    def test_reference_is_stable(self):
        self.assertEqual(self.report.reference(), self.report.reference())
        self.assertTrue(self.report.reference().startswith("fc_"))


if __name__ == "__main__":
    unittest.main()
