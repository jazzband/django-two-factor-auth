from django.apps import apps
from django.utils.translation import gettext_lazy as _

from .base import Method

try:
    import yubiotp  # NOQA
    from otp_yubikey.models import ValidationService, RemoteYubikeyDevice
    libs_available = True
except ImportError:
    libs_available = False


class YubiKeyMethod(Method):
    code = 'yubikey'
    verbose_name = _('YubiKey')
    form_path = 'two_factor.forms.YubiKeyDeviceForm'

    def is_available(self):
        return libs_available and apps.is_installed('otp_yubikey')

    def get_device(self, user, key, validated_data):
        if not self.is_available():
            return None

        public_id = validated_data.get('token', '')[:-32]
        try:
            service = ValidationService.objects.get(name='default')
        except ValidationService.DoesNotExist:
            raise KeyError("No ValidationService found with name 'default'")
        except ValidationService.MultipleObjectsReturned:
            raise KeyError("Multiple ValidationService found with name 'default'")
        return RemoteYubikeyDevice(
            name='default', user=user, public_id=public_id, service=service
        )
