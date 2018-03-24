from django.apps import AppConfig
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

from two_factor.plugins.registry import registry


class TwoFactorEmailConfig(AppConfig):
    name = 'two_factor.plugins.email'
    verbose_name = "Django Two Factor Authentication – Email Method"

    def ready(self):
        if not settings.EMAIL_BACKEND or not settings.DEFAULT_FROM_EMAIL:
            raise ImproperlyConfigured(
                "Please configure the EMAIL_BACKEND and DEFAULT_FROM_EMAIL "
                "settings to use the Email plugin."
            )

        from .method import EmailMethod

        registry.register(EmailMethod())
