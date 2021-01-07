import re

import phonenumbers
from django import template
from django.utils.translation import gettext as _
from django_otp.plugins.otp_totp.models import TOTPDevice 

from ..models import PhoneDevice, WebauthnDevice

register = template.Library()

phone_mask = re.compile('(?<=.{3})[0-9](?=.{2})')


@register.filter
def mask_phone_number(number):
    """
    Masks a phone number, only first 3 and last 2 digits visible.

    Examples:

    * `+31 * ******58`

    :param number: str or phonenumber object
    :return: str
    """
    if isinstance(number, phonenumbers.PhoneNumber):
        number = format_phone_number(number)
    return phone_mask.sub('*', number)


@register.filter
def format_phone_number(number):
    """
    Formats a phone number in international notation.
    :param number: str or phonenumber object
    :return: str
    """
    if not isinstance(number, phonenumbers.PhoneNumber):
        number = phonenumbers.parse(number)
    return phonenumbers.format_number(number, phonenumbers.PhoneNumberFormat.INTERNATIONAL)


@register.filter
def device_action(device):
    """
    Generates an actionable text for a :class:`~two_factor.models.PhoneDevice`.

    Examples:

    * Send text message to `+31 * ******58`
    * Call number `+31 * ******58`
    """
    if isinstance(device, PhoneDevice):
        number = mask_phone_number(format_phone_number(device.number))
        if device.method == 'sms':
            return _('Send text message to %s') % number
        elif device.method == 'call':
            return _('Call number %s') % number

    if isinstance(device, TOTPDevice):
        return _('Insert a token from your TOTP device')

    if isinstance(device, WebauthnDevice):
        return _('Use one of your WebAuthn-compatible devices')

    raise NotImplementedError('Unknown method: %s' % device.method)
