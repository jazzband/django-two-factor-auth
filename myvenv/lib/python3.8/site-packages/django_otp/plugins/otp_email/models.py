from django.core.mail import send_mail
from django.db import models
from django.template import Context, Template
from django.template.loader import get_template

from django_otp.models import SideChannelDevice, ThrottlingMixin
from django_otp.util import hex_validator, random_hex

from .conf import settings


def default_key():  # pragma: no cover
    """ Obsolete code here for migrations. """
    return random_hex(20)


def key_validator(value):  # pragma: no cover
    """ Obsolete code here for migrations. """
    return hex_validator()(value)


class EmailDevice(ThrottlingMixin, SideChannelDevice):
    """
    A :class:`~django_otp.models.SideChannelDevice` that delivers a token to
    the email address saved in this object or alternatively to the user's
    registered email address (``user.email``).

    The tokens are valid for :setting:`OTP_EMAIL_TOKEN_VALIDITY` seconds. Once
    a token has been accepted, it is no longer valid.

    Note that if you allow users to reset their passwords by email, this may
    provide little additional account security. It may still be useful for,
    e.g., requiring the user to re-verify their email address on new devices.

    .. attribute:: email

        *EmailField*: An alternative email address to send the tokens to.

    """
    email = models.EmailField(
        max_length=254,
        blank=True,
        null=True,
        help_text='Optional alternative email address to send tokens to'
    )

    def get_throttle_factor(self):
        return settings.OTP_EMAIL_THROTTLE_FACTOR

    def generate_challenge(self):
        """
        Generates a random token and emails it to the user.
        """
        self.generate_token(valid_secs=settings.OTP_EMAIL_TOKEN_VALIDITY)

        context = {'token': self.token}
        if settings.OTP_EMAIL_BODY_TEMPLATE:
            body = Template(settings.OTP_EMAIL_BODY_TEMPLATE).render(Context(context))
        else:
            body = get_template('otp/email/token.txt').render(context)

        send_mail(settings.OTP_EMAIL_SUBJECT,
                  body,
                  settings.OTP_EMAIL_SENDER,
                  [self.email or self.user.email])

        message = "sent by email"

        return message

    def verify_token(self, token):
        verify_allowed, _ = self.verify_is_allowed()
        if verify_allowed:
            verified = super().verify_token(token)

            if verified:
                self.throttle_reset()
            else:
                self.throttle_increment()
        else:
            verified = False

        return verified
