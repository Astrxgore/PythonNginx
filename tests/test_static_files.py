import asyncio
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from pynginx.config.models import ServerConfig
from pynginx.http.request import HTTPRequest
from pynginx.static.files import serve_static
from pynginx.static.open_file_cache import OpenFileCache


class StaticFilesTests(unittest.TestCase):
    def test_serves_file_through_open_file_cache(self) -> None:
        async def run() -> None:
            with TemporaryDirectory() as tmp:
                root = Path(tmp) / "public"
                root.mkdir()
                file_path = root / "hello.txt"
                file_path.write_text("hello", encoding="utf-8")
                server = ServerConfig("test", "127.0.0.1", 8080, ["localhost"], root)
                request = HTTPRequest("GET", "/hello.txt", "HTTP/1.1", {"host": "localhost"}, b"")
                cache = OpenFileCache(max_entries=4)

                response = await serve_static(request, server, None, cache)

                self.assertEqual(response.status, 200)
                self.assertEqual(response.body, b"hello")
                self.assertIsNotNone(cache.get(file_path))
                cache.close_all()

        asyncio.run(run())

    def test_blocks_path_traversal(self) -> None:
        async def run() -> None:
            with TemporaryDirectory() as tmp:
                root = Path(tmp) / "public"
                root.mkdir()
                (Path(tmp) / "secret.txt").write_text("secret", encoding="utf-8")
                server = ServerConfig("test", "127.0.0.1", 8080, ["localhost"], root)
                request = HTTPRequest("GET", "/../secret.txt", "HTTP/1.1", {"host": "localhost"}, b"")

                response = await serve_static(request, server, None)

                self.assertEqual(response.status, 403)

        asyncio.run(run())

    def test_autoindex_lists_directory_entries(self) -> None:
        async def run() -> None:
            with TemporaryDirectory() as tmp:
                root = Path(tmp) / "public"
                directory = root / "files"
                directory.mkdir(parents=True)
                (directory / "a.txt").write_text("hello", encoding="utf-8")
                server = ServerConfig("test", "127.0.0.1", 8080, ["localhost"], root, autoindex=True)
                request = HTTPRequest("GET", "/files/", "HTTP/1.1", {"host": "localhost"}, b"")

                response = await serve_static(request, server, None)

                self.assertEqual(response.status, 200)
                self.assertIn(b"a.txt", response.body)

        asyncio.run(run())
