#!/usr/bin/env python3

"""
Klasker Scanner v0.1.1

Path: ~/klasker-scanner/src/scanner.py

Main scanner orchestration and command-line interface.

The scanner is deliberately modular:

- fetcher.py   -> HTTP fetching
- parser.py    -> HTML and JSON-LD parsing
- analyser.py  -> scoring
- database.py  -> TiDB persistence and cache

It produces one structured JSON evaluation for one website.
"""

import json
import sys
import time
from urllib.parse import urlparse, urljoin

from analyser import calculate_score
from database import get_latest_scan_metadata, get_scan, save_scan
from fetcher import fetch, fetch_optional
from parser import HTMLMetadataParser, extract_json_ld


SCAN_CACHE_HOURS = 24


def normalise_url(url):
    """Normalise and validate a website URL."""

    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    parsed = urlparse(url)

    if not parsed.netloc:
        raise ValueError("Invalid URL")

    return url


def scan(url):
    """Scan one website and return structured evidence."""

    url = normalise_url(url)

    homepage = fetch(url)

    html_body = homepage["body"]

    parser = HTMLMetadataParser()

    try:
        parser.feed(
            html_body.decode(
                "utf-8",
                errors="replace",
            )
        )

    except Exception:
        pass

    json_ld = extract_json_ld(parser.json_ld)

    base_url = homepage["url"].rstrip("/") + "/"

    robots_url = urljoin(base_url, "robots.txt")
    llms_url = urljoin(base_url, "llms.txt")
    sitemap_url = urljoin(base_url, "sitemap.xml")

    result = {
        "scanner": {
            "name": "Klasker Scanner",
            "version": "0.1.1",
        },

        "target": {
            "requested_url": url,
            "final_url": homepage["url"],
            "domain": urlparse(homepage["url"]).netloc,
        },

        "http": {
            "status": homepage["status"],
            "elapsed_ms": homepage["elapsed_ms"],
            "size_bytes": len(html_body),
            "headers": homepage["headers"],
        },

        "html": {
            "title": parser.title,
            "description": parser.description,
            "canonical": parser.canonical,
            "open_graph": parser.og,
            "json_ld": json_ld,
        },

        "discovery": {
            "robots": fetch_optional(robots_url),
            "llms": fetch_optional(llms_url),
            "sitemap": fetch_optional(sitemap_url),
        },
    }

    result["score"] = calculate_score(result)

    return result


def scan_with_cache(url):
    """Return a cached result when available, otherwise scan and save."""

    url = normalise_url(url)

    domain = urlparse(url).netloc

    previous_scan = get_latest_scan_metadata(domain)

    if previous_scan is not None:
        scanned_at = previous_scan["scanned_at"]

        if hasattr(scanned_at, "timestamp"):
            scan_age_seconds = time.time() - scanned_at.timestamp()

            cache_limit_seconds = SCAN_CACHE_HOURS * 60 * 60

            if scan_age_seconds < cache_limit_seconds:
                result = get_scan(previous_scan["id"])

                if result is not None:
                    result["database"] = {
                        "saved": False,
                        "scan_id": previous_scan["id"],
                        "cache": {
                            "used": True,
                            "age_seconds": round(
                                scan_age_seconds,
                                2,
                            ),
                            "max_age_hours": SCAN_CACHE_HOURS,
                        },
                    }

                    return result

    result = scan(url)

    scan_id = save_scan(result)

    result["database"] = {
        "saved": True,
        "scan_id": scan_id,
        "cache": {
            "used": False,
            "max_age_hours": SCAN_CACHE_HOURS,
        },
    }

    return result


def main():
    """Run the command-line scanner."""

    if len(sys.argv) != 2:
        print(
            "Usage: scanner.py <URL>",
            file=sys.stderr,
        )

        return 2

    try:
        result = scan_with_cache(sys.argv[1])

        print(
            json.dumps(
                result,
                indent=2,
                ensure_ascii=False,
            )
        )

    except Exception as exc:
        error = {
            "scanner": {
                "name": "Klasker Scanner",
                "version": "0.1.1",
            },
            "error": str(exc),
        }

        print(
            json.dumps(
                error,
                indent=2,
            ),
            file=sys.stderr,
        )

        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
