"""Synchronous IO wrappers around jeepney
"""
from errno import ECONNRESET
import functools
import os
import socket

from jeepney.auth import SASLParser, make_auth_external, BEGIN, AuthenticationError
from jeepney.bus import get_bus
from jeepney.low_level import Parser, MessageType
from jeepney.wrappers import ProxyBase
from jeepney.routing import Router
from jeepney.bus_messages import message_bus


class _Future:
    def __init__(self):
        self._result = None

    def done(self):
        return bool(self._result)

    def set_exception(self, exception):
        self._result = (False, exception)

    def set_result(self, result): 
        self._result = (True, result)

    def result(self):
        success, value = self._result
        if success:
            return value
        raise value


class DBusConnection:
    def __init__(self, sock):
        self.sock = sock
        self.parser = Parser()
        self.router = Router(_Future)
        self.bus_proxy = Proxy(message_bus, self)
        hello_reply = self.bus_proxy.Hello()
        self.unique_name = hello_reply[0]

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False

    def send_message(self, message):
        future = self.router.outgoing(message)
        data = message.serialise()
        self.sock.sendall(data)
        return future

    def recv_messages(self):
        """Read data from the socket and handle incoming messages.
        
        Blocks until at least one message has been read.
        """
        while True:
            b = unwrap_read(self.sock.recv(4096))
            msgs = self.parser.feed(b)
            if msgs:
                for msg in msgs:
                    self.router.incoming(msg)
                return

    def send_and_get_reply(self, message):
        """Send a message, wait for the reply and return it.
        """
        future = self.send_message(message)
        while not future.done():
            self.recv_messages()

        return future.result()

    def close(self):
        self.sock.close()

class Proxy(ProxyBase):
    def __init__(self, msggen, connection):
        super().__init__(msggen)
        self._connection = connection

    def __repr__(self):
        return "Proxy({}, {})".format(self._msggen, self._connection)

    def _method_call(self, make_msg):
        @functools.wraps(make_msg)
        def inner(*args, **kwargs):
            msg = make_msg(*args, **kwargs)
            assert msg.header.message_type is MessageType.method_call
            return self._connection.send_and_get_reply(msg)

        return inner


def unwrap_read(b):
    """Raise ConnectionResetError from an empty read.

    Sometimes the socket raises an error itself, sometimes it gives no data.
    I haven't worked out when it behaves each way.
    """
    if not b:
        raise ConnectionResetError(ECONNRESET, os.strerror(ECONNRESET))
    return b


def connect_and_authenticate(bus='SESSION'):
    bus_addr = get_bus(bus)
    sock = socket.socket(family=socket.AF_UNIX)
    sock.connect(bus_addr)
    sock.sendall(b'\0' + make_auth_external())
    auth_parser = SASLParser()
    while not auth_parser.authenticated:
        auth_parser.feed(unwrap_read(sock.recv(1024)))
        if auth_parser.error:
            raise AuthenticationError(auth_parser.error)

    sock.sendall(BEGIN)

    conn = DBusConnection(sock)
    conn.parser.buf = auth_parser.buffer
    return conn

if __name__ == '__main__':
    conn = connect_and_authenticate()
    print("Unique name:", conn.unique_name)
