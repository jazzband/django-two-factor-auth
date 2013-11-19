try:
    from urllib.parse import urlencode
except ImportError:
    from urllib import urlencode

from django.conf import settings
from django.contrib import admin
from django.contrib.admin import sites
from django.contrib.auth import REDIRECT_FIELD_NAME
from django.shortcuts import redirect

from .models import PhoneDevice


if getattr(settings, 'TWO_FACTOR_PATCH_ADMIN', True):
    def redirect_admin_login(self, request):
        return redirect('%s?%s' % (
            settings.LOGIN_URL,
            urlencode({REDIRECT_FIELD_NAME: request.get_full_path()})
        ))
    sites.AdminSite.login = redirect_admin_login


admin.site.register(PhoneDevice)
