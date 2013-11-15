from django.conf import settings
from django.contrib import admin

from .models import PhoneDevice
from .utils import patch_admin_login

if getattr(settings, 'TWO_FACTOR_PATCH_ADMIN', True):
    patch_admin_login()

admin.site.register(PhoneDevice)
