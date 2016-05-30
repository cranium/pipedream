import asyncio
import base64
from hashlib import sha1
import struct


class OpCodes:
    CONTINUATION = 0
    TEXT = 1
    BINARY = 2
    CLOSE = 8
    PING = 9
    PONG = 10


def build_accept(key):
    return base64.b64encode(sha1(b"".join([key, b"258EAFA5-E914-47DA-95CA-C5AB0DC85B11"])).digest())


class WebsocketHandshakeProtocol:
    MAX_HEADERS = 256
    MAX_LINE = 4096

    def __init__(self, reader, writer):
        self.reader = reader
        self.writer = writer

    @asyncio.coroutine
    def handshake(self):
        try:
            headers = yield from self.read_request()
            ws_key = headers[b"Sec-WebSocket-Key"]
            ws_accept = build_accept(ws_key)
            arr = [
                b"HTTP/1.1 101 Switching Protocols",
                b"Upgrade: websocket",
                b"Connection: Upgrade",
                b"Sec-WebSocket-Accept: " + ws_accept,
                b"\r\n"
            ]
            response = b"\r\n".join(arr)
            self.writer.write(response)
            yield from self.writer.drain()
            return True
        except:
            return False

    @asyncio.coroutine
    def read_request(self):
        headers = {}
        request_line = yield from self.read_line()
        for _ in range(self.MAX_HEADERS):
            line = yield from self.read_line()
            if line == b'\r\n':
                break
            key, value = map(lambda x: x.strip(), line.split(b":", 1))
            headers[key] = value
        else:
            raise ValueError("Too many headers")
        return headers

    @asyncio.coroutine
    def read_line(self):
        line = yield from self.reader.readline()
        if len(line) > self.MAX_LINE:
            raise ValueError("Line too long")
        if not line.endswith(b'\r\n'):
            raise ValueError("Line without CRLF")
        return line


class WebsocketProtocol:
    def __init__(self, reader, writer):
        self.reader = reader
        self.writer = writer

    @asyncio.coroutine
    def listen(self):
        closed = False
        while not closed:
            message = yield from WebsocketMessage.await_message(self.reader)
            if message.opcode == OpCodes.CLOSE:
                closed = True
                self.writer.close()


class WebsocketFrame():
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


class WebsocketMessage():
    def __init__(self, opcode, data):
        self.opcode = opcode
        self.data = data

    @classmethod
    @asyncio.coroutine
    def await_message(cls, reader):
        frame = yield from WebsocketFrame.read_frame(reader)
        opcode = frame.opcode
        data = frame.data
        fin = frame.fin
        while not fin:
            frame = yield from WebsocketFrame.read_frame(reader)
            data.extend(frame.data)
            fin = frame.fin
        return cls(opcode, data)

@asyncio.coroutine
def protocol_factory(reader, writer):
    http = WebsocketHandshakeProtocol(reader, writer)
    upgrade = yield from http.handshake()
    if upgrade:
        ws = WebsocketProtocol(reader, writer)
        yield from ws.listen()

loop = asyncio.get_event_loop()
loop.set_debug(True)
coro = asyncio.start_server(protocol_factory, "0.0.0.0", 8888, loop=loop)
server = loop.run_until_complete(coro)
print('Serving on {}'.format(server.sockets[0].getsockname()))

loop.run_forever()
