from django.utils.translation import gettext_lazy as _
from django_otp.plugins.otp_email.models import EmailDevice

from django.contrib.humanize.templatetags.humanize import naturaltime
from django.core.mail import send_mail
from django.db import models
from django.template import Context, Template
from django.template.loader import get_template
from django.utils.translation import gettext

from django_otp.models import (
    CooldownMixin,
    GenerateNotAllowed,
    SideChannelDevice,
    ThrottlingMixin,
    TimestampMixin,
)
from django_otp.util import hex_validator, random_hex

from django_otp.plugins.otp_email.conf import settings

from two_factor.plugins.registry import MethodBase

from .forms import AuthenticationTokenForm, DeviceValidationForm, EmailForm
from .utils import mask_email


class EmailDeviceProxy(EmailDevice):
    class Meta:
        proxy = True

    def generate_challenge(self, extra_context=None):
        """
        Generates a random token and emails it to the user.

        :param extra_context: Additional context variables for rendering the
            email template.
        :type extra_context: dict

        """
        generate_allowed, data_dict = self.generate_is_allowed()
        if generate_allowed:
            message = self._deliver_token(extra_context)
        else:
            if data_dict['reason'] == GenerateNotAllowed.COOLDOWN_DURATION_PENDING:
                next_generation_naturaltime = naturaltime(
                    data_dict['next_generation_at']
                )
                message = (
                    "Token generation cooldown period has not expired yet. Next"
                    f" generation allowed {next_generation_naturaltime}."
                )
            else:
                message = "Token generation is not allowed at this time"

        return message

    def _deliver_token(self, extra_context):
        commit = extra_context.get('commit', True)

        self.cooldown_set(commit=False)
        self.generate_token(valid_secs=settings.OTP_EMAIL_TOKEN_VALIDITY, commit=commit)

        context = {'token': self.token, **(extra_context or {})}
        if settings.OTP_EMAIL_BODY_TEMPLATE:
            body = Template(settings.OTP_EMAIL_BODY_TEMPLATE).render(Context(context))
        else:
            body = get_template(settings.OTP_EMAIL_BODY_TEMPLATE_PATH).render(context)

        if settings.OTP_EMAIL_BODY_HTML_TEMPLATE:
            body_html = Template(settings.OTP_EMAIL_BODY_HTML_TEMPLATE).render(
                Context(context)
            )
        elif settings.OTP_EMAIL_BODY_HTML_TEMPLATE_PATH:
            body_html = get_template(settings.OTP_EMAIL_BODY_HTML_TEMPLATE_PATH).render(
                context
            )
        else:
            body_html = None

        self.send_mail(body, html_message=body_html)

        message = gettext("sent by email")

        return message

class EmailMethod(MethodBase):
    code = 'email'
    verbose_name = _('Email')

    def get_devices(self, user):
        return EmailDeviceProxy.objects.devices_for_user(user).all()

    def recognize_device(self, device):
        return isinstance(device, EmailDeviceProxy)

    def get_setup_forms(self, wizard):
        forms = {}
        if not wizard.request.user.email:
            forms[self.code] = EmailForm
        forms['validation'] = DeviceValidationForm
        return forms

    def get_device_from_setup_data(self, request, setup_data, **kwargs):
        if setup_data and not request.user.email:
            request.user.email = setup_data.get('email').get('email')
            request.user.save(update_fields=['email'])
        device = EmailDeviceProxy.objects.devices_for_user(request.user).first()
        if not device:
            device = EmailDeviceProxy(user=request.user, name='default')
        return device

    def get_token_form_class(self):
        return AuthenticationTokenForm

    def get_action(self, device):
        email = device.email or device.user.email
        return _('Send email to %s') % (email and mask_email(email) or None,)

    def get_verbose_action(self, device):
        return _('We sent you an email, please enter the token we sent.')
