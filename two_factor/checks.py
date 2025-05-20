from django.conf import settings
from django.core.checks import Error, Warning, register

INSTALLED_APPS_MSG = "two_factor should come before its plugins in INSTALLED_APPS"
INSTALLED_APPS_HINT = "Check documentation for proper ordering."
INSTALLED_APPS_ID = "two_factor.E001"

MISSING_MSG = "Could not reliably determine where in INSTALLED_APPS two_factor appears"
MISSING_HINT = INSTALLED_APPS_HINT
MISSING_ID = "two_factor.W001"

@register()
def check_installed_app_order(app_configs, **kwargs):
    """Check the order in which two_factor and its plugins are loaded"""
    apps = [app for app in settings.INSTALLED_APPS if app.startswith("two_factor")]
    if "two_factor" not in apps:
        # user might be using "two_factor.apps.TwoFactorConfig" or their own
        # custom app config for two_factor, so give them a warning
        return [Warning(
            MISSING_MSG,
            hint=MISSING_HINT,
            id=MISSING_ID,
        )]
    elif apps[0] != "two_factor":
        return [Error(
            INSTALLED_APPS_MSG,
            hint=INSTALLED_APPS_HINT,
            id=INSTALLED_APPS_ID,
        )]

    return []
