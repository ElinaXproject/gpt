import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from test_rss_feeds import domain_allowed


class RSSFeedSecurityTests(unittest.TestCase):
    def test_allows_exact_source_host(self):
        self.assertTrue(domain_allowed("bbc.co.uk", ["bbc.co.uk"]))

    def test_allows_real_subdomain(self):
        self.assertTrue(domain_allowed("feeds.bbc.co.uk", ["bbc.co.uk"]))

    def test_rejects_lookalike_suffix(self):
        self.assertFalse(domain_allowed("bbc.co.uk.attacker.example", ["bbc.co.uk"]))

    def test_rejects_unrelated_host(self):
        self.assertFalse(domain_allowed("example.org", ["bbc.co.uk"]))

    def test_rejects_empty_host(self):
        self.assertFalse(domain_allowed("", ["bbc.co.uk"]))

    def test_normalizes_case_and_www(self):
        self.assertTrue(domain_allowed("WWW.BBC.CO.UK", ["bbc.co.uk"]))


if __name__ == "__main__":
    unittest.main()
