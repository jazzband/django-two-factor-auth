from binascii import unhexlify

from django.apps import AppConfig
from django.conf import settings
from django.contrib.sites.shortcuts import get_current_site
from django.utils.translation import ugettext_lazy as _

from .utils import get_otpauth_qrcode_image_uri


class TwoFactorGeneratorConfig(AppConfig):
    name = 'two_factor.plugins.generator'
    verbose_name = "Django Two Factor Authentication - Generator Method"

    def get_method_from_device(self, device):
        from django_otp.plugins.otp_totp.models import TOTPDevice
        if isinstance(device, TOTPDevice):
            return 'generator'

    def get_two_factor_available_methods(self):
        return [
            ('generator', _('Token generator')),
        ]

    def get_two_factor_backup_devices(self, user):
        from django_otp.plugins.otp_totp.models import TOTPDevice
        if not user or user.is_anonymous:
            return TOTPDevice.objects.none()
        return user.totpdevice_set.filter(name='backup')

    def get_device_setup_form(self, method):
        from .forms import TOTPDeviceForm
        return TOTPDeviceForm

    def get_device_validation_form(self, method):
        return None

    def get_device_setup_form_kwargs(self, method, user, key, metadata):
        return {
            'key': key,
            'user': user,
        }

    def get_device_validation_form_kwargs(self, method, user, key, metadata, setup):
        return {}

    def get_device_setup_context_data(self, view, form):
        key = view.get_key()
        return {
            'QR_URL': self.get_otpauth_qrcode_image_uri(view.request, key)
        }

    def get_otpauth_qrcode_image_uri(self, request, key):
        assert isinstance(key, str), 'hex-encoded key expected'
        accountname = request.user.get_username()
        secret = unhexlify(key)
        issuer = get_current_site(request).name
        return get_otpauth_qrcode_image_uri(accountname, secret, issuer)
