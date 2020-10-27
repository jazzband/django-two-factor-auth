from django.conf import settings
from django.contrib import admin
from django.contrib.admin import AdminSite
from django.contrib.auth import REDIRECT_FIELD_NAME
from django.contrib.auth.views import redirect_to_login
from django.http import HttpResponseRedirect
from django.shortcuts import resolve_url
from django.urls import reverse
from django.utils.http import is_safe_url

from .models import PhoneDevice
from .utils import monkeypatch_method


class AdminSiteOTPRequiredMixin(object):
    """
    Mixin for enforcing OTP verified staff users.

    Custom admin views should either be wrapped using :meth:`admin_view` or
    use :meth:`has_permission` in order to secure those views.

    If user has admin permissions but 2FA not setup, then redirect to
    2FA setup page.
    """

    def has_permission(self, request):
        """
        Returns True if the given HttpRequest has permission to view
        *at least one* page in the admin site.
        """
        if not super().has_permission(request):
            return False
        return request.user.is_verified()

    def login(self, request, extra_context=None):
        """
        Redirects to the site login page for the given HttpRequest.
        """
                 # redirect to admin page after login
        redirect_to = request.POST.get(REDIRECT_FIELD_NAME, request.GET.get(REDIRECT_FIELD_NAME))

        # if user (is_active and is_staff)
        if request.method == "GET" and super().has_permission(request):
            # if user has 2FA setup, go to admin homepage
            if request.user.is_verified():
                index_path = reverse("admin:index", current_app=self.name)
            # 2FA not setup. redirect to 2FA setup page
            else:
                index_path = reverse("two_factor:setup", current_app=self.name)
            return HttpResponseRedirect(index_path)

        if not redirect_to or not is_safe_url(url=redirect_to, allowed_hosts=[request.get_host()]):
            redirect_to = resolve_url(settings.LOGIN_REDIRECT_URL)

        return redirect_to_login(redirect_to)


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
        redirect_to = request.POST.get(REDIRECT_FIELD_NAME, request.GET.get(REDIRECT_FIELD_NAME))

        if not redirect_to or not is_safe_url(url=redirect_to, allowed_hosts=[request.get_host()]):
            redirect_to = resolve_url(settings.LOGIN_REDIRECT_URL)

        return redirect_to_login(redirect_to)


def unpatch_admin():
    setattr(AdminSite, 'login', original_login)


original_login = AdminSite.login


class PhoneDeviceAdmin(admin.ModelAdmin):
    """
    :class:`~django.contrib.admin.ModelAdmin` for
    :class:`~two_factor.models.PhoneDevice`.
    """
    raw_id_fields = ('user',)


admin.site.register(PhoneDevice, PhoneDeviceAdmin)
