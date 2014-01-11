from django.views.generic import TemplateView
from two_factor.views import OTPRequiredMixin


class SecureView(OTPRequiredMixin, TemplateView):
    template_name = 'secure.html'


class SecureRaisingView(OTPRequiredMixin, TemplateView):
    raise_exception = True
    template_name = 'secure.html'
