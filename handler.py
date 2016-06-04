import asyncio
from protocol import Status, OpCode, CloseCode, WebSocketProtocol


class WebSocketHandler:
    """
    Base class for handling a WebSocket connection.
    Contains the loop that calls back to all of the appropriate methods.
    This should be subclassed by the application and passed into WebSocketServer
    """
    def __init__(self, protocol: WebSocketProtocol):
        """
        :param protocol: The WebSocketProtocol that is managing this connection
        :return:
        """
        self.protocol = protocol

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

    def on_close(self, status_code: int, message: str):
        """
        Callback called when a WebSocket has closed
        :param status_code: Status code used to close
        :param message: Message used to close
        :return:
        """
        pass

    @classmethod
    async def handle(cls, protocol):
        """
        Handles incoming messages on the socket and calls the appropriate callback
        :param protocol:
        :return:
        """
        websocket = cls(protocol)
        while protocol.status == Status.OPEN:
            message = await protocol.recv()
            if message.opcode == OpCode.TEXT:
                websocket.recv(message.data.decode("utf-8"))
            elif message.opcode == OpCode.BINARY:
                websocket.recv(message.data)
            elif message.opcode == OpCode.CLOSE:
                await protocol.close()
                status_code, message = message.decode_close()
                websocket.on_close(status_code, message)
