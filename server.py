import asyncio
from handshake import WebSocketHandshakeProtocol
from protocol import WebSocketProtocol


@asyncio.coroutine
def protocol_factory(reader, writer):
    http = WebSocketHandshakeProtocol(reader, writer)
    upgrade = yield from http.handshake()
    if upgrade:
        ws = WebSocketProtocol(reader, writer)
        yield from ws.listen()


loop = asyncio.get_event_loop()
loop.set_debug(True)
coro = asyncio.start_server(protocol_factory, "0.0.0.0", 8888, loop=loop)
server = loop.run_until_complete(coro)
print('Serving on {}'.format(server.sockets[0].getsockname()))

loop.run_forever()
