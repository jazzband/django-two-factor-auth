from binascii import unhexlify
from base64 import b32encode

from django.conf import settings
from django.contrib.auth import login as login, REDIRECT_FIELD_NAME
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.sites.models import get_current_site
from django.core.urlresolvers import reverse
from django.forms import Form
from django.http import HttpResponse, Http404
from django.shortcuts import redirect
from django.views.decorators.cache import never_cache
from django.views.generic import FormView, DeleteView, TemplateView
from django.views.generic.base import View

import django_otp
from django_otp.decorators import otp_required
from django_otp.plugins.otp_static.models import StaticToken, StaticDevice
from django_otp.util import random_hex
from two_factor import signals

try:
    from otp_yubikey.models import ValidationService, RemoteYubikeyDevice
except ImportError:
    ValidationService = RemoteYubikeyDevice = None

import qrcode
import qrcode.image.svg

from ..compat import is_safe_url, import_by_path
from ..forms import (MethodForm, TOTPDeviceForm, PhoneNumberMethodForm,
                     DeviceValidationForm, AuthenticationTokenForm,
                     PhoneNumberForm, BackupTokenForm, YubiKeyDeviceForm)
from ..models import PhoneDevice, get_available_phone_methods
from ..utils import (get_otpauth_url, default_device,
                     backup_phones)
from .utils import (IdempotentSessionWizardView, class_view_decorator)


@class_view_decorator(never_cache)
class LoginView(IdempotentSessionWizardView):
    """
    View for handling the login process, including OTP verification.

    The login process is composed like a wizard. The first step asks for the
    user's credentials. If the credentials are correct, the wizard proceeds to
    the OTP verification step. If the user has a default OTP device configured,
    that device is asked to generate a token (send sms / call phone) and the
    user is asked to provide the generated token. The backup devices are also
    listed, allowing the user to select a backup device for verification.
    """
    template_name = 'two_factor/core/login.html'
    form_list = (
        ('auth', AuthenticationForm),
        ('token', AuthenticationTokenForm),
        ('backup', BackupTokenForm),
    )
    idempotent_dict = {
        'token': False,
        'backup': False,
    }

    def has_token_step(self):
        return default_device(self.get_user())

    def has_backup_step(self):
        return default_device(self.get_user()) and \
            'token' not in self.storage.validated_step_data

    condition_dict = {
        'token': has_token_step,
        'backup': has_backup_step,
    }
    redirect_field_name = REDIRECT_FIELD_NAME

    def __init__(self, **kwargs):
        super(LoginView, self).__init__(**kwargs)
        self.user_cache = None
        self.device_cache = None

    def post(self, *args, **kwargs):
        """
        The user can select a particular device to challenge, being the backup
        devices added to the account.
        """
        if 'challenge_device' in self.request.POST:
            return self.render_goto_step('token')
        return super(LoginView, self).post(*args, **kwargs)

    def done(self, form_list, **kwargs):
        """
        Login the user and redirect to the desired page.
        """
        login(self.request, self.get_user())

        redirect_to = self.request.GET.get(self.redirect_field_name, '')
        if not is_safe_url(url=redirect_to, host=self.request.get_host()):
            redirect_to = str(settings.LOGIN_REDIRECT_URL)

        device = getattr(self.get_user(), 'otp_device', None)
        if device:
            signals.user_verified.send(sender=__name__, request=self.request,
                                       user=self.get_user(), device=device)
        return redirect(redirect_to)

    def get_form_kwargs(self, step=None):
        """
        AuthenticationTokenForm requires the user kwarg.
        """
        if step in ('token', 'backup'):
            return {
                'user': self.get_user(),
                'initial_device': self.get_device(step),
            }
        return {}

    def get_device(self, step=None):
        """
        Returns the OTP device selected by the user, or his default device.
        """
        if not self.device_cache:
            challenge_device_id = self.request.POST.get('challenge_device', None)
            if challenge_device_id:
                for device in backup_phones(self.get_user()):
                    if device.persistent_id == challenge_device_id:
                        self.device_cache = device
                        break
            if step == 'backup':
                try:
                    self.device_cache = self.get_user().staticdevice_set.get(name='backup')
                except StaticDevice.DoesNotExist:
                    pass
            if not self.device_cache:
                self.device_cache = default_device(self.get_user())
        return self.device_cache

    def render(self, form=None, **kwargs):
        """
        If the user selected a device, ask the device to generate a challenge;
        either making a phone call or sending a text message.
        """
        if self.steps.current == 'token':
            self.get_device().generate_challenge()
        return super(LoginView, self).render(form, **kwargs)

    def get_user(self):
        """
        Returns the user authenticated by the AuthenticationForm.
        """
        if not self.user_cache:
            form_obj = self.get_form(step='auth',
                                     data=self.storage.get_step_data('auth'))
            self.user_cache = form_obj.is_valid() and form_obj.user_cache
        return self.user_cache

    def get_context_data(self, form, **kwargs):
        """
        Adds user's default and backup OTP devices to the context.
        """
        context = super(LoginView, self).get_context_data(form, **kwargs)
        if self.steps.current == 'token':
            context['device'] = self.get_device()
            context['other_devices'] = [
                phone for phone in backup_phones(self.get_user())
                if phone != self.get_device()]
            try:
                context['backup_tokens'] = self.get_user().staticdevice_set\
                    .get(name='backup').token_set.count()
            except StaticDevice.DoesNotExist:
                context['backup_tokens'] = 0

        context['cancel_url'] = settings.LOGOUT_URL
        return context


@class_view_decorator(never_cache)
@class_view_decorator(login_required)
class SetupView(IdempotentSessionWizardView):
    """
    View for handling OTP setup using a wizard.

    The first step of the wizard shows an introduction text, explaining how OTP
    works and why it should be enabled. The user has to select the verification
    method (generator / call / sms) in the second step. Depending on the method
    selected, the third step configures the device. For the generator method, a
    QR code is shown which can be scanned using a mobile phone app and the user
    is asked to provide a generated token. For call and sms methods, the user
    provides the phone number which is then validated in the final step.
    """
    redirect_url = 'two_factor:setup_complete'
    qrcode_url = 'two_factor:qr'
    template_name = 'two_factor/core/setup.html'
    session_key_name = 'django_two_factor-qr_secret_key'
    initial_dict = {}
    form_list = (
        ('welcome', Form),
        ('method', MethodForm),
        ('generator', TOTPDeviceForm),
        ('sms', PhoneNumberForm),
        ('call', PhoneNumberForm),
        ('validation', DeviceValidationForm),
        ('yubikey', YubiKeyDeviceForm),
    )
    condition_dict = {
        'generator': lambda self: self.get_method() == 'generator',
        'call': lambda self: self.get_method() == 'call',
        'sms': lambda self: self.get_method() == 'sms',
        'validation': lambda self: self.get_method() in ('sms', 'call'),
        'yubikey': lambda self: self.get_method() == 'yubikey',
    }
    idempotent_dict = {
        'yubikey': False,
    }

    def get_method(self):
        method_data = self.storage.validated_step_data.get('method', {})
        return method_data.get('method', None)

    def get(self, request, *args, **kwargs):
        """
        Start the setup wizard. Redirect if already enabled.
        """
        if default_device(self.request.user):
            return redirect(self.redirect_url)
        return super(SetupView, self).get(request, *args, **kwargs)

    def render_next_step(self, form, **kwargs):
        """
        In the validation step, ask the device to generate a challenge.
        """
        next_step = self.steps.next
        if next_step == 'validation':
            self.get_device().generate_challenge()
        return super(SetupView, self).render_next_step(form, **kwargs)

    def done(self, form_list, **kwargs):
        """
        Finish the wizard. Save all forms and redirect.
        """
        # TOTPDeviceForm
        if self.get_method() == 'generator':
            form = [form for form in form_list if isinstance(form, TOTPDeviceForm)][0]
            device = form.save()

        # PhoneNumberForm / YubiKeyDeviceForm
        elif self.get_method() in ('call', 'sms', 'yubikey'):
            device = self.get_device()
            device.save()

        else:
            raise NotImplementedError("Unknown method '%s'" % self.get_method())

        django_otp.login(self.request, device)
        return redirect(self.redirect_url)

    def get_form_kwargs(self, step=None):
        kwargs = {}
        if step == 'generator':
            kwargs.update({
                'key': self.get_key(step),
                'user': self.request.user,
            })
        if step in ('validation', 'yubikey'):
            kwargs.update({
                'device': self.get_device()
            })
        metadata = self.get_form_metadata(step)
        if metadata:
            kwargs.update({
                'metadata': metadata,
            })
        return kwargs

    def get_device(self, **kwargs):
        """
        Uses the data from the setup step and generated key to recreate device.

        Only used for call / sms -- generator uses other procedure.
        """
        method = self.get_method()
        kwargs = kwargs or {}
        kwargs['name'] = 'default'
        kwargs['user'] = self.request.user

        if method in ('call', 'sms'):
            kwargs['method'] = method
            kwargs['number'] = self.storage.validated_step_data\
                .get(method, {}).get('number')
            return PhoneDevice(key=self.get_key(method), **kwargs)

        if method == 'yubikey':
            kwargs['public_id'] = self.storage.validated_step_data\
                .get('yubikey', {}).get('token', '')[:-32]
            try:
                kwargs['service'] = ValidationService.objects.get(name='default')
            except ValidationService.DoesNotExist:
                raise KeyError("No ValidationService found with name 'default'")
            except ValidationService.MultipleObjectsReturned:
                raise KeyError("Multiple ValidationService found with name 'default'")
            return RemoteYubikeyDevice(**kwargs)

    def get_key(self, step):
        self.storage.extra_data.setdefault('keys', {})
        if step in self.storage.extra_data['keys']:
            return self.storage.extra_data['keys'].get(step)
        key = random_hex(20).decode('ascii')
        self.storage.extra_data['keys'][step] = key
        return key

    def get_context_data(self, form, **kwargs):
        context = super(SetupView, self).get_context_data(form, **kwargs)
        if self.steps.current == 'generator':
            key = self.get_key('generator')
            rawkey = unhexlify(key.encode('ascii'))
            b32key = b32encode(rawkey).decode('utf-8')
            self.request.session[self.session_key_name] = b32key
            context.update({
                'QR_URL': reverse(self.qrcode_url)
            })
        elif self.steps.current == 'validation':
            context['device'] = self.get_device()
        context['cancel_url'] = settings.LOGIN_REDIRECT_URL
        return context

    def process_step(self, form):
        if hasattr(form, 'metadata'):
            self.storage.extra_data.setdefault('forms', {})
            self.storage.extra_data['forms'][self.steps.current] = form.metadata
        return super(SetupView, self).process_step(form)

    def get_form_metadata(self, step):
        self.storage.extra_data.setdefault('forms', {})
        return self.storage.extra_data['forms'].get(step, None)


@class_view_decorator(never_cache)
@class_view_decorator(otp_required)
class BackupTokensView(FormView):
    """
    View for listing and generating backup tokens.

    A user can generate a number of static backup tokens. When the user loses
    its phone, these backup tokens can be used for verification. These backup
    tokens should be stored in a safe location; either in a safe or underneath
    a pillow ;-).
    """
    form_class = Form
    redirect_url = 'two_factor:backup_tokens'
    template_name = 'two_factor/core/backup_tokens.html'
    number_of_tokens = 10

    def get_device(self):
        return self.request.user.staticdevice_set.get_or_create(name='backup')[0]

    def get_context_data(self, **kwargs):
        context = super(BackupTokensView, self).get_context_data(**kwargs)
        context['device'] = self.get_device()
        return context

    def form_valid(self, form):
        """
        Delete existing backup codes and generate new ones.
        """
        device = self.get_device()
        device.token_set.all().delete()
        for n in range(self.number_of_tokens):
            device.token_set.create(token=StaticToken.random_token())

        return redirect(self.redirect_url)


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
    redirect_url = None
    form_list = (
        ('setup', PhoneNumberMethodForm),
        ('validation', DeviceValidationForm),
    )
    key_name = 'key'

    def done(self, form_list, **kwargs):
        """
        Store the device and redirect to profile page.
        """
        self.get_device(user=self.request.user, name='backup').save()
        return redirect(self.redirect_url or str(settings.LOGIN_REDIRECT_URL))

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
        kwargs.setdefault('cancel_url', settings.LOGIN_REDIRECT_URL)
        return super(PhoneSetupView, self).get_context_data(form, **kwargs)


@class_view_decorator(never_cache)
@class_view_decorator(otp_required)
class PhoneDeleteView(DeleteView):
    """
    View for removing a phone number used for verification.
    """
    def get_queryset(self):
        return self.request.user.phonedevice_set.filter(name='backup')

    def get_success_url(self):
        return str(settings.LOGIN_REDIRECT_URL)


@class_view_decorator(never_cache)
@class_view_decorator(otp_required)
class SetupCompleteView(TemplateView):
    """
    View congratulation the user when OTP setup has completed.
    """
    template_name = 'two_factor/core/setup_complete.html'

    def get_context_data(self):
        return {
            'phone_methods': get_available_phone_methods(),
        }


@class_view_decorator(never_cache)
@class_view_decorator(login_required)
class QRGeneratorView(View):
    """
    View returns an SVG image with the OTP token information
    """
    http_method_names = ['get']
    default_qr_factory = 'qrcode.image.svg.SvgPathImage'
    session_key_name = 'django_two_factor-qr_secret_key'

    # The qrcode library only supports PNG and SVG for now
    image_content_types = {
        'PNG': 'image/png',
        'SVG': 'image/svg+xml; charset=utf-8',
    }

    def get(self, request, *args, **kwargs):
        # Get the data from the session
        try:
            key = self.request.session[self.session_key_name]
            del self.request.session[self.session_key_name]
        except KeyError:
            raise Http404()

        # Get data for qrcode
        image_factory_string = getattr(settings, 'TWO_FACTOR_QR_FACTORY', self.default_qr_factory)
        image_factory = import_by_path(image_factory_string)
        content_type = self.image_content_types[image_factory.kind]
        try:
            username = self.request.user.get_username()
        except AttributeError:
            username = self.request.user.username

        site_name = get_current_site(self.request).name
        alias = '{site_name}:{username}'.format(
            username=username, site_name=site_name)

        # Make and return QR code
        img = qrcode.make(get_otpauth_url(alias, key, site_name), image_factory=image_factory)
        resp = HttpResponse(content_type=content_type)
        img.save(resp)
        return resp
