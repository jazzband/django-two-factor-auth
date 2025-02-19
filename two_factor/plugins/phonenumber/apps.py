from django.apps import AppConfig, apps
from django.conf import settings
from django.test.signals import setting_changed

from two_factor.plugins.registry import registry


class TwoFactorPhoneNumberConfig(AppConfig):
    name = 'two_factor.plugins.phonenumber'
    verbose_name = "Django Two Factor Authentication – Phone Method"
    default_auto_field = "django.db.models.AutoField"
    url_prefix = 'phone'

    def ready(self):
        update_registered_methods(self, None, None)
        setting_changed.connect(update_registered_methods)


def update_registered_methods(sender, setting, value, **kwargs):
    # This allows for dynamic registration, typically when testing.
    from .method import PhoneCallMethod, SMSMethod

    phone_number_app_installed = apps.is_installed('two_factor.plugins.phonenumber')

    if phone_number_app_installed and getattr(settings, 'TWO_FACTOR_CALL_GATEWAY', None):
        registry.register(PhoneCallMethod())
    else:
        registry.unregister('call')
    if phone_number_app_installed and getattr(settings, 'TWO_FACTOR_SMS_GATEWAY', None):
        registry.register(SMSMethod())
    else:
        registry.unregister('sms')
