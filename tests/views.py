from django.http import HttpResponse
from django.views.generic import TemplateView

from two_factor.views import LoginView, OTPRequiredMixin


class SecureView(OTPRequiredMixin, TemplateView):
    template_name = 'secure.html'


class LoginViewWithContext(LoginView):

    def post(self, *args, **kwargs):
        return super().post(*args, **kwargs)

    def get_device_context_data(self, **kwargs):
        return super().get_device_context_data(**kwargs) | {
            "test": "hello, test",
        }


def plain_view(request):
    """ Non-class based view """
    return HttpResponse('plain')
