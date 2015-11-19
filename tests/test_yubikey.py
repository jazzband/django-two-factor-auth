# encoding=UTF8
from __future__ import unicode_literals
import sys

try:
    import unittest2 as unittest
except ImportError:
    import unittest

try:
    from unittest.mock import patch
except ImportError:
    from mock import patch

from django import forms
from django.conf import settings
from django.core.urlresolvers import reverse
from django.test import TestCase
from django.utils import six

try:
    from django.contrib.auth import get_user_model
except ImportError:
    from django.contrib.auth.models import User
else:
    User = get_user_model()

try:
    from otp_yubikey.models import ValidationService, RemoteYubikeyDevice
except ImportError:
    ValidationService = RemoteYubikeyDevice = None

from .tests import UserMixin


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

        # self.assertRaises is broken on Python 2.7.10. See also
        # https://bugs.python.org/issue24134 and
        # https://code.djangoproject.com/ticket/24903.
        if sys.version_info < (2, 7, 10) or sys.version_info >= (2, 7, 11):
            # Without ValidationService it won't work
            with six.assertRaisesRegex(self, KeyError, "No ValidationService "
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
        self.assertRedirects(response, str(settings.LOGIN_REDIRECT_URL))
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
