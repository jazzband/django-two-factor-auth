from django.conf import settings
from django_otp import devices_for_user

from .models import PhoneDevice

try:
    from urllib.parse import quote, urlencode
except ImportError:
    from urllib import quote, urlencode


def backup_phones(user):
    if not user or user.is_anonymous:
        return PhoneDevice.objects.none()
    return user.phonedevice_set.filter(name='backup')
