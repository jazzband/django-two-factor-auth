from django.contrib.auth import REDIRECT_FIELD_NAME
from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import PermissionDenied


class OTPRequiredMixin(object):
    """
    View mixin which verifies that the user logged in using OTP.

    .. note::
       This mixin should be the left-most base class.
    """

    login_url = None
    raise_exception = False
    redirect_field_name = REDIRECT_FIELD_NAME

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_verified():
            if self.raise_exception:
                raise PermissionDenied()
            else:
                return redirect_to_login(request.get_full_path(),
                                         self.login_url,
                                         self.redirect_field_name)
        return super(OTPRequiredMixin, self).dispatch(request, *args, **kwargs)
