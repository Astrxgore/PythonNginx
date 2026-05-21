"""Manual HTTP/1.x request parser."""

from __future__ import annotations

import asyncio

from pynginx.http.request import HTTPRequest


class HTTPParseError(Exception):
    status_code = 400
    reason = "Bad Request"


class HeaderTooLargeError(HTTPParseError):
    status_code = 431
    reason = "Request Header Fields Too Large"


async def read_request(reader: asyncio.StreamReader, header_limit: int) -> HTTPRequest | None:
    """Read and parse one request head.

    Returns None when the client closed the connection before sending data.
    """
    try:
        raw_head = await reader.readuntil(b"\r\n\r\n")
    except asyncio.IncompleteReadError as exc:
        if not exc.partial:
            return None
        raise HTTPParseError("connection closed during request head") from exc
    except asyncio.LimitOverrunError as exc:
        raise HeaderTooLargeError() from exc

    if len(raw_head) > header_limit:
        raise HeaderTooLargeError()

    head = raw_head.removesuffix(b"\r\n\r\n")
    lines = head.split(b"\r\n")
    try:
        request_line = lines[0].decode("ascii")
        method, target, version = request_line.split(" ")
    except ValueError as exc:
        raise HTTPParseError("invalid request line") from exc
    except UnicodeDecodeError as exc:
        raise HTTPParseError("non-ascii request line") from exc

    if version not in {"HTTP/1.0", "HTTP/1.1"}:
        raise HTTPParseError("unsupported HTTP version")

    headers: dict[str, str] = {}
    for raw_line in lines[1:]:
        if not raw_line:
            continue
        try:
            name, value = raw_line.decode("latin-1").split(":", 1)
        except ValueError as exc:
            raise HTTPParseError("invalid header") from exc
        headers[name.strip().lower()] = value.strip()

    if version == "HTTP/1.1" and "host" not in headers:
        raise HTTPParseError("HTTP/1.1 request without Host")

    return HTTPRequest(method=method, target=target, version=version, headers=headers, raw_head=head)
