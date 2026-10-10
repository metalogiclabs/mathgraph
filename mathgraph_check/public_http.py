"""Dependency-free, loopback-only WSGI API for one qualified public record.

GET routes serve immutable evidence views. POST /v1/resolve is a read-only
query (no proof search, network access, model calls or external writes).
This is a local preview/service reference, NOT an internet deployment.
"""
from __future__ import annotations

import argparse
from io import BytesIO
import json
from pathlib import Path
from wsgiref.simple_server import make_server

from .public_receipts import (
    RECORD_ID, ReleaseBoundaryError, _release_integrity,
    openapi, render_badge, render_html, resolve,
)

MAX_QUERY_BYTES = 8 * 1024
_HEADERS = [
    ("X-Content-Type-Options", "nosniff"),
    ("Referrer-Policy", "no-referrer"),
    ("Content-Security-Policy",
     "default-src 'none'; img-src 'self' data:; style-src 'unsafe-inline'; "
     "font-src 'self'; connect-src 'self'; base-uri 'none'; frame-ancestors 'none'"),
    ("Access-Control-Allow-Origin", "*"),
]


def load_release(path: Path) -> dict:
    root = Path(path)
    with (root / "record.json").open(encoding="utf-8") as f:
        record = json.load(f)
    _release_integrity(record)
    with (root / "evidence.json").open(encoding="utf-8") as f:
        evidence = json.load(f)
    if evidence != record["evidence"]:
        raise ReleaseBoundaryError("PUBLIC_EVIDENCE_AND_RECORD_DIVERGED")
    if (root / "index.html").read_text(encoding="utf-8") != render_html(record):
        raise ReleaseBoundaryError("PUBLIC_HTML_NOT_DERIVED_FROM_QUALIFIED_RECORD")
    if (root / "badge.svg").read_text(encoding="utf-8") != render_badge(record):
        raise ReleaseBoundaryError("PUBLIC_BADGE_NOT_DERIVED_FROM_QUALIFIED_RECORD")
    if json.loads((root / "openapi.json").read_text(encoding="utf-8")) != openapi():
        raise ReleaseBoundaryError("PUBLIC_API_SPEC_NOT_QUALIFIED")
    return record


def app_for(release_dir: Path):
    record = load_release(Path(release_dir))
    raw_record = (json.dumps(record, sort_keys=True, ensure_ascii=False) + "\n").encode()
    raw_evidence = (json.dumps(record["evidence"], sort_keys=True) + "\n").encode()
    raw_schema = (json.dumps(openapi(), sort_keys=True) + "\n").encode()
    raw_html = render_html(record).encode("utf-8")
    raw_badge = render_badge(record).encode("utf-8")

    def respond(start, status: str, body: bytes, mime: str,
                cache: str = "public,max-age=3600", head: bool = False,
                extra: list[tuple[str, str]] | None = None):
        h = _HEADERS + [
            ("Content-Type", mime),
            ("Content-Length", str(len(body))),
            ("Cache-Control", cache),
        ] + (extra or [])
        start(status, h)
        return [b"" if head else body]

    def application(environ, start_response):
        method = environ.get("REQUEST_METHOD", "GET").upper()
        path = environ.get("PATH_INFO", "")
        head = method == "HEAD"
        if method == "OPTIONS":
            if path != "/v1/resolve":
                return respond(start_response, "404 Not Found", b"", "text/plain",
                               cache="no-store")
            return respond(
                start_response, "204 No Content", b"", "text/plain",
                cache="no-store", extra=[
                    ("Access-Control-Allow-Methods", "POST, OPTIONS"),
                    ("Access-Control-Allow-Headers", "Content-Type"),
                ],
            )
        if method in ("GET", "HEAD"):
            known = {
                "/": (raw_html, "text/html; charset=utf-8"),
                "/records/" + RECORD_ID: (raw_html, "text/html; charset=utf-8"),
                "/v1/records/" + RECORD_ID: (raw_record, "application/json; charset=utf-8"),
                "/v1/records/" + RECORD_ID + "/evidence":
                    (raw_evidence, "application/json; charset=utf-8"),
                "/v1/badges/" + RECORD_ID + ".svg": (raw_badge, "image/svg+xml; charset=utf-8"),
                "/v1/openapi.json": (raw_schema, "application/json; charset=utf-8"),
            }
            if path == "/health":
                body = b'{"status":"ok","read_only":true,"hosted_deployment":false}\n'
                return respond(start_response, "200 OK", body,
                               "application/json; charset=utf-8",
                               cache="no-store", head=head)
            if path in known:
                body, mime = known[path]
                return respond(start_response, "200 OK", body, mime,
                               cache="public,max-age=31536000,immutable", head=head)
            if path == "/v1/resolve":
                return respond(start_response, "405 Method Not Allowed", b"",
                               "text/plain", cache="no-store",
                               extra=[("Allow", "POST, OPTIONS")])
            return respond(start_response, "404 Not Found",
                           b'{"status":"NOT_FOUND"}\n',
                           "application/json; charset=utf-8", cache="no-store", head=head)

        if method == "POST" and path == "/v1/resolve":
            if environ.get("CONTENT_TYPE", "").split(";")[0].strip() != "application/json":
                return respond(start_response, "415 Unsupported Media Type",
                               b'{"status":"BAD_REQUEST","reason":"JSON_CONTENT_TYPE_REQUIRED"}\n',
                               "application/json", cache="no-store")
            raw_length = environ.get("CONTENT_LENGTH", "")
            try:
                length = int(raw_length)
            except (ValueError, TypeError):
                length = -1
            if not (0 < length <= MAX_QUERY_BYTES):
                return respond(start_response, "413 Content Too Large",
                               b'{"status":"BAD_REQUEST","reason":"QUERY_SIZE_LIMIT"}\n',
                               "application/json", cache="no-store")
            stream = environ.get("wsgi.input")
            if stream is None:
                return respond(start_response, "400 Bad Request",
                               b'{"status":"BAD_REQUEST"}\n',
                               "application/json", cache="no-store")
            try:
                payload = json.loads(stream.read(length))
            except (UnicodeError, ValueError):
                payload = None
            result = resolve(record, payload)
            body = (json.dumps(result, sort_keys=True, ensure_ascii=False) + "\n").encode()
            return respond(start_response,
                           "400 Bad Request" if result["status"] == "BAD_REQUEST" else "200 OK",
                           body, "application/json; charset=utf-8", cache="no-store")

        return respond(start_response, "405 Method Not Allowed",
                       b'{"status":"BAD_REQUEST","reason":"READ_ONLY_API"}\n',
                       "application/json", cache="no-store",
                       extra=[("Allow", "GET, HEAD, POST, OPTIONS")])

    return application


def cli() -> None:
    p = argparse.ArgumentParser(description="Preview a frozen MathGraph Check record locally")
    p.add_argument("--release-dir", type=Path, required=True)
    p.add_argument("--host", choices=("127.0.0.1", "localhost"), default="127.0.0.1")
    p.add_argument("--port", type=int, default=8796)
    args = p.parse_args()
    app = app_for(args.release_dir)
    with make_server(args.host, args.port, app) as server:
        print("MathGraph Check evidence preview: http://%s:%s" %
              (args.host, server.server_port), flush=True)
        server.serve_forever()


if __name__ == "__main__":
    cli()
