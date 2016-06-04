import asyncio
from handler import WebSocketHandler
from server import start_server, WebSocketServer


class WebSocketEchoTest(WebSocketHandler):
    def recv(self, message):
        self.send(message)


ws_server = WebSocketServer(WebSocketEchoTest)

server = start_server(ws_server, "0.0.0.0", 8888)

loop = asyncio.get_event_loop()
loop.run_until_complete(server)
loop.run_forever()
