from django.apps import AppConfig
from django.conf import settings

from .admin import patch_admin


class TwoFactorConfig(AppConfig):
    name = 'two_factor'
    verbose_name = "Django Two Factor Authentication"

    def ready(self):
        if getattr(settings, 'TWO_FACTOR_PATCH_ADMIN', True):
            patch_admin()
