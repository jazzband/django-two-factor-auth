from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _
from django_otp.models import Device, ThrottlingMixin
from django_otp.oath import totp
from phonenumber_field.modelfields import PhoneNumberField

from two_factor.abstracts import TwoFactorModelBase
from two_factor.gateways import make_call, send_sms

from .utils import format_phone_number, mask_phone_number

PHONE_METHODS = (
    ('call', _('Phone Call')),
    ('sms', _('Text Message')),
)


class PhoneDevice(ThrottlingMixin, TwoFactorModelBase, Device):
    """
    Model with phone number and token seed linked to a user.
    """
    drift_range = range(-5, 1)

    number = PhoneNumberField()
    method = models.CharField(max_length=4, choices=PHONE_METHODS,
                              verbose_name=_('method'))

    class Meta:
        app_label = 'two_factor'

    def __repr__(self):
        return '<PhoneDevice(number={!r}, method={!r})>'.format(
            self.number,
            self.method,
        )

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

    @property
    def generate_challenge_button_title(self):
        number = mask_phone_number(format_phone_number(self.number))
        if self.method == 'sms':
            return _('Send text message to %s') % number
        else:
            return _('Call number %s') % number

    def get_throttle_factor(self):
        return getattr(settings, 'TWO_FACTOR_PHONE_THROTTLE_FACTOR', 1)
