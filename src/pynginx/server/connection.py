"""Per-connection keep-alive loop."""

from __future__ import annotations

import asyncio
import time

from pynginx.config.models import AppConfig
from pynginx.http.parser import HTTPParseError, read_body, read_request
from pynginx.http.response import text_response
from pynginx.logging import AccessLogger
from pynginx.server.router import Router


async def handle_connection(
    reader: asyncio.StreamReader,
    writer: asyncio.StreamWriter,
    config: AppConfig,
    router: Router,
    access_logger: AccessLogger,
) -> None:
    requests_count = 0
    peername = writer.get_extra_info("peername")
    client_ip = peername[0] if peername else ""
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
            started_at = time.monotonic()
            match = router.resolve(request)
            try:
                request.body = await asyncio.wait_for(read_body(reader, request, config.body_limit), config.keepalive_timeout)
                response = await router.dispatch(request, match, client_ip)
            except HTTPParseError as exc:
                response = text_response(exc.status_code, exc.reason, close=True)

            close = request.wants_close or requests_count >= config.keepalive_max_requests
            if response.headers.get("Connection", "").lower() == "close":
                close = True
            if close:
                response.headers["Connection"] = "close"

            include_body = request.method != "HEAD"
            writer.write(response.to_bytes(include_body=include_body))
            await writer.drain()
            access_logger.log(
                match.server,
                client_ip,
                request,
                response.status,
                len(response.body) if include_body else 0,
                time.monotonic() - started_at,
            )
            if close:
                break
    finally:
        writer.close()
        try:
            await writer.wait_closed()
        except OSError:
            pass
