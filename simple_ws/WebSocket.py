import asyncio
import hashlib
import base64
import struct
import time
import zlib

loop = asyncio.get_event_loop()


class RequestParser:
    ws_const = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"

    def __init__(self, req=None):
        self.headers = {}
        self.body = ""
        if req is not None:
            self.parse_request(req)

    def parse_request(self, req):
        data = req.split("\r\n\r\n")
        headers = data[0]
        self.body = "\r\n\r\n".join(data[1:])
        for line in headers.split("\r\n"):
            try:
                header_line = line.split(":")
                if (len(header_line) < 2):
                    raise Exception
                key = header_line[0].strip()
                if key == "Sec-WebSocket-Extensions":
                    l = header_line[1].split(";")
                    extensions = list(map(lambda line: line.strip().lower(), l))
                    self.headers[key] = extensions
                self.headers[key] = ":".join(header_line[1:]).strip()

            except:
                if "GET" in line:
                    self.headers["HTTP"] = line.lower()
                else:
                    self.headers[line] = None

    def does_support_compression(self):
        try:
            extensions = self.headers["Sec-WebSocket-Extensions"]
            if "permessage-deflate" in extensions:
                return True
        except KeyError:
            pass
        return False

    def is_valid_request(self, header):
        try:
            assert "get" in header["HTTP"].lower()
            assert header["Host"] is not None
            assert header["Upgrade"].lower() == "websocket"
            assert header["Connection"].lower() == "upgrade"
            assert header["Sec-WebSocket-Key"] is not None
            assert int(header["Sec-WebSocket-Version"]) == 13
        except KeyError as e:
            raise AssertionError(str(e.args) + " is missing from upgrade request")
        return True

    @staticmethod
    def create_update_header(key, compression=False):
        const = RequestParser.ws_const
        m = hashlib.sha1()
        m.update(str.encode(key))
        m.update(str.encode(const))
        hashed = m.digest()
        key = base64.b64encode(hashed)
        header = "HTTP/1.1 101 Switching Protocols\r\n"
        header += "Upgrade: websocket\r\n"
        header += "Connection: Upgrade\r\n"
        if compression:
            header += "Sec-WebSocket-Extensions: permessage-deflate; client_max_window_bits=8\r\n"
        header += "Sec-WebSocket-Accept: " + key.decode("utf-8") + "\r\n\r\n"
        return header


class Decompressor:
    def __init__(self):

        self.decompressor = zlib.decompressobj(-zlib.MAX_WBITS)

    def decompress(self, message):
        message.extend(b'\x00\x00\xff\xff')
        decompressor = self.decompressor
        message = decompressor.decompress(message)
        return message


class Compressor:
    def __init__(self):
        self.compressor = zlib.compressobj(6, zlib.DEFLATED, -zlib.MAX_WBITS, 8)

    def compress(self, message):
        self.compressor.compress(message)

        message = self.compressor.flush(zlib.Z_SYNC_FLUSH)
        assert message.endswith(b'\x00\x00\xff\xff')
        return message[:-4]


class WebSocketFrame:
    # RFC-specific opcodes
    CONTINUOUS = 0x0
    TEXT = 0x1
    BINARY = 0x2
    CLOSE = 0x8
    PING = 0x9
    PONG = 0xA

    def has_mask(self):
        return self.mask is not None

    def __init__(self, opcode=TEXT, payload="", mask=None, raw_data=None, max_frame_size=8192, compression=False,
                 ignore_mask=False):

        self.opcode = opcode
        if opcode is WebSocketFrame.TEXT and payload:
            self.payload = str.encode(payload)
        else:
            self.payload = payload
        self.mask = mask
        self.incomplete_message = False
        self.frame_size = 0
        self.max_frame_size = max_frame_size
        self.__compression = compression
        self.compressor = Compressor()
        self.__ignore_mask = ignore_mask  # Used for unit test

        # Parse message if raw_data isn't None
        if raw_data is not None:
            self.__parse(raw_data)

    """
        Desc: Creates a list of frames with data to send
        Input:
            -  opcode: int: 0 = Continous message, 1 = Msg is text, 2 = Msg is binary, 8 = Close, 9 = ping, 10 = pong
            - fin: bool: True = last message, False = more messages to come
            - msg: data to be sendt
    """

    def construct(self):
        frames = []
        if self.__compression and self.payload:
            self.payload = self.compressor.compress(self.payload)

        l = len(self.payload)
        frame_num = 0
        while l >= 0:
            finbit = 128 if (l <= self.max_frame_size) else 0
            opcode = self.opcode if (frame_num is 0) else WebSocketFrame.CONTINUOUS
            start = self.max_frame_size * frame_num
            end = min(self.max_frame_size + start, l + start)
            payload = self.payload[start:end]
            frames.append(self.__make_frame(finbit, opcode, payload))
            frame_num += 1
            l -= self.max_frame_size

        return frames

    def __make_frame(self, finbit, opcode, payload):
        rsv1_compress = 0x0
        if self.__compression and (opcode is 0x0 or opcode is 0x1 or opcode is 0x2):
            rsv1_compress = 0x40

        frame = bytearray(struct.pack("B", opcode | finbit | rsv1_compress))
        l = len(payload)
        if l < 126:
            length = struct.pack("B", l)
        elif l < 65536:
            l_code = 126
            length = struct.pack("!BH", l_code, l)
        else:
            l_code = 127
            length = struct.pack("!BQ", l_code, l)

        frame.extend(length)
        frame.extend(payload)
        return frame

    def __unmask(self, bit_tuple):
        if self.__ignore_mask:
            return bit_tuple

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
        self.compressed = head & 0x40 == 0x40
        self.opcode = head & 0xF
        has_mask = payload_len & 0x80 == 0x80
        if not has_mask and not self.__ignore_mask:
            raise Exception("Frame without mask")

        l = payload_len & 0x7F

        try:
            if l < 126:
                if not self.__ignore_mask:
                    self.mask = struct.unpack_from("BBBB", raw_data, offset=offset)
                    offset += 4
                self.frame_size = l + offset
                self.payload = self.__unmask(struct.unpack_from("B" * l, raw_data, offset=offset))

            elif l == 126:
                l = struct.unpack_from("!H", raw_data, offset=offset)[0]
                offset += 2

                if not self.__ignore_mask:
                    self.mask = struct.unpack_from("BBBB", raw_data, offset=offset)
                    offset += 4

                self.frame_size = l + offset
                if l > len(raw_data) - offset:
                    self.incomplete_message = True
                    return
                self.incomplete_message = False
                self.payload = self.__unmask(struct.unpack_from("B" * l, raw_data, offset=offset))

            else:
                l = struct.unpack_from("!Q", raw_data, offset=offset)[0]
                offset += 8

                if not self.__ignore_mask:
                    self.mask = struct.unpack_from("BBBB", raw_data, offset=offset)
                    offset += 4

                self.frame_size = l + offset
                self.payload = self.__unmask(struct.unpack_from("B" * l, raw_data, offset=offset))

        except:
            raise Exception("Frame does not follow protocol")

            # if self.opcode == WebSocketFrame.TEXT:
            #    self.payload = self.payload.decode('utf-8')


class FrameReader:
    def __init__(self):
        self.current_message = bytearray()
        self.recieved_data = bytearray()
        self.opcode = -1
        self.frame_size = 0
        self.compressed = False
        self.messages = []
        self.decompresser = Decompressor()


    def read_message(self, data, compression=False):
        message_rest = bytearray()
        self.recieved_data.extend(data)

        if len(self.recieved_data) < self.frame_size:
            return []

        frame = WebSocketFrame(raw_data=self.recieved_data, compression=compression)
        self.frame_size = frame.frame_size
        if frame.incomplete_message:
            return []
        else:
            if len(self.recieved_data) > frame.frame_size:
                message_rest = self.recieved_data[frame.frame_size:]
            self.recieved_data = bytearray()

        if frame.opcode is not WebSocketFrame.CONTINUOUS:
            self.opcode = frame.opcode
            self.compressed = frame.compressed

        self.current_message.extend(frame.payload)
        if frame.fin:
            if compression and self.compressed:
                self.current_message = self.decompresser.decompress(self.current_message)
            out = (frame.opcode, self.current_message)
            self.messages.append(out)
            self.current_message = bytearray()
            self.recieved_data = bytearray()
            self.frame_size = 0
            if len(message_rest) > 0:
                return self.read_message(message_rest, compression=compression)
            else:
                messages = self.messages
                self.messages = []
                return messages
        return []


class WebSocket:
    def __init__(self, host, port, ping=True, ping_interval=5, buffer_size=8192, max_frame_size=8192,
                 max_connections=10, compression=True):
        self.clients = []
        self.host = host
        self.port = port

        self.ping = ping
        self.ping_interval = ping_interval
        self.buffer_size = buffer_size
        self.max_frame_size = max_frame_size
        self.compression = compression

        self.server = asyncio.start_server(client_connected_cb=self.__client_connected, host=host, port=port,
                                           loop=loop)
        loop.run_until_complete(self.server)
        loop.run_forever()

    async def __client_connected(self, reader, writer):
        client = Client(server=self, reader=reader, writer=writer, buffer_size=self.buffer_size)
        self.clients.append(client)

    def on_disconnect(self, client):
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

    def on_ping(self, client):
        # Runs when ping is sent
        return None

    def on_pong(self, client):
        # Runs when pong is received
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
        self.__frame_reader = FrameReader()
        self.__pong_received = False
        self.__last_frame_received = time.time()
        self.rec = 0

        # Create async task to handle client data
        loop.create_task(self.__wait_for_data())
        # Create async task to send pings
        if self.server.ping:
            loop.create_task(self.__send_ping())

    def __send_frames(self, frames):
        for f in frames:
            self.__send_bytes(f)

    def __send_bytes(self, data):
        self.writer.write(data)

    def write_message(self, msg, binary=False):
        opcode = WebSocketFrame.BINARY if binary else WebSocketFrame.TEXT
        frame = WebSocketFrame(opcode=opcode, payload=msg, max_frame_size=self.server.max_frame_size, compression=self.server.compression)
        self.__send_frames(frame.construct())

    def is_open(self):
        return self.status == Client.OPEN

    def __upgrade(self, key, compression=False):
        if self.status == Client.OPEN:
            return
        update_header = RequestParser.create_update_header(key, compression=compression)
        self.__send_bytes(str.encode(update_header))
        self.status = Client.OPEN
        self.server.on_open(self)

    def __close_socket(self):
        if self.status == Client.CLOSED:
            return

        self.status = Client.CLOSED
        self.writer.close()
        self.server.on_disconnect(self)

    async def __send_ping(self):
        # Sends ping if more than 5 seconds since last message received
        while self.status != Client.CLOSED:
            if (time.time() - self.__last_frame_received) * 1000 < 5000:
                await asyncio.sleep(self.server.ping_interval)
                continue
            self.__pong_received = False
            frame = WebSocketFrame(opcode=WebSocketFrame.PING)
            self.__send_frames(frame.construct())
            await asyncio.sleep(self.server.ping_interval)
            if not self.__pong_received:
                self.close(1002, "Pong not recieved")

    def __send_pong(self):
        frame = WebSocketFrame(opcode=WebSocketFrame.PONG, max_frame_size=self.server.max_frame_size)
        self.__send_frames(frame.construct())

    async def __wait_for_data(self):
        while self.status != Client.CLOSED:
            data = await self.reader.read(self.buffer_size)
            if len(data) == 0:
                self.__close_socket()
                return

            if self.status == Client.CONNECTING:
                req = RequestParser()
                try:
                    data = data.decode('utf-8')
                    req.parse_request(data)
                except Exception as e:
                    raise UnicodeDecodeError(
                        "Error when decoding upgrade request to unicode ( " + str(e) + " )") from None

                try:
                    req.is_valid_request(req.headers)
                    if self.server.compression and req.does_support_compression():
                        self.server.compression = True
                        self.__upgrade(req.headers["Sec-WebSocket-Key"], compression=True)
                    else:
                        self.server.compression = False
                        self.__upgrade(req.headers["Sec-WebSocket-Key"])

                except AssertionError as a:
                    self.__close_socket()
                    raise Exception("Upgrade request does not follow protocol ( " + str(a) + " )") from None

            elif self.status == Client.OPEN:
                try:
                    messages = self.__frame_reader.read_message(data, compression=self.server.compression)
                    for data in messages:
                        self.__process_frame(data[0], data[1])
                except Exception as e:
                    self.close(1002, "Received invalid frame")
                    raise Exception("Invalid frame received, closing connection (" + str(e) + ")")

            else:
                raise Exception("Recieved message from client who was not open or connecting")

    def __process_frame(self, opcode, message):
        self.__last_frame_received = time.time()
        if opcode <= WebSocketFrame.CONTINUOUS:
            return
        elif opcode == WebSocketFrame.TEXT:
            message = message.decode('utf-8')
            self.server.on_message(message, self)
        elif opcode == WebSocketFrame.BINARY:
            self.server.on_message(message, self)
        elif opcode == WebSocketFrame.CLOSE:
            self.__close_received = True
            self.__close_conn_res()
        elif opcode == WebSocketFrame.PING:
            self.__send_pong()
            self.server.on_ping(self)
        elif opcode == WebSocketFrame.PONG:
            self.__pong_received = True
            self.server.on_pong(self)

    # Call this class every time close frame is sent or recieved
    # Checks if client has requested closing, if so sends a closing frame and closes connection
    # If close frame is sent and recieved
    async def __async_force_close(self, timeout):
        await asyncio.sleep(timeout)
        if not self.__close_received:
            self.__close_socket()

    def __force_close(self, timeout):
        loop.create_task(self.__async_force_close(timeout))

    # Call this class to respond to a close connection request
    def __close_conn_res(self):
        if not self._close_sent:
            frame = WebSocketFrame(opcode=WebSocketFrame.CLOSE, max_frame_size=self.server.max_frame_size)
            self.__send_frames(frame.construct())
            self._close_sent = True
            self.__close_socket()
        else:
            self.__close_socket()

    # Call class to request closing of connection to client
    def close(self, status, reason):
        # Status and reason not implemented
        if not self._close_sent:
            frame = WebSocketFrame(opcode=WebSocketFrame.CLOSE, max_frame_size=self.server.max_frame_size)
            self.__send_frames(frame.construct())
            self.__force_close(1)
