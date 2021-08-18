from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template import loader
from django.utils.translation import gettext as _
from django_otp.models import Device, ThrottlingMixin
from django_otp.oath import totp

from two_factor.abstracts import TwoFactorModelBase


class EmailDevice(ThrottlingMixin, TwoFactorModelBase, Device):
    """Model with token seed linked to a user."""
    drift_range = range(-30, 1)

    def __repr__(self):
        return '<EmailDevice(email={!r})>'.format(self.user.email)

    def generate_challenge(self):
        # local import to avoid circular import
        from two_factor.utils import totp_digits

        """
        Sends the current TOTP token to `self.number` using `self.method`.
        """
        no_digits = totp_digits()
        token = str(totp(self.bin_key, digits=no_digits)).zfill(no_digits)
        send_email(device=self, token=token)

    def get_throttle_factor(self):
        return getattr(settings, 'TWO_FACTOR_EMAIL_THROTTLE_FACTOR', 1)


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
            _("Hello,\n"
              "Your email address has been given for two-factor authorization on the our website.\n"
              "If you did't do this, just ignore this message.\n\n"
              "Authentication token for user {user} is {token}."
              ).format(**{'user': device.user, 'token': token}),
        ),
        settings.DEFAULT_FROM_EMAIL,
        [device.user.email]
    )

    if getattr(settings, 'TWO_FACTOR_EMAIL_HTML', True):
        html = loader.render_to_string('two_factor/email/email_template.html',
                                       context={'user': device.user, 'token': token})
        email.attach_alternative(html, "text/html")

    email.send()
