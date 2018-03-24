from django.utils.translation import gettext_lazy as _

from two_factor.plugins.registry import MethodBase

from .forms import PhoneNumberForm
from .models import PhoneDevice


class PhoneMethodBase(MethodBase):
    def recognize_device(self, device):
        return isinstance(device, PhoneDevice)

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


class PhoneCallMethod(PhoneMethodBase):
    code = 'call'
    verbose_name = _('Phone call')


class SMSMethod(PhoneMethodBase):
    code = 'sms'
    verbose_name = _('Text message')
