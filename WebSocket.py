import asyncio
import hashlib
import base64
import struct
import math
import time

loop = asyncio.get_event_loop()


class WebRequestParser():
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
        const = WebRequestParser.ws_const
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


class WebSocketFrame():
    # RFC-specific opcodes
    CONTINUOUS = 0x0
    TEXT = 0x1
    BINARY = 0x2
    CLOSE = 0x8
    PING = 0x9
    PONG = 0xA

    def has_mask(self):
        return self.mask is not None

    def __init__(self, opcode=TEXT, fin=True, payload=None, mask=None, raw_data=None):
        self.fin = fin
        self.opcode = opcode
        self.payload = payload
        self.mask = mask

        # Parse message if raw_data isn't None
        if raw_data is not None:
            self.__parse(raw_data)

    """
        Desc: Creates a frame with data to send
        Input:
            -  opcode: int: 0 = Continous message, 1 = Msg is text, 2 = Msg is binary, 8 = Close, 9 = ping, 10 = pong
            - fin: bool: True = last message, False = more messages to come
            - msg: data to be sendt
    """

    def construct(self):
        l = len(self.payload)
        if self.fin:
            finbit = 128
        else:
            finbit = 0
        frame = struct.pack("B", self.opcode | finbit)
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
        frame += str.encode(self.payload)
        return frame

    def __unmask(self, bit_tuple):
        res = []
        c = 0
        for byte in bit_tuple:
            res.append(byte ^ self.mask[c % 4])
            c += 1
        return bytes(res)
        # return bytes(res).decode()

    def __parse(self, raw_data):
        offset = 0
        head, payload_len = struct.unpack_from("BB", raw_data)
        offset += 2
        self.fin = head & 0x80 == 0x80
        self.opcode = head & 0xF

        has_mask = payload_len & 0x80 == 0x80
        if not has_mask:
            raise Exception("Frame without mask")

        l = payload_len & 0x7F

        try:
            if l < 126:
                self.mask = struct.unpack_from("BBBB", raw_data, offset=offset)
                offset += 4
                self.payload = self.__unmask(struct.unpack_from("B" * l, raw_data, offset=offset))

            elif l < 65536:
                l = struct.unpack_from("!H", raw_data, offset=offset)
                offset += 2
                self.mask = struct.unpack_from("BBBB", raw_data, offset=offset)
                offset += 4
                self.payload = self.__unmask(struct.unpack_from("B" * int(l[0]), raw_data, offset=offset))

            else:
                l = struct.unpack_from("!Q", raw_data, offset=offset)
                offset += 8
                self.mask = struct.unpack_from("BBBB", raw_data, offset=offset)
                offset += 4
                self.payload = self.__unmask(struct.unpack_from("B" * int(l[0]), raw_data, offset=offset))

        except:
            raise Exception("Frame does not follow protocol")

        if self.opcode == WebSocketFrame.TEXT:
            self.payload = self.payload.decode('utf-8')


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
        # Override to handle connections on open
        return None

    def on_message(self, msg, client):
        # Override to handle messages from client
        return None

    def on_error(self, err, client):
        # Override to handle error
        return None

    def on_close(self, client):
        # Override to handle closing of client
        return None


class Client:
    CONNECTING = 0
    OPEN = 1
    CLOSED = 2

    def __init__(self, server: WebSocket, reader: asyncio.StreamReader, writer: asyncio.StreamWriter, buffer_size: int):
        self.server = server
        self.reader = reader
        self.writer = writer
        self.buffer_size = buffer_size
        self.status = Client.CONNECTING
        self.sending_continuous = False
        self._close_sent = False
        self.__close_received = False

        # Create async task to handle client data
        loop.create_task(self.__wait_for_data())

    def send_bytes(self, data):
        print(data)
        self.writer.write(data)

    # TODO: Binary
    def write_message(self, msg, binary=False):
        """  if binary:
            msg_type = "binary"
        else:
            msg_type = "text"
        """
        frame = WebSocketFrame(opcode=WebSocketFrame.TEXT, fin=True, payload=msg)
        self.send_bytes(frame.construct())

    def send_string(self, data):
        self.send_bytes(str.encode(data))

    def is_open(self):
        return Client.OPEN == self.status

    def upgrade(self, key):
        if self.status == Client.OPEN:
            return
        update_header = WebRequestParser.create_update_header(key)
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
                req = WebRequestParser()
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
                try:
                    frame = WebSocketFrame(raw_data=data)
                    self.__process_frame(frame)
                except Exception as e:
                    print("Invalid frame received, closing connection (" + str(e) + ")")
                    self.close()
                    return
            else:
                raise Exception("Recieved message from client who was not open or connecting")

    def __process_frame(self, frame):
        if frame.opcode == WebSocketFrame.CONTINUOUS:
            pass  # TODO: Continuous
        elif frame.opcode == WebSocketFrame.TEXT:
            self.server.on_message(frame.payload, self)
        elif frame.opcode == WebSocketFrame.BINARY:
            self.server.on_message(frame.payload, self)
        elif frame.opcode == WebSocketFrame.CLOSE:
            self.__close_received = True
            self.__close_conn_res()
        elif frame.opcode == WebSocketFrame.PING:
            pass  # TODO: Ping
        elif frame.opcode == WebSocketFrame.PONG:
            pass  # TODO: Ping

    # Call this class every time close frame is sent or recieved
    # Checks if client has requested closing, if so sends a closing frame and closes connection
    # If close frame is sent and recieved
    async def __async_force_close(self, timeout):
        await asyncio.sleep(timeout)
        if not self.__close_received:
            self.close()

    def __force_close(self, timeout):
        loop.create_task(self.__async_force_close(timeout))

    def __close_conn_res(self):
        if not self._close_sent:
            frame = WebSocketFrame(opcode=WebSocketFrame.CLOSE, fin=True, payload="")
            self.send_bytes(frame.construct())
            self._close_sent = True
            self.close()
        else:
            self.close()

    def __close_conn_req(self, status, reason):
        # Status and reason not implemented
        if not self._close_sent:
            frame = WebSocketFrame(opcode=WebSocketFrame.CLOSE, fin=True, payload="")
            self.send_bytes(frame.construct())
            self.__force_close(1)


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

ws = WSHandler(host, port)
