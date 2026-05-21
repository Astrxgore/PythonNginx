"""HTTP request model."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class HTTPRequest:
    method: str
    target: str
    version: str
    headers: dict[str, str]
    raw_head: bytes

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
