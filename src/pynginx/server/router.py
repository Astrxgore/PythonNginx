"""Virtual host and location routing."""

from __future__ import annotations

from dataclasses import dataclass

from pynginx.config.models import AppConfig
from pynginx.config.models import LocationConfig, ServerConfig
from pynginx.http.request import HTTPRequest
from pynginx.http.response import HTTPResponse, text_response
from pynginx.static.open_file_cache import OpenFileCache


@dataclass(slots=True)
class RouteMatch:
    server: ServerConfig
    location: LocationConfig | None


class Router:
    def __init__(self, config: AppConfig, open_file_cache: OpenFileCache) -> None:
        servers = config.servers
        self.servers = servers
        self.default_server = servers[0]
        self.config = config
        self.open_file_cache = open_file_cache
        self.by_host = {
            server_name.lower(): server
            for server in servers
            for server_name in server.server_names
        }

    def resolve(self, request: HTTPRequest) -> RouteMatch:
        server = self.by_host.get(request.host, self.default_server)
        location = self.match_location(server, request.target)
        return RouteMatch(server=server, location=location)

    async def dispatch(self, request: HTTPRequest, match: RouteMatch, client_ip: str = "") -> HTTPResponse:
        server = match.server
        location = match.location
        if location and location.proxy_pass:
            from pynginx.proxy.upstream import proxy_request

            return await proxy_request(request, location.proxy_pass, client_ip, self.config.proxy_timeout)

        if request.method not in {"GET", "HEAD"}:
            return text_response(405, "Method Not Allowed")

        from pynginx.static.files import serve_static

        return await serve_static(request, server, location, self.open_file_cache)

    @staticmethod
    def match_location(server: ServerConfig, target: str) -> LocationConfig | None:
        path = target.split("?", 1)[0]
        matches = [location for location in server.locations if path.startswith(location.prefix)]
        if not matches:
            return None
        return max(matches, key=lambda item: len(item.prefix))
