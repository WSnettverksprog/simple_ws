import asyncio
import hashlib
import base64
import time
import struct
loop = asyncio.get_event_loop()


class RequestParser():
    ws_const = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"

    def __init__(self, req=None):
        self.headers = {}
        self.body = ""
        if req is not None:
            self.parse_request(req)

    def parse_request(self, req):
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
    def create_update_header(key):
        const = RequestParser.ws_const
        m = hashlib.sha1()
        m.update(str.encode(key))
        m.update(str.encode(const))
        hashed = m.digest()
        key = base64.b64encode(hashed)
        header = "HTTP/1.1 101 Switching Protocols\r\n"
        header += "Upgrade: websocket\r\n"
        header += "Connection: Upgrade\r\n"
        header += "Sec-WebSocket-Accept: " + key.decode("utf-8") + "\r\n\r\n"
        return header


class WebSocket:
    def __init__(self, host, port, on_open=None, on_message=None,
                 on_error=None, on_close=None, buffer_size=4096, max_connections=10):
        self.clients = []
        self.host = host
        self.port = port
        self.on_open = on_open
        self.on_message = on_message
        self.on_error = on_error
        self.on_close = on_close

        # Not currently used
        self.max_connections = max_connections
        self.buffer_size = buffer_size

        self.server = asyncio.start_server(client_connected_cb=self.__client_connected, host=host, port=port,
                                           loop=loop)
        loop.run_until_complete(self.server)
        loop.run_forever()

    def send_to_all(self, data):
        loop.create_task(self.__async_send_to_all(data))

    async def __async_send_to_all(self, data):
        for client in self.clients:
            client.send_bytes(data)

    async def __client_connected(self, reader, writer):
        client = Client(server=self, reader=reader, writer=writer, buffer_size=self.buffer_size)
        self.clients.append(client)
        if self.on_open is not None:
            self.on_open(self)


    def disconnect(self, client):
        self.clients.remove(client)
        if self.on_close is not None:
            self.on_close(client)


class Client:
    CONNECTING = 0
    OPEN = 1
    CLOSED = 2

    """
        Ole trenger:

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


    """
    def __init__(self, server: WebSocket, reader: asyncio.StreamReader, writer: asyncio.StreamWriter, buffer_size: int):
        self.server = server
        self.reader = reader
        self.writer = writer
        self.buffer_size = buffer_size
        self.status = Client.CONNECTING
        self.sending_continuous = False

        # Create async task to handle client data
        loop.create_task(self.__wait_for_data())

    def send_bytes(self, data):
        print(data)
        self.writer.write(data)

    def __frame(self, message, message_type='text', message_continues=False):

        #Setting opcode
        b1 = {
            'continuous': 0,
            'text': 0 if self.sending_continuous else 1,
            'binary': 0 if self.sending_continuous else 2,
            'close': 8,
            'ping': 9,
            'pong': 10,
        }[message_type]

        if message_continues:
            self.sending_continuous = True
        else:
            b1 += 128
            self.sending_continuous = False

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

    def _frame(self, msg):
        # if final frame = struct.pack("B", 128 | 0x1 | 0)
        frame = struct.pack("B", 1 | 128)
        l = len(msg)
        frame += struct.pack("B", l | 0)
        frame += str.encode(msg)
        return frame


    def write_message(self, msg, binary=False):
        """  if binary:
            msg_type = "binary"
        else:
            msg_type = "text"
        """
        data = self._frame(msg)
        self.send_bytes(data)


    def send_string(self, data):
        self.send_bytes(str.encode(data))

    def is_open(self):
        return Client.OPEN == self.status

    def upgrade(self, key):
        if self.status == Client.OPEN:
            return
        update_header = RequestParser.create_update_header(key)
        self.send_string(update_header)
        self.status = Client.OPEN

    def close(self):
        if self.status == Client.CLOSED:
            return

        self.status = Client.CLOSED
        self.writer.close()
        self.server.disconnect(self)

    async def __wait_for_data(self):
        while self.status != Client.CLOSED:
            data = await self.reader.read(self.buffer_size)
            if len(data) == 0:
                self.close()
                return

            # print(data.decode('utf-8'))
            req = RequestParser()
            try:
                data = data.decode('utf-8')
                req.parse_request(data)
            except (AttributeError, UnicodeDecodeError):
                break

            try:
                if req.headers["Upgrade"].lower() == "websocket" and req.headers["Connection"].lower() == "upgrade":
                    self.upgrade(req.headers["Sec-WebSocket-Key"])
            except KeyError:
                print("UNRECOGNIZED REQ")
                print(req.headers)

     #       if self.server.on_message:
#                self.server.on_message(self.server.clients, data.decode('utf-8'))


host = '0.0.0.0'
port = 8080

def on_open(ws):
    for c in ws.clients:
        if c.is_open():
            c.write_message("Nå har vi fått en ny klient!!")

def on_message(msg, clients):
    pass

def on_error(err, clients):
    pass

def on_close(clients):
    pass

ws = WebSocket(host,port, on_open=on_open, on_message=on_message, on_error=on_error, on_close=on_close)

""""
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

    def on_message(clients, msg):
        for client in clients:
            client.sendString("Vi mottok meldingen: " + msg)

ws = WS(host, port)

"""
