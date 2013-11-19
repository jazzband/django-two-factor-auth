import re

from django import template
from django.utils.translation import ugettext

from ..models import PhoneDevice

register = template.Library()

phone_mask = re.compile('(?<=.{3}).(?=.{4})')


@register.filter
def mask_phone_number(number):
    return phone_mask.sub('*', number)


@register.filter
def device_action(device):
    assert isinstance(device, PhoneDevice)
    number = mask_phone_number(device.number)
    if device.method == 'sms':
        return ugettext('Send text message to %s') % number
    elif device.method == 'call':
        return ugettext('Call number %s') % number
    raise NotImplementedError
