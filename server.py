import asyncio
from handshake import WebSocketHandshakeProtocol
from protocol import WebSocketProtocol, CloseCode


class WebSocketServer:
    def __init__(self, handler):
        self.handler = handler
        self.sockets = set()
        self.server = None

    async def protocol_factory(self, reader, writer):
        http = WebSocketHandshakeProtocol(reader, writer)
        upgrade = await http.handshake()
        if upgrade:
            protocol = WebSocketProtocol(reader, writer, self)
            self.sockets.add(protocol)
            asyncio.ensure_future(self.handler.handle(protocol))

    async def close(self, message="Server shutting down"):
        for socket in self.sockets:
            asyncio.ensure_future(socket.close(CloseCode.GOING_AWAY, message))
        self.server.close()


def start_server(ws_server, host=None, port=None):
    server = asyncio.start_server(ws_server.protocol_factory, host, port)
    ws_server.server = server
    return server
