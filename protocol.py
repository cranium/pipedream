import asyncio
import struct


class OpCodes:
    CONTINUATION = 0
    TEXT = 1
    BINARY = 2
    CLOSE = 8
    PING = 9
    PONG = 10


class WebSocketProtocol:
    def __init__(self, reader, writer):
        self.reader = reader
        self.writer = writer

    @asyncio.coroutine
    def listen(self):
        closed = False
        while not closed:
            message = yield from WebSocketMessage.await_message(self.reader)
            if message.opcode == OpCodes.CLOSE:
                closed = True
                self.writer.close()


class WebSocketFrame:
    def __init__(self, fin, opcode, data):
        self.fin = fin
        self.opcode = opcode
        self.data = data

    @classmethod
    @asyncio.coroutine
    def read_frame(cls, reader):
        head = (yield from reader.read(1))[0]
        fin = bool(head >> 7)
        opcode = int(head & 0b00001111)
        next = (yield from reader.read(1))[0]
        mask = bool(next >> 7)
        payload_length = next & 0b01111111
        if payload_length == 126:
            payload_bytes = yield from reader.read(2)
            payload_length = struct.unpack('H', payload_bytes)[0]
        elif payload_length == 127:
            payload_bytes = yield from reader.read(8)
            payload_length = struct.unpack('Q', payload_bytes)[0]
        if mask:
            masking_key = yield from reader.read(4)

        encoded_payload = yield from reader.read(payload_length)

        decoded_payload = bytearray()
        i = 0
        for byte in encoded_payload:
            if mask:
                decoded_payload.append(byte ^ masking_key[i % 4])
            else:
                decoded_payload.append(byte)
            i += 1

        return cls(fin, opcode, decoded_payload)


class WebSocketMessage:
    def __init__(self, opcode, data):
        self.opcode = opcode
        self.data = data

    @classmethod
    @asyncio.coroutine
    def await_message(cls, reader):
        frame = yield from WebSocketFrame.read_frame(reader)
        opcode = frame.opcode
        data = frame.data
        fin = frame.fin
        while not fin:
            frame = yield from WebSocketFrame.read_frame(reader)
            data.extend(frame.data)
            fin = frame.fin
        return cls(opcode, data)
