import socket
from tornado.concurrent import Future
from tornado.gen import coroutine
from tornado.ioloop import IOLoop
from tornado.iostream import IOStream

from jeepney.auth import SASLParser, make_auth_external, BEGIN, AuthenticationError
from jeepney.bus import get_bus
from jeepney.low_level import Parser, MessageType
from jeepney.wrappers import ProxyBase
from jeepney.routing import Router
from jeepney.bus_messages import message_bus

class DBusConnection:
    def __init__(self, bus_addr):
        self.auth_parser = SASLParser()
        self.parser = Parser()
        self.router = Router(Future)
        self.authentication = Future()
        self.unique_name = None

        self._sock = socket.socket(family=socket.AF_UNIX)
        self.stream = IOStream(self._sock, read_chunk_size=4096)

        def connected():
            self.stream.write(b'\0' + make_auth_external())

        self.stream.connect(bus_addr, connected)
        self.stream.read_until_close(streaming_callback=self.data_received)

    def _authenticated(self):
        self.stream.write(BEGIN)
        self.authentication.set_result(True)
        self.data_received_post_auth(self.auth_parser.buffer)

    def data_received(self, data):
        if self.authentication.done():
            return self.data_received_post_auth(data)

        self.auth_parser.feed(data)
        if self.auth_parser.authenticated:
            self._authenticated()
        elif self.auth_parser.error:
            self.authentication.set_exception(AuthenticationError(self.auth_parser.error))

    def data_received_post_auth(self, data):
        for msg in self.parser.feed(data):
            self.router.incoming(msg)

    def send_message(self, message):
        if not self.authentication.done():
            raise RuntimeError("Wait for authentication before sending messages")

        future = self.router.outgoing(message)
        data = message.serialise()
        self.stream.write(data)
        return future

class Proxy(ProxyBase):
    def __init__(self, msggen, connection):
        super().__init__(msggen)
        self._connection = connection

    def __repr__(self):
        return 'Proxy({}, {})'.format(self._msggen, self._connection)

    def _method_call(self, make_msg):
        def inner(*args, **kwargs):
            msg = make_msg(*args, **kwargs)
            assert msg.header.message_type is MessageType.method_call
            return self._connection.send_message(msg)

        return inner


@coroutine
def connect_and_authenticate(bus='SESSION'):
    bus_addr = get_bus(bus)
    conn = DBusConnection(bus_addr)
    yield conn.authentication
    conn.unique_name = (yield Proxy(message_bus, conn).Hello())[0]
    return conn

if __name__ == '__main__':
    conn = IOLoop.current().run_sync(connect_and_authenticate)
    print("Unique name is:", conn.unique_name)
