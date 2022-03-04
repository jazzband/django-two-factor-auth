from binascii import unhexlify

from django.db import models
from django_otp.oath import totp
from django_otp.util import hex_validator, random_hex


def key_validator(*args, **kwargs):
    """Wraps hex_validator generator, to keep makemigrations happy."""
    return hex_validator()(*args, **kwargs)


class TwoFactorModelBase(models.Model):
    class Meta:
        abstract = True

    drift_range = None
    key = models.CharField(max_length=40,
                           validators=[key_validator],
                           default=random_hex,
                           help_text="Hex-encoded secret key")

    @property
    def bin_key(self):
        return unhexlify(self.key.encode())

    def verify_token(self, token):
        # local import to avoid circular import
        from two_factor.utils import totp_digits

        try:
            token = int(token)
        except ValueError:
            return False

        for drift in self.drift_range:
            if totp(self.bin_key, drift=drift, digits=totp_digits()) == token:
                return True
        return False
