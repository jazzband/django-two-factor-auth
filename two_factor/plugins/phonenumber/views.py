import logging
import warnings
from base64 import b32encode
from binascii import unhexlify

import django_otp
import qrcode
import qrcode.image.svg
from django.conf import settings
from django.contrib.auth import REDIRECT_FIELD_NAME, login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.sites.shortcuts import get_current_site
from django.forms import Form
from django.http import Http404, HttpResponse
from django.shortcuts import redirect, resolve_url
from django.urls import reverse
from django.utils.http import is_safe_url
from django.utils.module_loading import import_string
from django.views.decorators.cache import never_cache
from django.views.decorators.debug import sensitive_post_parameters
from django.views.generic import DeleteView, FormView, TemplateView
from django.views.generic.base import View
from django_otp.decorators import otp_required
from django_otp.plugins.otp_static.models import StaticDevice, StaticToken
from django_otp.util import random_hex

from ... import signals
from ...forms import (
    AuthenticationTokenForm, BackupTokenForm, DeviceValidationForm, MethodForm,
    #PhoneNumberForm, PhoneNumberMethodForm,
    TOTPDeviceForm, YubiKeyDeviceForm,
)
from .forms import (
    PhoneNumberForm, PhoneNumberMethodForm,
)
#from ..models import PhoneDevice, get_available_phone_methods
from ...utils import (
    #backup_phones,
    get_otpauth_url, default_device, get_available_methods,
    totp_digits
)

from ...views.utils import IdempotentSessionWizardView, class_view_decorator

try:
    from otp_yubikey.models import ValidationService, RemoteYubikeyDevice
except ImportError:
    ValidationService = RemoteYubikeyDevice = None


logger = logging.getLogger(__name__)


@class_view_decorator(never_cache)
@class_view_decorator(otp_required)
class PhoneSetupView(IdempotentSessionWizardView):
    """
    View for configuring a phone number for receiving tokens.

    A user can have multiple backup :class:`~two_factor.models.PhoneDevice`
    for receiving OTP tokens. If the primary phone number is not available, as
    the battery might have drained or the phone is lost, these backup phone
    numbers can be used for verification.
    """
    template_name = 'two_factor/core/phone_register.html'
    success_url = settings.LOGIN_REDIRECT_URL
    form_list = (
        ('setup', PhoneNumberMethodForm),
        ('validation', DeviceValidationForm),
    )
    key_name = 'key'

    def get(self, request, *args, **kwargs):
        """
        Start the setup wizard. Redirect if no phone methods available.
        """
        if not get_available_phone_methods():
            return redirect(self.success_url)
        return super(PhoneSetupView, self).get(request, *args, **kwargs)

    def done(self, form_list, **kwargs):
        """
        Store the device and redirect to profile page.
        """
        self.get_device(user=self.request.user, name='backup').save()
        return redirect(self.success_url)

    def render_next_step(self, form, **kwargs):
        """
        In the validation step, ask the device to generate a challenge.
        """
        next_step = self.steps.next
        if next_step == 'validation':
            self.get_device().generate_challenge()
        return super(PhoneSetupView, self).render_next_step(form, **kwargs)

    def get_form_kwargs(self, step=None):
        """
        Provide the device to the DeviceValidationForm.
        """
        if step == 'validation':
            return {'device': self.get_device()}
        return {}

    def get_device(self, **kwargs):
        """
        Uses the data from the setup step and generated key to recreate device.
        """
        kwargs = kwargs or {}
        kwargs.update(self.storage.validated_step_data.get('setup', {}))
        return PhoneDevice(key=self.get_key(), **kwargs)

    def get_key(self):
        """
        The key is preserved between steps and stored as ascii in the session.
        """
        if self.key_name not in self.storage.extra_data:
            key = random_hex(20).decode('ascii')
            self.storage.extra_data[self.key_name] = key
        return self.storage.extra_data[self.key_name]

    def get_context_data(self, form, **kwargs):
        kwargs.setdefault('cancel_url', resolve_url(self.success_url))
        return super(PhoneSetupView, self).get_context_data(form, **kwargs)


@class_view_decorator(never_cache)
@class_view_decorator(otp_required)
class PhoneDeleteView(DeleteView):
    """
    View for removing a phone number used for verification.
    """
    success_url = settings.LOGIN_REDIRECT_URL

    def get_queryset(self):
        return self.request.user.phonedevice_set.filter(name='backup')

    def get_success_url(self):
        return resolve_url(self.success_url)
