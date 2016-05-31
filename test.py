import asyncio
from server import serve


@asyncio.coroutine
def handler(protocol):
    while True:
        message = yield from protocol.recv()
        yield from protocol.send("I fack u mather")

loop = asyncio.get_event_loop()
server = serve(handler, "0.0.0.0", 8888, loop)

loop.run_until_complete(server)
loop.run_forever()
