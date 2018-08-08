from binascii import unhexlify
from time import time

from django import forms
from django.forms import Form, ModelForm
from django.utils.translation import ugettext_lazy as _
from django_otp.forms import OTPAuthenticationFormMixin
from django_otp.oath import totp
from django_otp.plugins.otp_totp.models import TOTPDevice

from .models import PhoneDevice, get_available_phone_methods
from ...utils import totp_digits, get_available_methods
from ...validators import validate_international_phonenumber

class PhoneNumberMethodForm(ModelForm):
    number = forms.CharField(label=_("Phone Number"),
                             validators=[validate_international_phonenumber])
    method = forms.ChoiceField(widget=forms.RadioSelect, label=_('Method'))

    class Meta:
        model = PhoneDevice
        fields = 'number', 'method',

    def __init__(self, **kwargs):
        super(PhoneNumberMethodForm, self).__init__(**kwargs)
        self.fields['method'].choices = get_available_phone_methods()


class PhoneNumberForm(ModelForm):
    # Cannot use PhoneNumberField, as it produces a PhoneNumber object, which cannot be serialized.
    number = forms.CharField(label=_("Phone Number"),
                             validators=[validate_international_phonenumber])

    class Meta:
        model = PhoneDevice
        fields = 'number',
