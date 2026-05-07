from urllib.parse import quote, urlencode

from django.conf import settings
from django.utils.module_loading import import_string
from django_otp import devices_for_user
from django_otp.plugins.otp_static.models import StaticDevice

USER_DEFAULT_DEVICE_ATTR_NAME = "_default_device"


def default_device(user, confirmed=True):
    """Return the user's primary 2FA device, or ``None`` if they have none.

    The selection policy lives in a separate callable resolved at
    call-time (see :func:`_get_default_device_picker`). Projects can
    override the built-in policy by setting
    ``TWO_FACTOR_DEFAULT_DEVICE_PICKER`` to the dotted path of any
    callable taking ``(devices: list) -> Device | None``. The setting
    is resolved per call (not cached at import time), so projects can
    swap pickers without restart-time gymnastics.

    Built-in policy (when the setting is unset, see
    :func:`_pick_default_device` for the implementation):

    1. A device explicitly named ``"default"``. This preserves
       behaviour for existing deployments: the upstream setup wizard
       names the first enrolled device ``"default"``, and many projects
       have years of users with a primary device under that name. Such
       deployments see no behaviour change.
    2. The most-recently-used non-backup device (``last_used_at``
       descending). For users with multiple named devices, this is
       what they intuitively expect: the one they used last time
       becomes the primary at next login - useful for users who
       rotate between e.g. a YubiKey and a TOTP app.
    3. The non-backup device with the lowest ``persistent_id`` as a
       deterministic tie-breaker, used when the user has devices but
       has not yet logged in with any of them (fresh enrollment).

    Backup devices are excluded by the built-in picker:
    ``StaticDevice`` (one-time backup tokens) and any device with
    ``name == 'backup'`` (the convention also used by
    :func:`~two_factor.plugins.phonenumber.utils.backup_phones`).
    Custom pickers receive the unfiltered device list and may apply
    whatever policy they need; ``primary_device_candidates`` is
    exported as a public helper for the common case of "filter
    backups out then decide".

    The cache attribute on the user object (``USER_DEFAULT_DEVICE_ATTR_NAME``,
    introduced in PR #466) is preserved. Negative results are not
    cached, so a device enrolled later in the same request is found.
    """
    if not user or user.is_anonymous:
        return None
    if hasattr(user, USER_DEFAULT_DEVICE_ATTR_NAME):
        return getattr(user, USER_DEFAULT_DEVICE_ATTR_NAME)

    devices = list(devices_for_user(user, confirmed=confirmed))
    chosen = _get_default_device_picker()(devices)
    if chosen is not None:
        setattr(user, USER_DEFAULT_DEVICE_ATTR_NAME, chosen)
    return chosen


def _get_default_device_picker():
    """Return the configured default-device picker callable.

    Resolves ``TWO_FACTOR_DEFAULT_DEVICE_PICKER`` (a dotted path) at
    call-time so settings overrides in tests and post-startup config
    changes take effect immediately. Falls back to the built-in
    :func:`_pick_default_device` when the setting is unset.
    """
    path = getattr(settings, 'TWO_FACTOR_DEFAULT_DEVICE_PICKER', None)
    if path:
        return import_string(path)
    return _pick_default_device


def primary_device_candidates(devices):
    """Filter ``devices`` to those eligible to be the user's primary 2FA device.

    Excludes ``StaticDevice`` (backup tokens) and any device named
    ``"backup"`` (the convention used elsewhere in the codebase, see
    :func:`~two_factor.plugins.phonenumber.utils.backup_phones`).

    Public so custom :setting:`TWO_FACTOR_DEFAULT_DEVICE_PICKER`
    callables can apply the same backup-exclusion logic without
    re-implementing it.
    """
    return [
        d for d in devices
        if not isinstance(d, StaticDevice) and d.name != 'backup'
    ]


def _pick_default_device(devices):
    """Built-in default-device selection policy.

    See :func:`default_device` for the rules. Split out so it's
    testable in isolation (no DB / user object needed) and so the
    :setting:`TWO_FACTOR_DEFAULT_DEVICE_PICKER` hook can swap it.
    """
    candidates = primary_device_candidates(devices)

    for device in candidates:
        if device.name == 'default':
            return device

    used = [d for d in candidates if getattr(d, 'last_used_at', None) is not None]
    if used:
        return max(used, key=lambda d: d.last_used_at)

    if candidates:
        return min(candidates, key=lambda d: d.persistent_id)

    return None


def get_otpauth_url(accountname, secret, issuer=None, digits=None):
    # For a complete run-through of all the parameters, have a look at the
    # specs at:
    # https://github.com/google/google-authenticator/wiki/Key-Uri-Format

    # quote and urlencode work best with bytes, not unicode strings.
    accountname = accountname.encode('utf8')
    issuer = issuer.encode('utf8') if issuer else None

    label = quote(b': '.join([issuer, accountname]) if issuer else accountname)

    # Ensure that the secret parameter is the FIRST parameter of the URI, this
    # allows Microsoft Authenticator to work.
    query = [
        ('secret', secret),
        ('digits', digits or totp_digits())
    ]

    if issuer:
        query.append(('issuer', issuer))

    return 'otpauth://totp/%s?%s' % (label, urlencode(query))


# from http://mail.python.org/pipermail/python-dev/2008-January/076194.html
def monkeypatch_method(cls):
    def decorator(func):
        setattr(cls, func.__name__, func)
        return func
    return decorator


def totp_digits():
    """
    Returns the number of digits (as configured by the TWO_FACTOR_TOTP_DIGITS setting)
    for totp tokens. Defaults to 6
    """
    return getattr(settings, 'TWO_FACTOR_TOTP_DIGITS', 6)
