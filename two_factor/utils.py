from two_factor.models import PhoneDevice

from django_otp import devices_for_user


def default_device(user):
    if not user or user.is_anonymous():
        return
    for device in devices_for_user(user):
        if device.name == 'default':
            return device


def backup_phones(user):
    if not user or user.is_anonymous():
        return PhoneDevice.objects.none()
    return user.phonedevice_set.filter(name='backup')


def get_otpauth_url(alias, key):
    return 'otpauth://totp/%s?secret=%s' % (alias, key)


# from http://mail.python.org/pipermail/python-dev/2008-January/076194.html
def monkeypatch_method(cls):
    def decorator(func):
        setattr(cls, func.__name__, func)
        return func
    return decorator
