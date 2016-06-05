import asyncio
from pipedream import WebSocketHandler
from pipedream import WebSocketServer


class WebSocketEchoTest(WebSocketHandler):
    def on_connect(self):
        print("Connection made.")

    def recv(self, message):
        self.send(message)

    def on_close(self, *args):
        print("Connection closed.")

server = WebSocketServer.start(WebSocketEchoTest, "0.0.0.0", 8888)

loop = asyncio.get_event_loop()
loop.run_until_complete(server)
loop.run_forever()
