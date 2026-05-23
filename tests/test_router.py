from pathlib import Path
import unittest

from pynginx.config.models import LocationConfig, ServerConfig
from pynginx.config.models import AppConfig
from pynginx.http.request import HTTPRequest
from pynginx.server.router import Router
from pynginx.static.open_file_cache import OpenFileCache


class RouterTests(unittest.TestCase):
    def test_match_location_prefers_longest_prefix(self) -> None:
        server = ServerConfig(
            name="test",
            listen_host="127.0.0.1",
            listen_port=8080,
            server_names=["localhost"],
            root=Path("public"),
            locations=[LocationConfig("/"), LocationConfig("/api/")],
        )

        match = Router.match_location(server, "/api/users")

        self.assertIsNotNone(match)
        self.assertEqual(match.prefix, "/api/")

    def test_resolve_selects_virtual_server_by_host(self) -> None:
        first = ServerConfig("first", "127.0.0.1", 8080, ["first.local"], Path("public"))
        second = ServerConfig("second", "127.0.0.1", 8080, ["second.local"], Path("public2"))
        router = Router(AppConfig([first, second]), OpenFileCache())
        request = HTTPRequest("GET", "/", "HTTP/1.1", {"host": "second.local:8080"}, b"")

        match = router.resolve(request)

        self.assertEqual(match.server.name, "second")
