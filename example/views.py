from django.conf import settings
from django.contrib.auth.forms import UserCreationForm
from django.shortcuts import redirect, resolve_url
from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache
from django.views.generic import FormView, TemplateView

from two_factor.views import OTPRequiredMixin


class HomeView(TemplateView):
    template_name = 'home.html'


class RegistrationView(FormView):
    template_name = 'registration.html'
    form_class = UserCreationForm

    def form_valid(self, form):
        form.save()
        return redirect('registration_complete')


class RegistrationCompleteView(TemplateView):
    template_name = 'registration_complete.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['login_url'] = resolve_url(settings.LOGIN_URL)
        return context


@method_decorator(never_cache, name='dispatch')
class ExampleSecretView(OTPRequiredMixin, TemplateView):
    template_name = 'secret.html'
