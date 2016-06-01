import base64
from hashlib import sha1
import asyncio


class WebSocketHandshakeProtocol:
    MAX_HEADERS = 256
    MAX_LINE = 4096

    HANDSHAKE_UUID = b"258EAFA5-E914-47DA-95CA-C5AB0DC85B11"

    @classmethod
    def build_accept_hash(cls, key):
        return base64.b64encode(sha1(b"".join([key, cls.HANDSHAKE_UUID])).digest())

    def __init__(self, reader, writer):
        self.reader = reader
        self.writer = writer

    async def handshake(self):
        headers = await self.read_request()
        ws_key = headers[b"Sec-WebSocket-Key"]
        ws_accept = self.build_accept_hash(ws_key)
        response_lines = (
            b"HTTP/1.1 101 Switching Protocols",
            b"Upgrade: websocket",
            b"Connection: Upgrade",
            b"Sec-WebSocket-Accept: " + ws_accept,
            b"\r\n"
        )
        response = b"\r\n".join(response_lines)
        self.writer.write(response)
        await self.writer.drain()
        return True

    async def read_request(self):
        headers = {}
        request_line = await self.read_line()
        for _ in range(self.MAX_HEADERS):
            line = await self.read_line()
            if line == b'\r\n':
                break
            key, value = map(lambda x: x.strip(), line.split(b":", 1))
            headers[key] = value
        else:
            raise ValueError("Too many headers")
        return headers

    async def read_line(self):
        line = await self.reader.readline()
        if len(line) > self.MAX_LINE:
            raise ValueError("Line too long")
        if not line.endswith(b'\r\n'):
            raise ValueError("Line without CRLF")
        return line
