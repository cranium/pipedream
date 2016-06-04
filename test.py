import asyncio
from server import start_server, WebSocketServer
from protocol import Status, OpCode


class WebsocketHandler:
    def __init__(self, protocol):
        self.protocol = protocol

    def recv(self, message):
        if message.data == "close":
            self.close()

    def send(self, message, text=True):
        asyncio.ensure_future(self.protocol.send(message, text))

    def close(self):
        asyncio.ensure_future(self.protocol.close())

    def on_close(self):
        pass

    @classmethod
    async def handle(cls, protocol):
        websocket = cls(protocol)
        while protocol.status == Status.OPEN:
            message = await protocol.recv()
            if message.opcode == OpCode.TEXT:
                websocket.recv(message.data.decode("utf-8"))
            elif message.opcode == OpCode.BINARY:
                websocket.recv(message.data)
            elif message.opcode == OpCode.CLOSE:
                status_code, message = message.decode_close()
                websocket.on_close(status_code, message)

ws_server = WebSocketServer(WebsocketHandler)

server = start_server(ws_server, "0.0.0.0", 8888)

loop = asyncio.get_event_loop()
loop.run_until_complete(server)
loop.run_forever()
