from django.conf import settings
from django.test import TestCase, override_settings
from django.urls import reverse

from .utils import UserMixin


class ProfileTest(UserMixin, TestCase):
    PHONENUMBER_PLUGIN_NAME = 'two_factor.plugins.phonenumber'
    EXPECTED_BASE_CONTEXT_KEYS = {
        'default_device',
        'default_device_type',
        'backup_tokens',
    }
    EXPECTED_PHONENUMBER_PLUGIN_ADDITIONAL_KEYS = {
        'backup_phones',
        'available_phone_methods',
    }

    def setUp(self):
        super().setUp()
        self.user = self.create_user()
        self.enable_otp()
        self.login_user()

    @classmethod
    def get_installed_apps_list(cls, with_phone_number_plugin=True):
        apps = set(settings.INSTALLED_APPS)
        if with_phone_number_plugin:
            apps.add(cls.PHONENUMBER_PLUGIN_NAME)
        else:
            apps.remove(cls.PHONENUMBER_PLUGIN_NAME)
        return list(apps)

    def get_profile(self):
        url = reverse('two_factor:profile')
        return self.client.get(url)

    def test_get_profile_without_phonenumer_plugin_enabled(self):
        apps_list = self.get_installed_apps_list(with_phone_number_plugin=False)
        with override_settings(INSTALLED_APPS=apps_list):
            response = self.get_profile()
            context_keys = set(response.context.keys())
            self.assertTrue(self.EXPECTED_BASE_CONTEXT_KEYS.issubset(context_keys))
            # None of the phonenumber related keys are present
            self.assertTrue(
                self.EXPECTED_PHONENUMBER_PLUGIN_ADDITIONAL_KEYS.isdisjoint(
                    context_keys
                )
            )

    def test_get_profile_with_phonenumer_plugin_enabled(self):
        apps_list = self.get_installed_apps_list(with_phone_number_plugin=True)
        with override_settings(INSTALLED_APPS=apps_list):
            response = self.get_profile()
            context_keys = set(response.context.keys())
            expected_keys = (
                self.EXPECTED_BASE_CONTEXT_KEYS
                | self.EXPECTED_PHONENUMBER_PLUGIN_ADDITIONAL_KEYS
            )
            self.assertTrue(expected_keys.issubset(context_keys))
