"""Static file serving helpers."""

from __future__ import annotations

import asyncio
import mimetypes
from email.utils import formatdate
from pathlib import Path
from urllib.parse import unquote, urlsplit

from pynginx.config.models import LocationConfig, ServerConfig
from pynginx.http.request import HTTPRequest
from pynginx.http.response import HTTPResponse, text_response
from pynginx.static.autoindex import render_autoindex
from pynginx.static.open_file_cache import OpenFileCache


async def serve_static(
    request: HTTPRequest,
    server: ServerConfig,
    location: LocationConfig | None,
    cache: OpenFileCache | None = None,
) -> HTTPResponse:
    root = (location.root if location and location.root else server.root).resolve()
    autoindex = location.autoindex if location and location.autoindex is not None else server.autoindex

    url_path = unquote(urlsplit(request.target).path)
    relative = url_path.lstrip("/")
    candidate = (root / relative).resolve()
    if root != candidate and root not in candidate.parents:
        return text_response(403, "Forbidden")

    if candidate.is_dir():
        if not url_path.endswith("/"):
            return HTTPResponse(301, {"Location": url_path + "/"}, b"")
        index = candidate / "index.html"
        if index.exists():
            candidate = index
        elif autoindex:
            body = render_autoindex(url_path, candidate).encode("utf-8")
            return HTTPResponse(200, {"Content-Type": "text/html; charset=utf-8"}, body)
        else:
            return text_response(403, "Forbidden")

    if not candidate.exists() or not candidate.is_file():
        return text_response(404, "Not Found")

    if cache is not None:
        entry = cache.open_file(candidate)
        data = await asyncio.to_thread(cache.read, entry)
        modified_at = entry.mtime_ns / 1_000_000_000
    else:
        data = await asyncio.to_thread(candidate.read_bytes)
        stat = candidate.stat()
        modified_at = stat.st_mtime

    content_type = mimetypes.guess_type(candidate.name)[0] or "application/octet-stream"
    return HTTPResponse(
        200,
        {
            "Content-Type": content_type,
            "Last-Modified": formatdate(modified_at, usegmt=True),
        },
        data,
    )
