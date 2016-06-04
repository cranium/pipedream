import asyncio
from handshake import WebSocketHandshakeProtocol
from protocol import WebSocketProtocol, CloseCode
from handler import WebSocketHandler


class WebSocketServer:
    """
    This class comprises the factory to create and upgrade the protocols as well as contains a reference to all sockets
    """
    def __init__(self, handler: WebSocketHandler):
        """
        :param handler:
        :return:
        """
        self.handler = handler
        self.sockets = set()
        self.server = None

    async def protocol_factory(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        """
        Factory to create the protocols when a connection is made
        :param reader:
        :param writer:
        :return:
        """
        http = WebSocketHandshakeProtocol(reader, writer)
        upgrade = await http.handshake()
        if upgrade:
            protocol = WebSocketProtocol(reader, writer, self)
            self.sockets.add(protocol)
            asyncio.ensure_future(self.handler.handle(protocol))

    async def close(self, message: str="Server shutting down"):
        """
        Closes all of the sockets with the provided message
        :param message:
        :return:
        """
        for socket in self.sockets:
            asyncio.ensure_future(socket.close(CloseCode.GOING_AWAY, message))
        self.server.close()


def start_server(ws_server: WebSocketServer, host: str=None, port: int=None, loop: asyncio.BaseEventLoop=None):
    """
    Wraps asyncio.start_server to call WebSocketServer
    :param ws_server:
    :param host:
    :param port:
    :param loop:
    :return:
    """
    server = asyncio.start_server(ws_server.protocol_factory, host, port, loop=loop)
    ws_server.server = server
    return server
