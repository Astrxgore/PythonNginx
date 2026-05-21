"""Minimal reverse proxy implementation placeholder."""

from __future__ import annotations

from urllib.parse import urlparse

from pynginx.http.request import HTTPRequest
from pynginx.http.response import HTTPResponse, text_response


async def proxy_request(request: HTTPRequest, upstream_url: str) -> HTTPResponse:
    parsed = urlparse(upstream_url)
    if parsed.scheme != "http" or not parsed.hostname:
        return text_response(502, "Bad Gateway")

    # TODO: implement with asyncio.open_connection(parsed.hostname, parsed.port or 80).
    # Keep this module isolated so static serving can be completed independently.
    return HTTPResponse(
        502,
        {"Content-Type": "text/plain; charset=utf-8"},
        f"proxy_pass is planned for {upstream_url}\n".encode("utf-8"),
    )
