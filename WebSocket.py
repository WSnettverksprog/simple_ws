import socket

class Parser():
    def create_header(self):
        return "HTTP/1.1 200 OK\r\n\r\n"

class Client():

    parser = Parser()
    def __init__(self, conn, addr):
        self.conn = conn
        self.addr = addr

    def send(self, data):

        payload = "HTTP/1.1 200 OK\r\nContent-Type: text/plain\r\nContent-Length: "+str(len(data))+"\r\n\r\n"+data+"\r\n"
        print(str.encode(payload))
        self.conn.sendall(str.encode(payload))

    def isOpen(self):
        return True


class WebSocket():
    def __init__(self, host, port, on_open=None, on_message=None,
                 on_error=None, on_close=None, buffer_size=4096, max_connections=10):
        self.Socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.clients = []
        self.host = host
        self.port = port
        self.on_open = on_open
        self.on_message = on_message
        self.on_error = on_error
        self.on_close = on_close
        self.max_connections = max_connections
        self.buffer_size = buffer_size
        try:
            self.Socket.bind((host, port))
        except socket.error as e:
            raise Exception("Issue binding host to port\n",str(e))
        self.__listenForConn()

    def __listenForMsg(self, client):
        while True:
            message = client.conn.recv(self.buffer_size)
            print(message)
            if self.on_message:
                self.on_message(self.clients, message.decode('utf-8'))



    def __listenForConn(self):
        self.Socket.listen(self.max_connections)
        print(self.Socket)
        conn, addr = self.Socket.accept()
        client = Client(conn, addr)
        self.clients.append(client)
        print("New connection from: " + addr[0] + ":" + str(addr[1]))
        if self.on_open is not None:
            self.on_open(self.clients)
        self.__listenForMsg(client)


host = ''
port = 8080
def on_open(clients):
    for client in clients:
        if client.isOpen():
            print(client)

def on_message(clients, msg):
    for client in clients:
        client.send("Vi mottok meldingen: "+msg)

ws = WebSocket(host,port, on_open=on_open, on_message=on_message)
