from django.conf import settings
from django.test import TestCase, override_settings
from django.urls import reverse

from two_factor.plugins.registry import MethodNotFoundError, registry

from .utils import UserMixin


@override_settings(
    TWO_FACTOR_SMS_GATEWAY='two_factor.gateways.fake.Fake',
    TWO_FACTOR_CALL_GATEWAY='two_factor.gateways.fake.Fake',
)
class ProfileTest(UserMixin, TestCase):
    def setUp(self):
        super().setUp()
        self.user = self.create_user()
        self.enable_otp()
        self.login_user()

    def get_profile(self):
        url = reverse('two_factor:profile')
        return self.client.get(url)

    def test_get_profile_without_phonenumber_plugin_enabled(self):
        without_phonenumber_plugin = [
            app for app in settings.INSTALLED_APPS if app != 'two_factor.plugins.phonenumber']

        with override_settings(INSTALLED_APPS=without_phonenumber_plugin):
            with self.assertRaises(MethodNotFoundError):
                registry.get_method('call')
            with self.assertRaises(MethodNotFoundError):
                registry.get_method('sms')

            response = self.get_profile()

        self.assertTrue(response.context['available_phone_methods'] == [])

    def test_get_profile_with_phonenumer_plugin_enabled(self):
        self.assertTrue(registry.get_method('call'))
        self.assertTrue(registry.get_method('sms'))

        response = self.get_profile()
        available_phone_method_codes = {method.code for method in response.context['available_phone_methods']}
        self.assertTrue(available_phone_method_codes == {'call', 'sms'})
