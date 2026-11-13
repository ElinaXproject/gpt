#!/usr/bin/env python3
"""Read-only smoke test for AUTORED IDEA's curated RSS source list."""
from __future__ import annotations

import email.utils
import json
import sys
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
FEEDS = json.loads((ROOT / "config/research_feeds.json").read_text(encoding="utf-8"))


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


def parse_date(value: str):
    if not value:
        return None
    try:
        return email.utils.parsedate_to_datetime(value).astimezone(timezone.utc)
    except (TypeError, ValueError, OverflowError):
        pass
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
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


def inspect_feed(feed: dict) -> dict:
    configured_host = urlparse(feed["url"]).hostname or ""
    if urlparse(feed["url"]).scheme != "https" or not domain_allowed(configured_host, feed["allowed_domains"]):
        return {
            "id": feed["id"],
            "name": feed["name"],
            "status": "FAIL",
            "error": "feed_url_not_https_or_host_not_allowlisted",
        }
    request = urllib.request.Request(
        feed["url"],
        headers={"User-Agent": "AUTORED-IDEA-RSS-Audit/1.0 (+https://github.com/ElinaXproject/gpt)"},
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            status = response.status
            final_host = urlparse(response.geturl()).hostname or ""
            if not domain_allowed(final_host, feed["allowed_domains"]):
                return {
                    "id": feed["id"],
                    "name": feed["name"],
                    "status": "FAIL",
                    "error": "redirected_to_non_allowlisted_host",
                }
            body = response.read(2_000_000)
        root = ET.fromstring(body)
        items = []
        for node in root.iter():
            if local_name(node.tag) not in {"item", "entry"}:
                continue
            title = child_text(node, {"title"})
            link = child_text(node, {"link", "id"})
            published = child_text(node, {"pubdate", "published", "updated", "date"})
            domain = urlparse(link).hostname or ""
            domain = domain.lower().removeprefix("www.")
            allowed = domain_allowed(domain, feed["allowed_domains"])
            items.append({
                "title_present": bool(title),
                "link_present": bool(link),
                "published_at": parse_date(published).isoformat() if parse_date(published) else None,
                "domain": domain,
                "domain_allowed": allowed,
            })
        valid = [item for item in items if item["title_present"] and item["link_present"] and item["domain_allowed"]]
        newest = max((item["published_at"] for item in valid if item["published_at"]), default=None)
        return {
            "id": feed["id"],
            "name": feed["name"],
            "http_status": status,
            "item_count": len(items),
            "valid_item_count": len(valid),
            "newest_published_at": newest,
            "status": "PASS" if status == 200 and valid else "FAIL",
        }
    except (urllib.error.URLError, TimeoutError, ET.ParseError, OSError) as exc:
        return {
            "id": feed["id"],
            "name": feed["name"],
            "status": "FAIL",
            "error": type(exc).__name__ + ": " + str(exc)[:180],
        }


def main() -> int:
    results = [inspect_feed(feed) for feed in FEEDS]
    print(json.dumps(results, ensure_ascii=False, indent=2))
    failures = [item for item in results if item["status"] != "PASS"]
    print(f"\nRSS sources: {len(results)}; PASS: {len(results)-len(failures)}; FAIL: {len(failures)}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
