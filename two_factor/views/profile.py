from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, resolve_url
from django.utils.decorators import method_decorator
from django.utils.functional import lazy
from django.views.decorators.cache import never_cache
from django.views.generic import FormView, TemplateView
from django_otp import devices_for_user
from django_otp.decorators import otp_required

from two_factor.plugins.phonenumber.utils import (
    backup_phones, get_available_phone_methods,
)

from ..forms import DisableForm
from ..utils import default_device


@method_decorator([never_cache, login_required], name='dispatch')
class ProfileView(TemplateView):
    """
    View used by users for managing two-factor configuration.

    This view shows whether two-factor has been configured for the user's
    account. If two-factor is enabled, it also lists the primary verification
    method and backup verification methods.
    """
    template_name = 'two_factor/profile/profile.html'

    def get_context_data(self, **kwargs):
        user = self.request.user

        try:
            backup_tokens = user.staticdevice_set.all()[0].token_set.count()

        except Exception:
            backup_tokens = 0

        context = {
            'default_device': default_device(user),
            'default_device_type': default_device(user).__class__.__name__,
            'backup_tokens': backup_tokens,
            'backup_phones': backup_phones(user),
            'available_phone_methods': get_available_phone_methods(),
        }

        return context


@method_decorator(never_cache, name='dispatch')
class DisableView(FormView):
    """
    View for disabling two-factor for a user's account.
    """
    template_name = 'two_factor/profile/disable.html'
    success_url = lazy(resolve_url, str)(settings.LOGIN_REDIRECT_URL)
    form_class = DisableForm

    def dispatch(self, *args, **kwargs):
        # We call otp_required here because we want to use self.success_url as
        # the login_url. Using it as a class decorator would make it difficult
        # for users who wish to override this property
        fn = otp_required(super().dispatch, login_url=self.success_url, redirect_field_name=None)
        return fn(*args, **kwargs)

    def form_valid(self, form):
        for device in devices_for_user(self.request.user):
            device.delete()
        return redirect(self.success_url)
