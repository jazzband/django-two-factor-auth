from django.utils.translation import gettext_lazy as _

from two_factor.forms import DeviceValidationForm
from two_factor.plugins.registry import MethodBase

from .forms import EmailForm
from .models import EmailDevice


class EmailMethod(MethodBase):
    code = 'email'
    verbose_name = _('Email')

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
        key = kwargs.pop('key')
        return EmailDevice(key=key, user=request.user)
