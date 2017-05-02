# python-WS
Simple websocket implementation in python

## Test the library
To test the library, open two command windows and cd into python-WS directory
- Run `python -m http.server 8000`
- Run `python ws_example.py` in the other window
- Open localhost:8000 in a browser

## TODO
1. ~Implement continous frames~
2. Write tests
3. ~Extensions (compression etc.)~
4. ~Framework interface~
5. ~Ping, Pong and Closing~ (Extend ping and pong to support data)
6. Error handling
7. Clean up classes

### Example

```javascript
import WebSocket from simple_ws

class WSHandler(WebSocket):
    def on_message(self, msg, client):
        for c in self.clients:
            if c.status == c.is_open():
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
