import base64
import io
from urllib.parse import quote, urlencode

import qrcode
from qrcode.image.svg import SvgPathImage

from ...utils import totp_digits


def get_otpauth_url(accountname, secret, issuer=None, digits=None):
    assert isinstance(secret, bytes), 'bytes secret expected'

    # For a complete run-through of all the parameters, have a look at the
    # specs at:
    # https://github.com/google/google-authenticator/wiki/Key-Uri-Format

    # quote and urlencode work best with bytes, not unicode strings.
    accountname = accountname.encode('utf8')
    issuer = issuer.encode('utf8') if issuer else None

    label = quote(b': '.join([issuer, accountname]) if issuer else accountname)

    # Ensure that the secret parameter is the FIRST parameter of the URI, this
    # allows Microsoft Authenticator to work.
    query = [
        ('secret', base64.b32encode(secret).decode('utf-8')),
        ('digits', digits or totp_digits())
    ]

    if issuer:
        query.append(('issuer', issuer))

    return 'otpauth://totp/%s?%s' % (label, urlencode(query))


def get_otpauth_qrcode_image(accountname, secret, issuer=None, digits=None):
    otpauth_url = get_otpauth_url(accountname=accountname, secret=secret, issuer=issuer, digits=digits)
    print(otpauth_url)
    return qrcode.make(otpauth_url, image_factory=SvgPathImage)


def get_otpauth_qrcode_image_uri(accountname, secret, issuer=None, digits=None):
    image = get_otpauth_qrcode_image(accountname, secret, issuer, digits)
    stream = io.BytesIO()
    image.save(stream)
    stream.seek(0)
    return 'data:image/svg+xml;base64,' + base64.b64encode(stream.read()).decode('ascii')
