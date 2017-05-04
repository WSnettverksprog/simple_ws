# simple_ws
Simple websocket implementation in python

[![PyPI version](https://badge.fury.io/py/simple_ws.svg)](https://badge.fury.io/py/simple_ws)
[![Python version](https://img.shields.io/badge/python-3.6.1-blue.svg)](https://www.python.org/downloads/release/python-361/)

## Install 
```
$ pip install simple_ws
```

## Usage
To test the library, clone repo, open two command windows and cd into the python-WS directory

- Run `python -m http.server 8000`
- Run `python ws_example.py` in the other window
- Open http://localhost:8000 in a browser

### Example

```python
from simple_ws import WebSocket

class WSHandler(WebSocket):
    def on_message(self, msg, target_client):
        for client in self.clients:
            if client.is_open():
                client.write_message(msg)

    def on_open(self, client):
        print("Client connected!")

    def on_close(self, client):
        print("Client left...")

    def on_ping(self, client):
        print("Recieved ping!")

    def on_pong(self, client):
        print("Recieved pong!")

host = ''
port = 8080

ws = WSHandler(host, port)
```

## WebSocket parameters
|parameter|type|default|description|
|---------|---------|---------|---------|
|```host```|String||Host domain|
|```port```|Integer||Port number for websocket|
|```ping```|Boolean|True|Whether server should ping client in a given intervall, will close connection if pong is not received|
|```ping_intervall```|Integer|5|How often should server ping client in seconds, has no effect if ping is set to false|
|```compression```|Boolean|True|Whether messages should be compressed|
|```max_frame_size```|Integer|8192|Max size for a single websocket frame. If payload exceeds limit, the message will be split in several parts|
|```buffer_size```|Integer|4096|Max network buffer size|

## Functions
### WebSocket
#### on_open(self, client)
Called when the server opens a connection to a new client (client).
```python
def on_open(self, client):
    # Executes when opening a connection
```

#### on_close(self, client)
Called when the server closes a connection to a client (client).
```python
def on_close(self, client):
    # Executes when closing a connection
```

#### on_message(self, msg, client)
Called when the server has received a message (msg) from a client (client). The message can be in either binary or text format.
```python
def on_message(self, msg, client):
    # Executes when server recieves a messages from client
```

#### on_ping(self, client)
Called when the server sends a ping to a client (client).
```python
def on_ping(self, client):
    # Executes when ping is sent to a client
```

#### on_pong(self, client)
Called when the server receives a pong from a client (client).
```python
def on_pong(self, client):
    # Executes when pong is received from a client
```

### Client
#### write_message(self, msg, binary=False)
Sends a message payload (msg) to the client. If binary=True, the message gets sent as binary data.

```python
# Text message
client.write_message("Hello world")

# Binary message
client.write_message(b"0x00", binary=True)
```

#### is_open(self)
Returns True if the connection has gone through handshake, and is currently open.

#### close(self, status, reason)
Sends a close frame to the client, and closes the connection after either a response, or after 1 second. Status and reason are not currently implemented. Will ultimately result in __WebSocket.on_close__ being fired.
```python
client.close(1002, "Pong not recieved")
```

## TODO
1. Write more tests
2. Add support for payload in ping and pong frames
3. Error handling
4. Clean up classes
5. Implement close status and reason
6. Implement all compression configurations
7. Add more configurability/remove hardcoded constants
8. Implement connection limit

## External sources
* https://tools.ietf.org/html/rfc6455
* https://tools.ietf.org/html/rfc7692
* https://developer.mozilla.org/en-US/docs/Web/API/WebSockets_API/Writing_WebSocket_servers
* https://www.igvita.com/2013/11/27/configuring-and-optimizing-websocket-compression/
* https://github.com/tornadoweb/tornado
* https://docs.python.org/3/library/asyncio.html

## License
[MIT License](LICENSE)

## Authors
[Even Dalen](https://github.com/evedal), [Audun Wigum Arbo](https://github.com/AudunWA) and [Ole Kristian Aune](https://github.com/okaune)
