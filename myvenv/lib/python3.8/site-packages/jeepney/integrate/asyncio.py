import asyncio

from jeepney.auth import SASLParser, make_auth_external, BEGIN, AuthenticationError
from jeepney.bus import get_bus
from jeepney.low_level import Parser, MessageType
from jeepney.wrappers import ProxyBase
from jeepney.routing import Router
from jeepney.bus_messages import message_bus

class DBusProtocol(asyncio.Protocol):
    def __init__(self):
        self.auth_parser = SASLParser()
        self.parser = Parser()
        self.router = Router(asyncio.Future)
        self.authentication = asyncio.Future()
        self.unique_name = None

    def connection_made(self, transport):
        self.transport = transport
        self.transport.write(b'\0' + make_auth_external())

    def _authenticated(self):
        self.transport.write(BEGIN)
        self.authentication.set_result(True)
        self.data_received = self.data_received_post_auth
        self.data_received(self.auth_parser.buffer)

    def data_received(self, data):
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
        self.transport.write(data)
        return future

class Proxy(ProxyBase):
    def __init__(self, msggen, protocol):
        super().__init__(msggen)
        self._protocol = protocol

    def __repr__(self):
        return 'Proxy({}, {})'.format(self._msggen, self._protocol)

    def _method_call(self, make_msg):
        def inner(*args, **kwargs):
            msg = make_msg(*args, **kwargs)
            assert msg.header.message_type is MessageType.method_call
            return self._protocol.send_message(msg)

        return inner


async def connect_and_authenticate(bus='SESSION', loop=None):
    if loop is None:
        loop = asyncio.get_event_loop()
    (t, p) = await loop.create_unix_connection(DBusProtocol, path=get_bus(bus))
    await p.authentication
    bus = Proxy(message_bus, p)
    hello_reply = await bus.Hello()
    p.unique_name = hello_reply[0]
    return (t, p)
