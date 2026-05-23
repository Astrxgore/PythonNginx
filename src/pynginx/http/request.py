"""HTTP request model."""

from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlsplit


@dataclass(slots=True)
class HTTPRequest:
    method: str
    target: str
    version: str
    headers: dict[str, str]
    raw_head: bytes
    content_length: int = 0
    body: bytes = b""

    @property
    def host(self) -> str:
        value = self.headers.get("host", "")
        return value.split(":", 1)[0].lower()

    @property
    def wants_close(self) -> bool:
        connection = self.headers.get("connection", "").lower()
        if self.version == "HTTP/1.0":
            return connection != "keep-alive"
        return connection == "close"

    @property
    def path_with_query(self) -> str:
        parsed = urlsplit(self.target)
        path = parsed.path or "/"
        if parsed.query:
            return f"{path}?{parsed.query}"
        return path
