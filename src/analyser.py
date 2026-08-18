"""Analysis and scoring for Klasker Scanner."""


SECURITY_HEADERS = [
    "strict-transport-security",
    "content-security-policy",
    "x-content-type-options",
    "referrer-policy",
    "permissions-policy",
]


def calculate_score(result):
    """Calculate the Klasker score from collected website evidence."""

    score = 0
    checks = []

    if result["http"]["status"] == 200:
        score += 10
        checks.append(("HTTP 200", True))

    headers = {
        key.lower(): value
        for key, value in result["http"]["headers"].items()
    }

    for header in SECURITY_HEADERS:
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
