from django.conf import settings
from django.contrib import admin
from django.contrib.admin import sites
from django.shortcuts import redirect

from .models import PhoneDevice


if getattr(settings, 'TWO_FACTOR_PATCH_ADMIN', True):
    def redirect_admin_login(self, request):
        return redirect(str(settings.LOGIN_URL))
    sites.AdminSite.login = redirect_admin_login


admin.site.register(PhoneDevice)
