import asyncio
from server import serve

async def handler(protocol):
    while True:
        message = await protocol.recv()
        print("opcode: "+str(message.opcode))
        print(message.data)
        await protocol.send("I fack u mather")

loop = asyncio.get_event_loop()
server = serve(handler, "0.0.0.0", 8888, loop)

loop.run_until_complete(server)
loop.run_forever()
