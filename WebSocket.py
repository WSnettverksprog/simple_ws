import asyncio
import hashlib
import base64

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
        header += "Sec-WebSocket-Accept: " + code.decode("utf-8") + "\r\n\r\n"
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
            client.sendBytes(data)

    async def __client_connected(self, reader, writer):
        client = Client(server=self, reader=reader, writer=writer, buffer_size=self.buffer_size)
        self.clients.append(client)
        if self.on_open is not None:
            self.on_open(self.clients)

    def disconnect(self, client):
        self.clients.remove(client)
        if self.on_close is not None:
            self.on_close(client)


class Client:
    CONNECTING = 0
    OPEN = 1
    CLOSED = 2
    parser = RequestParser()

    def __init__(self, server: WebSocket, reader: asyncio.StreamReader, writer: asyncio.StreamWriter, buffer_size: int):
        self.server = server
        self.reader = reader
        self.writer = writer
        self.buffer_size = buffer_size
        self.status = Client.CONNECTING

        # Create async task to handle client data
        loop.create_task(self.__wait_for_data())

    def sendBytes(self, data):
        self.writer.write(data)

    def sendString(self, data):
        self.sendBytes(str.encode(data))

    def isOpen(self):
        return Client.OPEN == self.status

    def upgrade(self, header):
        code = header["Sec-WebSocket-Key"]
        updateHeader = RequestParser.create_update_header(code)
        print(str.encode(updateHeader))
        self.sendString(updateHeader)
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
            req.parse_request(data.decode('utf-8'))
            print(req.headers)
            try:
                if (req.headers["Upgrade"] == "websocket" and req.headers["Connection"] == "Upgrade" and req.headers[
                    "Sec-WebSocket-Key"] is not None):
                    self.upgrade(req.headers)
            except KeyError:
                print("UNRECOGNIZED REQ")
                print(req.headers)

            if self.server.on_message:
                self.server.on_message(self.server.clients, data.decode('utf-8'))


host = '0.0.0.0'
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

<<<<<<< HEAD

def on_message(clients, msg):
    for client in clients:
        client.sendString("Vi mottok meldingen: " + msg)


ws = WebSocket(host, port, on_open=on_open, on_message=on_message)
=======
ws = WS(host, port)

"""
