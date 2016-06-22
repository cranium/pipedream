import asyncio
import struct

__all__ = ["OpCode", "CloseCode", "Status", "WebSocketProtocol", "WebSocketFrame", "WebSocketMessage"]


class OpCode:
    """
    Codes used to indicate the type of frame
    """
    CONTINUATION = 0
    TEXT = 1
    BINARY = 2
    CLOSE = 8
    PING = 9
    PONG = 10


class CloseCode:
    """
    Codes used to close the socket
    """
    NORMAL = 1000
    GOING_AWAY = 1001
    PROTOCOL_ERROR = 1002
    UNEXPECTED_TYPE = 1003
    WRONG_TYPE = 1007
    POLICY_VIOLATION = 1008
    MESSAGE_TOO_BIG = 1009
    EXTENSION_EXPECTED = 1010
    UNEXPECTED_CONDITION = 1011


class Status:
    """
    Status of the connection
    """
    OPEN = 1
    CLOSING = 2
    CLOSED = 3


class WebSocketProtocol:
    """
    The protocol that manages the WebSocket. Defaults to operating as a server.
    """
    def __init__(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter, server: "WebSocketServer"):
        """
        :param reader: StreamReader used to read from the TCP socket
        :param writer: StreamWriter used to write to the TCP socket
        :param server: WebSocketServer managing this socket
        :return:
        """
        self.reader = reader
        self.writer = writer
        self.server = server
        self.status = Status.OPEN

    async def recv(self):
        """
        Future to listen on the WebSocket for a message
        :return: Message from the WebSocket
        :rtype: WebSocketMessage
        """
        message = WebSocketMessage()
        await message.recv(self.reader)
        return message

    async def send(self, data, text: bool=True):
        """
        Future to send a message over the WebSocket
        :param data:
        :type data: str|bytes
        :param text: If True, message is utf-8, if False, message is binary
        :return:
        """
        if self.status == Status.OPEN:
            message = WebSocketMessage()
            if text:
                message.data = data.encode()
                message.opcode = OpCode.TEXT
            else:
                message.data = bytes(data)
                message.opcode = OpCode.BINARY
            await message.send(self.writer)

    async def close(self, status_code: int=None, reason: str=None):
        """
        Future to begin the closing handshake on the WebSocket
        :param status_code: CloseCode indicating reason for closing
        :param reason: String indicating reason for closing
        :return:
        """
        if self.status == Status.OPEN:
            self.status = Status.CLOSING
            message = WebSocketMessage()
            message.opcode = OpCode.CLOSE
            message.build_close_data(status_code, reason)
            await message.send(self.writer)
            await asyncio.wait_for(self.recv(), 10)
            self.shutdown()

    async def on_close(self):
        """
        Respond to the closing handshake with a close frame followed by killing the socket
        :return:
        """
        if self.status == Status.OPEN:
            self.status = Status.CLOSING
            message = WebSocketMessage()
            message.opcode = OpCode.CLOSE
            await message.send(self.writer)
            self.shutdown()

    def shutdown(self):
        """
        Shut down the socket connection and detach it from the server
        :return:
        """
        if self.status == Status.CLOSING:
            self.writer.close()
            self.server.sockets.remove(self)
            self.status = Status.CLOSED


class WebSocketFrame:
    """
    A WebSocket message fragment
    """
    def __init__(self, fin: bool, opcode: int, data: bytes):
        """
        :param fin: If True, this is the last frame of the message
        :param opcode: OpCode indicating frame type
        :param data: Payload to be sent in the frame
        :return:
        """
        self.fin = fin
        self.opcode = opcode
        self.data = data

    @classmethod
    async def read_frame(cls, reader: asyncio.StreamReader):
        """
        Class Method to read a frame from the WebSocket and initialize a WebSocketFrame with the relevant data
        :param reader: StreamReader to read from
        :return: Initialized WebSocketFrame
        :rtype: WebSocketFrame
        """
        head = (await reader.readexactly(2))
        fin = bool(head[0] >> 7)
        opcode = int(head[0] & 0b00001111)
        mask = bool(head[1] >> 7)
        payload_length = head[1] & 0b01111111
        if payload_length == 126:
            payload_bytes = await reader.readexactly(2)
            payload_length = struct.unpack('!H', payload_bytes)[0]
        elif payload_length == 127:
            payload_bytes = await reader.readexactly(8)
            payload_length = struct.unpack('!Q', payload_bytes)[0]
        if mask:
            masking_key = await reader.readexactly(4)
            data = await reader.readexactly(payload_length)
            data = bytes(b ^ masking_key[i % 4] for i, b in enumerate(data))
        else:
            data = await reader.readexactly(payload_length)

        return cls(fin, opcode, data)


class WebSocketMessage:
    """
    A WebSocket message
    """
    def __init__(self, server: bool=True):
        """
        :param server: If True, the message originated from the server
        :return:
        """
        self.opcode = None
        self.data = None
        self.server = server

    async def recv(self, reader: asyncio.StreamReader):
        """
        Future to receive each frame of a message and set the data
        :param reader:
        :return:
        """
        frame = await WebSocketFrame.read_frame(reader)
        opcode = frame.opcode
        data = bytearray(frame.data)
        fin = frame.fin
        while not fin:
            frame = await WebSocketFrame.read_frame(reader)
            data.extend(frame.data)
            fin = frame.fin
        self.opcode = opcode
        self.data = data

    async def send(self, writer: asyncio.StreamWriter):
        """
        Future to send a message over the WebSocket
        :param writer: StreamWriter used to send the message
        :return:
        """
        opcode = self.opcode
        data = self.data

        frame = bytearray()
        head = 0b00000000
        head |= 0b10000000
        head |= opcode
        frame.append(head)
        next_byte = 0b00000000
        if data:
            payload_length = len(data)
        else:
            payload_length = 0
        if 65535 >= payload_length >= 126:
            next_byte |= 126
            extended_bytes = struct.pack("!H", payload_length)
        elif payload_length > 65535:
            next_byte |= 127
            extended_bytes = struct.pack("!Q", payload_length)
        else:
            next_byte |= payload_length
            extended_bytes = None
        frame.append(next_byte)
        if extended_bytes:
            frame.extend(extended_bytes)
        if data:
            frame.extend(data)
        writer.write(frame)
        await writer.drain()

    def build_close_data(self, status_code, message):
        """
        Sets the status code and message payload of a CLOSE message
        :param status_code: Status code to send in the payload
        :param message: Message to send in the payload
        :return:
        """
        data = bytearray()
        if status_code:
            data.extend(struct.pack("!H", status_code))
            if message:
                data.extend(message.encode())
        self.data = data

    def decode_close(self):
        """
        Returns the status code and closing message from a CLOSE message
        :return:
        """
        if len(self.data) >= 2:
            status_code = struct.unpack("!H", self.data[0:2])
            if len(self.data) > 2:
                message = self.data[2:]
            else:
                message = None
        else:
            status_code = None
            message = None
        return status_code, message
