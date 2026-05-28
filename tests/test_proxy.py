import asyncio
import socket
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

    async def test_proxy_pass_balances_between_upstreams(self) -> None:
        async def make_server(body: bytes) -> asyncio.Server:
            async def upstream_handler(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
                await reader.readuntil(b"\r\n\r\n")
                writer.write(
                    b"HTTP/1.1 200 OK\r\nContent-Length: "
                    + str(len(body)).encode("ascii")
                    + b"\r\n\r\n"
                    + body
                )
                await writer.drain()
                writer.close()
                await writer.wait_closed()

            return await asyncio.start_server(upstream_handler, "127.0.0.1", 0)

        first = await make_server(b"one")
        second = await make_server(b"two")
        first_port = first.sockets[0].getsockname()[1]
        second_port = second.sockets[0].getsockname()[1]
        try:
            request = HTTPRequest("GET", "/api/users", "HTTP/1.1", {"host": "localhost"}, b"")
            upstreams = f"http://127.0.0.1:{first_port} http://127.0.0.1:{second_port}"

            first_response = await proxy_request(request, upstreams, timeout=2.0)
            second_response = await proxy_request(request, upstreams, timeout=2.0)

            self.assertEqual(first_response.body, b"one")
            self.assertEqual(second_response.body, b"two")
        finally:
            first.close()
            second.close()
            await first.wait_closed()
            await second.wait_closed()

    async def test_proxy_pass_tries_next_upstream_when_one_is_down(self) -> None:
        async def upstream_handler(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
            await reader.readuntil(b"\r\n\r\n")
            writer.write(b"HTTP/1.1 200 OK\r\nContent-Length: 8\r\n\r\nfallback")
            await writer.drain()
            writer.close()
            await writer.wait_closed()

        alive = await asyncio.start_server(upstream_handler, "127.0.0.1", 0)
        alive_port = alive.sockets[0].getsockname()[1]
        dead_port = _unused_local_port()
        try:
            request = HTTPRequest("GET", "/api/users", "HTTP/1.1", {"host": "localhost"}, b"")
            upstreams = f"http://127.0.0.1:{dead_port} http://127.0.0.1:{alive_port}"

            response = await proxy_request(request, upstreams, timeout=0.5)

            self.assertEqual(response.status, 200)
            self.assertEqual(response.body, b"fallback")
        finally:
            alive.close()
            await alive.wait_closed()


def _unused_local_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]
