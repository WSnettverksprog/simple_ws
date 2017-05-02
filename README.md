# python-WS
Simple websocket implementation in python

## Running the example code
To test the library, open two command windows and cd into the python-WS directory
- Run `python -m http.server 8000`
- Run `python ws_example.py` in the other window
- Open http://localhost:8000 in a browser


## TODO
1. ~Implement continous frames~
2. Write tests
3. ~Extensions (compression etc.)~
4. ~Framework interface~
5. ~Ping, Pong and Closing~ (Extend ping and pong to support data)
6. Error handling
7. Clean up classes
8. Implement close status and reason
9. Implement all compression configurations
10. Add more configurability/remove hardcoded constants
11. Implement connection limit

## Example code

```javascript
from simple_ws import WebSocket


class WSHandler(WebSocket):
    def on_message(self, msg, client):
        for client in self.clients:
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

## Functions
### WebSocket
#### on_open(self, client)
Called when the server opens a connection to a new client (client).
```python
def on_open(self, client):
    # Code here executes when opening a connection
```

#### on_close(self, client)
Called when the server closes a connection to a client (client).
```python
def on_close(self, client):
    # Code here executes when closing a connection
```

#### on_message(self, msg, client)
Called when the server has received a message (msg) from a client (client). The message can be in either binary or text format.
```python
def on_message(self, msg, client):
    # Code here executes when server recieves a messages from client
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
