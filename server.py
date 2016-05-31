import asyncio
from handshake import WebSocketHandshakeProtocol
from protocol import WebSocketProtocol


class WebSocketServer:
    def __init__(self, handler):
        self.handler = handler

    @asyncio.coroutine
    def protocol_factory(self, reader, writer):
        http = WebSocketHandshakeProtocol(reader, writer)
        upgrade = yield from http.handshake()
        if upgrade:
            protocol = WebSocketProtocol(reader, writer)
            yield from self.handler(protocol)


@asyncio.coroutine
def serve(handler, host=None, port=None, loop=None):

    if loop is None:
        loop = asyncio.get_event_loop()

    ws_server = WebSocketServer(handler)
    return asyncio.start_server(ws_server.protocol_factory, host, port, loop=loop)
