import re

import phonenumbers
from django import template
from django.utils.translation import ugettext

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


