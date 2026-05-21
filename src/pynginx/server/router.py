"""Virtual host and location routing."""

from __future__ import annotations

from pynginx.config.models import LocationConfig, ServerConfig
from pynginx.http.request import HTTPRequest
from pynginx.http.response import HTTPResponse, text_response


class Router:
    def __init__(self, servers: list[ServerConfig]) -> None:
        self.servers = servers
        self.default_server = servers[0]
        self.by_host = {
            server_name.lower(): server
            for server in servers
            for server_name in server.server_names
        }

    async def dispatch(self, request: HTTPRequest) -> HTTPResponse:
        if request.method not in {"GET", "HEAD"}:
            return text_response(405, "Method Not Allowed")

        server = self.by_host.get(request.host, self.default_server)
        location = self.match_location(server, request.target)

        if location and location.proxy_pass:
            from pynginx.proxy.upstream import proxy_request

            return await proxy_request(request, location.proxy_pass)

        from pynginx.static.files import serve_static

        return await serve_static(request, server, location)

    @staticmethod
    def match_location(server: ServerConfig, target: str) -> LocationConfig | None:
        path = target.split("?", 1)[0]
        matches = [location for location in server.locations if path.startswith(location.prefix)]
        if not matches:
            return None
        return max(matches, key=lambda item: len(item.prefix))
