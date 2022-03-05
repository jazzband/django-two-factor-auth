from django.utils.translation import gettext_lazy as _
from django_otp.plugins.otp_email.models import EmailDevice

from two_factor.plugins.registry import MethodBase

from .forms import AuthenticationTokenForm, DeviceValidationForm, EmailForm


class EmailMethod(MethodBase):
    code = 'email'
    verbose_name = _('Email')

    def recognize_device(self, device):
        return isinstance(device, EmailDevice)

    def get_setup_forms(self, wizard):
        forms = {}
        if not wizard.request.user.email:
            forms[self.code] = EmailForm
        forms['validation'] = DeviceValidationForm
        return forms

    def get_device_from_setup_data(self, request, setup_data, **kwargs):
        if setup_data and not request.user.email:
            request.user.email = setup_data.get('email').get('email')
            request.user.save(update_fields=['email'])
        device = EmailDevice.objects.devices_for_user(request.user).first()
        if not device:
            device = EmailDevice(user=request.user, name='default')
        return device

    def get_token_form_class(self):
        return AuthenticationTokenForm
