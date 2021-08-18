from django.core.signals import setting_changed
from django.dispatch import Signal, receiver

# Signal additional parameters are: request, user, and device.
user_verified = Signal()


@receiver(setting_changed, dispatch_uid="two_factor.handle_setting_changed")
def handle_setting_changed(sender, setting: str, value, **kwargs):
    from .admin import __default_admin_site__, patch_admin, unpatch_admin

    is_patched = __default_admin_site__ is not None

    if setting == "TWO_FACTOR_PATCH_ADMIN":
        if value is True and not is_patched:
            patch_admin()
        elif value is False and is_patched:
            unpatch_admin()

    elif setting == "TWO_FACTOR_FORCE_OTP_ADMIN":
        if is_patched:
            unpatch_admin()
            patch_admin()
