import base64
from hashlib import sha1

__all__ = ["WebSocketHandshakeProtocol"]


class WebSocketHandshakeProtocol:
    """
    HTTP protocol to handle the handshake with the client
    """

    # TODO: Move these constants to a config
    MAX_HEADERS = 256
    MAX_LINE = 4096

    HANDSHAKE_UUID = b"258EAFA5-E914-47DA-95CA-C5AB0DC85B11"

    @classmethod
    def build_accept_hash(cls, key: bytes):
        """
        Returns the Sec-WebSocket-Accept from the Sec-WebSocket-Key
        :param key: Value of the Sec-WebSocket-Key header
        :return: Returns the Sec-WebSocket-Accept header value
        """
        return base64.b64encode(sha1(b"".join([key, cls.HANDSHAKE_UUID])).digest())

    def __init__(self, reader, writer):
        """
        :param reader: StreamReader to read from the TCP socket
        :param writer: StreamWriter to write to the TCP socket
        :return:
        """
        self.reader = reader
        self.writer = writer

    async def handshake(self):
        """
        Future that handles the entire handshake
        :return:
        """
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
        """
        Reads the HTTP request and returns an list of headers
        :return: Dict of headers
        :rtype: dict(bytes: bytes)
        """
        headers = {}
        request_line = await self.read_line()  # Skip this
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
        """
        Reads a line from the TCP socket
        :return: Line from the HTTP request
        :rtype: bytes
        """
        line = await self.reader.readline()
        if len(line) > self.MAX_LINE:
            raise ValueError("Line too long")
        if not line.endswith(b'\r\n'):
            raise ValueError("Line without CRLF")
        return line
