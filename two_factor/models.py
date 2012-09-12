from django.utils.translation import ugettext_lazy as _
from django.db import models
from django.contrib.auth.models import User
from two_factor import call_gateways, sms_gateways

TOKEN_METHODS = [
    ('generator', 'Token generator (iPhone/Android App)'),
]
if call_gateways.GATEWAY:
    TOKEN_METHODS += [
        ('call', 'Phone call'),
    ]
if sms_gateways.GATEWAY:
    TOKEN_METHODS += [
        ('sms', 'Text message'),
    ]


class VerifiedComputer(models.Model):
    user = models.ForeignKey(User, verbose_name=_('verified computer'))
    verified_until = models.DateTimeField(_('verified until'))
    ip = models.IPAddressField(_('IP address'))
    last_used_at = models.DateTimeField(_('last used at'))


class Token(models.Model):
    user = models.OneToOneField(User, verbose_name=_('user'))
    seed = models.CharField(_('seed'), max_length=16)

    method = models.CharField(_('authentication method'), choices=TOKEN_METHODS,
        max_length=16)

    phone = models.CharField(_('phone number'), max_length=16)
    backup_phone = models.CharField(_('backup phone number'), max_length=16,
        null=True, blank=True)
