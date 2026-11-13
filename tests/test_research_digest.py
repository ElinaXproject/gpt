import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import research_digest


class FakeResponse:
    def __init__(self, body, url, status=200):
        self.body = body
        self.url = url
        self.status = status

    def read(self, _limit=None):
        return self.body

    def geturl(self):
        return self.url

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


class ResearchDigestTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 11, 13, 12, tzinfo=timezone.utc)
        self.feed = {
            "id": "test_feed",
            "name": "The Verge",
            "url": "https://feeds.theverge.com/rss/index.xml",
            "feed_domains": ["theverge.com"],
            "allowed_domains": ["theverge.com"],
        }

    def test_fetches_only_fresh_allowlisted_articles(self):
        xml = b"""<rss><channel>
        <item><title>New AI model released</title><link>https://www.theverge.com/ai/123</link><pubDate>Fri, 13 Nov 2026 10:00:00 GMT</pubDate></item>
        <item><title>Old AI model story</title><link>https://theverge.com/ai/old</link><pubDate>Mon, 09 Nov 2026 10:00:00 GMT</pubDate></item>
        <item><title>Future AI story</title><link>https://theverge.com/ai/future</link><pubDate>Fri, 13 Nov 2026 15:00:00 GMT</pubDate></item>
        <item><title>Untrusted source</title><link>https://theverge.com.attacker.example/a</link><pubDate>Fri, 13 Nov 2026 11:00:00 GMT</pubDate></item>
        </channel></rss>"""
        with patch.object(research_digest.urllib.request, "urlopen", return_value=FakeResponse(xml, self.feed["url"])):
            items = research_digest.fetch_feed_items(self.feed, self.now)
        self.assertEqual(1, len(items))
        self.assertEqual("New AI model released", items[0]["title"])
        self.assertEqual("theverge.com", items[0]["domain"])

    def test_rejects_redirect_to_untrusted_feed_host(self):
        with patch.object(research_digest.urllib.request, "urlopen", return_value=FakeResponse(b"<rss/>", "https://attacker.example/feed")):
            with self.assertRaisesRegex(ValueError, "feed_redirect_not_allowlisted"):
                research_digest.fetch_feed_items(self.feed, self.now)

    def test_atom_link_prefers_alternate_not_self(self):
        import xml.etree.ElementTree as ET
        node = ET.fromstring(
            '<entry xmlns="http://www.w3.org/2005/Atom">'
            '<link rel="self" href="https://theverge.com/self"/>'
            '<link rel="alternate" href="https://theverge.com/article"/>'
            '</entry>'
        )
        self.assertEqual("https://theverge.com/article", research_digest.extract_link(node))

    def test_match_sources_ranks_keyword_overlap(self):
        items = [
            {"title": "AI model changes search", "published_at": "2026-11-13T10:00:00+00:00", "source": "A"},
            {"title": "New electric car battery", "published_at": "2026-11-13T11:00:00+00:00", "source": "B"},
        ]
        result = research_digest.match_sources("AI model research", items)
        self.assertEqual(1, len(result))
        self.assertEqual("A", result[0]["source"])
        self.assertGreater(result[0]["relevance_score"], 0)

    def test_empty_feed_list_is_supported_for_offline_digest(self):
        result = research_digest.build_digest(
            [{"profile_id": "youtube_memoryagent", "topic": "AI", "research_query": "AI model"}],
            feeds=[],
            now=self.now,
        )
        self.assertEqual(0, result["feed_summary"]["total"])
        self.assertEqual("no_recent_source_match", result["profiles"][0]["status"])


    def test_humor_profile_does_not_require_news_research(self):
        result = research_digest.build_digest(
            [{
                "profile_id": "tiktok_pieknemedia",
                "theme": "humor",
                "topic": "Humor sytuacyjny",
                "research_query": "treść autorska"
            }],
            feeds=[],
            now=self.now,
        )
        self.assertEqual("research_not_required", result["profiles"][0]["status"])

    def test_naive_now_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "now_must_be_timezone_aware"):
            research_digest.build_digest([], feeds=[], now=datetime(2026, 11, 13, 12))


if __name__ == "__main__":
    unittest.main()
