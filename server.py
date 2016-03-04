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
        yield from self.read_frame()

    @asyncio.coroutine
    def read_frame(self):
        head = yield from self.reader.read(2)
        fmt = "!BB"
        print(len(head))
        print(struct.unpack(fmt, head))


        # data = yield from reader(2)
        # head1, head2 = struct.unpack('', data)
        # fin = bool(head1 & 0b10000000)
        # if head1 & 0b01110000:
        #     raise WebSocketProtocolError("Reserved bits must be 0")
        # opcode = head1 & 0b00001111
        # if bool(head2 & 0b10000000) != mask:
        #     raise WebSocketProtocolError("Incorrect masking")
        # length = head2 & 0b01111111
        # if length == 126:
        #     data = yield from reader(2)
        #     length, = struct.unpack('!H', data)
        # elif length == 127:
        #     data = yield from reader(8)
        #     length, = struct.unpack('!Q', data)
        # if max_size is not None and length > max_size:
        #     raise PayloadTooBig("Payload exceeds limit "
        #                         "({} > {} bytes)".format(length, max_size))
        # if mask:
        #     mask_bits = yield from reader(4)
        #
        # # Read the data
        # data = yield from reader(length)
        # if mask:
        #     data = bytes(b ^ mask_bits[i % 4] for i, b in enumerate(data))
        #
        # frame = Frame(fin, opcode, data)
        # check_frame(frame)
        # return frame



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
