from django.conf import settings
from django.utils.translation import gettext_lazy as _


def backup_phones(user):
    if not user or user.is_anonymous:
        from .models import PhoneDevice
        return PhoneDevice.objects.none()
    return user.phonedevice_set.filter(name='backup')


def get_available_phone_methods():
    methods = []
    if getattr(settings, 'TWO_FACTOR_CALL_GATEWAY', None):
        methods.append(('call', _('Phone call')))
    if getattr(settings, 'TWO_FACTOR_SMS_GATEWAY', None):
        methods.append(('sms', _('Text message')))
    return methods
