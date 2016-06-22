import asyncio

from .protocol import Status, OpCode, CloseCode, WebSocketProtocol

__all__ = ["WebSocketHandler"]


class WebSocketHandler:
    """
    Base class for handling a WebSocket connection.
    Contains the loop that calls back to all of the appropriate methods.
    This should be sub-classed by the application and passed into WebSocketServer
    """
    def __init__(self, protocol: WebSocketProtocol):
        """
        :param protocol: The WebSocketProtocol that is managing this connection
        :return:
        """
        self.protocol = protocol

    def on_connect(self):
        """
        Callback called after the HTTP handshake has completed and the socket is online
        :return:
        """
        pass

    def recv(self, message: str):
        """
        Callback for a received message
        :param message: The binary or utf-8 encoded string received on the socket
        :return:
        """
        pass

    def send(self, message: str, text: bool=True):
        """
        Sends a message over the socket
        :param message: Message to send
        :param text: If True, encodes the message as utf-8, if false, sends as bytes
        :return:
        """
        asyncio.ensure_future(self.protocol.send(message, text))

    def close(self, status: int=CloseCode.NORMAL, message: str=None):
        """
        Closes the WebSocket
        :param status: Status code to close with. See: CloseCode
        :param message: Message to close with
        :return:
        """
        asyncio.ensure_future(self.protocol.close(status, message))
        self.on_close(status, message)

    def on_close(self, status_code: int, message: str):
        """
        Callback called when a WebSocket has closed
        :param status_code: Status code used to close
        :param message: Message used to close
        :return:
        """
        pass

    @classmethod
    async def handle(cls, protocol: WebSocketProtocol):
        """
        Handles incoming messages on the socket and calls the appropriate callback
        :param protocol:
        :return:
        """
        web_socket = cls(protocol)
        web_socket.on_connect()
        while protocol.status == Status.OPEN:
            message = await protocol.recv()
            if message.opcode == OpCode.TEXT:
                web_socket.recv(message.data.decode("utf-8"))
            elif message.opcode == OpCode.BINARY:
                web_socket.recv(message.data)
            elif message.opcode == OpCode.CLOSE:
                await protocol.on_close()
                status_code, message = message.decode_close()
                web_socket.on_close(status_code, message)
