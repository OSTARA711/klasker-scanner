"""HTTP fetching utilities for Klasker Scanner."""

import time
import urllib.request


USER_AGENT = "KlaskerScanner/0.1.1 (+https://www.klasker.com/)"


def fetch(url, timeout=15):
    """Fetch a URL and return the HTTP response details."""

    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml",
        },
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
    """Fetch an optional resource without failing the scan."""

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
