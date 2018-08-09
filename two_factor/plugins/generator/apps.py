from django.apps import AppConfig
from django.conf import settings
from django.utils.translation import ugettext_lazy as _


class TwoFactorGeneratorConfig(AppConfig):
    name = 'two_factor.plugins.generator'
    verbose_name = "Django Two Factor Authentication - Generator Method"

    def get_two_factor_available_methods(self):
        return [
            ('generator', _('Token generator')),
        ]

    def get_device_setup_form(self, method):
        from .forms import TOTPDeviceForm
        return TOTPDeviceForm

    def get_device_validation_form(self, method):
        return None

    def get_device_setup_form_kwargs(self, method, user, key, metadata):
        return {
            'key': key,
            'user': user,
        }

    def get_device_validation_form_kwargs(self, method, user, key, metadata, setup):
        return {}
