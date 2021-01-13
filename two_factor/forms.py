from binascii import unhexlify
import json
from time import time

from django import forms
from django.conf import settings
from django.forms import Form, ModelForm
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django_otp.forms import OTPAuthenticationFormMixin
from django_otp.oath import totp
from django_otp.plugins.otp_totp.models import TOTPDevice

from . import webauthn_utils
from .models import (
    PhoneDevice, WebauthnDevice, get_available_methods, get_available_phone_methods,
)
from .utils import totp_digits
from .validators import validate_international_phonenumber

try:
    from otp_yubikey.models import RemoteYubikeyDevice, YubikeyDevice
except ImportError:
    RemoteYubikeyDevice = YubikeyDevice = None


class MethodForm(forms.Form):
    method = forms.ChoiceField(label=_("Method"),
                               initial='generator',
                               widget=forms.RadioSelect)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.fields['method'].choices = get_available_methods()


class PhoneNumberMethodForm(ModelForm):
    number = forms.CharField(label=_("Phone Number"),
                             validators=[validate_international_phonenumber])
    method = forms.ChoiceField(widget=forms.RadioSelect, label=_('Method'))

    class Meta:
        model = PhoneDevice
        fields = 'number', 'method',

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
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

    token.widget.attrs.update({'autofocus': 'autofocus',
                               'inputmode': 'numeric',
                               'autocomplete': 'one-time-code'})
    error_messages = {
        'invalid_token': _('Entered token is not valid.'),
    }

    def __init__(self, device, **args):
        super().__init__(**args)
        self.device = device

    def clean_token(self):
        token = self.cleaned_data['token']
        if not self.device.verify_token(token):
            raise forms.ValidationError(self.error_messages['invalid_token'])
        return token


class WebauthnDeviceForm(forms.Form):
    token = forms.CharField(
        label=_("WebAuthn Token"),
        widget=forms.PasswordInput(attrs={
            'autofocus': 'autofocus',
            'inputmode': 'none',
            'autocomplete': 'one-time-code',
        })
    )

    class Media:
        js = ('js/webauthn_utils.js', )

    def _get_relying_party(self):
        return {
            'id': self.request.get_host(),
            'name': settings.TWO_FACTOR_WEBAUTHN_RP_NAME
        }

    def _get_origin(self):
        return '{scheme}://{host}'.format(
            scheme='https' if self.request.is_secure() else 'http', host=self.request.get_host()
        )

    def __init__(self, user, request, **kwargs):
        super(WebauthnDeviceForm, self).__init__(**kwargs)
        self.request = request
        self.user = user
        self.webauthn_device_info = None

        if self.data:
            self.registration_request = self.request.session['webauthn_registration_request']
        else:
            make_credential_options = webauthn_utils.make_credentials_options(user, self._get_relying_party())
            self.registration_request = json.dumps(make_credential_options)
            self.request.session['webauthn_registration_request'] = self.registration_request

    def clean_token(self):
        response = json.loads(self.cleaned_data['token'])
        try:
            request = json.loads(self.request.session['webauthn_registration_request'])
            webauthn_registration_response = webauthn_utils.make_registration_response(
                request, response, self._get_relying_party(), self._get_origin()
            )

            credentials = webauthn_registration_response.verify()
            key_format = webauthn_utils.get_response_key_format(response)

            self.webauthn_device_info = dict(
                keyHandle=credentials.credential_id.decode('utf-8'),
                publicKey=credentials.public_key.decode('utf-8'),
                signCount=credentials.sign_count,
                format=key_format,
            )

        except Exception as e:
            message = e.args[0] if e.args else _('an unknown error happened.')
            raise forms.ValidationError(_('Token validation failed: %s') % (message, ))
        return response

    def save(self):
        self.full_clean()
        name = 'secondary'
        if self.webauthn_device_info['format']:
            name += f' ({self.webauthn_device_info["format"]})'

        if len(self.request.user.webauthn_keys.all()) == 0:
            name = "default"

        return WebauthnDevice.objects.create(
            name=name,
            public_key=self.webauthn_device_info['publicKey'],
            key_handle=self.webauthn_device_info['keyHandle'],
            sign_count=self.webauthn_device_info['signCount'],
            user=self.user
        )


class YubiKeyDeviceForm(DeviceValidationForm):
    token = forms.CharField(label=_("YubiKey"), widget=forms.PasswordInput())

    error_messages = {
        'invalid_token': _("The YubiKey could not be verified."),
    }

    def clean_token(self):
        self.device.public_id = self.cleaned_data['token'][:-32]
        return super().clean_token()


class TOTPDeviceForm(forms.Form):
    token = forms.IntegerField(label=_("Token"), min_value=0, max_value=int('9' * totp_digits()))

    token.widget.attrs.update({'autofocus': 'autofocus',
                               'inputmode': 'numeric',
                               'autocomplete': 'one-time-code'})

    error_messages = {
        'invalid_token': _('Entered token is not valid.'),
    }

    def __init__(self, key, user, metadata=None, **kwargs):
        super().__init__(**kwargs)
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

    otp_token.widget.attrs.update({'autofocus': 'autofocus',
                                   'inputmode': 'numeric',
                                   'autocomplete': 'one-time-code'})

    # Our authentication form has an additional submit button to go to the
    # backup token form. When the `required` attribute is set on an input
    # field, that button cannot be used on browsers that implement html5
    # validation. For now we'll use this workaround, but an even nicer
    # solution would be to move the button outside the `<form>` and into
    # its own `<form>`.
    use_required_attribute = False

    class Media:
        js = ('js/webauthn_utils.js', )

    def _get_relying_party(self):
        return {
            'id': self.request.get_host(),
            'name': settings.TWO_FACTOR_WEBAUTHN_RP_NAME
        }

    def _get_origin(self):
        return '{scheme}://{host}'.format(
            scheme='https' if self.request.is_secure() else 'http', host=self.request.get_host()
        )

    def __init__(self, user, initial_device, request, **kwargs):
        """
        `initial_device` is either the user's default device, or the backup
        device when the user chooses to enter a backup token. The token will
        be verified against all devices, it is not limited to the given
        device.
        """
        super().__init__(**kwargs)
        self.user = user
        self.initial_device = initial_device
        self.request = request

        # YubiKey generates a OTP of 44 characters (not digits). So if the
        # user's primary device is a YubiKey, replace the otp_token
        # IntegerField with a CharField.
        if RemoteYubikeyDevice and YubikeyDevice and \
                isinstance(initial_device, (RemoteYubikeyDevice, YubikeyDevice)):
            self.fields['otp_token'] = forms.CharField(label=_('YubiKey'), widget=forms.PasswordInput())
        elif isinstance(initial_device, WebauthnDevice):
            self.fields['otp_token'] = forms.CharField(label=_('WebAuthn Token'), widget=forms.PasswordInput())
            if self.data:
                self.sign_request = self.request.session['webauthn_sign_request']
            else:
                relying_party = self._get_relying_party()
                webauthn_assertion_options = webauthn_utils.make_assertion_options(user, relying_party)
                self.sign_request = json.dumps(webauthn_assertion_options)
                self.request.session['webauthn_sign_request'] = self.sign_request

        # Add a field to remember this browser.
        if getattr(settings, 'TWO_FACTOR_REMEMBER_COOKIE_AGE', None):
            if settings.TWO_FACTOR_REMEMBER_COOKIE_AGE < 3600:
                minutes = int(settings.TWO_FACTOR_REMEMBER_COOKIE_AGE / 60)
                label = _("Don't ask again on this device for %(minutes)i minutes") % {'minutes': minutes}
            elif settings.TWO_FACTOR_REMEMBER_COOKIE_AGE < 3600 * 24:
                hours = int(settings.TWO_FACTOR_REMEMBER_COOKIE_AGE / 3600)
                label = _("Don't ask again on this device for %(hours)i hours") % {'hours': hours}
            else:
                days = int(settings.TWO_FACTOR_REMEMBER_COOKIE_AGE / 3600 / 24)
                label = _("Don't ask again on this device for %(days)i days") % {'days': days}

            self.fields['remember'] = forms.BooleanField(
                required=False,
                initial=True,
                label=label
            )

    def clean(self):
        otp_token = self.cleaned_data.get('otp_token')
        if otp_token and isinstance(self.initial_device, WebauthnDevice):
            # simulate what is done in the self.clean_otp
            self.user.otp_device = None
            request = json.loads(self.request.session['webauthn_sign_request'])

            try:
                response = json.loads(otp_token)
                device = webauthn_utils.get_device_used_in_response(self.user, response)
                if self.initial_device is None:
                    raise forms.ValidationError('Could not find valid credentials in the response')

                self.initial_device = device
                webauthn_assertion_response = webauthn_utils.make_assertion_response(
                    self.user, self._get_relying_party(), self._get_origin(), self.initial_device, request, response
                )
                sign_count = webauthn_assertion_response.verify()
                self.initial_device.sign_count = sign_count
                self.initial_device.last_used_at = timezone.now()
                self.initial_device.save()

                self.user.otp_device = self.initial_device
            except json.JSONDecodeError:
                self.add_error('otp_token', _('Invalid WebAuthn token'))
            except Exception as e:
                message = e.args[0] if e.args else _('an unknown error happened.')
                self.add_error('otp_token', _('Token validation failed: %s') % (message, ))

        else:
            self.clean_otp(self.user)

        return self.cleaned_data


class BackupTokenForm(AuthenticationTokenForm):
    otp_token = forms.CharField(label=_("Token"))
