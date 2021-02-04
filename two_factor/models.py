import logging
from binascii import unhexlify

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _
from django_otp.models import Device, ThrottlingMixin
from django_otp.oath import totp
from django_otp.util import hex_validator, random_hex
from phonenumber_field.modelfields import PhoneNumberField

from .gateways import make_call, send_email, send_sms

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


def get_available_email_methods():
    methods = []
    if getattr(settings, 'TWO_FACTOR_EMAIL_GATEWAY', None):
        methods.append(('email', _('Email message')))

    return methods


def get_available_methods():
    methods = [('generator', _('Token generator'))]
    methods.extend(get_available_phone_methods())
    methods.extend(get_available_yubikey_methods())
    methods.extend(get_available_email_methods())
    return methods


def key_validator(*args, **kwargs):
    """Wraps hex_validator generator, to keep makemigrations happy."""
    return hex_validator()(*args, **kwargs)


class TwoFactorDevice(Device):
    """
    Base class for 2FA devices
    """
    class Meta:
        abstract = True
        app_label = 'two_factor'

    drift_range = []
    key = models.CharField(max_length=40,
                           validators=[key_validator],
                           default=random_hex,
                           help_text="Hex-encoded secret key")

    @property
    def bin_key(self):
        return unhexlify(self.key.encode())

    def get_challenge_token(self):
        """
        Generate TOTP challenge token
        :return: String token
        """
        from two_factor.utils import totp_digits

        no_digits = totp_digits()
        return str(totp(self.bin_key, digits=no_digits)).zfill(no_digits)

    def verify_token(self, token):
        # local import to avoid circular import
        from two_factor.utils import totp_digits

        try:
            token = int(token)
        except ValueError:
            return False

        for drift in self.drift_range:
            if totp(self.bin_key, drift=drift, digits=totp_digits()) == token:
                return True
        return False


class PhoneDevice(ThrottlingMixin, TwoFactorDevice):
    """
    Base class for 2FA devices
    """
    class Meta:
        app_label = 'two_factor'

    drift_range = range(-5, 1)
    number = PhoneNumberField()
    method = models.CharField(max_length=4, choices=PHONE_METHODS,
                              verbose_name=_('method'))

    def __repr__(self):
        return '<PhoneDevice(number={!r}, method={!r}>'.format(
            self.number,
            self.method,
        )

    def generate_challenge(self):
        """
        """
        token = self.get_challenge_token()

        if self.method == 'call':
            make_call(device=self, token=token)
        else:
            send_sms(device=self, token=token)

    def get_throttle_factor(self):
        return getattr(settings, 'TWO_FACTOR_PHONE_THROTTLE_FACTOR', 1)


class EmailDevice(TwoFactorDevice):
    """
    Device wrapper for communication via email
    """
    drift_range = range(-30, 1)
    email = models.EmailField(verbose_name=_('Email'))

    def __repr__(self):
        return '<EmailDevice(email={!r})>'.format(
            self.email
        )

    @property
    def method(self):
        return 'email'

    def generate_challenge(self):
        """
        Sends the current TOTP token to `self.email`
        """
        token = self.get_challenge_token()
        send_email(device=self, token=token)
