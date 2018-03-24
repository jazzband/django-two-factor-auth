from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template import loader
from django.utils.module_loading import import_string
from django.utils.translation import ugettext_lazy as _


def get_gateway_class(import_path):
    return import_string(import_path)


def make_call(device, token):
    gateway = get_gateway_class(getattr(settings, 'TWO_FACTOR_CALL_GATEWAY'))()
    gateway.make_call(device=device, token=token)


def send_sms(device, token):
    gateway = get_gateway_class(getattr(settings, 'TWO_FACTOR_SMS_GATEWAY'))()
    gateway.send_sms(device=device, token=token)


def send_email(device, token):
    email = EmailMultiAlternatives(
        getattr(
            settings,
            'TWO_FACTOR_EMAIL_SUBJECT',
            _('Authentication token email')
        ),
        getattr(
            settings,
            'TWO_FACTOR_EMAIL_TEXT',
            _('Authentication token for user {user} is {token}.')
        ).format(**{'user': device.user, 'token': token}),
        getattr(settings, 'DEFAULT_FROM_EMAIL', None),
        [device.user.email, ]
    )

    if getattr(settings, 'TWO_FACTOR_EMAIL_HTML', True):
        html = loader.render_to_string('two_factor/email/email_template.html',
                                       context={'user': device.user, 'token': token})
        email.attach_alternative(html, "text/html")

    email.send()
