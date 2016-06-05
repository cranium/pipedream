import asyncio
from pipedream import WebSocketHandler
from pipedream import WebSocketServer


class WebSocketEchoTest(WebSocketHandler):
    def recv(self, message):
        self.send(message)

server = WebSocketServer.start(WebSocketEchoTest, "0.0.0.0", 8888)

loop = asyncio.get_event_loop()
loop.run_until_complete(server)
loop.run_forever()
