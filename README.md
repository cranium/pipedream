# pipedream
A Python3 asyncio based websocket library

Usage:

Extend WebSocketHandler and override these functions:

1. on_connect
2. recv
3. send
4. close
5. on_close

Pass the extended WebSocketHandler to WebSocketServer.start and start up your event loop

This library is in early phase development
