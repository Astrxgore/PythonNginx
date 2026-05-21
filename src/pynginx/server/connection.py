"""Per-connection keep-alive loop."""

from __future__ import annotations

import asyncio

from pynginx.config.models import AppConfig
from pynginx.http.parser import HTTPParseError, read_request
from pynginx.http.response import text_response
from pynginx.server.router import Router


async def handle_connection(
    reader: asyncio.StreamReader,
    writer: asyncio.StreamWriter,
    config: AppConfig,
    router: Router,
) -> None:
    requests_count = 0
    try:
        while requests_count < config.keepalive_max_requests:
            try:
                request = await asyncio.wait_for(read_request(reader, config.header_limit), config.keepalive_timeout)
            except asyncio.TimeoutError:
                break
            except HTTPParseError as exc:
                response = text_response(exc.status_code, exc.reason, close=True)
                writer.write(response.to_bytes())
                await writer.drain()
                break

            if request is None:
                break

            requests_count += 1
            response = await router.dispatch(request)
            close = request.wants_close or requests_count >= config.keepalive_max_requests
            if close:
                response.headers["Connection"] = "close"

            writer.write(response.to_bytes(include_body=request.method != "HEAD"))
            await writer.drain()
            if close:
                break
    finally:
        writer.close()
        await writer.wait_closed()
