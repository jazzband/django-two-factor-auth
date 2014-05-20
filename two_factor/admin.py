try:
    from urllib.parse import urlencode
except ImportError:
    from urllib import urlencode

from django.conf import settings
from django.contrib import admin
from django.contrib.admin import AdminSite
from django.contrib.auth import REDIRECT_FIELD_NAME
from django.core.urlresolvers import reverse
from django.shortcuts import redirect

from .utils import monkeypatch_method
from .models import PhoneDevice


class AdminSiteOTPRequiredMixin(object):
    """
    Mixin for enforcing OTP verified staff users.

    Custom admin views should either be wrapped using :meth:`admin_view` or
    use :meth:`has_permission` in order to secure those views.
    """
    def has_permission(self, request):
        """
        Returns True if the given HttpRequest has permission to view
        *at least one* page in the admin site.
        """
        if not super(AdminSiteOTPRequiredMixin, self).has_permission(request):
            return False
        return request.user.is_verified()

    def login(self, request, extra_context=None):
        """
        Redirects to the site login page for the given HttpRequest.
        """
        if REDIRECT_FIELD_NAME in request.GET:
            url = request.GET[REDIRECT_FIELD_NAME]
        else:
            url = request.get_full_path()
        return redirect('%s?%s' % (
            reverse('two_factor:login'),
            urlencode({REDIRECT_FIELD_NAME: url})
        ))


class AdminSiteOTPRequired(AdminSiteOTPRequiredMixin, AdminSite):
    """
    AdminSite enforcing OTP verified staff users.
    """
    pass


def patch_admin():
    @monkeypatch_method(AdminSite)
    def login(self, request, extra_context=None):
        """
        Redirects to the site login page for the given HttpRequest.
        """
        if REDIRECT_FIELD_NAME in request.GET:
            url = request.GET[REDIRECT_FIELD_NAME]
        else:
            url = request.get_full_path()
        return redirect('%s?%s' % (
            reverse('two_factor:login'),
            urlencode({REDIRECT_FIELD_NAME: url})
        ))


def unpatch_admin():
    setattr(AdminSite, 'login', original_login)


original_login = AdminSite.login
if getattr(settings, 'TWO_FACTOR_PATCH_ADMIN', True):
    patch_admin()


admin.site.register(PhoneDevice)
