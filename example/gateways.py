from django.contrib import messages
from django.utils.translation import gettext as _

from two_factor.middleware.threadlocals import get_current_request
from two_factor.plugins.phonenumber.utils import mask_phone_number


class Messages:
    @classmethod
    def make_call(cls, device, token):
        cls._add_message(_('Fake call to %(number)s: "Your token is: %(token)s"'),
                         device, token)

    @classmethod
    def send_sms(cls, device, token):
        cls._add_message(_('Fake SMS to %(number)s: "Your token is: %(token)s"'),
                         device, token)

    @classmethod
    def _add_message(cls, message, device, token):
        message = message % {'number': mask_phone_number(device.number),
                             'token': token}
        messages.add_message(get_current_request(), messages.INFO, message)
