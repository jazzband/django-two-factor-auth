import re

from django import template
from django.utils.translation import ugettext

from ..models import PhoneDevice

register = template.Library()

phone_mask = re.compile('(?<=.{3}).(?=.{2})')


@register.filter
def mask_phone_number(number):
    """
    Masks a phone number, only first 3 and last 2 digits visible.

    Examples:

    * +31*******58
    """
    return phone_mask.sub('*', number)


@register.filter
def device_action(device):
    """
    Generates an actionable text for a :class:`~two_factor.models.PhoneDevice`.

    Examples:

    * Send text message to +1234
    * Call number +3456
    """
    assert isinstance(device, PhoneDevice)
    number = mask_phone_number(device.number)
    if device.method == 'sms':
        return ugettext('Send text message to %s') % number
    elif device.method == 'call':
        return ugettext('Call number %s') % number
    raise NotImplementedError('Unknown method: %s' % device.method)
