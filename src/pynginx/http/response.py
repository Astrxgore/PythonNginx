"""HTTP response model and serialization helpers."""

from __future__ import annotations

from dataclasses import dataclass, field
from email.utils import formatdate


REASONS = {
    200: "OK",
    301: "Moved Permanently",
    304: "Not Modified",
    400: "Bad Request",
    403: "Forbidden",
    404: "Not Found",
    405: "Method Not Allowed",
    431: "Request Header Fields Too Large",
    500: "Internal Server Error",
    502: "Bad Gateway",
}


@dataclass(slots=True)
class HTTPResponse:
    status: int
    headers: dict[str, str] = field(default_factory=dict)
    body: bytes = b""

    def to_bytes(self, include_body: bool = True) -> bytes:
        reason = REASONS.get(self.status, "Unknown")
        headers = {
            "Date": formatdate(usegmt=True),
            "Server": "pynginx/0.1",
            "Content-Length": str(len(self.body)),
            **self.headers,
        }
        head = [f"HTTP/1.1 {self.status} {reason}", *(f"{k}: {v}" for k, v in headers.items()), "", ""]
        payload = "\r\n".join(head).encode("latin-1")
        if include_body:
            payload += self.body
        return payload


def text_response(status: int, text: str, *, close: bool = False) -> HTTPResponse:
    headers = {"Content-Type": "text/plain; charset=utf-8"}
    if close:
        headers["Connection"] = "close"
    return HTTPResponse(status=status, headers=headers, body=text.encode("utf-8"))
