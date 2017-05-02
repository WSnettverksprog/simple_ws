from simple_ws import WebSocket


class WSHandler(WebSocket):
    def on_message(self, msg, client):
        for c in self.clients:
            if c.status == c.is_open():
                c.write_message(msg)

    def on_open(self, client):
        print("Client connected!")

    def on_close(self, client):
        print("Client left...")


host = ''
port = 8080

ws = WSHandler(host, port, compression=True)
