from django.views.generic import TemplateView
from two_factor.views import OTPRequiredMixin


class SecureView(OTPRequiredMixin, TemplateView):
    template_name = 'secure.html'
