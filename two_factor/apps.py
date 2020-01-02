from django.apps import AppConfig, apps
from django.conf import settings
from django.test.signals import setting_changed


class TwoFactorConfig(AppConfig):
    name = 'two_factor'
    verbose_name = "Django Two Factor Authentication"

    def ready(self):
        from .methods import method_registry
        from .methods.yubikey import YubiKeyMethod
        from .methods.phone import PhoneCallMethod, SMSMethod

        setting_changed.connect(register_methods)
        # Register available methods.
        for method in (PhoneCallMethod(), SMSMethod(), YubiKeyMethod()):
            if method.is_available():
                method_registry.register(method)

        if getattr(settings, 'TWO_FACTOR_PATCH_ADMIN', True):
            from .admin import patch_admin
            patch_admin()


def register_methods(sender, setting, value, **kwargs):
    # Mostly useful in test context.
    from .methods import method_registry
    from .methods.yubikey import YubiKeyMethod
    from .methods.phone import PhoneCallMethod, SMSMethod

    if setting == 'TWO_FACTOR_CALL_GATEWAY':
        if value:
            method_registry.register(PhoneCallMethod())
        else:
            method_registry.unregister('call')

    if setting == 'TWO_FACTOR_SMS_GATEWAY':
        if value:
            method_registry.register(SMSMethod())
        else:
            method_registry.unregister('sms')

    if setting == 'INSTALLED_APPS':
        if apps.is_installed('otp_yubikey'):
            method_registry.register(YubiKeyMethod())
        else:
            method_registry.unregister('yubikey')
