from django.contrib import messages
from two_factor.middleware.threadlocals import get_current_request


class Messages(object):
    @classmethod
    def make_call(cls, device, token):
        cls._add_message('Fake call to %s: "Your token is: %s"' %
                         (device.number, token))

    @classmethod
    def send_sms(cls, device, token):
        cls._add_message('Fake SMS to %s: "Your token is: %s"' %
                         (device.number, token))

    @classmethod
    def _add_message(cls, message):
        messages.add_message(get_current_request(), messages.INFO, message)
