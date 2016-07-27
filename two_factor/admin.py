from functools import update_wrapper

from django.conf import settings
from django.contrib import admin
from django.contrib.admin import AdminSite
from django.contrib.auth import REDIRECT_FIELD_NAME
from django.contrib.auth.views import redirect_to_login
from django.core.urlresolvers import reverse
from django.shortcuts import resolve_url
from django.utils.http import is_safe_url
from django.utils.translation import ugettext

from .models import PhoneDevice
from .utils import monkeypatch_method
from .views import BackupTokensView, LoginView, ProfileView, SetupView


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
        redirect_to = self.request.GET.get(self.redirect_field_name, '')
        url_is_safe = is_safe_url(url=redirect_to, host=self.request.get_host())
        if url_is_safe:
            self.request.session[REDIRECT_FIELD_NAME] = redirect_to
        user_is_validated = getattr(self.request.user, 'is_verified', None)
        if not url_is_safe or not user_is_validated:
            redirect_to = resolve_url(self.redirect_url)
        return redirect_to


admin_login_view = AdminLoginView.as_view()


class AdminSetupView(SetupView):
    form_templates = {
        'method': 'two_factor/admin/_wizard_form_method.html',
        'generator': 'two_factor/admin/_wizard_form_generator.html',
        'sms': 'two_factor/admin/_wizard_form_phone_number.html',
        'call': 'two_factor/admin/_wizard_form_phone_number.html',
        'validation': 'two_factor/admin/_wizard_form_validation.html',
        'yubikey': 'two_factor/admin/_wizard_form_yubikey.html',
    }
    redirect_url = 'admin:two_factor:profile'
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

    def get_redirect_url(self):
        redirect_to = self.request.session.pop(REDIRECT_FIELD_NAME, '')
        url_is_safe = is_safe_url(url=redirect_to, host=self.request.get_host())
        user_is_validated = self.request.user.is_verified()
        if url_is_safe and user_is_validated:
            return redirect_to
        return super(AdminSetupView, self).get_redirect_url()

admin_setup_view = AdminSetupView.as_view()


class AdminBackupTokensView(BackupTokensView):
    redirect_url = 'admin:two_factor:backup_tokens'
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

    def get_urls(self):
        from django.conf.urls import include, url

        def wrap(view, cacheable=False):
            def wrapper(*args, **kwargs):
                return self.admin_view(view, cacheable)(*args, **kwargs)
            wrapper.admin_site = self
            return update_wrapper(wrapper, view)

        urlpatterns_2fa = [
            url(r'^profile/$', wrap(self.two_factor_profile), name='profile'),
            url(r'^setup/$', self.two_factor_setup, name='setup'),
            url(r'^backup/tokens/$', wrap(self.two_factor_backup_tokens), name='backup_tokens'),
        ]

        urlpatterns = [
            url(r'^two_factor/', include(urlpatterns_2fa, namespace='two_factor'))
        ]
        urlpatterns += super(AdminSiteOTPRequiredMixin, self).get_urls()
        return urlpatterns

    def login(self, request, extra_context=None):
        return admin_login_view(request, extra_context=extra_context)

    def two_factor_profile(self, request):
        return admin_profile_view(request)

    def two_factor_setup(self, request):
        return admin_setup_view(request)

    def two_factor_backup_tokens(self, request):
        return admin_backup_tokens_view(request)


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

        if not redirect_to or not is_safe_url(url=redirect_to, host=request.get_host()):
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
