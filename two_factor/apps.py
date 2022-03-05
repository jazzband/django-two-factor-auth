from django.apps import AppConfig, apps
from django.conf import settings

from two_factor.plugins.registry import registry


class TwoFactorConfig(AppConfig):
    name = 'two_factor'
    verbose_name = "Django Two Factor Authentication"

    def ready(self):
        if getattr(settings, 'TWO_FACTOR_PATCH_ADMIN', True):
            from .admin import patch_admin
            patch_admin()
        if apps.is_installed('django_otp.plugins.otp_email'):
            from two_factor.plugins.email.method import EmailMethod
            registry.register(EmailMethod())
