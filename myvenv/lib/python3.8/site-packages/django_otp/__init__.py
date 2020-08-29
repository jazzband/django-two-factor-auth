from django.contrib.auth.signals import user_logged_in


DEVICE_ID_SESSION_KEY = 'otp_device_id'


def login(request, device):
    """
    Persist the given OTP device in the current session. The device will be
    rejected if it does not belong to ``request.user``.

    This is called automatically any time :func:`django.contrib.auth.login` is
    called with a user having an ``otp_device`` atribute. If you use Django's
    :func:`~django.contrib.auth.views.login` view with the django-otp
    authentication forms, then you won't need to call this.

    :param request: The HTTP request
    :type request: :class:`~django.http.HttpRequest`

    :param device: The OTP device used to verify the user.
    :type device: :class:`~django_otp.models.Device`
    """
    user = getattr(request, 'user', None)

    if (user is not None) and (device is not None) and (device.user_id == user.pk):
        request.session[DEVICE_ID_SESSION_KEY] = device.persistent_id
        request.user.otp_device = device


def _handle_auth_login(sender, request, user, **kwargs):
    """
    Automatically persists an OTP device that was set by an OTP-aware
    AuthenticationForm.
    """
    if hasattr(user, 'otp_device'):
        login(request, user.otp_device)


user_logged_in.connect(_handle_auth_login)


def match_token(user, token):
    """
    Attempts to verify a :term:`token` on every device attached to the given
    user until one of them succeeds. When possible, you should prefer to verify
    tokens against specific devices.

    :param user: The user supplying the token.
    :type user: :class:`~django.contrib.auth.models.User`

    :param string token: An OTP token to verify.

    :returns: The device that accepted ``token``, if any.
    :rtype: :class:`~django_otp.models.Device` or ``None``
    """
    matches = (d for d in devices_for_user(user) if d.verify_token(token))

    return next(matches, None)


def devices_for_user(user, confirmed=True):
    """
    Return an iterable of all devices registered to the given user.

    Returns an empty iterable for anonymous users.

    :param user: standard or custom user object.
    :type user: :class:`~django.contrib.auth.models.User`

    :param confirmed: If ``None``, all matching devices are returned.
        Otherwise, this can be any true or false value to limit the query
        to confirmed or unconfirmed devices, respectively.

    :rtype: iterable
    """
    if user.is_anonymous:
        return

    for model in device_classes():
        for device in model.objects.devices_for_user(user, confirmed=confirmed):
            yield device


def user_has_device(user, confirmed=True):
    """
    Return ``True`` if the user has at least one device.

    Returns ``False`` for anonymous users.

    :param user: standard or custom user object.
    :type user: :class:`~django.contrib.auth.models.User`

    :param confirmed: If ``None``, all matching devices are considered.
        Otherwise, this can be any true or false value to limit the query
        to confirmed or unconfirmed devices, respectively.
    """
    try:
        next(devices_for_user(user, confirmed=confirmed))
    except StopIteration:
        has_device = False
    else:
        has_device = True

    return has_device


def device_classes():
    """
    Returns an iterable of all loaded device models.
    """
    from django.apps import apps           # isort: skip
    from django_otp.models import Device

    for config in apps.get_app_configs():
        for model in config.get_models():
            if issubclass(model, Device):
                yield model
