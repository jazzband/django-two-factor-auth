from binascii import hexlify
import os

def make_auth_external():
    hex_uid = hexlify(str(os.geteuid()).encode('ascii'))
    return b'AUTH EXTERNAL %b\r\n' % hex_uid

def make_auth_anonymous():
    """Format an AUTH command line for the ANONYMOUS mechanism

    Jeepney's higher-level wrappers don't currently use this mechanism,
    but third-party code may choose to.

    See <https://tools.ietf.org/html/rfc4505> for details.
    """
    from . import __version__
    trace = hexlify(('Jeepney %s' % __version__).encode('ascii'))
    return b'AUTH ANONYMOUS %s\r\n' % trace

BEGIN = b'BEGIN\r\n'

class AuthenticationError(ValueError):
    """Raised when DBus authentication fails"""
    def __init__(self, data):
        self.data = data

    def __str__(self):
        return "Authentication failed. Bus sent: %r" % self.data

class SASLParser:
    def __init__(self):
        self.buffer = b''
        self.authenticated = False
        self.error = None

    def process_line(self, line):
        if line.startswith(b'OK '):
            self.authenticated = True
        else:
            self.error = line

    def feed(self, data):
        self.buffer += data
        while (b'\r\n' in self.buffer) and not self.authenticated:
            line, self.buffer = self.buffer.split(b'\r\n', 1)
            self.process_line(line)
