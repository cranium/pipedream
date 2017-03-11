import asyncio

from .handler import WebSocketHandler
from .handshake import WebSocketHandshakeProtocol
from .protocol import WebSocketProtocol, CloseCode

__all__ = ["WebSocketServer"]


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

        self.sockets = set()  # type: set(WebSocketProtocol)
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
        for socket in self.sockets:  # type: WebSocketHandler
            asyncio.ensure_future(socket.close(CloseCode.GOING_AWAY, message))
        self.server.close()

    @classmethodd
    def start(cls, ws_handler: WebSocketHandler, host: str=None, port: int=None, loop: asyncio.BaseEventLoop=None):
        """
        Instantiates a WebSocketServer and wraps the server object
        :param ws_handler:
        :param host:
        :param port:
        :param loop:
        :return:
        """
        ws_server = cls(ws_handler)
        server = asyncio.start_server(ws_server.protocol_factory, host, port, loop=loop)
        ws_server.server = server
        return server
