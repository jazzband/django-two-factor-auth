from django.apps import AppConfig
from django.conf import settings

from .admin import patch_admin


class TwoFactorConfig(AppConfig):
    name = 'two_factor'
    verbose_name = "Django Two Factor Authentication"

    def ready(self):
        print("This does also printy")
        if getattr(settings, 'TWO_FACTOR_PATCH_ADMIN', True):
            print("This does no printy")
            patch_admin()
