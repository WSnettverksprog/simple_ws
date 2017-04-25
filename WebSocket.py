import socket
import hashlib
import base64



class RequestParser():
    ws_const = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"
    def __init__(self, req=None):
        self.headers = {}
        self.body = ""
        if req is not None:
            self.parseRequest(req)

    def parseRequest(self, req):
        data = req.split("\r\n\r\n")
        headers = data[0]
        self.body = "\r\n\r\n".join(data[1:-1])
        for line in headers.split("\r\n"):
            try:
                header_line = line.split(":")
                self.headers[header_line[0].strip()] = header_line[1].strip()
            except:
                self.headers[line] = None


    @staticmethod
    def create_update_header(code):
        const = RequestParser.ws_const
        m = hashlib.sha1()
        m.update(str.encode(code))
        m.update(str.encode(const))
        hashed = m.digest()
        code = base64.b64encode(hashed)
        header = "HTTP/1.1 101 Switching Protocols\r\n"
        header += "Upgrade: websocket\r\n"
        header += "Connection: Upgrade\r\n"
        header += "Sec-WebSocket-Accept: "+code.decode("utf-8")+"\r\n\r\n"
        return header

class Client():
    CONNECTING = 0
    OPEN = 1
    CLOSED = 2
    parser = RequestParser()
    def __init__(self, conn, addr):
        self.conn = conn
        self.addr = addr
        self.status = Client.CONNECTING

    def send(self, data):
        pass

    def isOpen(self):
        return Client.OPEN == self.status

    def upgrade(self, header):
        code = header["Sec-WebSocket-Key"]
        updateHeader = RequestParser.create_update_header(code)
        print(str.encode(updateHeader))
        self.conn.sendall(str.encode(updateHeader))
        self.status = Client.OPEN



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
        req = RequestParser()
        while True:
            message = client.conn.recv(self.buffer_size)
            print(message)
            req.parseRequest(message.decode('utf-8'))
            print(req.headers)
            try:
                if(req.headers["Upgrade"] == "websocket" and req.headers["Connection"] == "Upgrade" and req.headers["Sec-WebSocket-Key"] is not None):
                    client.upgrade(req.headers)
            except KeyError:
                print("UNRECOGNIZED REQ")
                print(req.headers)




    def __listenForConn(self):
        self.Socket.listen(self.max_connections)
        print(self.Socket)
        conn, addr = self.Socket.accept()
        client = Client(conn, addr)
        self.clients.append(client)
        print("New connection from: " + addr[0] + ":" + str(addr[1]))
        self.__listenForMsg(client)

    #def __handleUpgrade(self):



host = ''
port = 8080

def on_open(clients):
    pass

def on_message(msg, clients):
    pass

def on_error(err, clients):
    pass

def on_close(clients):
    pass

ws = WebSocket(host,port, on_open=on_open, on_message=on_message, on_error=on_error, on_close=on_close)
"""
Interface example:

class WS(WebSocket):
    def on_open(self, client):
        print("Client connected:"+client)

    def on_message(self, message, client):
        for c in self.clients:
            if c.status is WebSocket.OPEN and c is not client:
                c.send("Message recieved: "+message+"\nFrom client"+client)

    def on_close(self, client):
        self.send(WebSocket.OTHER, "We lost a client: "+client)

ws = WS(host, port)

"""