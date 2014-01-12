from django.views.generic import TemplateView
from two_factor.views import OTPRequiredMixin


class SecureView(OTPRequiredMixin, TemplateView):
    raise_anonymous = False
    raise_unverified = False
    template_name = 'secure.html'


class SecureRaisingView(OTPRequiredMixin, TemplateView):
    raise_anonymous = False
    raise_unverified = True
    template_name = 'secure.html'
