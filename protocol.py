import struct


class OpCode:
    CONTINUATION = 0
    TEXT = 1
    BINARY = 2
    CLOSE = 8
    PING = 9
    PONG = 10


class CloseCode:
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
    OPEN = 1
    CLOSING = 2
    CLOSED = 3


class WebSocketProtocol:
    def __init__(self, reader, writer, server):
        self.reader = reader
        self.writer = writer
        self.server = server
        self.status = Status.OPEN

    async def recv(self):
        message = await WebSocketMessage.await_message(self.reader)
        return message


    async def send(self, data, text=True):
        if text:
            data = data.encode()
            opcode = OpCode.TEXT
        else:
            data = bytes(data)
            opcode = OpCode.BINARY
        await WebSocketMessage.compose_frame(self.writer, True, opcode, False, data)

    async def close(self, status_code=CloseCode.NORMAL, message="Connection Close"):
        self.status = Status.CLOSING
        data = WebSocketMessage.build_close_data(status_code, message)
        await WebSocketMessage.compose_frame(self.writer, True, OpCode.CLOSE, False, data)
        self.server.sockets.remove(self)
        self.status = Status.CLOSED


class WebSocketFrame:
    def __init__(self, fin, opcode, data):
        self.fin = fin
        self.opcode = opcode
        self.data = data

    @classmethod
    async def read_frame(cls, reader):
        head = (await reader.readexactly(1))[0]
        fin = bool(head >> 7)
        opcode = int(head & 0b00001111)
        next = (await reader.readexactly(1))[0]
        mask = bool(next >> 7)
        payload_length = next & 0b01111111
        if payload_length == 126:
            payload_bytes = await reader.readexactly(2)
            payload_length = struct.unpack('!H', payload_bytes)[0]
        elif payload_length == 127:
            payload_bytes = await reader.readexactly(8)
            payload_length = struct.unpack('!Q', payload_bytes)[0]
        if mask:
            masking_key = await reader.readexactly(4)

        data = await reader.readexactly(payload_length)

        if mask:
            data = bytes(b ^ masking_key[i % 4] for i, b in enumerate(data))

        return cls(fin, opcode, data)


class WebSocketMessage:
    def __init__(self, opcode, data):
        self.opcode = opcode
        self.data = data

    @classmethod
    async def await_message(cls, reader):
        frame = await WebSocketFrame.read_frame(reader)
        opcode = frame.opcode
        data = bytearray(frame.data)
        fin = frame.fin
        while not fin:
            frame = await WebSocketFrame.read_frame(reader)
            data.extend(frame.data)
            fin = frame.fin

        return cls(opcode, data)

    @classmethod
    async def compose_frame(cls, writer, fin, opcode, mask, data):
        frame = bytearray()
        head = 0b00000000
        if fin:
            head |= 0b10000000
        head |= opcode
        frame.append(head)
        next_byte = 0b00000000
        payload_length = len(data)
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

    @classmethod
    def build_close_data(cls, status_code, message):
        data = bytearray()
        if status_code:
            data.extend(struct.pack("!H", status_code))
            if message:
                data.extend(message.encode())
        return data

    def decode_close(self):
        status_code = struct.unpack("!H", self.data[0:2])
        message = self.data[2:]
        return status_code, message
