from __future__ import absolute_import, division, unicode_literals

import logging
from binascii import unhexlify

from django.conf import settings
from django.db import models
from django.utils.translation import ugettext_lazy as _
from django_otp.models import Device
from django_otp.oath import totp
from django_otp.util import hex_validator, random_hex
from otp_yubikey.models import RemoteYubikeyDevice
from phonenumber_field.modelfields import PhoneNumberField

from .gateways import make_call, send_sms

try:
    import yubiotp
except ImportError:
    yubiotp = None


logger = logging.getLogger(__name__)

PHONE_METHODS = (
    ('call', _('Phone Call')),
    ('sms', _('Text Message')),
)


def get_available_phone_methods():
    methods = []
    if getattr(settings, 'TWO_FACTOR_CALL_GATEWAY', None):
        methods.append(('call', _('Phone call')))
    if getattr(settings, 'TWO_FACTOR_SMS_GATEWAY', None):
        methods.append(('sms', _('Text message')))
    return methods


def get_available_yubikey_methods():
    methods = []
    if yubiotp and 'otp_yubikey' in settings.INSTALLED_APPS:
        methods.append(('yubikey', _('YubiKey')))
    return methods


def get_available_methods():
    methods = [('generator', _('Token generator'))]
    methods.extend(get_available_phone_methods())
    methods.extend(get_available_yubikey_methods())
    return methods


def key_validator(*args, **kwargs):
    """Wraps hex_validator generator, to keep makemigrations happy."""
    return hex_validator()(*args, **kwargs)


class PhoneDevice(Device):
    """
    Model with phone number and token seed linked to a user.
    """
    class Meta:
        app_label = 'two_factor'

    number = PhoneNumberField()
    key = models.CharField(max_length=40,
                           validators=[key_validator],
                           default=random_hex,
                           help_text="Hex-encoded secret key")
    method = models.CharField(max_length=4, choices=PHONE_METHODS,
                              verbose_name=_('method'))

    def __repr__(self):
        return '<PhoneDevice(number={!r}, method={!r}>'.format(
            self.number,
            self.method,
        )

    def __eq__(self, other):
        if not isinstance(other, PhoneDevice):
            return False
        return self.number == other.number \
            and self.method == other.method \
            and self.key == other.key

    @property
    def bin_key(self):
        return unhexlify(self.key.encode())

    def verify_token(self, token):
        # local import to avoid circular import
        from two_factor.utils import totp_digits

        try:
            token = int(token)
        except ValueError:
            return False

        for drift in range(-5, 1):
            if totp(self.bin_key, drift=drift, digits=totp_digits()) == token:
                return True
        return False

    def generate_challenge(self):
        # local import to avoid circular import
        from two_factor.utils import totp_digits

        """
        Sends the current TOTP token to `self.number` using `self.method`.
        """
        no_digits = totp_digits()
        token = str(totp(self.bin_key, digits=no_digits)).zfill(no_digits)
        if self.method == 'call':
            make_call(device=self, token=token)
        else:
            send_sms(device=self, token=token)


class TrustedAgent(models.Model):
    """
    When a login comes in with a skip token cookie, a corresponding
    TrustedAgent record will need to match both the user id and user_agent.
    If there is no matching record in the TrustedAgent table,
    the token step will be required.
    Stolen lost phones/Yubikeys can be handled by removing them from
    their respective tables or by removing them from the TrustedAgent table.
    """
    user = models.ForeignKey(getattr(settings, 'AUTH_USER_MODEL', 'auth.User'),
                             null=False, on_delete=models.CASCADE)
    user_agent = models.CharField(null=False, blank=True, max_length=200)
    yubi = models.ForeignKey(RemoteYubikeyDevice, on_delete=models.CASCADE, null=True)
    phone = models.ForeignKey(PhoneDevice, on_delete=models.CASCADE, null=True)
    ip = models.GenericIPAddressField(null=True, blank=True, verbose_name='IP')

    class Meta:
        unique_together = (('user', 'user_agent'))
