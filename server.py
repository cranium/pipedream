import asyncio
from handshake import WebSocketHandshakeProtocol
from protocol import WebSocketProtocol


class WebSocketServer:
    @asyncio.coroutine
    def protocol_factory(self, reader, writer):
        http = WebSocketHandshakeProtocol(reader, writer)
        upgrade = yield from http.handshake()
        if upgrade:
            ws = WebSocketProtocol(reader, writer)
            yield from ws.listen()
