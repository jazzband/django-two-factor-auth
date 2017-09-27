from binascii import unhexlify
import json
from time import time

from django import forms
from django.forms import Form, ModelForm
from django.utils.translation import ugettext_lazy as _
from django_otp.forms import OTPAuthenticationFormMixin
from django_otp.oath import totp
from django_otp.plugins.otp_totp.models import TOTPDevice

from .models import (
    PhoneDevice, U2FDevice, get_available_methods, get_available_phone_methods,
)
from .utils import totp_digits
from .validators import validate_international_phonenumber

from u2flib_server import u2f

try:
    from otp_yubikey.models import RemoteYubikeyDevice, YubikeyDevice
except ImportError:
    RemoteYubikeyDevice = YubikeyDevice = None


class MethodForm(forms.Form):
    method = forms.ChoiceField(label=_("Method"),
                               initial='generator',
                               widget=forms.RadioSelect)

    def __init__(self, disabled_methods=None, **kwargs):
        super(MethodForm, self).__init__(**kwargs)
        self.fields['method'].choices = get_available_methods(disabled_methods=disabled_methods)


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


class DeviceValidationForm(forms.Form):
    token = forms.IntegerField(label=_("Token"), min_value=1, max_value=int('9' * totp_digits()))

    error_messages = {
        'invalid_token': _('Entered token is not valid.'),
    }

    def __init__(self, device, **args):
        super(DeviceValidationForm, self).__init__(**args)
        self.device = device

    def clean_token(self):
        token = self.cleaned_data['token']
        if not self.device.verify_token(token):
            raise forms.ValidationError(self.error_messages['invalid_token'])
        return token


class YubiKeyDeviceForm(DeviceValidationForm):
    token = forms.CharField(label=_("YubiKey"))

    error_messages = {
        'invalid_token': _("The YubiKey could not be verified."),
    }

    def clean_token(self):
        self.device.public_id = self.cleaned_data['token'][:-32]
        return super(YubiKeyDeviceForm, self).clean_token()

class U2FDeviceForm(DeviceValidationForm):
    token = forms.CharField(label=_("Token"))

    def __init__(self, user, device, request, **kwargs):
        super(U2FDeviceForm, self).__init__(device, **kwargs)
        self.request = request
        self.user = user
        self.u2f_device = None
        self.appId = '{scheme}://{host}'.format(scheme='https' if self.request.is_secure() else 'http', host=self.request.get_host())

        if self.data:
            self.registration_request = self.request.session['u2f_registration_request']
        else:
            self.registration_request = u2f.begin_registration(self.appId, [key.to_json() for key in self.request.user.u2f_keys.all()])
            self.request.session['u2f_registration_request'] = self.registration_request

    def clean_token(self):
        response = self.cleaned_data['token']
        try:
            request = self.request.session['u2f_registration_request']
            u2f_device, attestation_cert = u2f.complete_registration(request, response)
            self.u2f_device = u2f_device
            if U2FDevice.objects.filter(public_key=self.u2f_device['publicKey']).count() > 0:
                raise forms.ValidationError("U2F device already exists in database: "+str(e))
        except ValueError as e:
            raise forms.ValidationError("U2F device could not be verified: "+str(e))
        return response

    def save(self):
        self.full_clean()
        name = None
        if len(self.request.user.u2f_keys.all()) == 0:
            name = "default"
        else:
            name = "key"
        return U2FDevice.objects.create(name=name, public_key=self.u2f_device['publicKey'], key_handle=self.u2f_device['keyHandle'], app_id=self.u2f_device['appId'], user=self.user)

class TOTPDeviceForm(forms.Form):
    token = forms.IntegerField(label=_("Token"), min_value=0, max_value=int('9' * totp_digits()))

    error_messages = {
        'invalid_token': _('Entered token is not valid.'),
    }

    def __init__(self, key, user, metadata=None, **kwargs):
        super(TOTPDeviceForm, self).__init__(**kwargs)
        self.key = key
        self.tolerance = 1
        self.t0 = 0
        self.step = 30
        self.drift = 0
        self.digits = totp_digits()
        self.user = user
        self.metadata = metadata or {}

    @property
    def bin_key(self):
        """
        The secret key as a binary string.
        """
        return unhexlify(self.key.encode())

    def clean_token(self):
        token = self.cleaned_data.get('token')
        validated = False
        t0s = [self.t0]
        key = self.bin_key
        if 'valid_t0' in self.metadata:
            t0s.append(int(time()) - self.metadata['valid_t0'])
        for t0 in t0s:
            for offset in range(-self.tolerance, self.tolerance):
                if totp(key, self.step, t0, self.digits, self.drift + offset) == token:
                    self.drift = offset
                    self.metadata['valid_t0'] = int(time()) - t0
                    validated = True
        if not validated:
            raise forms.ValidationError(self.error_messages['invalid_token'])
        return token

    def save(self):
        return TOTPDevice.objects.create(user=self.user, key=self.key,
                                         tolerance=self.tolerance, t0=self.t0,
                                         step=self.step, drift=self.drift,
                                         digits=self.digits,
                                         name='default')


class DisableForm(forms.Form):
    understand = forms.BooleanField(label=_("Yes, I am sure"))


class AuthenticationTokenForm(OTPAuthenticationFormMixin, Form):
    otp_token = forms.IntegerField(label=_("Token"), min_value=1,
                                   max_value=int('9' * totp_digits()))

    otp_token.widget.attrs.update({'autofocus': 'autofocus'})

    # Our authentication form has an additional submit button to go to the
    # backup token form. When the `required` attribute is set on an input
    # field, that button cannot be used on browsers that implement html5
    # validation. For now we'll use this workaround, but an even nicer
    # solution would be to move the button outside the `<form>` and into
    # its own `<form>`.
    use_required_attribute = False

    def __init__(self, user, initial_device, request, **kwargs):
        """
        `initial_device` is either the user's default device, or the backup
        device when the user chooses to enter a backup token. The token will
        be verified against all devices, it is not limited to the given
        device.
        """
        super(AuthenticationTokenForm, self).__init__(**kwargs)
        self.user = user
        self.request = request
        self.initial_device = initial_device
        self.appId = '{scheme}://{host}'.format(scheme='https' if self.request.is_secure() else 'http', host=self.request.get_host())

        # YubiKey generates a OTP of 44 characters (not digits). So if the
        # user's primary device is a YubiKey, replace the otp_token
        # IntegerField with a CharField.
        if RemoteYubikeyDevice and YubikeyDevice and \
                isinstance(initial_device, (RemoteYubikeyDevice, YubikeyDevice)):
            self.fields['otp_token'] = forms.CharField(label=_('YubiKey'))
        elif isinstance(initial_device, U2FDevice):
            self.fields['otp_token'] = forms.CharField(label=_('Token'))
            if self.data:
                self.sign_request = self.request.session['u2f_sign_request']
            else:
                self.sign_request = u2f.begin_authentication(self.appId, [key.to_json() for key in user.u2f_keys.all()])
                self.request.session['u2f_sign_request'] = self.sign_request

    def clean(self):
        if isinstance(self.initial_device, U2FDevice):
            response = json.loads(self.cleaned_data['otp_token'])
            request = self.request.session['u2f_sign_request']
            try:
                device, login_counter, _ = u2f.complete_authentication(request, response)
            except ValueError:
                self.add_error('__all__', 'U2F validation failed -- bad signature.')
        return self.cleaned_data


class BackupTokenForm(AuthenticationTokenForm):
    otp_token = forms.CharField(label=_("Token"))
