#!/usr/bin/env python3

"""
Klasker Scanner v0.1.1

Path: ~/klasker-scanner/src/scanner.py

Initial website evidence extraction engine for Klasker.

v0.1.1 deliberately avoids:
- external AI APIs
- browser automation
- concurrency
- persistent queues

Database persistence is handled separately by database.py.

It produces one structured JSON evaluation for one website.

v0.1.1 adds:
- JSON-LD extraction
- JSON-LD type detection
- Product extraction
- Offer extraction
- Brand extraction
- Organisation extraction
- AggregateRating extraction
- 24-hour scan result reuse
"""

import json
import sys
import time
from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse

import urllib.request


USER_AGENT = "KlaskerScanner/0.1.1 (+https://www.klasker.com/)"

SCAN_CACHE_HOURS = 24


class HTMLMetadataParser(HTMLParser):
    def __init__(self):
        super().__init__()

        self.title = ""
        self.description = ""
        self.canonical = ""
        self.og = {}

        self.json_ld = []
        self._json_ld_active = False
        self._json_ld_parts = []

        self._inside_title = False
        self._title_parts = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)

        if tag == "title":
            self._inside_title = True
            self._title_parts = []

        elif tag == "meta":
            name = attrs.get("name", "").lower()
            property_name = attrs.get("property", "").lower()
            content = attrs.get("content", "")

            if name == "description":
                self.description = content

            if property_name.startswith("og:"):
                self.og[property_name] = content

        elif tag == "link":
            rel = attrs.get("rel", "").lower()

            if "canonical" in rel:
                self.canonical = attrs.get("href", "")

        elif tag == "script":
            script_type = attrs.get("type", "").lower()

            if script_type == "application/ld+json":
                self._json_ld_active = True
                self._json_ld_parts = []

    def handle_endtag(self, tag):
        if tag == "title":
            self._inside_title = False
            self.title = "".join(self._title_parts).strip()

        elif tag == "script" and self._json_ld_active:
            raw_json = "".join(self._json_ld_parts).strip()

            if raw_json:
                try:
                    parsed = json.loads(raw_json)

                    if isinstance(parsed, list):
                        self.json_ld.extend(parsed)

                    else:
                        self.json_ld.append(parsed)

                except json.JSONDecodeError:
                    # Invalid JSON-LD must not prevent the rest of
                    # the website from being scanned.
                    pass

            self._json_ld_active = False
            self._json_ld_parts = []

    def handle_data(self, data):
        if self._inside_title:
            self._title_parts.append(data)

        if self._json_ld_active:
            self._json_ld_parts.append(data)


def normalise_url(url):
    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    parsed = urlparse(url)

    if not parsed.netloc:
        raise ValueError("Invalid URL")

    return url


def fetch(url, timeout=15):
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml"
        }
    )

    start = time.monotonic()

    with urllib.request.urlopen(request, timeout=timeout) as response:
        body = response.read()
        elapsed = time.monotonic() - start

        headers = dict(response.headers.items())

        return {
            "url": response.geturl(),
            "status": response.status,
            "headers": headers,
            "body": body,
            "elapsed_ms": round(elapsed * 1000, 2),
        }


def fetch_optional(url, timeout=10):
    try:
        result = fetch(url, timeout)

        return {
            "available": True,
            "status": result["status"],
            "url": result["url"],
            "size": len(result["body"]),
        }

    except Exception as exc:
        return {
            "available": False,
            "error": str(exc),
        }


def json_ld_types(data):
    types = []

    if not isinstance(data, dict):
        return types

    value = data.get("@type")

    if isinstance(value, str):
        types.append(value)

    elif isinstance(value, list):
        types.extend(
            item for item in value
            if isinstance(item, str)
        )

    return types


def extract_json_ld(json_ld):
    products = []
    offers = []
    organisations = []
    brands = []
    ratings = []
    types = []

    def inspect(item):
        if not isinstance(item, dict):
            return

        item_types = json_ld_types(item)

        for item_type in item_types:
            if item_type not in types:
                types.append(item_type)

        normalised_types = {
            item_type.lower()
            for item_type in item_types
        }

        if "product" in normalised_types:
            products.append(item)

        if "offer" in normalised_types or "aggregateoffer" in normalised_types:
            offers.append(item)

        if (
            "organization" in normalised_types
            or "organisation" in normalised_types
            or "localbusiness" in normalised_types
        ):
            organisations.append(item)

        if "brand" in normalised_types:
            brands.append(item)

        if "aggregaterating" in normalised_types or "rating" in normalised_types:
            ratings.append(item)

        # JSON-LD can contain nested structured objects.
        for value in item.values():

            if isinstance(value, dict):
                inspect(value)

            elif isinstance(value, list):
                for nested in value:
                    if isinstance(nested, dict):
                        inspect(nested)

    for item in json_ld:
        inspect(item)

    return {
        "detected": bool(json_ld),
        "types": types,
        "products": products,
        "offers": offers,
        "organisations": organisations,
        "brands": brands,
        "ratings": ratings,
    }


def calculate_score(result):
    score = 0
    checks = []

    if result["http"]["status"] == 200:
        score += 10
        checks.append(("HTTP 200", True))

    headers = {
        key.lower(): value
        for key, value in result["http"]["headers"].items()
    }

    security_headers = [
        "strict-transport-security",
        "content-security-policy",
        "x-content-type-options",
        "referrer-policy",
        "permissions-policy",
    ]

    for header in security_headers:
        present = header in headers

        if present:
            score += 5

        checks.append((header, present))

    html = result["html"]

    if html["title"]:
        score += 10
        checks.append(("title", True))
    else:
        checks.append(("title", False))

    if html["description"]:
        score += 10
        checks.append(("description", True))
    else:
        checks.append(("description", False))

    if html["canonical"]:
        score += 5
        checks.append(("canonical", True))
    else:
        checks.append(("canonical", False))

    if html["open_graph"]:
        score += 10
        checks.append(("OpenGraph", True))
    else:
        checks.append(("OpenGraph", False))

    if html["json_ld"]["detected"]:
        score += 10
        checks.append(("JSON-LD", True))
    else:
        checks.append(("JSON-LD", False))

    if result["discovery"]["robots"]["available"]:
        score += 5

    if result["discovery"]["llms"]["available"]:
        score += 10

    if result["discovery"]["sitemap"]["available"]:
        score += 5

    return {
        "score": score,
        "maximum": 100,
        "checks": checks,
    }


def scan(url):
    url = normalise_url(url)

    homepage = fetch(url)

    html_body = homepage["body"]

    parser = HTMLMetadataParser()

    try:
        parser.feed(
            html_body.decode(
                "utf-8",
                errors="replace"
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


def main():
    if len(sys.argv) != 2:
        print(
            "Usage: scanner.py <URL>",
            file=sys.stderr
        )

        return 2

    try:
        url = normalise_url(sys.argv[1])

        from database import get_latest_scan_metadata, get_scan, save_scan

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
                                    2
                                ),
                                "max_age_hours": SCAN_CACHE_HOURS,
                            },
                        }

                        print(
                            json.dumps(
                                result,
                                indent=2,
                                ensure_ascii=False
                            )
                        )

                        return 0

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

        print(
            json.dumps(
                result,
                indent=2,
                ensure_ascii=False
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
                indent=2
            ),
            file=sys.stderr
        )

        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
