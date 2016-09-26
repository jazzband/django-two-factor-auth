from django.conf import settings
from django_otp import devices_for_user

from two_factor.models import PhoneDevice

try:
    from urllib.parse import quote, urlencode
except ImportError:
    from urllib import quote, urlencode


def default_device(user):
    if not user or user.is_anonymous():
        return
    for device in devices_for_user(user):
        if device.name == 'default':
            return device


def backup_phones(user):
    if not user or user.is_anonymous():
        return PhoneDevice.objects.none()
    return user.phonedevice_set.filter(name='backup')


def get_otpauth_url(accountname, secret, issuer=None, digits=None):
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
        ('secret', secret),
        ('digits', digits or totp_digits())
    ]

    if issuer:
        query.append(('issuer', issuer))

    return 'otpauth://totp/%s?%s' % (label, urlencode(query))


def totp_digits():
    """
    Returns the number of digits (as configured by the TWO_FACTOR_TOTP_DIGITS setting)
    for totp tokens. Defaults to 6
    """
    return getattr(settings, 'TWO_FACTOR_TOTP_DIGITS', 6)
