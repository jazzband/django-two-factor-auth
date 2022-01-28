from django.conf import settings
from django.utils.translation import gettext_lazy as _

try:
    import yubiotp
except ImportError:
    yubiotp = None


def get_available_yubikey_methods():
    methods = []
    if yubiotp and 'otp_yubikey' in settings.INSTALLED_APPS:
        methods.append(('yubikey', _('YubiKey')))
    return methods
