from simple_ws import WebSocket


class WSHandler(WebSocket):
    def on_message(self, msg, client):
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
