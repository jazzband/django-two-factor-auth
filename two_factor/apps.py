from django.apps import AppConfig
from django.conf import settings
from django.utils.translation import ugettext_lazy as _


class TwoFactorConfig(AppConfig):
    name = 'two_factor'
    verbose_name = "Django Two Factor Authentication"

    def ready(self):
        from .admin import patch_admin
        if getattr(settings, 'TWO_FACTOR_PATCH_ADMIN', True):
            patch_admin()
        from . import signals

    def get_two_factor_available_methods(self):
        return [
            ('generator', _('Token generator')),
        ]

    def get_device_setup_form(self, method):
        from .forms import TOTPDeviceForm
        return TOTPDeviceForm

    def get_device_validation_form(self, method):
        return None
