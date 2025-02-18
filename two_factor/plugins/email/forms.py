from django import forms
from django.utils.translation import gettext_lazy as _

from two_factor.forms import (
    AuthenticationTokenForm as BaseAuthenticationTokenForm,
    DeviceValidationForm as BaseValidationForm,
)


class EmailForm(forms.Form):
    email = forms.EmailField(label=_("Email address"))

    def __init__(self, **kwargs):
        kwargs.pop('device', None)
        super().__init__(**kwargs)


class DeviceValidationForm(BaseValidationForm):
    token = forms.CharField(label=_("Token"))
    token.widget.attrs.update({'autofocus': 'autofocus',
                               'autocomplete': 'one-time-code'})
    idempotent = False  # Once validated, the token is cleared.

    # TODO we probably don't need a device here.
    def __init__(self, key, device, **kwargs):
        super().__init__(device, **kwargs)
        print("Pax was in email.forms.DeviceValidationForm.__init__. Key is {}".format(key))
        self.key = key

    def clean_token(self):
        print("Pax was in email.forms.DeviceValidationForm.clean_token")
        token = self.cleaned_data['token']
        if not self.device.verify_token(token):
            raise forms.ValidationError(self.error_messages['invalid_token'])
        return token


class AuthenticationTokenForm(BaseAuthenticationTokenForm):
    def _chosen_device(self, user):
        return self.initial_device
