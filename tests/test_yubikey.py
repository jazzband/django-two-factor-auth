import unittest
from unittest.mock import patch

from django import forms
from django.apps import apps
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.shortcuts import resolve_url
from django.test import TestCase, override_settings
from django.urls import reverse

from .utils import UserMixin

try:
    from otp_yubikey.models import RemoteYubikeyDevice, ValidationService

    from two_factor.plugins.yubikey.method import YubikeyMethod
except ImportError:
    ValidationService = RemoteYubikeyDevice = None


@unittest.skipUnless(ValidationService, 'No YubiKey support')
class YubiKeyTest(UserMixin, TestCase):
    @patch('otp_yubikey.models.RemoteYubikeyDevice.verify_token')
    def test_setup(self, verify_token):
        user = self.create_user()
        self.login_user()
        verify_token.return_value = [True, False]  # only first try is valid

        # Should be able to select YubiKey method
        response = self.client.post(reverse('two_factor:setup'),
                                    data={'setup_view-current_step': 'welcome'})
        self.assertContains(response, 'YubiKey')

        # Without ValidationService it won't work
        with self.assertRaisesMessage(KeyError, "No ValidationService "
                                                "found with name 'default'"):
            self.client.post(reverse('two_factor:setup'),
                             data={'setup_view-current_step': 'method',
                                   'method-method': 'yubikey'})

        # With a ValidationService, should be able to input a YubiKey
        ValidationService.objects.create(name='default', param_sl='', param_timeout='')

        response = self.client.post(reverse('two_factor:setup'),
                                    data={'setup_view-current_step': 'method',
                                          'method-method': 'yubikey'})
        self.assertContains(response, 'YubiKey:')

        # Should call verify_token and create the device on finish
        token = 'jlvurcgekuiccfcvgdjffjldedjjgugk'
        response = self.client.post(reverse('two_factor:setup'),
                                    data={'setup_view-current_step': 'yubikey',
                                          'yubikey-token': token})
        self.assertRedirects(response, reverse('two_factor:setup_complete'))
        verify_token.assert_called_with(token)

        yubikeys = user.remoteyubikeydevice_set.all()
        self.assertEqual(len(yubikeys), 1)
        self.assertEqual(yubikeys[0].name, 'default')

    @patch('otp_yubikey.models.RemoteYubikeyDevice.verify_token')
    def test_login(self, verify_token):
        user = self.create_user()
        verify_token.return_value = [True, False]  # only first try is valid
        service = ValidationService.objects.create(name='default', param_sl='', param_timeout='')
        user.remoteyubikeydevice_set.create(service=service, name='default')

        # Input type should be text, not numbers like other tokens
        response = self.client.post(reverse('two_factor:login'),
                                    data={'auth-username': 'bouke@example.com',
                                          'auth-password': 'secret',
                                          'login_view-current_step': 'auth'})
        self.assertContains(response, 'YubiKey:')
        self.assertIsInstance(response.context_data['wizard']['form'].fields['otp_token'],
                              forms.CharField)

        # Should call verify_token
        token = 'cjikftknbiktlitnbltbitdncgvrbgic'
        response = self.client.post(reverse('two_factor:login'),
                                    data={'token-otp_token': token,
                                          'login_view-current_step': 'token'})
        self.assertRedirects(response, resolve_url(settings.LOGIN_REDIRECT_URL))
        verify_token.assert_called_with(token)

    def test_show_correct_label(self):
        """
        The token form replaces the input field when the user's device is a
        YubiKey. However when the user decides to enter a backup token, the
        normal backup token form should be shown. Refs #50.
        """
        user = self.create_user()
        service = ValidationService.objects.create(name='default', param_sl='', param_timeout='')
        user.remoteyubikeydevice_set.create(service=service, name='default')
        backup = user.staticdevice_set.create(name='backup')
        backup.token_set.create(token='RANDOM')

        response = self.client.post(reverse('two_factor:login'),
                                    data={'auth-username': 'bouke@example.com',
                                          'auth-password': 'secret',
                                          'login_view-current_step': 'auth'})
        self.assertContains(response, 'YubiKey:')

        response = self.client.post(reverse('two_factor:login'),
                                    data={'wizard_goto_step': 'backup'})
        self.assertNotContains(response, 'YubiKey:')
        self.assertContains(response, 'Token:')

    def test_missing_management_data(self):
        # missing management data
        response = self.client.post(reverse('two_factor:login'),
                                    data={'auth-username': 'bouke@example.com',
                                          'auth-password': 'secret'})

        # view should return HTTP 400 Bad Request
        self.assertEqual(response.status_code, 400)

    def test_double_validation_service(self):
        ValidationService.objects.create(
            name='default', use_ssl=True, param_sl='', param_timeout=''
        )
        ValidationService.objects.create(
            name='default', use_ssl=True, param_sl='', param_timeout=''
        )
        msg = "Multiple ValidationService found with name 'default'"
        with self.assertRaisesMessage(KeyError, msg):
            YubikeyMethod().get_device_from_setup_data(None, {})

    @patch('two_factor.plugins.yubikey.apps.apps.is_installed', return_value=False)
    def test_no_otp_yubikey_installed(self, *args):
        msg = "'otp_yubikey' must be installed to be able to use the yubikey plugin."
        with self.assertRaisesMessage(ImproperlyConfigured, msg):
            apps.get_app_config('yubikey').ready()

    @override_settings(TWO_FACTOR_REMEMBER_COOKIE_AGE=60 * 60)
    @patch('otp_yubikey.models.RemoteYubikeyDevice.verify_token')
    def test_login_with_remember_cookie(self, verify_token):
        user = self.create_user()
        verify_token.return_value = True
        service = ValidationService.objects.create(name='default', param_sl='', param_timeout='')
        user.remoteyubikeydevice_set.create(service=service, name='default')

        response = self.client.post(reverse('two_factor:login'),
                                    data={'auth-username': 'bouke@example.com',
                                          'auth-password': 'secret',
                                          'login_view-current_step': 'auth'})
        # Should call verify_token
        token = 'cjikftknbiktlitnbltbitdncgvrbgic'
        response = self.client.post(reverse('two_factor:login'),
                                    data={'token-otp_token': token,
                                          'login_view-current_step': 'token',
                                          'token-remember': 'on'})
        self.assertRedirects(response, resolve_url(settings.LOGIN_REDIRECT_URL))
        verify_token.assert_called_with(token)

        self.client.post(reverse('logout'))
        response = self.client.post(reverse('two_factor:login'),
                                    data={'auth-username': 'bouke@example.com',
                                          'auth-password': 'secret',
                                          'login_view-current_step': 'auth'})
        self.assertRedirects(response, resolve_url(settings.LOGIN_REDIRECT_URL))
