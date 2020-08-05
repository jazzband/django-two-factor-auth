from django.conf import settings
import warnings
from functools import update_wrapper

from django.contrib.admin import AdminSite
from django.contrib.auth import REDIRECT_FIELD_NAME
from django.contrib.auth.views import redirect_to_login
from django.http import HttpResponseRedirect
from django.shortcuts import resolve_url
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils.translation import gettext as _
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_protect

from .utils import default_device

class TwoFactorAdminSiteMixin:
    """
    Mixin for enforcing OTP verified staff users.

    Custom admin views should either be wrapped using :meth:`admin_view` or
    use :meth:`has_permission` in order to secure those views.
    """

    def has_admin_permission(self, request):
        return super().has_permission(request)

    def has_permission(self, request):
        """
        Returns True if the given HttpRequest has permission to view
        *at least one* page in the admin site.
        """
        return self.has_admin_permission(request) and request.user.is_verified()

    def has_mfa_setup(self, request):
        otp_device = default_device(request.user)
        return otp_device is not None

    def redirect_to_mfa_setup(self, request):
        # Already logged-in, but they did not login with MFA and do not
        # have MFA enabled on their account. We're going to redirect them
        # to the MFA setup.

        # TODO: Add redirect_to functionality to MFA setup.
        # TODO: Add message indicating why the user was directed or setup and MFA required
        #       interstitial page to explain to the user they need to setup MFA.
        setup_url = reverse('two_factor:setup')
        next = request.GET.get(REDIRECT_FIELD_NAME, reverse('admin:index'))

        # the name redirect_to_login is a little misleading, the function actually
        # redirects to the specified view setting the REDIRECT_FIELD_NAME to the
        # next value. We're not logging in here, we're just sending the user to the
        # MFA setup screen.
        return redirect_to_login(next, setup_url)

    @method_decorator(never_cache)
    def login(self, request, extra_context=None):
        """
        Redirects to the site login page for the given HttpRequest.
        """
        redirect_to = request.POST.get(REDIRECT_FIELD_NAME, request.GET.get(REDIRECT_FIELD_NAME))
        if not redirect_to or not url_has_allowed_host_and_scheme(url=redirect_to, allowed_hosts=[request.get_host()]):
            redirect_to = resolve_url(settings.LOGIN_REDIRECT_URL)
        return redirect_to_login(redirect_to)
        

    def admin_view(self, view, cacheable=False):
        """
        Decorator to create an admin view attached to this ``AdminSite``. This
        wraps the view and provides permission checking by calling
        ``self.has_permission``.

        You'll want to use this from within ``AdminSite.get_urls()``:

            class MyAdminSite(AdminSite):

                def get_urls(self):
                    from django.urls import path

                    urls = super().get_urls()
                    urls += [
                        path('my_view/', self.admin_view(some_view))
                    ]
                    return urls

        By default, admin_views are marked non-cacheable using the
        ``never_cache`` decorator. If the view can be safely cached, set
        cacheable=True.
        """
        def inner(request, *args, **kwargs):
            if self.has_admin_permission(request) and not self.has_mfa_setup(request):
                return self.redirect_to_mfa_setup(request)

            if not self.has_permission(request):
                if request.path == reverse('admin:logout', current_app=self.name):
                    index_path = reverse('admin:index', current_app=self.name)
                    return HttpResponseRedirect(index_path)

                # Inner import to prevent django.contrib.admin (app) from
                # importing django.contrib.auth.models.User (unrelated model).
                from django.contrib.auth.views import redirect_to_login
                return redirect_to_login(
                    request.get_full_path(),
                    reverse('%s:login' % self.name, current_app=self.name)
                )
            return view(request, *args, **kwargs)

        if not cacheable:
            inner = never_cache(inner)
        # We add csrf_protect here so this function can be used as a utility
        # function for any view, without having to repeat 'csrf_protect'.
        if not getattr(view, 'csrf_exempt', False):
            inner = csrf_protect(inner)
        return update_wrapper(inner, view)


class TwoFactorAdminSite(TwoFactorAdminSiteMixin, AdminSite):
    """
    AdminSite with MFA Support.
    """
    pass


class AdminSiteOTPRequiredMixin(TwoFactorAdminSiteMixin):
    warnings.warn('AdminSiteOTPRequiredMixin is deprecated by TwoFactorAdminSiteMixin, please update.',
                  category=DeprecationWarning)
    pass


class AdminSiteOTPRequired(TwoFactorAdminSite):
    warnings.warn('AdminSiteOTPRequired is deprecated by TwoFactorAdminSite, please update.',
                  category=DeprecationWarning)
    pass


def patch_admin():
    warnings.warn('two-factor admin patching will be removed, use TwoFactorAdminSite or TwoFactorAdminSiteMixin.',
                  category=DeprecationWarning)
    # overrides
    setattr(AdminSite, 'login', TwoFactorAdminSiteMixin.login)
    setattr(AdminSite, 'admin_view', TwoFactorAdminSiteMixin.admin_view)
    setattr(AdminSite, 'has_permission', TwoFactorAdminSiteMixin.has_permission)
    # additions
    setattr(AdminSite, 'has_admin_permission', original_has_permission)
    setattr(AdminSite, 'has_mfa_setup', TwoFactorAdminSiteMixin.has_mfa_setup)
    setattr(AdminSite, 'redirect_to_mfa_setup', TwoFactorAdminSiteMixin.redirect_to_mfa_setup)


def unpatch_admin():
    warnings.warn('django-two-factor admin patching is deprecated, use TwoFactorAdminSite or TwoFactorAdminSiteMixin.',
                  category=DeprecationWarning)
    # we really only need unpatching in our tests so this can be a noop.
    # overrides
    setattr(AdminSite, 'login', original_login)
    setattr(AdminSite, 'admin_view', original_admin_view)
    setattr(AdminSite, 'has_permission', original_has_permission)
    # NOTE: this unpatching doesn't really work, but becuase it just patches in our mixin it isn't harmful.


original_login = AdminSite.login
original_admin_view = AdminSite.admin_view
original_has_permission = AdminSite.has_permission
