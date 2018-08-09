from django.apps import AppConfig
from django.conf import settings
from django.utils.translation import ugettext_lazy as _


class TwoFactorPhoneNumberConfig(AppConfig):
    name = 'two_factor.plugins.phonenumber'
    verbose_name = "Django Two Factor Authentication – Phone Method"

    def get_two_factor_available_methods(self):
        from .models import get_available_phone_methods
        return get_available_phone_methods()

    def get_device_setup_form(self, method):
        from .forms import PhoneNumberForm
        return PhoneNumberForm

    def get_device_validation_form(self, method):
        from ...forms import DeviceValidationForm
        return DeviceValidationForm

    def get_device_setup_form_kwargs(self, method, user, key, metadata):
        return {}

    def get_device_validation_form_kwargs(self, method, user, key, metadata, setup):
        from .models import PhoneDevice
        device = PhoneDevice(name='default', method=method, user=user, key=key, number=setup['number'])
        device.generate_challenge()
        return {
            'device': device,
        }
