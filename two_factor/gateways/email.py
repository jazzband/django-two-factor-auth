from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.translation import gettext_lazy as _


class Email(object):
    """
    Gateway for sending text messages via email.
    Uses core django mail module.
    You need to configure your project mail settings first.

    ``TWO_FACTOR_EMAIL_SUBJECT``(default: ````)
      Custom email subject text

    ``TWO_FACTOR_EMAIL_HTML``(default: ``True``)
      Attach html version from `two_factor/email/email_template.html` to email or not.
    """
    def send_email(self, device, token):
        """
        send email using template 'two_factor/email/otp_message.html'
        """
        body = render_to_string(
            'two_factor/email/otp_message.html',
            {'token': token}
        )

        email = EmailMultiAlternatives(
            getattr(
                settings,
                'TWO_FACTOR_EMAIL_SUBJECT',
                _('Authentication token email')
            ),
            body,
            getattr(settings, 'DEFAULT_FROM_EMAIL', None),
            [device.email, ]
        )

        if getattr(settings, 'TWO_FACTOR_EMAIL_HTML', True):
            html = render_to_string('two_factor/email/email_template.html',
                                    {'token': token})
            email.attach_alternative(html, "text/html")

        email.send()
