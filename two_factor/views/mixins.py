try:
    from urllib.parse import urlencode
except ImportError:
    from urllib import urlencode

from django.conf import settings
from django.contrib.auth import REDIRECT_FIELD_NAME
from django.core.exceptions import PermissionDenied, ImproperlyConfigured
from django.shortcuts import redirect


class OTPRequiredMixin(object):
    """
    View mixin which verifies that the user logged in using OTP.

    .. note::
       This mixin should be the left-most base class.
    """

    login_url = None
    raise_exception = False
    redirect_field_name = REDIRECT_FIELD_NAME

    def get_login_url(self):
        """
        Returns login url to redirect to.
        """
        login_url = self.login_url or settings.LOGIN_URL
        if not login_url:
            raise ImproperlyConfigured(
                "Define %(cls)s.login_url or settings.LOGIN_URL or override "
                "%(cls)s.get_login_url()." % {"cls": self.__class__.__name__})
        return str(login_url)

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_verified():
            if self.raise_exception:
                raise PermissionDenied()
            else:
                return redirect('%s?%s' % (
                    self.get_login_url(),
                    urlencode({self.redirect_field_name: request.get_full_path()})
                ))
        return super(OTPRequiredMixin, self).dispatch(request, *args, **kwargs)
