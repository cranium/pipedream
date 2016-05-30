import asyncio
import base64
from hashlib import sha1
import struct

opcodes = {
    0: "continuation frame",
    1: "text frame",
    2: "binary frame",
    8: "connection close",
    9: "ping",
    10: "pong"
}


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

            print(headers)

            ws_key = headers[b"Sec-WebSocket-Key"]

            ws_accept = build_accept(ws_key)

            print(ws_accept)

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
        self.open = True

    @asyncio.coroutine
    def listen(self):
        while True:
            message = yield from WebsocketFrame.read_frame(self.reader)


class WebsocketFrame():
    def __init__(self):
        pass

    @classmethod
    @asyncio.coroutine
    def read_frame(cls, reader):
        head_byte = yield from reader.read(1)
        head = head_byte[0]
        fin = bool(head >> 7)
        opcode = int(head & 0b00001111)
        next_byte = yield from reader.read(1)
        next = next_byte[0]
        mask = bool(next >> 7)
        payload_length = next & 0b01111111
        if payload_length == 126:
            payload_bytes = yield from reader.read(2)
            payload_length = struct.unpack('BB', payload_bytes)
        elif payload_length == 127:
            payload_bytes = yield from reader.read(8)
            payload_length = struct.unpack('BBBBBBBB', payload_bytes)
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

        return cls()


class WebsocketMessage():
    @classmethod
    @asyncio.coroutine
    def await_message(cls, reader):
        frame = yield from WebsocketFrame.read_frame(reader)
        



@asyncio.coroutine
def protocol_factory(reader, writer):
    print("Connection Opened to:")
    print(writer.get_extra_info('peername'))
    http = WebsocketHandshakeProtocol(reader, writer)
    upgrade = yield from http.handshake()
    if upgrade:
        print("Connection Upgraded")
        ws = WebsocketProtocol(reader, writer)
        yield from ws.listen()
    print("Connection Closed")
    writer.close()

loop = asyncio.get_event_loop()
loop.set_debug(True)
coro = asyncio.start_server(protocol_factory, "0.0.0.0", 8888, loop=loop)
server = loop.run_until_complete(coro)
print('Serving on {}'.format(server.sockets[0].getsockname()))

loop.run_forever()
