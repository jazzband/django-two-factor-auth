from django.conf import settings
from django.contrib import admin
from django.contrib.admin import AdminSite
from django.contrib.auth import REDIRECT_FIELD_NAME
from django.contrib.auth.views import redirect_to_login
from django.shortcuts import resolve_url
from django.utils.http import is_safe_url

from .models import PhoneDevice
from ...utils import monkeypatch_method

class PhoneDeviceAdmin(admin.ModelAdmin):
    """
    :class:`~django.contrib.admin.ModelAdmin` for
    :class:`~two_factor.models.PhoneDevice`.
    """
    raw_id_fields = ('user',)


admin.site.register(PhoneDevice, PhoneDeviceAdmin)
