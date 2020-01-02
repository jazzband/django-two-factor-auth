from django.conf import settings
from django.utils.translation import gettext_lazy as _

from two_factor.models import PhoneDevice

from .base import Method


class PhoneCallMethod(Method):
    code = 'call'
    verbose_name = _('Phone call')
    form_path = 'two_factor.forms.PhoneNumberForm'

    def is_available(self):
        return bool(getattr(settings, 'TWO_FACTOR_CALL_GATEWAY', None))

    def get_device(self, user, key, validated_data):
        number = validated_data.get('number')
        return PhoneDevice(
            name='default', user=user, key=key, method=self.code, number=number
        )


class SMSMethod(PhoneCallMethod):
    code = 'sms'
    verbose_name = _('Text message')
    form_path = 'two_factor.forms.PhoneNumberForm'

    def is_available(self):
        return bool(getattr(settings, 'TWO_FACTOR_SMS_GATEWAY', None))
