from django.apps import AppConfig
from django.conf import settings
from django.utils.translation import ugettext_lazy as _


class TwoFactorPhoneNumberConfig(AppConfig):
    name = 'two_factor.plugins.phonenumber'
    verbose_name = "Django Two Factor Authentication – Phone Method"

    def get_two_factor_available_methods(self):
        from .models import get_available_phone_methods
        return get_available_phone_methods()
