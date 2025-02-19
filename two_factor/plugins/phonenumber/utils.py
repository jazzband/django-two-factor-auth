import re

import phonenumbers

from two_factor.plugins.registry import MethodNotFoundError, registry

phone_mask = re.compile(r'(?<=.{3})[0-9](?=.{2})')


def get_available_phone_methods():
    methods = []
    for code in ['sms', 'call']:
        try:
            method = registry.get_method(code)
        except MethodNotFoundError:
            pass
        else:
            methods.append(method)

    return methods


def backup_phones(user):
    if not user or user.is_anonymous:
        return []

    phones = []
    for method in get_available_phone_methods():
        phones += list(method.get_devices(user))

    return [phone for phone in phones if phone.name == 'backup']


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


def format_phone_number(number):
    """
    Formats a phone number in international notation.
    :param number: str or phonenumber object
    :return: str
    """
    if not isinstance(number, phonenumbers.PhoneNumber):
        number = phonenumbers.parse(number)
    return phonenumbers.format_number(number, phonenumbers.PhoneNumberFormat.INTERNATIONAL)
