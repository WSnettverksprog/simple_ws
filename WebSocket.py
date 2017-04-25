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

#Vet ikke hvordan brukere er implementert, men i implementasjonen under, har jeg lagt til en del av det jeg trenger
class WebSocketUser():
    def __init__(self, id, socket):
        self.id = id
        self.socket = socket
        self.headers = []
        self.handshake = False
        self.handling_partial_packet = False
        self.partial_buffer = ""
        self.sending_continuous = False
        self.partial_message = ""
        self.has_sent_close = False



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


    def __frame(self, message, user, message_type='text', message_continues=False):

        #Setting opcode
        b1 = {
            'continuous': 0,
            'text': 0 if user.sending_continuous else 1,
            'binary': 0 if user.sending_continuous else 2,
            'close': 8,
            'ping': 9,
            'pong': 10,
        }[message_type]

        if message_continues:
            user.sending_continuous = True
        else:
            b1 += 128
            user.sending_continuous = False

        length = len(message)
        length_field = ''
        if length < 126:
            b2 = length
        elif length < 65536:
            b2 = 126
            hex_length = hex(length)
            if len(hex_length)%2 == 1:
                hex_length = '0' + hex_length
            n = len(hex_length) - 2

            for i in range(n, 0, -2):
                length_field = chr(int(hex_length[i:2],16)) + length_field
            while len(length_field) < 2:
                length_field = chr(0) + length_field
        else:
            b2 = 127
            hex_length = hex(length)
            if len(hex_length) % 2 == 1:
                hex_length = '0' + hex_length
            n = len(hex_length) - 2

            for i in range(n, 0, -2):
                length_field = chr(int(hex_length[i:2],16)) + length_field
            while len(length_field) < 8:
                length_field = chr(0) + length_field

        return chr(b1) + chr(b2) + length_field + message


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
