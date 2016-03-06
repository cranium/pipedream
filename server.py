import asyncio
import base64
import struct
from hashlib import sha1


def buildAccept(key):
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

            ws_accept = buildAccept(ws_key)

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
            msg = yield from WebsocketMessage(self.reader).read_message()


class WebsocketMessage():
    def __init__(self, reader):
        self.reader = reader
        self.fin = None

    @asyncio.coroutine
    def read_message(self):
        a = yield from self.reader.read(2)
        head, opcode = struct.unpack("!BB", a)
        fin = head >> 7
        if fin:
            self.fin = True
        else:
            self.fin = False



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
