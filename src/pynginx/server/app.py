"""Async server bootstrap."""

from __future__ import annotations

import asyncio
import ssl
from collections import defaultdict

from pynginx.config.models import AppConfig, ServerConfig
from pynginx.logging import AccessLogger
from pynginx.server.connection import handle_connection
from pynginx.server.router import Router
from pynginx.static.open_file_cache import OpenFileCache


class ServerApp:
    def __init__(self, config: AppConfig) -> None:
        self.config = config
        self.open_file_cache = OpenFileCache(config.open_file_cache_max, config.open_file_cache_inactive)
        self.router = Router(config, self.open_file_cache)
        self.access_logger = AccessLogger(config.servers)

    async def serve_forever(self) -> None:
        by_listen: dict[tuple[str, int], list[ServerConfig]] = defaultdict(list)
        for server in self.config.servers:
            by_listen[(server.listen_host, server.listen_port)].append(server)

        servers = []
        for (host, port), virtual_servers in by_listen.items():
            ssl_context = _build_ssl_context(virtual_servers)
            server = await asyncio.start_server(
                lambda reader, writer: handle_connection(
                    reader,
                    writer,
                    self.config,
                    self.router,
                    self.access_logger,
                ),
                host,
                port,
                ssl=ssl_context,
            )
            servers.append(server)
            scheme = "https" if ssl_context else "http"
            print(f"listening on {scheme}://{host}:{port}")

        try:
            async with asyncio.TaskGroup() as group:
                for server in servers:
                    group.create_task(server.serve_forever())
        finally:
            self.open_file_cache.close_all()


def _build_ssl_context(virtual_servers: list[ServerConfig]) -> ssl.SSLContext | None:
    ssl_servers = [server for server in virtual_servers if server.ssl_enabled]
    if not ssl_servers:
        return None
    if len(ssl_servers) != len(virtual_servers):
        raise ValueError("all virtual servers on the same listen address must use the same ssl mode")

    server = ssl_servers[0]
    if not server.ssl_certfile or not server.ssl_keyfile:
        raise ValueError(f"server {server.name!r} has ssl enabled but no ssl_certfile/ssl_keyfile")

    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain(server.ssl_certfile, server.ssl_keyfile)
    return context
