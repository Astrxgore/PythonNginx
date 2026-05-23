import asyncio
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from pynginx.config.models import AppConfig, ServerConfig
from pynginx.logging import AccessLogger
from pynginx.server.connection import handle_connection
from pynginx.server.router import Router
from pynginx.static.open_file_cache import OpenFileCache


class ConnectionIntegrationTests(unittest.IsolatedAsyncioTestCase):
    async def test_keep_alive_static_and_access_log(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp) / "public"
            root.mkdir()
            (root / "index.html").write_text("ok", encoding="utf-8")
            access_log = Path(tmp) / "logs" / "access.log"
            server_config = ServerConfig(
                name="test",
                listen_host="127.0.0.1",
                listen_port=0,
                server_names=["localhost"],
                root=root,
                access_log=access_log,
            )
            config = AppConfig([server_config], keepalive_timeout=1.0)
            cache = OpenFileCache()
            router = Router(config, cache)
            access_logger = AccessLogger(config.servers)

            async def handler(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
                await handle_connection(reader, writer, config, router, access_logger)

            server = await asyncio.start_server(handler, "127.0.0.1", 0)
            port = server.sockets[0].getsockname()[1]
            try:
                reader, writer = await asyncio.open_connection("127.0.0.1", port)
                writer.write(
                    b"GET / HTTP/1.1\r\nHost: localhost\r\n\r\n"
                    b"GET / HTTP/1.1\r\nHost: localhost\r\nConnection: close\r\n\r\n"
                )
                await writer.drain()
                data = await reader.read()
                writer.close()
                await writer.wait_closed()

                self.assertEqual(data.count(b"HTTP/1.1 200 OK"), 2)
                self.assertIn(b"Connection: close", data)
                self.assertIn('"GET / HTTP/1.1" 200', access_log.read_text(encoding="utf-8"))
            finally:
                server.close()
                await server.wait_closed()
                cache.close_all()
