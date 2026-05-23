"""Minimal reverse proxy implementation."""

from __future__ import annotations

import asyncio
from urllib.parse import urlparse

from pynginx.http.request import HTTPRequest
from pynginx.http.response import HTTPResponse, text_response


HOP_BY_HOP_HEADERS = {
    "connection",
    "keep-alive",
    "proxy-authenticate",
    "proxy-authorization",
    "te",
    "trailer",
    "transfer-encoding",
    "upgrade",
}


async def proxy_request(
    request: HTTPRequest,
    upstream_url: str,
    client_ip: str = "",
    timeout: float = 10.0,
) -> HTTPResponse:
    parsed = urlparse(upstream_url)
    if parsed.scheme != "http" or not parsed.hostname:
        return text_response(502, "Bad Gateway")

    port = parsed.port or 80
    try:
        reader, writer = await asyncio.wait_for(asyncio.open_connection(parsed.hostname, port), timeout)
        try:
            writer.write(_build_upstream_request(request, parsed.netloc, client_ip))
            await asyncio.wait_for(writer.drain(), timeout)
            return await asyncio.wait_for(_read_upstream_response(reader), timeout)
        finally:
            writer.close()
            try:
                await writer.wait_closed()
            except OSError:
                pass
    except (OSError, asyncio.TimeoutError, ValueError):
        return text_response(502, "Bad Gateway")


def _build_upstream_request(request: HTTPRequest, host_header: str, client_ip: str) -> bytes:
    headers = {
        name: value
        for name, value in request.headers.items()
        if name not in HOP_BY_HOP_HEADERS and name != "host"
    }
    headers["host"] = host_header
    headers["connection"] = "close"
    if request.body:
        headers["content-length"] = str(len(request.body))
    else:
        headers.pop("content-length", None)
    if client_ip:
        previous = headers.get("x-forwarded-for")
        headers["x-forwarded-for"] = f"{previous}, {client_ip}" if previous else client_ip

    lines = [f"{request.method} {request.path_with_query} HTTP/1.1"]
    lines.extend(f"{name}: {value}" for name, value in headers.items())
    head = ("\r\n".join(lines) + "\r\n\r\n").encode("latin-1")
    return head + request.body


async def _read_upstream_response(reader: asyncio.StreamReader) -> HTTPResponse:
    raw_head = await reader.readuntil(b"\r\n\r\n")
    head = raw_head.removesuffix(b"\r\n\r\n")
    lines = head.split(b"\r\n")
    status_line = lines[0].decode("latin-1")
    try:
        _version, status, _reason = status_line.split(" ", 2)
    except ValueError:
        _version, status = status_line.split(" ", 1)

    headers: dict[str, str] = {}
    for raw_line in lines[1:]:
        if not raw_line:
            continue
        name, value = raw_line.decode("latin-1").split(":", 1)
        lower_name = name.strip().lower()
        if lower_name in HOP_BY_HOP_HEADERS or lower_name in {"content-length"}:
            continue
        headers[name.strip()] = value.strip()

    if any(line.lower().startswith(b"transfer-encoding:") for line in lines[1:]):
        return text_response(502, "Bad Gateway")

    content_length = 0
    for raw_line in lines[1:]:
        if raw_line.lower().startswith(b"content-length:"):
            content_length = int(raw_line.split(b":", 1)[1].strip())
            break

    body = await reader.readexactly(content_length) if content_length else await reader.read()
    return HTTPResponse(int(status), headers, body)
