from django.utils.translation import gettext_lazy as _

from two_factor.plugins.registry import MethodBase

from .forms import PhoneNumberForm
from .models import PhoneDevice
from .utils import format_phone_number, mask_phone_number


class PhoneMethodBase(MethodBase):
    def get_devices(self, user):
        return PhoneDevice.objects.filter(user=user, method=self.code)

    def recognize_device(self, device):
        return isinstance(device, PhoneDevice) and device.method == self.code

    def get_setup_forms(self, *args):
        return {self.code: PhoneNumberForm}

    def get_device_from_setup_data(self, request, storage_data, **kwargs):
        return PhoneDevice(
            key=kwargs['key'],
            name='default',
            user=request.user,
            method=self.code,
            number=storage_data.get(self.code, {}).get('number'),
        )

    def get_action(self, device):
        number = mask_phone_number(format_phone_number(device.number))
        return self.action % number

    def get_verbose_action(self, device):
        return self.verbose_action


class PhoneCallMethod(PhoneMethodBase):
    code = 'call'
    verbose_name = _('Phone call')
    action = _('Call number %s')
    verbose_action = _('We are calling your phone right now, please enter the digits you hear.')


class SMSMethod(PhoneMethodBase):
    code = 'sms'
    verbose_name = _('Text message')
    action = _('Send text message to %s')
    verbose_action = _('We sent you a text message, please enter the token we sent.')
