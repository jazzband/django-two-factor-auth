from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect
from django.views.decorators.cache import never_cache
from django.views.generic import TemplateView, FormView
from django_otp import user_has_device, devices_for_user

from ..forms import DisableForm
from ..utils import default_device, backup_phones
from .utils import class_view_decorator


@class_view_decorator(never_cache)
@class_view_decorator(login_required)
class ProfileView(TemplateView):
    template_name = 'two_factor/profile/profile.html'

    def get_context_data(self, **kwargs):
        try:
            backup_tokens = self.request.user.staticdevice_set.all()[0].token_set.count()
        except Exception:
            backup_tokens = 0

        return {
            'default_device': default_device(self.request.user),
            'default_device_type': default_device(self.request.user).__class__.__name__,
            'backup_phones': backup_phones(self.request.user),
            'backup_tokens': backup_tokens,
        }


@class_view_decorator(never_cache)
@class_view_decorator(login_required)
class DisableView(FormView):
    template_name = 'two_factor/profile/disable.html'
    form_class = DisableForm

    def get(self, request, *args, **kwargs):
        if not user_has_device(self.request.user):
            return redirect(str(settings.LOGIN_REDIRECT_URL))
        return super(DisableView, self).get(request, *args, **kwargs)

    def form_valid(self, form):
        for device in devices_for_user(self.request.user):
            device.delete()
        return redirect(str(settings.LOGIN_REDIRECT_URL))
