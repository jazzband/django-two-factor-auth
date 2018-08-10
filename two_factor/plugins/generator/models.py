from django.utils.translation import ugettext_lazy as _
from django_otp.plugins.otp_totp.models import TOTPDevice

from ...utils import monkeypatch_method

TOTPDevice.generate_challenge_button_title = property(lambda self: _('Token generator'))
