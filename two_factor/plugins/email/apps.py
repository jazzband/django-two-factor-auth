from django.apps import AppConfig
from django.conf import settings
from two_factor.plugins.registry import registry


class TwoFactorEmailConfig(AppConfig):
    # Allows you to resolve conflict between two apps called email.
    name = getattr(settings, "TWO_FACTOR_EMAIL_APPCONFIG_NAME", 'two_factor.plugins.email')
    verbose_name = "Django Two Factor Authentication – Email Method"

    def ready(self):
        from .method import EmailMethod

        registry.register(EmailMethod())
