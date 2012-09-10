# coding=utf-8
from django.utils.translation import ugettext_lazy as _
from django.db import models
from django.contrib.auth.models import User

class VerifiedComputer(models.Model):
    user = models.ForeignKey(User, verbose_name=_('verified computer'))
    verified_until = models.DateTimeField(_('verified until'))
    ip = models.IPAddressField(_('IP address'))
    last_used_at = models.DateTimeField(_('last used at'))


class Secret(models.Model):
    user = models.OneToOneField(User, verbose_name=_('user'))
    seed = models.CharField(_('secret'), max_length=16)
