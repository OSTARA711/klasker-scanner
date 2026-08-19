# ~/domains/scanner1.klasker.com/public_python/app.py

import json
import sys

sys.path.insert(0, "/usr/home/SVELTRON/klasker-scanner/src")

from scanner import scan_with_cache


def response(start_response, status, body, content_type="application/json"):
    data = json.dumps(body).encode("utf-8")

    start_response(
        status,
        [
            ("Content-Type", content_type),
            ("Content-Length", str(len(data))),
            ("Cache-Control", "no-store"),
        ],
    )

    return [data]


def application(environ, start_response):
    path = environ.get("PATH_INFO", "/")
    method = environ.get("REQUEST_METHOD", "GET")

    if path == "/health" and method == "GET":
        return response(
            start_response,
            "200 OK",
            {
                "status": "ok",
                "service": "klasker-scanner",
                "server": "s12",
            },
        )

    if path == "/scan" and method == "POST":
        try:
            length = int(environ.get("CONTENT_LENGTH", "0"))
        except ValueError:
            length = 0

        try:
            raw_body = environ["wsgi.input"].read(length)
            request = json.loads(raw_body.decode("utf-8"))

            url = request.get("url")

            if not isinstance(url, str) or not url.strip():
                return response(
                    start_response,
                    "400 Bad Request",
                    {"error": "url is required"},
                )

            result = scan_with_cache(url.strip())

            return response(
                start_response,
                "200 OK",
                result,
            )

        except Exception as exc:
            return response(
                start_response,
                "500 Internal Server Error",
                {
                    "error": str(exc),
                },
            )

    return response(
        start_response,
        "404 Not Found",
        {
            "error": "Not found",
        },
    )
