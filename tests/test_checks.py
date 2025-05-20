from django.core.checks import Error, Warning
from django.test import TestCase, override_settings

from two_factor import checks


class InstallAppOrderCheckTest(TestCase):
    @override_settings(INSTALLED_APPS=("django_otp", "two_factor", "two_factor.plugins.email"))
    def test_correct(self):
        self.assertEqual(checks.check_installed_app_order(None), [])

    @override_settings(INSTALLED_APPS=("django_otp", "two_factor.plugins.email", "two_factor"))
    def test_incorrect(self):
        self.assertEqual(checks.check_installed_app_order(None),
            [Error(checks.INSTALLED_APPS_MSG, hint=checks.INSTALLED_APPS_HINT, id=checks.INSTALLED_APPS_ID)])

    @override_settings(INSTALLED_APPS=("django_otp", "two_factor.apps.TwoFactorConfig", "two_factor.plugins.email"))
    def test_two_factor_not_found(self):
        self.assertEqual(checks.check_installed_app_order(None),
            [Warning(checks.MISSING_MSG, hint=checks.MISSING_HINT, id=checks.MISSING_ID)])
