import asyncio
import hashlib
import base64
import struct
import math
import time
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
    def __init__(self, host, port, buffer_size=4096, max_connections=10):
        self.clients = []
        self.host = host
        self.port = port

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

    def disconnect(self, client):
        self.clients.remove(client)
        self.on_close(client)

    def on_open(self, client):
        #Override to handle connections on open
        return None
    def on_message(self, msg, client):
        #Override to handle messages from client
        return None
    def on_error(self, err, client):
        #Override to handle error
        return None
    def on_close(self, client):
        #Override to handle closing of client
        return None


class Client:
    CONNECTING = 0
    OPEN = 1
    CLOSED = 2

    #RFC-specific opcodes
    _continuous = 0x0
    _text = 0x1
    _binary = 0x2
    _close = 0x8
    _ping = 0x9
    _pong = 0xA


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
        self._close_sent = False
        self._close_rec = False

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

    """
        Desc: Creates a frame with data to send
        Input:
            -  opcode: int: 0 = Continous message, 1 = Msg is text, 2 = Msg is binary, 8 = Close, 9 = ping, 10 = pong
            - fin: bool: True = last message, False = more messages to come
            - msg: data to be sendt
    """
    def _frame(self, opcode, fin, msg):
        msg = str.encode(msg)
        l = len(msg)
        if(fin):
            finbit = 128
        else:
            finbit = 0
        frame = struct.pack("B", opcode | finbit)
        print(frame)
        if l < 126:
            length = struct.pack("B", l)
        elif l < 65536:
            l_code = 126
            length = struct.pack("!BH", l_code, l)
        else:
            l_code = 127
            length = struct.pack("!BQ", l_code, l)

        frame += length
        frame += msg
        return frame


    def write_message(self, msg, binary=False):
        """  if binary:
            msg_type = "binary"
        else:
            msg_type = "text"
        """
        data = self._frame(1, True, msg)
        self.send_bytes(data)

    def unmask(self, mask, bit_tuple):
        res = []
        c = 0
        for byte in bit_tuple:
            res.append(byte ^ mask[c % 4])
            c += 1
        return ''.join([chr(x) for x in res])
        #return bytes(res).decode()


    def _rec_frame(self, msg):
        offset = 0
        head, payload_len = struct.unpack_from("BB", msg)
        offset += 2
        fin = head & 0x80 == 0x80
        opcode = head & 0xF
        if opcode is Client._close:
            self._close_rec = True
            print(self._close_rec)
        has_mask = payload_len & 0x80 == 0x80
        l = payload_len & 0x7F
        if not has_mask:
            self.close()
            raise Exception("Unmasked message sent from client, abort connection")
        if l < 126:
            mask = struct.unpack_from("BBBB", msg, offset=offset)
            offset += 4
            try:
                return self.unmask(mask, struct.unpack_from("B"*l, msg, offset=offset))
            except:
                self.close()
                raise Exception("Message does not follow protocol, abort connection")

        elif l < 65536:
            l = struct.unpack_from("!H", msg, offset=offset)
            offset += 2
            mask = struct.unpack_from("BBBB", msg, offset=offset)
            offset += 4
            try:
                return self.unmask(mask, struct.unpack_from("B"*int(l[0]), msg, offset=offset))
            except:
                self.close()
                raise Exception("Message does not follow protocol, abort connection")

        else:
            l = struct.unpack_from("!Q", msg, offset=offset)
            offset += 8
            mask = struct.unpack_from("BBBB", msg, offset=offset)
            offset += 4
            try:
                return self.unmask(mask, struct.unpack_from("B"*int(l[0]), msg, offset=offset))
            except:
                self.close()
                raise Exception("Message does not follow protocol, abort connection")


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
        if self.server.on_open:
            self.server.on_open(self.server)

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

            if self.status == Client.CONNECTING:
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
            elif self.status == Client.OPEN:
                msg = self._rec_frame(data)
                self.server.on_message(msg, self)
                if self._close_rec:
                    self._close_conn_res()

            else:
                raise Exception("Recieved message from client who was not open or connecting")


    async def _async_force_close(self, timeout):
        await asyncio.sleep(timeout)
        if not self._close_rec:
            self.close()

    def _force_close(self,timeout):
        loop.create_task(self._async_force_close(timeout))

    #Call this class to respond to a close connection request
    def _close_conn_res(self):
        if not self._close_sent:
            data = self._frame(Client._close, True, "")
            self.send_bytes(data)
            self._close_sent = True
            self.close()
        else:
            self.close()

    #Call class to request closing of connection to client
    def _close_conn_req(self, status, reason):
        #Status and reason not implemented
        if not self._close_sent:
            data = self._frame(Client._close, True, "")
            self.send_bytes(data)
            self._force_close(1)











class WSHandler(WebSocket):

    def on_message(self, msg, client):
        for c in self.clients:
            if c.status == c.is_open():
                c.write_message(msg)

    def on_open(self, client):
        print("Client connected!")

    def on_close(self, client):
        print("Client left...")


host = '0.0.0.0'
port = 8080

ws = WSHandler(host,port)

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
