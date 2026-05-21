from pathlib import Path

from pynginx.config.models import LocationConfig, ServerConfig
from pynginx.server.router import Router


def test_match_location_prefers_longest_prefix() -> None:
    server = ServerConfig(
        name="test",
        listen_host="127.0.0.1",
        listen_port=8080,
        server_names=["localhost"],
        root=Path("public"),
        locations=[LocationConfig("/"), LocationConfig("/api/")],
    )

    assert Router.match_location(server, "/api/users").prefix == "/api/"
