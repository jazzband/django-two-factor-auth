from django.http import HttpResponse
from django.views.generic import TemplateView

from two_factor.views import OTPRequiredMixin


class SecureView(OTPRequiredMixin, TemplateView):
    template_name = 'secure.html'


def plain_view(request):
    """ Non-class based view """
    return HttpResponse('plain')
