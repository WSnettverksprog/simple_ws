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
import WebSocket from simple_ws

class WSHandler(WebSocket):
    def on_message(self, msg, client):
        for c in self.clients:
              c.write_message(msg)

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
### on_message(self, msg, client)
Called when a the server has received a message (msg) from a client (client). The message can be in either binary or text format.
