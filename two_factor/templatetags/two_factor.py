import re

import phonenumbers
from django import template
from django.urls import reverse
from django.utils.translation import gettext as _

from ..models import EmailDevice, PhoneDevice

register = template.Library()

phone_mask = re.compile('(?<=.{3})[0-9](?=.{2})')
email_mask = re.compile('(?<=.)[^@](?=[^@]*?[^@]@)|(?:(?<=@.)|(?!^)(?=[^@]*$)).(?=.*[^@]\\.)')


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
def mask_email(email):
    """
    Masks an email, display only first and last characters of each email's part

    Examples:

    * `f*o@**r.com`

    :param email: str
    :return: str
    """
    return email_mask.sub('*', email)


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
    Generates an actionable text for a devices:
      :class:`~two_factor.models.PhoneDevice`
      :class:`~two_factor.models.EmailDevice`.

    Examples:

    * Send text message to `+31 * ******58`
    * Call number `+31 * ******58`
    * Send email to `f*o@**r.com`
    """
    if isinstance(device, EmailDevice):
        return _('Send email to %s') % mask_email(device.email)

    assert isinstance(device, PhoneDevice)
    number = mask_phone_number(format_phone_number(device.number))
    if device.method == 'sms':
        return _('Send text message to %s') % number
    elif device.method == 'call':
        return _('Call number %s') % number
    raise NotImplementedError('Unknown method: %s' % device.method)


@register.filter
def device_remove_url(device):
    """
    Provide link to device unregister for
      :class:`~two_factor.models.PhoneDevice`
      :class:`~two_factor.models.EmailDevice`.
    """
    if isinstance(device, EmailDevice):
        return reverse('two_factor:email_delete', args=[device.id])
    elif isinstance(device, PhoneDevice):
        return reverse('two_factor:phone_delete', args=[device.id])

    raise NotImplementedError("Can't generate remove_url for : %s" % device)
