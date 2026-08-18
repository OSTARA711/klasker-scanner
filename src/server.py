#!/usr/bin/env python3

"""
Klasker Scanner HTTP server.

Provides a minimal authenticated HTTP interface to the scanner.

POST /scan
Authorization: Bearer <secret>

Body:
{
  "url": "https://example.com"
}
"""

import json
import os
from http.server import BaseHTTPRequestHandler, HTTPServer

from dotenv import load_dotenv

from scanner import scan_with_cache


load_dotenv()

HOST = "127.0.0.1"
PORT = int(os.environ.get("KLASKER_SCANNER_PORT", "8080"))
API_SECRET = os.environ.get("KLASKER_SCANNER_SECRET")


class ScannerHandler(BaseHTTPRequestHandler):
    """Handle scanner HTTP requests."""

    def send_json(self, status, data):
        body = json.dumps(
            data,
            ensure_ascii=False,
        ).encode("utf-8")

        self.send_response(status)
        self.send_header(
            "Content-Type",
            "application/json",
        )
        self.send_header(
            "Content-Length",
            str(len(body)),
        )
        self.end_headers()

        self.wfile.write(body)

    def do_POST(self):
        if self.path != "/scan":
            self.send_json(
                404,
                {"error": "Not found"},
            )
            return

        if not API_SECRET:
            self.send_json(
                500,
                {"error": "Scanner secret is not configured"},
            )
            return

        authorization = self.headers.get(
            "Authorization",
            "",
        )

        if authorization != f"Bearer {API_SECRET}":
            self.send_json(
                401,
                {"error": "Unauthorized"},
            )
            return

        content_length = self.headers.get("Content-Length")

        if not content_length:
            self.send_json(
                400,
                {"error": "Request body is required"},
            )
            return

        try:
            length = int(content_length)
            body = self.rfile.read(length)
            payload = json.loads(body)

        except (ValueError, json.JSONDecodeError):
            self.send_json(
                400,
                {"error": "Invalid JSON"},
            )
            return

        url = payload.get("url")

        if not isinstance(url, str) or not url.strip():
            self.send_json(
                400,
                {"error": "A URL is required"},
            )
            return

        try:
            result = scan_with_cache(url.strip())

            self.send_json(
                200,
                result,
            )

        except Exception:
            self.send_json(
                500,
                {"error": "Scanner error"},
            )

    def do_GET(self):
        self.send_json(
            405,
            {"error": "Method not allowed"},
        )

    def log_message(self, format, *args):
        print(
            f"{self.address_string()} - {format % args}"
        )


def main():
    server = HTTPServer(
        (HOST, PORT),
        ScannerHandler,
    )

    print(
        f"Klasker Scanner HTTP server listening on "
        f"{HOST}:{PORT}"
    )

    try:
        server.serve_forever()

    except KeyboardInterrupt:
        print("\nStopping scanner server.")

    finally:
        server.server_close()


if __name__ == "__main__":
    main()
