import asyncio
import unittest

from pynginx.http.request import HTTPRequest
from pynginx.proxy.upstream import proxy_request


class ProxyTests(unittest.IsolatedAsyncioTestCase):
    async def test_proxy_pass_forwards_request_to_upstream(self) -> None:
        received: list[bytes] = []

        async def upstream_handler(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
            received.append(await reader.readuntil(b"\r\n\r\n"))
            writer.write(b"HTTP/1.1 200 OK\r\nContent-Length: 5\r\nContent-Type: text/plain\r\n\r\nproxy")
            await writer.drain()
            writer.close()
            await writer.wait_closed()

        server = await asyncio.start_server(upstream_handler, "127.0.0.1", 0)
        port = server.sockets[0].getsockname()[1]
        try:
            request = HTTPRequest("GET", "/api/users?limit=1", "HTTP/1.1", {"host": "localhost"}, b"")

            response = await proxy_request(request, f"http://127.0.0.1:{port}", "10.0.0.1", 2.0)

            self.assertEqual(response.status, 200)
            self.assertEqual(response.body, b"proxy")
            self.assertIn(b"GET /api/users?limit=1 HTTP/1.1", received[0])
            self.assertIn(b"x-forwarded-for: 10.0.0.1", received[0])
        finally:
            server.close()
            await server.wait_closed()
