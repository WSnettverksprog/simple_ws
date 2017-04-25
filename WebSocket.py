import asyncio

loop = asyncio.get_event_loop()


class Parser():
    def create_header(self):
        return "HTTP/1.1 200 OK\r\n\r\n"


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
        # loop.create_task(self.__send_periodic())
        loop.run_forever()

    async def __send_periodic(self):
        while True:
            await asyncio.sleep(1)
            for client in self.clients:
                client.sendBytes(str.encode("Ping"))
                client.close()

    def send_to_all(self, data):
        loop.create_task(self.__async_send_to_all(data))

    async def __async_send_to_all(self, data):
        for client in self.clients:
            client.sendBytes(data)

    async def __client_connected(self, reader, writer):
        client = Client(self, reader, writer)
        self.clients.append(client)
        if self.on_open is not None:
            self.on_open(self.clients)

    def disconnect(self, client):
        self.clients.remove(client)
        if self.on_close is not None:
            self.on_close(client)


class Client:
    parser = Parser()

    def __init__(self, server: WebSocket, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        self.server = server
        self.reader = reader
        self.writer = writer
        self.open = True

        # Test of sending
        self.sendString("Hei!")

        # Create async task to handle client data
        loop.create_task(self.__wait_for_data())

    def sendBytes(self, data):
        self.writer.write(data)

    def sendString(self, data):
        self.sendBytes(str.encode(data))

    def isOpen(self):
        return self.open

    def close(self):
        if not self.open:
            return

        self.open = False
        self.writer.close()
        self.server.disconnect(self)

    async def __wait_for_data(self):
        while self.open:
            data = await self.reader.readline()
            if len(data) == 0:
                self.close()
                return

            print(data.decode('utf-8'))
            if self.server.on_message:
                self.server.on_message(self.server.clients, data.decode('utf-8'))

                # Test code
                # self.server.send_to_all(data)


host = '0.0.0.0'
port = 8080


def on_open(clients):
    for client in clients:
        if client.isOpen():
            print(client)


def on_message(clients, msg):
    for client in clients:
        client.sendString("Vi mottok meldingen: " + msg)


ws = WebSocket(host, port, on_open=on_open, on_message=on_message)
