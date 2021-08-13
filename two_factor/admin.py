from functools import update_wrapper

from django.conf import settings
from django.contrib import admin
from django.contrib.admin import AdminSite
from django.contrib.auth import REDIRECT_FIELD_NAME
from django.shortcuts import redirect, resolve_url
from django.urls import reverse
from django.utils.http import is_safe_url
from django.utils.translation import ugettext

from .models import PhoneDevice
from .views import BackupTokensView, LoginView, ProfileView, SetupView, SetupCompleteView, DisableView, QRGeneratorView


class AdminLoginView(LoginView):
    form_templates = {
        'auth': 'two_factor/admin/_wizard_form_auth.html',
        'token': 'two_factor/admin/_wizard_form_token.html',
        'backup': 'two_factor/admin/_wizard_form_backup.html',
    }
    redirect_url = 'admin:two_factor:setup'
    template_name = 'two_factor/admin/login.html'

    def get_context_data(self, form, **kwargs):
        context = super(AdminLoginView, self).get_context_data(form, **kwargs)
        if self.kwargs['extra_context']:
            context.update(self.kwargs['extra_context'])
        user_is_validated = getattr(self.request.user, 'is_verified', None)
        context.update({
            'cancel_url': reverse('admin:index' if user_is_validated else 'admin:login'),
            'wizard_form_template': self.form_templates.get(self.steps.current),
        })
        return context

    def get_redirect_url(self):
        redirect_to = self.request.GET.get(self.redirect_field_name, None)
        url_is_safe = is_safe_url(
            url=redirect_to,
            allowed_hosts=self.get_success_url_allowed_hosts(),
            require_https=self.request.is_secure(),
        )
        if url_is_safe:
            self.request.session[REDIRECT_FIELD_NAME] = redirect_to

        print(dir(self.request.user))
        user_is_validated = getattr(self.request.user, 'is_verified', None)
        if not user_is_validated:
            redirect_to = resolve_url(self.redirect_url)

        print("login: ", redirect_to)
        return redirect_to


admin_login_view = AdminLoginView.as_view()


class AdminSetupCompleteView(SetupCompleteView):
    template_name = 'two_factor/admin/setup_complete.html'

admin_setup_complete_view = AdminSetupCompleteView.as_view()


class AdminSetupView(SetupView):
    form_templates = {
        'method': 'two_factor/admin/_wizard_form_method.html',
        'generator': 'two_factor/admin/_wizard_form_generator.html',
        'sms': 'two_factor/admin/_wizard_form_phone_number.html',
        'call': 'two_factor/admin/_wizard_form_phone_number.html',
        'validation': 'two_factor/admin/_wizard_form_validation.html',
        'yubikey': 'two_factor/admin/_wizard_form_yubikey.html',
    }
    qrcode_url = 'admin:two_factor:qr'
    redirect_url = 'admin:two_factor:profile'
    success_url = 'admin:two_factor:setup_complete'
    template_name = 'two_factor/admin/setup.html'

    def get_context_data(self, form, **kwargs):
        context = super(AdminSetupView, self).get_context_data(form, **kwargs)
        user_is_validated = getattr(self.request.user, 'is_verified', None)
        context.update({
            'cancel_url': reverse('admin:two_factor:profile' if user_is_validated else 'admin:login'),
            'site_header': ugettext("Enable Two-Factor Authentication"),
            'title': ugettext("Enable Two-Factor Authentication"),
            'wizard_form_template': self.form_templates.get(self.steps.current),
        })
        return context

    def get_success_url(self):
        redirect_to = self.request.session.pop(REDIRECT_FIELD_NAME, '')
        assert False, "test"
        url_is_safe = is_safe_url(url=redirect_to, host=self.request.get_host())
        user_is_validated = self.request.user.is_verified()
        if url_is_safe and user_is_validated:
            return redirect_to
        return super(AdminSetupView, self).get_redirect_url()

admin_setup_view = AdminSetupView.as_view()


class AdminBackupTokensView(BackupTokensView):
    redirect_url = 'admin:two_factor:backup_tokens'
    success_url = 'admin:two_factor:backup_tokens'
    template_name = 'two_factor/admin/backup_tokens.html'

    def get_context_data(self, **kwargs):
        context = super(AdminBackupTokensView, self).get_context_data(**kwargs)
        context.update({
            'site_header': ugettext("Backup Tokens"),
            'title': ugettext("Backup Tokens"),
        })
        return context

admin_backup_tokens_view = AdminBackupTokensView.as_view()


class AdminProfileView(ProfileView):
    template_name = 'two_factor/admin/profile.html'

    def get_context_data(self, **kwargs):
        context = super(AdminProfileView, self).get_context_data(**kwargs)
        context.update({
            'site_header': ugettext("Account Security"),
            'title': ugettext("Account Security"),
        })
        return context

admin_profile_view = AdminProfileView.as_view()


class AdminDisableView(DisableView):
    template_name = 'two_factor/admin/disable.html'


admin_disable_view = AdminDisableView.as_view()


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


class AdminSiteOTPMixin(object):

    def get_urls(self):
        from django.conf.urls import include, url

        def wrap(view, cacheable=False):
            def wrapper(*args, **kwargs):
                return self.admin_view(view, cacheable)(*args, **kwargs)
            wrapper.admin_site = self
            return update_wrapper(wrapper, view)

        urlpatterns_2fa = [
            url(r'^qrcode/$', QRGeneratorView.as_view(), name='qr'),
            url(r'^profile/$', wrap(self.two_factor_profile), name='profile'),
            url(r'^profile/disable/$', wrap(self.two_factor_disable), name='disable'),
            url(r'^setup/$', self.two_factor_setup, name='setup'),
            url(r'^setup-complete/$', self.two_factor_setup_complete, name='setup_complete'),
            url(r'^backup/tokens/$', wrap(self.two_factor_backup_tokens), name='backup_tokens'),
        ]
        urlpatterns = [
            url(r'^two_factor/', include((urlpatterns_2fa, "two_factor"), namespace='two_factor'))
        ]
        urlpatterns += super(AdminSiteOTPMixin, self).get_urls()
        return urlpatterns

    def login(self, request, extra_context=None):
        return admin_login_view(request, extra_context=extra_context)

    def two_factor_profile(self, request):
        return admin_profile_view(request)

    def two_factor_setup(self, request):
        return admin_setup_view(request)

    def two_factor_disable(self, request):
        return admin_disable_view(request)

    def two_factor_setup_complete(self, request):
        return admin_setup_complete_view(request)

    def two_factor_backup_tokens(self, request):
        return admin_backup_tokens_view(request)

class AdminSiteOTP(AdminSiteOTPMixin, AdminSite):
    """
    AdminSite using OTP login.
    """
    pass


class AdminSiteOTPRequired(AdminSiteOTPMixin, AdminSiteOTPRequiredMixin, AdminSite):
    """
    AdminSite enforcing OTP verified staff users.
    """
    pass

__default_admin_site__ = None


def patch_admin():
    global __default_admin_site__
    __default_admin_site__ = admin.site.__class__
    if getattr(settings, 'TWO_FACTOR_FORCE_OTP_ADMIN', True):
        admin.site.__class__ = AdminSiteOTPRequired
    else:
        admin.site.__class__ = AdminSiteOTP


def unpatch_admin():
    global __default_admin_site__
    admin.site.__class__ = __default_admin_site__
    __default_admin_site__ = None


class PhoneDeviceAdmin(admin.ModelAdmin):
    """
    :class:`~django.contrib.admin.ModelAdmin` for
    :class:`~two_factor.models.PhoneDevice`.
    """
    raw_id_fields = ('user',)


admin.site.register(PhoneDevice, PhoneDeviceAdmin)
