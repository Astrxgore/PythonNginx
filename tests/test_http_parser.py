import asyncio
import unittest

from pynginx.http.parser import HeaderTooLargeError, read_body, read_request


def _reader_with(data: bytes) -> asyncio.StreamReader:
    reader = asyncio.StreamReader()
    reader.feed_data(data)
    reader.feed_eof()
    return reader


class HTTPParserTests(unittest.TestCase):
    def test_reads_request_line_and_headers(self) -> None:
        async def run() -> None:
            reader = _reader_with(b"GET /hello HTTP/1.1\r\nHost: LocalHost:8080\r\n\r\n")
            request = await read_request(reader, 16 * 1024)

            self.assertIsNotNone(request)
            self.assertEqual(request.method, "GET")
            self.assertEqual(request.target, "/hello")
            self.assertEqual(request.host, "localhost")

        asyncio.run(run())

    def test_reads_content_length_body_only_when_called(self) -> None:
        async def run() -> None:
            reader = _reader_with(b"POST /api HTTP/1.1\r\nHost: localhost\r\nContent-Length: 4\r\n\r\ndata")
            request = await read_request(reader, 16 * 1024)
            body = await read_body(reader, request, 1024)

            self.assertEqual(request.content_length, 4)
            self.assertEqual(body, b"data")

        asyncio.run(run())

    def test_rejects_large_headers(self) -> None:
        async def run() -> None:
            reader = _reader_with(b"GET / HTTP/1.1\r\nHost: localhost\r\nX-Long: value\r\n\r\n")

            with self.assertRaises(HeaderTooLargeError):
                await read_request(reader, 8)

        asyncio.run(run())
