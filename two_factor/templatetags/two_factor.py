import re

import phonenumbers
from django import template
from django.utils.translation import ugettext

register = template.Library()

phone_mask = re.compile('(?<=.{3})[0-9](?=.{2})')


@register.filter
def device_action(device):
    """
    Generates an actionable text for a :class:`~two_factor.models.PhoneDevice`.

    Examples:

    * Send text message to `+31 * ******58`
    * Call number `+31 * ******58`
    """
    assert isinstance(device, PhoneDevice)
    number = mask_phone_number(format_phone_number(device.number))
    if device.method == 'sms':
        return ugettext('Send text message to %s') % number
    elif device.method == 'call':
        return ugettext('Call number %s') % number
    raise NotImplementedError('Unknown method: %s' % device.method)
