from django.apps import AppConfig
from django.conf import settings


class TwoFactorConfig(AppConfig):
    name = 'two_factor'
    verbose_name = "Django Two Factor Authentication"

    def ready(self):
        from .admin import patch_admin
        from .signals import login_alert  # noqa: F401
        if getattr(settings, 'TWO_FACTOR_PATCH_ADMIN', True):
            patch_admin()
