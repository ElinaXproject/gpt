#!/usr/bin/env python3
"""Build a source-backed 72-hour research candidate digest from curated RSS feeds.

This is discovery, not fact-checking. Only article titles, dates, URLs and
allowlisted domains are used; no external page text is passed into AI prompts.
"""
from __future__ import annotations

import argparse
import email.utils
import json
import re
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[1]
FEEDS = json.loads((ROOT / "config/research_feeds.json").read_text(encoding="utf-8"))
USER_AGENT = "AUTORED-IDEA-Research/1.0 (+https://github.com/ElinaXproject/gpt)"
STOP_WORDS = {
    "about", "after", "and", "are", "for", "from", "how", "into", "that", "the",
    "this", "with", "what", "when", "where", "why", "your", "oraz", "jest",
    "jako", "który", "która", "które", "oraz", "przez", "czyli", "tego", "dla",
    "nad", "pod", "bez", "jak", "czy", "nie", "się", "or", "a", "i", "w", "z",
}


def local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1].lower()


def child_text(element: ET.Element, names: set[str]) -> str:
    for child in list(element):
        if local_name(child.tag) in names:
            if child.text and child.text.strip():
                return child.text.strip()
            href = child.attrib.get("href")
            if href:
                return href.strip()
    return ""


def extract_link(element: ET.Element) -> str:
    links = [node for node in list(element) if local_name(node.tag) == "link"]
    for node in links:
        rel = node.attrib.get("rel", "alternate").lower()
        if rel in {"alternate", ""}:
            candidate = node.attrib.get("href") or (node.text or "").strip()
            if candidate:
                return candidate
    return child_text(element, {"link", "id"})


def parse_date(value: str):
    if not value:
        return None
    try:
        parsed = email.utils.parsedate_to_datetime(value)
        if parsed.tzinfo is None:
            return None
        return parsed.astimezone(timezone.utc)
    except (TypeError, ValueError, OverflowError):
        pass
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            return None
        return parsed.astimezone(timezone.utc)
    except (TypeError, ValueError, OverflowError):
        return None


def domain_allowed(host: str, allowed_domains: list[str]) -> bool:
    host = (host or "").lower().removeprefix("www.").rstrip(".")
    return bool(host) and any(
        host == domain.lower().removeprefix("www.") or
        host.endswith("." + domain.lower().removeprefix("www."))
        for domain in allowed_domains
    )


def fetch_feed_items(feed: dict, now: datetime, lookback_hours: int = 72) -> list[dict]:
    feed_domains = feed.get("feed_domains", feed["allowed_domains"])
    parsed_feed_url = urlparse(feed["url"])
    if parsed_feed_url.scheme != "https" or not domain_allowed(parsed_feed_url.hostname or "", feed_domains):
        raise ValueError("feed_url_not_allowlisted")
    request = urllib.request.Request(feed["url"], headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=20) as response:
        if response.status != 200:
            raise ValueError("feed_http_status")
        final_host = urlparse(response.geturl()).hostname or ""
        if not domain_allowed(final_host, feed_domains):
            raise ValueError("feed_redirect_not_allowlisted")
        body = response.read(2_000_000)
    root = ET.fromstring(body)
    cutoff = now.astimezone(timezone.utc) - timedelta(hours=lookback_hours)
    results = []
    for node in root.iter():
        if local_name(node.tag) not in {"item", "entry"}:
            continue
        title = child_text(node, {"title"})
        link = extract_link(node)
        published = child_text(node, {"pubdate", "published", "updated", "date"})
        published_at = parse_date(published)
        parsed_link = urlparse(link)
        domain = (parsed_link.hostname or "").lower().removeprefix("www.")
        if (
            not title
            or parsed_link.scheme != "https"
            or not domain_allowed(domain, feed["allowed_domains"])
            or not published_at
            or published_at < cutoff
            or published_at > now.astimezone(timezone.utc) + timedelta(minutes=5)
        ):
            continue
        results.append({
            "source_id": feed["id"],
            "source": feed["name"],
            "title": re.sub(r"\s+", " ", title).strip()[:300],
            "url": link,
            "domain": domain,
            "published_at": published_at.isoformat(),
        })
    return results


def tokens(value: str) -> set[str]:
    return {
        token.lower()
        for token in re.findall(r"[0-9A-Za-zÀ-ž_-]{3,}", value or "")
        if token.lower() not in STOP_WORDS
    }


def match_sources(query: str, items: list[dict], limit: int = 5) -> list[dict]:
    query_tokens = tokens(query)
    ranked = []
    for item in items:
        title_tokens = tokens(item.get("title", ""))
        score = len(query_tokens & title_tokens)
        if score:
            ranked.append((score, item))
    ranked.sort(key=lambda pair: (pair[0], pair[1]["published_at"]), reverse=True)
    return [
        {**item, "relevance_score": score}
        for score, item in ranked[:limit]
    ]


def build_digest(ideas: list[dict], feeds: list[dict] | None = None, now: datetime | None = None) -> dict:
    current = now or datetime.now(timezone.utc)
    if current.tzinfo is None:
        raise ValueError("now_must_be_timezone_aware")
    candidates = []
    feed_status = []
    for feed in (FEEDS if feeds is None else feeds):
        try:
            items = fetch_feed_items(feed, current, 72)
            candidates.extend(items)
            feed_status.append({"id": feed["id"], "status": "PASS", "fresh_items": len(items)})
        except (urllib.error.URLError, TimeoutError, ET.ParseError, OSError, ValueError) as exc:
            feed_status.append({"id": feed["id"], "status": "FAIL", "error": str(exc)[:120]})

    profiles = []
    for idea in ideas:
        query = str(idea.get("research_query", "")).strip()
        matches = match_sources(query, candidates)
        profiles.append({
            "profile_id": idea.get("profile_id"),
            "topic": idea.get("topic"),
            "research_query": query,
            "status": "sources_found" if matches else "no_recent_source_match",
            "sources": matches,
        })
    return {
        "generated_at": current.astimezone(timezone.utc).isoformat(),
        "lookback_hours": 72,
        "feed_summary": {
            "total": len(feed_status),
            "passed": sum(1 for feed in feed_status if feed["status"] == "PASS"),
            "failed": sum(1 for feed in feed_status if feed["status"] == "FAIL"),
            "fresh_candidates": len(candidates),
        },
        "feed_status": feed_status,
        "profiles": profiles,
        "notice": "RSS title/date/domain match is discovery evidence only; it does not verify factual claims. Open and independently verify every source before scripting or publishing.",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ideas", type=Path, required=True, help="JSON object with an items array")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        payload = json.loads(args.ideas.read_text(encoding="utf-8"))
        ideas = payload.get("items", [])
        if not isinstance(ideas, list) or not ideas:
            raise ValueError("ideas_items_required")
        result = build_digest(ideas)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(json.dumps({"status": "blocked", "error": str(exc)[:120]}, ensure_ascii=False))
        return 2
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result["feed_summary"], ensure_ascii=False))
    return 0 if result["feed_summary"]["passed"] > 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
