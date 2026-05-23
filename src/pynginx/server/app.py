"""Async server bootstrap."""

from __future__ import annotations

import asyncio
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
        for (host, port), _virtual_servers in by_listen.items():
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
            )
            servers.append(server)
            print(f"listening on http://{host}:{port}")

        try:
            async with asyncio.TaskGroup() as group:
                for server in servers:
                    group.create_task(server.serve_forever())
        finally:
            self.open_file_cache.close_all()
